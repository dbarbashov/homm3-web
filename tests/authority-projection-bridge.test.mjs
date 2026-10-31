import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';
const source=fs.readFileSync(new URL('../web/site/authority-game.js',import.meta.url),'utf8');
function client(clock=Date,ready={}){
  const window={homm3Network:{self:'a',host:'a'}},sent=[];
  vm.runInNewContext(source,{window,Date:clock,Number,Array,Map,Error});
  const api=window.homm3Authority;api.start(m=>sent.push(m));
  api.receive({type:'authority_ready',generation:'g1',actor:0,...ready});api.nativeReady('maps/trusted.h3m',Array(41).fill(0));
  const receive=m=>api.receive({generation:'g1',...m});
  const state=(revision=0)=>receive({type:'authority_state',schema:1,actor:0,revision,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)]});
  const apply=()=>{const heap=new Int32Array(api.pendingLength());api.copyPending(heap,0);api.applied();};
  state();apply();return {window,sent,api,receive,state,apply};
}
function battle(actions){return {
  schema:1,round:1,side:0,actingSide:0,actingSlot:0,tactics:false,point:[1,1,0],terrain:2,magicTerrain:0,town:-1,fortification:0,drawbridge:0,surrounded:0,largeObstacle:-1,players:[0,1],heroes:[{id:-1,mana:0},{id:-1,mana:0}],spellsCast:[0,0],placementDepth:0,
  stacks:[{side:0,slot:0,creature:0,count:10,hex:86,damage:0,flags:0,facing:1,originalIndex:0,originalCount:10,attack:4,defense:5,speed:4,hp:10,shots:0,morale:0,luck:0,retaliations:1,effects:[]}],
  walls:Array(18).fill(0),obstacles:[],cells:Array.from({length:187},()=>Array(49).fill(0)),actions
};}
test('commands are authenticated intents and wait for the committed projection',()=>{
  const {api,receive,state,apply,sent}=client();const id=api.send(5);
  assert.equal(typeof sent.at(-1).id,'string');assert.equal(sent.at(-1).generation,'g1');assert.equal(sent.at(-1).actor,undefined);
  receive({type:'authority_result',id:sent.find(m=>m.type==='authority_command').id,ok:true,revision:1});assert.equal(api.result(id),0);
  state(1);assert.equal(api.result(id),0);apply();assert.equal(api.result(id),1);
});
test('same-revision choice projection is installed before the original dialog opens',()=>{
  const {api,receive,state,apply}=client();state(0);
  receive({type:'authority_choice',actor:0,token:4,kind:'normal',text:'\u00e0',options:[1],data:{mbType:1,special:-1,icons:[[-1,0],[-1,0],[-1,0]]}});
  const fields=new Int32Array(16),text=new Uint8Array(20);
  assert.equal(api.takeChoice(fields,0,text,20),0);apply();assert.equal(api.takeChoice(fields,0,text,20),1);assert.equal(text[0],224);
});
test('late packets from other generations cannot change the world or dismiss a request',()=>{
  const {api,receive,sent}=client();const id=api.send(5);
  assert.equal(receive({generation:'old',type:'authority_result',id:sent.find(m=>m.type==='authority_command').id,ok:false}),false);assert.equal(api.result(id),0);
  assert.equal(receive({generation:'old',type:'authority_fault',message:'late'}),false);assert.equal(api.revision,0);
});
test('transient reconnect keeps the applied world and pending request',()=>{
  const {api,receive,sent}=client();const id=api.send(5);api.disconnect();
  assert.equal(api.revision,0);assert.equal(api.send(1,0,1),0);
  receive({type:'authority_ready',actor:0});receive({type:'authority_result',id:sent.find(m=>m.type==='authority_command').id,ok:false,error:'stale'});assert.equal(api.result(id),-1);
});
test('original battle actions submit only server-offered indices',()=>{
  const {api,receive,sent}=client();
  receive({type:'authority_choice',actor:0,token:8,kind:'combat',options:[0,1],data:battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1},{id:1,action:2,hex:87,extra:-1,hex2:-1}])});
  const heap=new Int32Array(api.combatLength());assert(heap.length>9000);api.takeCombat(heap,0);
  assert.equal(api.combatAction(2,100,-1,-1),false);assert.equal(api.combatAction(2,87,-1,-1),true);
  assert.equal(sent.at(-1).type,'authority_answer');assert.equal(sent.at(-1).value,1);assert.equal(sent.at(-1).token,8);
});
test('staged hero spell selection preserves target and uses the new server token',()=>{
  const {api,receive,sent}=client();
  receive({type:'authority_choice',actor:0,token:10,kind:'combat',options:[0],data:battle([{id:0,action:101,hex:-1,extra:63,hex2:-1}])});
  api.takeCombat(new Int32Array(api.combatLength()),0);assert(api.combatAction(1,90,63,86));assert.equal(sent.at(-1).token,10);
  receive({type:'authority_choice',actor:0,token:11,kind:'combat_spell',options:[0,1],data:{actions:[{id:0,action:102,hex:-1,extra:-1,hex2:-1},{id:1,action:1,hex:90,extra:63,hex2:86}]}});
  assert.equal(sent.at(-1).value,1);assert.equal(sent.at(-1).token,11);
});
test('committed post-battle state returns the original battle manager to adventure',()=>{
  const {api,receive,state}=client();receive({type:'authority_choice',actor:0,token:12,kind:'combat',options:[0],data:battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}])});
  api.takeCombat(new Int32Array(api.combatLength()),0);api.combatAction(3,0,0,0);assert.equal(api.combatFinished(),false);state(1);assert.equal(api.combatFinished(),true);
});
test('initial informational event with omitted icons opens the original dialog',()=>{
  const {api,receive}=client();receive({type:'authority_choice',actor:0,token:16,kind:'normal',text:'Welcome',options:[1],data:{mbType:1,icons:[]}});
  const fields=new Int32Array(16);assert.equal(api.takeChoice(fields,0,new Uint8Array(32),32),1);
  assert.deepEqual(Array.from(fields.slice(0,9)),[1,1,-1,-1,0,-1,0,-1,0]);
});
test('inactive participant sees the original battle projection without gaining a choice token',()=>{
  const {api,receive,sent}=client();const data=battle([]);data.canAct=false;
  receive({type:'authority_combat_state',actor:0,revision:0,data});
  const length=api.combatLength();assert(length>9000);api.takeCombat(new Int32Array(length),0);
  assert.equal(api.combatCanAct(),false);const before=sent.length;assert.equal(api.combatAction(3,-1,-1,-1),false);assert.equal(sent.length,before);
});
test('state application preserves phase and exposes the authoritative active turn',()=>{
  const {api,receive,state,apply,window}=client();receive({type:'authority_status',phase:'adventure',activeActor:0,revision:0});state(1);apply();
  assert.equal(window.homm3AuthorityStatus.phase,'adventure');assert.equal(window.homm3AuthorityStatus.activeActor,0);
  receive({type:'authority_ready',actor:0,phase:'choice',activeActor:1,revision:1});assert.equal(window.homm3AuthorityStatus.phase,'choice');assert.equal(window.homm3AuthorityStatus.activeActor,1);assert.equal(api.revision,1);
});
test('deferred interface events are private, deduplicated, and wait for command completion',()=>{
  const {api,receive,sent}=client();const id=api.send(1,3,4);const result={type:'authority_result',id:sent.find(m=>m.type==='authority_command').id,ok:true,revision:0,uiEvents:[{kind:'open_town',actor:0,id:2,other:-1}]};
  receive(result);receive(result);const fields=new Int32Array(3);assert.equal(api.takeUIEvent(fields,0),0);assert.equal(api.result(id),1);assert.equal(api.takeUIEvent(fields,0),1);assert.deepEqual(Array.from(fields),[1,2,-1]);assert.equal(api.takeUIEvent(fields,0),0);
});
test('choice copies respect the native field buffer boundary',()=>{
  const {api,receive}=client();receive({type:'authority_choice',actor:0,token:90,kind:'normal',options:[1],data:{}});
  const heap=new Int32Array(80);heap.fill(123456);
  assert.equal(api.takeChoice(heap,4,new Uint8Array(8),8,16),1);
  assert.equal(heap[3],123456);assert.equal(heap[20],123456);
});
test('oversized choice is rejected before touching a smaller native buffer',()=>{
  const {api,receive}=client();receive({type:'authority_choice',actor:0,token:91,kind:'army_exchange',options:[0],data:{heroId:0,other:Array.from({length:7},()=>[-1,0])}});
  const heap=new Int32Array(80);heap.fill(123456);
  assert.equal(api.takeChoice(heap,4,new Uint8Array(8),8,16),0);
  assert.equal(api.fatal,true);assert(heap.every(v=>v===123456));
});
test('rejected modal answer restores its original token for correction',()=>{
  const {api,receive,sent}=client();receive({type:'authority_choice',actor:0,token:92,kind:'university',options:[-1,3],data:{heroId:0,cost:2000,skills:[3,4,5,6]}});
  const fields=new Int32Array(16),text=new Uint8Array(80);api.takeChoice(fields,0,text,80);api.answer(3);
  receive({type:'authority_result',id:sent.at(-1).id,ok:false,error:'Insufficient gold'});
  assert.equal(api.takeChoiceError(text,80),1);assert.equal(api.takeChoice(fields,0,text,80),4);api.answer(-1);
  assert.equal(sent.at(-1).token,92);assert.equal(api.fatal,false);
});
test('combat results precede level-up and acknowledge only after original modal dismissal',()=>{
  const {api,receive,sent,state,apply}=client();
  const data={...battle([]),canAct:false,winner:0,mySide:0,siege:false,experience:123,retreated:false,surrendered:false,loot:[[7,-1]],eagleEye:[2],necromancy:{creature:56,count:3}};
  data.heroes[0].nameBytes=[224,225];
  const result={type:'authority_combat_result',id:'result:1',actor:0,revision:0,data};
  receive(result);receive(result);
  receive({type:'authority_choice',actor:0,token:100,kind:'level_up',options:[1],data:{hero:0,primary:0,skills:[1,-1]}});
  const fields=new Int32Array(64),text=new Uint8Array(32);
  assert.equal(api.takeChoice(fields,0,text,32,64),0);assert.equal(api.combatFinished(),false);
  api.takeCombat(new Int32Array(api.combatLength()),0);
  const output=new Int32Array(api.combatResultLength());api.copyCombatResult(output,0);
  assert.equal(output[3],123);assert.equal(output[6],2);assert.equal(output[7],224);
  assert.equal(sent.filter(m=>m.type==='authority_seen').length,0);
  assert.equal(api.combatCanAct(),false);api.combatResultShown();
  assert.equal(sent.at(-1).type,'authority_seen');assert.equal(sent.at(-1).id,'result:1');assert.equal(api.combatFinished(),true);
  assert.equal(api.takeChoice(fields,0,text,32,64),2);api.answer(1);
  receive(result);assert.equal(api.combatLength(),0);assert.equal(sent.at(-1).id,'result:1');
});
test('market choices preserve the fixed seven-slot inventory and allow a town without visiting hero',()=>{
  const {api,receive}=client();receive({type:'authority_choice',actor:0,token:101,kind:'market',options:[0,1],data:{heroId:-1,townId:0,source:0,count:1,window:0,artifacts:Array(7).fill(-1)}});
  const fields=new Int32Array(64);assert.equal(api.takeChoice(fields,0,new Uint8Array(8),8,64),7);
  assert.deepEqual(Array.from(fields.slice(0,6)),[7,-1,0,0,1,0]);
});
test('fresh pages in the same session cannot reuse command or answer cache IDs',()=>{
  const first=client(),second=client();const a=first.api.send(5),b=second.api.send(5);
  assert.equal(a,b);assert.notEqual(first.sent.at(-1).id,second.sent.at(-1).id);
  assert(first.sent.at(-1).id.length<=64);assert(second.sent.at(-1).id.length<=64);
  second.receive({type:'authority_result',id:first.sent.at(-1).id,ok:false,error:'Old cached command'});
  assert.equal(second.api.result(b),0);
  second.receive({type:'authority_result',id:second.sent.at(-1).id,ok:false,error:'New command'});
  assert.equal(second.api.result(b),-1);
});
test('server Auto Combat waits for a rendered step and queues Stop across an in-flight action',()=>{
  let now=1000;const {api,receive,sent}=client({now:()=>now});
  const data={...battle([{id:0,action:103,hex:-1,extra:-1,hex2:-1},{id:1,action:104,hex:-1,extra:-1,hex2:-1}]),autoCombat:true};
  receive({type:'authority_choice',actor:0,token:110,kind:'combat',options:[0,1],data});api.takeCombat(new Int32Array(api.combatLength()),0);
  assert.equal(api.combatAutoStep(),false);now+=80;assert.equal(api.combatAutoStep(),true);assert.equal(sent.at(-1).value,0);
  assert.equal(api.combatToggleAuto(),true);
  receive({type:'authority_choice',actor:0,token:111,kind:'combat',options:[0,1],data});api.takeCombat(new Int32Array(api.combatLength()),0);
  now+=80;assert.equal(api.combatAutoStep(),true);assert.equal(sent.at(-1).token,111);assert.equal(sent.at(-1).value,1);
});
test('battle names preserve original bytes and unavailable Auto Combat stays disabled',()=>{
  const {api,receive}=client();const data=battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}]);data.heroes[0].nameBytes=[224,225];
  receive({type:'authority_choice',actor:0,token:112,kind:'combat',options:[0],data});api.takeCombat(new Int32Array(api.combatLength()),0);
  const name=new Uint8Array(12);assert.equal(api.copyCombatHeroName(0,name,12),1);assert.deepEqual(Array.from(name.slice(0,3)),[224,225,0]);assert.equal(api.combatCanAuto(),false);
});
test('extended rewards retain every original resource icon instead of truncating to three',()=>{
  const {api,receive,sent}=client();const icons=[[6,1000],[5,2],[7,9],[20,4],[21,196664]];
  receive({type:'authority_choice',actor:0,token:113,kind:'normal',options:[0x7802],text:'Rewards',data:{mbType:1,icons}});
  const fields=new Int32Array(64);assert.equal(api.takeChoice(fields,0,new Uint8Array(32),32,64),11);
  assert.equal(api.normalIconsLength(),10);const words=new Int32Array(10);api.copyNormalIcons(words,0);assert.deepEqual(Array.from(words),icons.flat());
  assert(api.answer(0x7802));assert.equal(sent.at(-1).value,0x7802);
});
test('eliminated or finished seats retain their final view while new intents remain disabled',()=>{
  const {api,receive,apply,window}=client();
  receive({type:'authority_state',schema:1,actor:0,revision:1,eliminated:true,finished:false,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)]});apply();
  assert.equal(api.eliminated,true);assert.equal(api.send(5),0);
  receive({type:'authority_status',phase:'adventure',activeActor:0,revision:1});assert.equal(api.send(5),0);assert.equal(window.homm3AuthorityStatus.eliminated,true);
  receive({type:'authority_state',schema:1,actor:0,revision:2,eliminated:false,finished:true,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)]});apply();
  assert.equal(api.finished,true);assert.equal(api.send(1,0,1),0);assert.equal(api.fatal,false);
});
test('puzzle imports only bounded masked RGB565 pixels and acknowledges its token',()=>{
  const {api,receive,sent}=client(),pixels=Buffer.alloc(592*544*2);
  pixels.writeUInt16LE(0xf800,0);pixels.writeUInt16LE(0x07e0,2);pixels.writeUInt16LE(0x001f,pixels.length-2);
  receive({type:'authority_choice',actor:0,token:77,kind:'puzzle',options:[0],data:{alignment:2,revealed:12,width:592,height:544,encoding:'rgb565le-base64',pixels:pixels.toString('base64')}});
  const fields=new Int32Array(64);assert.equal(api.takeChoice(fields,0,new Uint8Array(4),4,64),15);
  assert.deepEqual(Array.from(fields.slice(0,5)),[15,2,592,544,12]);
  const heap=new Uint16Array(592*544+2);heap[0]=123;heap[heap.length-1]=456;
  assert.equal(api.copyPuzzlePixels(heap,1,592*544-1),0);assert.equal(api.copyPuzzlePixels(heap,1,592*544),592*544);
  assert.equal(heap[0],123);assert.equal(heap[1],0xf800);assert.equal(heap[2],0x07e0);assert.equal(heap[heap.length-2],0x001f);assert.equal(heap[heap.length-1],456);
  api.answer(0);assert.equal(sent.at(-1).token,77);assert.equal(sent.at(-1).value,0);
});
test('per-seat outcome notices are original bytes, nonblocking and deduplicated',()=>{
  const {api,receive,apply,window}=client();
  const state={type:'authority_state',schema:1,actor:0,revision:1,words:[1,0,1,1,1,1,36,1,...Array(13).fill(0)],eliminated:true,finished:false,outcome:-1,notices:[{id:1,textBytes:[224,225]}]};
  receive(state);apply();const text=new Uint8Array(10);assert.equal(api.takeNotice(text,10),1);assert.deepEqual([...text.slice(0,3)],[224,225,0]);assert.equal(window.homm3AuthorityStatus.outcome,-1);
  assert.equal(api.takeNotice(text,10),0);api.noticeShown();receive(state);apply();assert.equal(api.takeNotice(text,10),0);
});
test('puzzle nested in View Earth/Air follows offered tokens and returns to its original view',()=>{
  const {api,receive,sent}=client(),image={alignment:4,revealed:0,width:592,height:544,encoding:'rgb565le-base64',pixels:Buffer.alloc(592*544*2).toString('base64')};
  const world=token=>receive({type:'authority_choice',actor:0,token,kind:'world_view',options:[0,1],data:{spell:3,level:2,markers:[]}});
  const fields=new Int32Array(64),text=new Uint8Array(4),heap=new Uint16Array(592*544);
  world(78);assert.equal(api.takeChoice(fields,0,text,4,64),6);assert.equal(api.worldSpell(),3);assert.equal(api.copyPuzzlePixels(heap,0,heap.length),0);
  api.answer(1);assert.equal(sent.at(-1).token,78);assert.equal(sent.at(-1).value,1);
  receive({type:'authority_choice',actor:0,token:79,kind:'puzzle',options:[0],data:image});
  assert.equal(api.takeChoice(fields,0,text,4,64),15);assert.equal(api.copyPuzzlePixels(heap,0,heap.length),heap.length);
  api.answer(0);assert.equal(sent.at(-1).token,79);
  world(80);assert.equal(api.takeChoice(fields,0,text,4,64),6);api.answer(0);assert.equal(sent.at(-1).token,80);
  assert.equal(sent.filter(m=>m.type==='authority_command').length,0);
});

