"""Two independent WASM clients; drive only UI, inspect diagnostics for assertions."""
from pathlib import Path
import json, time, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'test-results'/('fast-runtime-'+os.environ.get('BROWSER','chromium')+('-iphone' if os.environ.get('VIEW')=='iphone' else ''));OUT.mkdir(parents=True,exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
with sync_playwright() as p:
    browser=getattr(p,os.environ.get('BROWSER','chromium')).launch(headless=os.environ.get('HEADFUL')!='1')
    credentials=json.loads(Path(os.environ['SITE_ACCESS_FILE']).read_text()) if os.environ.get('SITE_ACCESS_FILE') else None
    options={'http_credentials':{k:credentials[k] for k in ('username','password')}} if credentials else {}
    display={'viewport':{'width':852,'height':393},'device_scale_factor':3,'is_mobile':True,'has_touch':True} if os.environ.get('VIEW')=='iphone' else {'viewport':{'width':1360,'height':1000}}
    record=Path(os.environ['RECORD_DIR']).resolve() if os.environ.get('RECORD_DIR') else None
    if record:
        record.mkdir(parents=True,exist_ok=True)
        options.update(record_video_dir=str(record/'raw'),record_video_size=display['viewport'])
    contexts=[browser.new_context(**display,**options) for _ in range(2)]
    for context in contexts: use_silent_audio(context)
    pages=[c.new_page() for c in contexts];logs=[[],[]];errors=[[],[]]
    for i,page in enumerate(pages):
        page.on('console',lambda m,i=i:logs[i].append(m.text))
        page.on('pageerror',lambda e,i=i:(errors[i].append(e.stack),print('ERROR',i,e.stack,flush=True)))
    def dump(step):
        result=[]
        for i,page in enumerate(pages):
            page.screenshot(path=str(OUT/f'{step}-{i}.png'),full_page=True)
            result.append(page.evaluate('({room:{title:window.homm3Room?.title,phase:window.homm3Room?.phase},state:window.homm3GameState,net:window.homm3NetworkState,heroes:window.homm3HeroStates,screen:window.homm3PortDiagnostics?.screen,queue:window.homm3Network.peek(),fast:window.__fastView,controls:window.__fastControls,status:document.querySelector("#status").textContent})'))
        if record:a.wait_for_timeout(1300)
        (OUT/f'{step}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(step,[{'player':c['state'].get('localPlayer'),'day':c['state'].get('day'),'hero':c['state'].get('hero'),'xy':[c['state'].get('x'),c['state'].get('y')]} if c.get('state') else c['screen'] for c in result],flush=True)
    try:
        a,b=pages
        for page in pages:
            page.add_init_script("""window.__fastControls=[];window.addEventListener('homm3-fast-control',e=>window.__fastControls.push(e.detail));window.addEventListener('DOMContentLoaded',()=>{const n=window.homm3FastNative;const c=n.complete;n.complete=function(meta,bytes){window.__fastView=meta.view;window.__fastLast=meta;return c.call(this,meta,bytes);};});""")
        for i,page in enumerate(pages):
            page.goto(BASE+'/port/game.html?hd=0#multiplayer')
            page.wait_for_function('!document.querySelector("#start").disabled',timeout=60000)

        title='Browser integration '+str(time.time_ns());a.locator('#show-create').click();a.locator('#player-name').fill('Host');a.locator('#identity-submit').click();a.locator('#room-name').fill(title);a.locator('#fast-game').check();a.locator('#capacity').select_option('2');a.locator('#create-submit').click()
        a.wait_for_function('window.homm3Room?.players.length === 1')
        b.locator('#refresh-rooms').click();b.get_by_role('button',name='Войти: '+title,exact=True).click();b.locator('#player-name').fill('Guest');b.locator('#identity-submit').click()
        a.wait_for_function('window.homm3Room?.players.length === 2')
        b.locator('#room-chat').click();b.locator('#chat-input').fill('Привет! <b>Проверяем чат</b>');b.locator('#chat-send').click()
        a.wait_for_function('document.querySelector("#chat-log").textContent.includes("Привет!")')
        b.locator('#chat-back').click();a.locator('#ready').click();b.locator('#ready').click()
        a.wait_for_function('window.homm3Room?.players.every(p=>p.ready)',timeout=120000)
        dump('lobby-ready')
        a.locator('#launch-room').click()
        for page in pages: page.wait_for_function('window.homm3PortDiagnostics?.screen === "scenarios"',timeout=60000)
        a.wait_for_timeout(5000);dump('scenarios')
        box=a.locator('#canvas').bounding_box();a.locator('#canvas').click(position={'x':box['width']*495/800,'y':box['height']*555/600});a.wait_for_timeout(5000);dump('begin')
        assert not any(errors), errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        for page in pages: page.locator('#canvas').press('Enter')
        for page in pages: page.wait_for_function('window.homm3GameState?.day === 1',timeout=60000)
        dump('adventure')
        for page in pages:page.wait_for_function('window.homm3PortDiagnostics?.screen === "adventure"')
        for page in pages: page.wait_for_function('window.__fastView?.absoluteDay===1',timeout=60000)
        dump('fast-started')
        def view(page):return page.evaluate('window.__fastView')
        def settled():
            for page in pages:
                page.wait_for_function('window.__fastControls.filter(v=>v.type==="fast_state").at(-1)?.pending===0 && !document.querySelector("#fast-end-day").disabled',timeout=30000)
            a.wait_for_timeout(200)
        initial=[view(page) for page in pages]
        assert [v['localPlayer'] for v in initial]==[0,1]
        for page in pages:page.get_by_role('button',name='Юг',exact=True).click()
        for page,v in zip(pages,initial):page.wait_for_function('(v)=>window.__fastView.heroes[0].y===v.heroes[0].y+1',arg=v)
        settled();dump('both-moved')
        for page in pages:assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
        for page,v in zip(pages,initial):
            assert view(page)['heroes'][0]['movement']==v['heroes'][0]['movement']-100
            assert view(page)['absoluteDay']==1
        # Server derives the acting slot; engine rejects an enemy hero even with a valid id.
        b.evaluate('(id)=>window.homm3FastTransport.sendCommand({kind:"move",id,a:4},"wrong-owner",1)',initial[0]['heroes'][0]['id'])
        b.wait_for_function('window.__fastControls.some(v=>v.type==="fast_result"&&v.id==="wrong-owner"&&!v.ok)')
        b.wait_for_function('document.querySelector("#fast-message").textContent.includes("not yours")')
        settled()
        # Recruit two units in the existing city, preserving resource/population totals.
        before=view(a);town=before['towns'][0];creature=town['creatures'][0]
        a.locator('[data-section="recruit"] summary').click()
        a.locator(f'[data-focus-key="count-{town["id"]}-{creature["slot"]}"]').fill('2')
        a.locator(f'[data-focus-key="recruit-{town["id"]}-{creature["slot"]}"]').click()
        a.wait_for_function('(n)=>window.__fastView.towns[0].creatures[0].available===n',arg=creature['available']-2);settled()
        after=view(a)
        assert after['players'][0]['resources']==[x-2*c for x,c in zip(before['players'][0]['resources'],creature['cost'])]
        assert any(stack['type']==creature['type'] and stack['count']>=2 for stack in after['towns'][0]['army'])
        # Hire into a now-free entrance and verify original price and ownership on both clients.
        before=view(a);offer=before['towns'][0]['offers'][0]
        a.locator('[data-section="hire"] summary').click();a.locator(f'[data-focus-key="hire-{offer["id"]}"]').click()
        a.wait_for_function('(id)=>window.__fastView.heroes.some(h=>h.id===id)',arg=offer['id']);settled()
        assert view(a)['players'][0]['resources'][6]==before['players'][0]['resources'][6]-2500
        assert view(b)['players'][0]['resources']==view(a)['players'][0]['resources']
        # A normal paid building, once/day; duplicate/replay cannot charge twice.
        before=view(a);town=before['towns'][0];building=next(x for x in town['buildings'] if x['allowed'] and x['id'] not in [20,26])
        a.locator('[data-section="build"] summary').click();a.locator(f'[data-focus-key="build-{building["id"]}"]').click()
        a.wait_for_function('(cost)=>window.__fastView.players[0].resources[6]===cost',arg=before['players'][0]['resources'][6]-building['cost'][6]);settled()
        assert view(a)['players'][0]['resources']==[x-c for x,c in zip(before['players'][0]['resources'],building['cost'])]
        assert not any(x['allowed'] for x in view(a)['towns'][0]['buildings'])
        dump('economy')
        # Only one's own day ends: guest can still move, no global day advance yet.
        a.locator('#fast-end-day').click();b.wait_for_function('window.__fastControls.some(v=>v.type==="fast_state"&&v.ready.includes(0))')
        y=view(b)['heroes'][0]['y'];b.get_by_role('button',name='Север',exact=True).click();b.wait_for_function('(y)=>window.__fastView.heroes[0].y===y-1',arg=y)
        assert view(a)['absoluteDay']==1
        b.locator('#fast-end-day').click()
        for page in pages:page.wait_for_function('window.__fastView?.absoluteDay===2',timeout=90000)
        settled();dump('fast-day-two')
        # Select original hero and approach the real neutral encounter on the bundled default map.
        hero=initial[0]['heroes'][0];a.locator('#fast-hero').select_option(str(hero['id']))
        a.get_by_role('button',name='Юг',exact=True).click();a.wait_for_function('(id)=>window.__fastView.heroes.find(h=>h.id===id).y===7',arg=hero['id']);settled()
        before=view(a);revision=a.evaluate('window.__fastControls.filter(v=>v.type==="fast_state").at(-1).revision');a.get_by_role('button',name='Юго-запад',exact=True).click()
        a.wait_for_function('(n)=>window.__fastControls.filter(v=>v.type==="fast_state").at(-1)?.revision>n',arg=revision)
        settled();dump('neutral-combat')
        after=view(a);old=next(h for h in before['heroes'] if h['id']==hero['id']);new=next((h for h in after['heroes'] if h['id']==hero['id']),None)
        assert new is None or new['experience']>old['experience'] or new['army']!=old['army'], 'Neutral encounter did not resolve'
        assert view(a)['players']==view(b)['players']
        # Native adventure UI cannot bypass canonical commands in fast mode.
        day=view(a)['absoluteDay'];a.locator('#canvas').press('e');a.wait_for_timeout(500);assert view(a)['absoluteDay']==day
        b.evaluate('window.homm3FastTransport.interrupt("Integration disconnect")');a.wait_for_function('window.homm3Room.phase==="interrupted"');assert a.locator('#fast-end-day').is_disabled()
        assert not any(errors),errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        (OUT/'results.json').write_text(json.dumps({'passed':True,'browser':os.environ.get('BROWSER','chromium'),'display':display,'checks':['two independent real WASM clients','both players move during same day','movement costs preserved','foreign hero rejected','paid creature recruitment and population','paid hero hiring','paid building and one building per day','guest continues after host ends day','shared AI/day barrier','original neutral combat casualties and experience','native mutation input blocked','interruption fails closed'],'errors':errors},indent=2))
    finally:
        try:dump('final-state')
        except:pass
        for i,page in enumerate(pages):
            try:page.screenshot(path=str(OUT/f'last-{i}.png'),full_page=True)
            except:pass
        (OUT/'console.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2));(OUT/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2))
        if record:
            for i,context in enumerate(contexts):
                video=pages[i].video
                context.close()
                video.save_as(str(record/f'player-{i+1}.webm'))
        browser.close()
