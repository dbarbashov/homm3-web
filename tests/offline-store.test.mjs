import {test} from 'node:test';
import assert from 'node:assert/strict';
import {installed,fetchInstalled,resetInstalled} from '../web/site/offline-store.js';

test('existing CacheStorage installations handle apostrophes and escaped filenames without redownloading', async()=>{
  const previous=globalThis.caches;
  const maps=["The Battle of Daeyan's Ford.h3m",'Карта + 100%.h3m','Dwarven Tunnels(Allies).h3m'];
  const entries=maps.map(name=>({name,url:'/api/scenario?name='+encodeURIComponent(name)}));
  let active=null;
  const bodies=new Map(entries.map(e=>[new URL(e.url,'https://offline.invalid').href,new Response(e.name)]));
  const cache={keys:async()=>[...bodies.keys()].map(url=>new Request(url)),match:async url=>bodies.get(new URL(url,'https://offline.invalid').href)?.clone()};
  globalThis.caches={has:async()=>true,open:async name=>name==='homm3-offline-meta-v1'
    ? {match:async()=>active ? Response.json(active) : undefined} : cache};
  resetInstalled();
  try {
    assert.equal(await fetchInstalled(new URL('https://offline.invalid/api/catalog')),null);
    active={cache:'existing-copy',entries,catalog:{maps,ready:true}};
    assert.equal((await installed()).complete,true);
    const catalog=await fetchInstalled(new URL('https://offline.invalid/api/catalog'));
    assert.equal((await catalog.json()).maps[0],maps[0],'missing state must not stick after installation');
    for(const entry of entries) {
      const response=await fetchInstalled(new URL(entry.url,'https://offline.invalid'));
      assert.equal(await response.text(),entry.name);
    }
    // Already running games retain their generation until explicitly reset.
    active={...active,catalog:{maps:['other.h3m']}};
    assert.deepEqual((await (await fetchInstalled(new URL('https://offline.invalid/api/catalog'))).json()).maps,maps);
    bodies.delete(new URL(entries[0].url,'https://offline.invalid').href);
    assert.equal((await installed()).complete,false,'genuinely missing resources must remain incomplete');
  } finally {resetInstalled();globalThis.caches=previous;}
});
