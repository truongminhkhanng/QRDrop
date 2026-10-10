from pathlib import Path

import pytest

from core import RequestError, SESSION_SECONDS, State
from viewmodel import dashboard, format_size, format_time, initial_geometry


@pytest.mark.parametrize('size,expected', [(0,'0 B'),(1024,'1.0 KiB'),(1024**2,'1.0 MiB'),(5*1024**3,'5.0 GiB')])
def test_format_size(size, expected):
    assert format_size(size) == expected


def test_window_fits_small_screen():
    w,h = initial_geometry(1366,768)
    assert w <= 1286 and h <= 648
    assert initial_geometry(800,600) == (720,480)


def test_time_does_not_go_negative():
    assert format_time(-1) == '00:00'
    assert format_time(1200) == '20:00'
    assert format_time(3599) == '59:59'
    assert format_time(3600) == '01:00:00'
    assert format_time(43199) == '11:59:59'
    assert format_time(43200) == '12:00:00'


def test_progress_snapshots_and_session_remaining(tmp_path):
    now = [1000.0]
    state = State(tmp_path, clock=lambda:now[0])
    try:
        pending = state.join(state.token, '192.168.1.9', 'Phone')
        view = dashboard(state.snapshot(), connected=True)
        assert view['state'] == 'pending'
        assert pending.sid not in str(view)
        state.set_state(pending.sid, 'approved')
        now[0] += 10
        assert state.snapshot()['session_remaining'] == SESSION_SECONDS - 10
        upload = state.begin_upload(pending.sid, '192.168.1.9', 'x.txt', total=10)
        state.write_upload(upload,b'abc')
        snapshot = state.snapshot()
        assert snapshot['upload'] == {'name':'x.txt','received':3,'total':10}
        view = dashboard(snapshot, connected=True)
        assert view['progress'] == 30 and view['amount'] == '3 B / 10 B'
        assert view['action'] == 'Ngắt kết nối'
        state.write_upload(upload,b'defghij')
        assert snapshot['upload']['received'] == 3  # Immutable copy, no live upload object exposed.
        state.finish_upload(upload,10)
        assert state.snapshot()['upload'] is None
        assert (tmp_path/'x.txt').read_bytes() == b'abcdefghij'
    finally:
        state.close()


def test_rotation_resets_progress_and_action(tmp_path):
    state = State(tmp_path)
    try:
        session = state.join(state.token,'192.168.1.9','')
        state.set_state(session.sid,'approved')
        upload = state.begin_upload(session.sid,'192.168.1.9','x.txt',total=10)
        state.write_upload(upload,b'a')
        state.rotate()
        snapshot = state.snapshot()
        view = dashboard(snapshot,connected=True)
        assert view['state']=='waiting' and view['action']=='Tạo QR mới' and view['show_qr']
        assert snapshot['upload'] is None and not upload.part.exists()
        assert state.events.get_nowait() == ('cancelled','x.txt')
        assert dashboard(snapshot,connected=False)['action']=='Kết nối lại'
    finally:
        state.close()


def test_declared_total_cannot_be_overrun_or_changed(tmp_path):
    state = State(tmp_path)
    try:
        session=state.join(state.token,'192.168.1.9','')
        state.set_state(session.sid,'approved')
        with pytest.raises(RequestError):
            state.begin_upload(session.sid,'192.168.1.9','x.txt',total=-1)
        assert not list(tmp_path.iterdir())
        upload=state.begin_upload(session.sid,'192.168.1.9','x.txt',total=2)
        with pytest.raises(RequestError):
            state.write_upload(upload,b'abc')
        state.write_upload(upload,b'a')
        with pytest.raises(RequestError):
            state.finish_upload(upload,1)
    finally:
        state.close()
