/* A replay view has no lobby connection and never submits an engine intent. */
(() => {
  if(location.hash!=='#replay-view')return;
  document.body.classList.add('replay-view');
  let started=false;
  // Parent controls navigation. Native input is disabled for this immutable view.
  for(const type of ['pointerdown','pointerup','mousedown','mouseup','keydown','keyup','touchstart','touchend'])
    window.addEventListener(type,event=>{event.preventDefault();event.stopImmediatePropagation();},{capture:true,passive:false});
  window.addEventListener('message',async event=>{
    if(event.origin!==location.origin || event.source!==parent || event.data?.type!=='homm3-replay-state' || started)return;
    const data=event.data.snapshot;if(!data?.verified || !data.state?.state || !data.startup)return;
    started=true;
    try{
      if(!window.homm3Boot.ready)await new Promise(resolve=>window.addEventListener('homm3-boot-ready',resolve,{once:true}));
      if(event.data.files?.length)await window.homm3Assets.select(event.data.files);
      const choice=data.choice;
      window.homm3AuthorityRestore={...data.startup,actor:data.actor};
      window.homm3Authority.start(()=>{});
      window.homm3Authority.receive({type:'authority_ready',generation:data.match,actor:data.actor,revision:data.revision,phase:data.phase,activeActor:data.activeActor,choiceActor:choice?.actor,choiceKind:choice?.kind});
      window.homm3Authority.receive(data.state);
      if(choice)window.homm3Authority.receive({...choice,type:'authority_choice',generation:data.match});
      else if(data.battle)window.homm3Authority.receive(data.battle);
      await window.homm3Boot.prepare();
      window.homm3Boot.run('authority-restore');
      parent.postMessage({type:'homm3-replay-started',cursor:data.cursor},location.origin);
    }catch(error){parent.postMessage({type:'homm3-replay-error',message:error.message},location.origin);}
  });
  window.addEventListener('homm3-failed',()=>parent.postMessage({type:'homm3-replay-error',message:window.homm3EngineError||'Не удалось открыть запись'},location.origin));
  parent.postMessage({type:'homm3-replay-ready'},location.origin);
})();
