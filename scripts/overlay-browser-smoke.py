"""Real window lifetimes: quick view, map dialog, town and nested recruitment."""
from pathlib import Path
from io import BytesIO
import json, os
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/overlays';OUT.mkdir(exist_ok=True)
engine=os.getenv('BROWSER','chromium')
with sync_playwright() as p:
    browser=getattr(p,engine).launch(headless=True)
    page=browser.new_page(viewport={'width':1600,'height':800});c=page.locator('#canvas')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)));checks=[]
    def state():return page.evaluate('window.homm3HDState')
    def layers(n):page.wait_for_function('(n)=>window.homm3HDState?.layers===n',arg=n)
    def point(x,y):
        s=state();r=c.bounding_box();return r['x']+x*r['width']/s['width'],r['y']+y*r['height']/s['height']
    def idle():page.mouse.move(1,1);page.wait_for_timeout(200)
    def shot(name):
        idle();data=c.screenshot();(OUT/f'{engine}-{name}.png').write_bytes(data)
        return Image.open(BytesIO(data)).convert('RGB')
    def stable_margin(name):
        a=shot(name);page.wait_for_timeout(400);b=shot(name+'-idle');s=state()
        dx=(s['width']-800)/2*a.width/s['width'];dy=(s['height']-600)/2*a.height/s['height']
        rects=[(0,0,int(dx)-2,a.height),(int(a.width-dx)+2,0,a.width,a.height)] if dx else [(0,0,a.width,int(dy)-2),(0,int(a.height-dy)+2,a.width,a.height)]
        for rect in rects:
            assert ImageChops.difference(a.crop(rect),b.crop(rect)).getbbox() is None,(name,'map margin changed')
        checks.append(name+': surrounding map pixels stable')
    try:
        page.goto('http://127.0.0.1:8783/port/game.html');page.locator('#start').click(timeout=60000)
        page.wait_for_function('window.homm3PortDiagnostics?.screen==="main"',timeout=90000)
        c.press('n');page.wait_for_function('window.homm3PortDiagnostics.screen==="new"');c.press('s');page.wait_for_function('window.homm3PortDiagnostics.screen==="scenarios"')
        c.press('b');page.wait_for_timeout(4000);c.press('Enter');page.wait_for_function('window.homm3HDState?.adventure && window.homm3HDState.width===1200',timeout=60000)
        for orientation,viewport,w,h in [('wide',{'width':1600,'height':800},1200,600),('portrait',{'width':800,'height':1200},800,1200)]:
            page.set_viewport_size(viewport);page.wait_for_function('([w,h])=>window.homm3HDState.width===w && window.homm3HDState.height===h',arg=[w,h]);idle()
            page.evaluate('''()=>{window.overlayFrames=[];window.recordOverlays=true;function sample(){if(!window.recordOverlays)return;overlayFrames.push([Module.canvas.width,Module.canvas.height,window.homm3HDState.layers]);requestAnimationFrame(sample)}sample()}''')
            shot(orientation+'-map')
            for repeat in range(2):
                page.mouse.move(*point(w-160,228));page.mouse.down(button='right');layers(1)
                stable_margin(f'{orientation}-quickview-{repeat}')
                page.mouse.up(button='right');layers(0)
                c.press('Escape');layers(1);stable_margin(f'{orientation}-confirmation-{repeat}');c.press('Escape');layers(0)
                page.mouse.dblclick(*point(w-30,228),delay=140);layers(1);stable_margin(f'{orientation}-town-{repeat}')
                c.press('r');layers(2);stable_margin(f'{orientation}-recruit-{repeat}')
                c.press('Escape');layers(1);c.press('Escape');layers(0)
                assert state()['overlayX']==0 and state()['overlayY']==0
            frames=page.evaluate('()=>{recordOverlays=false;return overlayFrames}')
            assert frames and all(f[:2]==[w,h] for f in frames),(orientation,'canvas resized during overlay')
            assert {0,1,2}<=set(f[2] for f in frames)
            checks.append(f'{orientation}: {len(frames)} frames with constant {w}x{h} canvas')
            shot(orientation+'-returned')
        assert not errors,errors
        (OUT/f'{engine}.json').write_text(json.dumps({'passed':True,'checks':checks,'errors':errors},indent=2));print(json.dumps(checks),flush=True)
    finally:
        c.screenshot(path=str(OUT/f'{engine}-last.png'));print(state(),flush=True);browser.close()
