use crate::errors::{AppError, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const CHUNK_BYTES: u64 = 8 * 1024 * 1024;
pub const MAX_FILES: usize = 1000;
pub const MANIFEST_BYTES: usize = 1024 * 1024;
pub const JOIN_SECONDS: u64 = 600;
pub const START_SECONDS: u64 = 120;
pub const IDLE_SECONDS: u64 = 300;
pub const MAX_SESSION_SECONDS: u64 = 24 * 60 * 60;

#[derive(Clone, Serialize, Deserialize)]
pub struct Settings { pub destination: PathBuf }
pub fn default_destination() -> Result<PathBuf> {
    dirs::download_dir().or_else(|| dirs::home_dir().map(|p| p.join("Downloads")))
        .map(|p| p.join("QRDrop")).ok_or_else(|| AppError::invalid("Không xác định được thư mục Downloads. Hãy chọn thư mục nhận."))
}
pub fn load(root: &Path) -> Result<Settings> {
    let path = root.join("settings.json");
    match std::fs::read(&path) {
        Ok(bytes) => serde_json::from_slice(&bytes).map_err(|_| AppError::invalid("Không đọc được cài đặt đã lưu. Kiểm tra tệp settings.json trong thư mục dữ liệu của QRDrop.")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Settings { destination: default_destination()? }),
        Err(e) => Err(e.into()),
    }
}
pub fn save(root: &Path, settings: &Settings) -> Result<()> {
    let temp = root.join("settings.new.json");
    let bytes = serde_json::to_vec_pretty(settings).map_err(|_| AppError::invalid("Không thể lưu cài đặt. Hãy thử lại."))?;
    std::fs::write(&temp, bytes)?;
    std::fs::rename(temp, root.join("settings.json"))?;
    Ok(())
}
