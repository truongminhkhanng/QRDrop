use crate::{auth, config, errors::{AppError, Result}, files::{self, Storage}, network, protocol::{FileState, FileView, RecentTransfer}, transfer::FileWork};
use serde::Serialize;
use std::{net::SocketAddr, path::PathBuf, sync::Arc, time::{Duration, Instant, SystemTime, UNIX_EPOCH}};
use tokio::sync::{Mutex, Semaphore};
use tokio_util::sync::CancellationToken;

#[derive(Clone, Copy, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SessionState { Waiting, WaitingForApproval, Approved, Transferring, Verifying, Completed, Rejected, Expired, Cancelled, Failed, PartiallyCompleted }
impl SessionState {
    pub fn terminal(self) -> bool { matches!(self, Self::Completed | Self::Rejected | Self::Expired | Self::Cancelled | Self::Failed | Self::PartiallyCompleted) }
}
pub struct SessionInner {
    pub state: SessionState,
    pub join_token: String,
    pub attempt_token: Option<String>,
    pub grant: Option<String>,
    pub request_fingerprint: Option<String>,
    pub device: Option<String>,
    pub peer: Option<String>,
    pub files: Vec<FileView>,
    pub work: Vec<Arc<Mutex<FileWork>>>,
    pub approved_at: Option<Instant>,
    pub last_progress: Instant,
    pub terminal_at: Option<Instant>,
    pub error: Option<String>,
}
pub struct Session {
    pub id: String,
    pub address: SocketAddr,
    pub created: Instant,
    pub created_unix: u64,
    pub qr_svg: String,
    pub storage: Arc<Storage>,
    pub inner: Mutex<SessionInner>,
    pub cancel: CancellationToken,
    pub stop_server: CancellationToken,
    pub server_task: Mutex<Option<tokio::task::JoinHandle<()>>>,
    pub operation: Arc<Semaphore>,
    pub state_dir: PathBuf,
    pub allow_loopback: bool,
    pub requests: Arc<Semaphore>,
    pub rate: Mutex<std::collections::HashMap<std::net::IpAddr, (Instant, u32)>>,
}
#[derive(Clone, Serialize)]
pub struct DesktopSnapshot {
    pub session_id: String, pub state: SessionState, pub url: String, pub qr_svg: String,
    pub address: String, pub expires_at: u64, pub device: Option<String>, pub peer: Option<String>,
    pub files: Vec<FileView>, pub error: Option<String>, pub destination: String,
}
pub struct Manager {
    pub current: Mutex<Option<Arc<Session>>>,
    pub settings: Mutex<config::Settings>,
    pub state_dir: PathBuf,
    pub recent: Mutex<Vec<RecentTransfer>>,
    _instance_lock: std::fs::File,
}
pub fn unix_now() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() }
impl Manager {
    pub fn new(state_dir: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(&state_dir)?;
        let lock = std::fs::OpenOptions::new().read(true).write(true).create(true).truncate(false).open(state_dir.join("instance.lock"))?;
        fs2::FileExt::try_lock_exclusive(&lock).map_err(|_| AppError::conflict("QRDrop đang chạy trong một cửa sổ khác."))?;
        files::recover(&state_dir)?;
        let settings = config::load(&state_dir)?;
        let recent = match std::fs::read(state_dir.join("recent.json")) {
            Ok(bytes) => serde_json::from_slice(&bytes).map_err(|_| AppError::invalid("Lịch sử nhận tệp không hợp lệ."))?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Vec::new(), Err(e) => return Err(e.into()),
        };
        Ok(Self { current: Mutex::new(None), settings: Mutex::new(settings), state_dir, recent: Mutex::new(recent), _instance_lock: lock })
    }
    pub async fn start(self: &Arc<Self>, requested: Option<std::net::Ipv4Addr>) -> Result<DesktopSnapshot> {
        let ip = network::choose(requested)?;
        self.start_at(SocketAddr::from((ip, 0)), false).await
    }
    // Loopback is allowed only for the headless test harness, never desktop network selection.
    pub async fn start_at(self: &Arc<Self>, address: SocketAddr, allow_loopback: bool) -> Result<DesktopSnapshot> {
        if !matches!(address.ip(), std::net::IpAddr::V4(ip) if ip.is_private() || (allow_loopback && ip.is_loopback())) { return Err(AppError::invalid("Hãy chọn kết nối mạng nội bộ của máy tính.")); }
        let mut current = self.current.lock().await;
        if let Some(previous) = current.as_ref() {
            if !previous.inner.lock().await.state.terminal() { return Err(AppError::conflict("Hủy phiên hiện tại trước khi tạo mã QR mới.")); }
            previous.close_server().await;
            // Wait for disk operation and cleanup before replacing the crash journal.
            let _permit = previous.operation.acquire().await.map_err(|_| AppError::conflict("Phiên đang đóng."))?;
            previous.cleanup().await?;
        }
        let listener = tokio::net::TcpListener::bind(address).await?;
        let address = listener.local_addr()?;
        let id = uuid::Uuid::new_v4().to_string();
        let token = auth::random_token()?;
        let url = format!("http://{address}/connect#t={token}");
        let qr_svg = qrcode::QrCode::new(url.as_bytes()).map_err(|_| AppError::invalid("Không thể tạo mã QR."))?.render::<qrcode::render::svg::Color>().min_dimensions(280, 280).build();
        let destination = self.settings.lock().await.destination.clone();
        let storage = Arc::new(files::create(&destination, &self.state_dir, &id)?);
        let session = Arc::new(Session {
            id, address, created: Instant::now(), created_unix: unix_now(), qr_svg, storage,
            inner: Mutex::new(SessionInner { state: SessionState::Waiting, join_token: token, attempt_token: None, grant: None, request_fingerprint: None, device: None, peer: None, files: Vec::new(), work: Vec::new(), approved_at: None, last_progress: Instant::now(), terminal_at: None, error: None }),
            cancel: CancellationToken::new(), stop_server: CancellationToken::new(), server_task: Mutex::new(None), operation: Arc::new(Semaphore::new(1)), state_dir: self.state_dir.clone(), allow_loopback,
            requests: Arc::new(Semaphore::new(16)), rate: Mutex::new(std::collections::HashMap::new()),
        });
        crate::server::spawn(listener, session.clone(), self.clone()).await;
        *current = Some(session.clone());
        drop(current);
        Ok(session.snapshot().await)
    }
    pub async fn active(&self) -> Result<Arc<Session>> { self.current.lock().await.clone().ok_or_else(|| AppError::conflict("Chưa có phiên nhận tệp.")) }
    pub async fn cancel(&self) -> Result<()> { self.active().await?.terminate(SessionState::Cancelled, None).await; Ok(()) }
    pub async fn stop_receiving(&self) -> Result<()> {
        // Serialize stop/start so cleanup cannot remove a newer session's files.
        let mut current = self.current.lock().await;
        let Some(session) = current.as_ref().cloned() else { return Ok(()); };
        session.terminate(SessionState::Cancelled, None).await;
        session.close_server().await;
        let _permit = session.operation.acquire().await.map_err(|_| AppError::conflict("Phiên đang đóng."))?;
        // Retain the cancelled session on cleanup failure so the next start must
        // retry cleanup before it replaces the ownership journal.
        session.cleanup().await?;
        *current = None;
        Ok(())
    }
    pub async fn decide(&self, id: &str, accept: bool) -> Result<()> {
        let session = self.active().await?;
        if session.id != id { return Err(AppError::conflict("Yêu cầu này không còn hiệu lực.")); }
        let mut inner = session.inner.lock().await;
        if inner.state != SessionState::WaitingForApproval || session.created.elapsed().as_secs() >= config::JOIN_SECONDS { return Err(AppError::conflict("Yêu cầu đã hết hạn hoặc đã được xử lý.")); }
        if accept {
            let total: u64 = inner.files.iter().map(|f| f.size).sum();
            if fs2::available_space(&session.storage.root)? < total.saturating_add(16 * 1024 * 1024) { return Err(AppError::new(axum::http::StatusCode::INSUFFICIENT_STORAGE, "disk_full", "Thư mục nhận không đủ dung lượng trống.")); }
            inner.grant = Some(auth::random_token()?);
            inner.state = SessionState::Approved;
            inner.approved_at = Some(Instant::now());
            inner.last_progress = Instant::now();
            inner.join_token.clear();
        } else {
            session.terminate_inner(&mut inner, SessionState::Rejected, None);
        }
        Ok(())
    }
    pub async fn set_destination(&self, path: PathBuf) -> Result<()> {
        if !path.is_absolute() { return Err(AppError::invalid("Hãy chọn đường dẫn thư mục tuyệt đối.")); }
        std::fs::create_dir_all(&path)?;
        let path = std::fs::canonicalize(path)?;
        let updated = config::Settings { destination: path };
        config::save(&self.state_dir, &updated)?;
        *self.settings.lock().await = updated;
        Ok(())
    }
    pub async fn record(&self, item: RecentTransfer) -> Result<()> {
        let mut recent = self.recent.lock().await;
        recent.insert(0, item);
        recent.truncate(100);
        let bytes = serde_json::to_vec_pretty(&*recent).map_err(|_| AppError::invalid("Không thể lưu lịch sử nhận tệp."))?;
        std::fs::write(self.state_dir.join("recent.new.json"), bytes)?;
        std::fs::rename(self.state_dir.join("recent.new.json"), self.state_dir.join("recent.json"))?;
        Ok(())
    }
}
impl Session {
    pub async fn close_server(&self) {
        self.stop_server.cancel();
        if let Some(task) = self.server_task.lock().await.take() {
            task.abort();
            let _ = task.await;
        }
    }
    pub async fn snapshot(&self) -> DesktopSnapshot {
        let inner = self.inner.lock().await;
        let url = if inner.state == SessionState::Waiting { format!("http://{}/connect#t={}", self.address, inner.join_token) } else { String::new() };
        let qr_svg = if url.is_empty() { String::new() } else { self.qr_svg.clone() };
        DesktopSnapshot { session_id: self.id.clone(), state: inner.state, url, qr_svg, address: self.address.to_string(), expires_at: self.created_unix + config::JOIN_SECONDS,
            device: inner.device.clone(), peer: inner.peer.clone(), files: inner.files.clone(), error: inner.error.clone(), destination: self.storage.root.to_string_lossy().into_owned() }
    }
    pub async fn terminate(&self, requested: SessionState, error: Option<String>) {
        let mut inner = self.inner.lock().await;
        self.terminate_inner(&mut inner, requested, error);
    }
    fn terminate_inner(&self, inner: &mut SessionInner, requested: SessionState, error: Option<String>) {
        if inner.state.terminal() { return; }
        inner.state = if requested != SessionState::Completed && inner.files.iter().any(|f| f.status == FileState::Complete) { SessionState::PartiallyCompleted } else { requested };
        inner.join_token.clear(); inner.grant = None;
        if error.is_some() { inner.error = error; }
        inner.terminal_at = Some(Instant::now());
        for file in &mut inner.files { if file.status != FileState::Complete { file.status = if matches!(requested, SessionState::Failed | SessionState::Expired) { FileState::Failed } else { FileState::Cancelled }; } }
        self.cancel.cancel();
    }
    pub async fn cleanup(&self) -> Result<()> {
        let work = self.inner.lock().await.work.clone();
        // Close all file handles before removing files (important on Windows).
        for item in &work { drop(item.lock().await.file.take()); }
        let ids: Vec<_> = self.inner.lock().await.files.iter().map(|f| f.id.clone()).collect();
        files::cleanup(&self.storage, &ids, &self.state_dir)
    }
    pub async fn expired(&self) -> bool {
        let inner = self.inner.lock().await;
        if inner.state.terminal() { return false; }
        match inner.state {
            SessionState::Waiting | SessionState::WaitingForApproval => self.created.elapsed() >= Duration::from_secs(config::JOIN_SECONDS),
            SessionState::Approved => inner.last_progress.elapsed() >= Duration::from_secs(config::START_SECONDS),
            _ => inner.last_progress.elapsed() >= Duration::from_secs(config::IDLE_SECONDS) || inner.approved_at.is_some_and(|t| t.elapsed() >= Duration::from_secs(config::MAX_SESSION_SECONDS)),
        }
    }
}
