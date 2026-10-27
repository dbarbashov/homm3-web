"""Local integration check; requires a running npm start and Playwright Chromium."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path('test-results')
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8783')
    page.wait_for_function('window.homm3Diagnostics !== undefined')
    first = page.evaluate('window.homm3Diagnostics')
    assert first['wasm'] and first['objects'] > 0 and not first['failures']
    page.locator('#underground').click()
    page.screenshot(path=str(out / 'underground.png'), full_page=True)
    page.locator('#surface').click()
    page.locator('#plus').click()
    assert page.locator('#scale').inner_text() == '125%'
    page.locator('#grid').check()
    page.locator('#map').click(position={'x': 300, 'y': 250})
    assert '·' in page.locator('#cell').inner_text()
    page.locator('#grid').uncheck()
    page.locator('#minus').click()
    page.locator('#music').click()
    page.wait_for_timeout(300)
    assert page.locator('#music').inner_text() == 'Выключить музыку'
    page.locator('#music').click()
    page.screenshot(path=str(out / 'browser-map.png'), full_page=True)
    page.locator('#maps').select_option('Dead and Buried.h3m')
    page.locator('#open').click()
    page.wait_for_function('window.homm3Diagnostics?.map === "Dead and Buried.h3m"')
    second = page.evaluate('window.homm3Diagnostics')
    assert second['objects'] > 0 and not second['failures']
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(300)
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.screenshot(path=str(out / 'mobile.png'), full_page=True)
    assert not errors, errors
    result = {'firstMap': first, 'secondMap': second, 'browserErrors': errors,
              'controls': 'pass', 'musicPlayback': 'started', 'mobileOverflow': False}
    (out / 'browser-smoke.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False))
    browser.close()
