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
    pub requested_at: Option<Instant>,
    pub requested_unix: Option<u64>,
    pub paired_device_token: Option<String>,
    pub trusted_device_id: Option<String>,
    pub trusted_device_name: Option<String>,
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
    pub replaces_session_id: Option<String>,
    pub relay: Option<crate::relay::Registration>,
    pub receiver_id: String,
    pub storage: Arc<Storage>,
    pub inner: Mutex<SessionInner>,
    pub cancel: CancellationToken,
    pub stop_server: CancellationToken,
    pub server_task: Mutex<Option<tokio::task::JoinHandle<()>>>,
    pub operation: Arc<Semaphore>,
    pub state_dir: PathBuf,
    pub allow_loopback: bool,
    pub requests: Arc<Semaphore>,
    pub rate: Arc<Mutex<std::collections::HashMap<std::net::IpAddr, (Instant, u32)>>>,
}
#[derive(Clone, Serialize)]
pub struct DesktopSnapshot {
    pub session_id: String, pub state: SessionState, pub url: String, pub qr_svg: String,
    pub address: String, pub expires_at: u64, pub device: Option<String>, pub peer: Option<String>,
    pub files: Vec<FileView>, pub error: Option<String>, pub destination: String,
    pub approval_expires_at: Option<u64>, pub replaces_session_id: Option<String>,
    pub transport: &'static str,
    pub trust_available: bool, pub trusted_device_name: Option<String>,
}
pub struct Manager {
    pub current: Mutex<Option<Arc<Session>>>,
    pub settings: Mutex<config::Settings>,
    pub state_dir: PathBuf,
    pub recent: Mutex<Vec<RecentTransfer>>,
    connect_rate: Arc<Mutex<std::collections::HashMap<std::net::IpAddr, (Instant, u32)>>>,
    pub trusted: Mutex<crate::trust::TrustStore>,
    _instance_lock: std::fs::File,
}
pub fn unix_now() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() }
enum ReceiverConfig { Lan(SocketAddr, bool), Internet(String, bool) }
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
        let trusted = crate::trust::TrustStore::load(&state_dir)?;
        Ok(Self { current: Mutex::new(None), settings: Mutex::new(settings), state_dir, recent: Mutex::new(recent), connect_rate: Arc::new(Mutex::new(std::collections::HashMap::new())), trusted: Mutex::new(trusted), _instance_lock: lock })
    }
    pub async fn start(self: &Arc<Self>, requested: Option<std::net::Ipv4Addr>) -> Result<DesktopSnapshot> {
        // The operator embeds the verified endpoint in the installer. Users
        // never need credentials, a tunnel CLI or a port-forwarding setup.
        if requested.is_none() {
            if let Some(origin) = option_env!("QRDROP_RELAY_URL").filter(|origin| !origin.is_empty()) { return self.start_relay(origin, false).await; }
        }
        let ip = network::choose(requested)?;
        self.start_at(SocketAddr::from((ip, 0)), false).await
    }
    // Loopback is allowed only for the headless test harness, never desktop network selection.
    pub async fn start_at(self: &Arc<Self>, address: SocketAddr, allow_loopback: bool) -> Result<DesktopSnapshot> {
        if !matches!(address.ip(), std::net::IpAddr::V4(ip) if ip.is_private() || (allow_loopback && ip.is_loopback())) { return Err(AppError::invalid("Hãy chọn kết nối mạng nội bộ của máy tính.")); }
        let mut current = self.current.lock().await;
        self.replace_receiver(&mut current, ReceiverConfig::Lan(address, allow_loopback), None).await
    }
    pub async fn start_relay(self: &Arc<Self>, origin: &str, allow_insecure_loopback: bool) -> Result<DesktopSnapshot> {
        let mut current = self.current.lock().await;
        self.replace_receiver(&mut current, ReceiverConfig::Internet(origin.to_owned(), allow_insecure_loopback), None).await
    }
    async fn replace_receiver(self: &Arc<Self>, current: &mut Option<Arc<Session>>, mode: ReceiverConfig, replaces_session_id: Option<String>) -> Result<DesktopSnapshot> {
        if let Some(previous) = current.as_ref() {
            if !previous.inner.lock().await.state.terminal() { return Err(AppError::conflict("Hủy phiên hiện tại trước khi tạo mã QR mới.")); }
            previous.close_server().await;
            // Wait for disk operation and cleanup before replacing the crash journal.
            let _permit = previous.operation.acquire().await.map_err(|_| AppError::conflict("Phiên đang đóng."))?;
            previous.cleanup().await?;
        }
        let (listener, relay, address, allow_loopback) = match mode {
            ReceiverConfig::Lan(address, allow_loopback) => {
                let listener = tokio::net::TcpListener::bind(address).await?;
                let address = listener.local_addr()?;
                (Some(listener), None, address, allow_loopback)
            },
            ReceiverConfig::Internet(origin, allow_insecure_loopback) => {
                let (receiver_id, receiver_secret) = { let trusted = self.trusted.lock().await; (trusted.receiver_id.clone(), trusted.receiver_secret.clone()) };
                let relay = crate::relay::Registration::open(&origin, allow_insecure_loopback, &receiver_id, &receiver_secret).await?;
                (None, Some(relay), SocketAddr::from(([127, 0, 0, 1], 0)), false)
            },
        };
        let id = uuid::Uuid::new_v4().to_string();
        let token = auth::random_token()?;
        let base = relay.as_ref().map_or_else(|| format!("http://{address}/connect"), |relay| relay.mobile_url());
        let receiver_id = self.trusted.lock().await.receiver_id.clone();
        let url = format!("{base}#t={token}&r={receiver_id}");
        let qr_svg = qrcode::QrCode::new(url.as_bytes()).map_err(|_| AppError::invalid("Không thể tạo mã QR."))?.render::<qrcode::render::svg::Color>().min_dimensions(280, 280).build();
        let destination = self.settings.lock().await.destination.clone();
        let storage = match files::create(&destination, &self.state_dir, &id) {
            Ok(storage) => Arc::new(storage),
            Err(error) => { if let Some(relay) = &relay { relay.close().await; } return Err(error); }
        };
        let session = Arc::new(Session {
            id, address, created: Instant::now(), created_unix: unix_now(), qr_svg, storage, replaces_session_id, relay: relay.clone(), receiver_id,
            inner: Mutex::new(SessionInner { state: SessionState::Waiting, join_token: token, attempt_token: None, grant: None, request_fingerprint: None, device: None, peer: None, files: Vec::new(), work: Vec::new(), requested_at: None, requested_unix: None, paired_device_token: None, trusted_device_id: None, trusted_device_name: None, approved_at: None, last_progress: Instant::now(), terminal_at: None, error: None }),
            cancel: CancellationToken::new(), stop_server: CancellationToken::new(), server_task: Mutex::new(None), operation: Arc::new(Semaphore::new(1)), state_dir: self.state_dir.clone(), allow_loopback,
            requests: Arc::new(Semaphore::new(16)), rate: self.connect_rate.clone(),
        });
        if let Some(relay) = relay { crate::relay::spawn(relay, session.clone(), self.clone()); }
        else if let Some(listener) = listener { crate::server::spawn(listener, session.clone(), self.clone()); }
        *current = Some(session.clone());
        Ok(session.snapshot().await)
    }
    // The same current-session lock serializes renewal with stop/manual refresh.
    // A late watcher must never replace a newer session or turn receiving back on.
    pub async fn renew_expired_request(self: &Arc<Self>, id: &str) -> Result<bool> {
        let mut current = self.current.lock().await;
        let Some(session) = current.as_ref().filter(|session| session.id == id).cloned() else { return Ok(false); };
        {
            let mut inner = session.inner.lock().await;
            if !matches!(inner.state, SessionState::Waiting | SessionState::WaitingForApproval) || !session.expired_inner(&inner) { return Ok(false); }
            session.terminate_inner(&mut inner, SessionState::Expired, Some("Yêu cầu đã hết hạn. Quét mã QR mới trên máy tính để gửi lại.".to_owned()));
            // A terminal request has no valid status credential after replacement.
            inner.attempt_token = None;
        }
        let mode = match &session.relay {
            Some(relay) => ReceiverConfig::Internet(relay.origin.clone(), relay.allow_insecure_loopback),
            None => ReceiverConfig::Lan(SocketAddr::from((session.address.ip(), 0)), session.allow_loopback),
        };
        self.replace_receiver(&mut current, mode, Some(session.id.clone())).await?;
        Ok(true)
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
        self.decide_with_trust(id, accept, false).await
    }
    pub async fn decide_with_trust(&self, id: &str, accept: bool, remember: bool) -> Result<()> {
        let session = self.active().await?;
        if session.id != id { return Err(AppError::conflict("Yêu cầu này không còn hiệu lực.")); }
        let mut inner = session.inner.lock().await;
        if inner.state != SessionState::WaitingForApproval || session.expired_inner(&inner) { return Err(AppError::conflict("Yêu cầu đã hết hạn hoặc đã được xử lý.")); }
        if accept {
            if remember && !session.trust_available() { return Err(AppError::invalid("Ghép đôi thiết bị cần kết nối HTTPS.")); }
            let grant = Self::checked_grant(&session, &inner)?;
            if remember {
                let (device, token) = self.trusted.lock().await.add(&self.state_dir, inner.device.as_deref().unwrap_or("Trình duyệt"))?;
                inner.paired_device_token = Some(token); inner.trusted_device_id = Some(device.id); inner.trusted_device_name = Some(device.name);
            }
            Self::approve_inner(&mut inner, grant);
        } else {
            session.terminate_inner(&mut inner, SessionState::Rejected, None);
        }
        Ok(())
    }
    fn checked_grant(session: &Session, inner: &SessionInner) -> Result<String> {
        let total: u64 = inner.files.iter().map(|file| file.size).sum();
        if fs2::available_space(&session.storage.root)? < total.saturating_add(16 * 1024 * 1024) { return Err(AppError::new(axum::http::StatusCode::INSUFFICIENT_STORAGE, "disk_full", "Thư mục nhận không đủ dung lượng trống.")); }
        auth::random_token()
    }
    fn approve_inner(inner: &mut SessionInner, grant: String) {
        inner.grant = Some(grant); inner.state = SessionState::Approved; inner.approved_at = Some(Instant::now()); inner.last_progress = Instant::now(); inner.join_token.clear();
    }
    pub async fn approve_trusted(&self, session: &Session, inner: &mut SessionInner, token: Option<&str>) -> Result<()> {
        if !session.trust_available() { return Ok(()); }
        let Some(token) = token else { return Ok(()); };
        let trusted = self.trusted.lock().await;
        if let Some(device) = trusted.find(token) {
            let grant = Self::checked_grant(session, inner)?;
            inner.trusted_device_id = Some(device.id); inner.trusted_device_name = Some(device.name); Self::approve_inner(inner, grant);
        }
        Ok(())
    }
    pub async fn forget_trusted_device(&self, id: &str) -> Result<()> {
        self.trusted.lock().await.remove(&self.state_dir, id)?;
        if let Some(session) = self.current.lock().await.as_ref() {
            let mut inner = session.inner.lock().await;
            if inner.trusted_device_id.as_deref() == Some(id) { session.terminate_inner(&mut inner, SessionState::Cancelled, Some("Quyền tin cậy đã bị thu hồi. Quét mã QR mới để gửi lại.".to_owned())); }
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
    pub fn trust_available(&self) -> bool { self.relay.as_ref().is_some_and(|relay| relay.origin.starts_with("https://") || relay.allow_insecure_loopback) }
    pub async fn close_server(&self) {
        self.stop_server.cancel();
        if let Some(task) = self.server_task.lock().await.take() {
            task.abort();
            let _ = task.await;
        }
        if let Some(relay) = &self.relay { relay.close().await; }
    }
    pub async fn snapshot(&self) -> DesktopSnapshot {
        let inner = self.inner.lock().await;
        let base = self.relay.as_ref().map_or_else(|| format!("http://{}/connect", self.address), |relay| relay.mobile_url());
        let url = if inner.state == SessionState::Waiting { format!("{base}#t={}&r={}", inner.join_token, self.receiver_id) } else { String::new() };
        let qr_svg = if url.is_empty() { String::new() } else { self.qr_svg.clone() };
        DesktopSnapshot { session_id: self.id.clone(), state: inner.state, url, qr_svg, address: self.relay.as_ref().map_or_else(|| self.address.to_string(), |relay| relay.origin.clone()), expires_at: self.created_unix + config::JOIN_SECONDS,
            device: inner.device.clone(), peer: inner.peer.clone(), files: inner.files.clone(), error: inner.error.clone(), destination: self.storage.root.to_string_lossy().into_owned(),
            approval_expires_at: if inner.state == SessionState::WaitingForApproval { inner.requested_unix.map(|at| at + config::APPROVAL_SECONDS) } else { None }, replaces_session_id: self.replaces_session_id.clone(), transport: if self.relay.is_some() { "internet" } else { "lan" }, trust_available: self.trust_available(), trusted_device_name: inner.trusted_device_name.clone() }
    }
    pub async fn terminate(&self, requested: SessionState, error: Option<String>) {
        let mut inner = self.inner.lock().await;
        self.terminate_inner(&mut inner, requested, error);
    }
    fn terminate_inner(&self, inner: &mut SessionInner, requested: SessionState, error: Option<String>) {
        if inner.state.terminal() { return; }
        inner.state = if requested != SessionState::Completed && inner.files.iter().any(|f| f.status == FileState::Complete) { SessionState::PartiallyCompleted } else { requested };
        inner.join_token.clear(); inner.grant = None; inner.paired_device_token = None;
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
        self.expired_inner(&inner)
    }
    pub fn expired_inner(&self, inner: &SessionInner) -> bool {
        if inner.state.terminal() { return false; }
        match inner.state {
            SessionState::Waiting => self.created.elapsed() >= Duration::from_secs(config::JOIN_SECONDS),
            SessionState::WaitingForApproval => inner.requested_at.is_none_or(|at| at.elapsed() >= Duration::from_secs(config::APPROVAL_SECONDS)),
            SessionState::Approved => inner.last_progress.elapsed() >= Duration::from_secs(config::START_SECONDS),
            _ => inner.last_progress.elapsed() >= Duration::from_secs(config::IDLE_SECONDS) || inner.approved_at.is_some_and(|t| t.elapsed() >= Duration::from_secs(config::MAX_SESSION_SECONDS)),
        }
    }
}
