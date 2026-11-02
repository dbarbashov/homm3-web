"""Real service-worker rollback/staging checks against an isolated static export."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import functools, http.server, json, shutil, subprocess, tempfile, threading
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/offline'
class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if 'If-Modified-Since' in self.headers:del self.headers['If-Modified-Since']
  super().do_GET()
 def end_headers(self):
  self.send_header('Cache-Control','no-store');super().end_headers()
with tempfile.TemporaryDirectory(prefix='offline-update-',dir=ROOT/'.local') as temporary:
 root=Path(temporary);(root/'web').mkdir();(root/'lib').mkdir()
 files=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {shellFiles} from './lib/offline-shell.mjs';console.log(JSON.stringify(shellFiles));"],cwd=ROOT))
 for name in files:
  target=root/'web'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'web'/name,target)
 shutil.copyfile(ROOT/'lib/offline-worker.js',root/'lib/offline-worker.js')
 original=(root/'web/index.html').read_text()
 def build(label):
  (root/'web/index.html').write_text(original+f'<!-- offline test {label} -->')
  subprocess.run(['node','--input-type=module','-e',"import {writeFile} from 'node:fs/promises';import {buildOfflineWorker} from './lib/offline-shell.mjs';await writeFile(process.argv[1]+'/web/offline-worker.js',await buildOfflineWorker(process.argv[1]));",str(root)],cwd=ROOT,check=True)
 build('A')
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root/'web')))
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f'http://127.0.0.1:{server.server_port}';errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True);context=browser.new_context();use_silent_audio(context)
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base+'/')
  page.evaluate("async()=>{await navigator.serviceWorker.register('/offline-worker.js',{updateViaCache:'none'});await navigator.serviceWorker.ready;}")
  page.reload();assert page.evaluate('!!navigator.serviceWorker.controller')
  first=page.evaluate("async()=>{const keys=await caches.keys();return keys.find(k=>k.startsWith('homm3-shell-'));}")
  # Served HTML changed between manifest generation and fetch: this update must fail.
  build('B');(root/'web/index.html').write_text('corrupt partial deployment')
  page.evaluate("""async()=>{window.updateState='';const r=await navigator.serviceWorker.getRegistration('/');r.addEventListener('updatefound',()=>{const w=r.installing;w.addEventListener('statechange',()=>window.updateState=w.state);window.updateState=w.state;},{once:true});await r.update();}""")
  page.wait_for_function("window.updateState==='redundant'")
  assert 'offline test A' in page.evaluate("async()=>await (await fetch('/')).text()")
  assert page.evaluate("async()=>!(await navigator.serviceWorker.getRegistration('/')).waiting")
  print('failed update preserves working shell PASS',flush=True)
  (root/'web/index.html').write_text(original+'<!-- offline test B -->')
  page.evaluate("async()=>await (await navigator.serviceWorker.getRegistration('/')).update()")
  page.wait_for_function("async()=>!!(await navigator.serviceWorker.getRegistration('/')).waiting")
  other=context.new_page();other.goto(base+'/')
  assert 'offline test A' in other.evaluate("async()=>await (await fetch('/')).text()")
  assert 'offline test A' in page.evaluate("async()=>await (await fetch('/')).text()")
  other.close();page.close()
  # Observe activation from an unrelated blank document, without creating a new controlled client.
  blank=context.new_page();blank.wait_for_timeout(700)
  page=context.new_page();page.goto(base+'/')
  page.wait_for_function("async()=>!(await navigator.serviceWorker.getRegistration('/')).waiting")
  page.reload()
  assert 'offline test B' in page.evaluate("async()=>await (await fetch('/')).text()")
  assert not page.evaluate('(key)=>caches.has(key)',first)
  print('update waits for all old tabs; new shell activates together PASS',flush=True)
  # Simulate an evicted entry: retrieve only matching bytes, never unrelated latest runtime.
  page.evaluate("async()=>{const key=(await caches.keys()).find(k=>k.startsWith('homm3-shell-'));await (await caches.open(key)).delete('/site/offline.css');}")
  assert page.evaluate("async()=>(await fetch('/site/offline.css')).ok")
  assert not errors,errors
  OUT.mkdir(parents=True,exist_ok=True)
  (OUT/'update-results.json').write_text(json.dumps({'passed':True,'failedUpdatePreserved':True,'waitsForAllTabs':True,'atomicActivation':True,'evictionRepair':True,'errors':errors},indent=2))
  browser.close()
 server.shutdown();server.server_close()
