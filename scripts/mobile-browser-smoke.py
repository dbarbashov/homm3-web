"""iPhone-shaped WebKit + Chromium: real game, touch input and viewport geometry."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/mobile';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
with sync_playwright() as p:
    engine=os.environ.get('BROWSER','webkit')
    browser=getattr(p,engine).launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=3)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:(errors.append(e.stack),print(e.stack,flush=True)))
    page.on('console',lambda m:print(m.text,flush=True) if m.type=='error' else None)
    page.add_init_script("Object.defineProperty(document,'fullscreenEnabled',{get:()=>false})")
    def shot(name):
        page.screenshot(path=str(OUT/(engine+'-'+name+'.png')));print(name,page.evaluate('({view:window.homm3Viewport,screen:window.homm3PortDiagnostics?.screen,canvas:[Module.canvas.width,Module.canvas.height],dpr:devicePixelRatio})'),flush=True)
    def control(selector):
        page.locator('#view-toggle').tap();page.locator(selector).tap()
    def point(x,y):
        r=page.locator('#canvas').bounding_box();return (r['x']+x*r['width']/800,r['y']+y*r['height']/600)
    try:
        page.goto(BASE+'/port/game.html');page.locator('#start').tap(timeout=60000)
        page.wait_for_function('window.homm3PortDiagnostics?.screen==="main"',timeout=90000);page.wait_for_timeout(500)
        assert page.evaluate('window.homm3Viewport.immersive');shot('portrait-main')
        assert page.evaluate('[Module.canvas.width,Module.canvas.height]')==[800,600]
        assert page.locator('#view-plus').count()==0
        assert page.locator('#view-actions').is_hidden()
        if engine=='chromium':
            cdp=context.new_cdp_session(page)
            page.evaluate("window.testMouse=[]; for(const type of ['mousedown','mouseup']) Module.canvas.addEventListener(type,e=>testMouse.push([type,e.button]));")
            x,y=point(650,70)
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]})
            page.wait_for_timeout(750)
            assert page.evaluate('window.testMouse')==[['mousedown',2]]
            assert page.locator('#touch-hold-ring').is_visible()
            shot('long-press-help')
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            page.wait_for_timeout(250)
            assert page.evaluate('window.testMouse')==[['mousedown',2],['mouseup',2]]
            assert not page.locator('#touch-hold-ring').is_visible()
            assert page.evaluate('window.homm3PortDiagnostics.screen')=='main'
            # Two fingers neither zoom nor inject game clicks.
            page.evaluate('window.testMouse=[]');before=page.locator('#canvas').bounding_box()
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':130,'y':350,'id':1},{'x':250,'y':350,'id':2}]})
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':110,'y':350,'id':1},{'x':270,'y':350,'id':2}]})
            page.wait_for_timeout(200)
            assert page.locator('#canvas').bounding_box()==before
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            assert page.evaluate('window.testMouse')==[]
            # A cancelled hold must release the right button, never left-click.
            page.evaluate('window.testMouse=[]');x,y=point(650,70)
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]});page.wait_for_timeout(700)
            cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]});page.wait_for_timeout(250)
            assert page.evaluate('window.testMouse')==[['mousedown',2],['mouseup',2]]
        page.touchscreen.tap(*point(650,70));page.wait_for_function('window.homm3PortDiagnostics.screen==="new"',timeout=15000)
        page.touchscreen.tap(*point(650,70));page.wait_for_function('window.homm3PortDiagnostics.screen==="scenarios"',timeout=15000);shot('portrait-scenarios')
        page.set_viewport_size({'width':844,'height':390});page.wait_for_timeout(1000);shot('landscape-scenarios')
        r=page.locator('#canvas').bounding_box();assert r['y']>=0 and r['y']+r['height']<=390
        page.touchscreen.tap(*point(495,555));page.wait_for_timeout(4000);control('[data-game-key=Enter]');page.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure"',timeout=60000);shot('landscape-adventure')
        page.wait_for_function('window.homm3HDState.width>1000 && window.homm3HDState.adventure');page.wait_for_timeout(500);shot('hd-landscape')
        hd=page.evaluate('window.homm3HDState');r=page.locator('#canvas').bounding_box();assert abs(r['width']/r['height']-hd['width']/hd['height'])<0.01
        page.set_viewport_size({'width':390,'height':844});page.wait_for_function('window.homm3HDState.height>1200');shot('hd-portrait')
        page.set_viewport_size({'width':844,'height':390});page.wait_for_function('window.homm3HDState.height===600');shot('hd-restored')
        def hdpoint(x,y,modal=False):
            hd=page.evaluate('window.homm3HDState');r=page.locator('#canvas').bounding_box()
            if modal:x+=(hd['width']-800)/2;y+=(hd['height']-600)/2
            return r['x']+x*r['width']/hd['width'],r['y']+y*r['height']/hd['height']
        width=page.evaluate('window.homm3HDState.width')
        for _ in range(2):page.touchscreen.tap(*hdpoint(width-160,228));page.wait_for_timeout(160)
        page.wait_for_function('!window.homm3HDState.adventure');page.wait_for_timeout(300)
        total=page.evaluate('window.homm3Army.reduce((n,s)=>n+s.count,0)')
        control('[data-army-action="2"]');page.touchscreen.tap(*hdpoint(107,524,True))
        page.wait_for_function('window.homm3Army.filter(s=>s.count>0).length===7');shot('touch-singles')
        assert page.evaluate('window.homm3Army.reduce((n,s)=>n+s.count,0)')==total
        control('[data-army-action="2"]');assert page.evaluate('window.homm3ArmyAction')==0
        control('[data-game-key="Escape"]');page.wait_for_function('window.homm3HDState.adventure')
        page.locator('#open-tavern').tap();assert page.locator('#tavern').is_visible();page.locator('#close-tavern').tap()
        control('#fullscreen');assert page.evaluate('window.homm3Viewport.immersive');assert page.evaluate('document.documentElement.scrollHeight<=innerHeight')
        assert not errors,errors
        (OUT/(engine+'.json')).write_text(json.dumps({'passed':True,'checks':['fullscreen fallback','original menus stay 800x600','HD adventure follows screen aspect ratio','no zoom controls or pinch zoom','touch menu navigation','in-game Enter','touch single-unit army split','tavern sidebar','fullscreen retains viewport'],'touchHoldAndCancel':engine=='chromium','errors':errors},indent=2))
    finally:
        shot('last');browser.close()
