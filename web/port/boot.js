/* Browser host: transport whole LODs into MEMFS; all decoding/UI run in C++. */
const canvas = document.querySelector('#canvas');
const start = document.querySelector('#start');
const status = document.querySelector('#status');
const progress = document.querySelector('#progress');
const fullGame = location.pathname.endsWith('/game.html');
let catalog;
let archives;
let exited = false;
let prepared = false, preparing = null, runtimeReady = false, running = false, filesystemCreated = false;
function failEngine(message) {
  if (window.homm3EngineError) return;
  window.homm3EngineError = String(message || 'Неизвестная ошибка движка');
  exited = true;
  if (window.homm3PortDiagnostics) window.homm3PortDiagnostics.ready = false;
  document.querySelector('#launch-cover')?.removeAttribute('hidden');
  document.querySelector('#source-hint').textContent = 'Не удалось продолжить игру. Перезагрузите страницу для новой попытки.';
  for (const node of document.querySelectorAll('#launch-cover .file-label, #launch-cover .notice')) node.hidden = true;
  progress.hidden = true;
  status.textContent = window.homm3EngineError;
  status.setAttribute('role', 'alert');
  start.hidden = false; start.disabled = false; start.textContent = 'Перезагрузить страницу';
  window.homm3Music?.stop();
  window.dispatchEvent(new Event('homm3-failed'));
  start.focus();
}
window.addEventListener('homm3-engine-error', event => failEngine(event.detail));
const assetFetch = (...args) => (window.homm3Assets?.fetch || fetch)(...args);
async function refreshCatalog() {
  const response = await assetFetch('/api/catalog');
  if (!response.ok) throw new Error('Сервер ресурсов недоступен');
  catalog = await response.json();
  window.homm3VideoNames = new Set((catalog.videos || []).map(n=>n.toLowerCase()));
  window.homm3Music?.configure(catalog.music || []);
  if (!catalog.ready) {
    const hint = document.querySelector('#source-hint');
    if (hint) hint.textContent = 'Выберите папку Heroes III Complete с Data, Maps и Mp3.';
    throw new Error(catalog.error || 'Выберите папку своей игры');
  }
  archives = [...catalog.archives, ...(fullGame ? catalog.soundArchives || [] : [])];
  const size = archives.reduce((sum, a) => sum + a.bytes, 0);
  start.textContent = 'Играть'; start.disabled = false;
  status.textContent = `Ресурсы готовы · ${Math.round(size / 1024 / 1024)} МБ`;
  const hint = document.querySelector('#source-hint');
  if (hint) hint.textContent = 'Ваша установка найдена. Можно отправляться в путь.';
}
window.addEventListener('homm3-assets-selected', () => { if(runtimeReady && !prepared && !preparing) refreshCatalog().catch(e => status.textContent = e.message); });
window.Module = {
  canvas,
  locateFile: name => `/port/${name}`,
  print: text => console.log('[engine]', text),
  printErr: text => console.error('[engine]', text),
  onAbort: text => failEngine(`Ошибка движка: ${text}`),
  onRuntimeInitialized: async () => {
    try {
      runtimeReady = true;
      window.dispatchEvent(new Event('homm3-boot-ready'));
      await refreshCatalog();
      if(new URLSearchParams(location.search).get('play')==='1' && !location.hash) {
        await prepare(); runGame();
      }
    } catch (error) { status.textContent = error.message; start.textContent = 'Архивы недоступны'; }
  }
};
async function prepare() {
  if (prepared) return;
  if (preparing) return preparing;
  preparing = (async () => {
    if (!runtimeReady) throw new Error('Движок ещё загружается');
    window.homm3Music?.unlock();
    await refreshCatalog();
    start.disabled = true; start.textContent = 'Загрузка архивов…'; progress.hidden = false;
    const fingerprints = [];
    const { digest } = await import('/port/sha256.js');
    const dataDir = fullGame ? '/runtime/data' : '/data';
    filesystemCreated = true;
    if (fullGame) {
      Module.FS.mkdir('/runtime');
      try {
        const prefs = localStorage.getItem('homm3.preferences.v1');
        if (prefs && prefs.length <= 1024 * 1024) Module.FS.writeFile('/runtime/preferences.dat', prefs);
      } catch (error) { window.dispatchEvent(new CustomEvent('homm3-storage-error', {detail: String(error)})); }
      for (const name of ['maps','games','random_maps']) Module.FS.mkdir('/runtime/' + name);
    }
    Module.FS.mkdir(dataDir);
    if (fullGame) {
      Module.FS.mount(Module.IDBFS, {}, '/runtime/games');
      await new Promise((resolve, reject) => Module.FS.syncfs(true, error => error ? reject(error) : resolve()));
    }
    const total = archives.reduce((n, a) => n + a.bytes, 0); let loaded = 0;
    for (const archive of archives) {
      status.textContent = `Чтение ${archive.name}`;
      const response = await assetFetch(`/api/archive?name=${encodeURIComponent(archive.name)}`);
      if (!response.ok) throw new Error(`Не удалось прочитать ${archive.name}`);
      const data = new Uint8Array(archive.bytes), reader = response.body.getReader(); let offset = 0;
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        if (offset + value.length > data.length) throw new Error('Размер архива изменился');
        data.set(value, offset); offset += value.length; loaded += value.length;
        progress.value = loaded / total;
      }
      if (offset !== archive.bytes) throw new Error(`Архив ${archive.name} прочитан не полностью`);
      fingerprints.push(archive.name.toLowerCase() + ":" + await digest(data));
      Module.FS.writeFile(`${dataDir}/${archive.name.toLowerCase()}`, data, { canOwn: true });
    }
    status.textContent = 'Запуск исходного C++…';
    if (fullGame) {
      const scenarios = [...catalog.maps,...(catalog.campaigns || [])];
      let next = 0;
      await Promise.all(Array.from({length: 4}, async () => {
        while (next < scenarios.length) {
          const name = scenarios[next++];
          status.textContent = 'Загрузка сценариев: ' + next + '/' + scenarios.length;
          const response = await assetFetch('/api/scenario?name=' + encodeURIComponent(name));
          if (!response.ok) throw new Error('Не удалось прочитать сценарий ' + name);
          Module.FS.writeFile('/runtime/maps/' + name, new Uint8Array(await response.arrayBuffer()));
        }
      }));
    }
    const wasm = await fetch(fullGame ? '/port/game.wasm' : '/port/homm3.wasm');
    if (!wasm.ok) throw new Error('Не удалось проверить версию движка');
    fingerprints.push(await digest(await wasm.arrayBuffer()));
    window.homm3Build = await digest(new TextEncoder().encode(fingerprints.sort().join('\n')));
    prepared = true; progress.hidden = true; status.textContent = 'Готово к запуску';
  })();
  try { await preparing; } catch(error) {
    if (!filesystemCreated) preparing = null;
    else error.message = error.message.includes('Перезагрузите страницу') ? error.message : error.message + '. Перезагрузите страницу для повтора.';
    status.textContent = error.message; throw error;
  }
}
// Keep this name distinct from the generated Emscripten global run().
function runGame(network=false) {
  if (!prepared || running) return;
  running = true; window.dispatchEvent(new Event('homm3-running')); document.querySelector('#launch-cover')?.setAttribute('hidden','');
  Module.callMain(fullGame ? ['/runtime', ...(['authority-restore','authority-setup'].includes(network) ? ['--'+network] : network ? ['--network'] : [])] : ['/data/']);
}
window.homm3Boot = { prepare, run: runGame, fail: failEngine, get running() { return running; }, get ready() { return runtimeReady; } };
start.addEventListener('click', async () => {
  if (exited) { location.reload(); return; }
  try { await prepare(); runGame(); } catch(error) { status.textContent = error.message; start.textContent = 'Перезагрузите страницу для повтора'; }
});
window.addEventListener('homm3-ready', () => {
  if (window.homm3EngineError) return;
  start.hidden = true; progress.hidden = true;
  const labels = { main: 'Главное меню', new: 'Новая игра', load: 'Загрузить игру', confirm: 'Подтверждение', message: 'Сообщение', scenarios: 'Выбор сценария / сохранения', adventure: 'Карта приключений', combat: 'Бой', 'combat-results': 'Результат боя' };
  const d = window.homm3PortDiagnostics;
  status.textContent = `${labels[d.screen] || d.screen} · мышь и горячие клавиши · правая кнопка: подсказка`;
  document.querySelector('#hash').textContent = `Кадр ${d.framebufferFNV1a}`;
  if (!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) canvas.focus();
});
window.addEventListener('homm3-command', event => {
  window.homm3PortDiagnostics.commands.push(event.detail);
});
window.addEventListener('homm3-exit', () => {
  if (window.homm3EngineError) return;
  exited = true;
  if (window.homm3PortDiagnostics) { window.homm3PortDiagnostics.ready = false; window.homm3PortDiagnostics.screen = 'closed'; }
  status.textContent = 'Клиент закрыт';
  document.querySelector('#launch-cover')?.removeAttribute('hidden');
  start.hidden = false; start.disabled = false; start.textContent = 'Запустить снова';
});
canvas.addEventListener('contextmenu', e => e.preventDefault());

let saveQueue = Promise.resolve();
window.addEventListener('homm3-save', event => {
  saveQueue = saveQueue.then(() => new Promise((resolve, reject) => {
    Module.FS.syncfs(false, error => error ? reject(error) : resolve());
  })).then(() => {
    window.homm3LastSave = event.detail;
    window.dispatchEvent(new Event('homm3-save-persisted'));
  }).catch(error => { status.textContent = 'Не удалось записать сохранение в браузер: ' + error.message; });
});

window.addEventListener('homm3-storage-error', event => {
  document.querySelector('#command').textContent = 'Не удалось сохранить настройки: ' + event.detail;
});
