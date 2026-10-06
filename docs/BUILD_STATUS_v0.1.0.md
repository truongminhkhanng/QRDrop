# QRDrop — kết quả build và phát hành v0.1.0

Kiểm tra: 2026-10-06 21:21, Asia/Ho_Chi_Minh.

[Release v0.1.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v0.1.0) đã publish dạng bản thử nghiệm (prerelease), đủ bốn bộ cài mới. Repository giữ riêng tư; đăng nhập tài khoản có quyền truy cập để tải.

Source ứng dụng đã kiểm thử: `f118e962e0af655e43e5f061b06cabe434ff0eec`.
[Build và kiểm thử 37471485522](https://github.com/truongminhkhanng/QRDrop/actions/runs/37471485522): thành công trên Windows x64, macOS Apple Silicon ARM64 và Ubuntu 24.04 x64.
[Publish 37477828846](https://github.com/truongminhkhanng/QRDrop/actions/runs/37477828846): thành công.

Tag `v0.1.0` trỏ đến commit phát hành `e97eaa26b92f4668572eb32d870fb2299dc89b01`. Đã so sánh Git blob: 53 tệp ứng dụng/config/lockfile/test/icon/tool giống hệt source đã kiểm thử; chỉ tài liệu và workflow publish khác. Tag commit dùng nội dung workflow hiện tại để phù hợp quyền của GITHUB_TOKEN. Không thay mã ứng dụng sau build.

## Kiểm thử tự động

- Strict TypeScript, production build desktop/mobile, SHA-256, code-index fixtures và bốn mobile API regressions đạt trên cả ba runner.
- Receiver dùng HTTP/listener/disk thật: **11 tests Windows, 12 macOS, 13 Linux**, không có test thất bại.
- Bao gồm: approval trước ghi dữ liệu; reject/expiry/cancel; Host/Origin; Accept/Reject đồng thời; chunk 8 MiB; rollback/hash/replay/offset; zero-byte; không ghi đè; phục hồi chỉ dọn tệp tạm thuộc phiên.
- Test mới đạt: token QR được thu hồi ngay sau connect hợp lệ, gửi lại đúng yêu cầu nhận cùng phản hồi, token không tạo yêu cầu thứ hai; trường lạ/kích thước âm/traversal bị từ chối mà chưa tiêu thụ token.
- Linux dùng socket từ 127.0.0.2 để chứng minh peer khác không lấy attempt, đọc trạng thái, gửi bằng grant bị lấy lại hoặc hủy phiên. Test này chỉ chạy trên Linux; không coi là nghiệm thu mạng hai điện thoại.
- Desktop Cargo check và đóng gói native đạt trên cả ba OS; npm ci và Cargo --locked dùng lockfile đã commit.

## Bộ cài và SHA-256

| Bộ cài | Bytes | SHA-256 |
|---|---:|---|
| QRDrop_0.1.0_aarch64.dmg | 3989963 | `75da57075abe0db7cbb7455a1afad1148e8374141264ad159f858b02f3530ebb` |
| QRDrop_0.1.0_amd64.AppImage | 80464376 | `ddd8dd107f335efb8d957c5c33a1256d6215f3061c3d9b5f40ab9a3c1d2d922b` |
| QRDrop_0.1.0_amd64.deb | 4941382 | `28ed704a834366bf1dd61d1dbbd604ef77adb0eba3f0f48f81e47a7749d888e3` |
| QRDrop_0.1.0_x64-setup.exe | 218085176 | `d1a9acfa4b3349372a4997f62eb317a27a685f2bdc72b3ba058d47df18f9b178` |

Digest lấy từ metadata GitHub. Trước/sau publication, cả bốn asset giữ nguyên ID, tên, kích thước và digest. Không tải bộ cài lớn xuống VPS. So sánh SHA-256 sau khi tải về PC.

## Bảo mật và câu chữ

Token 256 bit dùng cho một yêu cầu, kiểm tra đầu vào phía máy tính, quyền gửi riêng sau phê duyệt, API ràng buộc IP đã kết nối. Chỉ mở listener trên IPv4 riêng đã chọn, cổng do OS cấp; đóng sau khi phiên kết thúc. Xem [SECURITY.md](../SECURITY.md) về retry, timeout, IP/NAT và giới hạn bảo vệ.

Đã chuẩn hóa lỗi Offset/chunk/hash, đọc/ghi dữ liệu, chọn/mở thư mục, server/Worker và cài đặt thành tiếng Việt cho người dùng; không hiển thị lỗi runtime thô trong UI. Thông báo của hệ điều hành khi cài đặt nằm ngoài câu chữ của ứng dụng.

## Dependency đã khóa

Lockfiles lấy từ CI thành công trước đó, không tạo checksum giả. Run mới đã thực sự sử dụng và kiểm thử với các lock này; Rust Tauri và npm API 2.12.1.

| File | SHA-256 |
|---|---|
| package-lock.json | `1e3666b5494b74d6d6b14d9dd174567fa51dfde50d2f5899791bb610c52808c0` |
| src-tauri/Cargo.lock | `67db921d72bfd1058e2c6d6e316c8e5a573f3388fa292a8d3066ba2e15d9972c` |

VPS không phân giải npm/crates; native/build mới được xác minh trên GitHub runners. Local hash/mobile/index checks đạt bằng TypeScript 5.9.2 cache có sẵn đã kiểm tra SHA-512; CI dùng TypeScript 5.9.3 đã khóa. Code index cuối: 42 files/756 symbols, fresh; SQLite integrity đạt.

## Cần nghiệm thu trên thiết bị thật

Chưa chạy cài đặt/mở app và iPhone/Android LAN transfer trên thiết bị người dùng; chưa nghiệm thu truyền nhiều GB, RAM điện thoại, firewall, disk-full và các filesystem. Xem [TESTING.md](TESTING.md). HTTP không mã hóa; token/IP/port/SHA-256 không chống nghe lén hoặc MITM. TLS cần thiết kế chứng chỉ/trust riêng cho điện thoại và chưa được triển khai.

Windows chưa ký publisher; macOS ký ad-hoc, chưa Developer ID/notarization. Chưa có Mac Intel; macOS minimum 13.0 và khả năng tương thích các distro Linux cần nghiệm thu. Đây là prerelease có kiểm thử tự động, chưa phải production đã nghiệm thu.

## Dọn VPS

Đợt này đã xóa node_modules, cache npm riêng /tmp/qrdrop-final-npm và hai scratch files: **24,092,672 allocated bytes (22.977 MiB)**. Hai lần dọn trước (285.74 MiB và 22.953 MiB) là số đo riêng, không cộng lặp. Không tải installer vào VPS. Giữ source, locks, history/memory, index và artifacts/QRDrop-source.zip. Muốn chạy lại tooling/build: npm ci rồi npm run build.
