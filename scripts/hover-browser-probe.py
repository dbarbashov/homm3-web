"""Measure real menu hover and combat toolbar pixels after mouse-event bursts.

RUN names the output. BEFORE_BUILD optionally supplies an older game.js/WASM
pair for a matched baseline. Synthetic MouseEvents enter the normal SDL path;
latencies describe this controlled burst fixture, not every user's hardware.
"""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/hover' / os.getenv('RUN', 'current')
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = getattr(p, os.getenv('BROWSER', 'chromium')).launch(headless=True)
    page = browser.new_page(viewport={'width': 1200, 'height': 900})
    use_silent_audio(page)
    page.add_init_script("""
        window.hoverLabel = null;
        for(const type of [WebGLRenderingContext, WebGL2RenderingContext]){
            for(const method of ['drawElements','drawArrays']){
                const original=type.prototype[method];
                type.prototype[method]=function(...args){
                    const result=original.apply(this,args);
                    if(window.measureCombatHover && this.canvas===document.getElementById('canvas')){
                        const bytes=new Uint8Array(390*50*4);
                        this.readPixels(220,0,390,50,this.RGBA,this.UNSIGNED_BYTE,bytes);
                        let hash=2166136261;
                        for(const value of bytes)hash=Math.imul(hash^value,16777619);
                        window.hoverLabel=hash>>>0;window.hoverGLInfo={width:this.drawingBufferWidth,height:this.drawingBufferHeight,viewport:Array.from(this.getParameter(this.VIEWPORT)),sample:Array.from(bytes.slice(0,12))};
                    }
                    return result;
                };
            }
        }
    """)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    if os.getenv('BEFORE_BUILD'):
        before = ROOT / os.environ['BEFORE_BUILD']
        for name in ['game.js', 'game.wasm']:
            page.route('**/port/' + name, lambda route, request, name=name: route.fulfill(path=before / name))
    canvas = page.locator('#canvas')

    def screen(name):
        page.wait_for_function('(name) => window.homm3PortDiagnostics?.screen === name', arg=name, timeout=90000)

    def move(x, y):
        box = canvas.bounding_box()
        page.mouse.move(box['x'] + x * box['width'] / 800, box['y'] + y * box['height'] / 600)

    def measure(mode):
        result = page.evaluate('''async mode => {
            const canvas=Module.canvas, box=canvas.getBoundingClientRect();
            const sleep=t=>new Promise(resolve=>setTimeout(resolve,t));
            const frame=()=>new Promise(requestAnimationFrame);
            function move(x,y){canvas.dispatchEvent(new MouseEvent('mousemove',{
                bubbles:true,view:window,clientX:box.x+x*box.width/800,clientY:box.y+y*box.height/600
            }));}
            function label(){return window.hoverLabel;}
            window.measureCombatHover=mode==='combat';
            let expected;
            if(mode==='combat'){
                move(178,580);await sleep(1000);await frame();expected=label();
                move(20,580);await sleep(1000);await frame();
                if(expected===null || label()===expected)throw new Error('combat reference labels must differ: '+expected+'/'+label()+'/'+JSON.stringify(window.hoverGLInfo));
            }
            const cases=[];
            for(const n of [1,32,60]){
                if(mode==='menu')move(650,65);else move(20,580);
                await sleep(1000);
                if(mode==='combat' && label()===expected)throw new Error('starting label did not reset');
                for(let i=0;i<n;++i){
                    if(mode==='menu')move(650,30+i*70/n);else move(10+i*20/n,580);
                }
                if(mode==='menu')move(650,185);else move(178,580);
                const sent=performance.now();let matched=false;
                do {
                    await frame();
                    matched=mode==='menu'?homm3PortDiagnostics.hovered===102:label()===expected;
                } while(!matched && performance.now()-sent<3000);
                cases.push({events:n+1,latencyMs:performance.now()-sent,matched});
            }
            return cases;
        }''', mode)
        print(mode, json.dumps(result), flush=True)
        canvas.screenshot(path=str(OUT / (mode + '.png')))
        return result

    try:
        page.goto('http://127.0.0.1:8783/port/game.html?hd=0')
        page.locator('#start').click(); screen('main')
        menu = measure('menu')
        # Original nested button loop: dragging outside cancels the click.
        move(650,65); page.mouse.down(); page.wait_for_timeout(80)
        move(400,70); page.mouse.up(); page.wait_for_timeout(200); screen('main')
        # Trusted click still launches the selected item after fast pointer input.
        move(650,65); page.mouse.down(); page.mouse.up(); screen('new')
        canvas.press('s'); screen('scenarios')
        canvas.press('b'); page.wait_for_timeout(4000); canvas.press('Enter'); screen('adventure')
        canvas.press('ArrowDown'); page.wait_for_function('homm3GameState.y===6 && !homm3GameState.moving')
        canvas.press('ArrowDown'); page.wait_for_function('homm3GameState.y===7 && !homm3GameState.moving')
        canvas.press('End'); screen('combat'); page.wait_for_timeout(7500)
        combat = measure('combat')
        result = {'menu': menu, 'combat': combat, 'dragCancel': True, 'click': True, 'errors': errors}
        (OUT / 'results.json').write_text(json.dumps(result, indent=2))
        assert not errors, errors
        assert all(case['matched'] for case in menu + combat)
        if not os.getenv('BEFORE_BUILD'):
            assert max(case['latencyMs'] for case in menu + combat) < 120, result
    finally:
        canvas.screenshot(path=str(OUT / 'last.png'))
        browser.close()
