"""Real-time unlimited/finite turns and saved-game restoration, driven through game UI."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import os,json,argparse
p=argparse.ArgumentParser();p.add_argument('--finite',action='store_true');args=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/turn-duration';OUT.mkdir(parents=True,exist_ok=True)
engine=os.environ.get('BROWSER','chromium');base=os.environ.get('SITE_URL','http://127.0.0.1:8798');label=engine+('-finite' if args.finite else '-unlimited')
with sync_playwright() as p:
 b=getattr(p,engine).launch();ctx=b.new_context(viewport={'width':1000,'height':750});use_silent_audio(ctx);g=ctx.new_page();errors=[];g.on('pageerror',lambda e:errors.append(str(e)));c=g.locator('#canvas')
 def screen(s):g.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=s,timeout=120000)
 def point(x,y):
  box=c.bounding_box();c.click(position={'x':box['width']*x/800,'y':box['height']*y/600})
 def state():return g.evaluate('window.homm3GameState')
 def unlimited():
  g.wait_for_function('window.homm3GameState?.turnLimitIndex===10 && window.homm3GameState?.turnTimerOn===false');assert not state()['turnTimerExpired']
 g.goto(base+'/port/game.html');g.locator('#start').click();screen('main');c.press('n');screen('new');c.press('s');screen('scenarios');point(530,518);g.wait_for_timeout(300)
 if args.finite:
  for _ in range(10):point(66,565)
 g.screenshot(path=str(OUT/(label+'-setup.png')));c.press('b');g.wait_for_timeout(4000);c.press('Enter');screen('adventure')
 if args.finite:g.wait_for_function('window.homm3GameState?.turnLimitIndex===0 && window.homm3GameState?.turnTimerOn===true')
 else:unlimited()
 print(label,'started',state(),flush=True)
 for i in range(5):
  g.wait_for_timeout(14000)
  if not args.finite:unlimited();assert state()['day']==1
  print(label,'elapsed',(i+1)*14,flush=True)
 g.screenshot(path=str(OUT/(label+'-70seconds.png')))
 if args.finite:
  c.press('Enter');g.wait_for_function('window.homm3GameState.day===2 && window.homm3GameState.player===0',timeout=45000)
  assert state()['turnTimerOn'];checks=['one-minute limit chosen through slider','timer expires and advances day']
 else:
  c.press('s');screen('scenarios');point(495,555);g.wait_for_function('window.homm3LastSave',timeout=30000);c.press('Enter');g.wait_for_timeout(600)
  g.reload();g.locator('#start').click();screen('main');c.press('l');screen('load');c.press('s');screen('scenarios');c.press('l');screen('adventure');unlimited()
  c.press('e');g.wait_for_timeout(500);c.press('Enter');g.wait_for_function('window.homm3GameState.day===2 && window.homm3GameState.player===0',timeout=120000);unlimited()
  checks=['default unlimited stays on day 1 after 70 real seconds','save/reload retains disabled timer','manual end turn and AI next day retain disabled timer']
 assert not errors,errors;(OUT/(label+'.json')).write_text(json.dumps({'passed':True,'checks':checks,'state':state(),'errors':errors},indent=2));print(label,'PASS',flush=True);b.close()
