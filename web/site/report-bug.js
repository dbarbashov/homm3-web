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
    link.addEventListener('click', async event => {
      if(event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !window.homm3Network?.serverAuthority)return;
      const request=window.homm3Lobby?.captureReport();if(!request)return;
      event.preventDefault();
      const tab=window.open('about:blank','_blank');if(tab)tab.opener=null;
      link.setAttribute('aria-busy','true');
      try{const path=await request;if(!/^\/lobby\/reports\/[a-f0-9]{32}$/.test(path))throw Error('Invalid report URL');
        update(link);
        const issue=new URL(link.href);
        issue.searchParams.set('evidence','Воспроизведение / Reproduction: '+new URL(path,location.origin).href);
        if(tab)tab.location.replace(issue.href);else location.assign(issue.href);
      }catch(error){
        update(link);const fallback=new URL(link.href);fallback.searchParams.set('evidence','Автоматическая запись воспроизведения недоступна: '+String(error.message).slice(0,200));
        if(tab)tab.location.replace(fallback.href);else location.assign(fallback.href);
      }finally{link.removeAttribute('aria-busy');}
    });
    for (const event of ['focus', 'pointerdown', 'click', 'auxclick', 'contextmenu']) {
      link.addEventListener(event, () => update(link));
    }
  }
})();
