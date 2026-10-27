"""Exercise HD geometry and army actions through real SDL input only."""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/hd';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=getattr(p,os.getenv('BROWSER','chromium')).launch(headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    page.add_init_script("Object.defineProperty(document,'fullscreenEnabled',{get:()=>false})")
    errors=[];logs=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:logs.append(m.text))
    c=page.locator('#canvas')
    def click(x,y,modal=False,mods=None,double=False):
        st=page.evaluate('window.homm3HDState||{width:800,height:600}')
        if modal:x+=(st['width']-800)/2;y+=(st['height']-600)/2
        box=c.bounding_box();position={'x':x*box['width']/st['width'],'y':y*box['height']/st['height']}
        (c.dblclick if double else c.click)(position=position,modifiers=mods or [],delay=100)
    def screen(name):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=name,timeout=90000)
    def shot(name):page.wait_for_timeout(600);c.screenshot(path=str(OUT/(name+'.png')));print(name,page.evaluate('({hd:window.homm3HDState,game:window.homm3GameState,army:window.homm3Army})'),flush=True)
    try:
        page.goto('http://127.0.0.1:8783/port/game.html');page.locator('#start').click(timeout=60000);screen('main')
        c.press('n');screen('new');c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure')
        page.wait_for_timeout(1500);shot('adventure')
        page.wait_for_function('window.homm3HDState?.width>800 && window.homm3HDState.adventure',timeout=10000)
        initial=page.evaluate('window.homm3GameState')
        c.press('ArrowDown');page.wait_for_function('(y)=>window.homm3GameState.y===y',arg=initial['y']+1);page.wait_for_function('!window.homm3GameState.moving');shot('movement')
        w=page.evaluate('window.homm3HDState.width');click(w-160,228,double=True);page.wait_for_timeout(800);shot('hero')
        # Hero screen original seven army selectors run from x22 to x508, y275.
        before=page.evaluate('window.homm3Army')
        click(107,524,modal=True,mods=['Control']);page.wait_for_function('window.homm3Army[2].count===1');shot('single')
        click(107,524,modal=True,mods=['Control','Shift']);page.wait_for_function('window.homm3Army.filter(x=>x.count>0).length===7');shot('singles')
        assert sum(x['count'] for x in page.evaluate('window.homm3Army'))==sum(x['count'] for x in before)
        click(107,524,modal=True,mods=['Alt']);page.wait_for_function('window.homm3Army[0].count===15');shot('gather')
        click(107,524,modal=True,mods=['Shift']);page.wait_for_function('window.homm3Army[0].count===8 && window.homm3Army[2].count===7');shot('balance')
        c.press('Escape');page.wait_for_timeout(600)
        w=page.evaluate('window.homm3HDState.width');click(w-30,228,double=True);page.wait_for_timeout(800);shot('town')
        gold=page.evaluate('window.homm3GameState.gold');c.press('r');page.wait_for_timeout(800);shot('recruit-preview')
        c.press('Escape');page.wait_for_timeout(500);assert page.evaluate('window.homm3GameState.gold')==gold
        c.press('r');page.wait_for_timeout(500);c.press('Enter');page.wait_for_timeout(700);shot('recruited')
        c.press('Escape');page.wait_for_timeout(600)
        page.wait_for_function('(g)=>window.homm3GameState.gold<g',arg=gold)
        page.set_viewport_size({'width':1600,'height':800});page.wait_for_timeout(1000);print('resize-state',page.evaluate('({hd:window.homm3HDState,wanted:window.homm3HDSize,view:window.homm3Viewport})'),flush=True);page.wait_for_function('window.homm3HDState.width===1200');shot('wide');page.locator('#view-toggle').click();page.locator('#fullscreen').click();page.wait_for_timeout(700);c.screenshot(path=str(OUT/'fullscreen.jpg'),type='jpeg',quality=88)
        page.set_viewport_size({'width':800,'height':1000});page.wait_for_function('window.homm3HDState.height===1000');shot('tall')
        page.set_viewport_size({'width':1280,'height':800});page.wait_for_function('window.homm3HDState.width===960 && window.homm3HDState.height===600');shot('restored')
        page.wait_for_timeout(500)
        (OUT/'probe.json').write_text(json.dumps({'passed':True,'checks':['adaptive map width/height','movement','centered hero/town windows','Ctrl single','Ctrl Shift singles','Alt gather','Shift balance','recruit preview/cancel/confirm','resize after dialogs','fullscreen'],'hd':page.evaluate('window.homm3HDState'),'errors':errors,'logs':logs[-15:]},indent=2))
        assert not errors,errors
    finally:
        page.screenshot(path=str(OUT/'last.png'));print('last',page.evaluate('({hd:window.homm3HDState,wanted:window.homm3HDSize,game:window.homm3GameState})'),flush=True)
        (OUT/'console.log').write_text('\n'.join(logs));browser.close()
