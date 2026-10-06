# QRDrop

[English](README.md) · **Tiếng Việt**

Gửi tệp từ điện thoại sang máy tính bằng cách quét mã QR. Điện thoại dùng trình duyệt, không cần cài thêm ứng dụng.

## Tải và cài đặt

Mở [QRDrop 1.0.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v1.0.0), chọn bộ cài phù hợp với máy tính:

| Máy tính | Bộ cài | Cách cài |
|---|---|---|
| Windows 64-bit | `QRDrop_1.0.0_x64-setup.exe` | Mở tệp và làm theo hướng dẫn |
| Mac dùng chip Apple Silicon | `QRDrop_1.0.0_aarch64.dmg` | Mở tệp, kéo QRDrop vào Applications |
| Ubuntu/Debian 64-bit | `QRDrop_1.0.0_amd64.deb` | Mở bằng trình quản lý phần mềm để cài |
| Linux 64-bit | `QRDrop_1.0.0_amd64.AppImage` | Cấp quyền chạy cho tệp rồi mở |

**Không cần cài Node.js, npm hay Rust.** Chưa có bộ cài cho Mac Intel. Cấu hình macOS tối thiểu là 13.0.

Trang tải hiện giới hạn quyền truy cập. Nếu không thấy Release, hãy đăng nhập GitHub bằng tài khoản được cấp quyền.

Windows chưa có chữ ký nhà phát hành; macOS chưa notarize. Hệ điều hành có thể hiện cảnh báo khi mở bộ cài. Khả năng cài đặt và sử dụng trên từng thiết bị vẫn cần kiểm tra.

## Gửi tệp lần đầu

1. Kết nối điện thoại và máy tính vào cùng mạng Wi-Fi hoặc mạng nội bộ có thể truy cập nhau.
2. Mở QRDrop trên máy tính. Trong **Cài đặt**, chọn thư mục muốn lưu tệp.
3. Bấm **Bật nhận tệp**. Dùng camera điện thoại quét mã QR đang hiển thị.
4. Trên điện thoại, chọn tệp rồi bấm **Yêu cầu gửi tệp**.
5. Kiểm tra danh sách trên máy tính và bấm **Cho phép**.
6. Giữ trang gửi tệp mở và màn hình điện thoại hoạt động đến khi hoàn tất. Bấm **Mở thư mục** trên máy tính để xem tệp đã nhận.

QRDrop kiểm tra dữ liệu trước khi lưu hoàn tất và không ghi đè tệp đã có. Khi trùng tên, tệp mới được lưu với tên khác.

## Bật, tắt và làm mới QR

- Khi mở QRDrop, nhận tệp đang **tắt**. Bấm **Bật nhận tệp** để tạo mã QR.
- **Tắt nhận tệp** đóng kết nối nhận. Tệp đã lưu được giữ lại; phần gửi chưa hoàn tất bị hủy và dọn đi.
- **Làm mới QR** thay mã đang dùng. Mã cũ hết hiệu lực. Nếu đã có yêu cầu hoặc đang gửi, ứng dụng hỏi xác nhận trước khi kết thúc phiên.
- Sau khi một lần gửi kết thúc, bấm **Bật nhận tệp** để nhận tiếp.
- Đóng hoàn toàn QRDrop sẽ dừng nhận. Thu nhỏ cửa sổ vẫn giữ ứng dụng chạy.

## Nếu không kết nối được

- Kiểm tra hai thiết bị có thể truy cập nhau. Wi-Fi khách, VPN hoặc thiết lập cách ly thiết bị có thể chặn kết nối.
- Cho phép QRDrop truy cập mạng nội bộ khi hệ điều hành hỏi. Trong **Cài đặt**, chọn kết nối mạng phù hợp rồi tạo mã QR mới.
- Nếu mã đã hết hạn, đã dùng hoặc điện thoại đổi mạng, tạo mã QR mới và quét lại.
- Nếu gửi bị gián đoạn, giữ trang đang mở để thử lại. Khi tải lại trang hoặc mở lại ứng dụng, cần quét QR mới.
- Nếu không lưu được tệp, kiểm tra dung lượng trống và quyền ghi; thử chọn thư mục khác.

## Quyền riêng tư

Tệp đi trực tiếp từ điện thoại đến máy tính, không qua máy chủ đám mây. Máy tính phải cho phép trước khi nhận dữ liệu.

**Kết nối HTTP chưa mã hóa. Chỉ dùng trên mạng bạn tin cậy.** Mã QR và quyền gửi không thay thế mã hóa mạng. Xem [thông tin bảo mật](SECURITY.md) để biết thêm.

QRDrop giữ nguyên dữ liệu tệp do trình duyệt cung cấp. Với ảnh hoặc video chọn từ Photos, dữ liệu có thể khác bản gốc trong thư viện của điện thoại.
