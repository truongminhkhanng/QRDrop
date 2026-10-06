use crate::errors::{AppError, Result};
use sha2::{Digest, Sha256};
use tokio::io::AsyncReadExt;
use tokio_util::sync::CancellationToken;

pub async fn disk_digest(file: &mut tokio::fs::File, cancel: &CancellationToken, progress: &tokio::sync::Mutex<crate::session::SessionInner>) -> Result<String> {
    use tokio::io::AsyncSeekExt;
    file.seek(std::io::SeekFrom::Start(0)).await?;
    let mut hash = Sha256::new();
    let mut buffer = vec![0u8; 256 * 1024];
    loop {
        let n = tokio::select! {
            _ = cancel.cancelled() => return Err(AppError::conflict("Phiên đã bị hủy.")),
            result = file.read(&mut buffer) => result?,
        };
        if n == 0 { break; }
        hash.update(&buffer[..n]);
        progress.lock().await.last_progress = std::time::Instant::now();
    }
    Ok(hex::encode(hash.finalize()))
}
