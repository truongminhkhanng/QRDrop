use crate::errors::{AppError, Result};
use cap_std::{ambient_authority, fs::{Dir, OpenOptions}};
use serde::{Deserialize, Serialize};
use std::{path::{Path, PathBuf}, sync::Arc};

pub struct Storage { pub destination: Arc<Dir>, pub staging: Arc<Dir>, pub root: PathBuf, pub relative: String }
#[derive(Serialize, Deserialize)]
struct Journal { version: u8, destination: PathBuf, session_id: String }

pub fn safe_name(input: &str) -> Result<String> {
    if input.is_empty() || input.len() > 240 || input.contains(['/', '\\', '\0']) || input == "." || input == ".." {
        return Err(AppError::invalid("Tên tệp không hợp lệ hoặc quá dài."));
    }
    let mut name: String = input.chars().map(|c| {
        if c.is_control() || "<>:\"|?*".contains(c) || ('\u{202a}'..='\u{202e}').contains(&c) || ('\u{2066}'..='\u{2069}').contains(&c) { '_' } else { c }
    }).collect();
    name = name.trim_matches([' ', '.']).to_owned();
    if name.is_empty() { return Err(AppError::invalid("Tên tệp không hợp lệ.")); }
    let stem = name.split('.').next().unwrap_or_default().to_uppercase();
    if ["CON", "PRN", "AUX", "NUL"].contains(&stem.as_str()) || (stem.len() == 4 && (stem.starts_with("COM") || stem.starts_with("LPT")) && matches!(stem.as_bytes()[3], b'1'..=b'9')) { name.insert(0, '_'); }
    Ok(name)
}
pub fn create(root: &Path, state_dir: &Path, session_id: &str) -> Result<Storage> {
    std::fs::create_dir_all(root)?;
    let root = std::fs::canonicalize(root)?;
    let destination = Arc::new(Dir::open_ambient_dir(&root, ambient_authority())?);
    // Directory capabilities prevent paths and symlinks escaping the chosen root.
    destination.create_dir_all(".qrdrop-partials")?;
    let relative = format!(".qrdrop-partials/{session_id}");
    destination.create_dir(&relative)?;
    let staging = Arc::new(destination.open_dir(&relative)?);
    #[cfg(unix)] {
        use std::os::unix::fs::PermissionsExt;
        staging.set_permissions(".", cap_std::fs::Permissions::from_std(std::fs::Permissions::from_mode(0o700)))?;
    }
    let journal = Journal { version: 1, destination: root.clone(), session_id: session_id.to_owned() };
    let bytes = serde_json::to_vec(&journal).map_err(|_| AppError::invalid("Không thể tạo nhật ký tệp tạm."))?;
    std::fs::write(state_dir.join("partial-journal.json"), bytes)?;
    let storage = Storage { destination, staging, root, relative };
    // Fail before approval/data transfer if this filesystem cannot publish safely.
    let probe = uuid::Uuid::new_v4().to_string();
    let linked = uuid::Uuid::new_v4().to_string();
    let check: std::io::Result<()> = (|| {
        drop(storage.staging.open_with(format!("{probe}.part"), OpenOptions::new().write(true).create_new(true))?);
        storage.staging.hard_link(format!("{probe}.part"), &storage.staging, format!("{linked}.part"))?;
        storage.staging.remove_file(format!("{linked}.part"))?;
        storage.staging.remove_file(format!("{probe}.part"))?;
        Ok(())
    })();
    if let Err(error) = check {
        if let Err(cleanup_error) = cleanup(&storage, &[probe, linked], state_dir) {
            return Err(AppError::invalid(format!("Không thể lưu an toàn vào thư mục đã chọn: {error}. Không dọn được staging: {cleanup_error}")));
        }
        return Err(AppError::invalid(format!("Thư mục nhận không hỗ trợ lưu an toàn hoặc không ghi được ({error}). Hãy chọn thư mục trên ổ đĩa khác.")));
    }
    Ok(storage)
}
pub fn open_part(storage: &Storage, id: &str) -> Result<tokio::fs::File> {
    let file = storage.staging.open_with(format!("{id}.part"), OpenOptions::new().read(true).write(true).create_new(true))?;
    Ok(tokio::fs::File::from_std(file.into_std()))
}
pub fn publish(storage: &Storage, id: &str, name: &str) -> Result<(String, Option<String>)> {
    let path = Path::new(name);
    let ext = path.extension().and_then(|s| s.to_str());
    let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or(name);
    for suffix in 0..10_000 {
        let candidate = if suffix == 0 { name.to_owned() } else if let Some(ext) = ext { format!("{stem} ({suffix}).{ext}") } else { format!("{name} ({suffix})") };
        // Hard-link creates the final directory entry atomically, with no replacement.
        match storage.staging.hard_link(format!("{id}.part"), &storage.destination, &candidate) {
            Ok(()) => {
                // Publication has succeeded: a cleanup error must not cause duplicate publication.
                let warning = storage.staging.remove_file(format!("{id}.part")).err().map(|e| format!("Tệp đã lưu, nhưng chưa dọn được liên kết tạm: {e}"));
                return Ok((candidate, warning));
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(e.into()),
        }
    }
    Err(AppError::conflict("Có quá nhiều tệp trùng tên."))
}
pub fn cleanup(storage: &Storage, ids: &[String], state_dir: &Path) -> Result<()> {
    for id in ids {
        match storage.staging.remove_file(format!("{id}.part")) { Ok(()) => {}, Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}, Err(e) => return Err(e.into()) }
    }
    match storage.destination.remove_dir(&storage.relative) { Ok(()) => {}, Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}, Err(e) => return Err(e.into()) }
    // An old session's cleanup must never remove a newer session's journal.
    let journal_path = state_dir.join("partial-journal.json");
    match std::fs::read(&journal_path) {
        Ok(bytes) => {
            let journal: Journal = serde_json::from_slice(&bytes).map_err(|_| AppError::invalid("Nhật ký tệp tạm không hợp lệ."))?;
            if storage.relative == format!(".qrdrop-partials/{}", journal.session_id) && storage.root == journal.destination { remove_journal(state_dir)?; }
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {},
        Err(e) => return Err(e.into()),
    }
    Ok(())
}
fn remove_journal(state_dir: &Path) -> Result<()> {
    match std::fs::remove_file(state_dir.join("partial-journal.json")) { Ok(()) => Ok(()), Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()), Err(e) => Err(e.into()) }
}
pub fn recover(state_dir: &Path) -> Result<()> {
    let bytes = match std::fs::read(state_dir.join("partial-journal.json")) { Ok(b) => b, Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(()), Err(e) => return Err(e.into()) };
    let journal: Journal = serde_json::from_slice(&bytes).map_err(|_| AppError::invalid("Nhật ký tệp tạm không hợp lệ; cần kiểm tra thủ công."))?;
    if journal.version != 1 || uuid::Uuid::parse_str(&journal.session_id).is_err() { return Err(AppError::invalid("Nhật ký tệp tạm không hợp lệ.")); }
    let dir = Dir::open_ambient_dir(&journal.destination, ambient_authority())?;
    let relative = format!(".qrdrop-partials/{}", journal.session_id);
    let staging = match dir.open_dir(&relative) { Ok(d) => d, Err(e) if e.kind() == std::io::ErrorKind::NotFound => return remove_journal(state_dir), Err(e) => return Err(e.into()) };
    for entry in staging.entries()? {
        let entry = entry?;
        let name = entry.file_name();
        let text = name.to_string_lossy();
        if !text.ends_with(".part") || uuid::Uuid::parse_str(text.trim_end_matches(".part")).is_err() || !entry.file_type()?.is_file() {
            return Err(AppError::invalid("Có tệp không nhận diện được trong staging; cần kiểm tra thủ công."));
        }
        staging.remove_file(name)?;
    }
    dir.remove_dir(relative)?;
    remove_journal(state_dir)
}
