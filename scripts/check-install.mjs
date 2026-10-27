// Validates installed map streams with the exact WASM module used in-browser.
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import { openInstallation } from '../lib/assets.mjs';
const config=JSON.parse(await readFile('.local/game.json','utf8'));
const game=await openInstallation(config.gameRoot);
const {instance}=await WebAssembly.instantiate(await readFile('web/engine.wasm'));
const e=instance.exports, maps=[];
for(const name of game.maps){
  const source=gunzipSync(await readFile(path.join(game.root,'Maps',name)));
  const ptr=e.input_buffer(source.length);new Uint8Array(e.memory.buffer,ptr,source.length).set(source);
  const ok=e.parse_map();const text=new TextDecoder().decode(new Uint8Array(e.memory.buffer,e.output_ptr(),e.output_len()));
  const parsed=ok?JSON.parse(text):null;
  maps.push({name,ok:!!ok,...(parsed?{size:parsed.size,layers:parsed.layers,objects:parsed.objects.length,trailing:parsed.trailing}:{error:text})});
}
const exe=await readFile(path.join(game.root,'Heroes3.exe'));
const expected=JSON.parse(await readFile('upstream.lock.json','utf8')).retailExecutable;
const sha256=createHash('sha256').update(exe).digest('hex');
const report={gameRoot:game.root,exe:{size:exe.length,sha256,matchesUpstream:exe.length===expected.size&&sha256===expected.sha256},archives:game.archives,uniqueResources:game.entries.size,music:game.music.length,maps};
await mkdir('test-results',{recursive:true});await writeFile('test-results/installation.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({maps:maps.length,passed:maps.filter(x=>x.ok).length,failures:maps.filter(x=>!x.ok),resources:game.entries.size,music:game.music.length}));
if(maps.some(x=>!x.ok))process.exitCode=1;
