import io
import json
from pathlib import Path
import secrets
import socket
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

from app import MOBILE_HTML
from core import (APPROVAL_SECONDS, BLOCK_SECONDS, DANGEROUS_EXTENSIONS, Handler,
                  MAX_FILE_SIZE, PhoneDropServer, RequestError, SESSION_SECONDS,
                  State, TOKEN_SECONDS, is_dangerous, lan_ipv4, publish_part,
                  safe_name, unique_path)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def state(tmp_path):
    obj = State(tmp_path, clock=Clock())
    yield obj
    obj.close()


def approve(state, ip='127.0.0.1'):
    session = state.join(state.token, ip, 'Test phone')
    assert state.set_state(session.sid, 'approved')
    return session.sid


@pytest.mark.parametrize(('raw', 'expected'), [('../../x.txt', 'x.txt'),
    ('C:\\Windows\\a.dll', 'a.dll'), ('con.txt', '_con.txt'), ('', 'file'),
    ('NUL', '_NUL'), ('COM9.png', '_COM9.png'), ('LPT1', '_LPT1'),
    ('bad<>:"|?*.txt', 'bad_______.txt'), ('..', 'file'), (' a.txt. ', 'a.txt'),
    ('COM¹.txt', '_COM1.txt'), ('a\u202etxt.exe', 'a_txt.exe')])
def test_safe_name(raw, expected):
    assert safe_name(raw) == expected


@pytest.mark.parametrize('raw', ['a' * 1000 + '.exe', 'ắ' * 1000 + '.txt', '😀' * 1000 + '.txt'])
def test_safe_name_long(raw):
    result = safe_name(raw)
    assert len(result) <= 150
    assert len(result.encode('utf-8')) <= 240
    assert result.endswith(Path(raw).suffix)


@pytest.mark.parametrize('ext', sorted(DANGEROUS_EXTENSIONS))
def test_dangerous_extensions(ext):
    assert is_dangerous('file' + ext)
    assert is_dangerous('file' + ext.upper() + ' .')
    assert is_dangerous('file' + ext + '.txt')


def test_token_one_use(state):
    token = state.token
    session = state.join(token, '1', 'agent')
    assert len(token) == 22 and len(session.sid) == 43
    with pytest.raises(RequestError):
        state.join(token, '1', 'agent')
    assert state.session is session


def test_token_expiry_and_auto_rotation(state):
    old = state.token
    state.clock.advance(TOKEN_SECONDS)
    with pytest.raises(RequestError):
        state.join(old, '1', '')
    assert state.token and state.token != old


def test_token_constant_time_comparison(state, monkeypatch):
    calls = []
    original = secrets.compare_digest
    monkeypatch.setattr(secrets, 'compare_digest', lambda a, b: calls.append((len(a), len(b))) or original(a, b))
    approve(state)
    assert calls


def test_pending_wrong_ip_wrong_session_and_approval(state):
    session = state.join(state.token, '1', '')
    assert state.authorize(session.sid, '1', pending_ok=True) == 'pending'
    for sid, ip in [(session.sid, '2'), ('wrong', '1'), (session.sid, '1')]:
        with pytest.raises(RequestError):
            state.authorize(sid, ip)
    assert state.set_state(session.sid, 'approved')
    assert state.authorize(session.sid, '1') == 'approved'
    with pytest.raises(RequestError):
        state.authorize(session.sid, '2', pending_ok=True)


def test_approval_deadline_and_stale_dialog(state):
    session = state.join(state.token, '1', '')
    state.clock.advance(APPROVAL_SECONDS)
    assert not state.set_state(session.sid, 'approved')
    newer = state.join(state.token, '1', '')
    assert not state.set_state(session.sid, 'approved')
    assert newer.status == 'pending'


def test_session_expiry_not_extended_by_polling(state):
    sid = approve(state)
    state.clock.advance(SESSION_SECONDS - 1)
    assert state.authorize(sid, '127.0.0.1') == 'approved'
    state.clock.advance(1)
    with pytest.raises(RequestError):
        state.authorize(sid, '127.0.0.1')
    assert state.session is None


