/* Downloaded resources are separate from the engine's IDBFS saved games. */
const META = 'homm3-offline-meta-v1';
const PREFIX = 'homm3-resources-v1-';
const ACTIVE = '/__homm3_offline_active__';
const DRAFT = '/__homm3_offline_draft__';
const RECORD = '/__homm3_offline_record__';
let pinned;
const requestKey = value => {
  const url=new URL(value,globalThis.location?.href || 'https://offline.invalid/');
  return url.pathname+url.search;
};
export function resetInstalled() { pinned=null; }
const hex = data=>Array.from(new Uint8Array(data),b=>b.toString(16).padStart(2,'0')).join('');
const digest = async data=>hex(await crypto.subtle.digest('SHA-256',data));
const urlFor = (kind,name)=>'/api/'+kind+'?name='+encodeURIComponent(name);
async function readMeta(key) {
  if (!('caches' in globalThis)) return null;
  const response=await (await caches.open(META)).match(key);
  return response ? response.json() : null;
}
export function resourceEntries(catalog, videos=true) {
  if (!catalog?.ready || !Array.isArray(catalog.archives) || !Array.isArray(catalog.maps))
    throw new Error('Сначала выберите папку своей игры');
  const entries=[...catalog.archives,...(catalog.soundArchives||[])].map(a=>({url:urlFor('archive',a.name),name:a.name,bytes:a.bytes}));
  for (const [kind,names] of [['scenario',[...catalog.maps,...(catalog.campaigns||[])]],['music',catalog.music||[]],['video',videos ? catalog.videos||[] : []]])
    for (const name of names) entries.push({url:urlFor(kind,name),name});
  const names=new Set(entries.filter(e=>e.url.startsWith('/api/archive?')).map(e=>e.name.toLowerCase()));
  for (const name of ['h3bitmap.lod','h3sprite.lod','h3ab_bmp.lod','h3ab_spr.lod','heroes3.snd'])
    if (!names.has(name)) throw new Error('Не найден обязательный архив '+name);
  if (!catalog.maps.length && !catalog.campaigns?.length) throw new Error('В установке нет карт или кампаний');
  return entries;
}
export async function installed() {
  const record=await readMeta(ACTIVE);
  if (!record) return null;
  if (!await caches.has(record.cache)) return {...record,complete:false};
  const cache=await caches.open(record.cache);
  // CacheStorage serializes URL query apostrophes as %27. Compare serialized
  // requests on BOTH sides, including metadata written by older installations.
  const keys=new Set((await cache.keys()).map(r=>requestKey(r.url)));
  return {...record,complete:record.entries.every(e=>keys.has(requestKey(e.url)))};
}
export async function fetchInstalled(url) {
  // Freeze one resource generation for the lifetime of a document/game.
  const record=pinned || await installed().catch(()=>null);
  if (!record) return null;
  if (!record.complete) throw new Error('Офлайн-файлы удалены браузером. Откройте меню игры → «Без интернета» и восстановите копию.');
  pinned=record; // Never memoize a missing/incomplete installation.
  if (url.pathname==='/api/catalog') return Response.json({...record.catalog,offline:true,ready:true});
  const key=urlFor(url.pathname.slice(5),url.searchParams.get('name')||'');
  const entry=record.entries.find(e=>e.url.toLowerCase()===key.toLowerCase());
  const response=entry && await (await caches.open(record.cache)).match(entry.url);
  return response || new Response('Файл отсутствует в офлайн-установке',{status:404});
}
export async function exclusive(action) {
  if (!navigator.locks) throw new Error('Браузер не поддерживает безопасную установку. Обновите браузер.');
  return navigator.locks.request('homm3-offline-install',{ifAvailable:true},lock=>{
    if (!lock) throw new Error('Подготовка уже открыта в другой вкладке');
    return action();
  });
}
export async function install(source,{videos=false,signal,onProgress=()=>{}}={}) {
  const entries=resourceEntries(source.catalog,videos);
  const id=await digest(new TextEncoder().encode(JSON.stringify({identity:source.identity,entries,videos})));
  const name=PREFIX+id, meta=await caches.open(META), cache=await caches.open(name);
  const hashLookup=new Map(Object.entries(source.hashes||{}).map(([n,h])=>[n.toLowerCase(),h.split('.')[0]]));
  // Only a completed installation can change ACTIVE; interrupted downloads resume.
  const draft={cache:name,entries};
  await meta.put(DRAFT,Response.json(draft));
  let bytes=0, completed=0;
  for (const entry of entries) {
    signal?.throwIfAborted();
    let saved=await cache.match(entry.url);
    onProgress({name:entry.name,completed,total:entries.length,bytes});
    if (!saved) {
      const response=await source.fetch(entry.url,{signal});
      if (!response.ok) throw new Error('Не удалось скачать '+entry.name);
      const data=await response.arrayBuffer();
      if (!data.byteLength || (entry.bytes!=null && data.byteLength!==entry.bytes))
        throw new Error('Файл прочитан не полностью: '+entry.name);
      const expected=hashLookup.get(entry.name.toLowerCase());
      if (expected && /^[a-f0-9]{64}$/.test(expected) && await digest(data)!==expected)
        throw new Error('Контрольная сумма не совпала: '+entry.name);
      signal?.throwIfAborted();
      saved=new Response(data,{headers:{'Content-Type':response.headers.get('Content-Type')||'application/octet-stream','X-Homm3-Bytes':String(data.byteLength)}});
      await cache.put(entry.url,saved.clone());
    }
    bytes+=Number(saved.headers.get('X-Homm3-Bytes'));
    completed++;
    onProgress({name:entry.name,completed,total:entries.length,bytes});
  }
  signal?.throwIfAborted();
  const record={schema:1,cache:name,entries,bytes,videos,installedAt:new Date().toISOString(),
    catalog:{...source.catalog,videos:videos ? source.catalog.videos||[] : [],offline:true}};
  // Keep the previous generation available to already running games.
  await cache.put(RECORD,Response.json(record));
  await meta.put(ACTIVE,Response.json(record));
  await meta.delete(DRAFT);
  return record;
}
export async function removeDownloads() {
  // No IDBFS/localStorage calls: saved games and preferences remain untouched.
  for (const name of await caches.keys()) if (name.startsWith(PREFIX)) await caches.delete(name);
  await caches.delete(META);
  pinned=null;
}
