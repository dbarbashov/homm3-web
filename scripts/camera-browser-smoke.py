"""Exercise smooth camera through real movement and original options UI.

BROWSER=webkit and VIEW=portrait cover the tall HD map; VIEW=classic uses
800x600. Diagnostics are read-only (apart from opting into the render trace).
"""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
BROWSER = os.getenv('BROWSER', 'chromium')
VIEW = os.getenv('VIEW', 'wide')
OUT = ROOT / 'test-results/camera' / (BROWSER + '-' + VIEW)
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = getattr(p, BROWSER).launch(headless=True)
    viewport = {'width': 390, 'height': 844} if VIEW == 'portrait' else {'width': 1600, 'height': 800}
    page = browser.new_page(viewport=viewport)
    use_silent_audio(page)
    page.add_init_script('window.homm3CameraTrace=[]')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    canvas = page.locator('#canvas')
    samples = []

    def screen(name):
        page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s', arg=name, timeout=90000)

    def toggle(enabled):
        page.locator('#view-toggle').click()
        if page.evaluate('homm3SmoothCamera') != enabled:
            page.locator('#smooth-camera').click()
        assert page.locator('#smooth-camera').get_attribute('aria-pressed') == str(enabled).lower()
        page.locator('#view-toggle').click()
        page.mouse.move(viewport['width'] / 2, viewport['height'] / 2)
        page.wait_for_timeout(100)

    def click(x, y):
        hd = page.evaluate('homm3HDState')
        box = canvas.bounding_box()
        canvas.click(position={'x': (x + hd['overlayX']) * box['width'] / hd['width'],
                               'y': (y + hd['overlayY']) * box['height'] / hd['height']}, delay=80)

    def speed(value):
        canvas.press('o')
        page.wait_for_function('!homm3HDState.topIsMap')
        page.wait_for_timeout(300)
        click(209 + (value - 1) * 48, 148)
        page.wait_for_function('(v)=>homm3Settings.heroSpeed===v', arg=value)
        click(560, 492)
        page.wait_for_function('homm3HDState.topIsMap')
        page.wait_for_timeout(300)

    def move(key, dx, dy, enabled):
        toggle(enabled)
        before = page.evaluate('homm3GameState')
        page.evaluate('homm3CameraTrace=[]')
        canvas.press(key)
        page.wait_for_function('old=>homm3GameState.movement<old && !homm3GameState.moving', arg=before['movement'])
        after = page.evaluate('homm3GameState')
        trace = page.evaluate('homm3CameraTrace')
        assert (after['x'], after['y']) == (before['x'] + dx, before['y'] + dy), after
        assert trace and trace[-1]['x'] == trace[-1]['y'] == 0, trace
        assert len({(f['originX'], f['originY']) for f in trace}) == 1
        chosen = page.evaluate('homm3Settings.heroSpeed')
        final = [f for f in trace if not f['intermediate']]
        assert len(final) == {1: 4, 2: 3, 3: 2, 4: 1}[chosen], final
        assert [f['heroFrame'] for f in final] == list(range(1, len(final) + 1)), final
        axis = 'x' if dx else 'y'
        distance = [abs(f[axis]) for f in trace]
        assert all(a >= b for a, b in zip(distance, distance[1:])), distance
        if dx and dy:
            assert all(abs(f['x']) == abs(f['y']) for f in trace)
        steps = [32 - distance[0]] + [a - b for a, b in zip(distance, distance[1:])]
        if enabled and chosen != 4:
            assert len(trace) > len(final) and max(steps) < {1: 8, 2: 12, 3: 16}[chosen], steps
            # A tile still uses the original 100/150/200ms animation budget;
            # allow renderer/scheduler overhead, not another delay per redraw.
            budget = {1: 200, 2: 150, 3: 100}[chosen]
            assert trace[-1]['at'] - trace[0]['at'] < budget + 80
        result = {'smooth': enabled, 'speed': chosen, 'key': key,
                  'movementCost': before['movement'] - after['movement'], 'maxStepPixels': max(steps),
                  'trace': trace, 'final': after}
        samples.append(result)
        print(json.dumps({k: v for k, v in result.items() if k not in ('trace', 'final')}), flush=True)

    try:
        url = 'http://127.0.0.1:8783/port/game.html' + ('?hd=0' if VIEW == 'classic' else '')
        page.goto(url)
        assert page.evaluate('homm3SmoothCamera') is True
        toggle(False)
        page.reload()
        assert page.evaluate('homm3SmoothCamera') is False
        toggle(True)
        page.reload()
        assert page.evaluate('homm3SmoothCamera') is True
        page.locator('#start').click(); screen('main')
        canvas.press('n'); screen('new'); canvas.press('s'); screen('scenarios')
        canvas.press('b'); page.wait_for_timeout(4000); canvas.press('Enter'); screen('adventure')
        canvas.press('ArrowDown')
        page.wait_for_function('homm3GameState.y===6 && !homm3GameState.moving')
        for chosen in (2, 1, 3, 4):
            if chosen != 2:
                speed(chosen)
            move('ArrowDown', 0, 1, False)
            move('ArrowUp', 0, -1, True)
            assert samples[-1]['movementCost'] == samples[-2]['movementCost'] == 100
        speed(2)
        move('ArrowDown', 0, 1, True)
        move('PageUp', 1, -1, True)
        move('End', -1, 1, True)
        move('ArrowUp', 0, -1, True)
        canvas.screenshot(path=str(OUT / 'map.png'))
        # Platform motion preference supplies the initial default, but an
        # explicit saved choice wins. No game boot is needed for this check.
        reduced = browser.new_context(reduced_motion='reduce')
        pref = reduced.new_page(); pref.goto(url)
        assert pref.evaluate('homm3SmoothCamera') is False
        pref.locator('#view-toggle').click(); pref.locator('#smooth-camera').click(); pref.reload()
        assert pref.evaluate('homm3SmoothCamera') is True
        reduced.close()
        assert not errors, errors
        (OUT / 'results.json').write_text(json.dumps({'passed': True, 'samples': samples,
            'persistence': True, 'reducedMotion': True, 'errors': errors}, indent=2))
    finally:
        canvas.screenshot(path=str(OUT / 'last.png'))
        browser.close()
