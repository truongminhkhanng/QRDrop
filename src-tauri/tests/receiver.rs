use qrdrop_lib::{auth, config::{Settings, START_SECONDS}, files, session::{Manager, SessionState}};
use reqwest::{Client, Method, Response, StatusCode};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{net::SocketAddr, sync::Arc, time::Duration};

struct Harness { manager: Arc<Manager>, client: Client, base: String, _root: tempfile::TempDir, destination: std::path::PathBuf }
impl Harness {
    async fn new() -> Self {
        let root = tempfile::tempdir().expect("test directory");
        let destination = root.path().join("receive");
        let manager = Arc::new(Manager::new(root.path().join("state")).expect("manager"));
        *manager.settings.lock().await = Settings { destination: destination.clone() };
        let snapshot = manager.start_at("127.0.0.1:0".parse::<SocketAddr>().expect("address"), true).await.expect("listener");
        Self { manager, client: Client::new(), base: format!("http://{}", snapshot.address), _root: root, destination }
    }
    fn request(&self, method: Method, route: &str) -> reqwest::RequestBuilder { self.client.request(method, format!("{}{route}", self.base)).header("Origin", &self.base) }
    async fn request_transfer(&self, names: &[(&str,u64)]) -> Value {
        let session = self.manager.active().await.expect("session");
        let token = session.inner.lock().await.join_token.clone();
        let response = self.request(Method::POST,"/api/connect").json(&json!({"token":token,"request_id":uuid::Uuid::new_v4().to_string(),"device":"test browser","files":names.iter().map(|(name,size)| json!({"name":name,"size":size})).collect::<Vec<_>>() })).send().await.expect("connect request");
        assert_eq!(response.status(),StatusCode::OK);
        response.json().await.expect("connection response")
    }
    async fn status(&self, attempt: &str) -> Value { self.request(Method::GET,"/api/status").bearer_auth(attempt).send().await.expect("status").json().await.expect("status JSON") }
    async fn accept(&self, attempt: &str) -> Value { let id=self.manager.active().await.expect("session").id.clone(); self.manager.decide(&id,true).await.expect("approve"); self.status(attempt).await }
    async fn chunk(&self, grant: &str, id: &str, offset: u64, data: &[u8]) -> Response {
        self.request(Method::PUT,&format!("/api/files/{id}/chunks")).bearer_auth(grant).header("content-type","application/octet-stream").header("x-qrdrop-offset",offset).header("x-qrdrop-length",data.len()).header("x-qrdrop-sha256",hex::encode(Sha256::digest(data))).body(data.to_vec()).send().await.expect("chunk request")
    }
    async fn finish(&self, grant: &str, attempt: &str, id: &str, data: &[u8]) {
        let response=self.request(Method::POST,&format!("/api/files/{id}/finish")).bearer_auth(grant).json(&json!({"sha256":hex::encode(Sha256::digest(data))})).send().await.expect("finish");
        assert_eq!(response.status(),StatusCode::ACCEPTED);
        for _ in 0..100 {
            let status=self.status(attempt).await;
            if status["files"].as_array().expect("files").iter().any(|file| file["id"]==id && file["status"]=="complete") { return; }
            assert_ne!(status["state"],"FAILED", "{status}");
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
        panic!("Verification did not finish");
    }
    async fn stop(&self) { let session=self.manager.active().await.expect("session");session.terminate(SessionState::Cancelled,None).await;session.stop_server.cancel();let _permit=session.operation.acquire().await.expect("disk gate");session.cleanup().await.expect("cleanup"); }
}
#[tokio::test]
async fn real_http_requires_approval_retries_no_overwrite_verifies_and_invalidates() {
    let h=Harness::new().await;
    std::fs::write(h.destination.join("photo.DNG"),b"existing").expect("existing file");
    let data=b"opaque binary\0\xffEXIF ICC raw bytes";
    let connection=h.request_transfer(&[("photo.DNG",data.len() as u64),("empty.zip",0)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let pending=h.status(attempt).await;
    assert!(pending["grant"].is_null());
    let id=pending["files"][0]["id"].as_str().expect("file id");
    assert_eq!(h.chunk(attempt,id,0,data).await.status(),StatusCode::FORBIDDEN);
    let approved=h.accept(attempt).await;
    let grant=approved["grant"].as_str().expect("grant");
    let first=h.chunk(grant,id,0,data).await;
    assert_eq!(first.status(),StatusCode::OK);
    assert_eq!(h.chunk(grant,id,0,data).await.status(),StatusCode::OK); // Lost ACK replay, not append.
    h.finish(grant,attempt,id,data).await;
    assert_eq!(std::fs::read(h.destination.join("photo.DNG")).expect("original"),b"existing");
    assert_eq!(std::fs::read(h.destination.join("photo (1).DNG")).expect("received"),data);
    let empty_id=approved["files"][1]["id"].as_str().expect("empty id");
    h.finish(grant,attempt,empty_id,b"").await;
    assert_eq!(h.request(Method::POST,"/api/complete").bearer_auth(grant).json(&json!({})).send().await.expect("complete").status(),StatusCode::OK);
    assert_eq!(h.chunk(grant,id,0,data).await.status(),StatusCode::FORBIDDEN);
    assert_eq!(h.status(attempt).await["state"],"COMPLETED");
    h.stop().await;
}
#[tokio::test]
async fn rejects_bad_origin_traversal_mutated_manifest_and_rejected_sessions() {
    let h=Harness::new().await;
    let session=h.manager.active().await.expect("session");
    let token=session.inner.lock().await.join_token.clone();
    let request=json!({"token":token,"request_id":uuid::Uuid::new_v4().to_string(),"device":"browser","files":[{"name":"../escape","size":1}]});
    assert_eq!(h.request(Method::POST,"/api/connect").json(&request).send().await.expect("bad path").status(),StatusCode::BAD_REQUEST);
    assert_eq!(h.client.post(format!("{}/api/connect",h.base)).header("Origin","https://attacker.invalid").json(&request).send().await.expect("origin").status(),StatusCode::FORBIDDEN);
    assert_eq!(h.request(Method::POST,"/api/connect").header("Origin","https://attacker.invalid").json(&request).send().await.expect("duplicate origin").status(),StatusCode::FORBIDDEN);
    let connection=h.request_transfer(&[("safe.pdf",1)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let changed=json!({"token":token,"request_id":uuid::Uuid::new_v4().to_string(),"device":"browser","files":[{"name":"other.pdf","size":1}]});
    assert_eq!(h.request(Method::POST,"/api/connect").json(&changed).send().await.expect("changed manifest").status(),StatusCode::FORBIDDEN);
    h.manager.decide(&session.id,false).await.expect("reject");
    assert_eq!(h.status(attempt).await["state"],"REJECTED");
    assert_eq!(h.request(Method::POST,"/api/connect").json(&changed).send().await.expect("old token").status(),StatusCode::FORBIDDEN);
    assert!(h.manager.decide(&session.id,true).await.is_err());
    h.stop().await;
}
#[tokio::test]
async fn mismatch_never_publishes() {
    let h=Harness::new().await;
    let connection=h.request_transfer(&[("bad.mov",3)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let state=h.accept(attempt).await;
    let id=state["files"][0]["id"].as_str().expect("id");
    let grant=state["grant"].as_str().expect("grant");
    assert_eq!(h.chunk(grant,id,0,b"abc").await.status(),StatusCode::OK);
    let wrong_digest = hex::encode(Sha256::digest(b"xyz"));
    assert_eq!(h.request(Method::POST,&format!("/api/files/{id}/finish")).bearer_auth(grant).json(&json!({"sha256":wrong_digest})).send().await.expect("finish").status(),StatusCode::ACCEPTED);
    for _ in 0..100 { if h.status(attempt).await["state"]=="FAILED" {break;} tokio::time::sleep(Duration::from_millis(20)).await; }
    assert_eq!(h.status(attempt).await["state"],"FAILED");
    assert!(!h.destination.join("bad.mov").exists());
    h.stop().await;
}
#[test]
fn names_and_auth_are_safe() {
    for bad in ["../file","a/b","a\\b","\0","..",""] { assert!(files::safe_name(bad).is_err()); }
    assert_eq!(files::safe_name("CON.jpg").expect("reserved"),"_CON.jpg");
    assert_eq!(files::safe_name("image.DNG").expect("extension"),"image.DNG");
    assert!(auth::matches("abc","abc"));assert!(!auth::matches("abc","abd"));
    assert_eq!(auth::random_token().expect("CSPRNG").len(),64);
    assert_ne!(auth::random_token().expect("CSPRNG"),auth::random_token().expect("CSPRNG"));
}
#[tokio::test]
async fn expired_upload_grant_is_denied_before_disk_write() {
    let h=Harness::new().await;
    let connection=h.request_transfer(&[("expired.zip",1)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let state=h.accept(attempt).await;
    let session=h.manager.active().await.expect("session");
    session.inner.lock().await.last_progress=std::time::Instant::now()-Duration::from_secs(START_SECONDS+1);
    assert_eq!(h.chunk(state["grant"].as_str().expect("grant"),state["files"][0]["id"].as_str().expect("id"),0,b"a").await.status(),StatusCode::FORBIDDEN);
    assert!(!h.destination.join("expired.zip").exists());
    h.stop().await;
}
#[tokio::test]
async fn cancel_preserves_completed_file_and_removes_incomplete_file() {
    let h=Harness::new().await;
    let connection=h.request_transfer(&[("good.pdf",3),("unfinished.zip",6)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let state=h.accept(attempt).await;
    let grant=state["grant"].as_str().expect("grant");
    let first=state["files"][0]["id"].as_str().expect("first");
    let second=state["files"][1]["id"].as_str().expect("second");
    assert_eq!(h.chunk(grant,first,0,b"abc").await.status(),StatusCode::OK);
    h.finish(grant,attempt,first,b"abc").await;
    assert_eq!(h.chunk(grant,second,0,b"abc").await.status(),StatusCode::OK);
    h.manager.cancel().await.expect("cancel");
    assert_eq!(h.status(attempt).await["state"],"PARTIALLY_COMPLETED");
    h.stop().await;
    assert_eq!(std::fs::read(h.destination.join("good.pdf")).expect("retained file"),b"abc");
    assert!(!h.destination.join("unfinished.zip").exists());
}
#[cfg(unix)]
#[test]
fn staging_symlink_cannot_escape_destination() {
    let root=tempfile::tempdir().expect("root");
    let destination=root.path().join("destination");
    let outside=root.path().join("outside");
    let state=root.path().join("state");
    for dir in [&destination,&outside,&state] { std::fs::create_dir(dir).expect("directory"); }
    std::os::unix::fs::symlink(&outside,destination.join(".qrdrop-partials")).expect("symlink");
    assert!(files::create(&destination,&state,&uuid::Uuid::new_v4().to_string()).is_err());
    assert_eq!(std::fs::read_dir(outside).expect("outside directory").count(),0);
}

#[tokio::test]
async fn large_chunks_roll_back_bad_digest_and_reject_wrong_offsets() {
    let h=Harness::new().await;
    let data=vec![0xa5; qrdrop_lib::config::CHUNK_BYTES as usize+17];
    let first=&data[..qrdrop_lib::config::CHUNK_BYTES as usize];
    let connection=h.request_transfer(&[("large.bin",data.len() as u64)]).await;
    let attempt=connection["attempt_token"].as_str().expect("attempt");
    let approved=h.accept(attempt).await;
    let grant=approved["grant"].as_str().expect("grant");
    let id=approved["files"][0]["id"].as_str().expect("id");
    let wrong=h.request(Method::PUT,&format!("/api/files/{id}/chunks")).bearer_auth(grant)
        .header("content-type","application/octet-stream").header("x-qrdrop-offset",0)
        .header("x-qrdrop-length",first.len()).header("x-qrdrop-sha256","0".repeat(64))
        .body(first.to_vec()).send().await.expect("bad digest request");
    assert_eq!(wrong.status(),StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(h.status(attempt).await["files"][0]["received"],0);
    let part=h.destination.join(".qrdrop-partials").join(h.manager.active().await.expect("session").id.clone()).join(format!("{id}.part"));
    assert_eq!(std::fs::metadata(part).expect("staging file").len(),0);
    assert_eq!(h.chunk(grant,id,0,first).await.status(),StatusCode::OK);
    assert_eq!(h.chunk(grant,id,0,first).await.status(),StatusCode::OK);
    assert_eq!(h.chunk(grant,id,1,b"x").await.status(),StatusCode::CONFLICT);
    assert!(!h.destination.join("large.bin").exists());
    assert_eq!(h.chunk(grant,id,first.len() as u64,&data[first.len()..]).await.status(),StatusCode::OK);
    h.finish(grant,attempt,id,&data).await;
    assert_eq!(std::fs::read(h.destination.join("large.bin")).expect("received file"),data);
    h.stop().await;
}

#[tokio::test(flavor="multi_thread",worker_threads=2)]
async fn concurrent_accept_and_reject_have_exactly_one_winner() {
    let h=Harness::new().await;
    h.request_transfer(&[("decision.bin",1)]).await;
    let session=h.manager.active().await.expect("session");
    let barrier=Arc::new(tokio::sync::Barrier::new(3));
    let mut tasks=Vec::new();
    for accept in [false,true] {
        let manager=h.manager.clone();
        let id=session.id.clone();
        let barrier=barrier.clone();
        tasks.push(tokio::spawn(async move { barrier.wait().await; manager.decide(&id,accept).await }));
    }
    barrier.wait().await;
    let mut winners=0;
    for task in tasks { if task.await.expect("decision task").is_ok() { winners+=1; } }
    assert_eq!(winners,1);
    let inner=session.inner.lock().await;
    assert!(matches!(inner.state,SessionState::Approved|SessionState::Rejected));
    assert_eq!(inner.grant.is_some(),inner.state==SessionState::Approved);
    drop(inner);
    h.stop().await;
}
