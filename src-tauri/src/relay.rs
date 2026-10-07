//! Bounded reverse HTTP bridge. The desktop makes only outbound connections;
//! TLS validates the operator's relay, which is inside this transport's trust boundary.
use crate::{auth, errors::{AppError, Result}, server::{self, ServerState}, session::{Manager, Session, SessionState}};
use axum::{body::Body, extract::ConnectInfo, http::Request};
use http_body_util::BodyExt;
use serde::Deserialize;
use std::{collections::HashMap, net::SocketAddr, sync::Arc, time::Duration};
use tower::ServiceExt;

#[derive(Clone)]
pub struct Registration {
    pub origin: String,
    pub id: String,
    secret: String,
    client: reqwest::Client,
    pub allow_insecure_loopback: bool,
}
#[derive(Deserialize)]
struct Message { id: String, method: String, path: String, peer: std::net::IpAddr, headers: HashMap<String, String> }
fn unavailable() -> AppError { AppError::conflict("Không kết nối được với máy chủ. Kiểm tra Internet rồi bật nhận tệp lại.") }
impl Registration {
    pub async fn open(origin: &str, allow_insecure_loopback: bool, receiver_id: &str, receiver_secret: &str) -> Result<Self> {
        let url = reqwest::Url::parse(origin).map_err(|_| AppError::invalid("Địa chỉ máy chủ không hợp lệ."))?;
        if url.path() != "/" || url.query().is_some() || url.fragment().is_some() || !url.username().is_empty() || url.password().is_some() ||
            (url.scheme() != "https" && !(allow_insecure_loopback && url.scheme() == "http" && url.host_str() == Some("127.0.0.1"))) {
            return Err(AppError::invalid("Kết nối Internet cần máy chủ HTTPS."));
        }
        let registration = Self {
            origin: url.origin().ascii_serialization(), id: auth::random_token()?, secret: auth::random_token()?, allow_insecure_loopback,
            client: reqwest::Client::builder().redirect(reqwest::redirect::Policy::none()).connect_timeout(Duration::from_secs(10)).timeout(Duration::from_secs(110)).build().map_err(|_| unavailable())?,
        };
        let response = registration.client.post(format!("{}/receiver", registration.origin)).json(&serde_json::json!({"id": registration.id, "secret": registration.secret, "receiver_id": receiver_id, "receiver_secret": receiver_secret})).send().await.map_err(|_| unavailable())?;
        if response.status() != reqwest::StatusCode::CREATED { return Err(unavailable()); }
        Ok(registration)
    }
    pub fn mobile_url(&self) -> String { format!("{}/s/{}/connect", self.origin, self.id) }
    fn endpoint(&self, suffix: &str) -> String { format!("{}/receiver/{}{}", self.origin, self.id, suffix) }
    pub async fn close(&self) {
        // Remote outage cannot keep a local receiver alive; the relay lease also expires.
        let _ = self.client.delete(self.endpoint("")).bearer_auth(&self.secret).timeout(Duration::from_secs(3)).send().await;
    }
    async fn poll(&self) -> Result<Option<Message>> {
        let mut response = self.client.post(self.endpoint("/poll")).bearer_auth(&self.secret).timeout(Duration::from_secs(30)).send().await.map_err(|_| unavailable())?;
        if response.status() == reqwest::StatusCode::NO_CONTENT { return Ok(None); }
        if response.status() != reqwest::StatusCode::OK { return Err(unavailable()); }
        let mut data = Vec::new();
        while let Some(chunk) = response.chunk().await.map_err(|_| unavailable())? {
            if data.len() + chunk.len() > 16 * 1024 { return Err(unavailable()); }
            data.extend_from_slice(&chunk);
        }
        serde_json::from_slice(&data).map(Some).map_err(|_| unavailable())
    }
    async fn dispatch(&self, app: axum::Router, message: Message) -> Result<()> {
        if message.id.len() != 32 || !message.id.bytes().all(|c| c.is_ascii_hexdigit()) || !message.path.starts_with('/') || message.path.contains(['?', '#']) || message.headers.len() > 16 { return Err(unavailable()); }
        let mut builder = Request::builder().method(message.method.as_str()).uri(&message.path);
        for (name, value) in message.headers {
            if !matches!(name.as_str(), "host" | "origin" | "sec-fetch-site" | "authorization" | "content-type" | "content-length" | "x-qrdrop-offset" | "x-qrdrop-length" | "x-qrdrop-sha256") { return Err(unavailable()); }
            builder = builder.header(name, value);
        }
        // A complete bounded request avoids cancelling the phone's connection
        // when a handler rejects credentials before consuming its request body.
        // Never buffer a whole file: PUT is limited to one 8 MiB chunk.
        let data = if message.method == "GET" { Vec::new() } else {
            let mut body = self.client.get(self.endpoint(&format!("/requests/{}/body", message.id))).bearer_auth(&self.secret).send().await.map_err(|_| unavailable())?;
            if !body.status().is_success() { return Err(unavailable()); }
            let limit = if message.method == "PUT" { crate::config::CHUNK_BYTES as usize } else { crate::config::MANIFEST_BYTES };
            let mut data = Vec::new();
            while let Some(chunk) = body.chunk().await.map_err(|_| unavailable())? {
                if data.len() + chunk.len() > limit { return Err(unavailable()); }
                data.extend_from_slice(&chunk);
            }
            data
        };
        let mut request = builder.body(Body::from(data)).map_err(|_| unavailable())?;
        request.extensions_mut().insert(ConnectInfo(server::limited::Peer(SocketAddr::from((message.peer, 0)))));
        let response = app.oneshot(request).await.map_err(|_| unavailable())?;
        let status = response.status().as_u16();
        let content_type = response.headers().get("content-type").and_then(|value| value.to_str().ok()).unwrap_or("application/octet-stream").to_owned();
        let response = self.client.post(self.endpoint(&format!("/requests/{}/response", message.id))).bearer_auth(&self.secret)
            .header("x-qrdrop-status", status).header("x-qrdrop-content-type", content_type)
            .body(reqwest::Body::wrap_stream(response.into_body().into_data_stream())).send().await.map_err(|_| unavailable())?;
        if !response.status().is_success() { return Err(unavailable()); }
        Ok(())
    }
}
pub fn spawn(registration: Registration, session: Arc<Session>, manager: Arc<Manager>) {
    let app = server::router(ServerState { session: session.clone(), manager: manager.clone() });
    let running = session.clone();
    let task = tokio::spawn(async move {
        let mut work = tokio::task::JoinSet::new();
        let mut failures = 0;
        loop {
            while work.try_join_next().is_some() {}
            if work.len() >= 16 {
                tokio::select! { _ = running.stop_server.cancelled() => break, _ = work.join_next() => {} }
                continue;
            }
            tokio::select! {
                _ = running.stop_server.cancelled() => break,
                message = registration.poll() => match message {
                    Ok(Some(message)) => { failures = 0; let registration = registration.clone(); let app = app.clone(); work.spawn(async move { registration.dispatch(app, message).await }); },
                    Ok(None) => { failures = 0; },
                    Err(_) => {
                        failures += 1;
                        if failures >= 5 { running.terminate(SessionState::Failed, Some(unavailable().message)).await; break; }
                        tokio::select! { _ = running.stop_server.cancelled() => break, _ = tokio::time::sleep(Duration::from_secs(2)) => {} }
                    }
                }
            }
        }
        work.abort_all();
        while work.join_next().await.is_some() {}
        registration.close().await;
    });
    *session.server_task.try_lock().expect("new session server task lock") = Some(task);
    server::watch(session, manager);
}
