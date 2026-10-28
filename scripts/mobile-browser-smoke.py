"""Silent real-game checks for the compact menu and responsive viewport."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import json, os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/network-ux';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783');engine=os.environ.get('BROWSER','webkit')
with sync_playwright() as p:
 browser=getattr(p,engine).launch(headless=True);context=browser.new_context(viewport={'width':734,'height':343},is_mobile=True,has_touch=True,device_scale_factor=3);use_silent_audio(context)
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("sessionStorage.setItem('homm3.session','old-network-session');localStorage.setItem('homm3.nickname','Solo player')")
 page.goto(BASE+'/');page.get_by_role('link',name='Одиночная игра',exact=True).click();page.wait_for_function('window.homm3PortDiagnostics?.screen==="main"',timeout=120000)
 assert page.evaluate('!window.homm3Room');assert page.locator('#tavern').is_hidden();assert page.locator('#view-tavern').is_hidden()
 canvas=page.locator('#canvas')
 if engine=='chromium':
  cdp=context.new_cdp_session(page)
  page.evaluate("window.testMouse=[];for(const type of ['mousedown','mouseup'])Module.canvas.addEventListener(type,e=>testMouse.push([type,e.button]));")
  box=canvas.bounding_box();x=box['x']+box['width']*650/800;y=box['y']+box['height']*70/600
  cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]});page.wait_for_timeout(750)
  assert page.evaluate('testMouse')==[['mousedown',2]];assert page.locator('#touch-hold-ring').is_visible()
  cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(250)
  assert page.evaluate('testMouse')==[['mousedown',2],['mouseup',2]];assert page.locator('#touch-hold-ring').is_hidden()
  page.evaluate('testMouse=[]');before=canvas.bounding_box()
  cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':300,'y':200,'id':1},{'x':400,'y':200,'id':2}]})
  cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':280,'y':200,'id':1},{'x':420,'y':200,'id':2}]});page.wait_for_timeout(200)
  cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});assert canvas.bounding_box()==before;assert page.evaluate('testMouse')==[]
  cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]});page.wait_for_timeout(700)
  cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]});page.wait_for_timeout(250)
  assert page.evaluate('testMouse')==[['mousedown',2],['mouseup',2]]
 canvas.press('n');page.wait_for_function('window.homm3PortDiagnostics.screen==="new"');canvas.press('s');page.wait_for_function('window.homm3PortDiagnostics.screen==="scenarios"');canvas.press('b');page.wait_for_timeout(3000);canvas.press('Enter');page.wait_for_function('window.homm3PortDiagnostics.screen==="adventure"',timeout=60000)
 initial=page.evaluate('window.homm3GameState.y');canvas.press('ArrowDown');page.wait_for_function('(y)=>window.homm3GameState.y===y+1',arg=initial)
 for width,height in [(734,343),(393,659),(1440,900)]:
  page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(500)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight')
  assert page.locator('.game-buttons button:visible').count()==1
  box=page.locator('#view-toggle').bounding_box();assert box['width']==44 and box['height']==44
  page.screenshot(path=str(OUT/(engine+f'-game-{width}.png')))
  page.locator('#view-toggle').tap();assert page.locator('#view-actions').is_visible();assert page.locator('#view-actions').evaluate('(e)=>e.scrollHeight<=e.clientHeight')
  assert page.locator('[data-army-action], [data-game-key], #extra-controls').count()==0
  page.screenshot(path=str(OUT/(engine+f'-menu-{width}.png')))
  page.locator('#view-settings').tap();page.locator('#smooth-camera').tap();assert page.locator('#smooth-camera').get_attribute('aria-pressed')=='false';page.locator('#smooth-camera').tap();page.locator('#settings-back').tap()
  page.locator('#view-exit').tap();assert page.locator('#exit-dialog').is_visible();page.locator('#exit-cancel').tap();assert page.locator('#exit-dialog').is_hidden();page.locator('#view-resume').tap();assert page.locator('#view-actions').is_hidden()
 assert not errors,errors
 (OUT/(engine+'-game-results.json')).write_text(json.dumps({'passed':True,'errors':errors,'checks':['real solo entry','old network session not restored in solo','actual hero movement','single 44px menu control','mobile and desktop menu fits','settings/back','cancel exit']},ensure_ascii=False,indent=2))
 browser.close();print(engine,'real solo, movement, compact menu, settings, exit, 3 sizes PASS')
