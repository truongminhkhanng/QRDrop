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
async fn decide_transfer(manager: State<'_, Managed>, session_id: String, accept: bool) -> Result<(), String> { manager.decide(&session_id, accept).await.map_err(|e| e.to_string()) }
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
    let chosen = tauri::async_runtime::spawn_blocking(move || app.dialog().file().blocking_pick_folder()).await.map_err(|e| e.to_string())?;
    if let Some(chosen) = chosen {
        let path = chosen.into_path().map_err(|e| e.to_string())?;
        manager.set_destination(path.clone()).await.map_err(|e| e.to_string())?;
        Ok(Some(path.to_string_lossy().into_owned()))
    } else { Ok(None) }
}
#[tauri::command]
async fn open_destination(app: tauri::AppHandle, manager: State<'_, Managed>) -> Result<(), String> {
    let path = match manager.current.lock().await.as_ref() { Some(session) => session.storage.root.clone(), None => manager.settings.lock().await.destination.clone() };
    std::fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    app.opener().open_path(path.to_string_lossy().into_owned(), None::<&str>).map_err(|e| e.to_string())
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
        .invoke_handler(tauri::generate_handler![create_session, session_snapshot, cancel_session, decide_transfer, network_interfaces, get_settings, set_destination, recent_transfers, choose_destination, open_destination])
        .build(tauri::generate_context!());
    match result {
        Ok(app) => app.run(|handle, event| {
            if let tauri::RunEvent::Exit = event {
                let manager = handle.state::<Managed>().inner().clone();
                tauri::async_runtime::block_on(async {
                    if let Ok(session) = manager.active().await {
                        session.terminate(crate::session::SessionState::Cancelled, None).await;
                        session.stop_server.cancel();
                        if let Ok(_permit) = session.operation.acquire().await {
                            if let Err(error) = session.cleanup().await { eprintln!("Partial cleanup failed: {error}"); }
                        }
                    }
                });
            }
        }),
        Err(error) => { eprintln!("QRDrop could not start: {error}"); std::process::exit(1); }
    }
}
