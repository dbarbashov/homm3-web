"""Real browser: original cursors, decoded MP3 output and combat presentation."""
from pathlib import Path
from browser_audio import use_silent_audio
from playwright.sync_api import sync_playwright
import json,time,os
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'test-results'/('media-after' if os.getenv('BROWSER','chromium')=='chromium' else 'media-after-webkit');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=getattr(p,os.getenv('BROWSER','chromium')).launch(headless=True)
    context=browser.new_context(viewport={'width':1100,'height':1100},record_video_dir=str(out),record_video_size={'width':1100,'height':1100})
    page=context.new_page();use_silent_audio(page);errors=[];samples=[]
    page.on('pageerror',lambda e:errors.append(e.stack))
    c=page.locator('#canvas')
    def screen(name):page.wait_for_function('(name)=>window.homm3PortDiagnostics?.screen===name',arg=name,timeout=90000)
    def capture(name,track=None,cursor=None):
        page.wait_for_timeout(250)
        page.wait_for_function('window.homm3Music?.state.playing && window.homm3Music.state.context === "running"',timeout=20000)
        if track:page.wait_for_function('(s)=>window.homm3Music.state.track.toLowerCase().includes(s)',arg=track,timeout=15000)
        page.wait_for_function('window.homm3Music.samplePeak()>0.001',timeout=15000)
        if cursor is not None:page.wait_for_function('(s)=>window.homm3CursorState?.visible && window.homm3CursorState.set===s',arg=cursor)
        result=page.evaluate('({music:window.homm3Music.state,peak:window.homm3Music.samplePeak(),cursor:window.homm3CursorState,game:window.homm3GameState})')
        samples.append({'step':name,**result});c.screenshot(path=str(out/(name+'.png')));print(name,result,flush=True)
        assert not errors,errors
    def pos(x,y):
        box=c.bounding_box();return {'x':x*box['width']/800,'y':y*box['height']/600}
    try:
        page.goto('http://127.0.0.1:8783/port/game.html?hd=0');page.locator('#start').click(timeout=90000);screen('main')
        c.hover(position=pos(650,70));capture('menu','mainmenu',0)
        assert page.evaluate('getComputedStyle(document.querySelector("canvas")).cursor')=='none'
        assert page.locator('#music-toggle').count()==0
        c.press('n');screen('new');c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure')
        c.hover(position=pos(320,280));capture('adventure',cursor=1)
        c.dblclick(position=pos(770,231),delay=150);page.wait_for_timeout(1500);capture('town','town')
        c.press('Escape');page.wait_for_timeout(3000);c.hover(position=pos(320,280));capture('town-return','town',cursor=1)
        c.press('ArrowDown');page.wait_for_timeout(2000);capture('town-return-after-move','dirt',cursor=1)
        for key in ['ArrowDown','End']:c.press(key);page.wait_for_timeout(1700)
        page.wait_for_function('window.homm3GameState.combat===1');c.hover(position=pos(400,250));capture('battle','combat',2)
        c.click(position=pos(178,580),delay=120);page.mouse.move(20,20)
        deadline=time.monotonic()+180
        while page.evaluate('window.homm3PortDiagnostics.screen')!='combat-results':
            assert time.monotonic()<deadline,'battle timeout'
            assert not errors,errors
            page.wait_for_timeout(1000)
        capture('victory')
        c.press('Enter');screen('adventure');c.hover(position=pos(320,280));capture('battle-return','dirt',cursor=1)
        assert page.evaluate('window.homm3GameState.experience')>72
        page.wait_for_timeout(2000);c.press('Escape');page.wait_for_timeout(800);c.press('Enter');screen('main');c.hover(position=pos(650,70));capture('menu-return','mainmenu',0)
        c.press('Escape');page.wait_for_timeout(500);c.press('Enter');screen('closed')
        assert not page.evaluate('window.homm3Music.state.playing')
        (out/'results.json').write_text(json.dumps({'passed':True,'samples':samples,'errors':errors},indent=2))
    finally:
        print('FINAL',page.evaluate('({music:window.homm3Music?.state,cursor:window.homm3CursorState})'),flush=True)
        (out/'errors.json').write_text(json.dumps(errors,indent=2));c.screenshot(path=str(out/'last.png'));context.close();browser.close()
