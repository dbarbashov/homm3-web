"""Theme ownership and all eight palettes, using engine snapshot fixtures (no game)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import os,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/player-theme';OUT.mkdir(parents=True,exist_ok=True);BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
with sync_playwright() as p:
 for engine in ['chromium','webkit']:
  b=getattr(p,engine).launch();ctx=b.new_context(viewport={'width':734,'height':343},has_touch=True);use_silent_audio(ctx);ctx.route('**/port/game.js',lambda r:r.fulfill(body=''));g=ctx.new_page();errors=[];g.on('pageerror',lambda e:errors.append(str(e)));g.goto(BASE+'/port/game.html');g.wait_for_load_state('networkidle')
  g.evaluate("()=>{window.homm3Boot={running:true};window.homm3PortDiagnostics={screen:'adventure'};document.querySelector('#launch-cover').hidden=true}")
  g.locator('#view-toggle').click()
  def snapshot(local,turn=0,remote=0,humans=1,slot=0,last=5):
   g.evaluate('''([local,turn,remote,humans,slot,last])=>{window.homm3GameState={localPlayer:local,player:turn,remote,humans};window.homm3NetworkState={turnSlot:slot,aiOwner:last};window.homm3HeroStates=Array.from({length:8},(_,i)=>({player:i,human:i===1||i===5,dpid:i+1}));}''',[local,turn,remote,humans,slot,last])
  def color(n):g.wait_for_function('(n)=>document.documentElement.dataset.playerColor===String(n)',arg=n)
  gold=g.locator('#view-resume').evaluate('(e)=>getComputedStyle(e).backgroundImage');frames=[];icons=[]
  for n in range(8):
   snapshot(n);color(n);frames.append(g.locator('#view-actions').evaluate('(e)=>getComputedStyle(e).borderImageSource'));icons.append(g.locator('.menu-icon').evaluate('(e)=>getComputedStyle(e).backgroundImage'))
   assert g.locator('#view-resume').evaluate('(e)=>getComputedStyle(e).backgroundImage')==gold
   assert g.locator('#view-actions').evaluate('(e)=>e.scrollHeight===e.clientHeight');g.screenshot(path=str(OUT/(engine+f'-palette-{n}.png')))
  assert len(set(frames))==8 and len(set(icons))==8
  snapshot(5,turn=2);color(5)  # Solo player's color survives an AI turn.
  snapshot(1,turn=5,remote=1,humans=2);color(1)  # Remote guest keeps blue on purple's turn.
  snapshot(0,turn=1,humans=2,slot=1);color(1)
  snapshot(0,turn=5,humans=2,slot=5);color(5)
  snapshot(0,turn=2,humans=2,slot=2,last=5);color(5)  # Same fallback as original hotseat UI.
  snapshot(-1);g.wait_for_timeout(350);assert g.locator('html').get_attribute('data-player-color')=='5'
  g.evaluate("window.homm3PortDiagnostics.screen='main';window.dispatchEvent(new Event('homm3-ready'))");assert g.locator('html').get_attribute('data-player-color') is None
  # The code-defined fallback also follows the player color without extracted assets.
  g.route('**/site/skin.css*',lambda r:r.fulfill(body='',content_type='text/css'));g.reload();g.evaluate("()=>{window.homm3Boot={running:true};window.homm3PortDiagnostics={screen:'adventure'};document.querySelector('#launch-cover').hidden=true}");snapshot(5);color(5);assert g.locator('.menu-icon').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(103, 38, 120)'
  assert not errors,errors;b.close();print(engine,'8 palettes, solo AI, remote ownership, hotseat, reset, fallback PASS',flush=True)
(OUT/'snapshot-results.json').write_text(json.dumps({'passed':True,'scope':'Browser snapshot fixtures, not actual games','engines':['chromium','webkit']},indent=2))
