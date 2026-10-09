"""PhoneDrop LAN protocol and storage. No GUI imports; no remote control APIs."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import queue
import re
import secrets
import socket
import ssl
import tempfile
import threading
import time
import unicodedata
from urllib.parse import parse_qs, unquote, urlsplit

MAX_FILE_SIZE = 5 * 1024**3
CHUNK_SIZE = 256 * 1024
TOKEN_SECONDS = 120
APPROVAL_SECONDS = 60
SESSION_SECONDS = 20 * 60
BLOCK_SECONDS = 300
MAX_CLIENTS = 12
DANGEROUS_EXTENSIONS = frozenset('''
.exe .msi .bat .cmd .com .scr .ps1 .psm1 .vbs .vbe .js .jse .wsf .wsh
.jar .lnk .dll .reg .hta .cpl .msc .pif .appx .msix .sys
.appxbundle .msixbundle .msp .mst .psd1 .scf .url .website .gadget
'''.split())
_RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)


def safe_name(value: str) -> str:
    """Portable Windows basename, <=150 characters and <=240 UTF-8 bytes."""
    value = unicodedata.normalize('NFKC', value).replace('\\', '/').rsplit('/', 1)[-1]
    value = ''.join('_' if c in '<>:"/\\|?*' or unicodedata.category(c).startswith('C') else c
                    for c in value).strip(' .') or 'file'
    if _RESERVED.match(value) or _RESERVED.fullmatch(value.split('.', 1)[0].rstrip(' .')):
        value = '_' + value
    stem, ext = os.path.splitext(value)
    # Preserve the final extension so shortening cannot turn an executable into text.
    if len(ext) > 30:
        stem, ext = value, ''
    stem = stem[:150 - len(ext)]
    while len((stem + ext).encode('utf-8')) > 240:
        stem = stem[:-1]
    return (stem + ext).rstrip(' .') or 'file'


def is_dangerous(name: str) -> bool:
    # Check each suffix, including disguised double extensions and Windows trailing dots.
    normalized = unicodedata.normalize('NFKC', name).replace('\\', '/').rsplit('/', 1)[-1]
    return any('.' + piece.strip(' .').casefold() in DANGEROUS_EXTENSIONS
               for piece in normalized.split('.')[1:])


def unique_path(folder: Path, name: str) -> Path:
    """Suggest an unused filename. Publication still performs an atomic no-clobber operation."""
    name = safe_name(name)
    stem, ext = os.path.splitext(name)
    for index in range(10000):
        candidate = folder / (name if index == 0 else f'{stem} ({index}){ext}')
        if not os.path.lexists(candidate):
            return candidate
    raise OSError('Too many filename collisions')


def publish_part(part: Path, folder: Path, name: str) -> Path:
    for _ in range(10000):
        target = unique_path(folder, name)
        try:
            if os.name == 'nt':
                # Windows rename fails if destination exists. Never use os.replace.
                os.rename(part, target)
            else:
                # POSIX rename overwrites: use atomic exclusive link + remove staging name.
                os.link(part, target)
                part.unlink()
            return target
        except FileExistsError:
            continue
    raise OSError('Too many filename collisions')


class RequestError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Session:
    sid: str = field(repr=False)
    ip: str
    user_agent: str
    pending_until: float
    status: str = 'pending'
    approved_until: float = 0


@dataclass
class Upload:
    sid: str = field(repr=False)
    ip: str
    name: str
    folder: Path
    part: Path
    file: object = field(repr=False)
    connection: object = field(repr=False)
    size: int = 0
    closed: bool = False


class State:
    def __init__(self, folder: Path, *, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.folder = Path(folder).expanduser().resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.allow_executables = False
        self.session: Session | None = None
        self.token = ''
        self.token_until = 0.0
        self.enabled = True
        self.failures: OrderedDict[str, tuple[int, float, float]] = OrderedDict()
        self.events: queue.Queue = queue.Queue(maxsize=256)
        self.upload: Upload | None = None
        self.rotate()

    def emit(self, kind, data):
        try:
            self.events.put_nowait((kind, data))
        except queue.Full:
            # UI history is bounded; authorization never depends on receiving an event.
            pass

    def _new_token(self):
        self.token = secrets.token_urlsafe(16)
        self.token_until = self.clock() + TOKEN_SECONDS

    def _abort_upload(self):
        upload = self.upload
        if upload is None:
            return
        self.upload = None
        upload.closed = True
        if upload.connection is not None:
            try:
                upload.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            upload.file.close()
        finally:
            try:
                upload.part.unlink(missing_ok=True)
            except OSError:
                self.emit('error', 'Không thể xóa file .part; hãy kiểm tra thư mục nhận.')

    def rotate(self):
        with self.lock:
            self.session = None
            self._abort_upload()
            self._new_token()

    def close(self):
        with self.lock:
            self.enabled = False
            self.session = None
            self.token = ''
            self._abort_upload()

    def tick(self):
        with self.lock:
            now = self.clock()
            if not self.enabled:
                return
            if self.session:
                deadline = (self.session.pending_until if self.session.status == 'pending'
                            else self.session.approved_until)
                if now >= deadline:
                    self.rotate()
            elif now >= self.token_until:
                self._new_token()

    def _check_block(self, ip):
        now = self.clock()
        record = self.failures.get(ip)
        if record and record[1] > now:
            raise RequestError(429, 'Thử lại sau 5 phút.')
        if record and now >= record[2]:
            del self.failures[ip]

    def _bad(self, ip):
        self._check_block(ip)
        now = self.clock()
        if ip not in self.failures and len(self.failures) >= 4096:
            for key in list(self.failures):
                if self.failures[key][2] <= now:
                    del self.failures[key]
            if len(self.failures) >= 4096:
                raise RequestError(429, 'Máy tính đang bận. Vui lòng thử lại sau.')
        count = self.failures.get(ip, (0, 0, 0))[0] + 1
        self.failures[ip] = (count, now + BLOCK_SECONDS if count >= 10 else 0,
                             now + BLOCK_SECONDS)
        if count >= 10:
            raise RequestError(429, 'Thử lại sau 5 phút.')
        raise RequestError(403, 'Yêu cầu không hợp lệ hoặc đã hết hạn.')

    @staticmethod
    def _matches(a, b):
        return isinstance(a, str) and a.isascii() and secrets.compare_digest(a, b)

    def join(self, token: str, ip: str, user_agent: str) -> Session:
        with self.lock:
            self._check_block(ip)
            self.tick()
            if (not self.enabled or not self.token or self.session is not None
                    or not self._matches(token, self.token)):
                self._bad(ip)
            self.token = ''  # Consume before returning the page or showing the prompt.
            clean_agent = ''.join(c for c in user_agent if not unicodedata.category(c).startswith('C'))[:240]
            self.session = Session(secrets.token_urlsafe(32), ip, clean_agent,
                                   self.clock() + APPROVAL_SECONDS)
            return self.session

    def set_state(self, sid: str, status: str) -> bool:
        """Desktop-only approval; stale dialogs cannot approve a newer request."""
        if status not in ('approved', 'denied'):
            raise ValueError('Invalid state')
        with self.lock:
            self.tick()
            if not self.session or not self._matches(sid, self.session.sid) or self.session.status != 'pending':
                return False
            if status == 'denied':
                self.rotate()
            else:
                self.session.status = 'approved'
                self.session.approved_until = self.clock() + SESSION_SECONDS
            return True

    def authorize(self, sid: str, ip: str, *, pending_ok=False) -> str:
        with self.lock:
            self._check_block(ip)
            self.tick()
            if (not self.enabled or not self.session or self.session.ip != ip
                    or not self._matches(sid, self.session.sid)):
                self._bad(ip)
            if self.session.status != 'approved' and not pending_ok:
                raise RequestError(403, 'Máy tính chưa cho phép nhận file.')
            return self.session.status

    def snapshot(self):
        with self.lock:
            self.tick()
            session = self.session
            return {'token': self.token, 'remaining': max(0, int(self.token_until - self.clock())),
                    'session': None if session is None else
                    (session.sid, session.ip, session.user_agent, session.status,
                     max(0, int(session.pending_until - self.clock())))}

    def set_folder(self, folder: Path):
        path = Path(folder).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise OSError('Not a directory')
        with self.lock:
            self.rotate()
            self.folder = path

    def set_allow_executables(self, allowed: bool):
        with self.lock:
            self.rotate()  # Revoke grants whenever the local security policy changes.
            self.allow_executables = bool(allowed)

    def begin_upload(self, sid, ip, name, connection=None):
        with self.lock:
            self.authorize(sid, ip)
            clean = safe_name(name)
            if not self.allow_executables and (is_dangerous(name) or is_dangerous(clean)):
                raise RequestError(415, 'Loại file này bị chặn trên máy tính.')
            if self.upload is not None:
                raise RequestError(409, 'Đang nhận một file khác.')
            fd, part = tempfile.mkstemp(prefix='.phonedrop-', suffix='.part', dir=self.folder)
            try:
                file = os.fdopen(fd, 'wb')
            except BaseException:
                os.close(fd)
                Path(part).unlink(missing_ok=True)
                raise
            self.upload = Upload(sid, ip, clean, self.folder, Path(part), file, connection)
            return self.upload

    def write_upload(self, upload, chunk):
        with self.lock:
            if upload.closed or self.upload is not upload:
                raise RequestError(403, 'Phiên đã bị ngắt.')
            self.authorize(upload.sid, upload.ip)
            if upload.size + len(chunk) > MAX_FILE_SIZE:
                raise RequestError(413, 'File vượt quá 5 GiB.')
            upload.file.write(chunk)
            upload.size += len(chunk)

    def finish_upload(self, upload, expected):
        with self.lock:
            if upload.closed or self.upload is not upload:
                raise RequestError(403, 'Phiên đã bị ngắt.')
            self.authorize(upload.sid, upload.ip)
            if upload.size != expected:
                raise RequestError(400, 'File chưa được nhận đầy đủ.')
            upload.file.flush()
            os.fsync(upload.file.fileno())
            upload.file.close()
            target = publish_part(upload.part, upload.folder, upload.name)
            upload.closed = True
            self.upload = None
            self.emit('received', (target.name, expected))
            return target.name

    def cancel_upload(self, upload):
        with self.lock:
            if self.upload is upload:
                self._abort_upload()


def lan_ipv4(value: str) -> bool:
    try:
        address = ipaddress.IPv4Address(value)
        return any(address in ipaddress.IPv4Network(net) for net in
                   ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    except ipaddress.AddressValueError:
        return False


def discover_lan_ips():
    found = []
    # UDP connect only asks the OS for its selected local route; sends no packet.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.168.255.254', 9))
            found.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        found.extend(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    return list(dict.fromkeys(ip for ip in found if lan_ipv4(ip)))


class PhoneDropServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 12

    def __init__(self, address, state, page, *, tls_context=None, allow_loopback=False):
        ip = address[0]
        if not lan_ipv4(ip) and not (allow_loopback and ip == '127.0.0.1'):
            raise ValueError('Only a selected private IPv4 address is allowed')
        self.state = state
        self.page = page
        self.tls_context = tls_context
        self.slots = threading.BoundedSemaphore(MAX_CLIENTS)
        self.stopped = threading.Event()
        self.connections = set()
        self.connection_lock = threading.Lock()
        super().__init__(address, Handler)
        self.host = f'{ip}:{self.server_address[1]}'
        self.origin = ('https' if tls_context else 'http') + '://' + self.host
        self.janitor = threading.Thread(target=self._expire, daemon=True)
        self.janitor.start()

    def _expire(self):
        while not self.stopped.wait(0.25):
            self.state.tick()

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        with self.connection_lock:
            self.connections.add(request)
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self.connection_lock:
                self.connections.discard(request)
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        raw = request
        try:
            request.settimeout(10)
            if self.tls_context:
                request = self.tls_context.wrap_socket(request, server_side=True, do_handshake_on_connect=False)
                with self.connection_lock:
                    self.connections.discard(raw)
                    self.connections.add(request)
                request.do_handshake()
            self.finish_request(request, client_address)
        except (OSError, ssl.SSLError):
            pass
        except Exception:
            self.state.emit('error', 'Không thể xử lý yêu cầu mạng.')
        finally:
            self.shutdown_request(request)
            with self.connection_lock:
                self.connections.discard(request)
                self.connections.discard(raw)
            self.slots.release()

    def server_close(self):
        self.stopped.set()
        self.state.close()
        with self.connection_lock:
            for connection in list(self.connections):
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        super().server_close()
        if hasattr(self, 'janitor'):
            self.janitor.join(timeout=1)

    def handle_error(self, request, client_address):
        self.state.emit('error', 'Không thể xử lý kết nối.')


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'  # One request per connection; no unread-body reuse.
    server_version = 'PhoneDrop'
    sys_version = ''

    def log_message(self, format, *args):
        pass  # Never log URL tokens, session headers, or raw untrusted request data.

    def reply(self, code, data, *, html=False, nonce=None):
        body = data.encode('utf-8') if html else json.dumps(data, ensure_ascii=True).encode('ascii')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8' if html else 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        policy = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        if nonce:
            policy += f"; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; img-src 'self' data:"
        self.send_header('Content-Security-Policy', policy)
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        if self.command != 'HEAD':
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler errors (including invalid verbs) must not echo paths.
        self.reply(404 if code == 501 else code, {'error': 'Yêu cầu không hợp lệ.'})

    def one_header(self, name, default=''):
        values = self.headers.get_all(name, [])
        if len(values) > 1:
            raise RequestError(400, 'Header không hợp lệ.')
        return values[0] if values else default

    def guard(self):
        host = self.one_header('Host')
        if host != self.server.host:
            raise RequestError(403, 'Yêu cầu không hợp lệ.')
        origin = self.one_header('Origin')
        if origin and origin != self.server.origin:
            raise RequestError(403, 'Yêu cầu không hợp lệ.')
        if self.one_header('Sec-Fetch-Site') == 'cross-site':
            raise RequestError(403, 'Yêu cầu không hợp lệ.')
        with self.server.state.lock:
            self.server.state._check_block(self.client_address[0])

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def dispatch(self, method):
        try:
            self.guard()
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise RequestError(404, 'Không tìm thấy.')
            if method == 'GET' and parsed.path == '/':
                if len(parsed.query) > 256:
                    raise RequestError(400, 'Yêu cầu không hợp lệ.')
                query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=4)
                token = query.get('t', [])
                if set(query) != {'t'} or len(token) != 1:
                    token = ['']
                session = self.server.state.join(token[0], self.client_address[0], self.one_header('User-Agent'))
                nonce = secrets.token_urlsafe(18)
                page = self.server.page.replace('__NONCE__', nonce).replace('__SESSION_JSON__', json.dumps(session.sid))
                self.reply(200, page, html=True, nonce=nonce)
            elif method == 'GET' and parsed.path == '/status' and not parsed.query:
                status = self.server.state.authorize(self.one_header('X-Session'), self.client_address[0], pending_ok=True)
                self.reply(200 if status == 'approved' else 202, {'status': status})
            elif method == 'POST' and parsed.path == '/upload' and not parsed.query:
                self.receive_upload()
            else:
                raise RequestError(404, 'Không tìm thấy.')
        except RequestError as exc:
            self.reply(exc.code, {'error': exc.message})
        except (ValueError, UnicodeError):
            self.reply(400, {'error': 'Yêu cầu không hợp lệ.'})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError:
            self.reply(500, {'error': 'Không thể nhận file. Hãy kiểm tra máy tính.'})
        except Exception:
            self.reply(500, {'error': 'Không thể xử lý yêu cầu.'})

    def receive_upload(self):
        state = self.server.state
        ip = self.client_address[0]
        sid = self.one_header('X-Session')
        state.authorize(sid, ip)
        if self.one_header('Origin') != self.server.origin:
            raise RequestError(403, 'Yêu cầu không hợp lệ.')
        if self.headers.get_all('Transfer-Encoding') or self.headers.get_all('Expect'):
            raise RequestError(400, 'Kiểu truyền không được hỗ trợ.')
        raw_length = self.one_header('Content-Length')
        if not raw_length:
            raise RequestError(411, 'Thiếu dung lượng file.')
        if not re.fullmatch(r'[0-9]{1,12}', raw_length):
            raise RequestError(400, 'Dung lượng không hợp lệ.')
        length = int(raw_length)
        if length > MAX_FILE_SIZE:
            raise RequestError(413, 'File vượt quá 5 GiB.')
        if self.one_header('Content-Type') != 'application/octet-stream':
            raise RequestError(415, 'Định dạng gửi không được hỗ trợ.')
        encoded = self.one_header('X-Filename')
        if not encoded or len(encoded) > 4096:
            raise RequestError(400, 'Tên file không hợp lệ.')
        name = unquote(encoded, encoding='utf-8', errors='strict')
        upload = state.begin_upload(sid, ip, name, self.connection)
        try:
            self.connection.settimeout(15)
            remaining = length
            while remaining:
                state.authorize(sid, ip)
                data = self.rfile.read1(min(CHUNK_SIZE, remaining))
                if not data:
                    raise RequestError(400, 'Kết nối ngắt trước khi nhận đủ file.')
                state.write_upload(upload, data)
                remaining -= len(data)
            saved = state.finish_upload(upload, length)
            self.reply(201, {'name': saved, 'size': length})
        finally:
            state.cancel_upload(upload)
