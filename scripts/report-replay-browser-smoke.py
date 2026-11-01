"""Silent immutable report checks: native adventure, battle, timeline and source isolation.
Run against an isolated service with game resources, never a populated server.
"""
from pathlib import Path
import json, os, re, time, tempfile
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SITE_URL', 'http://127.0.0.1:8783')
ENGINE = os.environ.get('BROWSER', 'chromium')
OUT = ROOT / 'test-results/report-replay' / ENGINE
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = getattr(p, ENGINE).launch(headless=True)
    contexts = [browser.new_context(viewport={'width': 852, 'height': 393}, is_mobile=True, has_touch=True) for _ in range(2)]
    errors = []
    for context in contexts:
        use_silent_audio(context)
        context.on("page",lambda page:page.on("pageerror",lambda error:errors.append(str(error))))
        context.add_init_script('''(() => {
          const Original = WebSocket;
          window.WebSocket = new Proxy(Original, {construct(Target, args) {
            const ws = new Target(...args), send = ws.send.bind(ws);
            ws.send = data => {
              if(typeof data==='string'){const p=JSON.parse(data);if(p.type.startsWith('authority_'))(window.testAuthorityInputs||=[]).push(p);}
              if (window.dropLeaveForTest && typeof data === 'string' && JSON.parse(data).type === 'leave') return;
              return send(data);
            };
            ws.addEventListener('message', event => {
              if(typeof event.data !== 'string')return;
              const message=JSON.parse(event.data);
              if(message.type==='authority_choice')window.testChoiceText=message.text||'';
            });
            return ws;
          }});
        })();''')
    a, b = [c.new_page() for c in contexts]
    for page in [a, b]:
        page.goto(BASE + '/port/game.html?hd=0#multiplayer')
        page.wait_for_function('!document.querySelector("#start").disabled', timeout=60000)
    a.locator('#show-create').click();a.locator('#player-name').fill('Replay host');a.locator('#identity-submit').click()
    a.locator('#room-name').fill('Replay check ' + str(time.time_ns()));a.locator('#visibility').select_option('private');a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
    a.wait_for_function('window.homm3Room?.players.length===1')
    b.goto(a.locator('#invite-link').input_value());b.locator('#join-invite').click();b.locator('#player-name').fill('Replay guest');b.locator('#identity-submit').click()
    a.wait_for_function('window.homm3Room?.players.length===2')
    room = a.evaluate('window.homm3Room.id')
    for page in [a, b]:page.locator('#ready').click()
    a.wait_for_function('!document.querySelector("#launch-room").disabled', timeout=90000)
    a.locator('#launch-room').click();a.wait_for_function('window.homm3PortDiagnostics?.screen==="scenarios"', timeout=60000)
    a.wait_for_timeout(3000)
    box = a.locator('#canvas').bounding_box()
    a.locator('#canvas').click(position={'x':box['width']*495/800,'y':box['height']*555/600})
    for _ in range(40):
        if all(page.evaluate('window.homm3PortDiagnostics?.screen==="adventure" && window.homm3Authority?.revision>=1 && window.homm3HDState?.layers===0') for page in [a,b]):break
        for page in [a,b]:
            if page.evaluate('window.homm3HDState?.layers>0 && (!window.homm3Authority?.pendingChoice || window.homm3Authority.pendingChoice.kind==="normal")'):page.locator('#canvas').press('Enter')
        a.wait_for_timeout(250)
    a.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure" && window.homm3Authority?.revision>=1')
    report=a.evaluate('window.homm3Lobby.captureReport()')
    viewer=contexts[0].new_page()
    viewer.on('response',lambda response:print('replay response', {key:response.json().get(key) for key in ['verified','error','cursor','positions','revision']},flush=True) if '/replay' in response.url and '/lobby/reports/' in response.url else None)
    local_replay=os.environ.get('HOMM3_TEST_LOCAL_REPLAY')=='1'
    if local_replay:
        viewer.route('**/api/catalog',lambda route:route.fulfill(json={'ready':False,'error':'Выберите папку своей игры'}))
        viewer.route('**/site/resources.json',lambda route:route.fulfill(status=404,body=''))
    viewer.on('console',lambda message:print('viewer console:',message.type,message.text[:300],flush=True) if message.type=='error' else None)
    viewer.on('pageerror',lambda error:print('viewer error:',str(error),flush=True))
    viewer.goto(BASE+report)
    if local_replay:
        viewer.wait_for_function('!document.querySelector("#replay-files").disabled && document.querySelector("#replay-status").textContent.includes("папку")',timeout=90000)
        with tempfile.TemporaryDirectory(prefix='homm3-replay-assets-') as folder:
            source=ROOT/'.local/runtime'
            for name in ['h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod','heroes3.snd']:
                os.link((source/'data'/name).resolve(),Path(folder)/name)
            os.link((source/'maps/Arrogance.h3m').resolve(),Path(folder)/'Arrogance.h3m')
            viewer.locator('#replay-files').set_input_files(folder)
            viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено")',timeout=90000)
            viewer.locator('#replay-position').fill('0');viewer.locator('#replay-position').dispatch_event('change')
            try:viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено") && document.querySelector("#replay-position").value==="0"',timeout=90000)
            except Exception:
                print('local seek failed',viewer.locator('#replay-status').text_content(),[f.evaluate('({error:window.homm3EngineError,ready:window.homm3Boot?.ready,running:window.homm3Boot?.running,status:document.querySelector("#status")?.textContent})') for f in viewer.frames],flush=True);raise
            viewer.frames[1].wait_for_function('window.homm3Authority?.revision===0 && (window.homm3PortDiagnostics?.screen==="adventure" || window.homm3HDState?.layers>0)',timeout=60000)
            viewer.locator('#replay-position').fill(viewer.locator('#replay-position').get_attribute('max'));viewer.locator('#replay-position').dispatch_event('change')
            viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено") && document.querySelector("#replay-position").value===document.querySelector("#replay-position").max',timeout=90000)
    viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено")',timeout=90000)
    frame=viewer.frames[1];frame.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure"',timeout=60000)
    assert frame.evaluate('!window.homm3Room')
    assert frame.evaluate('window.homm3Authority.revision')==a.evaluate('window.homm3Authority.revision')
    print('native adventure replay restored',flush=True)
    viewer.close()
    a.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure" && window.homm3HDState.layers===0')
    # Mobile layout updates the engine viewport after its first restored frame.
    a.wait_for_timeout(600)
    net=a.evaluate('window.homm3NetworkState');box=a.locator('#canvas').bounding_box();size=a.evaluate('window.homm3HDState')
    point={'x':box['width']*(8+32*(5-net['radarX'])+16)/size['width'],'y':box['height']*(8+32*(8-net['radarY'])+16)/size['height']}
    a.locator('#canvas').click(position=point);a.wait_for_timeout(200);a.locator('#canvas').click(position=point)
    for _ in range(80):
        if a.evaluate('window.homm3Authority?.combatRendererReady'):break
        if a.evaluate('window.homm3HDState.layers>0 && !window.homm3GameState.combat'):
            text=a.evaluate("new TextDecoder('windows-1251').decode(Uint8Array.from(window.testChoiceText||'',c=>c.charCodeAt(0)))")
            a.locator('#canvas').press('Escape' if 'присоедин' in text.lower() else 'Enter')
        a.wait_for_timeout(250)
    try:a.wait_for_function('window.homm3Authority.combatRendererReady',timeout=30000)
    except Exception:
        print('combat did not open',a.evaluate('({game:window.homm3GameState,status:window.homm3AuthorityStatus,choice:window.homm3Authority.pendingChoice,revision:window.homm3Authority.revision})'),flush=True);raise
    # Opening readiness may precede a faster enemy's automatic turn. Capture
    # a settled human decision, not an already-consumed opening token.
    a.wait_for_function('window.homm3Authority.combatCanAct()',timeout=60000)
    token=a.evaluate('window.homm3Authority.pendingChoice.token')
    restart_file=os.environ.get('HOMM3_TEST_RESTART_FILE')
    if restart_file:
        signal=Path(restart_file);signal.write_text('restart')
        for _ in range(300):
            if signal.read_text()=='ready':break
            a.wait_for_timeout(100)
        assert signal.read_text()=='ready'
        a.reload()
        a.wait_for_function('(token)=>window.homm3Authority?.combatRendererReady && window.homm3Authority.pendingChoice?.token===token',arg=token,timeout=90000)
        print('service restart restored current native battle',flush=True)
    a.wait_for_timeout(10000)
    report=a.evaluate('window.homm3Lobby.captureReport()')
    original_revision=a.evaluate('window.homm3Authority.revision')
    viewer=contexts[0].new_page()
    viewer.on('response',lambda response:print('replay response', {key:response.json().get(key) for key in ['verified','error','cursor','positions','revision']},flush=True) if '/replay' in response.url and '/lobby/reports/' in response.url else None)
    viewer.goto(BASE+report)
    viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено")',timeout=90000)
    frame=viewer.frames[1];frame.wait_for_function('(token)=>window.homm3Authority?.combatRendererReady && window.homm3Authority.pendingChoice?.token===token',arg=token,timeout=60000)
    assert frame.evaluate('!window.homm3Room')
    assert int(viewer.locator('#replay-position').get_attribute('max'))>0
    viewer.locator('#replay-position').fill('0');viewer.locator('#replay-position').dispatch_event('change')
    viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено") && document.querySelector("#replay-position").value==="0"',timeout=90000)
    viewer.frames[1].wait_for_function('window.homm3Authority?.revision>=0 && (window.homm3PortDiagnostics?.screen==="adventure" || window.homm3HDState?.layers>0)',timeout=60000)
    assert a.evaluate('window.homm3Authority.revision')==original_revision
    assert a.evaluate('window.homm3Authority.pendingChoice.token')==token
    # Branch from the current manual battle, not just a fresh adventure turn.
    viewer.locator('#replay-position').fill(viewer.locator('#replay-position').get_attribute('max'))
    viewer.locator('#replay-position').dispatch_event('change')
    viewer.wait_for_function('document.querySelector("#replay-status").textContent.includes("Проверено") && !document.querySelector("#replay-branch").disabled',timeout=90000)
    assert not viewer.locator('#replay-files').is_visible()
    assert viewer.locator('.replay-controls').bounding_box()['height']<=70
    viewer.screenshot(path=str(OUT/'replay-battle-mobile.png'))
    viewer.locator('#replay-branch').click()
    viewer.wait_for_url('**/port/game.html#*',timeout=90000)
    viewer.wait_for_function('(token)=>window.homm3Room?.training && window.homm3Authority?.combatRendererReady && window.homm3Authority.pendingChoice?.token===token',arg=token,timeout=90000)
    viewer.wait_for_function('window.homm3Authority.combatCanAct()',timeout=60000)
    viewer.wait_for_function('window.homm3HDState.width===document.querySelector("#canvas").width && window.homm3HDState.height===document.querySelector("#canvas").height')
    # A saved battle may still be in Tactics: the original placement bar has
    # an End Placement button instead of the ordinary Defend button.
    tactics_restored=viewer.evaluate('window.homm3Authority.combatTactics')
    if tactics_restored:
        box=viewer.locator('#canvas').bounding_box();size=viewer.evaluate('window.homm3HDState')
        viewer.locator('#canvas').click(position={'x':box['width']*(size['overlayX']+518)/size['width'],'y':box['height']*(size['overlayY']+575)/size['height']})
        viewer.wait_for_function('!window.homm3Authority.combatTactics && window.homm3Authority.combatCanAct()',timeout=30000)
        assert viewer.evaluate('window.homm3Authority.pendingChoice.token')>token
        token=viewer.evaluate('window.homm3Authority.pendingChoice.token')
    box=viewer.locator('#canvas').bounding_box();size=viewer.evaluate('window.homm3HDState')
    viewer.locator('#canvas').click(position={'x':box['width']*(size['overlayX']+770)/size['width'],'y':box['height']*(size['overlayY']+575)/size['height']})
    try:viewer.wait_for_function('(token)=>window.homm3Authority.pendingChoice?.token>token || window.homm3Authority.revision>'+str(original_revision),arg=token,timeout=15000)
    except Exception:
        print('branch defend failed',{'box':box,'size':size,'state':viewer.evaluate('({hd:window.homm3HDState,wanted:window.homm3HDSize,tactics:window.homm3Authority.combatTactics,inputs:window.testAuthorityInputs,authority:window.homm3Authority.diagnostics(),game:window.homm3GameState,error:window.homm3EngineError})')},flush=True);raise
    assert b.evaluate('window.homm3Authority.revision')==original_revision
    assert viewer.locator('#players small').all_text_contents().count('Компьютер')==1
    assert 'Нет связи' not in viewer.locator('#players').text_content()
    print('training branch restored manual battle and accepted native defend input',flush=True)
    result={'passed':True,'localFilesAndSeek':local_replay,'manualBattleBranch':True,'tacticsRestored':tactics_restored,'nativeAdventure':True,'nativeBattle':True,'latestBattleChoice':True,'seekEarlier':True,'sourceUnchanged':True,'noLobbyConnection':True,'serviceRestartRestoresBattle':bool(restart_file),'errors':errors}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    assert not errors,errors
    for context in contexts:context.close()
    browser.close()
