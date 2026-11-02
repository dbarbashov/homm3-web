import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

function viewer(){
  const nodes=new Map(),requests=[],handlers={},timeouts=new Map();let time=0;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:false,disabled:false,value:'',setAttribute(k,v){this[k]=v;},click(){this.onclick?.();}});return nodes.get(id);};
  const frame={postMessage(){}};node('replay-frame').contentWindow=frame;
  const context=vm.createContext({URL,AbortController,AbortSignal,Date,
    location:{hash:'#'+'a'.repeat(32),origin:'https://example.test'},
    document:{getElementById:node,querySelector:node,addEventListener(){}},
    window:{addEventListener(type,callback){handlers[type]=callback;}},
    localStorage:{getItem(){return null;}},sessionStorage:{getItem(){return null;}},
    setTimeout(callback,ms){const id=++time;timeouts.set(id,{callback,ms});return id;},clearTimeout(id){timeouts.delete(id);},
    fetch(url,options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}));}
  });
  vm.runInContext(fs.readFileSync(new URL('../web/site/replay.js',import.meta.url),'utf8'),context);
  async function reply(index,cursor=0,ok=true){requests[index].resolve({ok,json:async()=>ok?{verified:true,cursor,positions:3,branchAllowed:true,state:{state:{}},revision:1}:{error:'Запись недоступна'}});await new Promise(resolve=>setImmediate(resolve));}
  function message(data){handlers.message({origin:'https://example.test',source:frame,data});}
  return {node,requests,reply,message,timeouts};
}

test('failed replay can retry the same moment without reloading the page',async()=>{
  const v=viewer();await v.reply(0,0,false);
  assert.equal(v.node('replay-retry').hidden,false);
  v.node('replay-retry').click();await v.reply(1);
  v.message({type:'homm3-replay-started',cursor:0,requestId:2});
  assert.match(v.node('replay-status').textContent,/Проверено/);
  assert.equal(v.node('replay-retry').hidden,true);
  assert.equal(v.node('replay-next').disabled,false);
});

test('playback can be paused while the next moment is loading',async()=>{
  const v=viewer();await v.reply(0);v.message({type:'homm3-replay-started',cursor:0,requestId:1});
  v.node('replay-play').click();assert.equal(v.node('replay-play').disabled,false);
  assert.equal(v.node('replay-play').textContent,'Пауза');v.node('replay-play').click();
  await v.reply(1,1);v.message({type:'homm3-replay-started',cursor:1,requestId:2});
  assert.equal(v.node('replay-play').textContent,'Смотреть');
  assert.equal([...v.timeouts.values()].filter(t=>t.ms===2000).length,0);
});

test('selecting local files cancels the pending load and ignores its late response and renderer messages',async()=>{
  const v=viewer();v.node('replay-files').files=[{name:'H3bitmap.lod'}];v.node('replay-files').onchange();
  assert.equal(v.requests[0].options.signal.aborted,true);
  await v.reply(1,2);v.message({type:'homm3-replay-started',cursor:2,requestId:3});
  await v.reply(0,0);v.message({type:'homm3-replay-error',message:'Old failure',requestId:1});
  assert.equal(v.node('replay-position').value,2);
  assert.match(v.node('replay-status').textContent,/Проверено/);
});
