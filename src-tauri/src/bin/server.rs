//! Headless harness using the real receiver. Credentials are deliberately not printed.
use qrdrop_lib::{config::Settings, session::Manager};
use std::{path::PathBuf, sync::Arc};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    let destination = args.get(1).map(PathBuf::from).ok_or("Usage: qrdrop-server DESTINATION STATE_DIRECTORY")?;
    let state_dir = args.get(2).map(PathBuf::from).ok_or("Provide a state directory")?;
    let manager = Arc::new(Manager::new(state_dir)?);
    *manager.settings.lock().await = Settings { destination };
    let snapshot = manager.start(None).await?;
    eprintln!("Receiver listening at {}. Use the desktop app to approve transfers.", snapshot.address);
    tokio::signal::ctrl_c().await?;
    manager.cancel().await?;
    let session = manager.active().await?;
    session.stop_server.cancel();
    let _permit = session.operation.acquire().await?;
    session.cleanup().await?;
    Ok(())
}
