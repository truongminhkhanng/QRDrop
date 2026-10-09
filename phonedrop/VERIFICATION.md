# Bằng chứng kiểm chứng PhoneDrop — 2026-10-09

**Chưa đạt Definition of Done: chưa có Actions run xanh, chưa có file Windows `.exe`, chưa có repo/release GitHub được tạo thành công.** Đây là bản source đã triển khai với các giới hạn xác minh dưới đây, không phải tuyên bố sản phẩm đã hoàn tất.

## Đã chạy trong môi trường hiện tại

- Python 3.12.3, pytest có sẵn; `python3 -m pytest -q -m 'not network'`: **112 passed, 3 deselected**.
- `node --check` với JavaScript trích nguyên từ trang mobile: pass.
- `python3 -m compileall -q app.py core.py tls_support.py tests`: pass.
- Workflow YAML parse thành công; kiểm tra phụ thuộc `test → build → release` pass.
- Kiểm thử HTTPS không socket dùng cryptography 41.0.7 có sẵn. CI cài dependency khai báo `cryptography>=42.0`; chưa kiểm chứng phiên bản CI thực tế ở môi trường này.

## Các bước đã thử nhưng bị chặn

- `python3 -m pytest -q -m network`: **2 errors + 1 failed**, cả ba tại `socket.socket(...)` với `PermissionError: [Errno 1] Operation not permitted`, trước khi bind localhost. Hai test HTTP và một test HTTPS vẫn là test bắt buộc trong CI; không có automatic skip hay mock thay mạng để giả vờ pass.
- Cài requirements/PyInstaller vào `.venv`: pip không lấy được qrcode (`No matching distribution found`). qrcode, Pillow, Tkinter và PyInstaller không có sẵn; không có local GUI/packaging evidence. Không thể cross-compile Windows exe bằng PyInstaller trên Linux.
- `gh auth status` không xác thực được; `gh api user` báo không kết nối `api.github.com`. GitHub connector đọc được profile nhưng tra `truongminhkhanng/phonedrop` trả 404, không cung cấp thao tác tạo repo. Không thể coi 404 là bằng chứng repo không tồn tại ở mọi nơi; nó chưa truy cập được qua connector.
- Đã chạy `gh repo create phonedrop --private --source=. --push`: thất bại với `error connecting to api.github.com`. Repo Git cục bộ đã init nhánh `main` và commit source. Chưa có remote được tạo, workflow run để watch hoặc artifact/release để tải. Không tạo tag phát hành trước khi test/build xanh.

## Ma trận yêu cầu bảo mật

✔ dưới đây nghĩa là **code + test logic/handler đã pass**, không có nghĩa toàn bộ ứng dụng/network/Windows đã được xác minh.

