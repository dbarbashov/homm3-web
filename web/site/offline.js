import {installed,install,exclusive,removeDownloads,resourceEntries} from './offline-store.js';
const $=id=>document.getElementById(id);
const mb=n=>Math.ceil(n/1024/1024)+' МБ';
let source, controller, busy=false, sourceRequest=0;
const supported=isSecureContext && 'serviceWorker' in navigator && 'caches' in window && !!navigator.locks;
function setBusy(value) {
  busy=value;
  $('offline-install').disabled=value || !source || !supported;
  $('game-files').disabled=value; $('offline-videos').disabled=value;
  $('offline-remove').disabled=value;
  $('offline-cancel').hidden=!value;
}
function workerStatus(worker,type='homm3-offline-status') {
  return new Promise((resolve,reject)=>{
    const channel=new MessageChannel();
    const timeout=setTimeout(()=>{channel.port1.close();reject(new Error('Не удалось проверить офлайн-приложение'));},type==='homm3-offline-repair' ? 120000 : 10000);
    channel.port1.onmessage=event=>{clearTimeout(timeout);channel.port1.close();resolve(event.data);};
    worker.postMessage({type},[channel.port2]);
  });
}
async function check() {
  if (!supported) {
    $('offline-heading').textContent='Офлайн-режим недоступен';
    $('offline-status').textContent='Нужен современный браузер и HTTPS (или localhost). В приватном режиме хранение может быть недоступно.';
    return;
  }
  const record=await installed();
  const registration=await navigator.serviceWorker.getRegistration('/');
  const shell=registration?.active ? await workerStatus(registration.active) : null;
  const ready=!!(record?.complete && shell?.complete);
  $('offline-heading').textContent=ready ? 'Готово к игре без интернета' : 'Нужна подготовка';
  $('offline-status').textContent=ready
    ?  `Копия — ${mb(record.bytes+shell.bytes)} · ${record.catalog.maps.length} карт · ${record.catalog.music?.length||0} музыкальных тем${record.videos ? ' · с видео' : ' · без видеороликов'}`
    : record ? 'Копия неполная. Подключитесь к сети или выберите свою папку и повторите подготовку.' : 'Сохраним приложение, карты, кампании, звуки и музыку в этом браузере.';
  $('offline-play').hidden=!ready;
  document.querySelector('.offline-state').dataset.ready=String(ready);
  $('offline-install').textContent=record ? 'Обновить офлайн-копию' : 'Подготовить офлайн';
  $('offline-update').hidden=!registration?.waiting;
  $('offline-update').textContent='Обновление приложения готово. Закройте все вкладки игры и откройте её снова. Текущая версия пока доступна офлайн.';
  const persistent=await navigator.storage?.persisted?.().catch(()=>false);
  $('offline-storage').textContent=persistent
    ? 'Браузер разрешил постоянное хранение. Очистка данных сайта всё равно удалит файлы и сохранения. Сетевые партии требуют интернета.'
    : 'Постоянное хранение не гарантировано: браузер может очистить данные при нехватке места. Очистка данных сайта удаляет и сохранения. Сетевые партии требуют интернета.';
}
async function readSource() {
  const request=++sourceRequest;
  try {
    const next=await window.homm3Assets.source();
    const entries=resourceEntries(next.catalog,false);
    if(request!==sourceRequest)return;
    source=next;
    const size=entries.reduce((sum,e)=>sum+(e.bytes||0),0);
    $('source-hint').textContent=`Доступно: ${next.catalog.maps.length} карт. Архивы — ${mb(size)}, плюс музыка${next.catalog.videos?.length ? ' и выбранные видео' : ''}.`;
  } catch(error) {
    if(request!==sourceRequest)return;
    source=null; $('source-hint').textContent=$('offline-play').hidden
      ? 'Выберите папку своей игры или подключитесь к сети: '+error.message
      : 'Офлайн-копия уже доступна. Чтобы заменить её, выберите папку своей игры или подключитесь к сети.';
  }
  setBusy(busy);
}
async function prepareShell(signal) {
  $('status').textContent='Сохраняем приложение и движок…';
  const registration=await navigator.serviceWorker.register('/offline-worker.js',{scope:'/',updateViaCache:'none'});
  // register() resolves before installation. Observe failure instead of waiting forever on ready.
  const worker=registration.installing || registration.waiting || registration.active;
  if (!worker) throw new Error('Не удалось установить офлайн-приложение');
  await new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>finish(new Error('Подготовка движка заняла слишком долго. Повторите при стабильной сети.')),120000);
    function finish(error){clearTimeout(timeout);worker.removeEventListener('statechange',changed);signal.removeEventListener('abort',aborted);error ? reject(error) : resolve();}
    function aborted(){finish(signal.reason);}
    function changed(){
      if (worker.state==='redundant') finish(new Error('Не удалось сохранить приложение. Проверьте сеть и свободное место.'));
      else if (worker.state==='activated' || (worker.state==='installed' && registration.active)) finish();
    }
    worker.addEventListener('statechange',changed);signal.addEventListener('abort',aborted,{once:true});
    if(signal.aborted)aborted();else changed();
  });
  let status=await workerStatus(registration.active);
  if (!status.complete) status=await workerStatus(registration.active,'homm3-offline-repair');
  if (!status.complete) throw new Error('Копия приложения неполная. Закройте вкладки и повторите подготовку.');
}
$('offline-install').onclick=async()=>{
  if (!source || busy)return;
  // Ask from the user's gesture; denial is displayed but does not prevent installation.
  const persistence=navigator.storage?.persist?.().catch(()=>false);
  controller=new AbortController(); setBusy(true);
  try {
    await exclusive(async()=>{
      await persistence;
      await prepareShell(controller.signal);
      controller.signal.throwIfAborted();
      $('offline-progress').hidden=false;
      await install(source,{videos:$('offline-videos').checked,signal:controller.signal,onProgress:state=>{
        $('offline-progress').max=state.total; $('offline-progress').value=state.completed;
        $('status').textContent=`${state.completed}/${state.total} · ${mb(state.bytes)} · ${state.name}`;
      }});
    });
    $('status').textContent='Готово. Теперь можно закрыть вкладку и открыть игру без сети.';
  } catch(error) {
    $('status').textContent=error.name==='AbortError'
      ? 'Загрузка остановлена. Уже записанные файлы используем при повторе.'
      : error.name==='QuotaExceededError' ? 'Не хватает места в хранилище браузера. Освободите место и повторите. Сохранения не удалены.' : error.message;
  } finally {
    setBusy(false); $('offline-progress').hidden=true;
    await check().catch(error=>$('offline-status').textContent=error.message);
  }
};
$('offline-cancel').onclick=()=>controller?.abort();
$('offline-remove').onclick=async()=>{
  setBusy(true);
  try {await exclusive(removeDownloads);$('status').textContent='Скачанные ресурсы удалены. Сохранения партий оставлены.';await check();}
  catch(error){$('status').textContent=error.message;}
  finally{setBusy(false);}
};
window.addEventListener('homm3-assets-selected',readSource);
window.addEventListener('online',()=>{if(!busy)readSource();});
await check().catch(error=>{$('offline-heading').textContent='Не удалось проверить хранилище';$('offline-status').textContent=error.message;});
await readSource();
