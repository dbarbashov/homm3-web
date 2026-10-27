"""Profile real movement/town/scroll input with Chromium, without changing game state.
Run alone for comparable timings: RUN=before CPU=4 python3 scripts/performance-browser-probe.py
The CPU throttle is a stress test, not a model of a particular player's PC.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os,time,collections
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'test-results/performance'/os.getenv('RUN','current');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True);page=b.new_page(viewport={'width':1600,'height':900});errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:requests.append({'time':time.monotonic(),'url':r.url.split('?')[0]}))
 page.add_init_script('''(()=>{window.perf={frames:[],tasks:[],uploads:0};let last;function tick(t){if(last)perf.frames.push([t,t-last]);last=t;requestAnimationFrame(tick)}requestAnimationFrame(tick);new PerformanceObserver(l=>l.getEntries().forEach(e=>perf.tasks.push({start:e.startTime,duration:e.duration}))).observe({type:'longtask'});for(let type of [WebGLRenderingContext,WebGL2RenderingContext]){const orig=type.prototype.texSubImage2D;type.prototype.texSubImage2D=function(...args){++perf.uploads;return orig.apply(this,args)}}})()''')
 c=page.locator('#canvas')
 def screen(s):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=s,timeout=90000)
 def pos(x,y):
  st=page.evaluate('homm3HDState');box=c.bounding_box();return {'x':x*box['width']/st['width'],'y':y*box['height']/st['height']}
 page.goto('http://127.0.0.1:8783/port/game.html');page.locator('#start').click();screen('main');c.press('n');screen('new');c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure');page.wait_for_timeout(1500)
 c.hover(position=pos(320,280));cdp=page.context.new_cdp_session(page);cdp.send('Profiler.enable');cdp.send('Profiler.setSamplingInterval',{'interval':1000});cdp.send('Profiler.start')
 page.screenshot(path=str(out/'start.png'));print('start',page.evaluate('({screen:homm3PortDiagnostics,game:homm3GameState,hd:homm3HDState})'),flush=True)
 if os.getenv('CPU'):cdp.send('Emulation.setCPUThrottlingRate',{'rate':int(os.getenv('CPU'))})
 phases=[]
 def phase(name,fn):
  start=time.monotonic();before=page.evaluate('({now:performance.now(),uploads:perf.uploads})');ri=len(requests);fn();data=page.evaluate('(start)=>({elapsed:performance.now()-start.now,uploads:perf.uploads-start.uploads,frames:perf.frames.filter(x=>x[0]>=start.now).map(x=>x[1]),tasks:perf.tasks.filter(x=>x.start>=start.now)})',before);frames=sorted(data.pop('frames'));data.update({'phase':name,'rafFrames':len(frames),'p50':frames[len(frames)//2] if frames else 0,'p95':frames[int(len(frames)*.95)] if frames else 0,'max':max(frames,default=0),'gaps50':sum(x>50 for x in frames),'requests':requests[ri:]});data['state']=page.evaluate('({screen:homm3PortDiagnostics.screen,game:homm3GameState,hd:homm3HDState})');phases.append(data);page.screenshot(path=str(out/(name+'.png')));print(name,{k:v for k,v in data.items() if k not in ['tasks','requests','state']},flush=True)
 phase('idle',lambda:page.wait_for_timeout(5000))
 def movement():
  for key in ['ArrowDown','ArrowDown','ArrowUp','ArrowDown','ArrowUp','ArrowDown','ArrowUp']:
   old=page.evaluate('homm3GameState.y');c.press(key);page.wait_for_function('(y)=>homm3GameState.y!==y',arg=old);page.wait_for_function('!homm3GameState.moving');page.wait_for_timeout(300)
  assert page.evaluate('homm3HDState.layers')==0
 phase('movement',movement)
 def town():
  w=page.evaluate('homm3HDState.width');c.dblclick(position=pos(w-30,231),delay=120);page.wait_for_function('homm3HDState.layers>0');page.wait_for_timeout(1200);page.screenshot(path=str(out/'town-open.png'));c.press('Escape');page.wait_for_timeout(700)
 phase('town-first',town);phase('town-repeat',town)
 def scroll():
  for x in [page.evaluate('homm3HDState.width-212'),10]*3:c.hover(position=pos(x,280));page.wait_for_timeout(700)
  c.hover(position=pos(320,280))
 phase('scroll',scroll)
 phase('idle-after',lambda:page.wait_for_timeout(3000))
 profile=cdp.send('Profiler.stop')['profile'];(out/'cpu.json').write_text(json.dumps(profile));(out/'results.json').write_text(json.dumps({'phases':phases,'errors':errors,'hd':page.evaluate('homm3HDState'),'renderer':page.evaluate('Module.ctx?.getParameter?.(Module.ctx.RENDERER)'), 'cpuThrottle':int(os.getenv('CPU','1')), 'browser':b.version},indent=2))
 nodes={n['id']:n for n in profile['nodes']};counts=collections.Counter(profile.get('samples',[]));top=[{'samples':n,'function':nodes[i]['callFrame']['functionName'],'url':nodes[i]['callFrame']['url']} for i,n in counts.most_common(25)];(out/'top.json').write_text(json.dumps(top,indent=2));print(top[:12],flush=True);b.close()
