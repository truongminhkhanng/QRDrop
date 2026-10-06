# Kiểm thử QRDrop trên máy thật

## Kết quả khởi tạo trên VPS (lịch sử)
Ngày 2026-10-06: strict TypeScript và production builds của desktop/mobile pass; SHA-256 so với Node crypto và các fixture code index pass. Asset references nội bộ và hash Worker trong mobile bundle đã được kiểm tra tĩnh. Rust test dừng trước compile vì chưa có Axum trong cache; VPS không phân giải được `index.crates.io`. Native compile, bộ cài và truyền file trên điện thoại thật vẫn chưa được xác minh. Đây là giới hạn tại thời điểm khởi tạo. Kết quả native CI mới nhất nằm trong [BUILD_STATUS.md](BUILD_STATUS.md).

Stress test riêng chạy bằng `npm run test:hash:large`: so sánh browser hasher với Node crypto trên 4 GiB + 8 MiB + 3 bytes, tái sử dụng một buffer 8 MiB, không tạo file nhiều GB. Lệnh này chạy theo yêu cầu, không nằm trong test nhanh mặc định. Kết quả hash trên Node không thay thế kiểm thử upload hay RAM trên iPhone.

Kết quả stress: SHA-256 khớp trên 4.303.355.907 bytes, khoảng 135 giây; peak RSS của process Node khoảng 79 MiB. Đây là số đo VPS, không phải hiệu năng điện thoại. `npm run test:mobile` có 4 regression tests cho polling: phục hồi lỗi mạng, dừng với credential bị từ chối, retry lỗi HTTP tạm thời có giới hạn, và hủy trong backoff. Tests dùng fetch fixtures trên module API thật; không giả định server/native đã chạy. Nhánh polling đã sửa để HTTP status 0 (lỗi kết nối) được thử lại thay vì dừng ngay.

Dependency/cache tạm và output build trên VPS được dọn sau kiểm thử theo yêu cầu người dùng. Khi kiểm thử tiếp từ source: chạy `npm ci`, rồi `npm run build` trước Cargo để tạo lại mobile assets.

## Luồng cơ bản
1. Cài bộ cài trong Release v0.1.0 Windows/macOS/Linux sau khi CI build thành công. Dùng thư mục test riêng có đủ dung lượng.
2. Cho phép QRDrop truy cập LAN/firewall khi OS hỏi. Cùng mạng có thể bị guest/client isolation; tắt VPN hoặc chọn interface thực tế nếu địa chỉ sai.
3. Quét QR bằng camera → browser mở → chọn file → yêu cầu gửi.
4. **Chưa Accept:** không có file bytes được ghi. Từ chối: không được gửi, phải tạo QR mới.
5. Accept → quan sát tiến độ phone/desktop → verifying → complete. SHA-256 trong Recent Transfers phải khớp file nguồn thực sự browser cung cấp.
6. Open Folder mở native file manager. Nhận tiếp/Refresh tạo phiên mới; link cũ không authorize được.

## Ma trận cần ghi lại
OS/build version, điện thoại/model, iOS/Android/browser version, picker Files hay Photos, mạng/interface/firewall, filesystem/disk trống, file sizes/hash và kết quả. Không lưu token/URL QR vào report; thay `[REDACTED SECRET]`.

## Bytes và file lớn
File zero-byte; arbitrary extension; HEIC/DNG/MOV/ZIP từ Files; tên Unicode; trùng tên; 100MiB; >2GiB; >10GiB từ provider hỗ trợ. Theo dõi RAM để chứng minh không tăng theo tổng size. Kiểm tra cả SHA bên ngoài bằng công cụ OS khi có thể. Browser-provided JPG không chứng minh original HEIC được giữ.

## Gián đoạn và an toàn
- Mất Wi-Fi ngắn giữa chunk, phục hồi: không duplicate bytes; SHA vẫn khớp.
- Mất ACK/duplicate request: không append lần hai.
- Lock phone/đổi app/đóng browser: báo hoặc timeout rõ, không false complete.
- Hủy sau file đầu: giữ file complete, dọn phần dở, trạng thái partial completion.
- Disk full, folder mất quyền, tháo ổ đĩa: không có file hỏng mang tên hoàn chỉnh.
- Tạo file cùng tên ngay lúc finalize: file cũ không đổi bytes.
- Kill desktop giữa transfer, mở lại: owned partials được dọn; `.part` không thuộc QRDrop được giữ.
- QR hết hạn trước Accept và grant không hoạt động: không ghi file.
- Mã QR đã dùng không tạo thêm yêu cầu hoặc thay danh sách tệp. Gửi lại đúng yêu cầu từ cùng điện thoại nhận cùng phiên, không tạo phiên khác.
- Thiết bị có IP khác không lấy được trạng thái, gửi dữ liệu hay hủy phiên, kể cả khi dùng lại token phiên. Đổi IP điện thoại giữa phiên: cần tạo QR mới.
- HTTP vẫn không mã hóa; không diễn giải IP, port ngẫu nhiên hoặc SHA-256 thành khả năng chống nghe lén/MITM.
- Shared symlink/reparse path không thoát destination; unknown staging content không bị xóa mù.

## Backend automation
Sau `npm run build`, chạy `cargo test --locked --manifest-path src-tauri/Cargo.toml --no-default-features`. Integration suite dùng HTTP thật, không cần desktop/display. Source chứa kiểm tra approval/replay/no-overwrite/hash/zero-byte/origin/traversal/reject/expiry/cancel và symlink Unix. Suite phải compile/pass trước khi tin behavior.

Không thay phone acceptance bằng test mock. Gửi lỗi gồm OS/version, bước tái hiện, error message, kích thước/loại file và CI logs đã redact; không gửi credential.
