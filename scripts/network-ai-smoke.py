"""Two humans in a four-seat lobby; remaining scenario slots must run as AI."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json,time,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/network-ai';OUT.mkdir(parents=True,exist_ok=True)
MAP=os.environ.get('TEST_MAP','All for One.h3m')
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=[]);pages=[b.new_context(viewport={'width':1360,'height':1000}).new_page() for _ in range(2)];errors=[]
 def state(page):return page.evaluate('({game:window.homm3GameState,net:window.homm3NetworkState,heroes:window.homm3HeroStates,screen:window.homm3PortDiagnostics?.screen})')
 def catalog(route):
  r=route.fetch();v=r.json();v['maps']=[MAP];route.fulfill(response=r,json=v)
 def acknowledge(page,slot,day):
  for _ in range(50):
   st=state(page)
   if st.get('game') and st['net']['turnSlot']==slot and st['game']['day']==day and st['game']['hero']>=0 and st['screen']=='adventure':break
   page.locator('#canvas').press('Enter');page.wait_for_timeout(500)
  else:raise AssertionError(('Turn not ready',slot,day,state(page)))
  page.wait_for_timeout(1000)
 try:
  for i,page in enumerate(pages):
   page.on('pageerror',lambda e:errors.append(e.stack));page.route('**/api/catalog',catalog);page.goto('http://127.0.0.1:8783/port/game.html#multiplayer');page.locator('#player-name').fill(['AI host','AI guest'][i])
  a,c=pages;a.locator('#show-create').click();a.locator('#room-name').fill('AI regression '+str(time.time_ns()));a.locator('#capacity').select_option('4');a.locator('#create-submit').click();a.wait_for_function('window.homm3Room?.players.length===1');invite=a.locator('#invite-link').input_value();c.goto("about:blank");c.goto(invite);c.locator('#player-name').fill('AI guest');c.locator('#join-invite').click();a.wait_for_function('window.homm3Room.players.length===2')
  for page in pages:page.wait_for_function('document.querySelector("#status").textContent.includes("Ресурсы готовы")',timeout=60000);page.locator('#ready').click()
  a.wait_for_function('window.homm3Room.players.every(p=>p.ready)',timeout=120000);a.locator('#launch-room').click()
  for page in pages:page.wait_for_function('window.homm3PortDiagnostics?.screen==="scenarios"',timeout=60000)
  a.wait_for_timeout(2000);a.locator('#canvas').click(position={'x':495,'y':555});a.wait_for_timeout(4000)
  results=[];expected_army=None;hd_checks=[]
  for day in [1,2,3]:
   for slot,page in enumerate(pages):
    acknowledge(page,slot,day);st=state(page);print('turn',day,slot,st,flush=True);results.append(st)
    if day==1 and slot==0:
     canvas=page.locator('#canvas');page.wait_for_timeout(400)
     def hd_click(x,y,modal=False,mods=None,double=False):
      size=page.evaluate('window.homm3HDState');box=canvas.bounding_box()
      if modal:x+=(size['width']-800)/2;y+=(size['height']-600)/2
      (canvas.dblclick if double else canvas.click)(position={'x':x*box['width']/size['width'],'y':y*box['height']/size['height']},modifiers=mods or [],delay=100)
     width=page.evaluate('window.homm3HDState.width');hd_click(width-160,228,double=True);page.wait_for_timeout(500)
     hd_click(107,524,True,['Control','Shift']);page.wait_for_timeout(500)
     expected_army=page.evaluate('window.homm3HeroStates[0].counts');assert expected_army.count(1)>=1,expected_army
     canvas.press('Escape');page.wait_for_timeout(500);hd_checks.append('host split into single units')
    if day==1 and slot==1:
     assert page.evaluate('window.homm3HeroStates[0].counts')==expected_army,(expected_army,state(page))
     hd_checks.append('guest received identical army after turn transfer')
    page.locator('#canvas').press('e');page.wait_for_timeout(400);page.screenshot(path=str(OUT/f'transfer-{day}-{slot}.png'));page.wait_for_timeout(400);page.locator('#canvas').press('Enter')
   for tick in range(90):
    if a.evaluate('(day)=>window.homm3GameState?.day>day',day):break
    if tick%10==0:print('AI',state(c),flush=True)
    a.wait_for_timeout(1000)
   else:raise AssertionError(('AI did not finish',*[state(page) for page in pages]))
  assert not errors,errors
  (OUT/'results.json').write_text(json.dumps({'passed':True,'map':MAP,'capacity':4,'clients':2,'days':3,'states':results,'hdChecks':hd_checks,'errors':errors},indent=2));print('PASS',MAP,flush=True)
 finally:
  for i,page in enumerate(pages):
   page.screenshot(path=str(OUT/f'last-{i}.png'));(OUT/f'last-{i}.json').write_text(json.dumps(state(page),indent=2))
  b.close()
