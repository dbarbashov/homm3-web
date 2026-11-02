"""Silent offline install + cold browser restart + real save/load. Isolated origin/profile only."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import atexit, json, os, socket, subprocess, tempfile, time, urllib.request
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/offline';OUT.mkdir(parents=True,exist_ok=True)
owned_server=None
BASE=os.environ.get('SITE_URL')
if not BASE:
 with socket.socket() as sock:
  sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 BASE=f'http://127.0.0.1:{port}'
 owned_server=subprocess.Popen(['node','server.mjs'],cwd=ROOT,env={**os.environ,'HOST':'127.0.0.1','PORT':str(port),'LOBBY_PORT':'59999'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 atexit.register(lambda: owned_server.poll() is None and owned_server.terminate())
 for _ in range(100):
  try:
   urllib.request.urlopen(BASE+'/site/offline.html');break
  except OSError:time.sleep(.05)

ENGINE=os.environ.get('BROWSER','chromium')
installation=Path(json.loads((ROOT/'.local/game.json').read_text())['gameRoot'])
checks=[];errors=[];logs=[]
def record(name):
 checks.append(name);print(ENGINE,name,'PASS',flush=True)
def screen(page,name):
 page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=name,timeout=90000)
def attach(page):
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:logs.append(m.text) if m.type=='error' else None)
def click_game(page,x,y):
 c=page.locator('#canvas');box=c.bounding_box();c.click(position={'x':x*box['width']/800,'y':y*box['height']/600},delay=100)
with tempfile.TemporaryDirectory(prefix='offline-files-',dir=ROOT/'.local') as fixture, tempfile.TemporaryDirectory(prefix='offline-profile-',dir=ROOT/'.local') as profile:
 folder=Path(fixture)
 for source in (installation/'Data').iterdir():
  if source.name.lower() in ['h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod','heroes3.snd','h3ab_ahd.snd','h3ab_ahd.vid']:
   os.link(source,folder/source.name)
 for source in (installation/'Mp3').iterdir():
  if source.suffix.lower()=='.mp3':os.link(source,folder/source.name)
 os.link(installation/'Maps/Arrogance.h3m',folder/'Arrogance.h3m')
 with sync_playwright() as p:
  browser=getattr(p,ENGINE)
  webkit_browser=browser.launch(headless=True) if ENGINE=='webkit' else None
  context=webkit_browser.new_context(viewport={'width':1100,'height':900}) if webkit_browser else browser.launch_persistent_context(profile,headless=True,viewport={'width':1100,'height':900})
  use_silent_audio(context)
  page=context.pages[0] if context.pages else context.new_page();attach(page)
  try:
   page.goto(BASE+'/site/offline.html')
   page.wait_for_function('!document.querySelector("#offline-install").disabled')
   # Real CacheStorage regression checks, tiny synthetic data, no runtime or game files.
   result=page.evaluate('''async()=>{
     const store=await import('/site/offline-store.js');
     const names=['h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod','heroes3.snd'];
     const catalog={ready:true,archives:names.slice(0,4).map(name=>({name,bytes:3})),soundArchives:[{name:names[4],bytes:3}],maps:['test.h3m'],music:[],videos:['intro.smk']};
     let calls=[],fail='';
     const source={catalog,identity:'first',fetch:async url=>{calls.push(url);if(url===fail)throw Error('interrupted');return new Response(new Uint8Array([1,2,3]));}};
     await store.exclusive(()=>store.install(source));
     const original=await store.installed();
     if(!original.complete || original.catalog.videos.length)throw Error('invalid complete install');
     source.identity='second';fail='/api/scenario?name=test.h3m';calls=[];
     try{await store.exclusive(()=>store.install(source));throw Error('expected failure');}catch(e){if(e.message!=='interrupted')throw e;}
     if((await store.installed()).cache!==original.cache)throw Error('partial install replaced active');
     fail='';calls=[];await store.exclusive(()=>store.install(source));
     if(calls.length!==1 || !calls[0].includes('test.h3m'))throw Error('resume redownloaded resources');
     source.identity='checksum';source.hashes={'test.h3m':'0'.repeat(64)+'.h3m'};
     try{await store.exclusive(()=>store.install(source));throw Error('expected checksum failure');}catch(e){if(!e.message.includes('сумма'))throw e;}
     const previous=(await store.installed()).cache;
     source.identity='quota';source.hashes={};const realPut=Cache.prototype.put;
     Cache.prototype.put=function(key,response){if(String(key).includes('test.h3m'))throw new DOMException('test quota','QuotaExceededError');return realPut.call(this,key,response);};
     try{await store.exclusive(()=>store.install(source));throw Error('expected quota failure');}catch(e){if(e.name!=='QuotaExceededError')throw e;}finally{Cache.prototype.put=realPut;}
     if((await store.installed()).cache!==previous)throw Error('quota failure replaced active');
     await store.exclusive(async()=>{try{await store.exclusive(()=>{});throw Error('lock missing');}catch(e){if(!e.message.includes('другой вкладке'))throw e;}});
     await store.exclusive(store.removeDownloads);
     return {atomic:true,resume:true,hashes:true,quota:true,lock:true};
   }''')
   record('atomic install, interrupted resume, hash mismatch, quota failure, exclusive lock')
   page.locator('#game-files').set_input_files(folder)
   page.wait_for_function('document.querySelector("#source-hint").textContent.includes("1 карт")')
   page.locator('#offline-videos').check()
   page.locator('#offline-install').click()
   page.wait_for_function('!document.querySelector("#offline-play").hidden',timeout=180000)
   record('real local import, application + maps + music + sound + optional videos installed')
   page.screenshot(path=str(OUT/(ENGINE+'-ready.png')))
   for width,height in [(852,393),(393,852)]:
    page.set_viewport_size({'width':width,'height':height})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(OUT/(ENGINE+f'-ready-{width}.png')),full_page=True)
   page.set_viewport_size({'width':1100,'height':900})
   record('desktop and phone portrait/landscape layout')
   page.locator('#offline-play').click();screen(page,'main')
   assert page.evaluate('navigator.serviceWorker.controller!==null')
   assert page.evaluate('(async()=>{const c=await (await homm3Assets.fetch("/api/catalog")).json(); return c.offline && c.maps.length===1;})()')
   c=page.locator('#canvas');c.press('n');screen(page,'new');c.press('s');screen(page,'scenarios');c.press('b');page.wait_for_timeout(3000);c.press('Enter');screen(page,'adventure')
   page.evaluate('window.savedCount=0;addEventListener("homm3-save-persisted",()=>savedCount++)')
   c.press('s');screen(page,'scenarios');click_game(page,495,555)
   page.wait_for_function('window.savedCount>0',timeout=30000);c.press('Enter');screen(page,'adventure')
   state=page.evaluate('window.homm3GameState')
   saves=page.evaluate('''async()=>{const result={};for(const name of Module.FS.readdir('/runtime/games').filter(n=>/\\.GM1$/i.test(n))) {const data=Module.FS.readFile('/runtime/games/'+name);result[name]=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)));}return result;}''')
   assert saves
   record('real solo game and durable IDBFS save')
   # Chromium: full browser process restart. This WebKit test build cannot launch persistent profiles.
   if ENGINE=='webkit':
    page.close()
    if not owned_server:raise RuntimeError('WebKit offline check requires its own server; omit SITE_URL')
    owned_server.terminate();owned_server.wait(timeout=10);page=context.new_page()
   else:
    context.close()
    context=browser.launch_persistent_context(profile,headless=True,viewport={'width':1100,'height':900},offline=True)
    use_silent_audio(context);page=context.pages[0]
   attach(page)
   requests=[];page.on('request',lambda r:requests.append(r.url))
   page.goto(BASE+'/');page.get_by_role('link',name='Одиночная игра',exact=True).click();screen(page,'main')
   actual=page.evaluate('''async()=>{const result={};for(const name of Module.FS.readdir('/runtime/games').filter(n=>/\\.GM1$/i.test(n))) {const data=Module.FS.readFile('/runtime/games/'+name);result[name]=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)));}return result;}''')
   assert actual==saves
   record(('new WebKit tab' if ENGINE=='webkit' else 'cold process restart')+' offline: home, engine, assets and exact saved bytes')
   c=page.locator('#canvas');c.press('l');screen(page,'load');c.press('s');screen(page,'scenarios');c.press('l');screen(page,'adventure')
   loaded=page.evaluate('window.homm3GameState')
   for key in ['day','hero','x','y','z','movement','gold']:assert loaded[key]==state[key],(key,loaded,state)
   page.wait_for_function('window.homm3Music?.state?.playing===true',timeout=15000)
   record('saved game loads offline with identical day, hero, position, movement and gold; music plays silently')
   page.screenshot(path=str(OUT/(ENGINE+'-offline-adventure.png')))
   media=page.evaluate('''async()=>{const catalog=await (await homm3Assets.fetch('/api/catalog')).json();let count=0;for(const [kind,names] of [['music',catalog.music],['video',catalog.videos]])for(const name of names){const r=await homm3Assets.fetch('/api/'+kind+'?name='+encodeURIComponent(name));if(!r.ok || !(await r.arrayBuffer()).byteLength)throw Error(name);count++;}return count;}''')
   assert not any('/api/' in u or '/lobby/' in u for u in requests),requests
   record('all installed music/video readable offline; no game-resource or lobby network requests')
   # Explicit resource deletion must leave engine saves intact on disk.
   await_script='''async()=>{const s=await import('/site/offline-store.js');await s.exclusive(s.removeDownloads);return await s.installed();}'''
   assert page.evaluate(await_script) is None
   assert page.evaluate('Module.FS.readdir("/runtime/games").some(n=>/\\.GM1$/i.test(n))')
   record('remove downloads leaves saves untouched')
   assert not errors,errors
   result={'passed':True,'browser':ENGINE,'checks':checks,'errors':errors,'mediaFiles':media,'coldRestartOffline':ENGINE=='chromium','newTabOffline':True,'realSavedGameRestored':True}
   (OUT/(ENGINE+'-results.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
  finally:
   (OUT/(ENGINE+'-console.json')).write_text(json.dumps(logs,ensure_ascii=False,indent=2))
   (OUT/(ENGINE+'-errors.json')).write_text(json.dumps(errors,ensure_ascii=False,indent=2))
   context.close()