test('battle opening is retained before a faster AI choice and its visual journal',()=>{
  const {api,receive}=client();const opening={...battle([]),canAct:false,presentation:[]};
  receive({type:'authority_combat_state',actor:0,revision:0,data:opening});
  const event=[1,1,0,0,86,1,1,1,1,0,0,0];
  receive({type:'authority_choice',actor:0,token:120,kind:'combat',options:[0],data:{...battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}]),presentation:[event]}});
  let words=new Int32Array(api.combatLength());api.takeCombat(words,0);
  assert.equal(words.at(-1),0);assert.equal(api.combatCanAct(),false);
  words=new Int32Array(api.combatLength());api.takeCombat(words,0);
  assert.deepEqual(Array.from(words.slice(-12)),event);assert.equal(api.combatCanAct(),true);
});
test('visual replay and disconnected transport suppress additional battle input',()=>{
  const {api,receive,sent}=client();receive({type:'authority_choice',actor:0,token:121,kind:'combat',options:[0],data:battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}])});
  api.takeCombat(new Int32Array(api.combatLength()),0);api.presentationBusy(true);
  const n=sent.length;assert.equal(api.combatCanAct(),false);assert.equal(api.combatAction(3,-1,-1,-1),false);assert.equal(sent.length,n);
  api.presentationBusy(false);assert.equal(api.combatCanAct(),true);api.disconnect();assert.equal(api.combatCanAct(),false);
});
test('malformed or unbounded visual history cannot reach native animation routines',()=>{
  const event=[1,1,0,0,86,1,1,1,1,0,0,0];
  for(const history of [[event.slice(1)],[[...event.slice(0,1),99,...event.slice(2)]],[event,event],Array(257).fill(event),[[1,1,2,0,86,1,1,1,1,0,0,0]]]){
    const {api,receive,window}=client();receive({type:'authority_choice',actor:0,token:122,kind:'combat',options:[0],data:{...battle([]),presentation:history}});
    assert.equal(api.combatLength(),0);assert.equal(window.homm3AuthorityStatus.error,true);
  }
});

