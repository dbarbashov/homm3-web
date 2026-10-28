"""Silent Chromium/WebKit command-panel checks with explicit native/transport doubles."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from browser_audio import use_silent_audio
from playwright.sync_api import sync_playwright
CSS='\n'.join((ROOT/p).read_text() for p in ['web/site/site.css','web/site/mobile.css','web/site/fast-game.css'])
JS=(ROOT/'web/site/fast-game.js').read_text()
HTML='<html><head><style>'+CSS+'</style></head><body class="game-immersive"><main id="game-shell"><section class="game-board"><div id="game-stage"><canvas id="canvas" tabindex="0" width="800" height="600"></canvas></div><div class="game-buttons"><button id="menu">Меню</button></div></section><aside id="tavern" hidden></aside></main></body></html>'
fixture={"day":1,"week":1,"month":1,"absoluteDay":1,"localPlayer":0,"gameOver":False,"mapSize":72,"camera":{"x":1,"y":1,"z":0},"players":[{"slot":0,"dpid":1,"human":True,"alive":True,"name":"Красный","resources":[10,2,10,2,2,2,10000]},{"slot":1,"dpid":2,"human":True,"alive":True,"name":"Синий","resources":[10,2,10,2,2,2,10000]}],"heroes":[{"id":4,"owner":0,"name":"Катрин <img onerror=1>","movement":1500,"mana":20,"x":7,"y":8,"z":0,"army":[{"type":1,"count":10}]},{"id":5,"owner":1,"name":"Чужой","movement":1500}],"towns":[{"id":0,"owner":0,"name":"Замок","buildings":[{"id":1,"name":"Рынок","allowed":True,"cost":[5,0,0,0,0,0,500]},{"id":2,"name":"Капитолий","allowed":False,"cost":[0,0,0,0,0,0,10000]}],"offers":[{"id":6,"name":"Роланд"}],"creatures":[{"slot":0,"type":1,"name":"Копейщики","available":14,"cost":[0,0,0,0,0,0,60]}]},{"id":1,"owner":1,"name":"Чужой город"}]}
setup="""window.commands=[];window.snapshots=[];window.interrupts=[];window.fileWrites=[];window.nativeClicks=0;window.menuClicks=0;window.homm3FastTransport={sendCommand:(c,id,day)=>{commands.push({c,id,day});return true;},sendSnapshot:(meta,bytes)=>{snapshots.push({meta,bytes:Array.from(bytes)});return true;},interrupt:m=>interrupts.push(m)};window.Module={FS:{writeFile:(path,bytes)=>fileWrites.push({path,bytes:Array.from(bytes)}),unlink:()=>{}}};document.getElementById('canvas').addEventListener('mousedown',()=>nativeClicks++);document.getElementById('menu').addEventListener('click',()=>menuClicks++);"""
results=[]
with sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch(headless=True)
  ctx=browser.new_context(viewport={'width':1280,'height':800});use_silent_audio(ctx)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML);page.evaluate(setup);page.add_script_tag(content=JS)
  assert page.locator('#fast-panel').count()==0
  assert page.evaluate('homm3FastNative.take()') is None
  page.locator('#canvas').dispatch_event('mousedown');assert page.evaluate('nativeClicks')==1
  page.evaluate('homm3FastNative.started(0,true)')
  assert page.evaluate('Array.from(homm3FastNative.take())')==[10,0,0,0,0,0,0,0]
  page.evaluate('(view)=>homm3FastNative.complete({seq:0,ok:true,day:1,view},new Uint8Array([1,2,3]))',fixture)
  assert page.evaluate('snapshots.length')==1
  assert page.locator('#fast-hero option').count()==1
  assert page.locator('#fast-town option').count()==1
  assert page.locator('#fast-panel img').count()==0
  page.locator('#canvas').dispatch_event('mousedown');assert page.evaluate('nativeClicks')==1
  page.locator('#menu').click();assert page.evaluate('menuClicks')==1
  page.locator('button[aria-label="Восток"]').click()
  assert page.evaluate('commands.at(-1).c')=={'kind':'move','id':4,'a':2}
  page.keyboard.press('ArrowUp');assert page.evaluate('commands.at(-1).c.a')==0
  page.locator('#canvas').focus();page.keyboard.press('Shift+ArrowLeft')
  command=page.evaluate('Array.from(homm3FastNative.take())');assert command[0]==9 and command[3]==-4
  page.evaluate('(c)=>homm3FastNative.complete({seq:c[6],ok:true},null)',command)
  page.locator('[data-section=build] summary').click();assert page.locator('[data-focus-key=build-2]').is_disabled()
  page.locator('[data-focus-key=build-1]').click();assert page.evaluate('commands.at(-1).c.kind')=='build'
  page.locator('[data-section=hire] summary').click();page.locator('[data-focus-key=hire-6]').click();assert page.evaluate('commands.at(-1).c.kind')=='hire'
  page.locator('[data-section=recruit] summary').click();count=page.locator('[data-focus-key=count-0-0]');count.fill('15');assert page.locator('[data-focus-key=recruit-0-0]').is_disabled()
  count.fill('5');page.locator('[data-focus-key=recruit-0-0]').click();assert page.evaluate('commands.at(-1).c')=={'kind':'recruit','id':0,'a':0,'b':5}
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-control',{detail:{type:'fast_execute',seq:1,actor:1,day:1,command:{kind:'move',id:5,a:6}}}))")
  command=page.evaluate('Array.from(homm3FastNative.take())');assert command==[1,1,5,6,0,0,1,1]
  page.evaluate('(view)=>homm3FastNative.complete({seq:1,ok:true,day:1,view},new Uint8Array([4,5]))',fixture)
  assert page.evaluate('snapshots.length')==2
  previous_message=page.locator('#fast-message').text_content()
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-control',{detail:{type:'fast_execute',seq:2,actor:1,day:1,command:{kind:'move',id:4,a:6}}}))")
  command=page.evaluate('Array.from(homm3FastNative.take())');assert command[1]==1
  page.evaluate('(view)=>homm3FastNative.complete({seq:2,ok:false,error:"Hero is not yours",day:1,view},new Uint8Array([4,5]))',fixture)
  assert page.locator('#fast-message').text_content()==previous_message, 'A guest rejection leaked into host feedback'
  assert page.evaluate('snapshots.at(-1).meta.ok') is False
  page.locator('#fast-end-day').click();assert page.locator('button[aria-label="Восток"]').is_disabled()
  n=page.evaluate('commands.length');page.locator('#canvas').focus();page.keyboard.press('ArrowUp');assert page.evaluate('commands.length')==n
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-control',{detail:{type:'fast_state',day:2,ready:[],pending:0}}))")
  assert page.locator('#fast-end-day').is_disabled()
  nextview=dict(fixture,day=2,absoluteDay=2)
  page.evaluate('(view)=>homm3FastNative.projection(view)',nextview);assert page.locator('#fast-end-day').is_enabled()
  for w,h in [(1280,800),(393,820),(844,390)]:
   page.set_viewport_size({'width':w,'height':h})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight')
   box=page.locator('#fast-panel').bounding_box();assert box['x']>=0 and box['y']>=0 and box['x']+box['width']<=w+1 and box['y']+box['height']<=h+1,(engine,w,box)
   assert page.locator('#fast-end-day').bounding_box()['height']>=40
   page.locator('#fast-collapse').click();assert page.locator('#fast-content').is_hidden();page.locator('#fast-collapse').click()
  page.evaluate('(view)=>homm3FastNative.projection({...view,gameOver:true})',nextview);assert page.locator('#fast-end-day').is_disabled()
  # New guest: no export; an arriving newer snapshot never overwrites one being imported.
  page.close();page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML);page.evaluate(setup);page.add_script_tag(content=JS)
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-packet',{detail:{meta:{seq:0,revision:0,day:1},bytes:new Uint8Array([1])}}));homm3FastNative.started(1,false)")
  first=page.evaluate('Array.from(homm3FastNative.take())');assert first[0]==6
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-packet',{detail:{meta:{seq:1,revision:1,day:1,gameOver:true},bytes:new Uint8Array([2])}}))")
  assert page.evaluate('homm3FastNative.take()') is None
  assert page.evaluate('fileWrites.length')==1
  guest=dict(fixture,localPlayer=1)
  page.evaluate('([seq,view])=>homm3FastNative.complete({seq,ok:true,day:1,view},null)',[first[6],guest])
  second=page.evaluate('Array.from(homm3FastNative.take())');assert second[0]==6 and second[6]!=first[6] and second[5]==1
  assert page.evaluate('fileWrites.at(-1).bytes')==[2]
  page.evaluate('([seq,view])=>homm3FastNative.complete({seq,ok:true,day:1,view},null)',[second[6],guest])
  assert page.evaluate('snapshots.length')==0
  assert page.locator('#fast-hero option').text_content()=='Чужой'
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-control',{detail:{type:'fast_result',seq:3,ok:false,error:'Недостаточно ресурсов'}}))")
  assert page.locator('#fast-message').text_content()=='Недостаточно ресурсов'
  assert 'fast-error' in page.locator('#fast-message').get_attribute('class')
  assert page.evaluate('homm3FastNative.canRun'), 'Rejected commands must not stop the game'
  page.evaluate("window.dispatchEvent(new CustomEvent('homm3-fast-control',{detail:{type:'fast_result',seq:4,ok:true}}))")
  assert page.locator('#fast-message').text_content()=='Команда выполнена.'
  assert 'fast-error' not in page.locator('#fast-message').get_attribute('class')
  page.evaluate("homm3FastNative.fault('Test interruption')")
  assert page.locator('#fast-end-day').is_disabled() and not page.evaluate('homm3FastNative.canRun')
  assert page.evaluate('interrupts.length')==1
  assert not errors,errors
  results.append({'engine':engine,'passed':True,'checks':'off path; host/guest queue; own selection; move/keyboard/camera; build/hire/recruit; readiness/day gate; import serialization; game over/fault; private rejected/successful command results; 3 viewport geometries','errors':errors})
  ctx.close();browser.close()
output=ROOT/'test-results'/'fast-ui'
output.mkdir(parents=True,exist_ok=True)
(output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
