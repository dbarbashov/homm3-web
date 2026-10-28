"""A real move must publish the sidebar before any resize or extra action."""
from io import BytesIO
from pathlib import Path
import json
import os
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/sidebar'
OUT.mkdir(parents=True, exist_ok=True)
engine = os.getenv('BROWSER', 'chromium')
with sync_playwright() as p:
    browser = getattr(p, engine).launch(headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 800})
    use_silent_audio(page)
    canvas = page.locator('#canvas')
    errors, checks = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def screen(name):
        page.wait_for_function('(name) => window.homm3PortDiagnostics?.screen === name', arg=name, timeout=90000)

    def layout(w, h):
        page.wait_for_function('([w,h]) => homm3HDState.width === w && homm3HDState.height === h', arg=[w, h])

    def bars(name):
        page.mouse.move(1, 1)
        page.wait_for_timeout(200)
        image = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
        width = page.evaluate('homm3HDState.width')
        scale = image.width / width
        image = image.crop(tuple(round(v * scale) for v in (width - 190, 213, width - 126, 245)))
        image.save(OUT / f'{engine}-{name}.png')
        return image

    try:
        page.goto('http://127.0.0.1:8783/port/game.html')
        page.locator('#start').click()
        screen('main')
        canvas.press('n'); screen('new')
        canvas.press('s'); screen('scenarios')
        canvas.press('b'); page.wait_for_timeout(4000)
        canvas.press('Enter'); screen('adventure')
        for name, viewport, dimensions, key in [
            ('wide', (1600, 800), (1200, 600), 'ArrowDown'),
            ('portrait', (800, 1200), (800, 1200), 'ArrowDown'),
            ('classic', (800, 600), (800, 600), 'ArrowUp'),
        ]:
            page.set_viewport_size(dict(zip(('width', 'height'), viewport)))
            layout(*dimensions)
            before = bars(name + '-before')
            movement = page.evaluate('homm3GameState.movement')
            canvas.press(key)
            page.wait_for_function('(old) => homm3GameState.movement < old && !homm3GameState.moving', arg=movement)
            after = bars(name + '-after')
            assert ImageChops.difference(before, after).getbbox(), (name, 'movement changed but bar stayed stale')
            # A forced full repaint must not reveal additional stale pixels.
            page.set_viewport_size({'width': 1000, 'height': 800})
            page.wait_for_timeout(300)
            page.set_viewport_size(dict(zip(('width', 'height'), viewport)))
            layout(*dimensions)
            refreshed = bars(name + '-refreshed')
            assert ImageChops.difference(after, refreshed).getbbox() is None, (name, 'bar only caught up after resize')
            checks.append({'layout': name, 'beforeMovement': movement,
                           'afterMovement': page.evaluate('homm3GameState.movement'),
                           'immediate': True, 'unchangedAfterResize': True})
        page.set_viewport_size({'width': 1600, 'height': 800})
        layout(1200, 600)

        def town_icon(name):
            page.mouse.move(1, 1)
            page.wait_for_timeout(200)
            image = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
            scale = image.width / 1200
            image = image.crop(tuple(round(v * scale) for v in (1147, 212, 1195, 244)))
            image.save(OUT / f'{engine}-town-{name}.png')
            return image

        def click(x, y, double=False):
            box = canvas.bounding_box()
            point = {'x': x * box['width'] / 1200, 'y': y * box['height'] / 600}
            if double:
                canvas.dblclick(position=point, delay=140)
            else:
                canvas.click(position=point)

        def layers(count):
            page.wait_for_function('(count) => homm3HDState.layers === count', arg=count)

        available = town_icon('available')
        gold = page.evaluate('homm3GameState.gold')
        click(1170, 228, double=True); layers(1)
        # Conflux town hall, then its City Hall upgrade and original confirmation.
        click(300, 250); layers(2)
        click(300, 80); layers(3)
        canvas.press('Enter'); layers(1)
        page.wait_for_timeout(400)
        canvas.press('Escape'); layers(0)
        page.wait_for_function('(gold) => homm3GameState.gold === gold - 5000', arg=gold)
        built = town_icon('built')
        assert ImageChops.difference(available, built).getbbox(), 'town build marker stayed stale'
        day = page.evaluate('homm3GameState.day')
        canvas.press('e'); page.wait_for_timeout(700); canvas.press('Enter')
        page.wait_for_function('(day) => homm3GameState.day > day && homm3GameState.player === 0', arg=day, timeout=90000)
        page.wait_for_timeout(500); canvas.press('Enter'); layers(0)
        renewed = town_icon('new-day')
        assert ImageChops.difference(available, renewed).getbbox() is None, 'town build marker did not reset on new day'
        checks.append({'townBuildImmediate': True, 'townResetNextDay': True})
        assert not errors, errors
        result = {'passed': True, 'checks': checks, 'errors': errors}
        (OUT / f'{engine}.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    finally:
        canvas.screenshot(path=str(OUT / f'{engine}-last.png'))
        browser.close()
