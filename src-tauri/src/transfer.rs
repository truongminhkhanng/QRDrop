use crate::{auth, config, errors::{AppError, Result}, files, hash, protocol::{FileState, FileView, RecentTransfer}, session::{Manager, Session, SessionState}};
use axum::{body::Body, http::StatusCode};
use http_body_util::BodyExt;
use sha2::{Digest, Sha256};
use std::{io::SeekFrom, sync::Arc, time::{Duration, Instant}};
use tokio::io::{AsyncSeekExt, AsyncWriteExt};

pub struct FileWork {
    pub id: String,
    pub name: String,
    pub size: u64,
    pub offset: u64,
    pub file: Option<tokio::fs::File>,
    pub last_chunk: Option<(u64, u64, String)>,
}
pub async fn authorize(session: &Session, grant: &str) -> Result<()> {
    if session.cancel.is_cancelled() || session.expired().await { return Err(AppError::denied()); }
    let inner = session.inner.lock().await;
    if !matches!(inner.state, SessionState::Approved | SessionState::Transferring | SessionState::Verifying) || !inner.grant.as_ref().is_some_and(|value| auth::matches(value, grant)) { return Err(AppError::denied()); }
    Ok(())
}
async fn file_work(session: &Session, id: &str, allow_complete: bool) -> Result<Arc<tokio::sync::Mutex<FileWork>>> {
    let inner = session.inner.lock().await;
    let index = inner.files.iter().position(|file| file.id == id).ok_or_else(|| AppError::invalid("Tệp không thuộc danh sách được duyệt."))?;
    if !allow_complete && inner.files[index].status == FileState::Complete { return Err(AppError::conflict("Tệp đã hoàn tất.")); }
    if inner.files[index].status != FileState::Complete && inner.files.iter().take(index).any(|file| file.status != FileState::Complete) { return Err(AppError::conflict("Hãy gửi từng tệp theo thứ tự.")); }
    Ok(inner.work[index].clone())
}
pub async fn chunk(session: Arc<Session>, grant: &str, id: &str, start: u64, length: u64, digest: &str, mut body: Body) -> Result<u64> {
    authorize(&session, grant).await?;
    if length == 0 || length > config::CHUNK_BYTES || !auth::valid_digest(digest) { return Err(AppError::invalid("Phần dữ liệu gửi không hợp lệ. Hãy gửi lại tệp.")); }
    let _permit = session.operation.clone().try_acquire_owned().map_err(|_| AppError::conflict("Một tệp khác đang được xử lý."))?;
    let work = file_work(&session, id, false).await?;
    let mut work = work.lock().await;
    if let Some((previous_start, previous_length, previous_digest)) = &work.last_chunk {
        if start == *previous_start && length == *previous_length && digest.eq_ignore_ascii_case(previous_digest) {
            // Consume the bounded retry body before replying so HTTP clients do not
            // lose the ACK to a connection reset while they are still transmitting.
            verify_replay(&session, &mut body, length, digest).await?;
            return Ok(work.offset);
        }
    }
    if start != work.offset || start.checked_add(length).is_none_or(|end| end > work.size) { return Err(AppError::conflict("Tiến trình gửi và nhận chưa khớp. Hãy thử gửi lại tệp.")); }
    if work.file.is_none() { work.file = Some(files::open_part(&session.storage, &work.id)?); }
    let file = work.file.as_mut().ok_or_else(|| AppError::conflict("Tệp đang đóng."))?;
    file.seek(SeekFrom::Start(start)).await?;
    let mut hash = Sha256::new();
    let mut received = 0u64;
    {
        let mut inner = session.inner.lock().await;
        if inner.state.terminal() { return Err(AppError::denied()); }
        inner.state = SessionState::Transferring;
        if let Some(view) = inner.files.iter_mut().find(|view| view.id == id) { view.status = FileState::Receiving; }
    }
    let result: Result<()> = async {
        loop {
            let frame = tokio::select! {
                _ = session.cancel.cancelled() => return Err(AppError::conflict("Phiên đã bị hủy.")),
                value = tokio::time::timeout(Duration::from_secs(90), body.frame()) => value.map_err(|_| AppError::new(StatusCode::REQUEST_TIMEOUT, "chunk_timeout", "Kết nối bị gián đoạn. Hãy thử lại."))?,
            };
            let Some(frame) = frame else { break; };
            let frame = frame.map_err(|_| AppError::invalid("Dữ liệu gửi bị gián đoạn. Kiểm tra kết nối mạng và thử lại."))?;
            if let Ok(data) = frame.into_data() {
                if received.saturating_add(data.len() as u64) > length { return Err(AppError::new(StatusCode::PAYLOAD_TOO_LARGE, "chunk_too_large", "Dữ liệu gửi vượt kích thước đã khai báo. Hãy gửi lại tệp.")); }
                tokio::select! {
                    _ = session.cancel.cancelled() => return Err(AppError::conflict("Phiên đã bị hủy.")),
                    value = file.write_all(&data) => value?,
                }
                hash.update(&data);
                received += data.len() as u64;
                let mut inner = session.inner.lock().await;
                inner.last_progress = Instant::now();
                if let Some(view) = inner.files.iter_mut().find(|view| view.id == id) { view.received = start + received; }
            }
        }
        if received != length { return Err(AppError::invalid("Dữ liệu chưa được gửi đầy đủ. Kiểm tra kết nối mạng và thử lại.")); }
        if !hex::encode(hash.finalize()).eq_ignore_ascii_case(digest) { return Err(AppError::new(StatusCode::UNPROCESSABLE_ENTITY, "hash_mismatch", "Dữ liệu nhận được không khớp với dữ liệu gửi. Hãy gửi lại tệp.")); }
        file.flush().await?;
        Ok(())
    }.await;
    if let Err(error) = result {
        file.set_len(start).await?;
        file.seek(SeekFrom::Start(start)).await?;
        { let mut inner = session.inner.lock().await; if let Some(view) = inner.files.iter_mut().find(|v| v.id == id) { view.received = start; } }
        if error.code == "storage_error" { session.terminate(SessionState::Failed, Some(error.message.clone())).await; }
        return Err(error);
    }
    if session.cancel.is_cancelled() { file.set_len(start).await?; return Err(AppError::denied()); }
    work.offset = start + length;
    work.last_chunk = Some((start, length, digest.to_ascii_lowercase()));
    Ok(work.offset)
}
async fn verify_replay(session: &Session, body: &mut Body, length: u64, expected: &str) -> Result<()> {
    let mut hash = Sha256::new();
    let mut received = 0u64;
    loop {
        let frame = tokio::select! {
            _ = session.cancel.cancelled() => return Err(AppError::denied()),
            value = tokio::time::timeout(Duration::from_secs(90), body.frame()) => value.map_err(|_| AppError::new(StatusCode::REQUEST_TIMEOUT, "chunk_timeout", "Kết nối bị gián đoạn. Hãy thử lại."))?,
        };
        let Some(frame) = frame else { break; };
        let frame = frame.map_err(|_| AppError::invalid("Phần dữ liệu gửi lại bị gián đoạn."))?;
        if let Ok(data) = frame.into_data() {
            if received.saturating_add(data.len() as u64) > length { return Err(AppError::new(StatusCode::PAYLOAD_TOO_LARGE, "chunk_too_large", "Phần dữ liệu gửi lại vượt kích thước đã khai báo.")); }
            hash.update(&data);
            received += data.len() as u64;
        }
    }
    if received != length { return Err(AppError::invalid("Phần dữ liệu gửi lại chưa đầy đủ.")); }
    if !hex::encode(hash.finalize()).eq_ignore_ascii_case(expected) { return Err(AppError::new(StatusCode::UNPROCESSABLE_ENTITY, "hash_mismatch", "Dữ liệu gửi lại không khớp.")); }
    Ok(())
}
pub async fn start_verification(session: Arc<Session>, manager: Arc<Manager>, grant: &str, id: &str, expected: String) -> Result<()> {
    authorize(&session, grant).await?;
    if !auth::valid_digest(&expected) { return Err(AppError::invalid("Thông tin kiểm tra tệp không hợp lệ. Hãy gửi lại tệp.")); }
    {
        let inner = session.inner.lock().await;
        if let Some(view) = inner.files.iter().find(|f| f.id == id) {
            if view.status == FileState::Complete {
                return if view.sha256.as_ref().is_some_and(|hash| hash.eq_ignore_ascii_case(&expected)) { Ok(()) } else { Err(AppError::conflict("Tệp đã lưu khác với dữ liệu đang gửi. Hãy tạo mã QR mới để gửi lại.")) };
            }
            if view.status == FileState::Verifying { return Ok(()); }
        }
    }
    let permit = session.operation.clone().try_acquire_owned().map_err(|_| AppError::conflict("Một tệp khác đang được xử lý."))?;
    let work = file_work(&session, id, false).await?;
    { let work = work.lock().await; if work.offset != work.size { return Err(AppError::conflict("Tệp chưa được gửi đầy đủ.")); } }
    { let mut inner = session.inner.lock().await; if inner.state.terminal() { return Err(AppError::denied()); } inner.state = SessionState::Transferring; inner.last_progress = Instant::now(); if let Some(view) = inner.files.iter_mut().find(|f| f.id == id) { view.status = FileState::Verifying; } }
    let id = id.to_owned();
    tokio::spawn(async move {
        let _permit = permit;
        if let Err(error) = verify_file(&session, &manager, work, &id, &expected).await {
            session.terminate(SessionState::Failed, Some(error.message)).await;
        }
    });
    Ok(())
}
async fn verify_file(session: &Session, manager: &Manager, work: Arc<tokio::sync::Mutex<FileWork>>, id: &str, expected: &str) -> Result<()> {
    let mut work = work.lock().await;
    if work.file.is_none() { work.file = Some(files::open_part(&session.storage, id)?); }
    let file = work.file.as_mut().ok_or_else(|| AppError::conflict("Tệp đang đóng."))?;
    file.flush().await?;
    file.sync_all().await?;
    let digest = hash::disk_digest(file, &session.cancel, &session.inner).await?;
    if !digest.eq_ignore_ascii_case(expected) { return Err(AppError::new(StatusCode::UNPROCESSABLE_ENTITY, "hash_mismatch", "Dữ liệu nhận được không khớp với tệp đã gửi. Tệp chưa được lưu hoàn tất; hãy gửi lại.")); }
    drop(work.file.take());
    let mut inner = session.inner.lock().await;
    if inner.state.terminal() || session.cancel.is_cancelled() { return Err(AppError::denied()); }
    let (saved, warning) = files::publish(&session.storage, id, &work.name)?;
    if let Some(warning) = warning { inner.error = Some(warning); }
    if let Some(view) = inner.files.iter_mut().find(|f| f.id == id) { view.status = FileState::Complete; view.sha256 = Some(digest.clone()); view.saved_name = Some(saved.clone()); }
    inner.last_progress = Instant::now();
    drop(inner);
    let record = RecentTransfer { name: saved, size: work.size, sha256: digest, destination: session.storage.root.to_string_lossy().into_owned(), completed_at: crate::session::unix_now() };
    if let Err(error) = manager.record(record).await { session.inner.lock().await.error = Some(format!("Tệp đã lưu, nhưng không lưu được lịch sử: {}", error.message)); }
    Ok(())
}
pub async fn complete(session: &Session, grant: &str) -> Result<()> {
    authorize(session, grant).await?;
    let _permit = session.operation.clone().try_acquire_owned().map_err(|_| AppError::conflict("Đang xác minh tệp."))?;
    {
        let mut inner = session.inner.lock().await;
        if inner.files.is_empty() || inner.files.iter().any(|f| f.status != FileState::Complete) { return Err(AppError::conflict("Chưa hoàn tất tất cả tệp.")); }
        inner.state = SessionState::Verifying;
    }
    session.terminate(SessionState::Completed, None).await;
    Ok(())
}
pub fn views(inner: &crate::session::SessionInner) -> Vec<FileView> { inner.files.clone() }
