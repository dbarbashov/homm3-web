/* An explicitly selected installation stays in browser memory; never uploaded. */
(() => {
  let files = null, videoEntries = new Map();
  const nativeFetch = window.fetch.bind(window);
  const required = ['h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod'];
  const input = document.querySelector('#game-files');
  let remoteConfig;
  async function remote() {
    if (!remoteConfig) remoteConfig = (async () => {
      const response = await nativeFetch('/site/resources.json', {cache:'no-store'});
      if (response.status === 404) return null;
      if (!response.ok) throw new Error('Не удалось получить настройки ресурсов');
      const config = await response.json();
      if (!config.baseUrl) return null;
      const base = new URL(config.baseUrl);
      if (base.protocol !== 'https:' && !['localhost','127.0.0.1','[::1]'].includes(base.hostname)) throw new Error('Ресурсам требуется HTTPS');
      if (!base.pathname.endsWith('/')) throw new Error('Некорректный адрес ресурсов');
      return {...config, baseUrl:base.href, fileLookup:new Map(Object.entries(config.files).map(([name,file])=>[name.toLowerCase(),file]))};
    })();
    return remoteConfig;
  }
  window.homm3Assets = {
    async select(list) {
      const selected = new Map();
      for (const file of list) {
        const name = file.name.toLowerCase();
        if (/\.(lod|snd|h3m|h3c|mp3|vid)$/i.test(name)) {
          if (selected.has(name)) throw new Error('Несколько файлов с именем ' + file.name + '. Выберите одну установку.');
          selected.set(name, file);
        }
      }
      for (const name of [...required,'heroes3.snd']) if (!selected.has(name)) throw new Error('В выбранной папке не найден ' + name);
      const videos = new Map();
      const {indexVideoBlob} = await import('/site/video-archive.js');
      for (const name of ['heroes3.vid','video.vid','h3ab_ahd.vid']) {
        const archive = selected.get(name); if (!archive) continue;
        for (const entry of await indexVideoBlob(archive)) videos.set(entry.name.toLowerCase(),{...entry,archive});
      }
      videoEntries = videos;
      files = selected;
      window.dispatchEvent(new Event('homm3-assets-selected'));
    },
    async fetch(url, options) {
      const u = new URL(url, location.href);
      if (!files && u.origin === location.origin && ['/api/catalog','/api/archive','/api/scenario','/api/music','/api/video'].includes(u.pathname)) {
        const config = await remote();
        if (config) {
          if (u.pathname === '/api/catalog') return Response.json({...config.catalog,ready:true,remote:true});
          const name = u.searchParams.get('name') || '';
          const file = config.fileLookup.get(name.toLowerCase());
          if (!file) return new Response('Файл не найден',{status:404});
          if (!/^[a-f0-9]{64}\.(lod|snd|h3m|h3c|mp3|smk|bik)$/.test(file)) throw new Error('Некорректный файл ресурсов');
          // Browser downloads directly from the resource host, never through the game VPS.
          return nativeFetch(new URL(file, config.baseUrl), {...options,mode:'cors',credentials:'omit'});
        }
      }
      if (!files) return nativeFetch(url, options);
      if (u.pathname === '/api/catalog') {
        const all = [...files.values()];
        const archives = required.map(n => ({name:files.get(n).name,bytes:files.get(n).size}));
        const soundArchives = all.filter(f => /^(heroes3|h3ab_ahd)\.snd$/i.test(f.name)).map(f => ({name:f.name,bytes:f.size}));
        return Response.json({ready:true,archives,soundArchives,campaigns:all.filter(f=>/\.h3c$/i.test(f.name)).map(f=>f.name),videos:[...videoEntries.keys()],maps:all.filter(f=>/\.h3m$/i.test(f.name)).map(f=>f.name).sort(),music:all.filter(f=>/\.mp3$/i.test(f.name)).map(f=>f.name),local:true});
      }
      if (u.pathname === '/api/video') {
        const entry = videoEntries.get((u.searchParams.get('name') || '').toLowerCase());
        return entry ? new Response(entry.archive.slice(entry.offset,entry.offset+entry.bytes)) : new Response('Video not found',{status:404});
      }
      if (['/api/archive','/api/scenario','/api/music','/api/video'].includes(u.pathname)) {
        const file = files.get((u.searchParams.get('name') || '').toLowerCase());
        return file ? new Response(file) : new Response('Файл не найден',{status:404});
      }
      return nativeFetch(url, options);
    }
  };
  input?.addEventListener('change', async () => {
    try { await window.homm3Assets.select(input.files); }
    catch(error) { document.querySelector('#status').textContent = error.message; }
  });
})();
