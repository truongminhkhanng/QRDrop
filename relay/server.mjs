import http from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { isIP } from 'node:net';
import { pipeline } from 'node:stream/promises';
import { Transform } from 'node:stream';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const credential = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const headers = {
  'cache-control': 'no-store', 'referrer-policy': 'no-referrer',
  'x-content-type-options': 'nosniff',
  'content-security-policy': "default-src 'self'; script-src 'self'; worker-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
};
function reply(res, status, message) {
  if (res.destroyed || res.writableEnded) return;
  res.writeHead(status, { ...headers, 'content-type': 'application/json; charset=utf-8', ...(status === 429 ? { 'retry-after': '60' } : {}) });
  res.end(JSON.stringify({ message }));
}
async function json(req, limit = 1024) {
  const chunks = []; let size = 0;
  for await (const chunk of req) { size += chunk.length; if (size > limit) throw new Error('body'); chunks.push(chunk); }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
function bounded(limit) {
  let size = 0;
  return new Transform({ transform(chunk, _, done) { size += chunk.length; done(size > limit ? new Error('body limit') : null, chunk); } });
}
function allowed(method, path) {
  return (method === 'GET' && (path === '/connect' || path === '/api/status' || /^\/assets\/[a-zA-Z0-9_.-]+$/.test(path))) ||
    (method === 'POST' && ['/api/connect', '/api/complete', '/api/cancel'].includes(path)) ||
    (method === 'POST' && /^\/api\/files\/[a-f0-9-]{36}\/finish$/.test(path)) ||
    (method === 'PUT' && /^\/api\/files\/[a-f0-9-]{36}\/chunks$/.test(path));
}

// Only the operator sets an origin/proxy. Browser-supplied forwarding headers
// are never identities. Production listens on loopback behind the HTTPS proxy.
export function createRelay({ origin, allowInsecureLoopback = false, trustedProxy = false, maxSessions = 512, maxPending = 128, requestTimeout = 90_000, pollTimeout = 20_000, sessionTimeout = 75_000, registryPath, testAssets } = {}) {
  const publicUrl = new URL(origin);
  if (publicUrl.pathname !== '/' || publicUrl.search || publicUrl.hash || publicUrl.username || publicUrl.password ||
      (publicUrl.protocol !== 'https:' && !(allowInsecureLoopback && publicUrl.protocol === 'http:' && publicUrl.hostname === '127.0.0.1'))) throw new Error('A public HTTPS origin is required');
  const sessions = new Map(), rates = new Map(); let pendingCount = 0;
  // Mobile code is operator-owned. A PC must never serve arbitrary JavaScript
  // under this shared origin and read another receiver's browser pairing keys.
  const assets = testAssets ?? new Map();
  if (!testAssets) {
    const root = fileURLToPath(new URL('../mobile-dist/', import.meta.url));
    assets.set('/connect', { body: fs.readFileSync(path.join(root, 'index.html')), type: 'text/html; charset=utf-8' });
    for (const name of fs.readdirSync(path.join(root, 'assets'))) {
      if (!/^[a-zA-Z0-9_.-]+$/.test(name)) continue;
      const type = name.endsWith('.js') ? 'text/javascript; charset=utf-8' : name.endsWith('.css') ? 'text/css; charset=utf-8' : 'application/octet-stream';
      assets.set(`/assets/${name}`, { body: fs.readFileSync(path.join(root, 'assets', name)), type });
    }
  }
  let registry = { namespace: randomUUID(), receivers: {} };
  if (registryPath) {
    try { registry = JSON.parse(fs.readFileSync(registryPath, 'utf8')); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (!/^[a-f0-9-]{36}$/.test(registry.namespace) || !registry.receivers || typeof registry.receivers !== 'object' || Array.isArray(registry.receivers) || Object.entries(registry.receivers).some(([id, hash]) => !/^[a-f0-9-]{36}$/.test(id) || !credential(hash))) throw new Error('Invalid receiver registry');
  } else if (!allowInsecureLoopback && !testAssets) throw new Error('A persistent receiver registry is required');
  function saveRegistry() {
    if (!registryPath) return;
    fs.writeFileSync(`${registryPath}.new`, JSON.stringify(registry), { mode: 0o600 });
    fs.renameSync(`${registryPath}.new`, registryPath);
  }
  saveRegistry();
  function rate(key, maximum) {
    const now = Date.now();
    for (const [key, value] of rates) if (now - value.at >= 60_000) rates.delete(key);
    let value = rates.get(key);
    if (!value) { if (rates.size >= 4096) return false; value = { at: now, count: 0 }; rates.set(key, value); }
    return ++value.count <= maximum;
  }
  function source(req) {
    const socket = req.socket.remoteAddress?.replace(/^::ffff:/, '');
    if (trustedProxy && ['127.0.0.1', '::1'].includes(socket)) {
      const forwarded = req.headers['x-qrdrop-client-ip'];
      return typeof forwarded === 'string' && isIP(forwarded) ? forwarded : null;
    }
    return socket && isIP(socket) ? socket : null;
  }
  function finish(session, item, status, message) {
    if (!session.pending.delete(item.id)) return;
    pendingCount--; clearTimeout(item.timer);
    session.queue = session.queue.filter(id => id !== item.id);
    item.reader?.destroy();
    reply(item.res, status, message);
    // Do not drain an attacker's body indefinitely on a persistent socket.
    if (!item.req.complete) item.res.once('finish', () => item.req.destroy());
  }
  function remove(id) {
    const session = sessions.get(id); if (!session) return;
    sessions.delete(id);
    if (session.poll) { clearTimeout(session.poll.timer); reply(session.poll.res, 410, 'Phiên đã kết thúc. Quét mã QR mới.'); }
    for (const item of [...session.pending.values()]) finish(session, item, 410, 'Phiên đã kết thúc. Quét mã QR mới.');
  }
  function dispatch(session) {
    if (!session.poll) return;
    const id = session.queue.shift(); if (!id) return;
    const item = session.pending.get(id); if (!item) return dispatch(session);
    const poll = session.poll; session.poll = null; clearTimeout(poll.timer);
    poll.res.writeHead(200, { ...headers, 'content-type': 'application/json' });
    poll.res.end(JSON.stringify({ id, method: item.req.method, path: item.path, peer: item.peer, headers: item.headers }));
  }
  const server = http.createServer({ maxHeaderSize: 16 * 1024 }, async (req, res) => {
    res.on('error', () => {}); req.on('error', () => {});
    try {
      if (req.headers.host !== publicUrl.host) return reply(res, 403, 'Địa chỉ truy cập không hợp lệ.');
      if (req.headers.origin && req.headers.origin !== publicUrl.origin) return reply(res, 403, 'Yêu cầu không được cho phép.');
      if (req.headers['sec-fetch-site'] && !['same-origin', 'none'].includes(req.headers['sec-fetch-site'])) return reply(res, 403, 'Yêu cầu không được cho phép.');
      const peer = source(req); if (!peer) return reply(res, 403, 'Không xác định được kết nối.');
      const path = req.url;
      if (req.method === 'GET' && path === '/health') { res.writeHead(200, headers); return res.end('ok'); }
      if (req.method === 'POST' && path === '/receiver') {
        if (!rate(`register:${peer}`, 100)) return reply(res, 429, 'Quá nhiều yêu cầu. Hãy thử lại sau một phút.');
        if (sessions.size >= maxSessions) return reply(res, 503, 'Máy chủ đang bận. Hãy thử lại.');
        const data = await json(req, 2048);
        if (!credential(data?.id) || !credential(data?.secret) || sessions.has(data.id)) return reply(res, 400, 'Yêu cầu không hợp lệ.');
        if (sessions.size >= maxSessions) return reply(res, 503, 'Máy chủ đang bận. Hãy thử lại.');
        if (!/^[a-f0-9-]{36}$/.test(data.receiver_id) || !credential(data.receiver_secret)) return reply(res, 400, 'Thiếu thông tin máy tính.');
        const digest = createHash('sha256').update(data.receiver_secret).digest('hex');
        const existing = registry.receivers[data.receiver_id];
        if (existing && !timingSafeEqual(Buffer.from(existing), Buffer.from(digest))) return reply(res, 403, 'Không có quyền đăng ký máy tính này.');
        if (!existing) {
          if (Object.keys(registry.receivers).length >= 100_000) return reply(res, 503, 'Máy chủ đang bận.');
          registry.receivers[data.receiver_id] = digest;
          try { saveRegistry(); } catch (error) { delete registry.receivers[data.receiver_id]; throw error; }
        }
        sessions.set(data.id, { secret: data.secret, receiverId: data.receiver_id, seen: Date.now(), queue: [], pending: new Map(), poll: null });
        res.writeHead(201, headers); return res.end();
      }
      const receiver = /^\/receiver\/([a-f0-9]{64})(?:\/(poll|requests\/([a-f0-9]{32})\/(body|response)))?$/.exec(path);
      if (receiver) {
        const [, id, route, requestId, operation] = receiver;
        const session = sessions.get(id);
        const secret = req.headers.authorization?.replace(/^Bearer /, '');
        if (!session || !credential(secret) || !timingSafeEqual(Buffer.from(secret), Buffer.from(session.secret))) return reply(res, 403, 'Không có quyền truy cập.');
        session.seen = Date.now();
        if (!route && req.method === 'DELETE') { remove(id); res.writeHead(204, headers); return res.end(); }
        if (route === 'poll' && req.method === 'POST') {
          if (session.poll) return reply(res, 409, 'Kết nối đang hoạt động.');
          const poll = { res, timer: null };
          poll.timer = setTimeout(() => { if (session.poll !== poll) return; session.poll = null; res.writeHead(204, headers); res.end(); }, pollTimeout);
          session.poll = poll;
          res.on('close', () => { if (session.poll === poll) session.poll = null; clearTimeout(poll.timer); });
          return dispatch(session);
        }
        const item = session.pending.get(requestId);
        if (!item) return reply(res, 410, 'Yêu cầu đã hết hạn.');
        if (operation === 'body' && req.method === 'GET') {
          if (item.reader || item.bodyRead) return reply(res, 409, 'Dữ liệu đã được đọc.');
          item.reader = res; item.bodyRead = true;
          res.writeHead(200, { ...headers, 'content-type': 'application/octet-stream', ...(item.req.headers['content-length'] ? { 'content-length': item.req.headers['content-length'] } : {}) });
          try { await pipeline(item.req, bounded(item.limit), res); }
          catch { finish(session, item, 400, 'Dữ liệu gửi bị gián đoạn.'); }
          return;
        }
        if (operation === 'response' && req.method === 'POST') {
          if (item.responding) return reply(res, 409, 'Yêu cầu đã được xử lý.');
          const status = Number(req.headers['x-qrdrop-status']);
          const type = req.headers['x-qrdrop-content-type'];
          if (!Number.isInteger(status) || status < 200 || status > 599 || typeof type !== 'string' || type.length > 128) return reply(res, 400, 'Phản hồi không hợp lệ.');
          item.responding = true;
          item.res.writeHead(status, { ...headers, 'content-type': type });
          try { await pipeline(req, bounded(4 * 1024 * 1024), item.res); res.writeHead(204, headers); res.end(); }
          catch { res.destroy(); }
          finally { finish(session, item, 502, 'Kết nối bị gián đoạn.'); }
          return;
        }
        return reply(res, 404, 'Không tìm thấy yêu cầu.');
      }
      const mobile = /^\/s\/([a-f0-9]{64})(\/[^?#]*)$/.exec(path);
      if (!mobile || !(allowed(req.method, mobile[2]) || (req.method === 'GET' && mobile[2] === '/identity'))) return reply(res, 404, 'Liên kết không còn hiệu lực. Quét mã QR mới.');
      const session = sessions.get(mobile[1]);
      if (!session || Date.now() - session.seen >= sessionTimeout) return reply(res, 410, 'Máy tính đang ngoại tuyến. Quét mã QR mới khi kết nối lại.');
      if (req.method === 'GET' && mobile[2] === '/identity') {
        res.writeHead(200, { ...headers, 'content-type': 'application/json' });
        return res.end(JSON.stringify({ receiver_id: session.receiverId, namespace: registry.namespace }));
      }
      if (req.method === 'GET' && (mobile[2] === '/connect' || mobile[2].startsWith('/assets/'))) {
        const asset = assets.get(mobile[2]);
        if (!asset) return reply(res, 404, 'Không tìm thấy tài nguyên.');
        res.writeHead(200, { ...headers, 'content-type': asset.type }); return res.end(asset.body);
      }
      if (req.method !== 'GET' && req.headers.origin !== publicUrl.origin) return reply(res, 403, 'Yêu cầu không được cho phép.');
      if (mobile[2] === '/api/connect' && !rate(`join:${peer}`, 60)) return reply(res, 429, 'Quá nhiều yêu cầu kết nối. Hãy thử lại sau một phút.');
      if (session.pending.size >= 16 || pendingCount >= maxPending) return reply(res, 503, 'Kết nối đang bận. Hãy thử lại.');
      const limit = req.method === 'PUT' ? 8 * 1024 * 1024 : 1024 * 1024;
      const length = req.headers['content-length'];
      if ((req.method === 'PUT' && length === undefined) || (length !== undefined && (!/^\d+$/.test(length) || Number(length) > limit))) return reply(res, 413, 'Dữ liệu vượt giới hạn của một yêu cầu.');
      const forwarded = {};
      for (const name of ['host', 'origin', 'sec-fetch-site', 'authorization', 'content-type', 'content-length', 'x-qrdrop-offset', 'x-qrdrop-length', 'x-qrdrop-sha256']) if (typeof req.headers[name] === 'string') forwarded[name] = req.headers[name];
      const id = randomBytes(16).toString('hex');
      const item = { id, req, res, path: mobile[2], peer, headers: forwarded, limit, reader: null, bodyRead: false, responding: false, timer: null };
      item.timer = setTimeout(() => finish(session, item, 504, 'Không nhận được phản hồi từ máy tính.'), requestTimeout);
      session.pending.set(id, item); session.queue.push(id); pendingCount++;
      res.on('close', () => finish(session, item, 499, 'Đã ngắt kết nối.'));
      req.on('aborted', () => finish(session, item, 400, 'Dữ liệu gửi bị gián đoạn.'));
      dispatch(session);
    } catch { reply(res, 400, 'Yêu cầu không hợp lệ.'); }
  });
  server.headersTimeout = 15_000; server.requestTimeout = requestTimeout + 10_000; server.keepAliveTimeout = 5000;
  server.maxConnections = 512;
  const sweeper = setInterval(() => { for (const [id, session] of sessions) if (Date.now() - session.seen >= sessionTimeout) remove(id); }, Math.min(sessionTimeout, 10_000));
  sweeper.unref();
  server.on('close', () => { clearInterval(sweeper); for (const id of [...sessions.keys()]) remove(id); });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = createRelay({ origin: process.env.QRDROP_PUBLIC_ORIGIN, trustedProxy: true, registryPath: process.env.QRDROP_REGISTRY_PATH });
  server.listen(Number(process.env.QRDROP_RELAY_PORT ?? 8787), '127.0.0.1', () => process.stdout.write('QRDrop relay ready on loopback.\n'));
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { server.close(); server.closeAllConnections(); });
}
