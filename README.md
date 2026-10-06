# QRDrop

Nhận tệp từ iPhone/Android về máy tính qua mạng nội bộ: quét QR → chọn tệp → cho phép trên máy tính → gửi → kiểm tra SHA-256.

**Trạng thái: bản triển khai ban đầu cần kiểm thử native.** TypeScript/build frontend và self-test local đã chạy. Rust compile, bộ cài và luồng điện thoại thật chưa được xác minh trong môi trường khởi tạo do mạng tải crates bị chặn. Không coi đây là bản release đã nghiệm thu.

## Các điều cần biết
- Điện thoại không cần cài app. File phải có sẵn cục bộ nếu không có Internet.
- HTTP trên LAN không mã hóa. Chỉ dùng mạng tin cậy.
- Giữ browser mở và màn hình hoạt động khi gửi.
- Giữ nguyên bytes của file browser cung cấp; không hứa lấy tài nguyên Photos gốc.
- File được staging và kiểm tra trước khi tạo tên cuối. Không overwrite.
- Retry trong phiên đang chạy; không resume sau reload hoặc app restart.

## Tải bộ cài qua GitHub
1. Giải nén source và đưa nội dung project lên repository của bạn, bao gồm `.github/workflows/build.yml`.
2. Mở **Actions → Build QRDrop installers → Run workflow**. Workflow cũng chạy khi push main/master.
3. Khi cả ba job thành công, tải artifact tương ứng:
   - `qrdrop-windows-x64`: NSIS setup.exe, có WebView2 offline installer.
   - `qrdrop-macos-arm64`: DMG cho Apple Silicon.
   - `qrdrop-linux-x64`: AppImage/deb, baseline Ubuntu 24.04 build host.
4. Artifact riêng `qrdrop-rust-lock-...` có `Cargo.lock` được CI resolve. Commit một bản lockfile sau run đầu thành công để pin Rust dependencies; các run sau dùng lockfile đã commit. Không chỉnh checksum bằng tay.
5. Tag `v...` tạo **draft** GitHub Release; không tự publish public.

GitHub dùng cho build/phân phối, không trung chuyển file. Người dùng bộ cài không cần Node/Rust/npm.

Windows installer hiện chưa ký publisher certificate. macOS build test ad-hoc signed; muốn phát hành public cần Developer ID + notarization. Không tắt bảo vệ hệ thống toàn cục để xử lý lỗi cài đặt. Linux compatibility phải kiểm thử theo distro; không hứa mọi Linux.

## Chạy từ source
Cần Node >=24, Rust stable và native prerequisites Tauri theo OS. Dependencies npm/Cargo là local trong project; các SDK/compiler/GTK/WebKit hệ thống là prerequisites desktop build, không phải global code-index service.

```bash
npm ci
npm run build
npm run tauri -- dev
```

Dev mở desktop assets đã build để mobile/server cùng có assets offline. Sau thay đổi UI, build lại. Không dùng Vite page một mình để giả lập quyền nhận file desktop.

Build trực tiếp trên native host:

```bash
# Windows
npm run tauri -- build --bundles nsis
# macOS Apple Silicon
npm run tauri -- build --target aarch64-apple-darwin --bundles dmg
# Linux
npm run tauri -- build --bundles appimage,deb
```

## Kiểm tra
```bash
npm run build
npm run test:hash
npm run test:codeintel
npm run test:mobile
cargo test --manifest-path src-tauri/Cargo.toml --no-default-features
cargo check --manifest-path src-tauri/Cargo.toml
```

Build mobile assets trước Cargo: Axum embed `mobile-dist` bằng `include_dir`. Các test Rust dùng listener/disk thật và Manager approval; không có auto-approve trong sản phẩm. Đọc `docs/TESTING.md` để kiểm thử trên PC/phone.

Kiểm tra SHA-256 riêng với dữ liệu trên 4 GiB: `npm run test:hash:large` (buffer 8 MiB tái sử dụng, không tạo file lớn). Đây là stress test thuật toán trên Node, không phải nghiệm thu truyền file điện thoại. Sau đợt kiểm thử VPS, dependency/cache và output build tạm được dọn; source và ZIP vẫn được giữ. Chạy lại `npm ci` và `npm run build` trước khi build/test tiếp.

## Kiến trúc và agent
`docs/MVP.md`: contract, protocol/limits, failure semantics. `src-tauri/src`: Rust modules. `src/desktop` và `src/mobile`: UI riêng. `tools/codeintel/README.md`: local index và giới hạn parser.

Session sau chỉ cần: `@AGENT.md [task]`. Agent phải đọc MEMORY, load context chọn lọc, query graph khi phù hợp, xác minh source, sửa tối thiểu và cập nhật history/memory.
