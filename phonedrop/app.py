"""PhoneDrop desktop UI and self-contained mobile page."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import sys
import threading

from core import PhoneDropServer, State, discover_lan_ips, lan_ipv4

MOBILE_HTML = r'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer"><title>PhoneDrop</title>
<style nonce="__NONCE__">
:root{color-scheme:dark;font:18px system-ui,sans-serif;background:#10151f;color:#f1f5fc}
body{margin:0;padding:24px 18px}main{max-width:560px;margin:auto}
h1{font-size:34px;margin-bottom:8px}p{line-height:1.6;color:#c7d2e3}
.panel{background:#1b2638;border:1px solid #354761;border-radius:18px;padding:22px;margin:22px 0}
button,.pick{box-sizing:border-box;display:block;width:100%;padding:18px;margin:14px 0;border:0;border-radius:12px;
background:#70d7bf;color:#09241f;font:700 18px system-ui;text-align:center;cursor:pointer}
button:disabled{opacity:.5;cursor:wait}input{max-width:100%;font:16px system-ui}
progress{width:100%;height:22px;accent-color:#70d7bf}.file{padding:16px 0;border-bottom:1px solid #354761;overflow-wrap:anywhere}
[hidden]{display:none!important}.muted{font-size:15px;color:#aab9cf}.result{white-space:pre-wrap}
</style></head><body><main><h1>PhoneDrop</h1><p>Gửi file đến máy tính qua mạng nội bộ.</p>
<section class="panel"><p id="status" role="status" aria-live="polite">Đang chờ máy tính xác nhận</p>
<div id="controls" hidden><label class="pick" for="files">Chọn nhiều file</label>
<input id="files" type="file" multiple><button id="send" disabled>Gửi file</button></div>
<div id="results" aria-live="polite"></div></section>
<p class="muted">Giữ trang này mở khi gửi. Mỗi file tối đa 5 GiB. Máy tính có thể ngắt kết nối bất cứ lúc nào.</p>
<p id="privacy" class="muted"></p></main>
<script nonce="__NONCE__">
'use strict';
const sid=__SESSION_JSON__;
history.replaceState(null,'','/');
const statusEl=document.getElementById('status'),controls=document.getElementById('controls');
const files=document.getElementById('files'),send=document.getElementById('send'),results=document.getElementById('results');
let approved=false,busy=false,stopped=false,active=null;
document.getElementById('privacy').textContent=location.protocol==='https:'?
 'HTTPS đang bật. Đối chiếu fingerprint chứng chỉ với máy tính trước khi gửi.':
 'HTTP không mã hóa. Chỉ dùng trên mạng riêng mà bạn tin cậy; người trong mạng có thể đọc hoặc sửa dữ liệu.';
function stop(message){stopped=true;approved=false;controls.hidden=true;statusEl.textContent=message;if(active)active.abort();}
async function poll(){
 if(stopped)return;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
 try{
  const response=await fetch('/status',{headers:{'X-Session':sid},cache:'no-store',signal:controller.signal});
  if(response.status!==200&&response.status!==202){stop('Phiên đã hết hạn hoặc bị từ chối. Hãy quét QR mới trên máy tính.');return;}
  const data=await response.json();approved=data.status==='approved';
  controls.hidden=!approved;send.disabled=!approved||busy||!files.files.length;
  statusEl.textContent=approved?'Máy tính đã cho phép. Bạn có thể gửi file.':'Đang chờ máy tính xác nhận';
 }catch(error){stop('Mất kết nối. Kiểm tra máy tính và quét QR mới.');}
 finally{clearTimeout(timer);if(!stopped)setTimeout(poll,1500);}
}
files.addEventListener('change',()=>{send.disabled=!approved||busy||!files.files.length;});
function upload(file,bar){return new Promise((resolve,reject)=>{
 const xhr=new XMLHttpRequest();active=xhr;xhr.open('POST','/upload');xhr.timeout=20*60*1000;
 xhr.setRequestHeader('X-Session',sid);xhr.setRequestHeader('X-Filename',encodeURIComponent(file.name));
 xhr.setRequestHeader('Content-Type','application/octet-stream');
 xhr.upload.onprogress=event=>{if(event.lengthComputable)bar.value=Math.round(event.loaded/event.total*100);};
 xhr.onload=()=>{active=null;let data;try{data=JSON.parse(xhr.responseText);}catch(error){reject(new Error('Phản hồi không hợp lệ.'));return;}
  if(xhr.status===201){bar.value=100;resolve(data.name);}else{reject(new Error(data.error||'Không thể gửi file.'));}};
 xhr.onerror=()=>{active=null;reject(new Error('Mất kết nối; hãy kiểm tra danh sách đã nhận trên máy tính.'));};
 xhr.ontimeout=()=>{active=null;reject(new Error('Hết thời gian gửi file.'));};
 xhr.onabort=()=>{active=null;reject(new Error('Đã ngắt kết nối.'));};
 try{xhr.send(file);}catch(error){active=null;reject(new Error('Không thể đọc hoặc gửi file.'));}
});}
send.addEventListener('click',async()=>{
 if(!approved||busy)return;busy=true;send.disabled=true;files.disabled=true;results.replaceChildren();
 const selected=Array.from(files.files);
 try{for(const file of selected){
  const row=document.createElement('div');row.className='file';
  const title=document.createElement('div');title.textContent=file.name;
  const bar=document.createElement('progress');bar.max=100;bar.value=0;bar.setAttribute('aria-label','Tiến trình gửi');
  const result=document.createElement('p');result.className='result';result.textContent='Đang gửi…';
  row.append(title,bar,result);results.append(row);
  if(stopped){result.textContent='Lỗi: Phiên đã ngắt.';continue;}
  if(file.size>5*1024**3){result.textContent='Lỗi: File vượt quá 5 GiB.';continue;}
  try{const name=await upload(file,bar);result.textContent='Xong: '+name;}
  catch(error){result.textContent='Lỗi: '+error.message;}
 }}finally{busy=false;files.disabled=false;send.disabled=!approved||stopped||!files.files.length;}
});
poll();
</script></body></html>'''


def change_executable_policy(state, enabled, confirm):
    """A local affirmative confirmation is required before enabling dangerous files."""
    if enabled and not confirm():
        return False
    state.set_allow_executables(enabled)
    return bool(enabled)


def smoke_test(output: Path):
    """Run in the frozen Windows executable in CI, including Tk/Pillow/QR/TLS imports."""
    import tkinter as tk
    from PIL import ImageTk
    import qrcode
    from tls_support import create_tls_context
    import tempfile
    from urllib.request import Request, urlopen
    with tempfile.TemporaryDirectory() as directory:
        context, fingerprint, certificate = create_tls_context('127.0.0.1', Path(directory))
        root = tk.Tk()
        root.withdraw()
        qr = qrcode.make('PhoneDrop packaging self-test')
        picture = ImageTk.PhotoImage(qr.get_image(), master=root)
        root.update()
        assert picture.width() > 0 and context and certificate.exists()
        root.destroy()
        state = State(Path(directory) / 'received')
        server = PhoneDropServer(('127.0.0.1', 0), state, MOBILE_HTML, allow_loopback=True)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        thread.start()
        try:
            with urlopen(server.origin + '/?t=' + state.token, timeout=5) as response:
                assert response.status == 200
            sid = state.session.sid
            assert state.set_state(sid, 'approved')
            request = Request(server.origin + '/upload', data=b'PhoneDrop smoke test', method='POST',
                              headers={'X-Session': sid, 'X-Filename': 'smoke.txt',
                                       'Content-Type': 'application/octet-stream', 'Origin': server.origin})
            with urlopen(request, timeout=5) as response:
                assert response.status == 201
            assert (state.folder / 'smoke.txt').read_bytes() == b'PhoneDrop smoke test'
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
    output.write_text(json.dumps({'ok': True, 'python': sys.version.split()[0],
                                  'tk': True, 'qr': True, 'tls': bool(fingerprint),
                                  'http_upload': True}), encoding='utf-8')


def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from PIL import ImageTk
    import qrcode
    import subprocess
    import tempfile
    from tls_support import create_tls_context

    root = tk.Tk()
    root.title('PhoneDrop')
    root.geometry('760x850')
    root.minsize(650, 730)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TButton', padding=9)
    style.configure('Title.TLabel', font=('Segoe UI', 25, 'bold'))
    style.configure('TLabel', font=('Segoe UI', 10))
    container = ttk.Frame(root, padding=20)
    container.pack(fill='both', expand=True)
    ttk.Label(container, text='PhoneDrop', style='Title.TLabel').pack(anchor='w')
    ttk.Label(container, text='Quét QR trên điện thoại • Xác nhận trên máy tính • Gửi file').pack(anchor='w', pady=(0, 12))
    folder = Path.home() / 'Downloads' / 'PhoneDrop'
    try:
        state = State(folder)
    except OSError:
        messagebox.showerror('PhoneDrop', 'Không thể tạo thư mục Downloads/PhoneDrop.', parent=root)
        root.destroy()
        return
    runtime = {'server': None, 'thread': None, 'dialog': None, 'dialog_sid': None, 'qr': None,
               'certificate_dir': None, 'closing': False}
    addresses = discover_lan_ips()
    ip_var = tk.StringVar(value=addresses[0] if addresses else '')
    tls_var = tk.BooleanVar(value=False)
    dangerous_var = tk.BooleanVar(value=False)
    status_var = tk.StringVar(value='Đang khởi động…')
    folder_var = tk.StringVar(value=str(state.folder))
    address_var = tk.StringVar()
    fingerprint_var = tk.StringVar()
    network = ttk.Frame(container)
    network.pack(fill='x')
    ttk.Label(network, text='IPv4 LAN:').pack(side='left')
    ip_box = ttk.Combobox(network, textvariable=ip_var, values=addresses, width=19)
    ip_box.pack(side='left', padx=8)
    qr_label = ttk.Label(container, anchor='center')
    qr_label.pack(pady=8)
    ttk.Label(container, textvariable=status_var, anchor='center').pack(fill='x')
    ttk.Label(container, textvariable=address_var, anchor='center').pack(fill='x', pady=4)
    fingerprint = ttk.Entry(container, textvariable=fingerprint_var, state='readonly', font=('Consolas', 8))
    fingerprint.pack(fill='x', pady=4)
    ttk.Label(container, text='HTTPS: đối chiếu SHA-256 ở ô trên với chứng chỉ trên điện thoại.', wraplength=700).pack(anchor='w')
    warning = ttk.Label(container, text='HTTP không mã hóa. Chỉ sử dụng trên mạng LAN riêng, đáng tin cậy.', wraplength=700)
    warning.pack(anchor='w', pady=6)

    def dismiss_dialog():
        if runtime['dialog'] is not None:
            runtime['dialog'].destroy()
            runtime['dialog'] = None
            runtime['dialog_sid'] = None

    def stop_server():
        old = runtime['server']
        runtime['server'] = None
        state.close()
        dismiss_dialog()
        if old:
            old.shutdown()
            old.server_close()
            runtime['thread'].join(timeout=2)
        if runtime['certificate_dir']:
            runtime['certificate_dir'].cleanup()
            runtime['certificate_dir'] = None

    def start_server():
        stop_server()
        ip = ip_var.get().strip()
        qr_label.configure(image='')
        runtime['qr'] = None
        address_var.set('')
        fingerprint_var.set('')
        if not lan_ipv4(ip):
            status_var.set('Chưa tìm thấy IPv4 LAN. Kết nối Wi-Fi/Ethernet và nhập IP LAN của máy tính.')
            return
        try:
            tls_context = None
            if tls_var.get():
                runtime['certificate_dir'] = tempfile.TemporaryDirectory(prefix='phonedrop-tls-')
                tls_context, digest, _ = create_tls_context(ip, Path(runtime['certificate_dir'].name))
                fingerprint_var.set(digest)
            with state.lock:
                state.enabled = True
                state.rotate()
            server = PhoneDropServer((ip, 0), state, MOBILE_HTML, tls_context=tls_context)
            runtime['server'] = server
            runtime['thread'] = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.1}, daemon=True)
            runtime['thread'].start()
            address_var.set(server.origin)
            warning.configure(text=('HTTPS đang bật. Chứng chỉ tự ký thay đổi khi khởi động lại server.' if tls_var.get() else
                                    'HTTP không mã hóa. Chỉ sử dụng trên mạng LAN riêng, đáng tin cậy.'))
        except Exception:
            stop_server()
            status_var.set('Không thể mở server. Kiểm tra IP, quyền mạng và thư viện đã cài.')

    ttk.Button(network, text='Kết nối lại', command=start_server).pack(side='left')
    ttk.Checkbutton(network, text='HTTPS tự ký', variable=tls_var, command=start_server).pack(side='right')

    def rotate():
        state.rotate()
        dismiss_dialog()

    ttk.Button(container, text='Tạo QR mới / Ngắt kết nối', command=rotate).pack(fill='x', pady=8)
    ttk.Label(container, text='Thư mục nhận:').pack(anchor='w')
    ttk.Label(container, textvariable=folder_var, wraplength=700).pack(anchor='w')
    folder_buttons = ttk.Frame(container)
    folder_buttons.pack(fill='x', pady=6)

    def choose_folder():
        selected = filedialog.askdirectory(parent=root, initialdir=state.folder, mustexist=True)
        if selected:
            try:
                state.set_folder(Path(selected))
                folder_var.set(str(state.folder))
                dismiss_dialog()
            except OSError:
                messagebox.showerror('PhoneDrop', 'Không thể sử dụng thư mục này.', parent=root)

    def open_folder():
        try:
            if os.name == 'nt':
                os.startfile(str(state.folder))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(state.folder)])
        except OSError:
            messagebox.showerror('PhoneDrop', 'Không thể mở thư mục.', parent=root)

    ttk.Button(folder_buttons, text='Đổi thư mục', command=choose_folder).pack(side='left')
    ttk.Button(folder_buttons, text='Mở thư mục', command=open_folder).pack(side='left', padx=8)

    def change_dangerous():
        enabled = dangerous_var.get()
        def confirm():
            return messagebox.askyesno('Cho phép file nguy hiểm?',
                'File thực thi có thể gây hại khi mở. Chỉ bật nếu bạn hiểu rủi ro và tin cậy người gửi.\n\nTiếp tục?',
                parent=root, icon='warning', default='no')
        dangerous_var.set(change_executable_policy(state, enabled, confirm))
        dismiss_dialog()

    ttk.Checkbutton(container, text='Cho phép file thực thi - NGUY HIỂM', variable=dangerous_var,
                    command=change_dangerous).pack(anchor='w', pady=5)
    ttk.Label(container, text='File đã nhận (200 file gần nhất):').pack(anchor='w', pady=(8, 4))
    table_frame = ttk.Frame(container)
    table_frame.pack(fill='both', expand=True)
    table = ttk.Treeview(table_frame, columns=('name', 'size'), show='headings', height=6)
    table.heading('name', text='Tên file')
    table.heading('size', text='Dung lượng')
    table.column('name', width=480)
    table.column('size', width=110, anchor='e')
    table.pack(side='left', fill='both', expand=True)
    scroll = ttk.Scrollbar(table_frame, orient='vertical', command=table.yview)
    scroll.pack(side='right', fill='y')
    table.configure(yscrollcommand=scroll.set)

    def show_approval(info):
        sid, ip, agent, _, seconds = info
        dismiss_dialog()
        dialog = tk.Toplevel(root)
        runtime['dialog'] = dialog
        runtime['dialog_sid'] = sid
        dialog.title('Cho phép thiết bị gửi file?')
        dialog.transient(root)
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Thiết bị: {ip}', font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Trình duyệt: ' + (agent or 'Không cung cấp'), wraplength=480).pack(anchor='w', pady=12)
        countdown = ttk.Label(frame)
        countdown.pack(anchor='w')
        ttk.Label(frame, text='Chỉ cho phép nếu bạn vừa quét QR. IP và tên trình duyệt không chứng minh danh tính.',
                  wraplength=480).pack(anchor='w', pady=10)
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=8)

        def decide(status):
            state.set_state(sid, status)
            dismiss_dialog()

        deny = ttk.Button(buttons, text='Từ chối', command=lambda: decide('denied'))
        deny.pack(side='left', padx=8)
        ttk.Button(buttons, text='Cho phép', command=lambda: decide('approved')).pack(side='right', padx=8)
        dialog.protocol('WM_DELETE_WINDOW', lambda: decide('denied'))
        dialog.bind('<Escape>', lambda event: decide('denied'))
        dialog.lift()
        deny.focus_set()
        runtime['countdown'] = countdown

    def update():
        if runtime['closing']:
            return
        snapshot = state.snapshot()
        session = snapshot['session']
        server = runtime['server']
        if server:
            if session is None:
                dismiss_dialog()
                token = snapshot['token']
                if token != runtime['qr']:
                    picture = qrcode.make(server.origin + '/?t=' + token).get_image().resize((280, 280), resample=0)
                    runtime['picture'] = ImageTk.PhotoImage(picture, master=root)
                    qr_label.configure(image=runtime['picture'])
                    runtime['qr'] = token
                status_var.set(f'Quét QR để kết nối • Còn {snapshot["remaining"]} giây')
            else:
                qr_label.configure(image='')
                runtime['qr'] = None
                if session[3] == 'pending':
                    status_var.set('Đang chờ bạn xác nhận trên máy tính')
                    if runtime['dialog_sid'] != session[0]:
                        show_approval(session)
                    runtime['countdown'].configure(text=f'Tự động từ chối sau {session[4]} giây.')
                else:
                    dismiss_dialog()
                    status_var.set(f'Đã cho phép {session[1]} gửi file • Phiên tối đa 20 phút')
        for _ in range(64):
            try:
                kind, data = state.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'received':
                table.insert('', 0, values=(data[0], f'{data[1]:,} byte'))
                for item in table.get_children()[200:]:
                    table.delete(item)
            elif kind == 'error':
                warning.configure(text=data)
        root.after(250, update)

    def close():
        runtime['closing'] = True
        stop_server()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    start_server()
    update()
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        smoke_test(Path(sys.argv[2]))
    else:
        main()
