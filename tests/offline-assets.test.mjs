import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const script=await readFile(new URL('../web/site/assets.js',import.meta.url),'utf8');
function setup(fetch) {
  const window={fetch};
  vm.runInNewContext(script,{window,document:{querySelector:()=>null},location:{href:'https://game.example/site/offline.html',origin:'https://game.example'},URL,Response});
  return window.homm3Assets;
}
test('offline installer captures the configured catalog and content hashes, downloading directly without credentials',async()=>{
  const calls=[],hash='a'.repeat(64);
  const assets=setup(async(url,options)=>{
    calls.push({url:String(url),options});
    return String(url)==='/site/resources.json' ? Response.json({baseUrl:'https://resources.example/data/',files:{'MAINMENU.MP3':hash+'.mp3'},catalog:{maps:['Arrogance.h3m'],music:['MAINMENU.MP3']}}) : new Response('audio');
  });
  const source=await assets.source();
  assert.equal(source.catalog.ready,true);assert.equal(source.hashes['MAINMENU.MP3'],hash+'.mp3');
  assert.equal(await (await source.fetch('/api/music?name=mainmenu.mp3')).text(),'audio');
  assert.equal(calls[1].url,'https://resources.example/data/'+hash+'.mp3');
  assert.equal(calls[1].options.credentials,'omit');
  assert.equal((await source.fetch('/api/music?name=missing.mp3')).status,404);
});
test('transient configuration failure can be retried after network restoration',async()=>{
  let online=false;
  const assets=setup(async url=>{
    if(!online)throw new TypeError('offline');
    return Response.json(String(url)==='/site/resources.json' ? {baseUrl:null} : {ready:true,maps:['test.h3m']});
  });
  await assert.rejects(assets.source(),/offline/);online=true;
  assert.equal((await assets.source()).catalog.ready,true);
});
