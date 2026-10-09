# PhoneDrop

Ứng dụng Windows dùng Python 3.12 + Tkinter để nhận file từ trình duyệt điện thoại qua Wi-Fi/LAN. Điện thoại không cần cài app; trang tiếng Việt, dark mode, không CDN, không truy cập Internet khi chuyển file.

## Trạng thái bản source này

Đã có mã ứng dụng, kiểm thử và workflow Windows. Xem `VERIFICATION.md` để biết chính xác phần đã chạy và phần bị môi trường chặn. Chỉ coi bản `.exe` được xác minh khi workflow **Test and build PhoneDrop** xanh, gồm cả smoke test chạy chính executable. Source chưa được chứng minh hoạt động trên điện thoại thật.

## Cách dùng trên Windows

1. Tải `PhoneDrop.exe` từ Release của repo hoặc giải nén artifact `PhoneDrop-Windows` trong Actions. Đối chiếu SHA-256 với `PhoneDrop.exe.sha256` bằng `Get-FileHash .\PhoneDrop.exe -Algorithm SHA256`.
2. Chạy app bằng tài khoản thường, không cần Administrator. Máy tính tự chọn IPv4 LAN và mở cổng ngẫu nhiên **chỉ trên IP đó**. IP được chọn hiện phía trên QR; nếu nhiều card mạng/VPN, chọn hoặc nhập IP của card Wi-Fi/Ethernet đúng rồi bấm **Kết nối lại**. Không có IP LAN hợp lệ thì app không mở listener.
3. Điện thoại kết nối cùng mạng nội bộ có thể truy cập máy tính. Máy tính cắm Ethernet vẫn dùng được nếu điện thoại Wi-Fi cùng mạng và router cho phép liên lạc giữa hai thiết bị.
4. Quét QR. Trang hiện **Đang chờ máy tính xác nhận**. Máy tính hiện cửa sổ trên cùng, gồm IP, User-Agent, **Cho phép / Từ chối**. Chỉ cho phép nếu bạn vừa quét. Quá 60 giây tự từ chối; đóng hộp thoại cũng là từ chối.
5. Sau khi cho phép, chọn nhiều file và bấm **Gửi file**. File gửi tuần tự; mỗi file có tiến trình và kết quả **Xong / Lỗi**. Giữ màn hình điện thoại và trang web hoạt động trong lúc gửi.
6. File vào `~/Downloads/PhoneDrop`. **Đổi thư mục** chọn thư mục đang tồn tại và hủy phiên cũ; **Mở thư mục** dùng trình quản lý file hệ điều hành. App không tự mở file nhận được. Danh sách trong app giữ 200 file gần nhất của lần chạy hiện tại.
7. **Tạo QR mới / Ngắt kết nối** thu hồi phiên ngay, đóng socket upload đang chạy và dọn `.part` đang sở hữu. File đã hoàn thành được giữ lại. QR mới sẵn sàng cho lần ghép nối tiếp; để ngừng listener hoàn toàn, đóng app.

QR dùng một lần, hết hạn sau 120 giây và tự đổi nếu chưa quét. Sau khi quét, QR được ẩn trong lúc chờ/đã duyệt. Phiên được duyệt sống tối đa 20 phút kể từ lúc duyệt; polling không gia hạn. Phiên hết hạn giữa lúc gửi sẽ hủy file chưa hoàn thành. Reload trang sau khi token đã dùng không khôi phục phiên: tạo/quét QR mới. Mỗi lần chỉ một phiên và một file đang ghi.

## HTTPS tùy chọn

Bật **HTTPS tự ký**. Thao tác này khởi động lại server, hủy phiên cũ, tạo khóa ECDSA P-256/chứng chỉ mới ngẫu nhiên và đổi QR. Chứng chỉ có IP SAN đúng IP LAN, dùng TLS từ 1.2; hiệu lực 2 ngày. Khóa riêng trên đĩa được xóa ngay sau khi nạp vào SSLContext; chứng chỉ tạm được dọn khi đóng server bình thường. Nếu giữ server quá 2 ngày, khởi động lại để có chứng chỉ mới.

