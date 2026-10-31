(() => {
  const $=id=>document.getElementById(id),token=location.hash.slice(1);
  let snapshot,loading=false,playing=false,rendering=false,timer,loadTimer,files,request,requestId=0,wantedCursor;
  const status=message=>$('replay-status').textContent=message;
  function controls(){
    const position=snapshot?.cursor??0,max=(snapshot?.positions??1)-1;
    document.querySelector('.replay-controls').setAttribute('aria-busy',String(loading));
    $('replay-prev').disabled=loading||!snapshot||position===0;
    $('replay-next').disabled=loading||!snapshot||position===max;
    $('replay-play').disabled=!playing&&(loading||!snapshot||max===0);
    $('replay-branch').disabled=loading||!snapshot?.branchAllowed;
    $('replay-play').textContent=playing?'Пауза':'Смотреть';
    $('replay-position').disabled=loading||!snapshot;
    $('replay-position').max=max;$('replay-position').value=position;
    $('replay-counter').value=snapshot?`${position+1} / ${max+1}`:'—';
    $('replay-position').setAttribute('aria-valuetext',snapshot?`Момент ${position+1} из ${max+1}`:'Запись загружается');
    $('replay-branch').title=snapshot?.branchAllowed?'Продолжить отсюда против компьютера. Исходная партия сохранится.':'Тренировку можно начать с момента, где ход принадлежит вам.';
  }
  function stop(){playing=false;clearTimeout(timer);controls();}
  function fail(message){clearTimeout(loadTimer);rendering=false;loading=false;stop();status(message);$('replay-retry').hidden=false;}
  async function seek(cursor){
    if(loading)return;
    const id=++requestId;wantedCursor=cursor;request?.abort();request=new AbortController();
    loading=true;rendering=false;clearTimeout(timer);clearTimeout(loadTimer);controls();$('replay-retry').hidden=true;status('Открываем выбранный момент…');
    try{
      loadTimer=setTimeout(()=>{request.abort();fail('Загрузка заняла слишком много времени. Можно попробовать ещё раз.');},90000);
      const response=await fetch(`/lobby/reports/${token}/replay${cursor==null?'':'?cursor='+cursor}`,{method:'POST',signal:request.signal});
      const value=await response.json();if(!response.ok||!value.verified)throw Error(value.error||'Запись недоступна');
      if(id!==requestId)return;
      if(!value.state?.state)throw Error('В этом моменте ещё нет игрового состояния. Выберите следующий.');
      snapshot=value;rendering=true;
      // A fresh native renderer cannot retain objects/animations from a later frame.
      $('replay-frame').src='/port/game.html?replay='+Date.now()+'#replay-view';
    }catch(error){if(id===requestId&&error.name!=='AbortError')fail(error.message);}
  }
  window.addEventListener('message',event=>{
    if(event.origin!==location.origin||event.source!==$('replay-frame').contentWindow)return;
    if(event.data?.type==='homm3-replay-ready'&&snapshot&&rendering)event.source.postMessage({type:'homm3-replay-state',snapshot,files,requestId},location.origin);
    if(event.data?.requestId!==requestId||!rendering)return;
    if(event.data?.type==='homm3-replay-started'&&event.data.cursor===snapshot?.cursor){
      clearTimeout(loadTimer);loading=false;controls();status('Проверено · просмотр по моментам, без записи анимаций.'+(!snapshot.branchAllowed?' Для тренировки выберите свой ход.':''));
      if(playing&&snapshot.cursor<snapshot.positions-1)timer=setTimeout(()=>seek(snapshot.cursor+1),2000);else stop();
    }
    if(event.data?.type==='homm3-replay-error')fail(String(event.data.message));
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
    ++requestId;request?.abort();clearTimeout(loadTimer);loading=false;stop();seek(snapshot?.cursor);
  };
  $('replay-choose-files').onclick=()=>$('replay-files').click();
  $('replay-retry').onclick=()=>seek(wantedCursor);
  document.addEventListener('keydown',event=>{if(event.key==='Escape')document.querySelector('.replay-menu').open=false;});
  const issue=new URL('https://github.com/dbarbashov/homm3-web/issues/new?template=bug_report.yml');issue.searchParams.set('environment','Запись партии: '+location.origin+'/lobby/reports/'+token);$('replay-issue').href=issue.href;
  if(!/^[0-9a-f]{32}$/.test(token)){status('Некорректная ссылка на запись.');return;}
  seek();
})();
