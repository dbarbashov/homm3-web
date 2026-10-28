"""Silent Chromium/WebKit native transport checks with explicit native/transport doubles."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from browser_audio import use_silent_audio
from playwright.sync_api import sync_playwright
CSS='\n'.join((ROOT/p).read_text() for p in ['web/site/site.css','web/site/mobile.css'])
JS=(ROOT/'web/site/fast-game.js').read_text()
HTML='<html><head><style>'+CSS+'</style></head><body class="game-immersive"><main id="game-shell"><section class="game-board"><div id="game-stage"><canvas id="canvas" tabindex="0" width="800" height="600"></canvas></div><div class="game-buttons"><button id="menu">Меню</button></div></section><aside id="tavern" hidden></aside></main></body></html>'
fixture={"day":1,"week":1,"month":1,"absoluteDay":1,"localPlayer":0,"gameOver":False,"mapSize":72,"camera":{"x":1,"y":1,"z":0},"players":[{"slot":0,"dpid":1,"human":True,"alive":True,"name":"Красный","resources":[10,2,10,2,2,2,10000]},{"slot":1,"dpid":2,"human":True,"alive":True,"name":"Синий","resources":[10,2,10,2,2,2,10000]}],"heroes":[{"id":4,"owner":0,"name":"Катрин <img onerror=1>","movement":1500,"mana":20,"x":7,"y":8,"z":0,"army":[{"type":1,"count":10}]},{"id":5,"owner":1,"name":"Чужой","movement":1500}],"towns":[{"id":0,"owner":0,"name":"Замок","buildings":[{"id":1,"name":"Рынок","allowed":True,"cost":[5,0,0,0,0,0,500]},{"id":2,"name":"Капитолий","allowed":False,"cost":[0,0,0,0,0,0,10000]}],"offers":[{"id":6,"name":"Роланд"}],"creatures":[{"slot":0,"type":1,"name":"Копейщики","available":14,"cost":[0,0,0,0,0,0,60]}]},{"id":1,"owner":1,"name":"Чужой город"}]}
setup="""window.commands=[];window.snapshots=[];window.interrupts=[];window.fileWrites=[];window.nativeClicks=0;window.menuClicks=0;window.homm3FastTransport={sendCommand:(c,id,day)=>{commands.push({c,id,day});return true;},sendSnapshot:(meta,bytes)=>{snapshots.push({meta,bytes:Array.from(bytes)});return true;},interrupt:m=>interrupts.push(m)};window.Module={FS:{writeFile:(path,bytes)=>fileWrites.push({path,bytes:Array.from(bytes)}),unlink:()=>{}}};document.getElementById('canvas').addEventListener('mousedown',()=>nativeClicks++);document.getElementById('menu').addEventListener('click',()=>menuClicks++);"""
results=[]
with sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch(headless=True)
  ctx=browser.new_context();use_silent_audio(ctx)
  errors=[]
  def fresh():
   page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(HTML);page.evaluate(setup);page.add_script_tag(content=JS)
   return page
  page=fresh()
  def control(message):page.evaluate('(detail)=>dispatchEvent(new CustomEvent("homm3-fast-control",{detail}))',message)
  def packet(revision):page.evaluate('(revision)=>dispatchEvent(new CustomEvent("homm3-fast-packet",{detail:{meta:{revision,day:1},bytes:new Uint8Array([revision+1])}}))',revision)
  def imported():
   command=page.evaluate('Array.from(homm3FastNative.take())')
   page.evaluate('([seq,view])=>homm3FastNative.complete({seq,ok:true,day:1,view},null)',[command[6],dict(fixture,localPlayer=1)])
  assert page.evaluate('homm3FastNative.take()') is None
  assert page.evaluate('homm3FastNative.request(1,4,2,0)')==0
  page.evaluate('homm3FastNative.started(0,true)')
  assert page.evaluate('Array.from(homm3FastNative.take())')==[10,0,0,0,0,0,0,0]
  page.evaluate('(view)=>homm3FastNative.complete({seq:0,ok:true,day:1,view},new Uint8Array([1]))',fixture)
  assert page.locator('#fast-panel').count()==0
  page.locator('#canvas').dispatch_event('mousedown');assert page.evaluate('nativeClicks')==1
  for op,expected in [(1,{'kind':'move','id':4,'a':2}),(2,{'kind':'build','id':4,'a':2}),(3,{'kind':'hire','id':4,'a':2}),(4,{'kind':'recruit','id':4,'a':2,'b':7})]:
   ticket=page.evaluate('(op)=>homm3FastNative.request(op,4,2,7)',op)
   sent=page.evaluate('commands.at(-1)');assert sent['c']==expected
   assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==0
   control({'type':'fast_result','id':sent['id'],'ok':True,'revision':1})
   assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==1
  control({'type':'fast_execute','seq':1,'actor':1,'day':1,'command':{'kind':'move','id':5,'a':6}})
  assert page.evaluate('Array.from(homm3FastNative.take())')==[1,1,5,6,0,0,1,1]
  page.evaluate('(view)=>homm3FastNative.complete({seq:1,ok:true,day:1,view},new Uint8Array([2]))',fixture)
  assert page.evaluate('snapshots.length')==2
  ticket=page.evaluate('homm3FastNative.request(5,0,0,0)')
  assert page.evaluate('commands.at(-1).c')=={'kind':'end_day'}
  assert page.evaluate('homm3FastNative.request(1,4,2,0)')==0
  control({'type':'fast_state','day':1,'ready':[0],'pending':0})
  assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==1
  control({'type':'fast_state','day':2,'ready':[],'pending':0})
  assert page.evaluate('homm3FastNative.request(1,4,2,0)')==0
  page.evaluate('(view)=>homm3FastNative.projection({...view,day:2,absoluteDay:2})',fixture)
  assert page.evaluate('homm3FastNative.request(1,4,2,0)')>0
  page.close();page=fresh()
  packet(0);page.evaluate('homm3FastNative.started(1,false)');imported()
  ticket=page.evaluate('homm3FastNative.request(1,5,2,0)');sent=page.evaluate('commands.at(-1)')
  control({'type':'fast_result','id':sent['id'],'ok':True,'revision':2})
  assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==0
  packet(1)
  command=page.evaluate('Array.from(homm3FastNative.take())')
  packet(2);assert page.evaluate('homm3FastNative.take()') is None
  page.evaluate('([seq,view])=>homm3FastNative.complete({seq,ok:true,day:1,view},null)',[command[6],fixture])
  assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==0
  imported();assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==1
  assert page.evaluate('snapshots.length')==0
  ticket=page.evaluate('homm3FastNative.request(2,0,2,0)');sent=page.evaluate('commands.at(-1)')
  control({'type':'fast_error','id':sent['id'],'message':'Insufficient resources'})
  assert page.evaluate('(t)=>homm3FastNative.result(t)',ticket)==-1
  assert page.evaluate('homm3FastNative.canRun')
  page.evaluate("homm3FastNative.fault('Test interruption')")
  assert page.evaluate('homm3FastNative.request(1,5,2,0)')==0
  assert page.evaluate('interrupts.length')==1
  assert not errors,errors
  results.append({'engine':engine,'passed':True,'checks':'off-path input; no HTML controls; strict command payloads; host execution; readiness/day gate; guest ack waits for matching snapshot; serialized imports; command rejection; fatal interruption','errors':errors})
  ctx.close();browser.close()
output=ROOT/'test-results'/'fast-ui';output.mkdir(parents=True,exist_ok=True)
(output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