Trình duyệt sẽ cảnh báo vì chứng chỉ tự ký. **Trước khi gửi**, mở chi tiết chứng chỉ trên điện thoại, tìm SHA-256 fingerprint và so sánh toàn bộ với ô fingerprint trên PC (có thể chọn/copy). Nếu khác hoặc điện thoại không cho xem đầy đủ fingerprint, đừng dùng nút bỏ qua cảnh báo một cách mù quáng. Một số trình duyệt di động không cho kiểm tra chứng chỉ/tiếp tục; trường hợp này HTTPS tùy chọn chưa dùng được trên trình duyệt đó. App không cài CA gốc hay sửa kho tin cậy hệ thống. Không cần và không nên cài chứng chỉ làm CA gốc.

Chứng chỉ/fingerprint đổi khi restart server hoặc đổi IP/chế độ HTTPS. Fingerprint chỉ đối chiếu tính đúng của chứng chỉ nếu bạn đọc trực tiếp từ PC tin cậy. HTTPS với chứng chỉ tự ký chưa đối chiếu không bảo vệ chắc chắn khỏi kẻ giả mạo PC.

## Bảo mật và giới hạn thực tế

- Token QR tạo bằng `secrets.token_urlsafe(16)` (128 bit), một lần/120 giây; so sánh bằng `secrets.compare_digest`. Session dùng `token_urlsafe(32)` (256 bit), gắn IP và trạng thái duyệt. IP/User-Agent có thể gây nhầm lẫn hoặc giả mạo; chúng không thay thế bí mật session.
- Mọi `/status` kiểm tra session và IP. **Ngoại lệ cần thiết cho giao diện chờ:** phiên đúng nhưng chưa duyệt nhận HTTP 202 với `pending`; chỉ `approved` nhận HTTP 200. `/upload` luôn đòi phiên đã duyệt. Không có API mạng nào để duyệt, thay thư mục hoặc bật nhận executable.
- Chỉ `GET /?t=...`, `GET /status`, `POST /upload`. Không đọc file, liệt kê thư mục, chạy lệnh hay phục vụ source. Host phải đúng IP:cổng; Origin nếu có phải đúng; upload bắt buộc Origin đúng và session ở header. Không tin `X-Forwarded-For`; không CORS. CSP nonce, chống nhúng iframe và không chèn tên file bằng `innerHTML`.
- Tên file lấy basename cho cả `/` và `\`, chuẩn hóa Unicode, thay ký tự cấm/control/bidi, xử lý tên thiết bị Windows, giới hạn 150 ký tự và 240 byte UTF-8. Đuôi file được giữ khi cắt. Không cho đường dẫn từ điện thoại quyết định thư mục ghi.
- Mặc định chặn: `.exe .msi .bat .cmd .com .scr .ps1 .psm1 .vbs .vbe .js .jse .wsf .wsh .jar .lnk .dll .reg .hta .cpl .msc .pif .appx .msix .sys`; thêm `.appxbundle .msixbundle .msp .mst .psd1 .scf .url .website .gadget`. Không phân biệt hoa/thường, chặn cả đuôi nguy hiểm bên trong tên kép. Checkbox **Cho phép file thực thi - NGUY HIỂM** mặc định tắt, bật cần xác nhận và hủy phiên cũ.
- Tối đa 5 GiB (5 × 1024³ byte)/file. Bắt buộc một `Content-Length` hợp lệ, không chunked encoding, không đọc quá độ dài khai báo. Stream mỗi lần tối đa 256 KiB. File 0 byte hợp lệ. Không có quota tổng phiên; người đã được duyệt có thể gửi nhiều file làm đầy ổ đĩa.
- Tên staging ngẫu nhiên `.phonedrop-….part`, tạo exclusive. Chỉ công bố sau khi đủ byte và flush/fsync. Windows dùng rename không ghi đè; Linux dùng hard-link exclusive rồi xóa staging. File trùng tên thêm ` (1)`, ` (2)`… Không dùng `os.replace`. Dọn đúng `.part` thuộc upload hiện tại, không xóa file không liên quan. Nếu app/OS bị kill hoặc mất điện, `.part` có thể còn lại; đóng app rồi tự xóa file chưa hoàn thành sau khi kiểm tra.
- 10 lỗi token/session từ một IP trong cửa sổ hoạt động 5 phút khóa IP đó 5 phút; tạo QR mới không xóa khóa. Polling hợp lệ không tính lỗi. Bảng tối đa 4096 IP; khi đầy thì từ chối lỗi mới đến khi có mục hết hạn. Các thiết bị dùng chung IP có thể bị ảnh hưởng cùng nhau.
- Tối đa 12 kết nối xử lý đồng thời; timeout chờ dữ liệu header 10 giây, upload 15 giây; phiên có hạn chót tuyệt đối theo monotonic clock. Không có cam kết chống mọi kiểu DoS trên LAN.
- Header `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` trên phản hồi; không trả stack trace. Tắt request logging để URL/session không vào log. Token chỉ trong QR/trang ghép nối; session chỉ trong RAM/page script/header API, không ghi disk/cookie/localStorage. JavaScript xóa query token khỏi history của trang sau khi mở; không thể đảm bảo ứng dụng quét QR/trình duyệt không giữ bản sao URL.
- **HTTP không mã hóa**: thiết bị trong mạng có thể nghe lén token/file hoặc sửa dữ liệu. Chỉ dùng mạng tin cậy; không forward port, không mở ra Internet, không UPnP. Chặn đuôi chỉ là lớp phòng vệ: file đổi đuôi, archive, tài liệu có macro hoặc nội dung khai thác lỗ hổng vẫn có thể nguy hiểm. App không antivirus, không kiểm tra hash end-to-end, không xử lý hay tự mở file.
- Không đảm bảo “không bị hack”. Phần mềm độc hại đã chạy cùng tài khoản PC, thư mục do tiến trình cục bộ khác kiểm soát và admin là ngoài phạm vi bảo vệ. Dùng thư mục local do bạn kiểm soát; filesystem thiếu thao tác publish an toàn sẽ báo lỗi thay vì ghi đè.

`http.server` chỉ cung cấp kiểm tra bảo mật cơ bản; ứng dụng bổ sung kiểm tra giao thức ở `core.py`, chỉ dành cho LAN riêng theo yêu cầu. Tham khảo [tài liệu Python](https://docs.python.org/3.12/library/http.server.html) và [tài liệu chứng chỉ cryptography](https://cryptography.io/en/latest/x509/tutorial/).

## Firewall, SmartScreen, kết nối

- Nếu Windows hỏi Firewall, chỉ cho phép **Private networks**, không chọn Public. Không tắt toàn bộ Firewall. Cổng ngẫu nhiên đổi sau mỗi lần mở nên rule theo ứng dụng là phù hợp; chính sách công ty có thể cần IT cho phép.
- Nếu QR không mở: kiểm tra app đang chạy, đúng IP của card mạng, hai thiết bị truy cập nhau, guest Wi-Fi/client isolation, VPN và Firewall. Mobile data hoặc mạng Wi-Fi khác không dùng được với bản LAN này. Bind một IP cụ thể không thay thế Firewall và không chứng minh client thuộc cùng LAN.
- `.exe` chưa được ký số. SmartScreen có thể cảnh báo phần mềm chưa phổ biến. Chỉ chạy bản do bạn tự build hoặc tải từ repo tin cậy và kiểm tra checksum. Không vô hiệu hóa SmartScreen/antivirus trên máy. Chữ ký số cần chứng chỉ ký riêng, không có trong repo.
- Progress 100% có thể mới là dữ liệu đã gửi từ điện thoại; phải chờ **Xong** từ server. Nếu mạng mất sau khi PC đã lưu nhưng trước phản hồi, kiểm tra danh sách/thư mục PC trước khi gửi lại để tránh tạo bản sao.

## Chạy từ source và kiểm thử

Windows: cài Python 3.12 từ python.org với Tcl/Tk được chọn.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt pytest pyinstaller
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python app.py
```