test('successful spell sound survives the journal and rejects invalid spell IDs',()=>{
  const event=[1,9,0,0,86,1,53,0,0,0,0,0];
  const {api,receive}=client();
  receive({type:'authority_choice',actor:0,token:123,kind:'combat',options:[0],data:{...battle([]),presentation:[event]}});
  const words=new Int32Array(api.combatLength());api.takeCombat(words,0);
  assert.deepEqual(Array.from(words.slice(-12)),event);
  for(const spell of [-1,81]){
    const invalid=[...event];invalid[6]=spell;
    const {api,receive,window}=client();
    receive({type:'authority_choice',actor:0,token:123,kind:'combat',options:[0],data:{...battle([]),presentation:[invalid]}});
    assert.equal(api.combatLength(),0);assert.equal(window.homm3AuthorityStatus.error,true);
  }
});

test('turn transfer follows transport and ends when the next actor is announced',()=>{
  const {api,receive,state,apply,sent}=client();
  assert.equal(api.turnTransfer,0);
  const id=api.send(5);assert.equal(api.turnTransfer,1);
  receive({type:'authority_status',phase:'adventure',activeActor:1,revision:0});
  assert.equal(api.turnTransfer,0);assert.equal(api.result(id),0);
  receive({type:'authority_result',id:sent.find(m=>m.type==='authority_command').id,ok:true,revision:1});
  state(1);apply();assert.equal(api.result(id),1);assert.equal(api.turnTransfer,0);
  api.disconnect();assert.equal(api.turnTransfer,2);
  receive({type:'authority_ready',actor:0,phase:'adventure',activeActor:1,revision:1});assert.equal(api.turnTransfer,0);
});

