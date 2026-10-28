"""Two independent WASM clients; drive only UI, inspect diagnostics for assertions."""
from pathlib import Path
import json, time, os
from playwright.sync_api import sync_playwright
from browser_audio import use_silent_audio
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8783')
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'test-results'/('fast-native-'+os.environ.get('BROWSER','chromium')+('-iphone' if os.environ.get('VIEW')=='iphone' else '')+('-hd' if os.environ.get('HD')=='1' else ''));OUT.mkdir(parents=True,exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
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
    def click(page,x,y,double=False,raw=False):
        box=page.locator('#canvas').bounding_box();size=page.evaluate('window.homm3HDState||{width:800,height:600,adventure:false}')
        if not raw:
            if not size['adventure']:x+=(size['width']-800)/2;y+=(size['height']-600)/2
            elif x>=600:x+=size['width']-800
        getattr(page.locator('#canvas'),'dblclick' if double else 'click')(position={'x':box['width']*x/size['width'],'y':box['height']*y/size['height']},delay=120)
    try:
        a,b=pages
        for page in pages:
            page.add_init_script("""window.__wrongPlayers=[];setInterval(()=>{const v=window.homm3FastView,s=window.homm3GameState;if(v&&s?.remote===0&&s.localPlayer!==v.localPlayer)__wrongPlayers.push({expected:v.localPlayer,actual:s.localPlayer});},30);window.__fastControls=[];window.addEventListener('homm3-fast-control',e=>window.__fastControls.push(e.detail));window.addEventListener('DOMContentLoaded',()=>{const n=window.homm3FastNative;const c=n.complete;n.complete=function(meta,bytes){window.__fastView=meta.view;window.__fastLast=meta;return c.call(this,meta,bytes);};});""")
        for i,page in enumerate(pages):
            page.goto(BASE+'/port/game.html'+('' if os.environ.get('HD')=='1' else '?hd=0')+'#multiplayer')
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
        click(a,495,555);a.wait_for_timeout(5000);dump('begin')
        assert not any(errors), errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages), logs
        for _ in range(120):
            if all(page.evaluate('!!window.__fastView') for page in pages):break
            for page in pages:
                if page.evaluate('window.homm3GameState?.day===1 && window.homm3HDState?.layers>0 && !window.__fastView'):
                    page.locator('#canvas').press('Enter')
            a.wait_for_timeout(500)
        for page in pages: page.wait_for_function('window.homm3GameState?.day === 1',timeout=60000)
        dump('adventure')
        for page in pages:page.wait_for_function('window.homm3PortDiagnostics?.screen === "adventure"')
        for page in pages: page.wait_for_function('window.__fastView?.absoluteDay===1',timeout=60000)
        dump('fast-started')
        def view(page):return page.evaluate('window.__fastView')
        def settled():
            for page in pages:page.wait_for_function('window.homm3FastState?.canAct && window.homm3FastState.state?.pending===0',timeout=30000)
        initial=[view(page) for page in pages]
        assert [v['localPlayer'] for v in initial]==[0,1]
        assert all(page.locator('#fast-panel').count()==0 for page in pages)
        for page in pages:page.locator('#canvas').press('ArrowDown')
        for page,v in zip(pages,initial):page.wait_for_function('(v)=>window.__fastView.heroes[0].y===v.heroes[0].y+1',arg=v)
        settled();dump('native-both-moved')
        click(a,770,231,True);a.wait_for_function('window.homm3HDState.layers>0');a.wait_for_timeout(700);dump('native-town')
        x=view(b)['heroes'][0]['x'];b.locator('#canvas').press('ArrowRight')
        b.wait_for_function('(x)=>window.__fastView.heroes[0].x===x+1',arg=x)
        settled();dump('guest-moved-host-in-town')
        assert a.evaluate('window.homm3HDState.layers>0')
        gold=view(a)['players'][0]['resources'][6]
        click(a,120,260);a.wait_for_function('window.homm3HDState.layers===2')
        click(a,300,80);a.wait_for_function('window.homm3HDState.layers===3');a.locator('#canvas').press('Enter')
        a.wait_for_function('window.homm3HDState.layers===1');settled()
        assert view(a)['players'][0]['resources'][6]==gold-2500
        dump('native-building')
        assert view(a)['players'][0]['resources'][2]==initial[0]['players'][0]['resources'][2]-5
        click(a,590,270);a.wait_for_function('window.homm3HDState.layers===2')
        dump('native-tavern')
        a.locator('#canvas').press('Enter');a.wait_for_function('window.homm3HDState.layers===1');settled()
        assert len(view(a)['heroes'])==2
        assert view(a)['players'][0]['resources'][6]==gold-5000
        dump('native-hire')
        click(a,40,475);a.wait_for_function('window.homm3HDState.layers===2');a.wait_for_timeout(500)
        a.locator('#canvas').press('m');a.locator('#canvas').press('Enter')
        a.wait_for_function('window.homm3HDState.layers===1');settled()
        assert view(a)['players'][0]['resources'][6]==gold-5500
        dump('native-original-recruitment')
        a.locator('#canvas').press('r');a.wait_for_function('window.homm3HDState.layers===2')
        a.locator('#canvas').press('Enter');a.wait_for_function('window.homm3HDState.layers===1');settled()
        assert view(a)['players'][0]['resources'][6]<gold-5000
        dump('native-recruitment')
        a.locator('#canvas').press('Escape');a.wait_for_function('window.homm3HDState.layers===0')
        # Guest imports snapshots while a real nested native recruitment window is open.
        click(b,770,231,True);b.wait_for_function('window.homm3HDState.layers===1');b.wait_for_timeout(1200)
        b.locator('#canvas').press('r');b.wait_for_function('window.homm3HDState.layers===2')
        click(a,630,230);a.locator('#canvas').press('ArrowDown')
        a.wait_for_function('(v)=>window.__fastView.heroes.find(h=>h.id===v.heroes[0].id).y===v.heroes[0].y+2',arg=initial[0]);settled()
        assert b.evaluate('window.homm3HDState.layers===2')
        dump('host-moves-guest-recruitment-open')
        guestGold=view(b)['players'][1]['resources'][6]
        b.locator('#canvas').press('Enter');b.wait_for_function('window.homm3HDState.layers===1');settled()
        assert view(b)['players'][1]['resources'][6]<guestGold
        b.wait_for_timeout(400);b.locator('#canvas').press('Escape');b.wait_for_function('window.homm3HDState.layers===0')
        dump('native-guest-recruitment')
        click(a,710,372);a.wait_for_timeout(700);a.locator('#canvas').press('Enter')
        a.wait_for_function('window.homm3FastState.ready')
        assert view(a)['absoluteDay']==1
        click(b,630,230);b.locator('#canvas').press('ArrowDown')
        b.wait_for_function('(v)=>window.__fastView.heroes[0].y===v.heroes[0].y+2',arg=initial[1])
        b.wait_for_function('window.homm3FastState.canAct && window.homm3FastState.state.pending===0')
        b.locator('#canvas').press('e');b.wait_for_timeout(700);b.locator('#canvas').press('Enter')
        for page in pages:page.wait_for_function('window.__fastView.absoluteDay===2',timeout=90000)
        settled();dump('native-next-day')
        def mapClick(page,x,y):
            net=page.evaluate('window.homm3NetworkState')
            px=8+32*(x-net['radarX'])+16;py=8+32*(y-net['radarY'])+16
            click(page,px,py,raw=True);page.wait_for_timeout(200);click(page,px,py,raw=True)
        mapClick(b,5,33)
        b.wait_for_function('window.__fastView.heroes[0].x===5 && window.__fastView.heroes[0].y===33');settled()
        dump('native-mouse-route')
        for y in [32,31,30]:
            b.locator('#canvas').press('ArrowUp');b.wait_for_function('(y)=>window.__fastView.heroes[0].y===y',arg=y);settled()
        b.locator('#canvas').press('ArrowLeft');b.wait_for_function('window.__fastView.heroes[0].x===4');settled()
        guestGold=view(b)['players'][1]['resources'][6]
        b.locator('#canvas').press('ArrowUp');b.wait_for_function('window.homm3HDState.layers===1');settled();b.wait_for_timeout(1200)
        assert view(b)['players'][1]['resources'][6]==guestGold
        dump('native-enter-town-no-ai-purchases')
        b.locator('#canvas').press('Escape');b.wait_for_function('window.homm3HDState.layers===0')
        heroId=initial[0]['heroes'][0]['id'];xp=next(h for h in view(a)['heroes'] if h['id']==heroId)['experience']
        mapClick(a,6,8)
        a.wait_for_function('([id,xp])=>window.__fastView.heroes.some(h=>h.id===id && h.experience>xp)',arg=[heroId,xp],timeout=60000);settled()
        dump('native-neutral-battle')
        assert all(not page.evaluate('window.__wrongPlayers.length') for page in pages),[page.evaluate('window.__wrongPlayers') for page in pages]
        assert not any(errors),errors
        assert all(not page.evaluate('window.homm3EngineError') for page in pages),logs
        (OUT/'results.json').write_text(json.dumps({'passed':True,'checks':['native keyboard movement both players','no HTML panel','native town opens','guest moves while host town stays open','native building exact cost','tavern hiring','original creature dialog','quick recruitment','guest imports while nested modal open','native end-turn and day barrier','two-step mouse route','town entry without AI spending','neutral battle from map'],'errors':errors},indent=2))
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
