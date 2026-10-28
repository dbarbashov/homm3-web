"""Drive the real recovered game through SDL input; never mutate game memory."""
from pathlib import Path
import json, time, os
from browser_audio import use_silent_audio
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1200, 'height': 1100})
    use_silent_audio(page)
    errors, logs, states = [], [], []
    page.on('pageerror', lambda e: errors.append(e.stack))
    page.on('console', lambda m: logs.append(m.text))
    raw_canvas = page.locator('#canvas')
    class GameCanvas:
        def __getattr__(self,name): return getattr(raw_canvas,name)
        def pointer(self,method,position,**kwargs):
            size=page.evaluate('window.homm3HDState||{width:800,height:600,adventure:true}')
            x,y=position['x'],position['y']
            if not size['adventure']:x+=(size['width']-800)/2;y+=(size['height']-600)/2
            elif x>=600:x+=size['width']-800
            box=raw_canvas.bounding_box()
            return getattr(raw_canvas,method)(position={'x':x*box['width']/size['width'],'y':y*box['height']/size['height']},**kwargs)
        def click(self,position,**kwargs):return self.pointer('click',position,**kwargs)
        def dblclick(self,position,**kwargs):return self.pointer('dblclick',position,**kwargs)
        def hover(self,position,**kwargs):return self.pointer('hover',position,**kwargs)
    c=GameCanvas()
    def screen(name):
        page.wait_for_function('(name) => window.homm3PortDiagnostics?.screen === name', arg=name, timeout=90000)
    def state():
        return page.evaluate('window.homm3GameState')
    def capture(name):
        page.wait_for_timeout(500)
        assert not errors, errors
        states.append({'step': name, 'state': state()})
        c.screenshot(path=str(OUT / ('play-' + name + '.png')))
        print(name, state(), flush=True)
    def start():
        page.locator('#start').click(timeout=60000)
        screen('main')
    try:
        page.goto(os.environ.get('SITE_URL','http://127.0.0.1:8783')+'/port/game.html')
        start()
        c.hover(position={'x': 650, 'y': 70})
        page.wait_for_timeout(250)
        assert page.evaluate('window.homm3PortDiagnostics.hovered') == 101
        c.press('n'); screen('new'); c.press('s'); screen('scenarios')
        capture('scenario')
        c.press('b'); page.wait_for_timeout(4000); c.press('Enter'); screen('adventure')
        c.hover(position={'x': 320, 'y': 280}); capture('adventure')
        original = state()
        assert original['day'] == 1 and original['hero'] >= 0
        c.press('ArrowDown')
        page.wait_for_function('(y) => window.homm3GameState.y === y', arg=original['y'] + 1)
        capture('movement')
        moved = state()
        assert moved['movement'] < original['movement']
        c.dblclick(position={'x': 770, 'y': 231}, delay=150); page.wait_for_timeout(1500); capture('town')
        c.press('Escape'); page.wait_for_timeout(700)
        c.press('s'); screen('scenarios'); capture('save-dialog')
        c.click(position={'x': 495, 'y': 555}, delay=100)
        page.wait_for_function('window.homm3LastSave', timeout=30000)
        capture('saved'); c.press('Enter')
        saves = page.evaluate(r'Module.FS.readdir("/runtime/games").filter(n => /\.GM1$/i.test(n))')
        assert saves
        page.reload(); start()
        c.press('l'); screen('load'); c.press('s'); screen('scenarios'); capture('load-list')
        c.press('l'); screen('adventure'); capture('loaded')
        loaded = state()
        for key in ['day', 'hero', 'x', 'y', 'z', 'movement', 'gold']:
            assert loaded[key] == moved[key], (key, loaded, moved)
        c.hover(position={'x': 320, 'y': 280})
        c.press('ArrowDown')
        page.wait_for_function('(y) => window.homm3GameState.y === y', arg=moved['y'] + 1)
        page.wait_for_function('!window.homm3GameState.moving')
        page.wait_for_timeout(1000)
        capture('loaded-movement')
        c.press('e'); page.wait_for_timeout(800); c.press('Enter')
        page.wait_for_function('window.homm3GameState?.day === 2 && window.homm3GameState?.player === 0', timeout=120000)
        capture('next-day')
        assert state()['gold'] == original['gold'] + 1000
        assert state()['movement'] == original['movement']
        c.hover(position={'x': 320, 'y': 280})
        for key in ['End']:
            c.press(key); page.wait_for_timeout(1500)
        page.wait_for_function('window.homm3GameState.combat === 1', timeout=20000)
        capture('battle')
        c.click(position={'x': 27, 'y': 580}, delay=100); page.wait_for_timeout(700)
        c.click(position={'x': 345, 'y': 325}, delay=100); c.press('Enter'); page.wait_for_timeout(700)
        c.click(position={'x': 300, 'y': 200}, delay=100)
        page.wait_for_timeout(4500); capture('battle-manual-move')
        c.click(position={'x': 178, 'y': 580}, delay=120)
        page.wait_for_function('window.homm3GameState.autoCombat === 1', timeout=15000)
        deadline = time.monotonic() + 180
        while page.evaluate('window.homm3PortDiagnostics.screen') != 'combat-results':
            assert time.monotonic() < deadline, 'Battle did not finish'
            assert not errors, errors
            page.wait_for_timeout(1000)
        capture('battle-result')
        c.press('Enter'); screen('adventure'); capture('battle-return')
        assert state()['combat'] == 0
        assert state()['experience'] > loaded['experience']
        page.wait_for_timeout(2500)
        c.press('Escape'); page.wait_for_timeout(1000); capture('exit-confirm'); c.press('Enter'); screen('main')
        capture('return-menu')
        result = {'passed': True, 'engine': 'recovered C++ / WASM', 'states': states, 'saves': saves, 'errors': errors}
        (OUT / 'game-browser-smoke.json').write_text(json.dumps(result, indent=2))
        print('PASS: scenario, movement, town, persistent save/reload, AI day, manual combat, victory, menu return.', flush=True)
    finally:
        try: c.screenshot(path=str(OUT / 'play-last.png'))
        except Exception: pass
        (OUT / 'game-browser-console.json').write_text(json.dumps(logs, indent=2))
        (OUT / 'game-browser-errors.json').write_text(json.dumps(errors, indent=2))
        browser.close()
