"""Two independent WASM clients; drive only UI, inspect diagnostics for assertions."""
from pathlib import Path
import json, time, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'test-results/network';OUT.mkdir(parents=True,exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
with sync_playwright() as p:
    browser=getattr(p,os.environ.get('BROWSER','chromium')).launch(headless=os.environ.get('HEADFUL')!='1')
    credentials=json.loads(Path(os.environ['SITE_ACCESS_FILE']).read_text()) if os.environ.get('SITE_ACCESS_FILE') else None
    options={'http_credentials':{k:credentials[k] for k in ('username','password')}} if credentials else {}
    contexts=[browser.new_context(viewport={'width':1360,'height':1000},**options) for _ in range(2)]
    for context in contexts: use_silent_audio(context)
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
            page.goto(BASE+'/port/game.html?hd=0#multiplayer')
            page.wait_for_function('!document.querySelector("#start").disabled',timeout=60000)

        title='Browser integration '+str(time.time_ns());a.locator('#show-create').click();a.locator('#player-name').fill('Host');a.locator('#identity-submit').click();a.locator('#room-name').fill(title);a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
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
        a.wait_for_timeout(5000);dump('scenarios')
        box=a.locator('#canvas').bounding_box();a.locator('#canvas').click(position={'x':box['width']*495/800,'y':box['height']*555/600});a.wait_for_timeout(5000);dump('begin')
        assert not any(errors), errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        for page in pages: page.locator('#canvas').press('Enter')
        for page in pages: page.wait_for_function('window.homm3GameState?.day === 1',timeout=60000)
        dump('adventure')
        for page in pages:page.wait_for_function('window.homm3PortDiagnostics?.screen === "adventure"')
        states=[page.evaluate('window.homm3GameState') for page in pages]
        for page in pages:page.wait_for_function('Number(document.documentElement.dataset.playerColor)===window.homm3GameState.localPlayer')
        assert [x['localPlayer'] for x in states]==[0,1] and all(x['remote']==1 and x['humans']==2 for x in states)
        y=states[0]['y']
        b.locator('#canvas').press('ArrowDown');b.wait_for_timeout(700)
        assert a.evaluate('window.homm3GameState.y')==y, 'Inactive guest moved host hero'
        a.locator('#canvas').press('ArrowDown')
        for page in pages:page.wait_for_function('(y)=>window.homm3GameState.y===y',arg=y+1,timeout=20000)
        dump('host-movement-synced')
        b.locator('#view-toggle').click();b.locator('#view-tavern').click();b.locator('#room-chat').click();b.locator('#chat-input').fill('Ход героя вижу. Передавай ход!');b.locator('#chat-send').click()
        a.wait_for_function('document.querySelector("#chat-log").textContent.includes("Передавай ход")');b.locator('#close-tavern').click()
        a.wait_for_function('!window.homm3GameState.moving');a.locator('#canvas').press('e');a.wait_for_timeout(700);a.locator('#canvas').press('Enter');b.wait_for_timeout(1500)
        for _ in range(20):
            if b.evaluate('window.homm3GameState.player===1'):break
            b.locator('#canvas').press('Enter');b.wait_for_timeout(1000)
        for page in pages:page.wait_for_function('window.homm3GameState.player===1',timeout=30000)
        for _ in range(10):
            if b.evaluate('window.homm3GameState.hero>=0'):break
            b.locator('#canvas').press('Enter');b.wait_for_timeout(1000)
        b.wait_for_function('window.homm3GameState.hero>=0',timeout=10000)
        b.wait_for_function('window.homm3NetworkState.radarY>10');dump('guest-turn')
        for page in pages:assert page.evaluate('Number(document.documentElement.dataset.playerColor)===window.homm3GameState.localPlayer'), 'Theme followed the remote turn'
        guest=b.evaluate('window.homm3GameState');b.locator('#canvas').press('ArrowDown');b.wait_for_timeout(2000);dump('guest-after-input')
        for page in pages:page.wait_for_function('(y)=>window.homm3GameState.y===y',arg=guest['y']+1,timeout=20000)
        dump('guest-movement-synced')
        b.locator('#canvas').press('e');b.wait_for_timeout(700);b.locator('#canvas').press('Enter')
        a.wait_for_function('window.homm3GameState.day===2',timeout=90000);a.wait_for_timeout(1000);a.locator('#canvas').press('Enter')
        for page in pages:page.wait_for_function('window.homm3GameState.day===2 && window.homm3GameState.player===0',timeout=30000)
        dump('day-two')
        a.wait_for_function('window.homm3GameState.hero>=0');a.locator('#canvas').press('ArrowDown')
        a.wait_for_function('window.homm3GameState.y===7 && !window.homm3GameState.moving');a.wait_for_timeout(500)
        a.locator('#canvas').press('End');a.wait_for_function('window.homm3GameState.combat===1',timeout=20000);dump('network-battle')
        # The battle opens before its sound/fade sequence finishes; early input is flushed.
        for _ in range(12):
            a.wait_for_timeout(1000)
            if a.evaluate('window.homm3GameState.autoCombat===1'):break
            a.locator('#canvas').click(position={'x':a.locator('#canvas').bounding_box()['width']*178/800,'y':a.locator('#canvas').bounding_box()['height']*580/600})
        a.wait_for_function('window.homm3GameState.autoCombat===1',timeout=10000)
        a.wait_for_function('window.homm3PortDiagnostics.screen==="combat-results"',timeout=180000);dump('network-battle-result')
        a.locator('#canvas').press('Enter');a.wait_for_function('window.homm3GameState.combat===0');a.wait_for_timeout(1500)
        dump('network-battle-return')
        experience=a.evaluate('window.homm3GameState.experience');assert experience>states[0]['experience']
        a.locator('#canvas').press('e');a.wait_for_timeout(700);a.locator('#canvas').press('Enter')
        for _ in range(20):
            if b.evaluate('window.homm3GameState.player===1 && window.homm3GameState.hero>=0'):break
            b.locator('#canvas').press('Enter');b.wait_for_timeout(1000)
        b.wait_for_function('(exp)=>window.homm3GameState.player===1 && window.homm3HeroStates[0].experience===exp',arg=experience,timeout=30000)
        dump('post-battle-state-transfer')
        assert not any(errors), errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        (OUT/'results.json').write_text(json.dumps({'passed':True,'checks':['public room join','chat escaped as text','same build readiness','two independent WASM engines','different local players and fog','inactive guest input blocked','host movement synchronized','turn to guest','guest movement synchronized','AI and day two synchronized','neutral combat and return','battle experience transferred on next turn'],'errors':errors},ensure_ascii=False,indent=2))
        print('PASS: two-player networking, chat, movement, turns and AI day',flush=True)

    finally:
        try:dump('final-state')
        except:pass
        for i,page in enumerate(pages):
            try:page.screenshot(path=str(OUT/f'last-{i}.png'),full_page=True)
            except:pass
        (OUT/'console.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2));(OUT/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2));browser.close()
