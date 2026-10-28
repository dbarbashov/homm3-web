"""Pick purple through the original scenario UI and verify browser chrome in a real game."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import json,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/player-theme';OUT.mkdir(parents=True,exist_ok=True);BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783');engine=os.environ.get('BROWSER','chromium')
with sync_playwright() as p:
 b=getattr(p,engine).launch();ctx=b.new_context(viewport={'width':1000,'height':750});use_silent_audio(ctx);g=ctx.new_page();errors=[];g.on('pageerror',lambda e:errors.append(str(e)));g.goto(BASE+'/port/game.html');g.locator('#start').click(timeout=60000);c=g.locator('#canvas')
 def screen(name):g.wait_for_function('(name)=>window.homm3PortDiagnostics?.screen===name',arg=name,timeout=90000)
 def point(x,y):
  box=c.bounding_box();c.click(position={'x':box['width']*x/800,'y':box['height']*y/600})
 screen('main');c.press('n');screen('new');c.press('s');screen('scenarios');point(530,518);g.wait_for_timeout(300);point(34,255);g.wait_for_timeout(300);g.screenshot(path=str(OUT/(engine+'-purple-selected.png')));c.press('b');g.wait_for_timeout(4000);c.press('Enter');screen('adventure')
 g.wait_for_function('window.homm3GameState?.localPlayer===5');g.wait_for_function('document.documentElement.dataset.playerColor==="5"');assert g.evaluate('window.homm3GameState.remote')==0
 for width,height in [(1000,750),(734,343),(393,659)]:
  g.set_viewport_size({'width':width,'height':height});g.wait_for_timeout(600);g.locator('#view-toggle').click();assert g.locator('#view-actions').evaluate('(e)=>e.scrollWidth===e.clientWidth && e.scrollHeight===e.clientHeight');g.screenshot(path=str(OUT/(engine+f'-purple-game-{width}.png')));g.locator('#view-resume').click()
 # A new day runs AI turns; the browser theme must remain the local player's.
 c.press('e');g.wait_for_timeout(500);c.press('Enter');g.wait_for_function('window.homm3GameState.day===2 && window.homm3GameState.player===5',timeout=120000);assert g.locator('html').get_attribute('data-player-color')=='5'
 assert not errors,errors;(OUT/(engine+'-game-results.json')).write_text(json.dumps({'passed':True,'localPlayer':5,'errors':errors,'checks':['purple selected in original UI','3 responsive sizes','AI/day transition retains local color']},indent=2));print(engine,'actual purple selection, 3 sizes, next day PASS');b.close()
