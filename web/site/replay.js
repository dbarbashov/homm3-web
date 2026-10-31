(() => {
  const $=id=>document.getElementById(id),token=location.hash.slice(1);
  let snapshot,loading=false,playing=false,timer,loadTimer,files;
  const status=message=>$('replay-status').textContent=message;
  function controls(){
    const position=snapshot?.cursor??0,max=(snapshot?.positions??1)-1;
    $('replay-files').disabled=loading;
    $('replay-prev').disabled=loading||!snapshot||position===0;
    $('replay-next').disabled=loading||!snapshot||position===max;
    $('replay-play').disabled=loading||!snapshot||max===0;
    $('replay-branch').disabled=loading||!snapshot?.branchAllowed;
    $('replay-play').textContent=playing?'Пауза':'Смотреть';
    $('replay-position').disabled=loading||!snapshot;
    $('replay-position').max=max;$('replay-position').value=position;
    $('replay-counter').value=snapshot?`${position+1} / ${max+1}`:'—';
  }
  function stop(){playing=false;clearTimeout(timer);controls();}
  async function seek(cursor){
    if(loading)return;loading=true;clearTimeout(timer);clearTimeout(loadTimer);controls();status('Восстанавливаем выбранный момент и сверяем историю…');
    try{
      const response=await fetch(`/lobby/reports/${token}/replay${cursor==null?'':'?cursor='+cursor}`,{method:'POST',signal:AbortSignal.timeout(90000)});
      const value=await response.json();if(!response.ok||!value.verified)throw Error(value.error||'Запись недоступна');
      if(!value.state?.state)throw Error('В этом моменте ещё нет игрового состояния. Выберите следующий.');
      snapshot=value;
      loadTimer=setTimeout(()=>{loading=false;stop();status('Игра не открылась вовремя. Обновите страницу, чтобы повторить загрузку.');},90000);
      // A fresh native renderer cannot retain objects/animations from a later frame.
      $('replay-frame').src='/port/game.html?replay='+Date.now()+'#replay-view';
    }catch(error){loading=false;stop();status(error.message);}
  }
  window.addEventListener('message',event=>{
    if(event.origin!==location.origin||event.source!==$('replay-frame').contentWindow)return;
    if(event.data?.type==='homm3-replay-ready'&&snapshot)event.source.postMessage({type:'homm3-replay-state',snapshot,files},location.origin);
    if(event.data?.type==='homm3-replay-started'&&event.data.cursor===snapshot?.cursor){
      clearTimeout(loadTimer);loading=false;controls();status(`Проверено · ревизия ${snapshot.revision} · шаги вашей партии. Анимации между моментами не записаны.`);
      if(playing&&snapshot.cursor<snapshot.positions-1)timer=setTimeout(()=>seek(snapshot.cursor+1),2000);else stop();
    }
    if(event.data?.type==='homm3-replay-error'){clearTimeout(loadTimer);loading=false;stop();status(String(event.data.message));}
  });
  $('replay-prev').onclick=()=>{stop();seek(snapshot.cursor-1);};
  $('replay-next').onclick=()=>{stop();seek(snapshot.cursor+1);};
  $('replay-position').onchange=()=>{const cursor=Number($('replay-position').value);stop();seek(cursor);};
  $('replay-play').onclick=()=>{if(playing){stop();return;}playing=true;seek(snapshot.cursor===snapshot.positions-1?0:snapshot.cursor+1);};
  $('replay-branch').onclick=async()=>{
    if(!snapshot?.branchAllowed||loading)return;
    stop();loading=true;controls();status('Создаём отдельную тренировку. Остальными сторонами будет управлять ИИ…');
    try{
      const credential=sessionStorage.getItem('homm3.session')||localStorage.getItem('homm3.session');
      if(!credential)throw Error('Откройте запись в браузере, где вы играли, или сначала перенесите доступ по коду.');
      const response=await fetch(`/lobby/reports/${token}/branch`,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+credential},body:JSON.stringify({cursor:snapshot.cursor}),signal:AbortSignal.timeout(90000)});
      const value=await response.json();if(!response.ok||!value.url)throw Error(value.error||'Не удалось создать тренировку');
      location.href=value.url;
    }catch(error){loading=false;controls();status(error.message);}
  };
  $('replay-files').onchange=()=>{
    files=Array.from($('replay-files').files);
    if(!files.length)return;
    clearTimeout(loadTimer);loading=false;stop();seek(snapshot?.cursor);
  };
  const issue=new URL('https://github.com/dbarbashov/homm3-web/issues/new?template=bug_report.yml');issue.searchParams.set('environment','Запись партии: '+location.origin+'/lobby/reports/'+token);$('replay-issue').href=issue.href;
  if(!/^[0-9a-f]{32}$/.test(token)){status('Некорректная ссылка на запись.');return;}
  seek();
})();
