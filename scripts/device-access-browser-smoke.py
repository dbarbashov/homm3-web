"""Silent real-authority checks: one-time device transfer and native resume.
Run against an isolated service with game resources, never a populated server.
"""
from pathlib import Path
import json, os, re, time
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SITE_URL', 'http://127.0.0.1:8783')
ENGINE = os.environ.get('BROWSER', 'chromium')
OUT = ROOT / 'test-results/device-access' / ENGINE
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
    a.locator('#show-create').click();a.locator('#player-name').fill('Device host');a.locator('#identity-submit').click()
    a.locator('#room-name').fill('Device access ' + str(time.time_ns()));a.locator('#visibility').select_option('private');a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
    a.wait_for_function('window.homm3Room?.players.length===1')
    b.goto(a.locator('#invite-link').input_value());b.locator('#join-invite').click();b.locator('#player-name').fill('Device guest');b.locator('#identity-submit').click()
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
    # Exit preserves membership but does not auto-return to the match.
    a.evaluate('window.homm3Lobby.leaveToHome()');a.wait_for_url(BASE+'/')
    a.goto(BASE+'/port/game.html#multiplayer');a.locator('[data-resume-room="'+room+'"]').wait_for()
    a.locator('#device-access summary').click();a.locator('#device-create').click()
    a.locator('#device-issued').wait_for();code=a.locator('#device-code').input_value()
    third=browser.new_context(viewport={'width':852,'height':393},is_mobile=True,has_touch=True);contexts.append(third);use_silent_audio(third)
    c=third.new_page();c.on('pageerror',lambda error:errors.append(str(error)))
    c.goto(BASE+'/port/game.html#multiplayer');c.locator('#device-access summary').click()
    c.locator('#device-input').fill(code);c.locator('#device-submit').click()
    c.locator('[data-resume-room="'+room+'"]').wait_for(timeout=30000)
    new=c.evaluate('localStorage.getItem("homm3.session")');assert new and new!=identity
    a.wait_for_function('document.querySelector("#tavern-error").textContent.includes("другом устройстве")')
    a.wait_for_timeout(3500);assert a.evaluate('document.querySelector("#connection").dataset.online')=='false'
    c.locator('[data-resume-room="'+room+'"]').click()
    c.wait_for_function('window.homm3Authority?.revision>=1 && window.homm3Boot.running',timeout=90000)
    c.evaluate('window.homm3Lobby.leaveToHome()');c.wait_for_url(BASE+'/');c.goto(BASE+'/port/game.html#multiplayer')
    c.locator('[data-resume-room="'+room+'"]').wait_for();c.locator('#device-access summary').click()
    c.locator('#device-revoke').click();c.wait_for_function('document.querySelector("#device-status").textContent.includes("отозваны")')
    # Redeeming the same code again cannot overwrite the current identity.
    c.locator('#device-input').fill(code);c.locator('#device-submit').click()
    c.wait_for_function('document.querySelector("#device-status").textContent.includes("недействителен")')
    assert c.evaluate('localStorage.getItem("homm3.session")')==new
    c.reload();c.locator('[data-resume-room="'+room+'"]').wait_for()
    with c.expect_popup() as popup:
        c.locator('[data-review-room="'+room+'"]').click()
    review=popup.value
    review.wait_for_function('document.querySelector("#replay-status")?.textContent.includes("Проверено")',timeout=90000)
    review.frames[1].wait_for_function('window.homm3Authority?.revision>=1',timeout=60000)
    assert review.frames[1].evaluate('!window.homm3Room')
    review.close()
    assert not errors,errors
    result={'passed':True,'browser':ENGINE,'independentStorage':True,'oldTabStopsReconnect':True,'sameSavedGame':True,'resumesNativeGame':True,'oneUse':True,'revoke':True,'savedGameReview':True,'errors':errors}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    for context in contexts:context.close()
    browser.close()
