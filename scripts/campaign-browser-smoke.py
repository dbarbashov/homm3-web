"""Campaign UI, original movies, save and scenario handoff through SDL input."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os
from browser_audio import use_silent_audio
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/campaigns';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1100,'height':850});logs=[];errors=[]
 use_silent_audio(page)
 def log(text):
  logs.append(text);(OUT/'live.log').write_text('\n'.join(logs))
 page.on('console',lambda m:log(m.text));page.on('pageerror',lambda e:(errors.append(str(e)),log('ERROR '+str(e))))
 c=page.locator('#canvas')
 def screen(name):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=name,timeout=90000);page.wait_for_timeout(300)
 def click(x,y):
  box=c.bounding_box();c.click(position={'x':x*box['width']/800,'y':y*box['height']/600})
 def capture(name):
  page.screenshot(path=str(OUT/(name+'.png')));print(name,page.evaluate('({screen:window.homm3PortDiagnostics?.screen,video:window.homm3VideoState,campaign:window.homm3CampaignState,game:window.homm3GameState})'),flush=True);(OUT/'browser.log').write_text('\n'.join(logs+errors))
 try:
  page.goto(BASE+'/port/game.html?hd=0');page.locator('#start').click();screen('main')
  c.press('c');screen('credits');page.wait_for_function('window.homm3VideoState?.id===33 && window.homm3VideoState.frames>10');capture('credits');c.press('Escape');screen('main')
  c.press('n');screen('new');c.press('c');screen('campaign-sets');click(600,160);screen('campaigns');click(180,125);screen('campaign-briefing');page.wait_for_timeout(1300);capture('briefing')
  click(520,485);page.wait_for_timeout(300);capture('bonus');click(550,556);page.wait_for_timeout(4000);capture('prologue');click(200,200);page.wait_for_timeout(4000);capture('after-video')
  for _ in range(12):
   if page.evaluate('window.homm3PortDiagnostics?.screen==="adventure"'):break
   c.press('Enter');page.wait_for_timeout(350)
  screen('adventure');capture('scenario-1')
  assert page.evaluate('window.homm3CampaignState.active && window.homm3CampaignState.campaign===0 && window.homm3CampaignState.map===0')
  c.press('s');screen('scenarios');click(495,555);page.wait_for_timeout(600);c.press('Enter');page.wait_for_function('window.homm3LastSave');capture('save')
  page.reload();page.locator('#start').click();screen('main');c.press('l');screen('load');c.press('c');screen('scenarios');c.press('l');screen('adventure');capture('loaded')
  assert page.evaluate('window.homm3CampaignState.active && window.homm3CampaignState.map===0')
  c.press('Tab');c.press_sequentially('nwcredpill',delay=50);c.press('Enter');page.wait_for_timeout(2000);capture('victory')
  for _ in range(8):
   current=page.evaluate('window.homm3PortDiagnostics?.screen')
   if current=='scenarios':break
   c.press('Enter');page.wait_for_timeout(600)
  capture('victory-save');click(495,555);page.wait_for_timeout(1000);c.press('Enter');page.wait_for_timeout(2000);capture('next-briefing')
  for _ in range(12):
   if page.evaluate('window.homm3PortDiagnostics?.screen==="campaign-briefing"'):break
   c.press('Enter');page.wait_for_timeout(500)
  screen('campaign-briefing');page.wait_for_timeout(1300);capture('scenario-2-briefing')
  click(520,485);page.wait_for_timeout(200);click(550,556);page.wait_for_timeout(3000);click(200,200);page.wait_for_timeout(1500)
  for _ in range(12):
   if page.evaluate('window.homm3PortDiagnostics?.screen==="adventure"'):break
   c.press('Enter');page.wait_for_timeout(350)
  screen('adventure');capture('scenario-2')
  assert page.evaluate('window.homm3CampaignState.map===1 && window.homm3GameState.hero===6')
  for expected in [2,3]:
   c.press('Tab');page.wait_for_timeout(200);c.press_sequentially('nwcredpill',delay=30);c.press('Enter')
   for _ in range(12):
    if page.evaluate('window.homm3PortDiagnostics?.screen==="scenarios"'):break
    c.press('Enter');page.wait_for_timeout(400)
   screen('scenarios');click(495,555)
   for _ in range(18):
    current=page.evaluate('window.homm3PortDiagnostics?.screen')
    if current in ['campaign-briefing','campaigns']:break
    c.press('Enter');page.wait_for_timeout(400)
   if expected==3:
    # Original victory and high-score dialogs precede the campaign chooser.
    for _ in range(12):
     if page.evaluate('window.homm3PortDiagnostics?.screen==="campaigns"'):break
     c.press('Enter');page.wait_for_timeout(400)
    screen('campaigns');capture('campaign-complete');break
   screen('campaign-briefing');page.wait_for_timeout(1300);click(520,485);click(550,556);page.wait_for_timeout(3000);click(200,200);page.wait_for_timeout(1500)
   for _ in range(12):
    if page.evaluate('window.homm3PortDiagnostics?.screen==="adventure"'):break
    c.press('Enter');page.wait_for_timeout(350)
   screen('adventure');assert page.evaluate('window.homm3CampaignState.map')==expected;capture('scenario-3')
  assert not errors,errors
  (OUT/'results.json').write_text(json.dumps({'passed':True,'checks':['credits movie and text','RoE campaign selection and bonus','prologue skip','scenario startup','campaign save and reload','original victory cheat for bookkeeping test','victory save','next scenario and retained hero','three scenario completions and final campaign chooser']},indent=2))
 except Exception:
  capture('failure');raise
 finally:
  (OUT/'browser.log').write_text('\n'.join(logs+errors));browser.close()
