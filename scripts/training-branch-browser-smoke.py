"""Silent real-authority checks: immutable training branch and native AI opponents.
Run against an isolated service with game resources, never a populated server.
"""
from pathlib import Path
import json, os, re, time
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SITE_URL', 'http://127.0.0.1:8783')
ENGINE = os.environ.get('BROWSER', 'chromium')
OUT = ROOT / 'test-results/training-branch' / ENGINE
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = getattr(p, ENGINE).launch(headless=True)
    contexts = [browser.new_context(viewport={'width': 852, 'height': 393}, is_mobile=True, has_touch=True) for _ in range(2)]
    errors = []
    for context in contexts:
        use_silent_audio(context)
        context.add_init_script('''(() => {
          const Original = WebSocket;
          window.WebSocket = new Proxy(Original, {construct(Target, args) {
            const ws = new Target(...args), send = ws.send.bind(ws);
            ws.send = data => {
              if (window.dropLeaveForTest && typeof data === 'string' && JSON.parse(data).type === 'leave') return;
              return send(data);
            };
            return ws;
          }});
        })();''')
    a, b = [c.new_page() for c in contexts]
    for page in [a, b]:
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/port/game.html?hd=0#multiplayer')
        page.wait_for_function('!document.querySelector("#start").disabled', timeout=60000)
    a.locator('#show-create').click();a.locator('#player-name').fill('Branch host');a.locator('#identity-submit').click()
    a.locator('#room-name').fill('Training check ' + str(time.time_ns()));a.locator('#visibility').select_option('private');a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
    a.wait_for_function('window.homm3Room?.players.length===1')
    b.goto(a.locator('#invite-link').input_value());b.locator('#join-invite').click();b.locator('#player-name').fill('Branch guest');b.locator('#identity-submit').click()
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
    source_room=room;source_revision=a.evaluate('window.homm3Authority.revision')
    report=a.evaluate('window.homm3Lobby.captureReport()')
    viewer=contexts[0].new_page();viewer.goto(BASE+report)
    viewer.wait_for_function('!document.querySelector("#replay-branch").disabled',timeout=90000)
    # An unrelated identity cannot turn somebody else's public report into a game.
    other=contexts[1].request.post(BASE+report+'/branch',headers={'Authorization':'Bearer '+b.evaluate('localStorage.getItem("homm3.session")')},data={'cursor':1})
    assert other.status==422
    viewer.locator('#replay-branch').click()
    viewer.wait_for_url('**/port/game.html#*',timeout=90000)
    viewer.wait_for_function('window.homm3Room?.training && window.homm3Authority?.revision>=1 && window.homm3PortDiagnostics?.screen==="adventure"',timeout=90000)
    assert viewer.evaluate('window.homm3Room.id')!=source_room
    revision=viewer.evaluate('window.homm3Authority.revision')
    assert b.evaluate('window.homm3Authority.revision')==revision
    viewer.locator('#canvas').press('e');viewer.wait_for_timeout(250);viewer.locator('#canvas').press('Enter')
    for _ in range(160):
        if viewer.evaluate('(r)=>window.homm3Authority.revision>r && window.homm3AuthorityStatus.activeActor===window.homm3Authority.actor',revision):break
        if viewer.evaluate('window.homm3HDState?.layers>0 && window.homm3Authority.pendingChoice?.kind!=="combat"'):viewer.locator('#canvas').press('Enter')
        viewer.wait_for_timeout(100)
    assert viewer.evaluate('(r)=>window.homm3Authority.revision>r && window.homm3AuthorityStatus.activeActor===window.homm3Authority.actor',revision)
    assert b.evaluate('window.homm3Authority.revision')==revision,'Source match changed'
    result={'passed':True,'distinctGame':True,'sourceUnchanged':True,'authenticatedOwnerOnly':True,'nativePlay':True,'aiOpponentsReturnTurn':True,'errors':errors}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    assert not errors,errors
    for context in contexts:context.close()
    browser.close()
