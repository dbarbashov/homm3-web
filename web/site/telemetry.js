/* Aggregate usage only: fixed names, no URL parameters, chat, identities or saves. */
(() => {
  'use strict';
  const names = new Set(['/', '/port/game.html', 'play-single', 'play-network', 'engine-start',
    'adventure', 'combat', 'campaign', 'save', 'network-menu', 'fullscreen', 'smooth-camera',
    'github', 'report-bug', 'client-error']);
  const sent = new Set();
  let count = 0;
  function disabled() {
    if (location.hostname !== 'homm3.xyz' || navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return true;
    try { return localStorage.getItem('homm3.telemetry.off') === 'true'; } catch { return true; }
  }
  function track(name) {
    if (disabled() || !names.has(name) || sent.has(name) || count >= 24) return;
    sent.add(name); count++;
    const width = Number(window.screen?.width) || 0;
    const query = new URLSearchParams({p: name, e: String(!name.startsWith('/')),
      s: String(width < 600 ? 480 : width < 1200 ? 1024 : 1920), b: navigator.webdriver ? '153' : '0'});
    // No retries, polling, persistent ID or fallback image. Analytics never blocks play.
    try { navigator.sendBeacon?.('/telemetry?' + query); } catch {}
  }
  function pageView() {
    if (document.visibilityState === 'hidden') return;
    track(location.pathname === '/index.html' ? '/' : location.pathname);
  }
  pageView();
  document.addEventListener('visibilitychange', pageView);
  document.addEventListener('click', event => {
    const node = event.target.closest?.('a,button');
    if (!node) return;
    const byId = {'open-tavern':'network-menu','view-tavern':'network-menu',fullscreen:'fullscreen','smooth-camera':'smooth-camera'};
    let name = byId[node.id];
    if (node.hasAttribute('data-report-bug')) name = 'report-bug';
    if (node.classList.contains('github-link')) name = 'github';
    // Classify only these two literal links; never transmit href/query/hash.
    if (node.getAttribute('href') === '/port/game.html?play=1') name = 'play-single';
    if (node.getAttribute('href') === '/port/game.html#multiplayer') name = 'play-network';
    if (name) track(name);
  });
  window.addEventListener('homm3-running', () => track('engine-start'));
  window.addEventListener('homm3-save-persisted', () => track('save'));
  window.addEventListener('homm3-ready', () => {
    const screen = window.homm3PortDiagnostics?.screen;
    if (screen === 'adventure' || screen === 'combat') track(screen);
    if (window.homm3CampaignState?.active) track('campaign');
  });
  window.addEventListener('error', () => track('client-error'));
  const choice = document.getElementById('telemetry-opt-out');
  if (choice) {
    choice.checked = disabled();
    choice.addEventListener('change', () => {
      try { localStorage.setItem('homm3.telemetry.off', String(choice.checked)); } catch {}
    });
  }
})();