Linux (test headless không cần Tkinter, qrcode, Pillow):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
```

`core.py` không import GUI. `app.py` chỉ import Tkinter/Pillow/qrcode khi khởi chạy giao diện. HTTPS dùng `cryptography` với import lazy. Muốn chạy GUI Linux cần Tcl/Tk, ví dụ package distro `python3-tk`, và graphical display. Mục tiêu phân phối chính là Windows.

`pytest -q` mặc định chạy **tất cả** test, gồm server HTTP và HTTPS thật ở cổng ngẫu nhiên localhost. Socket bị môi trường cấm sẽ fail, không tự skip để giả vờ xanh. Có thể dùng `python -m pytest -q -m "not network"` để kiểm tra phần logic/handler khi bị giới hạn; kết quả đó không chứng minh LAN/E2E.

## Build Windows và GitHub Actions

Chạy trên Windows (PyInstaller không cross-compile Windows exe từ Linux):

```powershell
.\.venv\Scripts\pyinstaller --onefile --windowed --name PhoneDrop app.py
```

Kết quả `dist/PhoneDrop.exe`. Không cần Python trên máy người dùng. Có thể thử packaged smoke test:

```powershell
Start-Process -Wait .\dist\PhoneDrop.exe -ArgumentList '--self-test', 'smoke-result.json'
Get-Content smoke-result.json
```

Workflow `.github/workflows/build.yml` trigger push `main`, tag `v*`, hoặc `workflow_dispatch`. Hai job test Linux/Windows dùng Python 3.12 phải xanh trước build trên `windows-latest`. Job build cài requirements + PyInstaller, build đúng lệnh trên, chạy executable để xác minh Tk, QR/Pillow, TLS và upload HTTP localhost, kiểm tra magic `MZ`, kích thước 5–250 MiB, tạo SHA-256 và upload artifact. Tag `v*` chạy release job với `contents: write`, dùng `softprops/action-gh-release@v2`, đính kèm exe/checksum từ đúng artifact đã test. Release trong repo private chỉ người có quyền repo truy cập được. [Tài liệu trigger Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Repo QRDrop dùng chung

Theo yêu cầu cập nhật, source PhoneDrop nằm trong thư mục `phonedrop/` của [repo QRDrop](https://github.com/truongminhkhanng/QRDrop/tree/feature/phonedrop/phonedrop). Workflow chạy thật là `.github/workflows/phonedrop.yml` ở **gốc repo QRDrop**, với working directory `phonedrop`. File `phonedrop/.github/workflows/build.yml` là cấu hình khi tách PhoneDrop thành repo độc lập; GitHub không chạy workflow nằm trong thư mục con.

Clone nhánh và chạy test:

```bash
git clone --branch feature/phonedrop https://github.com/truongminhkhanng/QRDrop.git
cd QRDrop/phonedrop
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

