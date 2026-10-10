"""PhoneDrop desktop UI and self-contained mobile page."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import sys
import threading

from core import PhoneDropServer, SESSION_SECONDS, State
from viewmodel import change_executable_policy

MOBILE_HTML = r'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer"><title>PhoneDrop</title>
<style nonce="__NONCE__">
:root{color-scheme:dark;font:18px system-ui,sans-serif;background:#10151f;color:#f1f5fc}
*{box-sizing:border-box}body{margin:0;padding:24px 18px 36px}main{max-width:560px;margin:auto}
header{display:flex;align-items:center;justify-content:space-between;gap:12px}h1{font-size:30px;letter-spacing:-1px;margin:0}
h2{font-size:23px;line-height:1.3;margin:10px 0}p{line-height:1.55;color:#b6c4d8;margin:8px 0}
.brand{font-weight:800;color:#70d7bf}.badge{font-size:13px;color:#70d7bf;border:1px solid #354761;padding:6px 10px;border-radius:30px}
.panel{background:#1b2638;border:1px solid #354761;border-radius:18px;padding:22px;margin:22px 0}
button{width:100%;min-height:52px;padding:14px 16px;border:1px solid #354761;border-radius:12px;
background:#26384e;color:#f1f5fc;font:700 17px system-ui;cursor:pointer}
button.primary{background:#70d7bf;border-color:#70d7bf;color:#09241f;margin-top:12px}
button:disabled{opacity:.5;cursor:default}button:focus-visible,summary:focus-visible{outline:3px solid #f4cb80;outline-offset:4px}
progress{width:100%;height:14px;accent-color:#70d7bf}.file{padding:16px 0;border-top:1px solid #354761;overflow-wrap:anywhere}
.file:first-child{margin-top:14px}.file p{font-size:15px}.filename{font-weight:650;line-height:1.5}
[hidden]{display:none!important}.muted{font-size:14px;color:#b6c4d8}.result{white-space:pre-wrap}.ok{color:#70d7bf}.error{color:#ff9c9c}
#summary{margin-top:14px;font-weight:650}.steps{font-size:13px;color:#b6c4d8;margin:18px 0}.steps span{color:#70d7bf}
details{font-size:14px;line-height:1.5;color:#b6c4d8}summary{cursor:pointer;min-height:44px;padding:10px 0}
@media(max-width:360px){body{padding:18px 12px}.panel{padding:16px}}
</style></head><body><main>
<header><span class="brand">PhoneDrop</span><span class="badge" id="badge">Chờ xác nhận</span></header>
<p class="steps">1. Quét QR &nbsp; / &nbsp; 2. Xác nhận &nbsp; / &nbsp; <span>3. Gửi file</span></p>
<section class="panel"><h1 id="title">Sắp kết nối xong</h1>
<p id="status" role="status" aria-live="polite">Đang chờ máy tính xác nhận</p>
<p id="hint" class="muted">Bấm Cho phép trên máy tính để tiếp tục. Yêu cầu tự hết hạn sau 60 giây.</p>
<div id="controls" hidden>
<input id="files" type="file" multiple hidden>
<button id="pick" type="button">Chọn file</button>
<p id="selection" class="muted">Bạn có thể chọn nhiều file cùng lúc.</p>
<div id="queue" aria-label="File đã chọn"></div>
<button id="send" class="primary" type="button" disabled hidden>Gửi file</button>
</div>
<p id="summary" role="status" aria-live="polite" hidden></p>
<div id="results" aria-label="Kết quả gửi file"></div></section>
<p class="muted">Giữ trang này mở khi gửi. Mỗi file tối đa 5 GiB.</p>
<details><summary>Kết nối và quyền riêng tư</summary><p id="privacy"></p>
<p>Máy tính có thể ngắt kết nối bất cứ lúc nào. File chỉ được lưu sau khi nhận đủ dữ liệu.</p></details>
</main><script nonce="__NONCE__">
'use strict';
const sid=__SESSION_JSON__;
history.replaceState(null,'','/');
const el=id=>document.getElementById(id);
const statusEl=el('status'),controls=el('controls'),files=el('files'),send=el('send'),pick=el('pick'),results=el('results');
const queue=el('queue'),selection=el('selection'),summary=el('summary'),title=el('title'),hint=el('hint'),badge=el('badge');
let approved=false,busy=false,stopped=false,active=null,selected=[],pollFailures=0,uncertain=false;
el('privacy').textContent=location.protocol==='https:'?
 'HTTPS đang bật. Đối chiếu fingerprint chứng chỉ với máy tính trước khi gửi.':
 'HTTP không mã hóa. Chỉ dùng trên mạng riêng mà bạn tin cậy; người trong mạng có thể đọc hoặc sửa dữ liệu.';
function sizeText(bytes){let value=bytes;for(const unit of ['B','KiB','MiB','GiB','TiB']){
 if(value<1024||unit==='TiB')return (unit==='B'?String(value):value.toFixed(1))+' '+unit;value/=1024;}}
function buttons(){send.disabled=!approved||busy||stopped||uncertain||!selected.length;pick.disabled=busy||stopped||uncertain;}
function stop(message){stopped=true;approved=false;controls.hidden=true;badge.textContent='Đã ngắt';title.textContent='Kết nối đã kết thúc';
 statusEl.textContent=message;hint.textContent='Trên máy tính, tạo QR mới rồi quét lại để tiếp tục.';buttons();if(active)active.abort();}
async function poll(){
 if(stopped)return;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
 try{
  const response=await fetch('/status',{headers:{'X-Session':sid},cache:'no-store',signal:controller.signal});
  if([403,404,429].includes(response.status)){stop('Phiên đã hết hạn, bị từ chối hoặc đã được ngắt trên máy tính.');return;}
  if(response.status!==200&&response.status!==202)throw new Error('connection');
  const data=await response.json();
  if(!['pending','approved'].includes(data.status))throw new Error('response');
  pollFailures=0;uncertain=false;approved=data.status==='approved';controls.hidden=!approved;
  badge.textContent=approved?'Đã kết nối':'Chờ xác nhận';
  title.textContent=approved?'Gửi file đến máy tính':'Sắp kết nối xong';
  statusEl.textContent=approved?'Máy tính đã cho phép nhận file.':'Đang chờ máy tính xác nhận';
  hint.textContent=approved?'Chọn file, kiểm tra danh sách rồi bấm Gửi.':'Bấm Cho phép trên máy tính để tiếp tục. Yêu cầu tự hết hạn sau 60 giây.';
  buttons();
 }catch(error){
  uncertain=true;pollFailures++;buttons();
  statusEl.textContent='Đang kiểm tra lại kết nối…';
  if(pollFailures>=3)stop('Không thể liên lạc với máy tính. Kiểm tra Wi-Fi và ứng dụng trên PC.');
 }finally{clearTimeout(timer);if(!stopped)setTimeout(poll,1500);}
}
pick.addEventListener('click',()=>{if(!busy&&!stopped)files.click();});
files.addEventListener('change',()=>{
 if(busy||stopped)return;
 selected=Array.from(files.files);queue.replaceChildren();
 for(const file of selected){
  const row=document.createElement('div');row.className='file';
  const name=document.createElement('div');name.className='filename';name.textContent=file.name;
  const size=document.createElement('p');size.textContent=sizeText(file.size)+(file.size>5*1024**3?' · Vượt quá giới hạn 5 GiB':'');
  if(file.size>5*1024**3)size.className='error';row.append(name,size);queue.append(row);
 }
 selection.textContent=selected.length?selected.length+' file · '+sizeText(selected.reduce((total,file)=>total+file.size,0)):'Bạn có thể chọn nhiều file cùng lúc.';
 pick.textContent=selected.length?'Chọn lại file':'Chọn file';send.textContent='Gửi '+selected.length+' file';send.hidden=!selected.length;buttons();
});
function upload(file,bar,result){return new Promise((resolve,reject)=>{
 const xhr=new XMLHttpRequest();active=xhr;xhr.open('POST','/upload');xhr.timeout=__UPLOAD_TIMEOUT_MS__;
 xhr.setRequestHeader('X-Session',sid);xhr.setRequestHeader('X-Filename',encodeURIComponent(file.name));
 xhr.setRequestHeader('Content-Type','application/octet-stream');
 xhr.upload.onprogress=event=>{if(event.lengthComputable){bar.value=Math.round(event.loaded/event.total*100);
  result.textContent=event.loaded===event.total?'Đã gửi dữ liệu · Chờ máy tính lưu file…':'Đang gửi · '+bar.value+'%';}};
 xhr.onload=()=>{active=null;let data;try{data=JSON.parse(xhr.responseText);}catch(error){reject(new Error('Không rõ máy tính đã lưu file chưa. Kiểm tra thư mục nhận trước khi gửi lại.'));return;}
  if(xhr.status===201&&typeof data.name==='string'){bar.value=100;resolve(data.name);}else{
   if([403,429].includes(xhr.status))stop('Máy tính đã ngắt hoặc phiên đã hết hạn.');
   reject(new Error(data.error||'Không thể gửi file.'));}};
 const uncertainMessage='Chưa xác nhận được kết quả. Kiểm tra file trên PC trước khi gửi lại.';
 xhr.onerror=()=>{active=null;reject(new Error(uncertainMessage));};
 xhr.ontimeout=()=>{active=null;reject(new Error('Hết thời gian gửi. '+uncertainMessage));};
 xhr.onabort=()=>{active=null;reject(new Error('Đã ngắt kết nối. '+uncertainMessage));};
 try{xhr.send(file);}catch(error){active=null;reject(new Error('Không thể đọc hoặc gửi file.'));}
});}
send.addEventListener('click',async()=>{
 if(!approved||busy||stopped||uncertain||!selected.length)return;
 busy=true;buttons();files.disabled=true;results.replaceChildren();queue.replaceChildren();
 const batch=selected.slice();let completed=0,failed=0;summary.hidden=false;
 try{for(const [index,file] of batch.entries()){
  summary.textContent='Đang xử lý file '+(index+1)+' / '+batch.length;
  const row=document.createElement('div');row.className='file';
  const name=document.createElement('div');name.className='filename';name.textContent=file.name;
  const bar=document.createElement('progress');bar.max=100;bar.value=0;bar.setAttribute('aria-label','Tiến trình gửi '+file.name);
  const result=document.createElement('p');result.className='result';result.textContent='Đang gửi…';
  row.append(name,bar,result);results.append(row);
  if(stopped){result.textContent='Chưa gửi: Phiên đã ngắt.';result.className='result error';failed++;continue;}
  if(file.size>5*1024**3){result.textContent='Lỗi: File vượt quá 5 GiB.';result.className='result error';failed++;continue;}
  try{const saved=await upload(file,bar,result);result.textContent='Xong · '+saved;result.className='result ok';completed++;}
  catch(error){result.textContent='Lỗi: '+error.message;result.className='result error';failed++;}
 }}finally{
  busy=false;selected=[];files.value='';files.disabled=false;send.hidden=true;pick.textContent='Gửi thêm file';
  selection.textContent='Chọn nhóm file mới để tiếp tục.';summary.textContent='Đã lưu '+completed+' / '+batch.length+' file'+(failed?' · '+failed+' file chưa xác nhận thành công.':'.');
  buttons();
 }
});
poll();
</script></body></html>
'''.replace('__UPLOAD_TIMEOUT_MS__', str(SESSION_SECONDS * 1000))


def smoke_test(output: Path):
    """Exercise the real desktop widgets and network code in the packaged executable."""
    import tkinter as tk
    from tkinter import ttk
    from desktop import PhoneDropApp
    from tls_support import create_tls_context
    import tempfile
    from urllib.request import Request, urlopen

    def click_named(parent, name):
        for widget in parent.winfo_children():
            if isinstance(widget, ttk.Button) and widget.cget('text') == name:
                widget.invoke()
                return True
            if click_named(widget, name):
                return True
        return False

    with tempfile.TemporaryDirectory() as directory:
        context, fingerprint, certificate = create_tls_context('127.0.0.1', Path(directory))
        state = State(Path(directory) / 'received')
        root = tk.Tk()
        ui = PhoneDropApp(root, state, MOBILE_HTML, autostart=False)
        server = PhoneDropServer(('127.0.0.1', 0), state, MOBILE_HTML, allow_loopback=True)
        worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        worker.start()
        ui.server, ui.worker = server, worker
        try:
            ui.refresh()
            root.update()
            assert ui.photo and ui.photo.width() > 0 and context and certificate.exists()
            ui.open_settings()
            root.update()
            assert ui.settings is not None
            assert click_named(ui.settings, 'Hủy')
            with urlopen(server.origin + '/?t=' + state.token, timeout=5) as response:
                assert response.status == 200
            ui.refresh()
            root.update()
            assert ui.dialog is not None
            assert click_named(ui.dialog, 'Cho phép')
            sid = state.session.sid
            assert state.session.status == 'approved'
            progress_upload = state.begin_upload(sid, '127.0.0.1', 'progress.txt', total=4)
            state.write_upload(progress_upload, b'ab')
            ui.refresh()
            root.update()
            assert int(ui.progress['value']) == 50
            state.cancel_upload(progress_upload)
            request = Request(server.origin + '/upload', data=b'PhoneDrop smoke test', method='POST',
                              headers={'X-Session': sid, 'X-Filename': 'smoke.txt',
                                       'Content-Type': 'application/octet-stream', 'Origin': server.origin})
            with urlopen(request, timeout=5) as response:
                assert response.status == 201
            ui.refresh()
            root.update()
            assert (state.folder / 'smoke.txt').read_bytes() == b'PhoneDrop smoke test'
            assert len(ui.table.get_children()) == 1
            root.geometry('640x500')
            root.update()
            assert ui.layout == 'stacked'
            assert ui.action.winfo_width() > 100
            assert ui.canvas.bbox('all')[3] > ui.canvas.winfo_height()
            ui.connection_action()
            assert state.session is None
        finally:
            ui.close()
    output.write_text(json.dumps({'ok': True, 'python': sys.version.split()[0],
                                  'tk': True, 'qr': True, 'tls': bool(fingerprint),
                                  'desktop_ui': True, 'http_upload': True}), encoding='utf-8')


def main():
    import tkinter as tk
    from tkinter import messagebox
    from desktop import PhoneDropApp
    root = tk.Tk()
    try:
        state = State(Path.home() / 'Downloads' / 'PhoneDrop')
    except OSError:
        messagebox.showerror('PhoneDrop', 'Không thể tạo thư mục Downloads/PhoneDrop.', parent=root)
        root.destroy()
        return
    PhoneDropApp(root, state, MOBILE_HTML)
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        smoke_test(Path(sys.argv[2]))
    else:
        main()
