import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../web/site/report-bug.js', import.meta.url), 'utf8');
const base = 'https://github.com/dbarbashov/homm3-web/issues/new?template=bug_report.yml';
function setup({ broken = false } = {}) {
  const events = {},handlers={};
  const link = { href: base, setAttribute(){},removeAttribute(){},addEventListener: (name, handler) => { (handlers[name]??=[]).push(handler);events[name]=(event={button:0})=>Promise.all(handlers[name].map(fn=>fn(event))); } };
  const context = {
    URL, innerWidth: 1200, innerHeight: 800, devicePixelRatio: 2,
    location: { pathname: '/port/game.html' },
    navigator: { userAgent: 'Test browser', maxTouchPoints: 0 },
    document: {
      querySelectorAll: () => [link],
      getElementById: id => {
        assert.equal(id, 'canvas');
        if (broken) throw Error('Canvas unavailable');
        return { width: 800, height: 600 };
      }
    },
    window: { homm3Build: 'a'.repeat(64) }
  };
  for (const key of ['href', 'hash', 'search', 'origin']) {
    Object.defineProperty(context.location, key, { configurable:true,get() { throw Error(`Private URL read: ${key}`); } });
  }
  for (const key of ['localStorage', 'sessionStorage', 'fetch']) {
    Object.defineProperty(context, key, { get() { throw Error(`Unexpected access: ${key}`); } });
  }
  for (const key of ['homm3Room', 'homm3PortDiagnostics', 'Module']) {
    Object.defineProperty(context.window, key, { get() { throw Error(`Private game state read: ${key}`); } });
  }
  runInNewContext(source, context);
  return { link, events, context };
}

test('report contains only allowlisted facts without reading URL secrets, storage or game state', () => {
  const { link } = setup();
  const url = new URL(link.href);
  assert.equal(url.origin, 'https://github.com');
  assert.equal(url.pathname, '/dbarbashov/homm3-web/issues/new');
  assert.deepEqual([...url.searchParams.keys()], ['template', 'environment']);
  const facts = url.searchParams.get('environment');
  assert.match(facts, /Browser: Test browser/);
  assert.match(facts, /Viewport: 1200 x 800/);
  assert.match(facts, /Engine\/resource fingerprint: a{64}/);
  assert.equal(facts.split('\n').length, 6);
});

test('keyboard, touch, middle-click and context menu refresh the report at activation', () => {
  const { link, events, context } = setup();
  context.innerWidth = 390;
  context.navigator.maxTouchPoints = 5;
  context.window.homm3Build = 'private room invitation';
  for (const event of ['focus', 'pointerdown', 'click', 'auxclick', 'contextmenu']) {
    events[event]();
    const facts = new URL(link.href).searchParams.get('environment');
    assert.match(facts, /Viewport: 390 x 800/);
    assert.match(facts, /Touch available: yes/);
    assert.doesNotMatch(facts, /fingerprint|private room/);
  }
});

test('a failed environment read leaves a usable plain GitHub form link', () => {
  const { link, events } = setup({ broken: true });
  events.click();
  assert.equal(link.href, base);
});


test('authoritative report opens the GitHub form with a reproduction link without submitting an issue', async () => {
  const {events,context}=setup();let destination,prevented=false,captures=0;
  const tab={opener:'original',location:{replace:url=>destination=url}};
  Object.defineProperty(context.location,'origin',{value:'https://game.example',configurable:true});
  context.window.open=()=>tab;context.window.homm3Network={serverAuthority:true};
  context.window.homm3Lobby={captureReport:()=>{captures++;return Promise.resolve('/lobby/reports/'+'a'.repeat(32));}};
  await events.click({button:0,preventDefault:()=>prevented=true});
  assert.equal(captures,1);assert.equal(prevented,true);assert.equal(tab.opener,null);
  const issue=new URL(destination);
  assert.equal(issue.origin,'https://github.com');assert.equal(issue.pathname,'/dbarbashov/homm3-web/issues/new');
  assert.equal(issue.searchParams.get('template'),'bug_report.yml');
  assert.equal(issue.searchParams.get('evidence'),'Воспроизведение / Reproduction: https://game.example/lobby/reports/'+'a'.repeat(32));
  assert.match(issue.searchParams.get('environment'),/Browser: Test browser/);
});
test('failed capture retains the user-reviewed GitHub fallback', async () => {
  const {events,context}=setup();let destination;
  context.window.open=()=>({location:{replace:url=>destination=url}});
  context.window.homm3Network={serverAuthority:true};
  context.window.homm3Lobby={captureReport:()=>Promise.reject(Error('Server unavailable'))};
  await events.click({button:0,preventDefault(){}});
  assert.equal(new URL(destination).origin,'https://github.com');
  assert.match(new URL(destination).searchParams.get('evidence'),/Server unavailable/);
});
