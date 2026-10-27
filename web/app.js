import { Engine } from './engine.js';
import { MapRenderer, GROUND, RIVERS, ROADS } from './renderer.js';
const $=id=>document.getElementById(id);
const decode=bytes=>new TextDecoder($('encoding').value).decode(new Uint8Array(bytes)).replace(/\0/g,'');
const renderer=new MapRenderer($('map'),$('minimap'),cell=>{
  $('cell').textContent=`${cell.x}, ${cell.y} · ${cell.terrain}${cell.objects.length?' · '+cell.objects.join(', '):''}`;
});
let engine,catalog,busy=false;
const cache=new Map();
const audio=new Audio();audio.loop=true;audio.volume=.35;
function message(text,percent=0){$('loading-text').textContent=text;$('progress').value=percent;}
async function get(url){const r=await fetch(url);if(!r.ok)throw new Error(`${r.status}: ${url}`);return r.arrayBuffer();}
function controls(){const has=!!renderer.map;$('open').disabled=busy||!catalog?.ready;$('maps').disabled=busy||!catalog?.ready;$('surface').disabled=!has||busy;$('underground').disabled=!has||busy||renderer.map.layers<2;$('surface').classList.toggle('active',renderer.layer===0);$('underground').classList.toggle('active',renderer.layer===1);$('scale').textContent=Math.round(renderer.zoom*100)+'%';}
async function loadMap(){
  if(busy)return;busy=true;controls();$('loading').hidden=false;$('warnings').hidden=true;
  try{
    message('Читаем оригинальный H3M…',5);
    const map=engine.map(await get('/api/map?name='+encodeURIComponent($('maps').value)));
    map.types.forEach(t=>{t.filename=decode(t.name);});
    const jobs=new Map();
    for(const t of map.terrain){jobs.set(GROUND[t[0]],{opaque:true});if(t[2])jobs.set(RIVERS[t[2]],{});if(t[4])jobs.set(ROADS[t[4]],{});}
    for(const t of map.types)if(t.filename&&!t.hidden)jobs.set(t.filename.toLowerCase(),{animated:true});
    const failures=[],assets=new Map();let done=0;
    const pending=[...jobs];
    // Four IO workers; synchronous WASM calls cannot interleave input buffers.
    await Promise.all(Array.from({length:4},async()=>{
      while(pending.length){const [name,options]=pending.shift();try{
        if(!cache.has(name))cache.set(name,engine.sprite(await get('/api/asset?name='+encodeURIComponent(name)),options));
        assets.set(name,cache.get(name));
      }catch(error){failures.push(`${name}: ${error.message}`);}
      done++;message(`Графика карты · ${done} / ${jobs.size}`,10+done/jobs.size*90);
      }
    }));
    // Keep only this map's decoded sprites, preventing accumulation across scenarios.
    for(const name of cache.keys())if(!jobs.has(name))cache.delete(name);
    renderer.setMap(map,assets);
    $('map-name').textContent=decode(map.name)||$('maps').value;
    $('map-meta').textContent=`${map.size} × ${map.size} · ${map.layers===2?'два уровня':'поверхность'} · ${map.objects.length.toLocaleString('ru-RU')} объектов`;
    $('description').textContent=decode(map.description);
    $('status').textContent=failures.length?`${failures.length} ресурсов не прочитано`:`${assets.size} DEF · декодировано в WASM`;
    if(failures.length){$('warnings').hidden=false;$('warnings').querySelector('pre').textContent=failures.join('\n');}
    $('loading').hidden=true;
    // Expose read-only diagnostics for the browser smoke test.
    window.homm3Diagnostics={map:$('maps').value,size:map.size,objects:map.objects.length,assets:assets.size,failures,wasm:true};
  }catch(error){message('Не удалось открыть карту: '+error.message);$('status').textContent='Ошибка загрузки';console.error(error);}
  finally{busy=false;controls();}
}
$('open').onclick=loadMap;
$('encoding').onchange=()=>{if(renderer.map){$('map-name').textContent=decode(renderer.map.name);$('description').textContent=decode(renderer.map.description);}};
for(const [id,field] of [['objects','objects'],['animation','animate'],['grid','grid']])$(id).onchange=e=>{renderer[field]=e.target.checked;renderer.dirty=true;};
$('surface').onclick=()=>{renderer.setLayer(0);controls();};$('underground').onclick=()=>{renderer.setLayer(1);controls();};
$('minus').onclick=()=>{renderer.setZoom(renderer.zoom/1.25);controls();};$('plus').onclick=()=>{renderer.setZoom(renderer.zoom*1.25);controls();};
$('map').addEventListener('wheel',()=>controls());
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('viewport').requestFullscreen();}catch{$('status').textContent='Полный экран недоступен';}};
$('music').onclick=async()=>{try{if(audio.paused){await audio.play();$('music').textContent='Выключить музыку';}else{audio.pause();$('music').textContent='Включить музыку';}}catch{$('status').textContent='Не удалось воспроизвести музыку';}};
try{
  [engine,catalog]=await Promise.all([Engine.create(),fetch('/api/catalog').then(r=>r.json())]);
  if(!catalog.ready)throw new Error('Укажите gameRoot в .local/game.json и перезапустите сервер.');
  $('maps').replaceChildren(...catalog.maps.map(name=>new Option(name.replace(/\.h3m$/i,''),name)));
  const favorite=catalog.maps.find(x=>x==='All for One.h3m')||catalog.maps[0];$('maps').value=favorite;
  const track=catalog.music.find(x=>/^grass\.mp3$/i.test(x))||catalog.music[0];
  if(track){audio.src='/api/music?name='+encodeURIComponent(track);$('music').disabled=false;}
  controls();await loadMap();
}catch(error){message(error.message);$('status').textContent='Нужна настройка';console.error(error);}
