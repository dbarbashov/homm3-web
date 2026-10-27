"""Start AB, SoD and an external H3C; exercise touch WebKit too."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/campaigns';results=[]
with sync_playwright() as p:
 for label,engine,selected,campaign in [('ab','chromium',300,7),('sod-phone','webkit',70,15),('custom','chromium',420,20)]:
  if os.environ.get('CASE') and os.environ['CASE']!=label:continue
  browser=getattr(p,engine).launch(headless=True);page=browser.new_page(viewport={'width':844,'height':390} if engine=='webkit' else {'width':1100,'height':850},has_touch=engine=='webkit');logs=[];errors=[]
  def log(t):logs.append(t);(OUT/(label+'.log')).write_text('\n'.join(logs))
  page.on('console',lambda m:log(m.text));page.on('pageerror',lambda e:errors.append(str(e)))
  c=page.locator('#canvas')
  def screen(n):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=n,timeout=90000);page.wait_for_timeout(350)
  def click(x,y):
   box=c.bounding_box();c.click(position={'x':x*box['width']/800,'y':y*box['height']/600})
  try:
   page.goto('http://127.0.0.1:8783/port/game.html?hd=0');page.locator('#start').click();screen('main')
   if label=='custom':page.evaluate('''async()=>{const r=await fetch('/api/asset?name=Good1.h3c');if(!r.ok)throw Error('fixture missing');Module.FS.writeFile('/runtime/maps/Test.h3c',new Uint8Array(await r.arrayBuffer()));}''')
   c.press('n');screen('new');c.press('c');screen('campaign-sets');click(600,selected)
   if label=='custom':screen('custom-campaigns');click(170,132);click(495,555)
   else:screen('campaigns');click(180,125)
   screen('campaign-briefing');page.wait_for_timeout(1300);click(520,485);page.wait_for_timeout(200);click(550,556);page.wait_for_timeout(4000)
   page.screenshot(path=str(OUT/(label+'-prologue.png')))
   # Let AB's original narration finish naturally; other branches test skip input.
   if label=='ab':page.wait_for_function('window.homm3CampaignState?.active && window.homm3GameState?.day===1',timeout=150000)
   else:click(200,200);page.wait_for_timeout(1500)
   for _ in range(20):
    if page.evaluate('window.homm3PortDiagnostics?.screen==="adventure"'):break
    c.press('Enter');page.wait_for_timeout(350)
   screen('adventure');state=page.evaluate('window.homm3CampaignState');assert state['campaign']==campaign,state
   assert not errors,errors;page.screenshot(path=str(OUT/(label+'.png')));results.append({'case':label,'campaign':state,'errors':errors});print(results[-1],flush=True)
  except Exception:
   page.screenshot(path=str(OUT/(label+'-failure.png')));print(logs[-15:],errors,flush=True);raise
  finally:browser.close()
(OUT/'sets.json').write_text(json.dumps({'passed':True,'results':results},indent=2))
