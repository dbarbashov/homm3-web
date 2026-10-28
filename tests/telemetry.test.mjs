import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../web/site/telemetry.js',import.meta.url),'utf8');
function fixture(options={}) {
  const requests=[], listeners={}, values=new Map();
  if(options.off)values.set('homm3.telemetry.off','true');
  const context={URLSearchParams,Set,Number,String,location:{hostname:options.hostname||'homm3.xyz',pathname:'/port/game.html',search:'?secret=DO_NOT_SEND',hash:'#room=SECRET&invite=PRIVATE'},
    navigator:{doNotTrack:options.dnt,globalPrivacyControl:options.gpc,sendBeacon:url=>{if(options.fail)throw Error('blocked');requests.push(url);return true;}},
    localStorage:{getItem:key=>{if(options.storageDenied)throw Error('denied');return values.get(key)},setItem:(k,v)=>values.set(k,v)},
    document:{visibilityState:'visible',referrer:'https://example.com/private?token=NEVER_SEND',getElementById:()=>null,addEventListener:(name,fn)=>{listeners[name]=fn}},
    screen:{width:390},addEventListener:(name,fn)=>{listeners[name]=fn}};
  context.window=context;vm.runInNewContext(source,context);
  return {requests,listeners,context};
}
test('only canonical page and bucketed screen are sent, without private URL data',()=>{
 const f=fixture();assert.equal(f.requests.length,1);const q=new URL(f.requests[0],'https://homm3.xyz').searchParams;
 assert.deepEqual([...q.keys()],['p','e','s','b']);assert.equal(q.get('p'),'/port/game.html');assert.equal(q.get('s'),'480');assert.doesNotMatch(f.requests.join(),/SECRET|PRIVATE|DO_NOT_SEND|NEVER_SEND|token|invite|referrer/);
});
test('privacy preferences, local development and unavailable storage opt out',()=>{
 for(const options of [{off:true},{dnt:'1'},{gpc:true},{hostname:'localhost'},{storageDenied:true}]){
  const f=fixture(options);f.listeners['homm3-running']();assert.equal(f.requests.length,0);
 }
});
test('repeated render notifications do not create a beacon stream',()=>{
 const f=fixture();f.context.homm3PortDiagnostics={screen:'adventure'};
 for(let i=0;i<10000;i++){f.listeners['homm3-ready']();f.listeners['homm3-save-persisted']();f.listeners.error({message:'SECRET'})}
 assert.equal(f.requests.length,4);assert.doesNotMatch(f.requests.join(),/SECRET/);
 f.context.homm3PortDiagnostics={screen:'SECRET-CUSTOM-STATE'};f.listeners['homm3-ready']();assert.equal(f.requests.length,4);
});
test('blocked analytics does not throw into game event handlers',()=>{
 const f=fixture({fail:true});assert.doesNotThrow(()=>f.listeners['homm3-running']());assert.equal(f.requests.length,0);
});
