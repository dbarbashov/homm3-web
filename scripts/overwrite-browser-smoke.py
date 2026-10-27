"""Overwrite/cancel through original dialogs; verify bytes and loaded game after reload."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'test-results/overwrite';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True);context=b.new_context(viewport={'width':1100,'height':1100});page=context.new_page();errors=[];logs=[]
 page.on('pageerror',lambda e:errors.append(e.stack));page.on('console',lambda m:logs.append(m.text));c=page.locator('#canvas')
 def screen(name):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=name,timeout=90000)
 def state():page.wait_for_timeout(300);return page.evaluate('window.homm3GameState')
 def capture(name):c.screenshot(path=str(out/(name+'.png')));print(name,page.evaluate('window.homm3PortDiagnostics?.screen'),state(),flush=True)
 def digest(name):return page.evaluate('async n=>{const data=Module.FS.readFile("/runtime/games/"+n);let h=2166136261;for(const b of data)h=Math.imul(h^b,16777619);return {bytes:data.length,hash:(h>>>0).toString(16)}}',name)
 def start():page.locator('#start').click(timeout=90000);screen('main');page.evaluate('window.saveEvents=0;addEventListener("homm3-save-persisted",()=>++window.saveEvents)')
 def pos(x,y):
  box=c.bounding_box();return {'x':x*box['width']/800,'y':y*box['height']/600}
 def saveClick():c.click(position=pos(495,555),delay=100);page.wait_for_timeout(700)
 try:
  page.goto(os.environ.get('HOMM3_TEST_URL','http://127.0.0.1:8783/port/game.html'));start()
  c.press('n');screen('new');c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure')
  first=state();c.press('s');screen('scenarios');saveClick();page.wait_for_function('window.saveEvents===1');capture('first-saved');c.press('Enter');page.wait_for_timeout(700)
  saves=page.evaluate(r'Module.FS.readdir("/runtime/games").filter(n=>/\.GM1$/i.test(n))');name=next(n for n in saves if n.upper().startswith('NEWGAME'));before=digest(name)
  c.hover(position=pos(320,280));c.press('ArrowDown');page.wait_for_function('(y)=>window.homm3GameState.y===y && !window.homm3GameState.moving',arg=first['y']+1);changed=state();capture('moved')
  c.press('s');screen('scenarios');saveClick();capture('overwrite-prompt');c.press('Escape');page.wait_for_timeout(700);capture('overwrite-cancel')
  assert digest(name)==before,'Cancel changed the save'
  assert page.evaluate('window.saveEvents')==1
  saveClick();capture('overwrite-confirm');c.press('Enter');page.wait_for_function('window.saveEvents===2',timeout=15000);capture('overwritten');c.press('Enter');page.wait_for_timeout(700)
  after=digest(name);assert before!=after,'Overwrite kept old bytes'
  names=page.evaluate(r'Module.FS.readdir("/runtime/games").filter(n=>/\.GM1$/i.test(n))');assert names==saves,(names,saves)
  page.reload();start();assert digest(name)==after,'IndexedDB kept old bytes'
  c.press('l');screen('load');c.press('s');screen('scenarios');c.press('l');screen('adventure');loaded=state();capture('loaded-overwrite')
  for k in ['day','hero','x','y','z','movement','gold']:assert loaded[k]==changed[k],(k,loaded,changed)
  assert not errors,errors
  (out/'results.json').write_text(json.dumps({'passed':True,'url':page.url,'secureContext':page.evaluate('isSecureContext'),'buildFingerprint':page.evaluate('window.homm3Build'),'save':name,'before':before,'after':after,'cancelPreservedBytes':True,'persistedAfterReload':True,'initialState':first,'savedState':changed,'loadedState':loaded,'errors':errors},indent=2))
 finally:
  capture('last');(out/'errors.json').write_text(json.dumps(errors));(out/'console.json').write_text(json.dumps(logs,indent=2));context.close();b.close()
