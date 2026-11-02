/* Generated with a content-addressed, explicit public shell manifest. */
const SHELL = /* OFFLINE_MANIFEST */ null;
const CACHE = 'homm3-shell-v1-' + SHELL.version;
const paths = new Set(SHELL.entries.map(entry=>entry.url));
const hex = data => Array.from(new Uint8Array(data), b=>b.toString(16).padStart(2,'0')).join('');
async function fetchEntry(cache, entry) {
  const response = await fetch(entry.url, {cache:'no-store', credentials:'same-origin'});
  if (!response.ok || response.redirected) throw new Error('Shell unavailable: '+entry.url);
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== entry.bytes || hex(await crypto.subtle.digest('SHA-256',bytes)) !== entry.hash)
    throw new Error('Shell changed during download: '+entry.url);
  const headers = new Headers(response.headers);
  headers.delete('Content-Encoding'); headers.delete('Transfer-Encoding');
  headers.set('Content-Length',String(bytes.byteLength));
  const saved = new Response(bytes, {headers});
  await cache.put(entry.url, saved.clone());
  return saved;
}
async function fillMissing() {
  const cache = await caches.open(CACHE);
  for (const entry of SHELL.entries)
    if (!await cache.match(entry.url)) await fetchEntry(cache, entry);
}
self.addEventListener('install', event => {
  // A failed update never replaces the active worker or its complete cache.
  event.waitUntil(fillMissing());
  // Deliberately no skipWaiting: never switch code underneath a running game.
});
self.addEventListener('activate', event => {
  event.waitUntil((async()=>{
    for (const name of await caches.keys())
      if (name.startsWith('homm3-shell-v1-') && name!==CACHE) await caches.delete(name);
    // Existing documents keep their loaded version until the next navigation.
  })());
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method!=='GET' || url.origin!==self.location.origin) return;
  const key = url.pathname==='/' ? '/index.html' : url.pathname;
  if (!paths.has(key)) return; // No API, lobby, credentials, reports, or third-party caching.
  event.respondWith((async()=>{
    const cache = await caches.open(CACHE);
    const cached = await cache.match(key);
    if (cached) return cached;
    // Repair eviction only if the server still has the exact same version.
    try {return await fetchEntry(cache, SHELL.entries.find(e=>e.url===key));} catch {}
    // Never mix a deployed runtime with an older cached boot script.
    return new Response('Офлайн-файлы удалены браузером. Подготовьте игру заново при подключении к сети.',
      {status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
  })());
});
self.addEventListener('message', event=>{
  if (!['homm3-offline-status','homm3-offline-repair'].includes(event.data?.type)) return;
  event.waitUntil((async()=>{
    if (event.data.type==='homm3-offline-repair') {
      try { await fillMissing(); }
      catch(error) {event.ports[0]?.postMessage({complete:false,error:error.message});return;}
    }
    const cache=await caches.open(CACHE);
    const complete=(await Promise.all(SHELL.entries.map(e=>cache.match(e.url)))).every(Boolean);
    event.ports[0]?.postMessage({version:SHELL.version,complete,bytes:SHELL.entries.reduce((n,e)=>n+e.bytes,0)});
  })());
});
