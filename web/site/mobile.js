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
  function closeControls(){ $('view-actions').hidden=true;$('view-toggle').setAttribute('aria-expanded','false'); }
  $('view-toggle').onclick=()=>{const open=$('view-actions').hidden;$('view-actions').hidden=!open;$('view-toggle').setAttribute('aria-expanded',String(open));};
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
  $('view-exit').onclick=()=>{location.href='/';};
  document.addEventListener('fullscreenchange',resize);
  $('view-tavern').onclick=()=>{closeControls();$('open-tavern').click();};
  for(const button of document.querySelectorAll('[data-game-key]'))button.onclick=()=>{
    const key=button.dataset.gameKey,keyCode={Enter:13,Escape:27,e:69,r:82,b:66,g:71,F10:121,Space:32}[key];
    if(!window.homm3Boot.running)return;
    closeControls();canvas.focus({preventScroll:true});
    for(const type of ['keydown','keyup'])canvas.dispatchEvent(new KeyboardEvent(type,{key,code:key.length===1?'Key'+key.toUpperCase():key,keyCode,which:keyCode,bubbles:true,cancelable:true}));
  };
  for(const button of document.querySelectorAll('[data-army-action]'))button.onclick=()=>{
    const action=Number(button.dataset.armyAction);
    window.homm3ArmyAction=window.homm3ArmyAction===action?0:action;
    for(const item of document.querySelectorAll('[data-army-action]'))item.setAttribute('aria-pressed',String(Number(item.dataset.armyAction)===window.homm3ArmyAction));
    $('view-toggle').textContent=window.homm3ArmyAction?'Отряды: '+button.textContent:'Меню';
    closeControls();
  };

  new ResizeObserver(render).observe(stage);
  window.addEventListener('resize',resize);
  window.addEventListener('homm3-resolution',()=>requestAnimationFrame(render));
  window.visualViewport?.addEventListener('resize',resize);
  window.visualViewport?.addEventListener('scroll',resize);
  window.addEventListener('orientationchange',()=>{touch.cancel();setTimeout(resize,100);});
  resize();
})();
