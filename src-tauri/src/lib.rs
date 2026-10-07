pub mod auth;
pub mod config;
pub mod errors;
pub mod files;
pub mod hash;
pub mod network;
pub mod protocol;
pub mod relay;
pub mod server;
pub mod session;
pub mod transfer;
pub mod trust;
#[cfg(feature = "desktop")]
pub mod commands;

#[cfg(feature = "desktop")]
pub fn run() {
    commands::run();
}
