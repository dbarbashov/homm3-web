"""Real chat input, server rejection and mobile feedback; no engine launch needed."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os

base = os.environ.get('LOBBY_URL', 'http://127.0.0.1:8786')
out = Path(__file__).resolve().parents[1] / 'test-results/chat'
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width':390,'height':844})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + '/port/game.html#multiplayer')
    page.locator('#player-name').fill('Проверка')
    page.locator('#show-create').click();page.locator('#room-name').fill('Чат')
    page.locator('#create-submit').click()
    page.wait_for_function('window.homm3Room?.players.length===1')
    page.locator('#chat-input').fill('абв'*101)
    assert len(page.locator('#chat-input').input_value()) == 300
    page.locator('#chat-send').click()
    page.wait_for_function('document.querySelector("#chat-input").value === ""')
    assert page.locator('#chat-send').is_disabled()
    page.wait_for_timeout(2200)
    page.locator('#chat-input').fill('АБВ'*100)
    page.locator('#chat-send').click()
    page.wait_for_function('document.querySelector("#chat-error").textContent.includes("уже отправлялось")')
    assert len(page.locator('#chat-input').input_value()) == 300
    assert page.locator('#chat-log p').count() == 1
    page.locator('#chat-error').scroll_into_view_if_needed()
    page.screenshot(path=str(out/'mobile.png'))
    assert not errors, errors
    page.locator('#leave-room').click()
    result = {'passed':True,'checks':['300 Unicode code points','ack clears input','cooldown button','duplicate rejected','draft preserved','mobile error visible'],'errors':errors}
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(result)
    browser.close()