def test_rejection_rotation_shutdown(state):
    pending = state.join(state.token, '1', '')
    assert state.set_state(pending.sid, 'denied')
    with pytest.raises(RequestError):
        state.authorize(pending.sid, '1')
    sid = approve(state)
    state.rotate()
    with pytest.raises(RequestError):
        state.authorize(sid, '127.0.0.1')
    state.close()
    with pytest.raises(RequestError):
        state.join('', '1', '')


def test_ip_block_after_ten_failures_survives_rotation(state):
    for i in range(10):
        with pytest.raises(RequestError) as exc:
            state.join('wrong', 'bad', '')
        assert exc.value.code == (429 if i == 9 else 403)
    state.rotate()
    with pytest.raises(RequestError) as exc:
        state.join(state.token, 'bad', '')
    assert exc.value.code == 429
    session = state.join(state.token, 'other', '')
    assert session.ip == 'other'
    state.rotate()
    state.clock.advance(BLOCK_SECONDS)
    state.tick()
    assert state.join(state.token, 'bad', '').ip == 'bad'


def test_invalid_session_also_counts(state):
    approve(state)
    for i in range(10):
        with pytest.raises(RequestError) as exc:
            state.authorize('invalid', '127.0.0.1', pending_ok=True)
    assert exc.value.code == 429


def test_limiter_capacity_is_bounded(state):
    for i in range(4097):
        with pytest.raises(RequestError):
            state.join('wrong', str(i), '')
    assert len(state.failures) == 4096


def test_file_no_clobber_and_exact_bytes(state):
    sid = approve(state)
    for name, body in [('x.txt', b'first'), ('x.txt', b'\x00\xffsecond')]:
        upload = state.begin_upload(sid, '127.0.0.1', '../../' + name)
        assert upload.part.suffix == '.part'
        state.write_upload(upload, body)
        state.finish_upload(upload, len(body))
    assert (state.folder / 'x.txt').read_bytes() == b'first'
    assert (state.folder / 'x (1).txt').read_bytes() == b'\x00\xffsecond'
    assert not list(state.folder.glob('*.part'))


def test_atomic_publication_collision(tmp_path, monkeypatch):
    part = tmp_path / 'tmp.part'
    part.write_bytes(b'new')
    target = tmp_path / 'a.txt'
    target.write_bytes(b'old')
    assert publish_part(part, tmp_path, 'a.txt').name == 'a (1).txt'
    assert target.read_bytes() == b'old'


def test_pending_upload_creates_no_files(state):
    session = state.join(state.token, '1', '')
    with pytest.raises(RequestError):
        state.begin_upload(session.sid, '1', 'normal.txt')
    assert list(state.folder.iterdir()) == []


def test_executable_policy(state):
    sid = approve(state)
    with pytest.raises(RequestError) as exc:
        state.begin_upload(sid, '127.0.0.1', 'bad.EXE. ')
    assert exc.value.code == 415
    assert not list(state.folder.iterdir())
    state.set_allow_executables(True)
    with pytest.raises(RequestError):
        state.authorize(sid, '127.0.0.1')
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'tool.exe')
    state.write_upload(upload, b'MZ')
    state.finish_upload(upload, 2)
    assert (state.folder / 'tool.exe').read_bytes() == b'MZ'


def test_revoke_cancels_socket_and_part(state):
    sid = approve(state)
    calls = []
    connection = SimpleNamespace(shutdown=lambda how: calls.append(how))
    upload = state.begin_upload(sid, '127.0.0.1', 'x.txt', connection)
    state.write_upload(upload, b'partial')
    state.rotate()
    assert calls == [socket.SHUT_RDWR]
    assert upload.closed and not upload.part.exists()
    with pytest.raises(RequestError):
        state.write_upload(upload, b'late')
    with pytest.raises(RequestError):
        state.finish_upload(upload, 7)
    assert not (state.folder / 'x.txt').exists()


