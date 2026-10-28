"""Real room UI, safe chat, independent scroll and mobile browser checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os, time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/site';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    credentials=json.loads(Path(os.environ['SITE_ACCESS_FILE']).read_text()) if os.environ.get('SITE_ACCESS_FILE') else None
    options={'http_credentials':{k:credentials[k] for k in ('username','password')}} if credentials else {}
    contexts=[browser.new_context(viewport={'width':1440,'height':900},**options) for _ in range(2)]
    a,b=[c.new_page() for c in contexts];errors=[]
    for page in [a,b]:page.on('pageerror',lambda e:errors.append(e.stack))
    a.goto(BASE+'/');assert a.locator('main a').count()==3;assert a.get_by_role('link',name='GitHub',exact=True).get_attribute('href')=='https://github.com/dbarbashov/homm3-web'
    a.screenshot(path=str(OUT/'landing.png'))
    title='Тест '+str(time.time_ns())
    a.goto(BASE+'/port/game.html#multiplayer');a.locator('#player-name').fill('Изабель');a.locator('#show-create').click();a.locator('#room-name').fill(title);a.locator('#visibility').select_option('private');a.locator('#create-submit').click();a.wait_for_function('window.homm3Room?.players.length===1')
    invite=a.locator('#invite-link').input_value();rid=a.evaluate('window.homm3Room.id');public=a.request.get(BASE+'/lobby/rooms').json();assert all(r['id']!=rid for r in public['rooms'])
    b.goto(invite);b.locator('#player-name').fill('Роланд');b.locator('#join-invite').click();a.wait_for_function('window.homm3Room?.players.length===2')
    b.locator('#chat-input').fill('<b>До встречи в Эрафии!</b>');b.locator('#chat-send').click();a.wait_for_function('document.querySelector("#chat-log").textContent.includes("До встречи")');assert a.locator('#chat-log b').count()==0;assert a.locator('#chat-empty').count()==0;assert a.locator('#chat-rows tr td').count()==3
    b.locator('#chat-input').fill('🙂'*301);assert len(b.locator('#chat-input').input_value())==300
    assert b.locator('#chat-count').inner_text()=='300/300'
    a.screenshot(path=str(OUT/'private-room.png'))
    a.locator('#leave-room').click();b.wait_for_function('window.homm3Room?.players.length===1');assert b.evaluate('window.homm3Room.players[0].id===window.homm3Room.host');b.locator('#leave-room').click()
    a.locator('#show-create').click();a.locator('#visibility').select_option('public');a.locator('#create-submit').click();a.wait_for_function('window.homm3Room?.private===false');b.locator('#refresh-rooms').click();b.locator('.room-card').filter(has_text=title).click();b.locator('#join-selected').click();a.wait_for_function('window.homm3Room?.players.length===2')
    for w,h in [(1440,900),(390,844),(844,390)]:
        a.set_viewport_size({'width':w,'height':h});a.wait_for_timeout(200)
        assert a.evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight'),f'overflow {w}'
        assert a.locator('#chat-input').is_visible()
        a.screenshot(path=str(OUT/f'tavern-{w}.png'))
    a.locator('#leave-room').click();b.locator('#leave-room').click()
    assert not errors,errors
    for c in contexts:c.close()
    browser.close()
    browser=p.webkit.launch(headless=True);context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,**options);page=context.new_page();page.on('pageerror',lambda e:errors.append(e.stack))
    page.goto(BASE+'/port/game.html#multiplayer');page.locator('#player-name').fill('Проверка');page.locator('#show-create').click();page.locator('#cancel-create').click()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight')
    page.locator('#close-tavern').click();assert page.locator('#tavern').is_hidden();page.locator('#open-tavern').click();assert page.locator('#tavern').is_visible()
    page.screenshot(path=str(OUT/'webkit-phone.png'));browser.close()
    assert not errors,errors
    result={'passed':True,'base':BASE,'checks':['minimal landing and GitHub','private invite and public isolation','chat plain text/table/Unicode limit','waiting host migration','public room selection/join','desktop/portrait/landscape no document scroll','WebKit touch sidebar'],'errors':errors};(OUT/'ui.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(result)
