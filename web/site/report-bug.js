/* Only explicitly listed technical facts go into the user-reviewed GitHub form. */
(() => {
  const reportURL = 'https://github.com/dbarbashov/homm3-web/issues/new?template=bug_report.yml';
  function update(link) {
    try {
      const canvas = document.getElementById('canvas');
      const lines = [
        `Page: ${location.pathname === '/port/game.html' ? 'game' : 'home'}`,
        `Browser: ${navigator.userAgent.slice(0, 512)}`,
        `Viewport: ${innerWidth} x ${innerHeight}; pixel ratio: ${devicePixelRatio}`,
        `Touch available: ${navigator.maxTouchPoints > 0 ? 'yes' : 'no'}`
      ];
      if (canvas) lines.push(`Game canvas: ${canvas.width} x ${canvas.height}`);
      if (typeof window.homm3Build === 'string' && /^[a-f0-9]{64}$/.test(window.homm3Build)) {
        lines.push(`Engine/resource fingerprint: ${window.homm3Build}`);
      }
      const url = new URL(reportURL);
      url.searchParams.set('environment', lines.join('\n'));
      link.href = url.href;
    } catch {
      link.href = reportURL;
    }
  }
  for (const link of document.querySelectorAll('[data-report-bug]')) {
    update(link);
    for (const event of ['focus', 'pointerdown', 'click', 'auxclick', 'contextmenu']) {
      link.addEventListener(event, () => update(link));
    }
  }
})();