Workflow PhoneDrop chạy khi push `main`, `feature/phonedrop`, `release/phonedrop-v1.0.0` có thay đổi source/workflow PhoneDrop, khi push tag `phonedrop-v*`, hoặc workflow_dispatch. Build và smoke test phải xanh trước khi phát hành. Nhánh `release/phonedrop-v1.0.0` chỉ được tạo từ source đã test để kích hoạt test/build lại và tạo release `phonedrop-v1.0.0`. Tag có tiền tố để phân biệt với release QRDrop đã có. Repo hiện public nên source và bản phát hành PhoneDrop có thể truy cập công khai.

```bash
gh run list --repo truongminhkhanng/QRDrop --workflow phonedrop.yml --limit 5
gh run watch --repo truongminhkhanng/QRDrop --exit-status
gh run view --repo truongminhkhanng/QRDrop --log-failed
gh run download --repo truongminhkhanng/QRDrop --name PhoneDrop-Windows --dir downloaded-artifact
gh release download phonedrop-v1.0.0 --repo truongminhkhanng/QRDrop --pattern 'PhoneDrop.exe*' --dir downloaded-release
```

Artifact có cấu trúc `dist/PhoneDrop.exe`, `dist/PhoneDrop.exe.sha256` và `smoke-result.json`; release đính kèm trực tiếp `PhoneDrop.exe`. Kiểm tra SHA-256 và dung lượng file tải về. Không commit token GitHub, khóa ký, file nhận hay chứng chỉ riêng.

Trước khi công bố ứng dụng đã hoạt động ngoài thực tế, cần dùng điện thoại Android/iPhone thật: chờ/duyệt/từ chối/timeout, truyền nhiều file, file rỗng, file trùng, file nguy hiểm, ngắt giữa upload, Wi-Fi ↔ Ethernet, HTTPS/fingerprint và thông báo Firewall. CI loopback không thay thế kiểm thử thiết bị này.