test('university presentation distinguishes the town from the map encounter',()=>{
  for(const townUniversity of [false,true]){
    const {api,receive}=client();
    receive({type:'authority_choice',actor:0,token:93,kind:'university',options:[-1,3],data:{heroId:0,cost:2000,skills:[3,4,5,6],townUniversity}});
    const fields=new Int32Array(16);
    assert.equal(api.takeChoice(fields,0,new Uint8Array(80),80),4);
    assert.deepEqual(Array.from(fields.slice(0,8)),[4,0,2000,3,4,5,6,+townUniversity]);
  }
});

test('resource panel preserves CP1251 bytes, waits for the applied revision, and deduplicates',()=>{
  const {api,receive,sent,state,apply}=client();const ticket=api.send(1,3,0);
  const result={type:'authority_result',id:sent.at(-1).id,ok:true,revision:1,uiEvents:[{kind:'resource',actor:0,id:5,other:3,text:'\u00d1\u00f0'}]};
  receive(result);receive(result);const fields=new Int32Array(3),text=new Uint8Array(6);text.fill(77);
  assert.equal(api.takeUIEvent(fields,0,text,6),0);state(1);apply();assert.equal(api.result(ticket),1);
  assert.equal(api.takeUIEvent(fields,0,text,6),1);assert.deepEqual([...fields],[3,5,3]);assert.deepEqual([...text],[209,240,0,77,77,77]);
  assert.equal(api.takeUIEvent(fields,0,text,6),0);
});
test('invalid resource ids and non-byte or oversized text fail before presentation',()=>{
  for(const change of [{id:-1},{id:7},{text:'Ж'},{text:'x'.repeat(65537)}]){
    const {api,receive}=client();receive({type:'authority_result',id:'resource',ok:true,revision:0,uiEvents:[{kind:'resource',actor:0,id:0,other:1,text:'x',...change}]});
    assert.equal(api.fatal,true);assert.equal(api.takeUIEvent(new Int32Array(3),0,new Uint8Array(9),9),0);
  }
});
test('resource text capacity is validated before native buffers change',()=>{
  for(const capacity of [2,99,NaN]){
    const {api,receive}=client();receive({type:'authority_result',id:'resource',ok:true,revision:0,uiEvents:[{kind:'resource',actor:0,id:0,other:1,text:'xy'}]});
    const fields=new Int32Array(3).fill(77),text=new Uint8Array(3).fill(77);
    assert.equal(api.takeUIEvent(fields,0,text,capacity),0);assert.equal(api.fatal,true);assert(fields.every(v=>v===77));assert(text.every(v=>v===77));
  }
});

