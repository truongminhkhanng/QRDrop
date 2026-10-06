use crate::{auth, config, errors::{AppError, Result}, files, protocol::*, session::{Manager, Session, SessionState}, transfer::{self, FileWork}};
use axum::{body::Body, extract::{ConnectInfo, DefaultBodyLimit, Path, Request, State}, http::{header, HeaderMap, StatusCode}, middleware::{self, Next}, response::{IntoResponse, Response}, routing::{get, post, put}, Json, Router};
use include_dir::{include_dir, Dir};
use sha2::{Digest, Sha256};
use std::{sync::Arc, time::{Duration, Instant}};
use tokio::sync::Mutex;

static MOBILE: Dir<'_> = include_dir!("$CARGO_MANIFEST_DIR/../mobile-dist");
#[derive(Clone)]
pub struct ServerState { pub session: Arc<Session>, pub manager: Arc<Manager> }

pub fn router(state: ServerState) -> Router {
    Router::new()
        .route("/connect", get(page))
        .route("/", get(page))
        .route("/assets/{*path}", get(asset))
        .route("/api/connect", post(connect))
        .route("/api/status", get(status))
        .route("/api/files/{id}/chunks", put(chunk))
        .route("/api/files/{id}/finish", post(finish))
        .route("/api/complete", post(complete))
        .route("/api/cancel", post(cancel))
        .layer(DefaultBodyLimit::max(config::MANIFEST_BYTES))
        .layer(middleware::from_fn_with_state(state.clone(), guard))
        .with_state(state)
}
pub async fn spawn(listener: tokio::net::TcpListener, session: Arc<Session>, manager: Arc<Manager>) {
    let state = ServerState { session: session.clone(), manager };
    let app = router(state);
    let server_session = session.clone();
    let task = tokio::spawn(async move {
        let listener = crate::server::limited::LimitedListener::new(listener, server_session.allow_loopback);
        if axum::serve(listener, app.into_make_service_with_connect_info::<limited::Peer>()).with_graceful_shutdown(server_session.stop_server.clone().cancelled_owned()).await.is_err() {
            server_session.terminate(SessionState::Failed, Some("Kết nối nhận tệp đã dừng. Kiểm tra mạng và tạo mã QR mới để thử lại.".to_owned())).await;
        }
    });
    *session.server_task.lock().await = Some(task);
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(1)).await;
            if session.expired().await { session.terminate(SessionState::Expired, Some("Phiên đã hết hạn do không có tiến triển. Quét mã QR mới để thử lại.".to_owned())).await; }
            let terminal = session.inner.lock().await.state.terminal();
            if terminal {
                if let Ok(_permit) = session.operation.acquire().await {
                    if let Err(error) = session.cleanup().await { session.inner.lock().await.error = Some(format!("Không dọn được tệp tạm trong {}: {}", session.storage.root.display(), error.message)); }
                }
                tokio::select! { _ = session.stop_server.cancelled() => {}, _ = tokio::time::sleep(Duration::from_secs(30)) => {} }
                session.stop_server.cancel();
                break;
            }
        }
    });
}
async fn guard(State(state): State<ServerState>, request: Request, next: Next) -> Response {
    let session = &state.session;
    let expected = session.address.to_string();
    if request.headers().get(header::HOST).and_then(|h| h.to_str().ok()) != Some(expected.as_str()) { return AppError::denied().into_response(); }
    let expected_origin = format!("http://{expected}");
    let mut origins = request.headers().get_all(header::ORIGIN).iter();
    let supplied_origin = match origins.next() {
        Some(value) => match value.to_str() { Ok(origin) => Some(origin), Err(_) => return AppError::denied().into_response() },
        None => None,
    };
    if origins.next().is_some() { return AppError::denied().into_response(); }
    if supplied_origin.is_some_and(|value| value != expected_origin) || (request.method() != axum::http::Method::GET && supplied_origin != Some(expected_origin.as_str())) { return AppError::denied().into_response(); }
    if request.headers().get("sec-fetch-site").and_then(|h| h.to_str().ok()).is_some_and(|site| !matches!(site, "same-origin" | "none")) { return AppError::denied().into_response(); }
    let peer = request.extensions().get::<ConnectInfo<limited::Peer>>().map(|v| v.0.0.ip());
    if !peer.is_some_and(|ip| matches!(ip, std::net::IpAddr::V4(v4) if v4.is_private() || (session.allow_loopback && v4.is_loopback()))) { return AppError::denied().into_response(); }
    if request.uri().path().starts_with("/api/") {
        let inner = session.inner.lock().await;
        if inner.peer.as_ref().is_some_and(|selected| peer.is_none_or(|ip| selected != &ip.to_string())) { return AppError::denied().into_response(); }
    }
    if request.uri().path() == "/api/connect" {
        let mut rate = session.rate.lock().await;
        rate.retain(|_, (at, _)| at.elapsed() < Duration::from_secs(60));
        if rate.len() >= 256 { return StatusCode::TOO_MANY_REQUESTS.into_response(); }
        let Some(peer) = peer else { return AppError::denied().into_response(); };
        let entry = rate.entry(peer).or_insert((Instant::now(), 0));
        entry.1 += 1;
        if entry.1 > 10 { return AppError::new(StatusCode::TOO_MANY_REQUESTS, "rate_limited", "Quá nhiều yêu cầu kết nối. Hãy thử lại sau một phút.").into_response(); }
    }
    let Ok(_permit) = session.requests.clone().try_acquire_owned() else { return StatusCode::SERVICE_UNAVAILABLE.into_response(); };
    let mut response = next.run(request).await;
    let headers = response.headers_mut();
    headers.insert(header::CACHE_CONTROL, axum::http::HeaderValue::from_static("no-store"));
    headers.insert("referrer-policy", axum::http::HeaderValue::from_static("no-referrer"));
    headers.insert("x-content-type-options", axum::http::HeaderValue::from_static("nosniff"));
    headers.insert("content-security-policy", axum::http::HeaderValue::from_static("default-src 'self'; script-src 'self'; worker-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"));
    response
}
fn content(path: &str) -> Response {
    if let Some(file) = MOBILE.get_file(path) {
        let mime = mime_guess::from_path(path).first_or_octet_stream().to_string();
        ([(header::CONTENT_TYPE, mime)], file.contents().to_vec()).into_response()
    } else { StatusCode::NOT_FOUND.into_response() }
}
async fn page() -> Response { content("index.html") }
async fn asset(Path(path): Path<String>) -> Response {
    if path.contains("..") || path.contains('\\') { return StatusCode::NOT_FOUND.into_response(); }
    content(&format!("assets/{path}"))
}
fn credential(headers: &HeaderMap) -> Result<&str> {
    headers.get(header::AUTHORIZATION).and_then(|h| h.to_str().ok()).and_then(|value| value.strip_prefix("Bearer ")).filter(|value| value.len() == 64).ok_or_else(AppError::denied)
}
async fn connect(State(state): State<ServerState>, ConnectInfo(peer): ConnectInfo<limited::Peer>, Json(request): Json<ConnectRequest>) -> Result<Json<ConnectReply>> {
    if request.token.len() != 64 || request.device.len() > 128 || uuid::Uuid::parse_str(&request.request_id).is_err() || request.files.is_empty() || request.files.len() > config::MAX_FILES { return Err(AppError::invalid("Danh sách tệp hoặc yêu cầu kết nối không hợp lệ.")); }
    let mut total = 0u64;
    for file in &request.files {
        files::safe_name(&file.name)?;
        total = total.checked_add(file.size).ok_or_else(|| AppError::invalid("Dung lượng quá lớn."))?;
    }
    if total > 9_007_199_254_740_991 { return Err(AppError::invalid("Tổng dung lượng tệp vượt giới hạn của trình duyệt. Hãy chọn ít tệp hơn.")); }
    let fingerprint = hex::encode(Sha256::digest(serde_json::to_vec(&request).map_err(|_| AppError::invalid("Yêu cầu không hợp lệ."))?));
    let session = &state.session;
    if session.cancel.is_cancelled() || session.expired().await { return Err(AppError::denied()); }
    let mut inner = session.inner.lock().await;
    // Check again under the same lock that consumes the join token, including
    // concurrent requests that passed the middleware before a sender was selected.
    if inner.peer.as_ref().is_some_and(|selected| selected != &peer.0.ip().to_string()) { return Err(AppError::denied()); }
    if !inner.state.terminal() && inner.request_fingerprint.as_deref() == Some(fingerprint.as_str()) {
        return Ok(Json(ConnectReply { attempt_token: inner.attempt_token.clone().ok_or_else(AppError::denied)?, session_id: session.id.clone(), chunk_bytes: config::CHUNK_BYTES }));
    }
    if inner.state != SessionState::Waiting || session.created.elapsed().as_secs() >= config::JOIN_SECONDS || !auth::matches(&inner.join_token, &request.token) { return Err(AppError::denied()); }
    let attempt = auth::random_token()?;
    inner.work.clear(); inner.files.clear();
    for file in request.files {
        let id = uuid::Uuid::new_v4().to_string();
        let name = files::safe_name(&file.name)?;
        inner.files.push(FileView { id: id.clone(), name: name.clone(), saved_name: None, size: file.size, received: 0, status: FileState::Waiting, sha256: None });
        inner.work.push(Arc::new(Mutex::new(FileWork { id, name, size: file.size, offset: 0, file: None, last_chunk: None })));
    }
    inner.device = Some(format!("{} (chưa xác minh)", request.device));
    inner.peer = Some(peer.0.ip().to_string());
    inner.attempt_token = Some(attempt.clone());
    inner.request_fingerprint = Some(fingerprint);
    // Only an identical retry from this sender may recover the original reply.
    // The QR token can never create another request or change the approved files.
    inner.join_token.clear();
    inner.state = SessionState::WaitingForApproval;
    Ok(Json(ConnectReply { attempt_token: attempt, session_id: session.id.clone(), chunk_bytes: config::CHUNK_BYTES }))
}
async fn status(State(state): State<ServerState>, headers: HeaderMap) -> Result<Json<MobileStatus>> {
    let token = credential(&headers)?;
    let inner = state.session.inner.lock().await;
    if !inner.attempt_token.as_ref().is_some_and(|expected| auth::matches(expected, token)) { return Err(AppError::denied()); }
    Ok(Json(MobileStatus { state: inner.state, grant: if inner.state.terminal() { None } else { inner.grant.clone() }, files: inner.files.clone(), error: inner.error.clone() }))
}
fn number(headers: &HeaderMap, key: &str) -> Result<u64> { headers.get(key).and_then(|h| h.to_str().ok()).and_then(|s| s.parse().ok()).ok_or_else(|| AppError::invalid("Thông tin gửi tệp không đầy đủ. Quét mã QR mới để thử lại.")) }
async fn chunk(State(state): State<ServerState>, Path(id): Path<String>, headers: HeaderMap, body: Body) -> Result<Json<ChunkReply>> {
    if headers.get(header::CONTENT_TYPE).and_then(|v| v.to_str().ok()) != Some("application/octet-stream") { return Err(AppError::new(StatusCode::UNSUPPORTED_MEDIA_TYPE, "content_type", "Dữ liệu gửi không đúng định dạng. Quét mã QR mới để thử lại.")); }
    let length = number(&headers, "x-qrdrop-length")?;
    if number(&headers, "content-length")? != length { return Err(AppError::invalid("Kích thước dữ liệu gửi không khớp. Hãy gửi lại tệp.")); }
    let digest = headers.get("x-qrdrop-sha256").and_then(|h| h.to_str().ok()).ok_or_else(|| AppError::invalid("Thiếu thông tin kiểm tra tệp. Quét mã QR mới để thử lại."))?;
    let offset = match transfer::chunk(state.session.clone(), credential(&headers)?, &id, number(&headers, "x-qrdrop-offset")?, length, digest, body).await {
        Ok(offset) => offset,
        Err(error) => {
            if error.code == "storage_error" { state.session.terminate(SessionState::Failed, Some(error.message.clone())).await; }
            return Err(error);
        }
    };
    Ok(Json(ChunkReply { offset }))
}
async fn finish(State(state): State<ServerState>, Path(id): Path<String>, headers: HeaderMap, Json(request): Json<FinishRequest>) -> Result<StatusCode> {
    transfer::start_verification(state.session, state.manager, credential(&headers)?, &id, request.sha256).await?;
    Ok(StatusCode::ACCEPTED)
}
async fn complete(State(state): State<ServerState>, headers: HeaderMap) -> Result<StatusCode> { transfer::complete(&state.session, credential(&headers)?).await?; Ok(StatusCode::OK) }
async fn cancel(State(state): State<ServerState>, headers: HeaderMap) -> Result<StatusCode> {
    let inner = state.session.inner.lock().await;
    if !inner.attempt_token.as_ref().is_some_and(|token| auth::matches(token, credential(&headers).unwrap_or_default())) { return Err(AppError::denied()); }
    drop(inner);
    state.session.terminate(SessionState::Cancelled, None).await;
    Ok(StatusCode::OK)
}

