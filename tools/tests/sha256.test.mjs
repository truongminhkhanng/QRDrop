import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { Sha256 } from '../../src/utils/sha256.mjs';
test('incremental SHA-256 matches independent node:crypto, padding and arbitrary chunks',()=>{
  const inputs=[Buffer.alloc(0),Buffer.from('abc'),Buffer.alloc(1_000_000,97),...Array.from({length:140},(_,n)=>randomBytes(n)),randomBytes(8*1024*1024+73)];
  for(const input of inputs) {
    const expected=createHash('sha256').update(input).digest('hex');
    for(const chunk of [1,63,64,65,4093,8*1024*1024]) {
      if(input.length>100000 && chunk<4093) continue;
      const hash=new Sha256();for(let offset=0;offset<input.length;offset+=chunk)hash.update(input.subarray(offset,offset+chunk));
      assert.equal(hash.digest(),expected);assert.equal(hash.digest(),expected);
    }
  }
});
