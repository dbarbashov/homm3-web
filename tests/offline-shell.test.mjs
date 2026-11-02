import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash,webcrypto} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {shellFiles} from '../lib/offline-shell.mjs';
const template=await readFile(new URL('../lib/offline-worker.js',import.meta.url),'utf8');
const sha=value=>createHash('sha256').update(value).digest('hex');
function fixture(broken=false) {
  const entries=[{url:'/index.html',hash:sha('home'),bytes:4},{url:'/port/game.wasm',hash:sha('wasm'),bytes:4}];
  const events=new Map(),stores=new Map([['homm3-shell-v1-old',new Map([['/index.html',new Response('old')]])]]);
  const caches={keys:async()=>[...stores.keys()],delete:async key=>stores.delete(key),open:async name=>{
    if(!stores.has(name))stores.set(name,new Map());const store=stores.get(name);
    return {match:async key=>store.get(key)?.clone(),put:async(key,response)=>store.set(key,response.clone())};
  }};
  const calls=[];
  const self={location:{origin:'https://game.example'},addEventListener:(type,fn)=>events.set(type,fn),skipWaiting:()=>{throw Error('Must not interrupt active games');}};
  const context=vm.createContext({self,caches,URL,Response,Headers,crypto:webcrypto,fetch:async url=>{
    calls.push(url);return new Response(url==='/index.html' ? 'home' : broken ? 'oops' : 'wasm');
  }});
  vm.runInContext(template.replace('/* OFFLINE_MANIFEST */ null',JSON.stringify({version:'new',entries})),context);
  async function dispatch(type,event={}) {let pending;events.get(type)({...event,waitUntil:p=>pending=p,respondWith:p=>pending=p});return pending;}
  return {stores,calls,dispatch,breakServer:()=>{broken=true;}};
}
test('public offline manifest excludes API, credentials, retail files, journals and reports',()=>{
  assert(shellFiles.includes('site/offline-store.js'));
  assert(shellFiles.includes('port/game.wasm'));
  assert.equal(new Set(shellFiles).size,shellFiles.length);
  for(const name of shellFiles) assert(!/resources\.json|report[s/]|\.lod$|\.snd$|\.h3m$|\.mp3$|\.vid$|(^|\/)\.|lobby|sources\//i.test(name),name);
});
test('failed mixed-version shell download cannot replace or delete the previous working version',async()=>{
  const f=fixture(true);
  await assert.rejects(f.dispatch('install'),/changed during download/);
  assert.equal(await (await f.stores.get('homm3-shell-v1-old').get('/index.html')).text(),'old');
  assert(!f.stores.get('homm3-shell-v1-new').has('/port/game.wasm'));
});
test('atomic shell serves exact cached bytes offline, ignores queries and never intercepts private traffic',async()=>{
  const f=fixture();await f.dispatch('install');
  assert(f.stores.has('homm3-shell-v1-old'),'old tabs retain their version until activation');
  await f.dispatch('activate');assert(!f.stores.has('homm3-shell-v1-old'));
  const response=await f.dispatch('fetch',{request:{url:'https://game.example/?play=1',method:'GET'}});
  assert.equal(await response.text(),'home');
  for (const [url,method] of [['/lobby/reports/private','GET'],['/api/catalog','GET'],['/site/resources.json','GET'],['/index.html','POST'],['https://other.example/index.html','GET']]) {
    assert.equal(await f.dispatch('fetch',{request:{url:new URL(url,'https://game.example').href,method}}),undefined);
  }
  assert.equal(f.calls.length,2,'cached fetch should not access network');
});
test('missing cached runtime reports an error instead of mixing in the current server runtime',async()=>{
  const f=fixture();await f.dispatch('install');f.stores.get('homm3-shell-v1-new').delete('/port/game.wasm');f.breakServer();
  const response=await f.dispatch('fetch',{request:{url:'https://game.example/port/game.wasm',method:'GET'}});
  assert.equal(response.status,503);assert.equal(f.calls.length,3);
});

test('repair restores missing shell files with their original checksums',async()=>{
  const f=fixture();await f.dispatch('install');f.stores.get('homm3-shell-v1-new').delete('/port/game.wasm');
  let status;
  await f.dispatch('message',{data:{type:'homm3-offline-repair'},ports:[{postMessage:value=>status=value}]});
  assert.equal(status.complete,true);assert.equal(f.calls.length,3);
  assert.equal(await f.stores.get('homm3-shell-v1-new').get('/port/game.wasm').text(),'wasm');
});
