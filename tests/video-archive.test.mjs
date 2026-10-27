import test from 'node:test';
import assert from 'node:assert/strict';
import {parseVideoDirectory,indexVideoBlob} from '../web/site/video-archive.js';
function archive(){
  const b=new Uint8Array(112),v=new DataView(b.buffer);v.setUint32(0,2,true);
  b.set(new TextEncoder().encode('Last.BIK'),4);v.setUint32(44,102,true);
  b.set(new TextEncoder().encode('First.SMK'),48);v.setUint32(88,92,true);return b;
}
test('VID computes extents by offsets, even when directory names are not in physical order',async()=>{
  const data=archive(),entries=parseVideoDirectory(data.subarray(0,92),data.length);
  assert.deepEqual(entries,[{name:'Last.BIK',offset:102,bytes:10},{name:'First.SMK',offset:92,bytes:10}]);
  assert.deepEqual(await indexVideoBlob(new Blob([data])),entries);
});
test('VID rejects truncated directories, out-of-file offsets, overlapping names and oversized members',()=>{
  const data=archive(),v=new DataView(data.buffer);
  assert.throws(()=>parseVideoDirectory(data.subarray(0,90),112));
  v.setUint32(44,113,true);assert.throws(()=>parseVideoDirectory(data,112));
  v.setUint32(44,92,true);assert.throws(()=>parseVideoDirectory(data,112));
  v.setUint32(44,102,true);assert.throws(()=>parseVideoDirectory(data,128*1024*1024));
  data[4]=47;assert.throws(()=>parseVideoDirectory(data,112));
});
