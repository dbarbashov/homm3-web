import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const script = await readFile(new URL('../web/port/music.js', import.meta.url), 'utf8');
const flush = async () => { for (let n=0;n<15;n++) await Promise.resolve(); };
function setup() {
  let ctx;
  class Param {
    constructor(){this.base=1;this.events=[];}
    get value(){return this.events.filter(e=>e.time<=ctx.currentTime).at(-1)?.value ?? this.base;}
    set value(v){this.base=v;}
    setValueAtTime(value,time){this.events.push({value,time});}
    cancelScheduledValues(time){this.events=this.events.filter(e=>e.time<time);}
  }
  class AudioContext {
    constructor(){ctx=this;this.currentTime=0;this.state='running';this.sources=[];}
    createGain(){return {gain:new Param(),connect(){},disconnect(){}};}
    createAnalyser(){return {connect(){}};}
    addEventListener(){}
    resume(){return Promise.resolve();}
    decodeAudioData(data){return Promise.resolve({duration:60,name:new TextDecoder().decode(data)});}
    createBufferSource(){
      const source={connect(gain){this.gain=gain;},disconnect(){},start(time,offset){this.startedAt=time;this.offset=offset;this.active=true;},stop(time=ctx.currentTime){this.stopAt=time;}};
      this.sources.push(source);return source;
    }
    advance(seconds){
      this.currentTime+=seconds;
      for(const s of this.sources)if(s.active && s.stopAt<=this.currentTime){s.active=false;s.onended?.();}
    }
  }
  const window={};
  vm.runInNewContext(script,{window,AudioContext,localStorage:{removeItem(){}},document:{querySelector(){}},fetch:async url=>({ok:true,arrayBuffer:async()=>new TextEncoder().encode(url).buffer})});
  const music=window.homm3Music;music.configure(['A.mp3','B.mp3','C.mp3']);music.unlock();
  return {music,get ctx(){return ctx;}};
}
test('music follows the original sequential 900 ms fades and remembers pre-fade position',async()=>{
  const {music,ctx}=setup();await music.play('A',0,1);
  const a=ctx.sources[0];
  assert.equal(a.gain.gain.events.length,10);
  assert.deepEqual(a.gain.gain.events.map(e=>Number(e.time.toFixed(1))),[0,.1,.2,.3,.4,.5,.6,.7,.8,.9]);
  assert.deepEqual(a.gain.gain.events.map(e=>e.value),[.1,.2,.3,.4,.5,.6,.7,.8,.9,1]);
  ctx.advance(2);const switching=music.play('B',0,1);await flush();
  assert.equal(ctx.sources.length,1,'new track started before old faded');
  assert.equal(music.state.track,'A');assert.equal(a.stopAt,2.9);
  ctx.advance(.5);assert.equal(a.gain.gain.value,.4);
  ctx.advance(.4);await switching;assert.equal(ctx.sources.length,2);assert.equal(music.state.track,'B');
  ctx.advance(2);const returning=music.play('A',0,1);ctx.advance(.9);await returning;
  assert.equal(ctx.sources.at(-1).offset,2,'resume position should exclude outgoing fade');
  assert.equal(ctx.sources.filter(s=>s.active).length,1);
});
test('duplicate and superseded requests never overlap music or resurrect a stopped track',async()=>{
  const {music,ctx}=setup();await music.play('A',0,1);ctx.advance(2);
  const b=music.play('B',0,1);assert.equal(music.play('B',0,1),b);
  const c=music.play('C',0,1);ctx.advance(.9);await Promise.all([b,c]);
  assert.equal(ctx.sources.length,2);assert.equal(music.state.track,'C');
  const d=music.play('B',0,1);music.close();ctx.advance(2);await d;
  assert.equal(music.state.playing,false);assert.equal(ctx.sources.filter(s=>s.active).length,0);
});
test('finite music starts at zero without fade-in; stop and resume retain looping position',async()=>{
  const {music,ctx}=setup();await music.play('A',0,1);ctx.advance(2);
  const stopped=music.stop();assert.equal(music.state.playing,true);ctx.advance(.9);await stopped;assert.equal(music.state.playing,false);
  await music.resume();assert.equal(ctx.sources.at(-1).offset,2);ctx.advance(2);
  const b=music.play('B',0,1);ctx.advance(.9);await b;ctx.advance(2);
  const oneShot=music.play('A',1,1);ctx.advance(.9);await oneShot;
  const a=ctx.sources.at(-1);assert.equal(a.offset,0);assert.equal(a.loop,false);assert.equal(a.gain.gain.events.length,0);
});
