import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { digest, sha256Fallback } from '../web/port/sha256.js';

test('HTTP LAN fingerprints match native SHA-256, including padding and subarrays', async () => {
  const inputs=[Buffer.from(''),Buffer.from('abc'),Buffer.alloc(1000000,97)];
  for (const length of [55,56,63,64,65,119,120,127,128,129,1048577]) inputs.push(randomBytes(length+19).subarray(19));
  for (const input of inputs) {
    const expected=createHash('sha256').update(input).digest('hex');
    assert.equal(await sha256Fallback(input),expected,`fallback length ${input.length}`);
    assert.equal(await digest(input),expected,`Web Crypto length ${input.length}`);
  }
  assert.equal(await sha256Fallback(new ArrayBuffer(0)),createHash('sha256').digest('hex'));
});
