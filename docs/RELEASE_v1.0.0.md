# QRDrop 1.0.0

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