test('puzzle rejects invalid reveal counts before opening a window',()=>{
  for(const revealed of [-1,49,1.5,undefined]){
    const {api,receive}=client();
    receive({type:'authority_choice',actor:0,token:77,kind:'puzzle',options:[0],data:{alignment:2,revealed,width:592,height:544,encoding:'rgb565le-base64',pixels:Buffer.alloc(592*544*2).toString('base64')}});
    assert.equal(api.takeChoice(new Int32Array(64),0,new Uint8Array(4),4,64),0);
    assert.equal(api.fatal,true);
  }
});

test('battle opening waits for the preceding adventure position projection',()=>{
  const {api,receive,state,apply}=client();state(0);
  const data=battle([]);data.canAct=false;
  receive({type:'authority_combat_state',actor:0,revision:0,data});
  assert.equal(api.combatLength(),0);apply();assert(api.combatLength()>0);
});
test('adventure sounds follow applied state once, including same-revision choices',()=>{
  const {api,receive,apply}=client();
  const update=()=>receive({type:'authority_state',schema:1,actor:0,revision:0,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)],adventureSounds:[{id:1,name:'pickup03.82M'},{id:2,name:'Gazebo.wav'}]});
  const bytes=new Uint8Array(81);update();assert.equal(api.takeAdventureSound(bytes,81),0);apply();
  const read=()=>{assert.equal(api.takeAdventureSound(bytes,81),1);return new TextDecoder().decode(bytes.slice(0,bytes.indexOf(0)));};
  assert.equal(read(),'pickup03.82M');assert.equal(read(),'Gazebo.wav');assert.equal(api.takeAdventureSound(bytes,81),0);
  update();apply();assert.equal(api.takeAdventureSound(bytes,81),0);
});
test('adventure sound names cannot escape original resource names',()=>{
  const {api,receive,apply}=client();receive({type:'authority_state',schema:1,actor:0,revision:0,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)],adventureSounds:[{id:1,name:'../bad.wav'}]});
  apply();assert.equal(api.fatal,true);
});

