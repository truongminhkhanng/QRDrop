# Bảo mật QRDrop

## Phạm vi

QRDrop nhận tệp trên mạng nội bộ tin cậy. Kết nối HTTP hiện không mã hóa; người có khả năng nghe lén hoặc sửa lưu lượng mạng có thể lấy token, dữ liệu hoặc thay nội dung trang. Không dùng bản này trên mạng không tin cậy. Một cổng ngẫu nhiên và token dùng một lần không thay thế HTTPS/TLS với chứng chỉ được thiết bị tin cậy. Xem [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

## Các kiểm tra trong ứng dụng

- Token ngẫu nhiên 256 bit do hệ điều hành cấp nguồn ngẫu nhiên; so sánh credential theo thời gian cố định. Token chỉ tồn tại trong RAM; không ghi ra log, lịch sử hoặc code index.
- Token QR hết hạn sau 10 phút, chỉ tạo một yêu cầu với danh sách tệp cố định và bị xóa ngay khi yêu cầu hợp lệ được tiếp nhận. Gửi lại đúng yêu cầu từ cùng IP chỉ lấy lại phản hồi cũ để phục hồi mất kết nối.
- Token theo dõi và quyền gửi là hai credential riêng. Máy tính phải cho phép qua IPC local trước khi ghi dữ liệu tệp. Hủy, từ chối, hết hạn hoặc hoàn tất thu hồi quyền gửi.
- API chỉ chấp nhận IP đã kết nối, đồng thời vẫn yêu cầu đúng credential và trạng thái phiên. IP không chứng minh danh tính: nhiều thiết bị có thể dùng chung IP qua NAT/proxy; thiết bị đổi IP cần tạo phiên mới.
- Máy chủ kiểm tra schema, từ chối trường lạ, kiểm tra tên/dung lượng/số lượng tệp, giới hạn nội dung yêu cầu trước khi đọc JSON, và không nhận đường dẫn do điện thoại chỉ định. Xem [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html).
- Kiểm tra Host/Origin/Sec-Fetch-Site, giới hạn số kết nối/yêu cầu và tần suất kết nối, thời gian chờ và tiến triển; không có API LAN để phê duyệt hoặc thao tác thư mục máy tính.
- Chỉ bind vào IPv4 riêng đã chọn; hệ điều hành cấp cổng trống cho mỗi phiên. Không bind 0.0.0.0, không UPnP, không relay/cloud. Listener ngừng khi phiên kết thúc (giữ tối đa khoảng 30 giây cho điện thoại đọc kết quả) hoặc khi tạo phiên mới/đóng app.
- Dữ liệu nhận theo phần tối đa 8 MiB, kiểm tra dung lượng/vị trí/SHA-256, rollback phần sai và xác minh dữ liệu gửi lại. Tệp tạm chỉ được công bố sau khi kiểm tra SHA-256 trên đĩa; không ghi đè hoặc tự chạy tệp.

SHA-256 phát hiện sai khác dữ liệu; trên HTTP nó không xác thực bên gửi và không bảo vệ khỏi kẻ sửa cả dữ liệu lẫn mã kiểm tra. Phần mềm độc hại có quyền của chính người dùng hệ điều hành nằm ngoài phạm vi bảo vệ này.

## Kiểm thử và báo lỗi

Xem [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md) để biết source/run đã kiểm thử và [docs/TESTING.md](docs/TESTING.md) để nghiệm thu trên thiết bị thật. Kiểm thử peer khác dùng hai địa chỉ loopback trên Linux; không thay thế nghiệm thu hai điện thoại/PC thật. Bộ cài Windows chưa có chữ ký nhà phát hành; macOS ký ad-hoc, chưa notarize.

Khi báo lỗi trong repository riêng tư, ghi phiên bản, OS, bước tái hiện và thông báo lỗi. Không đính kèm token, URL QR đầy đủ, tệp riêng tư hoặc credential; dùng [REDACTED SECRET].