mod limited {
    use std::{future::Future, io, net::SocketAddr, pin::Pin, sync::Arc, task::{Context, Poll}, time::Duration};
    use tokio::{io::{AsyncRead, AsyncWrite, ReadBuf}, net::{TcpListener, TcpStream}, sync::{OwnedSemaphorePermit, Semaphore}, time::{sleep, Sleep}};
    pub struct LimitedListener { listener: TcpListener, slots: Arc<Semaphore>, allow_loopback: bool }
    #[derive(Clone, Copy)]
    pub struct Peer(pub SocketAddr);
    impl LimitedListener { pub fn new(listener: TcpListener, allow_loopback: bool) -> Self { Self { listener, slots: Arc::new(Semaphore::new(64)), allow_loopback } } }
    pub struct Stream { socket: TcpStream, _permit: OwnedSemaphorePermit, timer: Pin<Box<Sleep>> }
    impl axum::serve::Listener for LimitedListener {
        type Io = Stream;
        type Addr = SocketAddr;
        async fn accept(&mut self) -> (Stream, SocketAddr) {
            loop {
                let permit = match self.slots.clone().acquire_owned().await { Ok(p) => p, Err(_) => continue };
                match self.listener.accept().await {
                    Ok((socket, peer)) if matches!(peer.ip(), std::net::IpAddr::V4(ip) if ip.is_private() || (self.allow_loopback && ip.is_loopback())) => return (Stream { socket, _permit: permit, timer: Box::pin(sleep(Duration::from_secs(90))) }, peer),
                    _ => tokio::time::sleep(Duration::from_millis(50)).await,
                }
            }
        }
        fn local_addr(&self) -> io::Result<SocketAddr> { self.listener.local_addr() }
    }
    impl<'a> axum::extract::connect_info::Connected<axum::serve::IncomingStream<'a, LimitedListener>> for Peer {
        fn connect_info(stream: axum::serve::IncomingStream<'a, LimitedListener>) -> Self { Self(*stream.remote_addr()) }
    }
    impl AsyncRead for Stream {
        fn poll_read(mut self: Pin<&mut Self>, cx: &mut Context<'_>, buf: &mut ReadBuf<'_>) -> Poll<io::Result<()>> {
            if self.timer.as_mut().poll(cx).is_ready() { return Poll::Ready(Err(io::Error::new(io::ErrorKind::TimedOut, "idle connection"))); }
            let previous = buf.filled().len();
            let result = Pin::new(&mut self.socket).poll_read(cx, buf);
            if buf.filled().len() > previous { self.timer.as_mut().reset(tokio::time::Instant::now() + Duration::from_secs(90)); }
            result
        }
    }
    impl AsyncWrite for Stream {
        fn poll_write(mut self: Pin<&mut Self>, cx: &mut Context<'_>, buf: &[u8]) -> Poll<io::Result<usize>> { Pin::new(&mut self.socket).poll_write(cx, buf) }
        fn poll_flush(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<io::Result<()>> { Pin::new(&mut self.socket).poll_flush(cx) }
        fn poll_shutdown(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<io::Result<()>> { Pin::new(&mut self.socket).poll_shutdown(cx) }
    }
}
