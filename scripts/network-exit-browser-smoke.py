"""Silent real-authority checks: refresh resumes; explicit exit does not.
Run against an isolated service with game resources, never a populated server.
"""
from pathlib import Path
import json, os, re, time
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SITE_URL', 'http://127.0.0.1:8783')
ENGINE = os.environ.get('BROWSER', 'chromium')
OUT = ROOT / 'test-results/network-exit' / ENGINE
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
    a.locator('#show-create').click();a.locator('#player-name').fill('Exit host');a.locator('#identity-submit').click()
    a.locator('#room-name').fill('Exit regression ' + str(time.time_ns()));a.locator('#visibility').select_option('private');a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
    a.wait_for_function('window.homm3Room?.players.length===1')
    b.goto(a.locator('#invite-link').input_value());b.locator('#join-invite').click();b.locator('#player-name').fill('Exit guest');b.locator('#identity-submit').click()
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
    identity = a.evaluate('localStorage.getItem("homm3.session")')
    def restored():
        a.wait_for_function('(id)=>window.homm3Room?.id===id && window.homm3Boot.running && window.homm3Authority?.revision>=1',arg=room,timeout=90000)
    def lobby():
        a.goto(BASE+'/port/game.html#multiplayer')
        a.locator('[data-resume-room="'+room+'"]').wait_for(state='visible',timeout=30000)
        a.wait_for_function('!window.homm3Room && !window.homm3Boot.running && !document.querySelector("#show-create").disabled')
        assert a.evaluate('localStorage.getItem("homm3.session")') == identity
    def resume():
        a.locator('[data-resume-room="'+room+'"]').click();restored()
    def exit_home(drop=False):
        a.locator('#view-toggle').click();a.locator('#view-exit').click()
        assert 'Мои партии' in a.locator('#exit-description').inner_text()
        if drop:a.evaluate('window.dropLeaveForTest=true')
        a.locator('#exit-confirm').click();a.wait_for_url(BASE+'/',timeout=10000)
        assert a.evaluate('localStorage.getItem("homm3.session")') == identity
    a.reload();restored();print('refresh restored',flush=True)
    a.locator('#view-toggle').click();a.locator('#view-exit').click();a.locator('#exit-cancel').click()
    assert a.evaluate('window.homm3Room.id') == room
    a.locator('#view-resume').click()
    exit_home();lobby();print('exit stays in lobby',flush=True);a.reload();a.locator('[data-resume-room="'+room+'"]').wait_for(state='visible')
    assert a.evaluate('!window.homm3Room && !window.homm3Boot.running')
    resume();a.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure"')
    exit_home(drop=True)
    assert a.evaluate('localStorage.getItem("homm3.leavePending")') == identity
    lobby();a.wait_for_function('!localStorage.getItem("homm3.leavePending")');resume();print('lost leave recovered',flush=True)
    a.wait_for_function('window.homm3PortDiagnostics?.screen==="adventure" && window.homm3HDState.layers===0')
    # Mobile layout updates the engine viewport after its first restored frame.
    a.wait_for_timeout(600)
    net=a.evaluate('window.homm3NetworkState');box=a.locator('#canvas').bounding_box();size=a.evaluate('window.homm3HDState')
    point={'x':box['width']*(8+32*(6-net['radarX'])+16)/size['width'],'y':box['height']*(8+32*(8-net['radarY'])+16)/size['height']}
    a.locator('#canvas').click(position=point);a.wait_for_timeout(200);a.locator('#canvas').click(position=point)
    for _ in range(80):
        if a.evaluate('window.homm3Authority?.combatRendererReady'):break
        if a.evaluate('window.homm3HDState.layers>0 && !window.homm3GameState.combat'):a.locator('#canvas').press('Enter')
        a.wait_for_timeout(250)
    a.wait_for_function('window.homm3Authority.combatRendererReady',timeout=30000)
    token=a.evaluate('window.homm3Authority.pendingChoice.token')
    exit_home();lobby();resume()
    a.wait_for_function('(t)=>window.homm3Authority.combatRendererReady && window.homm3Authority.pendingChoice?.token===t',arg=token,timeout=60000)
    exit_home();assert not errors,errors
    result={'passed':True,'browser':ENGINE,'refreshResumes':True,'cancelKeepsGame':True,'exitPreservesIdentity':True,'lobbyStaysAfterRefresh':True,'manualResume':True,'lostLeaveRecovered':True,'battleExitAndResume':True,'errors':errors}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    for c in contexts:c.close()
    browser.close()