test('reconnect does not replay already heard adventure sounds',()=>{
  const {api,receive,apply}=client();
  const update=sounds=>receive({type:'authority_state',schema:1,actor:0,revision:0,words:[1,0,0,1,1,1,36,1,...Array(13).fill(0)],adventureSounds:sounds});
  const bytes=new Uint8Array(81),history=[{id:1,name:'pickup02.82M'}];
  update(history);apply();assert.equal(api.takeAdventureSound(bytes,81),1);
  api.disconnect();receive({type:'authority_ready',actor:0,phase:'adventure',activeActor:0,revision:0});
  update(history);apply();assert.equal(api.takeAdventureSound(bytes,81),0);
  update([...history,{id:2,name:'Gazebo.wav'}]);apply();assert.equal(api.takeAdventureSound(bytes,81),1);
  assert.equal(new TextDecoder().decode(bytes.slice(0,bytes.indexOf(0))),'Gazebo.wav');
});
test('native result return resets the battle even without another combatFinished poll',()=>{
  const {api,receive,state,apply}=client();
  const offer=token=>receive({type:'authority_choice',actor:0,token,kind:'combat',options:[0],data:battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}])});
  offer(201);api.takeCombat(new Int32Array(api.combatLength()),0);api.combatAction(3,-1,-1,-1);
  receive({type:'authority_combat_result',id:'result:first',actor:0,revision:0,data:{...battle([]),canAct:false,winner:0,mySide:0,siege:false,experience:0,retreated:false,surrendered:false,loot:[],eagleEye:[],necromancy:{creature:-1,count:0}}});
  api.takeCombat(new Int32Array(api.combatLength()),0);api.combatResultShown();
  // Native results() returns directly from the modal: no combatFinished call.
  api.rendererReady(true);api.combatWindowClosed();assert.equal(api.combatRendererReady,false);
  state(1);apply();offer(202);api.takeCombat(new Int32Array(api.combatLength()),0);
  // Same-revision snapshot while the second battle is active must not end it.
  state(1);assert.equal(api.combatFinished(),false);assert.equal(api.combatCanAct(),true);
  assert.equal(api.combatAction(3,-1,-1,-1),true);
});
test('shipyard opens the original typed window and preserves original dialog answers',()=>{
  for(const townType of [0,8])for(const answer of [30721,30722]){
    const {api,receive,sent}=client();
    receive({type:'authority_choice',actor:0,token:203,kind:'shipyard',options:[30721,30722],data:{townType}});
    const fields=new Int32Array(64);assert.equal(api.takeChoice(fields,0,new Uint8Array(8),8,64),16);
    assert.deepEqual(Array.from(fields.slice(0,2)),[16,townType]);assert(api.answer(answer));assert.equal(sent.at(-1).value,answer);
  }
});
test('invalid shipyard faction fails before presenting a native window',()=>{
  for(const townType of [-1,9,1.5,'0',null]){
    const {api,receive}=client();
    receive({type:'authority_choice',actor:0,token:204,kind:'shipyard',options:[30721],data:{townType}});
    assert.equal(api.takeChoice(new Int32Array(64),0,new Uint8Array(8),8,64),0);assert(api.fatal);
  }
});
test('original normal dialog coordinates survive the server bridge',()=>{
  const {api,receive}=client();
  receive({type:'authority_choice',actor:0,token:205,kind:'normal',options:[30722],data:{mbType:1,x:208,y:40}});
  const fields=new Int32Array(16);assert.equal(api.takeChoice(fields,0,new Uint8Array(8),8),1);
  assert.deepEqual(Array.from(fields.slice(9,11)),[208,40]);
});