def test_incomplete_and_concurrent_upload(state):
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'x.txt')
    state.write_upload(upload, b'a')
    with pytest.raises(RequestError):
        state.begin_upload(sid, '127.0.0.1', 'y.txt')
    with pytest.raises(RequestError):
        state.finish_upload(upload, 2)
    state.cancel_upload(upload)
    assert not list(state.folder.iterdir())


def test_zero_byte_file(state):
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'empty.txt')
    assert state.finish_upload(upload, 0) == 'empty.txt'
    assert (state.folder / 'empty.txt').stat().st_size == 0


def test_change_folder_cancels_session_and_pins_directory(state, tmp_path):
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'x.txt')
    destination = tmp_path / 'new'
    destination.mkdir()
    state.set_folder(destination)
    assert upload.closed and state.folder == destination
    assert not upload.part.exists()


@pytest.mark.parametrize('ip,valid', [('192.168.1.2', True), ('10.0.0.2', True), ('172.16.2.1', True),
    ('0.0.0.0', False), ('127.0.0.1', False), ('8.8.8.8', False), ('169.254.1.2', False), ('::', False)])
def test_lan_ip(ip, valid):
    assert lan_ipv4(ip) is valid


class MemoryConnection:
    """Real HTTP handler using in-memory streams; not a network/E2E substitute."""
    def __init__(self, raw):
        self.reader = io.BytesIO(raw)
        self.writer = io.BytesIO()
        self.shutdown_calls = []

    def makefile(self, mode, *args, **kwargs):
        return self.reader

    def sendall(self, body):
        self.writer.write(body)

    def settimeout(self, value):
        pass

    def shutdown(self, how):
        self.shutdown_calls.append(how)


def request_memory(state, method, path, headers=None, body=b'', *, ip='127.0.0.1', host='127.0.0.1:8000'):
    values = [('Host', host)] + list((headers or {}).items())
    head = f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k, v in values)
    conn = MemoryConnection(head.encode('ascii') + b'\r\n' + body)
    server = SimpleNamespace(state=state, page=MOBILE_HTML, host='127.0.0.1:8000', origin='http://127.0.0.1:8000')
    Handler(conn, (ip, 10000), server)
    head, data = conn.writer.getvalue().split(b'\r\n\r\n', 1)
    code = int(head.split(b' ', 2)[1])
    result_headers = dict(line.decode('latin-1').split(': ', 1) for line in head.split(b'\r\n')[1:])
    return code, result_headers, data


def upload_headers(sid, name='a.txt', size=4):
    return {'X-Session': sid, 'Origin': 'http://127.0.0.1:8000', 'X-Filename': quote(name),
            'Content-Length': str(size), 'Content-Type': 'application/octet-stream'}


def test_http_handler_join_pending_approve_upload(state):
    token = state.token
    code, headers, data = request_memory(state, 'GET', '/?t=' + token)
    assert code == 200 and b'__SESSION_JSON__' not in data and token.encode() not in data
    sid = state.session.sid
    assert request_memory(state, 'GET', '/status', {'X-Session': sid})[0] == 202
    assert request_memory(state, 'POST', '/upload', upload_headers(sid), b'data')[0] == 403
    assert not list(state.folder.iterdir())
    state.set_state(sid, 'approved')
    assert request_memory(state, 'GET', '/status', {'X-Session': sid})[0] == 200
    assert request_memory(state, 'POST', '/upload', upload_headers(sid), b'data')[0] == 201
    assert (state.folder / 'a.txt').read_bytes() == b'data'


def test_security_headers_and_no_secret_logs(state, capsys):
    token = state.token
    code, headers, _ = request_memory(state, 'GET', '/?t=' + token)
    assert headers['Cache-Control'] == 'no-store'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['Referrer-Policy'] == 'no-referrer'
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert 'nonce-' in headers['Content-Security-Policy']
    sid = state.session.sid
    request_memory(state, 'GET', '/?t=' + token)
    output = capsys.readouterr()
    assert token not in output.out + output.err and sid not in output.out + output.err
    assert not state.events.qsize()


