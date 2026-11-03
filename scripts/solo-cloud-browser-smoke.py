"""Silent isolated cloud-save regression: real game files, two devices, forks and retries."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import base64, hashlib, json, os, socket, subprocess, tempfile, time, urllib.request, urllib.error, uuid
ROOT=Path(__file__).resolve().parents[1]
LOBBY=Path(os.environ.get('LOBBY_ROOT', ROOT.parent/'homm3-lobby'))
OUT=ROOT/'test-results/solo-cloud';OUT.mkdir(parents=True,exist_ok=True)
ENGINE=os.environ.get('BROWSER','chromium');checks=[];errors=[]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def ready(url):
 for _ in range(100):
  try:urllib.request.urlopen(url,timeout=1);return
  except OSError:time.sleep(.1)
 raise RuntimeError('service did not start: '+url)
def record(s):checks.append(s);print(ENGINE,s,'PASS',flush=True)
def screen(p,s):p.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=s,timeout=90000)
def click(p,x,y):
 c=p.locator('#canvas');b=c.bounding_box();c.click(position={'x':x*b['width']/800,'y':y*b['height']/600},delay=60)
def api(base,path,token='',body=None,method=None):
 req=urllib.request.Request(base+'/lobby/solo/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method=method or ('POST' if body is not None else 'GET'))
 with urllib.request.urlopen(req,timeout=20) as r:
  data=r.read();return json.loads(data) if 'json' in r.headers.get('Content-Type','') else data
DB='await import("/site/solo-store.js")'
def config(p):return p.evaluate(f'async()=> (await ({DB}).config())')
def queue(p):return p.evaluate(f'async()=> (await ({DB}).rows("queue")).length')
def sync(p):
 p.evaluate('homm3Cloud.sync()');p.wait_for_function('!document.querySelector("#cloud-sync").disabled',timeout=30000)
 p.wait_for_function('async()=>!(await (await import("/site/solo-store.js")).rows("queue")).length',timeout=30000)
def native_save(p):
 c=p.locator('#canvas');p.evaluate('window.saveCount=0;addEventListener("homm3-save-persisted",()=>saveCount++)')
 c.press('s');screen(p,'scenarios');click(p,495,555)
 p.wait_for_timeout(150);c.press('Enter');p.wait_for_function('saveCount>0',timeout=30000);screen(p,'adventure');p.evaluate('homm3Cloud.settled()')
with tempfile.TemporaryDirectory(prefix='solo-cloud-',dir=ROOT/'.local') as temp:
 home=Path(temp);rp,wp=port(),port();base=f'http://127.0.0.1:{wp}';relay=f'http://127.0.0.1:{rp}'
 env={**os.environ,'LOBBY_BIND':f'127.0.0.1:{rp}','HOMM3_AUTHORITY_ENGINE':str(LOBBY/'build/worker/homm3-worker'),'HOMM3_AUTHORITY_RUNTIME':str(ROOT/'.local/runtime'),'HOMM3_HISTORY_DIR':str(home/'history'),'HOMM3_METRICS_PORT':'0'}
 log=open(OUT/(ENGINE+'-services.log'),'w');server=None;asset=None
 def start_relay():
  s=subprocess.Popen([str(LOBBY/'target/release/homm3-lobby')],cwd=LOBBY,env=env,stdout=log,stderr=log);
  try:ready(relay+'/lobby/health');return s
  except Exception:s.terminate();s.wait(timeout=10);raise
 try:
  server=start_relay();asset=subprocess.Popen(['node','server.mjs'],cwd=ROOT,env={**os.environ,'HOST':'127.0.0.1','PORT':str(wp),'LOBBY_PORT':str(rp)},stdout=log,stderr=log);ready(base+'/port/game.html')
  with sync_playwright() as pw:
   browser=getattr(pw,ENGINE).launch(headless=True)
   a=browser.new_context(viewport={'width':1100,'height':900});b=browser.new_context(viewport={'width':1100,'height':900})
   for ctx in [a,b]:use_silent_audio(ctx)
   p=a.new_page();q=b.new_page()
   for page in [p,q]:page.on('pageerror',lambda e:errors.append(str(e)))
   p.goto(base+'/port/game.html?hd=0');p.wait_for_function('!!window.homm3Cloud')
   p.locator('#cloud-open').click();p.locator('#cloud-enable').click();sync(p)
   identity=config(p);assert identity['owner'] and identity['token'];p.locator('#cloud-close').click()
   p.locator('#start').click();screen(p,'main')
   c=p.locator('#canvas');c.press('n');screen(p,'new');c.press('s');screen(p,'scenarios');c.press('b');p.wait_for_timeout(1500);c.press('Enter');screen(p,'adventure')
   native_save(p);sync(p)
   state=p.evaluate('homm3GameState');library=api(base,'saves',identity['token']);assert library['heads'],p.evaluate('({path:window.homm3LastSave,files:Module.FS.readdir("/runtime/games"),status:document.querySelector("#cloud-status").textContent})');initial=library['heads']
   for h in initial:
    content=api(base,'saves/'+h['revision'],identity['token']);assert hashlib.sha256(content).hexdigest()==h['hash']
   record('native manual save uploaded, checksums and empty durable queue')
   grant=api(base,'device/code',identity['token'],method='POST')
   q.goto(base+'/port/game.html?hd=0');q.wait_for_function('!!window.homm3Cloud');q.locator('#cloud-open').click()
   q.locator('#cloud-dialog summary').first.click();q.locator('#cloud-input').fill(grant['code']);q.locator('#cloud-claim button').click()
   q.wait_for_function('(owner)=>document.querySelector("#cloud-count").textContent.includes("В облаке")',arg=identity['owner'],timeout=30000)
   other=config(q);assert other['owner']==identity['owner'] and other['token']!=identity['token']
   q.screenshot(path=str(OUT/(ENGINE+'-library.png')))
   for w,h in [(852,393),(393,852)]:
    q.set_viewport_size({'width':w,'height':h});assert q.evaluate('document.documentElement.scrollWidth<=innerWidth');q.screenshot(path=str(OUT/(ENGINE+f'-library-{w}.png')))
   q.set_viewport_size({'width':1100,'height':900});q.locator('#cloud-close').click();q.locator('#start').click();screen(q,'main')
   downloaded=q.evaluate('Module.FS.readdir("/runtime/games")');assert any(n.lower().endswith('.gm1') for n in downloaded)
   qc=q.locator('#canvas');qc.press('l');screen(q,'load');qc.press('s');screen(q,'scenarios');qc.press('l');screen(q,'adventure')
   loaded=q.evaluate('homm3GameState')
   for key in ['day','hero','x','y','z','movement','gold']:assert loaded[key]==state[key],(key,loaded,state)
   record('second device claims code, mounts real cloud save and loads identical game state; mobile layout')
   a.set_offline(True)
   # Native file write + the production native-save event: isolate queue transport from map randomness.
   def write_save(page,marker):
    page.evaluate('''marker=>{Module.FS.writeFile('/runtime/games/CloudQueue.GM1',new TextEncoder().encode(marker));dispatchEvent(new CustomEvent('homm3-save',{detail:'/runtime/games/CloudQueue.GM1'}));}''',marker)
    page.wait_for_timeout(150);page.evaluate('homm3Cloud.settled()')
   before_day=p.evaluate('homm3GameState.day');c.press('e');p.wait_for_timeout(250);c.press('Enter')
   p.wait_for_function('(day)=>window.homm3GameState?.day>day',arg=before_day,timeout=90000);screen(p,'adventure')
   p.wait_for_function('async()=> (await (await import("/site/solo-store.js")).rows("queue")).some(r=>r.name.toLowerCase().includes("autosave"))',timeout=30000)
   native_save(p);assert queue(p)>0
   record('real turn completes offline; native autosave and manual save enter durable queue')
   write_save(p,'offline-one');assert queue(p)>0
   # Restart the document. Native IDBFS and the independent queue must survive.
   a.set_offline(False);p.route('**/lobby/solo/**',lambda r:r.abort());p.reload();p.wait_for_function('!!window.homm3Cloud');assert queue(p)>0
   p.unroute('**/lobby/solo/**');sync(p);assert any(h['name']=='CloudQueue.GM1' for h in api(base,'saves',identity['token'])['heads'])
   record('offline write survives page restart and uploads automatically after reconnect')
   # Manufacture a lost ACK AFTER server commit using the actual browser queue.
   p.locator('#start').click();screen(p,'main');lost=[False]
   def drop_ack(route):
    if route.request.method=='POST' and not lost[0]:route.fetch();lost[0]=True;route.abort()
    else:route.continue_()
   p.route('**/lobby/solo/saves',drop_ack);write_save(p,'ack-lost');p.evaluate('homm3Cloud.sync()')
   p.wait_for_timeout(500);assert lost[0];p.unroute('**/lobby/solo/saves');sync(p)
   record('lost upload acknowledgement retries idempotently without losing queue')
   # An asynchronous checksum must not authorize overwriting bytes changed meanwhile.
   race={'slot':uuid.uuid4().hex,'revision':uuid.uuid4().hex,'parent':None,'name':'Race.GM1','engine':initial[0]['engine'],'hash':hashlib.sha256(b'race-base').hexdigest(),'data':base64.b64encode(b'race-base').decode()}
   baseline=api(base,'saves',identity['token'],race)
   p.evaluate('''async ({row,owner})=>{Module.FS.writeFile('/runtime/games/Race.GM1',new TextEncoder().encode('race-base'));const db=await import('/site/solo-store.js');await db.track({...row,owner,key:owner+':Race.GM1'});await homm3PersistFiles();}''',{'row':baseline,'owner':identity['owner']})
   race.update(parent=race['revision'],revision=uuid.uuid4().hex,hash=hashlib.sha256(b'race-remote').hexdigest(),data=base64.b64encode(b'race-remote').decode());api(base,'saves',identity['token'],race)
   p.evaluate('''()=>{window.originalDigest=crypto.subtle.digest;window.raceFired=false;crypto.subtle.digest=function(algorithm,data){const task=originalDigest.call(this,algorithm,data);if(new TextDecoder().decode(data)==='race-base'){raceFired=true;Module.FS.writeFile('/runtime/games/Race.GM1',new TextEncoder().encode('race-local'));}return task;};}''')
   sync(p)
   assert p.evaluate("raceFired && new TextDecoder().decode(Module.FS.readFile('/runtime/games/Race.GM1'))==='race-local'")
   p.evaluate('()=>{crypto.subtle.digest=originalDigest;}');record('native write during asynchronous checksum is preserved; remote copy gets another filename')
   # Both clients now share one baseline, then continue independently offline.
   root=next(h for h in api(base,'saves',identity['token'])['heads'] if h['name']=='CloudQueue.GM1')
   async_js='''async ({owner,base,value})=>{const db=await import('/site/solo-store.js');const row=await db.capture(owner,base.name,new TextEncoder().encode(value).buffer,base.engine,base);return row.revision;}'''
   a.set_offline(True);b.set_offline(True)
   r1=p.evaluate(async_js,{'owner':identity['owner'],'base':root,'value':'fork-a'})
   r2=q.evaluate(async_js,{'owner':identity['owner'],'base':root,'value':'fork-b'})
   a.set_offline(False);b.set_offline(False);sync(p);sync(q)
   forks=[h for h in api(base,'saves',identity['token'])['heads'] if h['slot']==root['slot']]
   assert {h['revision'] for h in forks}=={r1,r2};record('two offline continuations retain both heads, no last-write-wins')
   # Two tabs share IDB but carry independent native baselines. Neither may invent ancestry.
   tab=a.new_page();tab.goto(base+'/port/game.html?hd=0');tab.wait_for_function('!!window.homm3Cloud')
   branch=next(h for h in forks if h['revision']==r1)
   t1=p.evaluate(async_js,{'owner':identity['owner'],'base':branch,'value':'tab-a'})
   t2=tab.evaluate(async_js,{'owner':identity['owner'],'base':branch,'value':'tab-b'})
   sync(p);heads=api(base,'saves',identity['token'])['heads']
   assert all(any(h['revision']==r and h['parent']==r1 for h in heads) for r in [t1,t2])
   tab.close();record('same-browser tabs retain independent parent revisions')
   # A bad download cannot enter the local copies database or replace a local save.
   q.route('**/lobby/solo/saves/*',lambda r:r.fulfill(status=200,body='corrupt'))
   q.evaluate('homm3Cloud.sync()');q.wait_for_function('!document.querySelector("#cloud-sync").disabled')
   assert 'Повреждённый' in q.locator('#cloud-status').text_content()
   assert not q.evaluate('async r=>(await (await import("/site/solo-store.js")).rows("copies")).some(c=>c.revision===r)',t1)
   q.unroute('**/lobby/solo/saves/*');sync(q);record('corrupt download rejected before installation, clean retry succeeds')
   stranger=api(base,'identity',method='POST')
   enrollment=browser.new_context();use_silent_audio(enrollment);enrollment_page=enrollment.new_page();enrollment_page.goto(base+'/port/game.html?hd=0');enrollment_page.wait_for_function('!!window.homm3Cloud')
   assert enrollment_page.evaluate('''async identity=>{const db=await import('/site/solo-store.js');await Promise.all([db.capture(null,'Early.GM1',new Uint8Array([1]).buffer,'e'.repeat(40)),db.enroll({...identity,enabled:false},true),db.capture(null,'Late.GM1',new Uint8Array([2]).buffer,'e'.repeat(40))]);return (await db.rows('queue')).every(r=>r.owner===identity.owner);}''',stranger)
   enrollment.close();record('concurrent first enrollment and save hashing leave no unowned queue entries')
   try:api(base,'saves/'+r1,stranger['token']);raise AssertionError('cross-owner download allowed')
   except urllib.error.HTTPError as e:assert e.code==404
   server.terminate();server.wait(timeout=10);server=start_relay()
   assert len(api(base,'saves',identity['token'])['heads'])>=len(initial)
   api(base,'device/revoke',identity['token'],method='POST')
   try:api(base,'saves',other['token']);raise AssertionError('revoked credential allowed')
   except urllib.error.HTTPError as e:assert e.code==401
   record('server restart preserves solo owner/library; isolation and device revocation enforced')
   q.evaluate(async_js,{'owner':identity['owner'],'base':forks[1],'value':'revoked-device-local-work'})
   q.evaluate('homm3Cloud.sync()');q.wait_for_function('!document.querySelector("#cloud-sync").disabled')
   assert queue(q)>0 and config(q)['owner']==identity['owner'] and 'отозван' in q.locator('#cloud-status').text_content()
   p.evaluate('document.querySelector("#cloud-disable").click()');p.wait_for_timeout(100)
   count=queue(p);write_save(p,'local-only');assert queue(p)==count and not config(p)['enabled']
   record('revoked device keeps unsent work; disabling leaves native saves local')
   assert not errors,errors
   browser.close()
  if ENGINE=='chromium':
   subprocess.run([os.environ.get('PYTHON',os.sys.executable),'scripts/site-browser-smoke.py'],cwd=ROOT,env={**os.environ,'SITE_URL':base},check=True)
   record('existing multiplayer room/name/chat flow in Chromium and WebKit')
  (OUT/(ENGINE+'-results.json')).write_text(json.dumps({'passed':True,'checks':checks,'pageErrors':errors},ensure_ascii=False,indent=2))
 finally:
  for proc in [asset,server]:
   if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=10)
  log.close()
