const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const html=execFileSync(process.env.PYTHON||(process.platform==='win32'?'python':'python3'),['-c','from app import MOBILE_HTML; print(MOBILE_HTML)'],
 {cwd:path.join(__dirname,'..'),encoding:'utf8',stdio:['ignore','pipe','inherit'],
  env:{...process.env,PYTHONIOENCODING:'utf-8'}});
const script=html.split('<script nonce=')[1].split('>').slice(1).join('>').split('</script>')[0].replace('__SESSION_JSON__','"test-session"');
class Element{
 constructor(){this.hidden=false;this.disabled=false;this.textContent='';this.children=[];this.events={};this.files=[];this.value='';}
 addEventListener(name,fn){this.events[name]=fn;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
 setAttribute(){}
 click(){if(!this.disabled&&this.events.click)return this.events.click();}
}
function harness({status='approved',uploadCodes=[201],failPoll=0,holdUploads=false}={}){
 const elements=new Map();const scheduled=[];const uploads=[],requests=[];let pollNumber=0,inFlight=0,maxInFlight=0;
 const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 class XHR{
  constructor(){this.upload={};this.headers={};this.aborted=false;}
  open(method,url){this.method=method;this.url=url;}
  setRequestHeader(k,v){this.headers[k]=v;}
  abort(){this.aborted=true;inFlight--;if(this.onabort)this.onabort();}
  send(file){uploads.push(file);requests.push(this);inFlight++;maxInFlight=Math.max(maxInFlight,inFlight);
   this.upload.onprogress({lengthComputable:true,loaded:file.size,total:file.size||1});
   if(holdUploads)return;
   const code=uploadCodes.shift()??201;
   queueMicrotask(()=>{if(this.aborted)return;inFlight--;if(code==='network'){this.onerror();return;}
    this.status=code;this.responseText=JSON.stringify(code===201?{name:file.name}:{error:'Bị chặn'});this.onload();});}
 }
 const context=vm.createContext({document:{getElementById:get,createElement:()=>new Element()},
  history:{replaceState(){}},location:{protocol:'http:'},AbortController,XMLHttpRequest:XHR,
  setTimeout:(fn,ms)=>{scheduled.push({fn,ms});return scheduled.length;},clearTimeout(){},
  fetch:async()=>{pollNumber++;if(pollNumber<=failPoll)throw new Error('offline');return {status:status==='pending'?202:200,json:async()=>({status})};}});
 vm.runInContext(script,context);
 const flush=()=>new Promise(resolve=>setImmediate(resolve));
 async function select(files){get('files').files=files;await get('files').events.change();}
 async function pollAgain(){await vm.runInContext('poll()',context);await flush();}
 return {get,uploads,requests,flush,select,pollAgain,get maxInFlight(){return maxInFlight;},
  disconnect:()=>vm.runInContext("stop('Đã ngắt trên máy tính.')",context)};
}

test('pending receiver exposes no upload controls',async()=>{
 const h=harness({status:'pending'});await h.flush();
 assert.equal(h.get('controls').hidden,true);
 await h.select([{name:'a.txt',size:4}]);await h.get('send').events.click();assert.equal(h.uploads.length,0);
});
test('selection shows count/size and untrusted name as text',async()=>{
 const h=harness();await h.flush();await h.select([{name:'<img src=x onerror=alert(1)>',size:1024},{name:'b',size:1024}]);
 assert.equal(h.get('selection').textContent,'2 file · 2.0 KiB');assert.equal(h.get('queue').children[0].children[0].textContent,'<img src=x onerror=alert(1)>');
 assert.equal(h.get('send').disabled,false);
});
test('completed batch cannot be accidentally resent and new selection works',async()=>{
 const h=harness();await h.flush();await h.select([{name:'a.txt',size:4},{name:'b.txt',size:5}]);
 await h.get('send').events.click();assert.equal(h.uploads.length,2);assert.equal(h.get('files').value,'');
 assert.equal(h.get('send').hidden,true);assert.equal(h.get('pick').textContent,'Gửi thêm file');
 assert.equal(h.get('summary').textContent,'Đã lưu 2 / 2 file.');
 await h.get('send').events.click();assert.equal(h.uploads.length,2);
 await h.select([{name:'new.txt',size:1}]);await h.get('send').events.click();assert.equal(h.uploads.length,3);
});
test('oversized files are not sent, other files still succeed',async()=>{
 const h=harness();await h.flush();await h.select([{name:'huge.bin',size:5*1024**3+1},{name:'ok.txt',size:1}]);
 await h.get('send').events.click();assert.equal(h.uploads.length,1);assert.equal(h.get('summary').textContent,'Đã lưu 1 / 2 file · 1 file chưa xác nhận thành công.');
});
test('unauthorized upload stops remaining batch',async()=>{
 const h=harness({uploadCodes:[403]});await h.flush();await h.select([{name:'a',size:1},{name:'b',size:1}]);
 await h.get('send').events.click();assert.equal(h.uploads.length,1);assert.equal(h.get('controls').hidden,true);
 assert.equal(h.get('badge').textContent,'Đã ngắt');
});
test('lost upload response is not retried automatically',async()=>{
 const h=harness({uploadCodes:['network']});await h.flush();await h.select([{name:'a',size:1}]);
 await h.get('send').events.click();assert.equal(h.uploads.length,1);
 assert.match(h.get('results').children[0].children[2].textContent,/Kiểm tra file trên PC/);
 assert.equal(h.get('send').hidden,true);
});
test('temporary polling failure recovers without permanently ending session',async()=>{
 const h=harness({failPoll:1});await h.flush();assert.equal(h.get('pick').disabled,true);
 await h.pollAgain();assert.equal(h.get('controls').hidden,false);assert.equal(h.get('pick').disabled,false);
});
test('three polling failures end session with explicit recovery instruction',async()=>{
 const h=harness({failPoll:3});await h.flush();await h.pollAgain();await h.pollAgain();
 assert.equal(h.get('controls').hidden,true);assert.match(h.get('hint').textContent,/QR mới/);
});

test('500 selected files are sent sequentially once with the longer deadline',async()=>{
 const h=harness();await h.flush();
 const files=Array.from({length:500},(_,i)=>({name:`image-${i}.jpg`,size:1024}));
 await h.select(files);await h.get('send').events.click();
 assert.deepEqual(h.uploads,files);assert.equal(h.maxInFlight,1);
 assert.equal(h.get('summary').textContent,'Đã lưu 500 / 500 file.');
 assert.ok(h.requests.every(request=>request.timeout===12*60*60*1000));
 await h.get('send').events.click();assert.equal(h.uploads.length,500);
});

test('500 MiB and exact 5 GiB file metadata pass selection validation',async()=>{
 // XHR is mocked: this checks limits, not transmission of multi-gigabyte payloads.
 const h=harness();await h.flush();
 await h.select([{name:'video.mp4',size:500*1024**2},{name:'large.zip',size:5*1024**3}]);
 await h.get('send').events.click();assert.equal(h.uploads.length,2);
 assert.equal(h.get('summary').textContent,'Đã lưu 2 / 2 file.');
});

test('manual disconnect aborts active upload and prevents the rest of a large batch',async()=>{
 const h=harness({holdUploads:true});await h.flush();
 await h.select(Array.from({length:500},(_,i)=>({name:`file-${i}`,size:1})));
 const sending=h.get('send').events.click();await h.flush();
 h.disconnect();await sending;
 assert.equal(h.uploads.length,1);assert.equal(h.requests[0].aborted,true);
 assert.equal(h.get('controls').hidden,true);assert.equal(h.get('pick').disabled,true);
 assert.equal(h.get('summary').textContent,'Đã lưu 0 / 500 file · 500 file chưa xác nhận thành công.');
});