@pytest.mark.parametrize('method,path', [('GET','/files'),('GET','/../app.py'),('GET','/upload'),
    ('POST','/status'),('POST','/'),('DELETE','/'),('HEAD','/'),('GET','/status?sid=bad'),('OPTIONS','/upload')])
def test_only_three_routes(state, method, path):
    assert request_memory(state, method, path)[0] == 404


@pytest.mark.parametrize('change,code', [({'Content-Length': ''},411),({'Content-Length':'-1'},400),
    ({'Content-Length':str(MAX_FILE_SIZE+1)},413),({'Content-Length':'1,2'},400),
    ({'Transfer-Encoding':'chunked'},400),({'Expect':'100-continue'},400),
    ({'Content-Type':'text/plain'},415),({'X-Filename':''},400),
    ({'Origin':'https://evil.example'},403),({'Origin':''},403),
    ({'Sec-Fetch-Site':'cross-site'},403)])
def test_upload_validation(state, change, code):
    sid = approve(state)
    headers = upload_headers(sid)
    headers.update(change)
    assert request_memory(state, 'POST', '/upload', headers, b'data')[0] == code
    assert not list(state.folder.iterdir())


def test_reads_exact_content_length(state):
    sid = approve(state)
    assert request_memory(state, 'POST', '/upload', upload_headers(sid, size=2), b'abEXTRA')[0] == 201
    assert (state.folder / 'a.txt').read_bytes() == b'ab'


def test_short_body_cleans_part(state):
    sid = approve(state)
    assert request_memory(state, 'POST', '/upload', upload_headers(sid, size=20), b'short')[0] == 400
    assert not list(state.folder.iterdir())


def test_invalid_host_and_forwarded_ip(state):
    sid = approve(state)
    assert request_memory(state, 'GET', '/status', {'X-Session':sid}, host='evil.example')[0] == 403
    assert request_memory(state, 'GET', '/status', {'X-Session':sid, 'X-Forwarded-For':'127.0.0.1'}, ip='10.0.0.2')[0] == 403


def test_duplicate_length_rejected(state):
    sid = approve(state)
    headers = upload_headers(sid)
    headers['Content-Length'] = '4\r\nContent-Length: 4'
    assert request_memory(state, 'POST', '/upload', headers, b'data')[0] == 400


def test_storage_error_generic_no_traceback(state, monkeypatch):
    sid = approve(state)
    def fail(*args, **kwargs):
        raise OSError('private-path-sensitive-error')
    monkeypatch.setattr('core.tempfile.mkstemp', fail)
    code, headers, body = request_memory(state, 'POST', '/upload', upload_headers(sid), b'data')
    assert code == 500 and b'Traceback' not in body and b'private-path' not in body
    assert headers['Cache-Control'] == 'no-store'


@pytest.fixture
def live_server(tmp_path):
    state = State(tmp_path)
    server = PhoneDropServer(('127.0.0.1', 0), state, MOBILE_HTML, allow_loopback=True)
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':0.01}, daemon=True)
    worker.start()
    yield server
    server.shutdown()
    server.server_close()
    worker.join(timeout=3)


def live_request(server, method, path, headers=None, body=None):
    req = Request(server.origin + path, data=body, headers=headers or {}, method=method)
    try:
        response = urlopen(req, timeout=4)
    except HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), response.read()


@pytest.mark.network
def test_real_http_phone_approval_files_no_overwrite(live_server):
    server = live_server
    state = server.state
    token = state.token
    assert live_request(server,'GET','/?t='+token)[0] == 200
    sid = state.session.sid
    assert live_request(server,'GET','/?t='+token)[0] == 403
    assert live_request(server,'GET','/status',{'X-Session':sid})[0] == 202
    headers = upload_headers(sid)
    headers['Origin'] = server.origin
    assert live_request(server,'POST','/upload',headers,b'data')[0] == 403
    assert not list(state.folder.iterdir())
    state.set_state(sid, 'approved')
    assert live_request(server,'GET','/status',{'X-Session':sid})[0] == 200
    headers['X-Filename'] = 'bad.exe'
    assert live_request(server,'POST','/upload',headers,b'data')[0] == 415
    headers['X-Filename'] = quote('../../photo.txt')
    for _ in range(2):
        assert live_request(server,'POST','/upload',headers,b'data')[0] == 201
    assert (state.folder/'photo.txt').read_bytes() == b'data'
    assert (state.folder/'photo (1).txt').read_bytes() == b'data'
    state.rotate()
    assert live_request(server,'POST','/upload',headers,b'data')[0] == 403
    assert not list(state.folder.glob('*.part'))


