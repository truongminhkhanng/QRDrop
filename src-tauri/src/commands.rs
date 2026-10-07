use crate::{config::Settings, network::{self, NetworkInterface}, protocol::RecentTransfer, session::{DesktopSnapshot, Manager}};
use std::{net::Ipv4Addr, path::PathBuf, sync::Arc};
use tauri::{Emitter, Manager as TauriManager, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

type Managed = Arc<Manager>;
#[tauri::command]
async fn create_session(manager: State<'_, Managed>, ip: Option<Ipv4Addr>) -> Result<DesktopSnapshot, String> { manager.inner().start(ip).await.map_err(|e| e.to_string()) }
#[tauri::command]
async fn session_snapshot(manager: State<'_, Managed>) -> Result<Option<DesktopSnapshot>, String> {
    let current = manager.current.lock().await.clone();
    Ok(match current { Some(session) => Some(session.snapshot().await), None => None })
}
#[tauri::command]
async fn cancel_session(manager: State<'_, Managed>) -> Result<(), String> { manager.cancel().await.map_err(|e| e.to_string()) }
#[tauri::command]
async fn stop_receiving(manager: State<'_, Managed>) -> Result<(), String> { manager.stop_receiving().await.map_err(|e| e.to_string()) }
#[tauri::command]
async fn decide_transfer(manager: State<'_, Managed>, session_id: String, accept: bool, remember: Option<bool>) -> Result<(), String> { manager.decide_with_trust(&session_id, accept, remember.unwrap_or(false)).await.map_err(|e| e.to_string()) }
#[tauri::command]
async fn trusted_devices(manager: State<'_, Managed>) -> Result<Vec<crate::trust::TrustedDevice>, String> { Ok(manager.trusted.lock().await.list()) }
#[tauri::command]
async fn forget_trusted_device(manager: State<'_, Managed>, device_id: String) -> Result<(), String> { manager.forget_trusted_device(&device_id).await.map_err(|e| e.to_string()) }
#[tauri::command]
fn network_interfaces() -> Result<Vec<NetworkInterface>, String> { network::interfaces().map_err(|e| e.to_string()) }
#[tauri::command]
async fn get_settings(manager: State<'_, Managed>) -> Result<Settings, String> { Ok(manager.settings.lock().await.clone()) }
#[tauri::command]
async fn set_destination(manager: State<'_, Managed>, destination: PathBuf) -> Result<(), String> { manager.set_destination(destination).await.map_err(|e| e.to_string()) }
#[tauri::command]
async fn recent_transfers(manager: State<'_, Managed>) -> Result<Vec<RecentTransfer>, String> { Ok(manager.recent.lock().await.clone()) }
#[tauri::command]
async fn choose_destination(app: tauri::AppHandle, manager: State<'_, Managed>) -> Result<Option<String>, String> {
    let chosen = tauri::async_runtime::spawn_blocking(move || app.dialog().file().blocking_pick_folder()).await.map_err(|_| "Không mở được cửa sổ chọn thư mục. Hãy thử lại.".to_owned())?;
    if let Some(chosen) = chosen {
        let path = chosen.into_path().map_err(|_| "Không sử dụng được thư mục đã chọn. Hãy chọn thư mục khác.".to_owned())?;
        manager.set_destination(path.clone()).await.map_err(|e| e.to_string())?;
        Ok(Some(path.to_string_lossy().into_owned()))
    } else { Ok(None) }
}
#[tauri::command]
async fn open_destination(app: tauri::AppHandle, manager: State<'_, Managed>) -> Result<(), String> {
    let path = match manager.current.lock().await.as_ref() { Some(session) => session.storage.root.clone(), None => manager.settings.lock().await.destination.clone() };
    std::fs::create_dir_all(&path).map_err(|e| crate::errors::AppError::io(e).to_string())?;
    app.opener().open_path(path.to_string_lossy().into_owned(), None::<&str>).map_err(|_| "Không mở được thư mục nhận. Hãy mở thư mục bằng trình quản lý tệp trên máy tính.".to_owned())
}

pub fn run() {
    let result = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let manager = Arc::new(Manager::new(app.path().app_data_dir()?)?);
            app.manage(manager.clone());
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                loop {
                    tokio::time::sleep(std::time::Duration::from_millis(300)).await;
                    if let Ok(session) = manager.active().await {
                        if let Err(error) = handle.emit("qrdrop:session", session.snapshot().await) { eprintln!("Unable to deliver desktop state: {error}"); }
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![create_session, session_snapshot, cancel_session, stop_receiving, decide_transfer, trusted_devices, forget_trusted_device, network_interfaces, get_settings, set_destination, recent_transfers, choose_destination, open_destination])
        .build(tauri::generate_context!());
    match result {
        Ok(app) => app.run(|handle, event| {
            if let tauri::RunEvent::Exit = event {
                let manager = handle.state::<Managed>().inner().clone();
                tauri::async_runtime::block_on(async {
                    if let Err(error) = manager.stop_receiving().await { eprintln!("Receiver cleanup failed: {error}"); }
                });
            }
        }),
        Err(error) => { eprintln!("QRDrop could not start: {error}"); std::process::exit(1); }
    }
}
