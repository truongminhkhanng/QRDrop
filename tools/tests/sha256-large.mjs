// Explicit stress test: >4 GiB of logical input, one reusable 8 MiB buffer.
// This tests the browser hasher under Node; it is not a phone upload test.
import { Sha256 } from '../../src/utils/sha256.mjs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const block = new Uint8Array(8 * 1024 * 1024);
for (let i = 0; i < block.length; i++) block[i] = (i * 31 + (i >>> 8)) & 255;
const hash = new Sha256();
const reference = createHash('sha256');
const start = performance.now();
for (let i = 0; i < 513; i++) {
  hash.update(block);
  reference.update(block);
  if ((i + 1) % 64 === 0) console.log(`Hashed ${(i + 1) * 8} MiB`);
}
const tail = new Uint8Array([0, 1, 255]);
hash.update(tail); reference.update(tail);
assert.equal(hash.digest(), reference.digest('hex'));
console.log(JSON.stringify({
  result: 'PASS',
  bytes: 513 * block.length + tail.length,
  seconds: (performance.now() - start) / 1000,
  peakRssMiB: process.resourceUsage().maxRSS / 1024,
}));
