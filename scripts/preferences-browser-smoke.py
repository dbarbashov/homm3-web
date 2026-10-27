"""Change the original options UI, reload, and inspect the restored C++ values."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'test-results/preferences';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True);context=b.new_context(viewport={'width':1100,'height':1100});page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(e.stack));c=page.locator('#canvas')
 def screen(name):page.wait_for_function('(s)=>window.homm3PortDiagnostics?.screen===s',arg=name,timeout=90000)
 def start():page.locator('#start').click(timeout=90000);screen('main');page.wait_for_function('window.homm3Settings')
 def click(x,y):
  box=c.bounding_box();c.click(position={'x':x*box['width']/800,'y':y*box['height']/600},delay=80);page.wait_for_timeout(350)
 try:
  page.goto(os.environ.get('HOMM3_TEST_URL','http://127.0.0.1:8783/port/game.html'));page.evaluate("localStorage.setItem('homm3.music.muted','true')");page.reload();start();assert page.locator('#music-toggle').count()==0
  page.wait_for_function('window.homm3Music.samplePeak()>0.001')
  page.evaluate('window.sfxPeak=0;window.sfxMonitor=setInterval(()=>window.sfxPeak=Math.max(window.sfxPeak,window.homm3Sfx.samplePeak()),5)')
  click(650,70);screen('new');page.wait_for_timeout(300)
  peak=page.evaluate('window.sfxPeak');assert peak>0.001,peak
  c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure')
  c.press('o');page.wait_for_timeout(700);c.screenshot(path=str(out/'options-before.png'))
  # Original window origin159,56; original slider slots19px apart.
  click(195,430);page.wait_for_function('window.homm3Settings.music===0')
  click(195+19*2,430);page.wait_for_function('window.homm3Settings.music===2')
  click(195,495);page.wait_for_function('window.homm3Settings.sound===0')
  click(195+19*7,495);page.wait_for_function('window.homm3Settings.sound===7')
  click(350,148);click(422,122) # Hero speed4 and show route toggle.
  c.screenshot(path=str(out/'options-changed.png'))
  expected=page.evaluate('window.homm3Settings');assert expected['heroSpeed']==4,expected
  click(560,492);page.wait_for_timeout(700)
  assert page.evaluate('!!localStorage.getItem("homm3.preferences.v1")')
  page.reload();start();page.wait_for_timeout(500)
  actual=page.evaluate('window.homm3Settings');assert actual==expected,(actual,expected)
  page.wait_for_function('window.homm3Music.samplePeak()>0.001')
  assert abs(page.evaluate('window.homm3Music.state.volume')-.3)<.001
  c.press('n');screen('new');c.press('s');screen('scenarios');c.press('b');page.wait_for_timeout(4000);c.press('Enter');screen('adventure')
  c.press('o');page.wait_for_timeout(700);c.screenshot(path=str(out/'options-restored.png'))
  assert page.evaluate('window.homm3Settings')==expected
  assert not errors,errors
  (out/'results.json').write_text(json.dumps({'passed':True,'url':page.url,'secureContext':page.evaluate('isSecureContext'),'buildFingerprint':page.evaluate('window.homm3Build'),'buttonOutputPeak':peak,'beforeReload':expected,'afterReload':actual,'obsoleteOuterMuteRemoved':True,'zeroVolumeCanBeReenabled':True,'errors':errors},indent=2))
 finally:
  print('FINAL',page.evaluate('({settings:window.homm3Settings,sfx:window.homm3Sfx?.stats.errors,errors:window.homm3Music?.state.error})'))
  c.screenshot(path=str(out/'last.png'));(out/'errors.json').write_text(json.dumps(errors));context.close();b.close()
