//! Revocable browser credentials. Only their hashes are persisted on the PC;
//! pairing credentials are provisioned and used through the HTTPS transport.
use crate::{auth, errors::{AppError, Result}, session::unix_now};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;

#[derive(Clone, Serialize, Deserialize)]
pub struct TrustedDevice {
    pub id: String, pub name: String, pub created_at: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    token_hash: Option<String>,
}
impl TrustedDevice {
    pub fn public(&self) -> Self { Self { token_hash: None, ..self.clone() } }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct TrustStore { pub receiver_id: String, pub receiver_secret: String, devices: Vec<TrustedDevice> }
impl TrustStore {
    pub fn load(root: &Path) -> Result<Self> {
        match std::fs::read(root.join("trusted-devices.json")) {
            Ok(bytes) => {
                let store: Self = serde_json::from_slice(&bytes).map_err(|_| AppError::invalid("Không đọc được danh sách thiết bị tin cậy."))?;
                if uuid::Uuid::parse_str(&store.receiver_id).is_err() || !auth::valid_digest(&store.receiver_secret) || store.devices.len() > 100 || store.devices.iter().any(|device| uuid::Uuid::parse_str(&device.id).is_err() || device.name.len() > 160 || !device.token_hash.as_ref().is_some_and(|hash| auth::valid_digest(hash))) {
                    return Err(AppError::invalid("Danh sách thiết bị tin cậy không hợp lệ."));
                }
                Ok(store)
            },
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                let store = Self { receiver_id: uuid::Uuid::new_v4().to_string(), receiver_secret: auth::random_token()?, devices: Vec::new() };
                store.save(root)?; Ok(store)
            },
            Err(error) => Err(error.into()),
        }
    }
    fn save(&self, root: &Path) -> Result<()> {
        let bytes = serde_json::to_vec(self).map_err(|_| AppError::invalid("Không lưu được danh sách thiết bị tin cậy."))?;
        let path = root.join("trusted-devices.new.json");
        use std::io::Write;
        let mut options = std::fs::OpenOptions::new(); options.write(true).create(true).truncate(true);
        #[cfg(unix)] { use std::os::unix::fs::OpenOptionsExt; options.mode(0o600); }
        let mut file = options.open(&path)?; file.write_all(&bytes)?; file.sync_all()?; drop(file);
        std::fs::rename(path, root.join("trusted-devices.json"))?;
        Ok(())
    }
    pub fn list(&self) -> Vec<TrustedDevice> { self.devices.iter().map(TrustedDevice::public).collect() }
    pub fn find(&self, token: &str) -> Option<TrustedDevice> {
        if token.len() != 64 || !auth::valid_digest(token) { return None; }
        let hash = hex::encode(Sha256::digest(token.as_bytes()));
        self.devices.iter().find(|device| device.token_hash.as_ref().is_some_and(|expected| auth::matches(expected, &hash))).map(TrustedDevice::public)
    }
    pub fn add(&mut self, root: &Path, name: &str) -> Result<(TrustedDevice, String)> {
        if self.devices.len() >= 100 { return Err(AppError::conflict("Danh sách đã có 100 thiết bị. Xóa thiết bị cũ trước khi thêm.")); }
        let token = auth::random_token()?;
        let device = TrustedDevice { id: uuid::Uuid::new_v4().to_string(), name: name.to_owned(), created_at: unix_now(), token_hash: Some(hex::encode(Sha256::digest(token.as_bytes()))) };
        let mut updated = self.clone(); updated.devices.push(device.clone()); updated.save(root)?; *self = updated;
        Ok((device.public(), token))
    }
    pub fn remove(&mut self, root: &Path, id: &str) -> Result<()> {
        let mut updated = self.clone(); updated.devices.retain(|device| device.id != id); updated.save(root)?; *self = updated; Ok(())
    }
}
