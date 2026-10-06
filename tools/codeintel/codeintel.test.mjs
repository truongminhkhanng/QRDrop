import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execute } from './cli.mjs';

test('local graph: AST, styles, stale hashes, incremental update, deletion, secret exclusion', () => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'qrdrop-codeintel-'));
  try {
    fs.writeFileSync(path.join(root,'App.tsx'),'import "./style.css"; export function App(){ return <button className="receive-button" onClick={send}>Receive</button>; } export function send(){return 1;}');
    fs.writeFileSync(path.join(root,'style.css'),'.receive-button { color: var(--accent); } :root { --accent: green; }');
    fs.writeFileSync(path.join(root,'.env'),'SECRET=must-never-enter-cache');
    fs.writeFileSync(path.join(root,'config.json'),' {"api_secret":"must-never-enter-cache"}');
    assert.equal(execute(root,'status').exists,false);
    assert.equal(execute(root,'index').mode,'full');
    assert.equal(execute(root,'status').stale,false);
    assert(execute(root,'search','App').matches.some(s=>s.kind==='component'));
    assert(execute(root,'explore','App').relationships.some(e=>e.kind==='uses_style'&&e.target.includes('receive-button')));
    const before=fs.statSync(path.join(root,'App.tsx'));
    const original=fs.readFileSync(path.join(root,'App.tsx'),'utf8');
    fs.writeFileSync(path.join(root,'App.tsx'),original.replace('return 1','return 2'));
    fs.utimesSync(path.join(root,'App.tsx'),before.atime,before.mtime);
    assert.deepEqual(execute(root,'status').changed,['App.tsx']);
    const update=execute(root,'update');assert.equal(update.mode,'incremental');assert.deepEqual(update.updated,['App.tsx']);
    assert.equal(execute(root,'status').stale,false);
    assert.equal(execute(root,'update').updated.length,0);
    const cache=fs.readFileSync(path.join(root,'.agent/codegraph.sqlite'));
    assert.equal(cache.includes(Buffer.from('must-never-enter-cache')),false);
    fs.unlinkSync(path.join(root,'style.css'));
    assert.deepEqual(execute(root,'update').removed,['style.css']);
    assert.equal(execute(root,'status').stale,false);
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
test('Rust graph includes real route/handler hints and callers',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'qrdrop-rust-index-'));
  try {
    fs.writeFileSync(path.join(root,'server.rs'),'fn router() { Router::new().route("/api/connect", post(connect)); }\nasync fn connect() { authorize(); }\nfn authorize() {}');
    execute(root,'index');
    assert(execute(root,'search','connect').matches.some(s=>s.kind==='route'));
    assert(execute(root,'callers','authorize').relationships.some(e=>e.kind==='calls'));
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
