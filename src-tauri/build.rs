fn main() {
    println!("cargo:rerun-if-changed=../mobile-dist");
    #[cfg(feature = "desktop")]
    tauri_build::build();
}