test('second-phase status follows the rendered snapshot, not a future observation',()=>{
  const {api,receive}=client();
  const load=()=>{const heap=new Int32Array(api.combatLength());api.takeCombat(heap,0);};
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false,secondPhase:false}});load();
  assert.equal(api.combatSecondPhase,false);
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false,secondPhase:true}});
  assert.equal(api.combatSecondPhase,false);
  load();assert.equal(api.combatSecondPhase,true);
});

test('versioned impact, morale and luck journal reaches native replay in order',()=>{
  const {api,receive}=client();const data={...battle([]),canAct:false};data.presentationVersion=2;
  data.presentation=[[1,10,0,0,86,1,1,0,0,0,0,0],[2,11,0,0,86,1,0,0,0,0,0,0],[3,12,0,0,86,1,-1,1,1,0,0,0]];
  receive({type:'authority_combat_state',actor:0,revision:0,data});
  const size=api.combatLength();assert(size>0);api.takeCombat(new Int32Array(size),0);
  assert.equal(api.combatPresentationVersion,2);assert.equal(api.fatal,false);
});
test('unknown journal version and invalid effect payloads fail closed',()=>{
  for(const [version,kind,args] of [[3,1,[0,0,0,0]],[1,10,[1,0,0,0]],[2,10,[2,0,0,0]],[2,12,[-2,1,0,0]],[2,12,[-1,1,-1,0]],[2,12,[-1,1,2097152,0]]]){
    const {api,receive}=client();const data={...battle([]),canAct:false};data.presentationVersion=version;data.presentation=[[1,kind,0,0,86,1,...args,0,0]];
    receive({type:'authority_combat_state',actor:0,revision:0,data});assert.equal(api.combatLength(),0);assert.equal(api.fatal,true);
  }
});

