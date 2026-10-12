# PhoneDrop — Lịch sử phiên bản

## 1.0.2 — 2026-10-12

- Thêm Bật nhận file / Tắt nhận file; mặc định tắt khi khởi động. Tắt đóng kết nối, thu hồi QR/phiên và hủy file dở; giữ file hoàn tất.
- Mở IP:cổng không có mã QR sẽ hiện trang kiểm tra kết nối, không tiêu thụ QR hoặc tính lỗi mã khiến thiết bị bị khóa tạm.
- Hiển thị địa chỉ đang dùng, sao chép liên kết đầy đủ, kiểm tra trên PC và trợ giúp Wi-Fi/Ethernet/Firewall.
- Làm mới danh sách IP khi bật nhận hoặc mở Cài đặt. Áp dụng cài đặt khi đang tắt không tự bật nhận.

Kiểm tra trên PC không chứng minh điện thoại truy cập được. Bản này vẫn dùng LAN; không thêm truyền qua 4G/5G khác mạng.

## 1.0.1 — 2026-10-10

- Hiển thị phiên bản trên thanh tiêu đề cửa sổ PC để nhận biết bản đang chạy.
- Đồng bộ phiên bản ứng dụng, kết quả kiểm tra EXE và tag phát hành; chặn phát hành nếu không khớp.
- Áp dụng quy trình tạo phiên bản mới và tự đặt bản chính thức làm Latest, với kiểm tra chống trùng hoặc lùi phiên bản.

Luồng gửi file giữ nguyên: phiên 12 giờ, ngắt thủ công, tối đa 5 GiB/file và gửi tuần tự qua LAN. Đây không phải bản bổ sung truyền qua Internet.

## 1.0.0 — 2026-10-10

- Phát hành ứng dụng Windows nhận file qua QR và trình duyệt điện thoại trên LAN.
- Giao diện tiếng Việt, duyệt trên PC, tiến trình nhận file, phiên 12 giờ và ngắt thủ công.
- Có EXE, checksum và kiểm thử tự động Windows/Linux; nghiệm thu điện thoại thật, DPI và đợt nhiều GB còn cần thực hiện.
