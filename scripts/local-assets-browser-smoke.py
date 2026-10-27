"""Boot standalone Rust-hosted site from a browser-selected local installation."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os, tempfile
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'test-results/site').mkdir(parents=True,exist_ok=True)
installation=Path(json.loads((ROOT/'.local/game.json').read_text())['gameRoot'])
with tempfile.TemporaryDirectory(prefix='browser-files-',dir=ROOT/'.local') as fixture:
    folder=Path(fixture)
    sources=[*(installation/'Data').glob('*.lod'),*(installation/'Data').glob('*.LOD')]
    names={'h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod'}
    sources=[p for p in sources if p.name.lower() in names]
    sources += [p for p in (installation/'Data').iterdir() if p.name.lower()=='heroes3.snd']
    sources += [next((installation/'Maps').glob('*.h3m'))]
    for source in sources: os.link(source,folder/source.name)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page();requests=[];errors=[]
        page.on('console',lambda m:print(m.text,flush=True))
        page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}));page.on('pageerror',lambda e:errors.append(e.stack))
        page.goto('http://127.0.0.1:8784/port/game.html')
        page.wait_for_function('document.querySelector("#source-hint").textContent.includes("Выберите")',timeout=60000)
        assert page.locator('#start').is_disabled()
        page.locator('#game-files').set_input_files(folder)
        page.locator('#start').click(timeout=30000)
        try:page.wait_for_function('window.homm3PortDiagnostics?.screen==="main"',timeout=45000)
        except:
            print(page.locator('#status').inner_text(),errors,flush=True)
            page.screenshot(path=str(ROOT/'test-results/site/local-files-error.png'));raise
        assert not errors,errors
        assert not any('/api/archive' in r['url'] or '/api/scenario' in r['url'] or r['method']=='POST' for r in requests)
        result={'passed':True,'files':len(sources),'resourcesReadLocally':True,'errors':errors}
        (ROOT/'test-results/site/local-files.json').write_text(json.dumps(result,indent=2));print(result)
        browser.close()