test('fresh page waits for current owner choice instead of replaying a cached opening',()=>{
  const {api,receive}=client(Date,{phase:'choice',activeActor:0,choiceActor:0,choiceKind:'combat'});
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false}});
  assert.equal(api.combatLength(),0,'must wait even when choice delivery is delayed');
  const current=battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}]);current.round=4;current.stacks[0].count=3;
  current.presentation=[[7,3,0,0,86,1,1,0,1,0,0,0],[8,5,0,0,86,1,4,1,3,0,0,0]];
  receive({type:'authority_choice',actor:0,token:9,kind:'combat',options:[0],data:current});
  const words=new Int32Array(api.combatLength());api.takeCombat(words,0);
  assert.equal(words[0],4);assert.deepEqual(Array.from(words.slice(-24)),current.presentation.flat());
  assert.equal(api.combatCanAct(),true);assert.equal(api.combatLength(),0);
});
test('transport reconnect retains the rendered current choice',()=>{
  const {api,receive}=client(Date,{phase:'choice',activeActor:0,choiceActor:0,choiceKind:'combat'});
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false}});
  receive({type:'authority_choice',actor:0,token:9,kind:'combat',options:[0],data:{...battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}]),round:3}});
  const words=new Int32Array(api.combatLength());api.takeCombat(words,0);assert.equal(words[0],3);
  api.disconnect();receive({type:'authority_ready',phase:'choice',activeActor:0,actor:0});
  assert(api.combatCanAct());assert.equal(api.combatLength(),0);
});

test('map turn owner reconnecting during enemy combat choice does not wait for its own choice',()=>{
  const {api,receive}=client(Date,{phase:'choice',activeActor:0,choiceActor:1,choiceKind:'combat'});
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false,round:4}});
  const words=new Int32Array(api.combatLength());assert(words.length);api.takeCombat(words,0);
  assert.equal(words[0],4);assert.equal(api.combatCanAct(),false);
});
test('older relay current choice already queued replaces its stale opening on a fresh page',()=>{
  const {api,receive}=client(Date,{phase:'choice',activeActor:0});
  receive({type:'authority_combat_state',actor:0,revision:0,data:{...battle([]),canAct:false}});
  receive({type:'authority_choice',actor:0,token:9,kind:'combat',options:[0],data:{...battle([{id:0,action:3,hex:-1,extra:-1,hex2:-1}]),round:4}});
  const words=new Int32Array(api.combatLength());api.takeCombat(words,0);assert.equal(words[0],4);
});
