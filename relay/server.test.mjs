import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomBytes, randomUUID } from 'node:crypto';
import { createRelay } from './server.mjs';

async function fixture(t, options = {}) {
  const server = createRelay({ origin: 'https://receiver.example', testAssets: new Map([['/connect', { body: '<html>fixture</html>', type: 'text/html' }]]), ...options });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); });
  const base = `http://127.0.0.1:${server.address().port}`;
  const id = randomBytes(32).toString('hex'), secret = randomBytes(32).toString('hex');
  const request = (path, options = {}) => fetch(base + path, { ...options, headers: { host: 'receiver.example', ...options.headers } });
  const receiver = (path, options = {}) => request(`/receiver/${id}${path}`, { ...options, headers: { authorization: `Bearer ${secret}`, ...options.headers } });
  const receiverId = randomUUID(), receiverSecret = randomBytes(32).toString('hex');
  const registration = await request('/receiver', { method: 'POST', body: JSON.stringify({ id, secret, receiver_id: receiverId, receiver_secret: receiverSecret }) });
  assert.equal(registration.status, 201);
  return { server, id, secret, receiverId, receiverSecret, request, receiver };
}
test('reverse bridge streams a body and preserves the receiver response', async t => {
  const h = await fixture(t);
  const data = randomBytes(1024 * 1024 + 17);
  const phone = h.request(`/s/${h.id}/api/files/00000000-0000-0000-0000-000000000000/chunks`, {
    method: 'PUT', body: data, headers: { origin: 'https://receiver.example', 'content-type': 'application/octet-stream', 'x-qrdrop-length': String(data.length), 'x-qrdrop-sha256': 'fixture' },
  });
  const metadata = await (await h.receiver('/poll', { method: 'POST' })).json();
  assert.equal(metadata.peer, '127.0.0.1');
  assert.equal(metadata.headers.origin, 'https://receiver.example');
  assert.deepEqual(Buffer.from(await (await h.receiver(`/requests/${metadata.id}/body`)).arrayBuffer()), data);
  const ack = await h.receiver(`/requests/${metadata.id}/response`, { method: 'POST', headers: { 'x-qrdrop-status': '200', 'x-qrdrop-content-type': 'application/json' }, body: JSON.stringify({ offset: data.length }) });
  assert.equal(ack.status, 204);
  const received = await phone;
  assert.equal(received.status, 200);
  assert.deepEqual(await received.json(), { offset: data.length });
  assert.equal(received.headers.get('cache-control'), 'no-store');
});
test('requires receiver credentials, exact origin and restricted mobile routes', async t => {
  const h = await fixture(t);
  assert.equal((await h.request(`/receiver/${h.id}/poll`, { method: 'POST', headers: { authorization: `Bearer ${'0'.repeat(64)}` } })).status, 403);
  assert.equal((await h.request(`/s/${h.id}/api/connect`, { method: 'POST', headers: { origin: 'https://attacker.example' }, body: '{}' })).status, 403);
  assert.equal((await h.request(`/s/${h.id}/api/connect`, { method: 'POST', body: '{}' })).status, 403);
  assert.equal((await h.request(`/s/${h.id}/api/approve`, { method: 'POST', headers: { origin: 'https://receiver.example' }, body: '{}' })).status, 404);
  assert.equal((await h.request(`/s/${h.id}/assets/../private`)).status, 404);
});
test('caps concurrent requests and revokes all waiting requests when receiving stops', async t => {
  const h = await fixture(t, { maxPending: 1 });
  const first = h.request(`/s/${h.id}/api/status`);
  await h.receiver('/poll', { method: 'POST' }); // First request is now queued in the bridge.
  assert.equal((await h.request(`/s/${h.id}/api/status`)).status, 503);
  assert.equal((await h.receiver('', { method: 'DELETE' })).status, 204);
  assert.equal((await first).status, 410);
  assert.equal((await h.request(`/s/${h.id}/connect`)).status, 410);
  assert.equal((await h.receiver('/poll', { method: 'POST' })).status, 403);
});
test('untrusted forwarded headers cannot change the source identity', async t => {
  const h = await fixture(t);
  const phone = h.request(`/s/${h.id}/api/status`, { headers: { 'x-qrdrop-client-ip': '203.0.113.44', 'x-forwarded-for': '203.0.113.44' } });
  const metadata = await (await h.receiver('/poll', { method: 'POST' })).json();
  assert.equal(metadata.peer, '127.0.0.1');
  assert.equal(metadata.headers['x-forwarded-for'], undefined);
  await h.receiver('', { method: 'DELETE' });
  assert.equal((await phone).status, 410);
});
test('unknown receiver requests expire instead of holding a browser forever', async t => {
  const h = await fixture(t, { requestTimeout: 40 });
  assert.equal((await h.request(`/s/${h.id}/api/status`)).status, 504);
});
test('production origins require HTTPS and test HTTP must be loopback', () => {
  assert.throws(() => createRelay({ origin: 'http://receiver.example' }));
  assert.throws(() => createRelay({ origin: 'http://192.168.1.2', allowInsecureLoopback: true }));
  assert.throws(() => createRelay({ origin: 'https://receiver.example/path' }));
});
