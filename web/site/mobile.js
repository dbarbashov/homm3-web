/* The game always fills its viewport; tavern content scrolls independently. */
(() => {
  const $=id=>document.getElementById(id), canvas=$('canvas'), stage=$('game-stage');
  function render() {
    const rect=stage.getBoundingClientRect(), ratio=rect.width/Math.max(1,rect.height);
    const classic=new URLSearchParams(location.search).get('hd')==='0';
    window.homm3HDSize=classic ? {width:800,height:600} : ratio>=4/3
      ? {width:Math.min(2048,Math.round(600*ratio)),height:600}
      : {width:800,height:Math.min(2048,Math.round(800/ratio))};
    canvas.style.width=canvas.width+'px';canvas.style.height=canvas.height+'px';
    const fit=Math.min(rect.width/canvas.width,rect.height/canvas.height);
    canvas.style.transform=`translate(-50%,-50%) scale(${fit})`;
    window.homm3Viewport={immersive:true,fit,width:rect.width,height:rect.height};
  }
  function resize() {
    const vv=window.visualViewport;
    for(const [name,value] of Object.entries({vh:vv?.height||innerHeight,vw:vv?.width||innerWidth,top:vv?.offsetTop||0,left:vv?.offsetLeft||0}))
      document.documentElement.style.setProperty('--game-'+name,value+'px');
    render();
  }
  // Match game::getLocalPlayerGamePos(): remote opponents/AI do not own our UI.
  let themeSnapshot;
  function syncPlayerTheme() {
    const root=document.documentElement,state=window.homm3GameState;
    const screen=window.homm3PortDiagnostics?.screen;
    if(!window.homm3Boot?.running || ['main','new','load','closed'].includes(screen)) {
      delete root.dataset.playerColor;themeSnapshot=state;return;
    }
    if(!state || state===themeSnapshot)return;
    themeSnapshot=state;
    let color=state.localPlayer;
    if(!state.remote && state.humans>1) {
      const slot=window.homm3NetworkState?.turnSlot;
      color=window.homm3HeroStates?.some(p=>p.player===slot && p.human)
        ? slot : window.homm3NetworkState?.aiOwner;
    }
    if(!Number.isInteger(color) || color<0 || color>7)return;
    if(root.dataset.playerColor!==String(color)) {
      root.dataset.playerColor=String(color);
      window.dispatchEvent(new Event('homm3-player-color'));
    }
  }
  // The existing engine snapshot is refreshed every 250 ms; no extra WASM calls.
  setInterval(syncPlayerTheme,250);
  window.addEventListener('homm3-ready',syncPlayerTheme);
  window.addEventListener('homm3-exit',syncPlayerTheme);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncPlayerTheme();});
  function closeControls(){ $('view-actions').hidden=true;$('view-toggle').setAttribute('aria-expanded','false'); }
  function menuPage(settings=false){$('menu-main').hidden=settings;$('menu-settings').hidden=!settings;}
  $('view-toggle').onclick=()=>{
    syncPlayerTheme();const open=$('view-actions').hidden;menuPage();window.homm3Lobby?.close();
    $('view-actions').hidden=!open;$('view-toggle').setAttribute('aria-expanded',String(open));
  };
  $('view-resume').onclick=()=>{closeControls();canvas.focus({preventScroll:true});};
  $('view-settings').onclick=()=>menuPage(true);
  $('settings-back').onclick=()=>menuPage(false);
  let smoothCamera=!matchMedia('(prefers-reduced-motion: reduce)').matches;
  try { const saved=localStorage.getItem('homm3.smoothCamera');if(saved!==null)smoothCamera=saved==='true'; } catch {}
  function setSmoothCamera(value) {
    window.homm3SmoothCamera=value;
    $('smooth-camera').setAttribute('aria-pressed',String(value));
  }
  setSmoothCamera(smoothCamera);
  $('smooth-camera').onclick=()=>{
    setSmoothCamera(!window.homm3SmoothCamera);
    try { localStorage.setItem('homm3.smoothCamera',String(window.homm3SmoothCamera)); } catch {}
  };
  const touch=new window.Homm3Touch(canvas,$('touch-hold-ring'));
  $('fullscreen').onclick=async()=>{
    closeControls();
    try {
      if(document.fullscreenElement)await document.exitFullscreen();
      else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();
    }catch{/* iOS uses the complete available viewport; Home Screen mode hides browser chrome. */}
    resize();
  };
  function exitToHome(){
    if(window.homm3Room)window.homm3Lobby.leaveToHome();
    else location.href='/';
  }
  $('view-exit').onclick=()=>{
    if(window.homm3Boot.running){
      $('exit-description').textContent=window.homm3Room?.serverAuthority
        ? 'Партия сохраняется автоматически. Продолжить её можно в разделе «Мои партии» в этом браузере.'
        : window.homm3Room
          ? 'Вы выйдете из сетевой комнаты. Текущая партия будет прервана.'
          : 'Сначала сохраните партию в игровом меню. Изменения после последнего сохранения могут потеряться.';
      $('exit-dialog').showModal();$('exit-cancel').focus();
    }
    else exitToHome();
  };
  $('exit-cancel').onclick=()=>$('exit-dialog').close();
  $('exit-confirm').onclick=exitToHome;
  document.addEventListener('fullscreenchange',resize);
  $('view-tavern').onclick=()=>{closeControls();window.homm3Lobby?.open();};

  new ResizeObserver(render).observe(stage);
  window.addEventListener('resize',resize);
  window.addEventListener('homm3-resolution',()=>requestAnimationFrame(render));
  window.visualViewport?.addEventListener('resize',resize);
  window.visualViewport?.addEventListener('scroll',resize);
  window.addEventListener('orientationchange',()=>{touch.cancel();setTimeout(resize,100);});
  resize();
})();
