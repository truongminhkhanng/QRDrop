# QRDrop 0.1.0 — Bản thử nghiệm

Nhận tệp từ điện thoại về máy tính qua mạng nội bộ. Điện thoại dùng trình duyệt, không cần cài ứng dụng.

## Chọn bộ cài

Đăng nhập GitHub bằng tài khoản có quyền truy cập repository, rồi chọn bộ cài phù hợp:

| Máy tính | Bộ cài |
|---|---|
| Windows 64-bit | [QRDrop_0.1.0_x64-setup.exe](https://github.com/truongminhkhanng/QRDrop/releases/download/v0.1.0/QRDrop_0.1.0_x64-setup.exe) |
| Mac dùng chip Apple Silicon | [QRDrop_0.1.0_aarch64.dmg](https://github.com/truongminhkhanng/QRDrop/releases/download/v0.1.0/QRDrop_0.1.0_aarch64.dmg) |
| Linux 64-bit — AppImage | [QRDrop_0.1.0_amd64.AppImage](https://github.com/truongminhkhanng/QRDrop/releases/download/v0.1.0/QRDrop_0.1.0_amd64.AppImage) |
| Ubuntu/Debian 64-bit — deb | [QRDrop_0.1.0_amd64.deb](https://github.com/truongminhkhanng/QRDrop/releases/download/v0.1.0/QRDrop_0.1.0_amd64.deb) |

Windows: mở file `.exe` để cài. Mac: mở `.dmg` và kéo QRDrop vào Applications. Linux: cài file `.deb` bằng trình quản lý phần mềm, hoặc cấp quyền chạy rồi mở `.AppImage`. Chưa có bộ cài cho Mac Intel.

## Gửi tệp

1. Mở QRDrop trên máy tính và chọn thư mục nhận trong Cài đặt.
2. Kết nối điện thoại và máy tính vào cùng mạng Wi-Fi hoặc mạng nội bộ có thể truy cập nhau.
3. Dùng camera điện thoại quét mã QR, chọn tệp rồi bấm **Yêu cầu gửi tệp**.
4. Trên máy tính, kiểm tra danh sách và bấm **Cho phép**.
5. Giữ trang trên điện thoại mở đến khi hoàn tất. Bấm **Mở thư mục** trên máy tính để xem tệp.

QRDrop kiểm tra dữ liệu trước khi hoàn tất và không ghi đè tệp đã có. Dữ liệu không đi qua máy chủ đám mây. Kết nối HTTP không mã hóa; chỉ dùng trên mạng bạn tin cậy. Tệp từ Photos có thể khác tài nguyên gốc do trình duyệt cung cấp.

## Bảo vệ phiên nhận tệp

Mã QR dùng cho một yêu cầu nhận tệp và hết hiệu lực ngay khi yêu cầu hợp lệ được tiếp nhận. Máy tính vẫn phải cho phép trước khi điện thoại gửi dữ liệu. Quyền gửi chỉ dùng cho danh sách tệp đã duyệt; kết thúc hoặc hủy phiên sẽ thu hồi quyền đó.

QRDrop kiểm tra đầu vào tại máy tính và chỉ nhận yêu cầu trong phiên từ địa chỉ IP của điện thoại đã kết nối. Nếu điện thoại đổi địa chỉ IP, hãy tạo mã QR mới. Cổng nhận tệp chỉ mở trên kết nối mạng nội bộ đã chọn và đóng sau khi phiên kết thúc. Các kiểm tra này không mã hóa kết nối HTTP và không chống được nghe lén mạng.

## Trạng thái bản thử nghiệm

Bộ cài đã build thành công và vượt qua kiểm thử tự động trên Windows x64, macOS ARM64 và Ubuntu 24.04 x64 trong [run 37471485522](https://github.com/truongminhkhanng/QRDrop/actions/runs/37471485522). Chưa nghiệm thu cài đặt và truyền tệp bằng PC/điện thoại thật, tệp nhiều GB hay khả năng tương thích mọi bản Linux.

Windows chưa có chữ ký nhà phát hành; macOS ký ad-hoc, chưa notarize. Hệ điều hành có thể hiện cảnh báo khi mở. Không tắt bảo vệ hệ thống toàn cục. Cấu hình macOS tối thiểu là 13.0, cần kiểm tra trên thiết bị thật.

Giao diện và thông báo lỗi của QRDrop dùng tiếng Việt. Lỗi kết nối, đọc/ghi tệp và kiểm tra dữ liệu có hướng dẫn xử lý; thông báo của hệ điều hành khi cài đặt có thể dùng ngôn ngữ hệ thống.


## Mã kiểm tra SHA-256

| Bộ cài | Bytes | SHA-256 |
|---|---:|---|
| QRDrop_0.1.0_aarch64.dmg | 3989963 | `75da57075abe0db7cbb7455a1afad1148e8374141264ad159f858b02f3530ebb` |
| QRDrop_0.1.0_amd64.AppImage | 80464376 | `ddd8dd107f335efb8d957c5c33a1256d6215f3061c3d9b5f40ab9a3c1d2d922b` |
| QRDrop_0.1.0_amd64.deb | 4941382 | `28ed704a834366bf1dd61d1dbbd604ef77adb0eba3f0f48f81e47a7749d888e3` |
| QRDrop_0.1.0_x64-setup.exe | 218085176 | `d1a9acfa4b3349372a4997f62eb317a27a685f2bdc72b3ba058d47df18f9b178` |
