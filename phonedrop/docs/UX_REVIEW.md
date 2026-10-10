# PhoneDrop — Bản UX/UI đã triển khai, chờ xem trực quan

Bản xem trước đã được gửi cho user. Ngày 2026-10-10, user trả lời yêu cầu tiếp tục GitHub/EXE bằng “AGENT.md Làm xong cho tao đi”; agent tiến hành upload và CI. Việc tiếp tục không thay thế kiểm tra trực quan giao diện native trên Windows.

## Xem bản cụ thể

Mở [ux-preview.html](ux-preview.html), chọn các trạng thái Sẵn sàng, Chờ xác nhận, Đã cho phép, Đang nhận, Nhận xong hoặc Chưa có mạng. Có thể mở Cài đặt, thu hẹp bố cục, bấm Cho phép/Từ chối và thử chọn file trong khung điện thoại.

Preview offline không gửi/lưu file. Desktop là bản mô phỏng bố cục dùng màu/trạng thái từ source, không phải ảnh chụp Tkinter. Mobile dùng đúng HTML/JS nhúng trong app, chỉ thay mạng bằng giả lập và bỏ đổi URL cho iframe. Không dùng preview để kết luận native UI đã qua kiểm chứng.

## Đã xử lý trong source

| Vấn đề trước | Thay đổi hiện tại |
|---|---|
| Cửa sổ760×850 dễ vượt màn hình | Kích thước tối đa980×660, giới hạn theo màn hình; hai cột hoặc xếp dọc; nội dung cuộn được |
| Thông tin IP/HTTPS/fingerprint chiếm trang chính | Cài đặt riêng; fingerprint chỉ có nút truy cập khi HTTPS đang hoạt động |
| Desktop/mobile khác phong cách | Cùng palette tối, chữ sáng, màu nhấn mint, trạng thái nguy hiểm màu ấm |
| Không thấy file đang nhận trên PC | Hiển thị tên file, byte đã ghi/tổng byte, progress và thời gian phiên còn lại |
| Mobile dễ gửi lại batch thành công | Xóa lựa chọn khi kết thúc, giữ kết quả, nút Gửi thêm file; phải chọn nhóm mới |
| Gộp hai hành động trong một label | Tạo QR mới khi chờ, Ngắt kết nối khi có phiên, Kết nối lại khi offline |
| Một lỗi polling ngắt phiên ngay | Thử lại tối đa3 lần; tạm khóa gửi mới khi kết nối chưa rõ; không tự retry file mất phản hồi |
| Thông tin thiết bị dài có thể đẩy nút duyệt | Vùng thông tin cuộn; nút duyệt và đếm ngược giữ ở footer |

## Phiên nhận dài — cập nhật 2026-10-10

Mặc định cục bộ tăng từ 20 phút lên 12 giờ để hỗ trợ đợt gửi lâu. PC hiển thị giờ:phút:giây, vẫn có Ngắt kết nối; ngắt sẽ hủy file dở và giữ file đã hoàn tất. Mobile dùng thời hạn từ cùng cấu hình server. QR 120 giây và xác nhận 60 giây giữ nguyên. 12 giờ là lựa chọn triển khai của agent, chưa phải xác nhận riêng của user. Preview đã được tạo lại; kiểm tra native vẫn còn trong danh sách nghiệm thu.

## Kiểm chứng

- 129 test Python đã qua trên Windows/Linux CI, gồm HTTP/HTTPS thật, gồm snapshot tiến trình, thời gian phiên, ràng buộc dung lượng và các test bảo mật cũ.
- 11 test JavaScript chạy mã trang mobile: chờ duyệt, tên file không thành HTML, chọn nhiều file, chống gửi trùng batch, giới hạn dung lượng, ngắt phiên, lỗi mạng và phục hồi polling.
- Các test mới kiểm tra 500 file tuần tự với dữ liệu nhỏ/thời gian mô phỏng, giới hạn metadata 500 MiB/5 GiB và ngắt giữa upload; chưa truyền 5 GB từ điện thoại thật.
- Python compileall, JavaScript syntax, JavaScript preview và YAML workflow đã kiểm tra.
- CI của source cũ c4f2cff5 đã qua115 test trên Windows/Linux, gồm HTTP/HTTPS thật. Run37938480572 dừng do quoting PowerShell ở bước syntax JS; đã sửa cục bộ thành script Python riêng.
- Smoke test exe đã được mở rộng để tạo đúng PhoneDropApp, mở Cài đặt, bấm Cho phép, kiểm tra progress50%, gửi HTTP, kiểm tra log, thu cửa sổ640×500 và ngắt phiên. Đã chạy thành công trong EXE trên Windows CI38055824859. Kiểm tra bằng mắt trên máy người dùng và các mức DPI vẫn còn.

## Còn cần kiểm tra native

Windows125–200% DPI, keyboard/screen reader, resize nhỏ, QR bằng camera điện thoại, dialog topmost, thư mục/tên file dài và đường dẫn Unicode, Firewall, Android/iPhone, HTTPS fingerprint. Không coi test logic hoặc preview HTML là bằng chứng cho các điểm này.
