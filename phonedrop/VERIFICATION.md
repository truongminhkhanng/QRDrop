# Bằng chứng kiểm chứng PhoneDrop — 2026-10-10

## Trạng thái hiện tại

Source cục bộ có phiên nhận tối đa 12 giờ, timeout gửi mobile lấy từ cùng cấu hình server, đồng hồ giờ:phút:giây và ngắt thủ công. 12 giờ là mặc định agent chọn khi tiếp tục yêu cầu kéo dài phiên; chưa phải thời lượng user xác nhận riêng. QR 120 giây và chờ duyệt 60 giây giữ nguyên.

**Chưa hoàn tất bản phát hành Windows:** source mới chưa chạy CI/native, chưa có PhoneDrop.exe được xác minh, chưa kiểm thử điện thoại thật. Sau khi nhận bản xem trước và câu hỏi tiếp tục GitHub/EXE, user yêu cầu “AGENT.md Làm xong cho tao đi”; agent tiếp tục upload và CI theo chỉ dẫn đó. Điều này không phải bằng chứng user đã kiểm tra trực quan native UI. Xem [bản xem trước](docs/ux-preview.html) và [bản mô tả UX](docs/UX_REVIEW.md).

## Đã kiểm tra trên source hiện tại

- `python3 -m pytest -q -m 'not network'`: **126 passed, 3 deselected**.
- `node tests/mobile-ui.test.cjs`: **11 passed**. Test nạp HTML đã được Python tạo để kiểm tra đúng timeout trong trang được phục vụ; `node --test tests/mobile-ui.test.cjs` cũng exit 0 (Node 26 ở môi trường này gộp báo cáo theo file).
- `python3 tools/check_mobile.py`: JavaScript mobile hợp lệ.
- Python compileall cho app/core/desktop/viewmodel/TLS/tests/tools: pass.
- Preview được tạo lại từ source, gồm đồng hồ 11:59:42 và timeout mobile 12 giờ. Desktop vẫn là minh họa, mobile dùng mạng giả lập và không đọc nội dung file.

| Hành vi | Bằng chứng | Giới hạn của bằng chứng |
|---|---|---|
| Tiếp tục upload sau mốc 20 phút | `test_slow_upload_crosses_old_twenty_minute_deadline` | Đồng hồ mô phỏng, dữ liệu nhỏ ghi đĩa thật |
| 500 file tuần tự, không gia hạn phiên | `test_500_sequential_handler_uploads_beyond_old_deadline` | HTTP handler thật với stream trong bộ nhớ; 500 file nhỏ ghi đĩa, thời gian mô phỏng 5.000 giây |
| 500 lựa chọn mobile chỉ gửi một lần, từng file tuần tự | Test JavaScript 500 file | DOM/XHR giả lập, không truyền payload qua mạng |
| Video 500 MiB và file đúng 5 GiB qua kiểm tra dung lượng | Test Python khai báo tổng byte và test mobile metadata | Không cấp phát hay truyền 5 GiB; quá 5 GiB vẫn bị chặn |
| Ngắt thủ công hủy upload, thu hồi quyền, giữ file hoàn tất | `test_manual_disconnect_after_old_deadline_preserves_completed_files`, test JS ngắt giữa 500 file | Đĩa thật, socket/XHR giả lập; ghép nối mới vẫn phải duyệt |
| Hết hạn phiên, polling không gia hạn, QR/duyệt riêng | Test expiry, monotonic clock, QR và stale-dialog hiện có | Test logic với đồng hồ mô phỏng |
| Guard Host/Origin, session/IP, executable, no-overwrite, streaming, TLS key cleanup | Các test core/TLS hiện có | Xem mã test; không thay thế kiểm tra thiết bị |

`/status` trả 202 cho phiên đúng đang chờ và 200 cho phiên đã duyệt; `/upload` luôn yêu cầu phiên đã duyệt. Phiên nhận vẫn có hạn chót tuyệt đối từ lúc duyệt; file đang dở bị hủy khi hết hạn. Chưa có resumable upload.

## Giới hạn môi trường đã xác minh lại

Chạy toàn bộ pytest trước khi sửa: 121 pass, 2 errors và 1 failed. Cả ba test mạng dừng tại tạo socket với `PermissionError: [Errno 1] Operation not permitted`, trước khi bind. Ba test HTTP/HTTPS vẫn bắt buộc trong CI; không sửa thành mock hoặc bỏ qua tự động.

Tkinter, Pillow, qrcode và PyInstaller vẫn không có trong môi trường hiện tại. Không có bằng chứng chạy native GUI hay đóng gói tại đây; Linux không tạo được Windows EXE bằng PyInstaller. Codeintel status/update cũng không chạy do thiếu TypeScript; việc sửa dựa trên đọc source và kiểm thử trực tiếp.

## CI trước đây và bước còn lại

[Run 37938480572](https://github.com/truongminhkhanng/QRDrop/actions/runs/37938480572) của source cũ `c4f2cff53815d66ca8e140c23b67408553178d04` đã được kiểm tra ở phiên trước: 115 pytest pass trên Windows/Linux, gồm HTTP/HTTPS. Windows job dừng tại quoting PowerShell của bước JavaScript. Bản sửa cục bộ dùng `tools/check_mobile.py`; không gán kết quả run cũ cho source hiện tại.

Bước tiếp theo: đưa đúng thư mục `phonedrop/` và workflow gốc `.github/workflows/phonedrop.yml` lên nhánh `feature/phonedrop` của repo `truongminhkhanng/QRDrop`. Không thay toàn bộ cây QRDrop bằng Git độc lập trong phonedrop. Theo dõi test Linux/Windows và smoke test executable (Tk, desktop UI, QR, TLS, HTTP upload), tải artifact rồi xác minh MZ, SHA-256 và chạy trên Windows. Chỉ phát hành bằng tag riêng `phonedrop-v1.0.0` sau khi thành công; giữ nguyên release QRDrop.

Kiểm tra tiếp Android/iPhone trên Wi-Fi ↔ Ethernet, 500 file/~5 GB thật, ngắt/hết hạn giữa upload, Firewall, DPI 125–200%, QR camera, keyboard và HTTPS fingerprint. Không coi preview hay test dữ liệu nhỏ là bằng chứng cho những bước này.
