"""Startup regression in visible/background windows, both room modes and fatal exits."""
from pathlib import Path
import json, time, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'test-results'/'network-startup'/('-'.join(os.environ.get(key,default) for key,default in [('BROWSER','chromium'),('AUDIO_SINK','virtual'),('HD','0'),('HEADFUL','0'),('FAST','0'),('FAULT','0')]));OUT.mkdir(parents=True,exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
with sync_playwright() as p:
    browser=getattr(p,os.environ.get('BROWSER','chromium')).launch(headless=os.environ.get('HEADFUL')!='1',ignore_default_args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'] if os.environ.get('BROWSER','chromium')=='chromium' else [])
    credentials=json.loads(Path(os.environ['SITE_ACCESS_FILE']).read_text()) if os.environ.get('SITE_ACCESS_FILE') else None
    options={'http_credentials':{k:credentials[k] for k in ('username','password')}} if credentials else {}
    contexts=[browser.new_context(viewport={'width':1360,'height':1000},**options) for _ in range(2)]
    for context in contexts: use_silent_audio(context,device_sink=os.environ.get('AUDIO_SINK')=='device')
    pages=[c.new_page() for c in contexts];logs=[[],[]];errors=[[],[]]
    for i,page in enumerate(pages):
        page.on('console',lambda m,i=i:logs[i].append(m.text))
        page.on('pageerror',lambda e,i=i:(errors[i].append(e.stack),print('ERROR',i,e.stack,flush=True)))
    def dump(step):
        result=[]
        for i,page in enumerate(pages):
            page.screenshot(path=str(OUT/f'{step}-{i}.png'),full_page=True)
            result.append(page.evaluate('({room:{title:window.homm3Room?.title,phase:window.homm3Room?.phase},state:window.homm3GameState,net:window.homm3NetworkState,heroes:window.homm3HeroStates,screen:window.homm3PortDiagnostics?.screen,queue:window.homm3Network.peek(),status:document.querySelector("#status").textContent})'))
        (OUT/f'{step}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(step,[{'player':c['state'].get('localPlayer'),'day':c['state'].get('day'),'hero':c['state'].get('hero'),'xy':[c['state'].get('x'),c['state'].get('y')]} if c.get('state') else c['screen'] for c in result],flush=True)
    try:
        a,b=pages
        for i,page in enumerate(pages):
            page.goto(BASE+'/port/game.html'+('' if os.environ.get('HD')=='1' else '?hd=0')+'#multiplayer')
            page.wait_for_function('!document.querySelector("#start").disabled',timeout=60000)

        title='Browser integration '+str(time.time_ns());a.locator('#show-create').click();a.locator('#player-name').fill('Host');a.locator('#identity-submit').click();a.locator('#room-name').fill(title);a.locator('#capacity').select_option('2');
        if os.environ.get('FAST')=='1': a.locator('#fast-game').check()
        a.locator('#create-submit').click()
        a.wait_for_function('window.homm3Room?.players.length === 1')
        b.locator('#refresh-rooms').click();b.get_by_role('button',name='Войти: '+title,exact=True).click();b.locator('#player-name').fill('Guest');b.locator('#identity-submit').click()
        a.wait_for_function('window.homm3Room?.players.length === 2')
        b.locator('#room-chat').click();b.locator('#chat-input').fill('Привет! <b>Проверяем чат</b>');b.locator('#chat-send').click()
        a.wait_for_function('document.querySelector("#chat-log").textContent.includes("Привет!")')
        b.locator('#chat-back').click();a.locator('#ready').click();b.locator('#ready').click()
        a.wait_for_function('window.homm3Room?.players.every(p=>p.ready)',timeout=120000)
        dump('lobby-ready')
        a.locator('#launch-room').click()
        for page in pages: page.wait_for_function('window.homm3PortDiagnostics?.screen === "scenarios"',timeout=60000)
        a.wait_for_timeout(int(os.environ.get('SETUP_DELAY','5000')));dump('scenarios')
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        if os.environ.get('FAULT')=='1':
            # Exercise the actual native-error event path, then relay disconnect
            # propagation. This is test input, not a production debug hook.
            b.evaluate("window.dispatchEvent(new CustomEvent('homm3-engine-error',{detail:'Truncated campaign text <b>test</b>'}))")
            for page in pages:
                page.wait_for_function('!!window.homm3EngineError')
                assert page.locator('#launch-cover').is_visible()
                assert page.get_by_role('button',name='Перезагрузить страницу',exact=True).is_visible()
                assert page.locator('#status b').count()==0
            a.wait_for_timeout(4000)
            assert all(page.evaluate('!window.homm3Network.connected && !sessionStorage.getItem("homm3.session")') for page in pages)
            dump('fatal-visible-on-both')
            for page in pages:
                page.get_by_role('button',name='Перезагрузить страницу',exact=True).click()
                page.wait_for_function('!document.querySelector("#start").disabled')
                assert page.locator('#room-browser').is_visible()
                assert page.evaluate('!window.homm3Room && !window.homm3EngineError')
            dump('fresh-room-browser')
        else:
            box=a.locator('#canvas').bounding_box();size=a.evaluate('window.homm3HDState||{width:800,height:600}')
            a.locator('#canvas').click(position={'x':box['width']*((size['width']-800)/2+495)/size['width'],'y':box['height']*((size['height']-600)/2+555)/size['height']})
            for page in pages:
                page.wait_for_function('()=>{if(window.homm3EngineError)throw Error(window.homm3EngineError);return window.homm3GameState?.day===1;}',timeout=30000)
            for _ in range(12):
                if all(page.evaluate('window.homm3PortDiagnostics?.screen==="adventure"') for page in pages):break
                for page in pages:page.locator('#canvas').press('Enter')
                a.wait_for_timeout(1000)
            for page in pages:page.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure"',timeout=15000)
            assert [page.evaluate('window.homm3GameState.localPlayer') for page in pages]==[0,1]
            assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
            dump('adventure')
        assert not any(errors), errors
        assert not any('Game startup:' in line for lines in logs for line in lines), logs
        (OUT/'results.json').write_text(json.dumps({'passed':True,'browser':os.environ.get('BROWSER','chromium'),'headed':os.environ.get('HEADFUL')=='1','fast':os.environ.get('FAST')=='1','fault':os.environ.get('FAULT')=='1','hd':os.environ.get('HD')=='1','errors':errors},indent=2))
        print('PASS',flush=True)
    finally:
        try:dump('final')
        except:pass
        (OUT/'console.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2));(OUT/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2));browser.close()
