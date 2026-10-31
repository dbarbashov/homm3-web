"""Real relay: identity before entry, persisted names, public/private rooms and chat."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
import json, os, time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/network-ux';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
with sync_playwright() as p:
 for engine in ['chromium','webkit']:
  browser=getattr(p,engine).launch(headless=True)
  contexts=[browser.new_context(viewport={'width':1000,'height':700}) for _ in range(2)]
  pages=[];errors=[]
  for context in contexts:
   use_silent_audio(context)
   # Lobby behavior is independent of loading the engine; launch is covered separately.
   context.route('**/port/game.js',lambda route:route.fulfill(body='',content_type='text/javascript'))
   page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));pages.append(page)
  a,b=pages;title='UX '+str(time.time_ns())
  def entry(page,name):
   page.locator('#player-name').fill(name);page.locator('#identity-submit').click()
  a.goto(BASE+'/');assert a.get_by_role('link',name='Одиночная игра',exact=True).count()==1;assert a.get_by_role('link',name='Сетевая игра',exact=True).count()==1
  a.get_by_role('link',name='Сетевая игра',exact=True).click();assert a.locator('#chat-panel').is_hidden();assert a.locator('#identity-form').is_hidden()
  a.locator('#show-create').click();assert a.locator('#identity-form').is_visible();assert a.locator('#create-room').is_hidden()
  a.locator('#identity-cancel').click();assert a.locator('#room-browser').is_visible();a.locator('#show-create').click()
  entry(a,'x'*21);assert '20' in a.locator('#identity-error').inner_text();assert a.locator('#identity-form').is_visible()
  a.screenshot(path=str(OUT/(engine+'-name.png')))
  entry(a,'Изабель');a.locator('#room-name').fill(title);a.locator('#visibility').select_option('private');a.locator('#create-submit').click();a.wait_for_function('window.homm3Room?.players.length===1')
  rid=a.evaluate('window.homm3Room.id');assert all(r['id']!=rid for r in a.request.get(BASE+'/lobby/rooms').json()['rooms'])
  invite=a.locator('#invite-link').input_value()
  b.goto(BASE+'/port/game.html#multiplayer');b.evaluate('window.invitationNavigationProbe=true')
  b.goto(invite);assert b.evaluate('window.invitationNavigationProbe'), 'Invitation must work without reloading the document'
  b.locator('#join-invite').click();assert b.locator('#identity-form').is_visible();entry(b,'Роланд');a.wait_for_function('window.homm3Room?.players.length===2')
  assert a.locator('#ready').text_content()=='Подготовить игру';assert a.locator('#launch-room').is_hidden()
  for page in [a,b]:page.locator('#room-chat').click()
  b.locator('#chat-input').fill('<b>До встречи!</b>');b.locator('#chat-send').click();a.wait_for_function('document.querySelector("#chat-log").textContent.includes("До встречи!")');assert a.locator('#chat-log b').count()==0
  b.locator('#chat-input').fill('🙂'*301);assert len(b.locator('#chat-input').input_value())==300
  for page in [a,b]:page.locator('#chat-back').click()
  b.reload();b.wait_for_function('window.homm3Room?.players.length===2');assert b.locator('#identity-form').is_hidden();assert 'Роланд' in b.locator('#players').inner_text()
  a.locator('#leave-room').click();b.wait_for_function('window.homm3Room?.players.length===1');b.locator('#leave-room').click();b.wait_for_function('!window.homm3Room')
  # Renaming preserves the durable identity and its saved-party memberships.
  old_token=b.evaluate('sessionStorage.getItem("homm3.session")');b.locator('#edit-name').click();entry(b,'Катрин');assert 'Катрин' in b.locator('#nickname-summary').inner_text()
  a.locator('#show-create').click();assert a.locator('#identity-form').is_hidden();a.locator('#visibility').select_option('public');a.locator('#create-submit').click();a.wait_for_function('window.homm3Room?.private===false')
  b.locator('#refresh-rooms').click();b.get_by_role('button',name='Войти: '+title,exact=True).click();a.wait_for_function('window.homm3Room?.players.length===2');assert 'Катрин' in a.locator('#players').inner_text();assert b.evaluate('sessionStorage.getItem("homm3.session")')==old_token
  assert b.evaluate('localStorage.getItem("homm3.nickname")')=='Катрин'
  for w,h in [(1000,700),(734,343),(393,659)]:
   b.set_viewport_size({'width':w,'height':h});b.wait_for_timeout(100)
   assert b.evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight')
   b.screenshot(path=str(OUT/(engine+f'-room-{w}.png')))
  a.locator('#leave-room').click();b.locator('#leave-room').click();b.wait_for_function('!window.homm3Room')
  b.reload();b.locator('#show-create').click();assert b.locator('#create-room').is_visible();assert b.locator('#identity-form').is_hidden()
  # Stored identity failure must not prevent joining during this visit.
  b.locator('#cancel-create').click();b.evaluate('localStorage.clear()');b.reload();b.locator('#edit-name').click();b.evaluate('()=>{Storage.prototype.setItem=()=>{throw new Error("storage blocked")};}');entry(b,'Адела');assert b.locator('#identity-form').is_hidden();assert 'не разрешил' in b.locator('#tavern-error').inner_text()
  assert not errors,errors
  for c in contexts:c.close()
  browser.close();print(engine,'identity, cancel, validation, persistence, rename/session, invites, public join, chat, mobile PASS',flush=True)
(OUT/'lobby-results.json').write_text(json.dumps({'passed':True,'engines':['chromium','webkit'],'errors':errors},ensure_ascii=False,indent=2))
