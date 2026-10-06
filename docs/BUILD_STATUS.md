# QRDrop — kết quả build thử nghiệm

Ngày kiểm tra: 2026-10-06, Asia/Ho_Chi_Minh.

## Cập nhật đang thực hiện lúc 19:34

Thông báo lỗi đã được chuẩn hóa cho người dùng. Source mới `27c1ad2a3c091b3ac3ee8ee97e940a6571dc5e89` đang chạy [build 37468085213](https://github.com/truongminhkhanng/QRDrop/actions/runs/37468085213) với lockfile đã commit. Bộ cài mới và Release v0.1.0 chưa được xác nhận hoàn tất tại thời điểm này. Kết quả bên dưới thuộc bản build trước, không chứng minh source mới đã đạt.

## Kết quả build trước

Source ứng dụng đã kiểm thử: `5378dc13f756edd3a0afe6b5ae0c365fd127316b`.
[GitHub Actions run 37401346039](https://github.com/truongminhkhanng/QRDrop/actions/runs/37401346039).
Run đã kết thúc thành công trên cả ba nền tảng. Repository `truongminhkhanng/QRDrop` giữ riêng tư. Bộ cài nằm trong draft `test-37401346039-1`, không tự publish.

## Kiểm tra tự động
- Strict TypeScript, production build desktop/mobile, SHA-256, fixture code index và 4 mobile API regression cases: đạt trên cả ba runner.
- HTTP receiver dùng listener/disk thật: 10 tests trên macOS/Linux, 9 trên Windows (symlink test chỉ có Unix).
- Bao gồm approval trước ghi bytes, reject/expiry/cancel, Origin sai hoặc trùng, Accept/Reject đồng thời, chunk 8 MiB, rollback khi hash sai, replay xác minh body không append, offset sai, zero-byte, không overwrite và phục hồi dọn owned partials.
- Desktop Cargo check và đóng gói native: xem bảng bộ cài bên dưới. Build thành công chưa chứng minh cài đặt/chạy trên thiết bị thật.

## Bộ cài
Đăng nhập tài khoản có quyền truy cập repository rồi mở [draft release](https://github.com/truongminhkhanng/QRDrop/releases/tag/untagged-bd0bed7be60df7c7f10c).

| Nền tảng / bộ cài | Kết quả | File | Bytes | SHA-256 |
|---|---|---|---:|---|
| macOS ARM64 DMG | Đạt; uploaded | `QRDrop_0.1.0_aarch64.dmg` | 3991086 | `8b7dbdc7e38ff33310bed9a0915281cb5fb519cb013807603da00271c39dcf02` |
| Linux x64 AppImage | Đạt; uploaded | `QRDrop_0.1.0_amd64.AppImage` | 80468472 | `853b96fdd9ec7644051eda5d1b35f215450a6c8359ee4cfc067adfceb8cfff96` |
| Linux x64 deb | Đạt; uploaded | `QRDrop_0.1.0_amd64.deb` | 4943938 | `99d1b42338d3b3248d92198cfc94cf9e6d5393446c8c13aaf00fe4065f771cf7` |
| Windows x64 NSIS | Đạt; uploaded | `QRDrop_0.1.0_x64-setup.exe` | 218079685 | `cfa1c3a8d60e78a9fd656de3bd5b6593d0c9af8870958d5ff68a83248f0824de` |

Digest trong bảng lấy từ metadata GitHub release assets; không tải bộ cài lớn xuống VPS. So sánh SHA-256 sau khi tải về PC.

## Dependency đã khóa
`package-lock.json` và `src-tauri/Cargo.lock` được lấy nguyên bytes từ log của job macOS thành công, không tự viết checksum. Cargo lock khớp từng byte trên cả ba runner; npm lock macOS/Linux khớp từng byte, Windows chỉ khác newline CRLF và nội dung JSON giống hệt. Rust Tauri và npm API cùng phiên bản `2.12.1`. npm TypeScript `5.9.3`, CLI `2.11.4`. Source dùng `npm ci` và Cargo `--locked`; bootstrap resolve lockfile đã bỏ. Commit ghi nhận sau run chỉ thêm lockfiles thật, tài liệu và bỏ bootstrap; source ứng dụng giữ nguyên so với commit đã build.

| File | SHA-256 |
|---|---|
| `package-lock.json` | `1e3666b5494b74d6d6b14d9dd174567fa51dfde50d2f5899791bb610c52808c0` |
| `src-tauri/Cargo.lock` | `67db921d72bfd1058e2c6d6e316c8e5a573f3388fa292a8d3066ba2e15d9972c` |

VPS không phân giải được npm/crates: không nhận kết quả CI là build native tại VPS. TypeScript phục vụ code index được trích từ cache có sẵn rồi dọn sau cập nhật index. Source ZIP giữ cả hai lockfile và không chứa dependency/build output.

## Cần kiểm thử trên thiết bị thật
Cài và mở app trên PC, quét QR từ iPhone/Android, Accept và truyền file để đối chiếu SHA-256; kiểm tra >2 GiB/>10 GiB, RAM điện thoại, Wi-Fi gián đoạn, firewall, disk-full và từng filesystem. Theo [TESTING.md](TESTING.md), ghi OS/browser và kết quả, không ghi credential. Windows chưa ký publisher; macOS ký ad-hoc, chưa có Developer ID/notarization; macOS minimum 13.0 và khả năng tương thích distro Linux chưa được nghiệm thu. Không coi bản thử nghiệm này là release production đã nghiệm thu.

## Dọn VPS
Đợt hoàn thiện này đã xóa dependency tooling trong `node_modules` và cache npm riêng `/tmp/qrdrop-completion-npm`: 24.068.096 allocated bytes, khoảng 22,95 MiB. Không tải bộ cài vào VPS. Giữ source, lockfiles, history/memory, SQLite code index và `artifacts/QRDrop-source.zip`; không xóa cache hay dữ liệu dự án khác. Để chạy lại tooling/build: `npm ci`, rồi `npm run build`.