| Yêu cầu | Code | Bằng chứng đã chạy |
|---|---|---|
| ✔ Bind IP private cụ thể, cổng ngẫu nhiên | `lan_ipv4`, `PhoneDropServer`, GUI `(ip, 0)` | `test_lan_ip`, `test_server_refuses_public_wildcard_and_loopback_by_default`; bind thật chưa chạy được |
| ✔ QR token 16 byte, một lần, 120s, constant-time | `State._new_token/join/_matches/tick` | `test_token_one_use`, `test_token_expiry_and_auto_rotation`, `test_token_constant_time_comparison`, `test_simultaneous_token_consumption_is_atomic` |
| ✔ Session 32 byte, một phiên, IP, duyệt, 20 phút | `State.join/set_state/authorize` | `test_pending_wrong_ip_wrong_session_and_approval`, `test_session_expiry_not_extended_by_polling`, `test_monotonic_deadlines_ignore_system_wall_clock` |
| ✔ Duyệt desktop, timeout 60s, hộp thoại cũ vô hiệu | `State.set_state`, `app.show_approval` | `test_approval_deadline_and_stale_dialog`, `test_pending_upload_creates_no_files`; topmost/GUI chưa chạy được |
| ✔ Đúng ba route, không API đọc/chạy lệnh | `Handler.dispatch` | `test_only_three_routes`, `test_invalid_host_and_forwarded_ip`; review source |
| ✔ Basename, ký tự cấm, tên dành riêng, ≤150 ký tự | `safe_name` | `test_safe_name`, `test_safe_name_long`, `test_reserved_name_with_space` |
| ✔ Chặn các đuôi yêu cầu, checkbox tắt, bật phải xác nhận | `is_dangerous`, `begin_upload`, `change_executable_policy` | `test_dangerous_extensions` (34 đuôi), `test_executable_policy`, `test_executable_switch_requires_confirmation` |
| ✔ 5 GiB, bắt buộc Content-Length, đọc có giới hạn | `Handler.receive_upload`, `State.write_upload` | `test_upload_validation`, `test_duplicate_length_rejected`, `test_reads_exact_content_length`, `test_upload_size_guard_before_write` |
| ✔ `.part`, đủ byte mới công bố, không ghi đè | `begin_upload/finish_upload/publish_part` | `test_file_no_clobber_and_exact_bytes`, `test_short_body_cleans_part`, `test_zero_byte_file`, `test_no_clobber_if_file_created_during_publication` |
| ✔ Ngắt phiên thu hồi quyền và dọn file đang nhận | `State.rotate/close/_abort_upload` | `test_revoke_cancels_socket_and_part`, `test_expiry_cancels_in_progress_upload`, `test_rejection_rotation_shutdown` |
| ✔ Sai 10 lần khóa IP 5 phút | `State._check_block/_bad` | `test_ip_block_after_ten_failures_survives_rotation`, `test_invalid_session_also_counts`, `test_limiter_capacity_is_bounded` |
| ✔ Header an toàn, không lỗi chi tiết/token trong log | `Handler.reply/send_error/log_message` | `test_security_headers_and_no_secret_logs`, `test_storage_error_generic_no_traceback` |
| ✔ Chứng chỉ tự ký ngẫu nhiên/fingerprint và xóa key tạm | `create_tls_context` | `test_fresh_certificate_san_fingerprint_and_key_cleanup`, `test_certificate_failure_removes_private_key` |
| ✘ HTTP/HTTPS thực tế, fingerprint qua TLS, ngắt socket thật | `PhoneDropServer`, test `network` | Có test nhưng 3 test chưa pass vì sandbox cấm socket |
| ✘ Giao diện Windows, đóng gói, phát hành | `app.py`, `.github/workflows/build.yml` | Có smoke test trong exe/CI; chưa chạy được CI, chưa có `.exe` |

`/status` nhận đúng session/IP chưa duyệt trả **202 pending** để trang chờ hoạt động; **200 approved** chỉ khi duyệt. `/upload` luôn cần approved. Đây là cách giải quyết hai yêu cầu “trang chờ polling” và “kiểm tra trạng thái approved”, đã ghi rõ trong README và test handler.

## Cần môi trường có mạng/socket để xác minh tiếp

Chạy `python -m pytest -q` đầy đủ, tạo/push repo riêng `phonedrop`, dùng `gh run watch --exit-status`, đọc `gh run view --log-failed` nếu lỗi, sửa/push đến khi xanh. Khi main xanh mới push tag `v1.0.0`, theo dõi run của tag, tải artifact/release, kiểm tra `MZ`, kích thước/SHA-256 và chạy trên Windows. Tiếp đó kiểm tra điện thoại thật qua Wi-Fi/Ethernet, approval timeout và HTTPS/fingerprint. Không thay các bước đó bằng kết quả in-memory.

## Cập nhật repo đích

User chọn dùng repo có sẵn `truongminhkhanng/QRDrop`. Kết nối GitHub xác minh repo public với quyền push/admin, đọc được main và workflow. Dùng connector để đưa source vào nhánh `feature/phonedrop`, workflow riêng ở `.github/workflows/phonedrop.yml`; kiểm chứng CI đang tiếp tục. Lỗi gh terminal không đồng nghĩa connector không ghi được repo hiện có. Không tạo repo phonedrop riêng nữa.
