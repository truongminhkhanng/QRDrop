"""Pure presentation helpers shared by desktop UI and visual review tools."""
from __future__ import annotations

COLORS = {
    'background': '#10151f', 'panel': '#1b2638', 'border': '#354761',
    'text': '#f1f5fc', 'muted': '#b6c4d8', 'accent': '#70d7bf',
    'accent_text': '#09241f', 'danger': '#ff9c9c', 'warning': '#f4cb80',
}


def format_size(size: int) -> str:
    value = max(0, size)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value:g} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


def format_time(seconds: int) -> str:
    minutes, seconds = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    return f'{minutes:02d}:{seconds:02d}'


def initial_geometry(screen_width: int, screen_height: int) -> tuple[int, int]:
    return min(980, max(320, screen_width - 80)), min(660, max(320, screen_height - 120))


def dashboard(snapshot: dict, *, connected: bool) -> dict:
    """No credentials in the returned presentation model."""
    result = {'title': 'Chưa kết nối mạng', 'detail': 'Mở Cài đặt để kiểm tra kết nối Wi-Fi hoặc Ethernet.',
              'action': 'Kết nối lại', 'state': 'offline', 'progress': 0,
              'transfer': 'Chưa có file đang gửi', 'amount': '', 'show_qr': False}
    if not connected:
        return result
    session = snapshot['session']
    if session is None:
        result.update(title='Sẵn sàng kết nối',
                      detail=f'Mở camera điện thoại và quét QR. Mã đổi sau {format_time(snapshot["remaining"])}.',
                      action='Tạo QR mới', state='waiting', show_qr=True)
    elif session[3] == 'pending':
        result.update(title='Thiết bị đang chờ', detail=f'{session[1]} • Xác nhận trong {format_time(session[4])}',
                      action='Ngắt kết nối', state='pending')
    else:
        result.update(title='Đã kết nối',
                      detail=f'{session[1]} • Còn {format_time(snapshot["session_remaining"])}',
                      action='Ngắt kết nối', state='approved')
    upload = snapshot.get('upload')
    if upload:
        total = upload['total']
        done = upload['received']
        result.update(state='receiving', title='Đang nhận file', transfer=upload['name'],
                      amount=f'{format_size(done)} / {format_size(total)}' if total is not None else format_size(done),
                      progress=min(100, done / total * 100) if total else 0)
    return result


def change_executable_policy(state, enabled, confirm):
    """Only a local affirmative confirmation can enable executable receipt."""
    if enabled and not state.allow_executables and not confirm():
        return False
    state.set_allow_executables(enabled)
    return bool(enabled)
