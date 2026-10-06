use serde::{Deserialize, Serialize};

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestFile { pub name: String, pub size: u64 }
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConnectRequest { pub token: String, pub request_id: String, pub device: String, pub files: Vec<ManifestFile> }
#[derive(Serialize)]
pub struct ConnectReply { pub attempt_token: String, pub session_id: String, pub chunk_bytes: u64 }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FinishRequest { pub sha256: String }
#[derive(Serialize)]
pub struct ChunkReply { pub offset: u64 }
#[derive(Serialize)]
pub struct MobileStatus { pub state: crate::session::SessionState, pub grant: Option<String>, pub files: Vec<FileView>, pub error: Option<String> }
#[derive(Clone, Serialize)]
pub struct FileView {
    pub id: String, pub name: String, pub saved_name: Option<String>, pub size: u64,
    pub received: u64, pub status: FileState, pub sha256: Option<String>,
}
#[derive(Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum FileState { Waiting, Receiving, Verifying, Complete, Failed, Cancelled }
#[derive(Clone, Serialize, Deserialize)]
pub struct RecentTransfer { pub name: String, pub size: u64, pub sha256: String, pub destination: String, pub completed_at: u64 }
