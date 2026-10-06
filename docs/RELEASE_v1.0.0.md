# QRDrop 1.0.0

English · Tiếng Việt

Receive files from your phone directly on your computer over a local network. Your phone uses a browser; the desktop installer requires no Node.js, npm or Rust.

## What's new

- **Enable / disable receiving:** receiving starts off when you open QRDrop. Turn it on when you need it and close the connection when you are done.
- **Refresh QR:** replace the current code and invalidate the old one. A pending request or transfer asks for confirmation before it ends.
- Disabling receiving revokes transfer permission, closes the listening port and removes unfinished data. Completed files are kept.
- Your computer still approves the file list before any file data is received. The app interface currently uses Vietnamese.

## Install

| Computer | Download |
|---|---|
| Windows 64-bit | [Windows installer](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_x64-setup.exe) |
| Apple Silicon Mac | [Mac disk image](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_aarch64.dmg) |
| Linux 64-bit | [AppImage](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_amd64.AppImage) |
| Ubuntu/Debian 64-bit | [Debian package](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_amd64.deb) |

Open the Windows installer, or open the Mac disk image and drag QRDrop into Applications. For Linux, install the Debian package with your software manager or allow the AppImage to run as a program. There is no Intel Mac installer. Sign in with an authorized GitHub account while the repository is private.

## Get started

Connect both devices to the same reachable network. Open Settings (**Cài đặt**) to choose a save folder, then enable receiving (**Bật nhận tệp**) and scan the QR code. Choose files on your phone, request to send, then approve the list on your computer (**Cho phép**). Keep the phone page open until the transfer finishes.

Files do not travel through a cloud relay and existing files are never overwritten. HTTP is not encrypted: use a trusted network. Photo-library files depend on the data supplied by your phone browser.

## Compatibility and verification

Installers pass automated checks and native packaging on Windows x64, macOS ARM64 and Ubuntu 24.04 x64 before publication. Installation and transfers on real PCs, iPhones and Android devices, multi-GB phone transfers and other Linux distributions still need verification.

Windows has no publisher signature; macOS is ad-hoc signed and is not notarized. The operating system may show a warning. The configured minimum macOS version is 13.0.

---

# QRDrop 1.0.0 — Tiếng Việt

Nhận tệp từ điện thoại về máy tính qua mạng nội bộ. Điện thoại dùng trình duyệt; bộ cài trên máy tính không cần Node.js, npm hay Rust.

## Điểm mới

- **Bật nhận tệp / Tắt nhận tệp:** chủ động mở hoặc đóng kết nối nhận. Khi mở ứng dụng, nhận tệp đang tắt.
- **Làm mới QR:** tạo mã kết nối mới và thu hồi mã cũ. Nếu đang có yêu cầu hoặc đang gửi, ứng dụng hỏi xác nhận trước khi kết thúc phiên.
- Tắt nhận đóng cổng kết nối, thu hồi quyền gửi và dọn tệp chưa hoàn tất. Tệp đã lưu được giữ lại.
- Giao diện và thông báo dùng tiếng Việt; máy tính vẫn phải cho phép trước khi điện thoại gửi dữ liệu.

## Chọn bộ cài

Đăng nhập GitHub bằng tài khoản có quyền truy cập, rồi chọn bộ cài phù hợp:

| Máy tính | Bộ cài |
|---|---|
| Windows 64-bit | [QRDrop_1.0.0_x64-setup.exe](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_x64-setup.exe) |
| Mac dùng chip Apple Silicon | [QRDrop_1.0.0_aarch64.dmg](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_aarch64.dmg) |
| Linux 64-bit — AppImage | [QRDrop_1.0.0_amd64.AppImage](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_amd64.AppImage) |
| Ubuntu/Debian 64-bit — deb | [QRDrop_1.0.0_amd64.deb](https://github.com/truongminhkhanng/QRDrop/releases/download/v1.0.0/QRDrop_1.0.0_amd64.deb) |

Windows: mở `.exe` để cài. Mac: mở `.dmg` rồi kéo QRDrop vào Applications. Linux: cài `.deb` bằng trình quản lý phần mềm hoặc cấp quyền chạy cho `.AppImage`. Chưa có bộ cài cho Mac Intel.

## Gửi tệp

1. Mở QRDrop, chọn thư mục nhận trong **Cài đặt**.
2. Kết nối điện thoại và máy tính vào cùng mạng có thể truy cập nhau.
3. Bấm **Bật nhận tệp**, dùng camera điện thoại quét QR.
4. Chọn tệp và bấm **Yêu cầu gửi tệp** trên điện thoại.
5. Kiểm tra danh sách trên máy tính rồi bấm **Cho phép**. Giữ trang điện thoại mở đến khi hoàn tất.
6. Bấm **Mở thư mục** để xem tệp. Bấm **Bật nhận tệp** cho lần gửi tiếp theo, hoặc **Làm mới QR** để thay mã đang chờ. Dùng **Tắt nhận tệp** khi không cần nhận nữa.

Mã QR chỉ tạo một yêu cầu hợp lệ. Dữ liệu không qua máy chủ đám mây, không ghi đè tệp đã có và được kiểm tra trước khi lưu hoàn tất. Kết nối HTTP chưa mã hóa; chỉ dùng mạng tin cậy. Tệp chọn từ Photos phụ thuộc dữ liệu do trình duyệt cung cấp.

## Kiểm thử và khả năng tương thích

Bộ cài được kiểm thử tự động và đóng gói trên Windows x64, macOS ARM64 và Ubuntu 24.04 x64 trước khi phát hành. Cài đặt và truyền tệp trên PC/iPhone/Android thật, tệp nhiều GB và khả năng tương thích từng bản Linux vẫn cần nghiệm thu.

Windows chưa có chữ ký nhà phát hành; macOS ký ad-hoc, chưa notarize. Hệ điều hành có thể hiện cảnh báo khi mở. Cấu hình macOS tối thiểu là 13.0; chưa xác minh trên mọi thiết bị.

Source ứng dụng đã kiểm thử: `523b49acfec366390313bfedfda42992f05a5c01`. Tag phát hành: `2ef17c68da39537f16a7d69fb1152d44d3f55c6c` (cùng mã ứng dụng và lockfile). [Kiểm thử và build](https://github.com/truongminhkhanng/QRDrop/actions/runs/37482136952).

## Mã kiểm tra SHA-256

| Bộ cài | Bytes | SHA-256 |
|---|---:|---|
| QRDrop_1.0.0_x64-setup.exe | 218094443 | `d8b5e41b11d0b638dc7ed5429ecd6407283cd8f3abdb0d8a34474167fd0c2040` |
| QRDrop_1.0.0_aarch64.dmg | 4005291 | `2001b0bc74fdfdbb0533ce4f892167e172f848be291906cd1fd9ffea0d46ec95` |
| QRDrop_1.0.0_amd64.AppImage | 80476664 | `a392b732e42a1178dbeed016048520d33413a86e886149ebd52e9e9e8b3cccdc` |
| QRDrop_1.0.0_amd64.deb | 4961130 | `8ec37aefe813c58ebe02c63e08b5268915ce12cfce7d063d2931e349bf45abf7` |
