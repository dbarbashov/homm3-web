"""Exercise recovered C++ menu handlers, nested dialogs and scaled SDL input."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = os.environ.get('HOMM3_URL', 'http://127.0.0.1:8783')
OUT = Path('test-results')
OUT.mkdir(exist_ok=True)
golden = {(x['screen'], x['hover']): x['framebufferFNV1a']
          for x in json.loads((OUT / 'frontend-native.json').read_text())}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1200, 'height': 1050})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/port/')
    page.locator('#start').click(timeout=30000)
    page.wait_for_function('window.homm3PortDiagnostics?.ready', timeout=60000)
    canvas = page.locator('#canvas')

    def state():
        return page.evaluate('window.homm3PortDiagnostics')

    def screen(name):
        page.wait_for_function('window.homm3PortDiagnostics.screen === ' + json.dumps(name))

    def move(x, y):
        box = canvas.bounding_box()
        page.mouse.move(box['x'] + x * box['width'] / 800,
                        box['y'] + y * box['height'] / 600)

    def click(x, y):
        move(x, y)
        page.mouse.down()
        page.wait_for_timeout(40)
        page.mouse.up()

    def pixels(name, hover=-1):
        page.wait_for_function('window.homm3PortDiagnostics.framebufferFNV1a === ' +
                               json.dumps(golden[name, hover]))

    def screenshot(name):
        page.screenshot(path=str(OUT / (name + '.png')), full_page=True)

    screen('main')
    pixels('main')
    assert page.locator('#progress').is_hidden()
    screenshot('cpp-menu-browser')
    for ident, y in [(101, 65), (102, 185), (103, 300), (104, 410), (105, 520)]:
        move(650, y)
        pixels('main', ident)
        assert state()['hovered'] == ident
        if ident == 101:
            screenshot('frontend-hover')
        move(100, 200)
        pixels('main')
        assert state()['hovered'] == -1
    # Original button::main owns the blocking press/release loop and drag cancel.
    move(650, 65)
    page.mouse.down()
    page.wait_for_timeout(100)
    assert state()['commands'] == []
    screenshot('cpp-menu-pressed')
    move(400, 70)
    page.mouse.up()
    page.wait_for_timeout(100)
    assert state()['commands'] == []
    screen('main')
    click(650, 65)
    screen('new')
    move(100, 200)
    pixels('new')
    screenshot('frontend-new')
    for ident, y in [(100, 65), (102, 180), (101, 290), (103, 410), (104, 520)]:
        move(650, y)
        pixels('new', ident)
    # S selects the original single-player widget; unsupported game startup is explicit.
    canvas.press('s')
    screen('message')
    screenshot('frontend-unavailable')
    canvas.press('Enter')
    screen('new')
    click(650, 520)
    screen('main')
    canvas.press('l')
    screen('load')
    move(100, 200)
    pixels('load')
    screenshot('frontend-load')
    canvas.press('Escape')
    screen('main')
    # Re-enter via keyboard and return; catches stale static hover IDs on reopened menus.
    canvas.press('n')
    screen('new')
    move(650, 65)
    pixels('new', 100)
    canvas.press('Escape')
    screen('main')
    move(650, 65)
    pixels('main', 101)
    # Real help text and original dialog chrome; release closes the popup.
    page.mouse.down(button='right')
    screen('message')
    screenshot('frontend-help')
    page.mouse.up(button='right')
    screen('main')
    canvas.press('Escape')
    screen('confirm')
    screenshot('frontend-confirm')
    canvas.press('Escape')
    screen('main')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(100)
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    click(650, 65)
    screen('new')
    screenshot('cpp-menu-mobile')
    canvas.press('Escape')
    screen('main')
    click(650, 520)
    screen('confirm')
    canvas.press('Enter')
    screen('closed')
    assert page.locator('#start').is_enabled()
    assert not errors, errors
    report = {**state(), 'browserErrors': errors, 'hoverPixelParity': True,
              'mouse': True, 'keyboard': True, 'dragCancellation': True,
              'newAndLoadMenus': True, 'rightClickHelp': True, 'quitAndCancel': True,
              'scaledCoordinates': True, 'mobileOverflow': False}
    (OUT / 'cpp-browser-smoke.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    browser.close()
