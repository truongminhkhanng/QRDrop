# QRDrop

Nhận tệp từ iPhone/Android về máy tính qua mạng nội bộ: quét QR, chọn tệp và cho phép trên máy tính. Điện thoại dùng trình duyệt, không cần cài ứng dụng.

**Đã phát hành [v0.1.0 — Bản thử nghiệm](https://github.com/truongminhkhanng/QRDrop/releases/tag/v0.1.0).** Source, kiểm thử HTTP thật và bộ cài được xác minh qua GitHub Actions; xem kết quả theo từng nền tảng tại [`docs/BUILD_STATUS.md`](docs/BUILD_STATUS.md). Cần kiểm thử cài đặt và truyền file bằng điện thoại/PC thật trước khi nghiệm thu sử dụng.

## Các điều cần biết
- Điện thoại không cần cài app. File phải có sẵn cục bộ nếu không có Internet.
- HTTP trên LAN không mã hóa. Chỉ dùng mạng tin cậy.
- Giữ trình duyệt mở và màn hình điện thoại hoạt động khi gửi.
- Giữ nguyên dữ liệu tệp do trình duyệt cung cấp; tệp chọn từ Photos có thể khác tài nguyên gốc.
- Tệp được nhận vào vùng tạm và kiểm tra trước khi lưu hoàn tất. Không ghi đè tệp đã có.
- Có thể thử gửi lại khi gián đoạn trong phiên đang chạy. Tải lại trang hoặc mở lại ứng dụng cần quét QR mới.

## Tải bộ cài qua GitHub
Repository riêng tư: [truongminhkhanng/QRDrop](https://github.com/truongminhkhanng/QRDrop). Đăng nhập tài khoản có quyền truy cập, mở [Release v0.1.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v0.1.0), rồi chọn bộ cài phù hợp. Mã kiểm tra SHA-256 nằm trong ghi chú phát hành.

- Windows x64: NSIS setup.exe, có WebView2 offline installer.
- macOS Apple Silicon: DMG ARM64.
- Linux x64: AppImage/deb, build trên Ubuntu 24.04.

Workflow chạy khi push main/master hoặc **Actions → Build QRDrop installers → Run workflow**. Build trong repository riêng tư lưu bộ cài ở draft release theo từng run; không tự publish. Actions artifacts chỉ dùng cho PR hoặc repository công khai. `package-lock.json` và `src-tauri/Cargo.lock` đã khóa dependency từ run CI thực tế; dùng `npm ci` và Cargo `--locked`, không sửa checksum bằng tay.

GitHub dùng cho build/phân phối, không trung chuyển file. Người dùng bộ cài không cần Node/Rust/npm.

Windows installer hiện chưa ký publisher certificate. macOS build test ad-hoc signed; muốn phát hành public cần Developer ID + notarization. Không tắt bảo vệ hệ thống toàn cục để xử lý lỗi cài đặt. Linux compatibility phải kiểm thử theo distro; không hứa mọi Linux.

## Bảo vệ phiên nhận

Token QR chỉ tạo một yêu cầu; máy tính kiểm tra đầu vào và phải phê duyệt trước khi nhận dữ liệu. Quyền gửi giới hạn trong danh sách tệp đã duyệt, bị thu hồi khi kết thúc phiên. API chỉ chấp nhận IP của điện thoại đã kết nối; đổi IP cần tạo mã QR mới. Cổng nhận chỉ mở trên IP mạng nội bộ đã chọn và đóng sau khi kết thúc phiên.

HTTP chưa mã hóa. Các kiểm tra token/IP/cổng không bảo vệ khỏi nghe lén mạng; xem [SECURITY.md](SECURITY.md) để biết giới hạn và kiểm thử.

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
npm run tauri -- build --bundles nsis -- --locked
# macOS Apple Silicon
npm run tauri -- build --target aarch64-apple-darwin --bundles dmg -- --locked
# Linux
npm run tauri -- build --bundles appimage,deb -- --locked
```

## Kiểm tra
```bash
npm run build
npm run test:hash
npm run test:codeintel
npm run test:mobile
cargo test --locked --manifest-path src-tauri/Cargo.toml --no-default-features
cargo check --locked --manifest-path src-tauri/Cargo.toml
```

Build mobile assets trước Cargo: Axum embed `mobile-dist` bằng `include_dir`. Các test Rust dùng listener/disk thật và Manager approval; không có auto-approve trong sản phẩm. Đọc `docs/TESTING.md` để kiểm thử trên PC/phone.

Kiểm tra SHA-256 riêng với dữ liệu trên 4 GiB: `npm run test:hash:large` (buffer 8 MiB tái sử dụng, không tạo file lớn). Đây là stress test thuật toán trên Node, không phải nghiệm thu truyền file điện thoại. Sau đợt kiểm thử VPS, dependency/cache và output build tạm được dọn; source và ZIP vẫn được giữ. Chạy lại `npm ci` và `npm run build` trước khi build/test tiếp.

## Kiến trúc và agent
`docs/MVP.md`: contract, protocol/limits, failure semantics. `src-tauri/src`: Rust modules. `src/desktop` và `src/mobile`: UI riêng. `tools/codeintel/README.md`: local index và giới hạn parser.

Session sau chỉ cần: `@AGENT.md [task]`. Agent phải đọc MEMORY, load context chọn lọc, query graph khi phù hợp, xác minh source, sửa tối thiểu và cập nhật history/memory.
