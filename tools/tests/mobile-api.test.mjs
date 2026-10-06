import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

// Unit tests of the actual mobile API module; controlled fetch responses are
// browser-network fixtures, not an end-to-end receiver or phone simulation.
const compile = file => ts.transpileModule(fs.readFileSync(new URL(file, import.meta.url), 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText;
const moduleUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const typesUrl = moduleUrl(compile('../../src/types/index.ts'));
const apiSource = compile('../../src/mobile/api.ts');
assert(apiSource.includes("from '../types'"));
const api = await import(moduleUrl(apiSource.replace("from '../types'", `from '${typesUrl}'`) + '\n//# sourceURL=qrdrop-mobile-api-unit.js'));
const approved = { state: 'APPROVED', grant: 'fixture-grant', files: [], error: null };

function timers(t) {
  const previous = globalThis.window;
  globalThis.window = { setTimeout: callback => setTimeout(callback, 0) };
  t.after(() => { if (previous === undefined) delete globalThis.window; else globalThis.window = previous; });
}

test('status polling retries a temporary network disconnect', async t => {
  timers(t);
  let requests = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    if (++requests === 1) throw new TypeError('fixture: disconnected');
    return Response.json(approved);
  });
  assert.deepEqual(await api.poll('fixture-attempt', new AbortController().signal), approved);
  assert.equal(requests, 2);
});

test('status polling stops immediately on rejected credentials', async t => {
  timers(t);
  let requests = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    requests++;
    return Response.json({ message: 'Denied' }, { status: 403 });
  });
  await assert.rejects(api.poll('fixture-attempt', new AbortController().signal), error => error instanceof api.HttpError && error.status === 403);
  assert.equal(requests, 1);
});

test('status polling retries transient HTTP errors and limits retries', async t => {
  timers(t);
  let requests = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    const code = [408, 429, 503][requests++];
    return code ? Response.json({ message: 'Retry' }, { status: code }) : Response.json(approved);
  });
  assert.deepEqual(await api.poll('fixture-attempt', new AbortController().signal), approved);
  assert.equal(requests, 4);
  requests = 0;
  t.mock.method(globalThis, 'fetch', async () => { requests++; throw new TypeError('fixture: offline'); });
  await assert.rejects(api.poll('fixture-attempt', new AbortController().signal), error => error instanceof api.HttpError && error.status === 0);
  assert.equal(requests, 9);
});

test('cancelling during retry backoff stops further requests', async t => {
  timers(t);
  const controller = new AbortController();
  let requests = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    requests++;
    queueMicrotask(() => controller.abort());
    throw new TypeError('fixture: offline');
  });
  await assert.rejects(api.poll('fixture-attempt', controller.signal));
  assert.equal(requests, 1);
});