@pytest.mark.network
def test_real_disconnect_during_upload(live_server):
    server = live_server
    sid = approve(server.state)
    with socket.create_connection(server.server_address, timeout=3) as client:
        request = (f'POST /upload HTTP/1.1\r\nHost: {server.host}\r\nOrigin: {server.origin}\r\n'
                   f'X-Session: {sid}\r\nX-Filename: big.txt\r\nContent-Type: application/octet-stream\r\n'
                   'Content-Length: 1000000\r\n\r\nsmall')
        client.sendall(request.encode())
        import time
        deadline = time.monotonic() + 3
        while server.state.upload is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert server.state.upload is not None
        server.state.rotate()
        assert client.recv(1024) == b''
    assert not list(server.state.folder.iterdir())


def test_reserved_name_with_space():
    assert safe_name('CON .txt') == '_CON .txt'


def test_executable_switch_requires_confirmation(state):
    from app import change_executable_policy
    assert not state.allow_executables
    assert not change_executable_policy(state, True, lambda: False)
    assert not state.allow_executables
    assert change_executable_policy(state, True, lambda: True)
    assert state.allow_executables
    assert not change_executable_policy(state, False, lambda: pytest.fail('Disabling must not require confirmation'))
    assert not state.allow_executables


def test_simultaneous_token_consumption_is_atomic(state):
    from concurrent.futures import ThreadPoolExecutor
    token = state.token
    barrier = threading.Barrier(2)
    def join(ip):
        barrier.wait(timeout=2)
        try:
            return state.join(token, ip, '').sid
        except RequestError:
            return None
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(join, ['one', 'two']))
    assert sum(result is not None for result in results) == 1


def test_expiry_cancels_in_progress_upload(state):
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'partial.txt')
    state.write_upload(upload, b'x')
    state.clock.advance(SESSION_SECONDS)
    state.tick()
    assert upload.closed and not upload.part.exists() and state.session is None


def test_upload_size_guard_before_write(state):
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'size.txt')
    upload.size = MAX_FILE_SIZE
    with pytest.raises(RequestError) as exc:
        state.write_upload(upload, b'x')
    assert exc.value.code == 413
    assert upload.part.stat().st_size == 0


def test_server_refuses_public_wildcard_and_loopback_by_default(state):
    for ip in ('0.0.0.0', '8.8.8.8', '127.0.0.1', '::'):
        with pytest.raises(ValueError):
            PhoneDropServer((ip, 0), state, MOBILE_HTML)


def test_no_clobber_if_file_created_during_publication(state, monkeypatch):
    import core
    original = core.unique_path
    first = True
    def race(folder, name):
        nonlocal first
        candidate = original(folder, name)
        if first:
            first = False
            candidate.write_bytes(b'other-writer')
        return candidate
    monkeypatch.setattr(core, 'unique_path', race)
    sid = approve(state)
    upload = state.begin_upload(sid, '127.0.0.1', 'race.txt')
    state.write_upload(upload, b'phone')
    assert state.finish_upload(upload, 5) == 'race (1).txt'
    assert (state.folder / 'race.txt').read_bytes() == b'other-writer'
    assert (state.folder / 'race (1).txt').read_bytes() == b'phone'


def test_monotonic_deadlines_ignore_system_wall_clock(state, monkeypatch):
    import time
    sid = approve(state)
    monkeypatch.setattr(time, 'time', lambda: -1e12)
    state.clock.advance(SESSION_SECONDS)
    with pytest.raises(RequestError):
        state.authorize(sid, '127.0.0.1')
