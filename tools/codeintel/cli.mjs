#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { DatabaseSync } from 'node:sqlite';
import ts from 'typescript';

export const SCHEMA = 1;
export const TOOL_VERSION = '0.1.0';
const defaultRoot = fileURLToPath(new URL('../../', import.meta.url));
const extensions = new Set(['.rs','.ts','.tsx','.js','.mjs','.css','.json','.toml','.yml','.yaml','.html']);
const ignoredDirectories = new Set(['node_modules','target','dist','mobile-dist','.git','.agent','.agents','.codex','.aws','HISTORY','gen','artifacts']);
const sensitive = /(^\.env|\.(pem|key|p12|pfx)$|credential|secret|^AGENT|^CLAUDE|^CONFIG\.md|^SKILL|^MEMORY|^LONG_TERM_MEMORY)/i;
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const lineAt = (text, index) => text.slice(0,index).split('\n').length;
const normalized = value => value.replace(/[^a-zA-Z0-9_/.:#-]/g, ' ').toLowerCase();
const glob = pattern => new RegExp('^' + pattern.split('**').map(part => part.split('*').map(s => s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('[^/]*')).join('.*') + '$');

function scan(root) {
  const ignorePath = path.join(root,'.agent/codegraph-ignore');
  const rules = fs.existsSync(ignorePath) ? fs.readFileSync(ignorePath,'utf8').split('\n').filter(s => s.trim() && !s.startsWith('#')).map(glob) : [];
  const result = new Map();
  function walk(directory) {
    for (const entry of fs.readdirSync(directory,{withFileTypes:true})) {
      if (entry.isSymbolicLink()) continue;
      const full = path.join(directory,entry.name), relative = path.relative(root,full).split(path.sep).join('/');
      if (ignoredDirectories.has(entry.name) || sensitive.test(entry.name) || rules.some(rule => rule.test(relative))) continue;
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile() && extensions.has(path.extname(entry.name)) && !/lock/i.test(entry.name)) {
        const stat = fs.statSync(full); if (stat.size > 2 * 1024 * 1024) continue;
        const text = fs.readFileSync(full,'utf8');
        result.set(relative,{path:relative,hash:hash(text),mtime:stat.mtimeMs,size:stat.size,language:path.extname(relative).slice(1),text});
      }
    }
  }
  walk(root);
  // Manifest/lock hashes influence freshness without indexing dependency bodies or values.
  const manifests = {};
  for (const name of ['package.json','package-lock.json','tsconfig.json','src-tauri/Cargo.toml','src-tauri/Cargo.lock','.agent/codegraph-ignore']) {
    const full = path.join(root,name); manifests[name] = fs.existsSync(full) ? hash(fs.readFileSync(full)) : null;
  }
  return {files:result,manifestHash:hash(JSON.stringify(manifests))};
}
function connect(root) {
  const directory = path.join(root,'.agent'); fs.mkdirSync(directory,{recursive:true});
  const db = new DatabaseSync(path.join(directory,'codegraph.sqlite'));
  db.exec(`PRAGMA foreign_keys=ON; CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,hash TEXT,mtime REAL,size INTEGER,language TEXT,module TEXT);
    CREATE TABLE IF NOT EXISTS symbols(id TEXT PRIMARY KEY,name TEXT,qualified TEXT,kind TEXT,file TEXT,start INTEGER,end INTEGER,exported INTEGER,confidence REAL);
    CREATE TABLE IF NOT EXISTS edges(source TEXT,target TEXT,kind TEXT,file TEXT,line INTEGER,confidence REAL);
    CREATE INDEX IF NOT EXISTS names ON symbols(name); CREATE INDEX IF NOT EXISTS symbols_file ON symbols(file);
    CREATE INDEX IF NOT EXISTS edge_source ON edges(source); CREATE INDEX IF NOT EXISTS edge_target ON edges(target);`);
  return db;
}
function fresh(db, scanResult) {
  const indexed = new Map(db.prepare('SELECT path,hash FROM files').all().map(row => [row.path,row.hash]));
  const changed = [...scanResult.files.values()].filter(file => indexed.get(file.path) !== file.hash).map(file => file.path);
  const removed = [...indexed.keys()].filter(file => !scanResult.files.has(file));
  const meta = Object.fromEntries(db.prepare('SELECT key,value FROM meta').all().map(row => [row.key,row.value]));
  const exists = meta.schema !== undefined;
  const schemaMismatch = exists && Number(meta.schema) !== SCHEMA;
  const toolMismatch = exists && meta.tool_version !== TOOL_VERSION;
  const manifestChanged = exists && meta.manifest_hash !== scanResult.manifestHash;
  return {exists,stale:!exists || schemaMismatch || toolMismatch || manifestChanged || changed.length>0 || removed.length>0,changed,removed,manifestChanged,schemaMismatch,toolMismatch,lastIndexed:meta.indexed_at ?? null,schemaVersion:SCHEMA,indexedSchema:meta.schema ? Number(meta.schema) : null,toolVersion:TOOL_VERSION};
}
function rustMask(text) {
  // Conservative lexical fallback; Rust is not type-resolved. Preserve offsets/newlines.
  return text.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*|r#*"[\s\S]*?"#*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])'/g, value => value.replace(/[^\n]/g,' '));
}
function balancedEnd(mask,start) {
  let depth = 0;
  for (let i=start;i<mask.length;i++) { if (mask[i]==='{') depth++; if (mask[i]==='}' && --depth===0) return i+1; }
  return start;
}
export function parseFile(file) {
  const symbols=[], edges=[];
  const add = (name,kind,start,end,exported=false,confidence=1,qualified=name) => {
    const id=`${file.path}#${qualified}:${lineAt(file.text,start)}`;
    const symbol={id,name,qualified:`${file.path}#${qualified}`,kind,file:file.path,start:lineAt(file.text,start),end:lineAt(file.text,end),exported:Number(exported),confidence,offset:start,finish:end};
    symbols.push(symbol); return id;
  };
  const edge = (source,target,kind,position,confidence) => edges.push({source,target,kind,file:file.path,line:lineAt(file.text,position),confidence});
  const owner = position => symbols.filter(s=>s.offset<=position && s.finish>=position && ['function','method','component'].includes(s.kind)).sort((a,b)=>(a.finish-a.offset)-(b.finish-b.offset))[0]?.id ?? `file:${file.path}`;
  if (['ts','tsx','js','mjs'].includes(file.language)) {
    const source = ts.createSourceFile(file.path,file.text,ts.ScriptTarget.Latest,true,file.language==='tsx'?ts.ScriptKind.TSX:ts.ScriptKind.TS);
    const declare = node => {
      const exported=node.modifiers?.some(m=>m.kind===ts.SyntaxKind.ExportKeyword) ?? false;
      if ((ts.isFunctionDeclaration(node)||ts.isClassDeclaration(node)||ts.isInterfaceDeclaration(node)||ts.isTypeAliasDeclaration(node)||ts.isMethodDeclaration(node)) && node.name) {
        const name=node.name.getText(source);
        const kind=ts.isClassDeclaration(node)?'class':ts.isMethodDeclaration(node)?'method':ts.isInterfaceDeclaration(node)||ts.isTypeAliasDeclaration(node)?'type':/^[A-Z]/.test(name)?'component':'function';
        const qualified=ts.isMethodDeclaration(node)&&node.parent.name?`${node.parent.name.getText(source)}.${name}`:name;
        add(name,kind,node.getStart(source),node.end,exported,1,qualified);
      }
      if (ts.isVariableDeclaration(node)&&ts.isIdentifier(node.name)) {
        const callable=node.initializer&&(ts.isArrowFunction(node.initializer)||ts.isFunctionExpression(node.initializer));
        add(node.name.text,callable?(/^[A-Z]/.test(node.name.text)?'component':'function'):'variable',node.getStart(source),node.end,false);
      }
      ts.forEachChild(node,declare);
    }; declare(source);
    const relations = node => {
      if (ts.isImportDeclaration(node)&&ts.isStringLiteral(node.moduleSpecifier)) edge(`file:${file.path}`,`import:${node.moduleSpecifier.text}`,'imports',node.getStart(source),1);
      if (ts.isExportDeclaration(node)&&node.moduleSpecifier&&ts.isStringLiteral(node.moduleSpecifier)) edge(`file:${file.path}`,`import:${node.moduleSpecifier.text}`,'exports',node.getStart(source),1);
      if (ts.isCallExpression(node)) { const name=ts.isPropertyAccessExpression(node.expression)?node.expression.name.text:ts.isIdentifier(node.expression)?node.expression.text:null; if(name) edge(owner(node.getStart(source)),`call:${name}`,'calls',node.getStart(source),.55); }
      if ((ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node))&&/^[A-Z]/.test(node.tagName.getText(source))) edge(owner(node.getStart(source)),`call:${node.tagName.getText(source)}`,'renders',node.getStart(source),.7);
      if (ts.isJsxAttribute(node)&&node.name.getText(source)==='className'&&node.initializer) {
        const literal=ts.isStringLiteral(node.initializer)?node.initializer:ts.isJsxExpression(node.initializer)&&node.initializer.expression&&ts.isStringLiteral(node.initializer.expression)?node.initializer.expression:null;
        if(literal) for(const token of literal.text.split(/\s+/).filter(Boolean)) edge(owner(node.getStart(source)),`style:${token}`,'uses_style',node.getStart(source),1);
      }
      ts.forEachChild(node,relations);
    }; relations(source);
  } else if (file.language==='rs') {
    const mask=rustMask(file.text);
    for(const match of mask.matchAll(/\b(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(fn|struct|enum|trait|const|type|mod)\s+([A-Za-z_]\w*)/g)) {
      const start=match.index, body=mask.indexOf('{',start), semicolon=mask.indexOf(';',start);
      const end=body>=0&&(semicolon<0||body<semicolon)?balancedEnd(mask,body):semicolon>=0?semicolon+1:start+match[0].length;
      add(match[2],match[1]==='fn'?'function':match[1]==='struct'?'class':match[1],start,end,/^pub/.test(match[0]),.65);
    }
    for(const match of mask.matchAll(/\buse\s+([^;]+);/g)) {
      for(const name of match[1].match(/[A-Za-z_]\w*/g)??[]) if(!['crate','self','super','std','tokio','axum','serde'].includes(name)) edge(`file:${file.path}`,`rust_module:${name}`,'imports',match.index,.45);
    }
    for(const match of mask.matchAll(/\b([A-Za-z_]\w*)\s*\(/g)) {
      const prefix=mask.slice(Math.max(0,match.index-12),match.index);
      if(!/\bfn\s*$/.test(prefix)&&!['if','while','match','for','Some','Ok','Err'].includes(match[1])) edge(owner(match.index),`call:${match[1]}`,'calls',match.index,.4);
    }
    for(const match of file.text.matchAll(/\.route\(\s*"([^"\n]+)"\s*,\s*(get|post|put|delete)\(\s*(\w+)\s*\)/g)) {
      const route=add(`${match[2].toUpperCase()} ${match[1]}`,'route',match.index,match.index+match[0].length,false,.75);
      edge(route,`call:${match[3]}`,'route_handler',match.index,.75);
    }
  } else if (file.language==='css') {
    for(const match of file.text.matchAll(/\.([A-Za-z_-][\w-]*)|(--[\w-]+)\s*:/g)) add(match[1]??match[2],match[1]?'selector':'style_token',match.index,match.index+match[0].length,false,.85);
  } else if (['json','toml','yml','yaml'].includes(file.language)) {
    // Keys only: values (including secrets) are never copied into index metadata.
    for(const match of file.text.matchAll(/(?:"([\w.-]+)"\s*:|^\s*([\w.-]+)\s*[=:])/gm)) add(match[1]??match[2],'config_key',match.index,match.index+match[0].length,false,.8);
  }
  add(path.basename(file.path),'file',0,file.text.length,false,1,file.path);
  return {symbols,edges};
}
function resolveEdges(db, files) {
  const symbols=db.prepare('SELECT * FROM symbols').all();
  const byName=new Map(); for(const symbol of symbols) { const list=byName.get(symbol.name)??[];list.push(symbol);byName.set(symbol.name,list); }
  const records=db.prepare('SELECT rowid,* FROM edges').all();
  const update=db.prepare('UPDATE edges SET target=?,confidence=? WHERE rowid=?');
  for(const record of records) {
    if(record.target.startsWith('import:')) {
      const specifier=record.target.slice(7);
      if(specifier.startsWith('.')) {
        const base=path.posix.normalize(path.posix.join(path.posix.dirname(record.file),specifier));
        const target=[base,...['.ts','.tsx','.mjs','.js','.css','/index.ts','/index.tsx'].map(ext=>base+ext)].find(candidate=>files.has(candidate));
        if(target) update.run(`file:${target}`,record.confidence,record.rowid);
      }
    } else if(record.target.startsWith('rust_module:')) {
      const name=record.target.slice(12), options=[...files.keys()].filter(file=>file.endsWith(`/${name}.rs`));
      if(options.length===1) update.run(`file:${options[0]}`,Math.min(record.confidence,.45),record.rowid);
    } else if(record.target.startsWith('call:') || record.target.startsWith('style:')) {
      const style=record.target.startsWith('style:'), name=record.target.slice(style?6:5);
      const candidates=(byName.get(name)??[]).filter(symbol=>style?symbol.kind==='selector':['function','method','component','class'].includes(symbol.kind));
      const local=candidates.filter(symbol=>symbol.file===record.file);
      const chosen=local.length===1?local[0]:candidates.length===1?candidates[0]:null;
      if(chosen) update.run(chosen.id,Math.min(record.confidence,style?.6:local.length===1?.8:.4),record.rowid);
    }
  }
  // Test-to-source is a naming/dependency hint, not proof of coverage.
  const insert=db.prepare('INSERT INTO edges VALUES(?,?,?,?,?,?)');
  for(const file of files.keys()) if(/test|tests|spec/.test(file)) {
    const stem=path.basename(file).replace(/\.(test|spec)/,'').split('.')[0];
    for(const candidate of files.keys()) if(candidate!==file && path.basename(candidate).split('.')[0]===stem) insert.run(`file:${file}`,`file:${candidate}`,'test_hint',file,1,.3);
  }
}
export function execute(root,command,query='') {
  const scanResult=scan(root), db=connect(root);
  try {
    const current=fresh(db,scanResult);
    if(command==='status') return {...current,files:db.prepare('SELECT COUNT(*) AS n FROM files').get().n,symbols:db.prepare('SELECT COUNT(*) AS n FROM symbols').get().n};
    if(command==='index'||command==='update') {
      const full=command==='index'||!current.exists||current.schemaMismatch||current.toolMismatch;
      const changed=full?[...scanResult.files.keys()]:current.changed;
      db.exec('BEGIN IMMEDIATE');
      try {
        if(full) db.exec('DELETE FROM edges; DELETE FROM symbols; DELETE FROM files;');
        const delSymbols=db.prepare('DELETE FROM symbols WHERE file=?'), delFiles=db.prepare('DELETE FROM files WHERE path=?');
        const putFile=db.prepare('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?)');
        const putSymbol=db.prepare('INSERT OR REPLACE INTO symbols VALUES(?,?,?,?,?,?,?,?,?)');
        for(const removed of current.removed) { delSymbols.run(removed);delFiles.run(removed); }
        for(const name of changed) {
          const file=scanResult.files.get(name);delSymbols.run(name);putFile.run(name,file.hash,file.mtime,file.size,file.language,path.posix.dirname(name));
          for(const symbol of parseFile(file).symbols) putSymbol.run(symbol.id,symbol.name,symbol.qualified,symbol.kind,symbol.file,symbol.start,symbol.end,symbol.exported,symbol.confidence);
        }
        // Persist raw edge drafts per file; unchanged files are not reparsed on update.
        db.exec('CREATE TABLE IF NOT EXISTS edge_drafts(file TEXT PRIMARY KEY,hash TEXT,data TEXT);');
        if(full) db.exec('DELETE FROM edge_drafts');
        for(const removed of current.removed) db.prepare('DELETE FROM edge_drafts WHERE file=?').run(removed);
        for(const name of changed) { const file=scanResult.files.get(name); db.prepare('INSERT OR REPLACE INTO edge_drafts VALUES(?,?,?)').run(name,file.hash,JSON.stringify(parseFile(file).edges)); }
        db.exec('DELETE FROM edges');
        const insert=db.prepare('INSERT INTO edges VALUES(?,?,?,?,?,?)');
        for(const row of db.prepare('SELECT data FROM edge_drafts').all()) for(const edge of JSON.parse(row.data)) insert.run(edge.source,edge.target,edge.kind,edge.file,edge.line,edge.confidence);
        resolveEdges(db,scanResult.files);
        const putMeta=db.prepare('INSERT OR REPLACE INTO meta VALUES(?,?)');
        const indexedAt=new Date().toISOString();
        for(const [key,value] of Object.entries({schema:String(SCHEMA),tool_version:TOOL_VERSION,indexed_at:indexedAt,manifest_hash:scanResult.manifestHash})) putMeta.run(key,value);
        db.exec('COMMIT');
        fs.writeFileSync(path.join(root,'.agent/codegraph-state.json'),JSON.stringify({schema:SCHEMA,toolVersion:TOOL_VERSION,indexedAt,manifestHash:scanResult.manifestHash},null,2)+'\n');
        return {mode:full?'full':'incremental',updated:changed,removed:current.removed,files:db.prepare('SELECT COUNT(*) AS n FROM files').get().n,symbols:db.prepare('SELECT COUNT(*) AS n FROM symbols').get().n,relationships:db.prepare('SELECT kind,COUNT(*) AS count FROM edges GROUP BY kind').all()};
      } catch(error) { db.exec('ROLLBACK');throw error; }
    }
    if(current.stale) return {error:'Index is stale. Run npm run codeintel -- update before querying.',status:current};
    const symbols=db.prepare('SELECT * FROM symbols').all();
    const terms=normalized(query).split(/\s+/).filter(Boolean);
    const selected=symbols.map(symbol=>({symbol,score:terms.reduce((score,term)=>score+(normalized(`${symbol.name} ${symbol.file} ${symbol.kind}`).includes(term)?1:0),0)})).filter(item=>item.score>0).sort((a,b)=>b.score-a.score||a.symbol.file.localeCompare(b.symbol.file));
    if(command==='search') return {query,matches:selected.slice(0,60).map(item=>item.symbol)};
    const edges=db.prepare('SELECT * FROM edges').all();
    const targetIds=new Set(selected.map(item=>item.symbol.id));
    const targetFiles=new Set(selected.map(item=>item.symbol.file));
    if(command==='callers'||command==='callees') return {query,matches:selected.slice(0,20).map(item=>item.symbol),relationships:edges.filter(edge=>command==='callers'?targetIds.has(edge.target):targetIds.has(edge.source))};
    if(command==='explore'||command==='impact') {
      const related=edges.filter(edge=>targetIds.has(edge.source)||targetIds.has(edge.target)||targetFiles.has(edge.file)||targetFiles.has(edge.target.replace(/^file:/,'')));
      const affected=new Set(targetFiles);
      const reasons=[];
      for(const edge of related) { affected.add(edge.file); if(edge.target.startsWith('file:')) affected.add(edge.target.slice(5)); const symbol=symbols.find(s=>s.id===edge.target);if(symbol)affected.add(symbol.file); }
      for(const file of affected) reasons.push({file,reason:targetFiles.has(file)?'query match':'relationship hint; verify source'});
      const tests=[...affected].filter(file=>/test|tests|spec/.test(file));
      if([...affected].some(file=>file.startsWith('src-tauri/src/'))) tests.push('src-tauri/tests/receiver.rs');
      if([...affected].some(file=>/sha256|hash.worker/.test(file))) tests.push('tools/tests/sha256.test.mjs');
      return {query,relevantFiles:reasons,relevantSymbols:selected.slice(0,40).map(item=>item.symbol),relationships:related.slice(0,100),routes:symbols.filter(s=>s.kind==='route'&&affected.has(s.file)),tests:[...new Set(tests)],impactHints:['Inspect actual source ranges before editing.','Unresolved call:/import:/style: targets are NOT confirmed relationships.','Rust calls, cross-file JS calls, test hints and global CSS matching are heuristic.','Dynamic className expressions are omitted; use rg and browser inspection.'],confidence:'per-symbol/per-edge; no type-checked Rust call graph'};
    }
    throw new Error(`Unknown command: ${command}`);
  } finally { db.close(); }
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const args=process.argv.slice(2), rootIndex=args.indexOf('--root');
  const root=rootIndex>=0?path.resolve(args.splice(rootIndex,2)[1]):defaultRoot;
  try {
    const result=execute(root,args[0]??'status',args.slice(1).join(' '));
    console.log(JSON.stringify(result,null,2));
    if(result.error) process.exitCode=1;
  } catch(error) { console.error(error.message);process.exitCode=1; }
}
