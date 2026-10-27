import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLodDirectory } from '../lib/assets.mjs';
import { readFile } from 'node:fs/promises';

function directory() {
  const data=Buffer.alloc(128);
  data.write('LOD\0');data.writeUInt32LE(1,8);data.write('TEST.TXT',92);
  data.writeUInt32LE(124,108);data.writeUInt32LE(4,112);data.write('test',124);
  return data;
}
test('LOD indexes original byte ranges without accepting out-of-file extents',()=>{
  const data=directory();
  assert.deepEqual(parseLodDirectory(data),[{name:'TEST.TXT',offset:124,size:4,compressed:0}]);
  data.writeUInt32LE(127,108);assert.throws(()=>parseLodDirectory(data),/Invalid LOD entry/);
});
test('LOD rejects truncated directories and invalid signatures',()=>{
  assert.throws(()=>parseLodDirectory(directory().subarray(0,100)),/Truncated/);
  const data=directory();data[0]=0;assert.throws(()=>parseLodDirectory(data),/signature/);
});
test('upstream WASM parsers reject malformed inputs without trapping',async()=>{
  const {instance}=await WebAssembly.instantiate(await readFile(new URL('../web/engine.wasm',import.meta.url)));
  const e=instance.exports;
  for(const length of [0,4,100]){
    const ptr=e.input_buffer(length);new Uint8Array(e.memory.buffer,ptr,length).fill(0);
    assert.equal(e.parse_map(),0);assert.ok(e.output_len()>0);
    assert.equal(e.sprite_info(),0);assert.ok(e.output_len()>0);
  }
});
