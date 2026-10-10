"""Produce an offline UX review. Desktop is illustrative; mobile uses production HTML/JS."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import MOBILE_HTML
from core import SESSION_SECONDS
from viewmodel import dashboard

snapshots = {
    'waiting': {'token':'', 'remaining':112,'session':None,'upload':None,'session_remaining':0},
    'pending': {'token':'','remaining':0,'session':('review-only','192.168.1.9','Điện thoại · Trình duyệt', 'pending',46),'upload':None,'session_remaining':0},
    'approved': {'token':'','remaining':0,'session':('review-only','192.168.1.9','Điện thoại · Trình duyệt', 'approved',0),'upload':None,'session_remaining':SESSION_SECONDS-18},
    'receiving': {'token':'','remaining':0,'session':('review-only','192.168.1.9','Điện thoại · Trình duyệt', 'approved',0),
                  'upload':{'name':'Anh-chuyen-di.jpg','received':6291456,'total':10485760},'session_remaining':SESSION_SECONDS-36},
    'offline': {'token':'','remaining':0,'session':None,'upload':None,'session_remaining':0},
}
views={key:dashboard(value,connected=key!='offline') for key,value in snapshots.items()}
# This simulator never reads file bytes or contacts any server. Only metadata drives display.
simulator=r'''
window.fetch=async()=>({status:window.REVIEW_STATE==='pending'?202:200,json:async()=>({status:window.REVIEW_STATE==='pending'?'pending':'approved'})});
window.XMLHttpRequest=class {
 constructor(){this.upload={};this.headers={};this.timer=null;}
 open(){} setRequestHeader(k,v){this.headers[k]=v;}
 send(file){let percent=0;this.timer=setInterval(()=>{percent+=20;
  if(this.upload.onprogress)this.upload.onprogress({lengthComputable:true,loaded:file.size*percent/100,total:file.size||1});
  if(percent>=100){clearInterval(this.timer);this.status=201;this.responseText=JSON.stringify({name:file.name});this.onload();}
 },250);}
 abort(){clearInterval(this.timer);if(this.onabort)this.onabort();}
};
'''
mobile=MOBILE_HTML.replace('__SESSION_JSON__','"review-session-never-authorized"')
mobile=mobile.replace("history.replaceState(null,'','/');",'// Offline review has no navigable server URL.')
mobile=mobile.replace('</head>',"<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:;\"></head>")

template=r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhoneDrop · Xem trước UX/UI</title><style>
:root{font:15px 'Segoe UI',system-ui,sans-serif;color:#f1f5fc;background:#0b1018;color-scheme:dark}*{box-sizing:border-box}
body{margin:0;padding:24px}h1{font-size:27px;margin:4px 0}p{line-height:1.55;color:#b6c4d8}.review{max-width:1420px;margin:auto}
.note{padding:16px 20px;background:#262235;border:1px solid #635379;border-radius:10px;margin:18px 0}.note p{margin:3px 0}
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:20px 0}button,select{font:inherit;background:#354761;border:1px solid #48607e;color:#f1f5fc;padding:10px 14px;cursor:pointer;border-radius:5px;min-height:44px}button:focus-visible,select:focus-visible{outline:3px solid #f4cb80;outline-offset:3px}.primary{background:#70d7bf;color:#09241f;border:0;font-weight:700}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:24px;align-items:start}.caption{font-size:13px;color:#b6c4d8;margin:10px 0}
.desktop{background:#10151f;border:1px solid #354761;border-radius:8px;overflow:hidden;position:relative}.titlebar{padding:8px 15px;background:#1b2638;font-size:12px}.titlebar span{float:right;letter-spacing:16px}
.apphead{display:flex;justify-content:space-between;align-items:center;padding:18px 22px}.apphead h2{font-size:29px;margin:0}.apphead p{margin:4px 0;font-size:13px}
.content{padding:0 18px;display:grid;grid-template-columns:310px minmax(0,1fr);gap:12px}.card{background:#1b2638;padding:18px;min-width:0}.card h3{font-size:19px;margin:0 0 16px}.connect{text-align:center}.connect button{width:100%;margin-top:8px}.qr{width:224px;height:224px;background:#111d2a;border:2px dashed #70d7bf;margin:18px auto;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:12px;color:#70d7bf}.qr svg{width:90px;height:90px}.qr strong{font-size:17px}.qr small{color:#b6c4d8}
#detail{font-size:14px;min-height:50px}progress{height:12px;width:100%;accent-color:#70d7bf}.transfer{padding:8px 0 18px}.transfer p{margin:8px 0;font-size:14px;overflow-wrap:anywhere}
.table{width:100%;border-collapse:collapse;font-size:13px;min-height:150px}.table th{padding:10px;background:#354761;text-align:left}.table td{padding:14px 6px;border-bottom:1px solid #354761}.empty{font-size:14px;color:#b6c4d8;text-align:center;padding:22px 0}
.folder{margin-top:22px;font-size:13px;overflow-wrap:anywhere}.folder p{margin:4px 0}.footer{padding:14px 22px;font-size:13px}.footer .warning{color:#f4cb80;margin:4px 0}.footer p{margin:4px 0}
.phone{background:#1b2638;border:2px solid #354761;border-radius:24px;padding:8px;overflow:hidden}iframe{width:100%;height:740px;border:0;border-radius:17px;background:#10151f}
.overlay{position:absolute;inset:0;background:#05090dcc;display:flex;align-items:center;justify-content:center;padding:20px;z-index:1}.dialog{background:#10151f;border:1px solid #48607e;padding:24px;width:470px;max-height:95%;overflow:auto}.dialog h3{font-size:22px;margin:0 0 16px}.dialog .agent{padding:16px;background:#1b2638;font-size:14px}.dialog .buttons{display:flex;justify-content:space-between;gap:12px;margin-top:20px}.dialog label{display:block;margin:18px 0 8px}.dialog input{padding:12px;background:#1b2638;border:1px solid #354761;color:#f1f5fc;max-width:100%}.dialog input[type=checkbox]{width:20px;height:20px;vertical-align:middle}.help{font-size:13px}[hidden]{display:none!important}.small .content{grid-template-columns:1fr}.small .desktop{max-width:650px}.small .card{min-height:0}
@media(max-width:1250px){.layout{grid-template-columns:1fr}.phone{width:360px;max-width:100%}.desktop{max-width:980px}}
@media(max-width:740px){body{padding:12px}.content{grid-template-columns:1fr}.apphead{gap:12px}.apphead h2{font-size:25px}}
</style></head><body><div class="review"><h1>PhoneDrop · Duyệt UX/UI</h1>
<div class="note"><strong>Bản mô phỏng ngoại tuyến — không phải ảnh chụp ứng dụng Windows.</strong>
<p>Desktop minh họa bố cục mới. Khung điện thoại dùng HTML/JS của app, với mạng mô phỏng. Bạn có thể chọn file để thử giao diện; bản xem trước không đọc nội dung, không gửi và không lưu file.</p>
<p>QR và dữ liệu file là minh họa. Giao diện ttk thực tế và DPI cần kiểm tra trên Windows trước khi phát hành.</p></div>
<div class="toolbar"><label for="scenario">Trạng thái</label><select id="scenario"><option value="waiting">Sẵn sàng / Chưa quét QR</option><option value="pending">Điện thoại chờ xác nhận</option><option value="approved">Đã cho phép / Chọn file</option><option value="receiving">Đang nhận file</option><option value="complete">Nhận xong</option><option value="offline">Chưa có mạng</option></select>
<button id="small">Thử bố cục hẹp</button><button id="resetMobile">Làm mới khung điện thoại</button></div>
<div class="layout"><section id="pc"><p class="caption">MÁY TÍNH · Bố cục theo trạng thái thực trong ứng dụng</p><div class="desktop">
<div class="titlebar">PhoneDrop <span>— □ ×</span></div><div class="apphead"><div><h2>PhoneDrop</h2><p>Từ điện thoại đến máy tính của bạn</p></div><button id="settings">Cài đặt</button></div>
<div class="content"><div class="card connect"><h3 id="heading"></h3><div class="qr" id="qr"><svg viewBox="0 0 100 100" aria-hidden="true"><path fill="none" stroke="#70d7bf" stroke-width="5" d="M6 36V6h30m28 0h30v30M6 64v30h30m28 0h30V64M27 27h15v15H27zM58 58h15v15H58z"/></svg><strong id="qrText">QR xem trước</strong><small id="qrHint">Không dùng để kết nối</small></div><p id="detail"></p><button id="action"></button></div>
<div class="card"><h3>Nhận file</h3><div class="transfer"><p id="transfer"></p><progress id="progress" max="100" value="0"></progress><p id="amount"></p></div><h3 id="receivedTitle">Đã nhận · 0 file</h3>
<table class="table"><thead><tr><th>Tên file</th><th>Dung lượng</th></tr></thead><tbody id="receivedRows"></tbody></table><p id="empty" class="empty">File hoàn tất sẽ xuất hiện ở đây.</p>
<div class="folder"><p>Thư mục nhận</p><div>Downloads / PhoneDrop</div><button id="openFolder">Mở thư mục</button></div></div></div>
<div class="footer"><p class="warning">HTTP không mã hóa · Chỉ dùng mạng nội bộ mà bạn tin cậy.</p><p id="notice">Chỉ người được bạn cho phép mới gửi được file.</p></div>
<div class="overlay" id="approval" hidden><div class="dialog"><h3>Thiết bị muốn gửi file</h3><p>192.168.1.9</p><div class="agent">Điện thoại · Trình duyệt</div><p style="color:#f4cb80">Tự động từ chối sau 46 giây.</p><p>Chỉ cho phép nếu bạn vừa quét QR. IP và tên trình duyệt không chứng minh danh tính.</p><div class="buttons"><button id="deny">Từ chối</button><button id="allow" class="primary">Cho phép</button></div></div></div>
<div class="overlay" id="settingsPanel" hidden><div class="dialog"><h3>Cài đặt PhoneDrop</h3><label>IPv4 trên Wi-Fi / Ethernet</label><input value="192.168.1.20" aria-label="Địa chỉ minh họa"><p class="help">Chọn IP mà điện thoại truy cập được.</p><label><input type="checkbox" id="https"> Dùng HTTPS với chứng chỉ tự ký</label><p class="help">Khi bật, đối chiếu fingerprint với PC trước khi gửi.</p><label>Thư mục nhận</label><input value="Downloads / PhoneDrop" readonly aria-label="Thư mục minh họa"><label><input type="checkbox" id="dangerous"> Cho phép file thực thi - NGUY HIỂM</label><p class="help">Áp dụng sẽ ngắt phiên hiện tại và tạo QR mới. File đang nhận chưa xong sẽ bị hủy.</p><div class="buttons"><button id="cancelSettings">Hủy</button><button id="applySettings" class="primary">Áp dụng</button></div></div></div>
</div></section><section><p class="caption">ĐIỆN THOẠI · Chọn trạng thái “Đã cho phép” để thử gửi</p><div class="phone"><iframe id="mobile" sandbox="allow-scripts" title="PhoneDrop trên điện thoại — mô phỏng ngoại tuyến"></iframe></div></section></div></div>
<script>
const views=__VIEWS__;const mobile=__MOBILE__;const simulator=__SIMULATOR__;
const $=id=>document.getElementById(id);let mode='waiting';
function mobileView(){const state=(mode==='pending'||mode==='waiting'||mode==='offline')?'pending':'approved';
 const stub='<script>window.REVIEW_STATE='+JSON.stringify(state)+';'+simulator+'<'+ '/script>';
 $('mobile').srcdoc=mobile.replace('</head>',stub+'</head>');}
function render(){const v=views[mode==='complete'?'approved':mode];$('heading').textContent=v.title;$('detail').textContent=v.detail;$('action').textContent=v.action;
 $('transfer').textContent=v.transfer;$('progress').value=v.progress;$('amount').textContent=v.amount||'File hoàn tất sẽ xuất hiện ở đây.';
 $('approval').hidden=mode!=='pending';$('qrText').textContent=v.show_qr?'QR xem trước':v.title;$('qrHint').textContent=v.show_qr?'Không dùng để kết nối':(mode==='receiving'?'Đang nhận từ điện thoại':'');
 const done=mode==='complete';$('receivedTitle').textContent=done?'Đã nhận · 1 file':'Đã nhận · 0 file';$('empty').hidden=done;
 $('receivedRows').replaceChildren();if(done){const tr=document.createElement('tr');for(const text of ['Anh-chuyen-di.jpg','10.0 MiB']){const td=document.createElement('td');td.textContent=text;tr.append(td);}$('receivedRows').append(tr);$('amount').textContent='Đã lưu Anh-chuyen-di.jpg · 10.0 MiB';}
 mobileView();}
$('scenario').onchange=()=>{mode=$('scenario').value;render();};$('allow').onclick=()=>{mode='approved';$('scenario').value=mode;render();};
$('deny').onclick=$('action').onclick=()=>{mode='waiting';$('scenario').value=mode;render();};
$('small').onclick=()=>$('pc').classList.toggle('small');$('settings').onclick=()=>$('settingsPanel').hidden=false;
$('cancelSettings').onclick=()=>$('settingsPanel').hidden=true;$('applySettings').onclick=()=>{if($('dangerous').checked&&!confirm('Minh họa xác nhận: cho phép file nguy hiểm?'))return;$('settingsPanel').hidden=true;mode='waiting';$('scenario').value=mode;render();};
$('openFolder').onclick=()=>$('notice').textContent='Bản xem trước không mở thư mục. Ứng dụng thật mở thư mục nhận trên PC.';
$('resetMobile').onclick=mobileView;render();
</script></body></html>'''

def script_json(value):
    return json.dumps(value, ensure_ascii=False).replace('</','<\\/')

output=template.replace('__VIEWS__',script_json(views)).replace('__MOBILE__',script_json(mobile)).replace('__SIMULATOR__',script_json(simulator))
path=Path(__file__).resolve().parents[1]/'docs'/'ux-preview.html'
path.parent.mkdir(exist_ok=True)
path.write_text(output,encoding='utf-8')
print(path)
