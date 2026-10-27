// Tileset ordering and flip flags follow upstream src/advmgr.cpp.
export const GROUND = ['dirttl.def','sandtl.def','grastl.def','snowtl.def','swmptl.def','rougtl.def','subbtl.def','lavatl.def','watrtl.def','rocktl.def'];
export const RIVERS = ['', 'clrrvr.def','icyrvr.def','mudrvr.def','lavrvr.def'];
export const ROADS = ['', 'dirtrd.def','gravrd.def','cobbrd.def'];
export const TERRAIN_NAMES = ['Земля','Песок','Трава','Снег','Болото','Каменистая земля','Подземелье','Лава','Вода','Скала'];
const COLORS = ['#73523a','#d8c17c','#436231','#d5dce3','#48614b','#8b7953','#835446','#4a3d3b','#345b99','#25232b'];

export class MapRenderer {
  constructor(canvas, minimap, onInspect) {
    this.canvas=canvas; this.ctx=canvas.getContext('2d', { alpha:false });
    this.minimap=minimap; this.mctx=minimap.getContext('2d'); this.onInspect=onInspect;
    this.x=0; this.y=0; this.zoom=1; this.layer=0; this.objects=true; this.grid=false; this.animate=true; this.dirty=true;
    this.assets=new Map(); this.selected=null; this.drag=null;
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    canvas.addEventListener('pointerdown', e => {
      if (!this.map) return;
      canvas.setPointerCapture(e.pointerId);
      this.drag={ sx:e.clientX, sy:e.clientY, x:this.x, y:this.y, moved:false };
    });
    canvas.addEventListener('pointermove', e => {
      if (!this.drag) return;
      const d=this.drag, dx=e.clientX-d.sx, dy=e.clientY-d.sy;
      if (Math.hypot(dx,dy)>4) d.moved=true;
      this.x=d.x-dx/this.zoom; this.y=d.y-dy/this.zoom; this.clamp(); this.dirty=true;
    });
    canvas.addEventListener('pointerup', e => {
      if (!this.drag) return;
      if (!this.drag.moved) {
        const b=canvas.getBoundingClientRect();
        const x=Math.floor((this.x+(e.clientX-b.left)/this.zoom)/32), y=Math.floor((this.y+(e.clientY-b.top)/this.zoom)/32);
        if(x>=0&&y>=0&&x<this.map.size&&y<this.map.size) {this.selected=[x,y];this.inspect(x,y);}
      }
      this.drag=null;this.dirty=true;
    });
    canvas.addEventListener('pointercancel',()=>{this.drag=null;});
    canvas.addEventListener('wheel', e => {e.preventDefault();this.setZoom(this.zoom*(e.deltaY<0?1.15:1/1.15));}, {passive:false});
    canvas.addEventListener('keydown', e => {
      if (!this.map) return;
      const d={ArrowLeft:[-96,0],ArrowRight:[96,0],ArrowUp:[0,-96],ArrowDown:[0,96]}[e.key];
      if(d){e.preventDefault();this.x+=d[0]/this.zoom;this.y+=d[1]/this.zoom;this.clamp();this.dirty=true;}
    });
    minimap.addEventListener('pointerdown',e=>{
      if(!this.map)return;
      const b=minimap.getBoundingClientRect();
      this.center((e.clientX-b.left)/b.width*this.map.size*32,(e.clientY-b.top)/b.height*this.map.size*32);
    });
    let last=0;
    const tick=time=>{if(this.dirty||(this.animate&&time-last>140)){this.draw(time);last=time;this.dirty=false;}requestAnimationFrame(tick);};
    requestAnimationFrame(tick);
  }
  resize(){const b=this.canvas.parentElement.getBoundingClientRect();this.w=b.width;this.h=b.height;const ratio=window.devicePixelRatio||1;this.canvas.width=Math.round(this.w*ratio);this.canvas.height=Math.round(this.h*ratio);this.ratio=ratio;this.clamp();this.dirty=true;}
  setMap(map, assets){this.map=map;this.assets=assets;this.layer=0;this.selected=null;this.sorted=[...map.objects].sort((a,b)=>a.position[1]-b.position[1]||a.position[0]-b.position[0]);this.buildMinimap();const town=map.players.find(p=>p.human&&p.town)||map.players.find(p=>p.town);const pos=town?.position||[map.size/2,map.size/2,0];this.layer=pos[2];this.center(pos[0]*32,pos[1]*32);}
  clamp(){if(!this.map)return;const size=this.map.size*32;this.x=Math.max(-64,Math.min(size-this.w/this.zoom+64,this.x));this.y=Math.max(-64,Math.min(size-this.h/this.zoom+64,this.y));}
  center(x,y){this.x=x-this.w/this.zoom/2;this.y=y-this.h/this.zoom/2;this.clamp();this.dirty=true;}
  setZoom(z){const cx=this.x+this.w/this.zoom/2,cy=this.y+this.h/this.zoom/2;this.zoom=Math.max(.5,Math.min(3,z));this.center(cx,cy);}
  setLayer(layer){this.layer=layer;this.selected=null;this.dirty=true;}
  inspect(x,y){const t=this.map.terrain[(this.layer*this.map.size+y)*this.map.size+x];const objects=this.map.objects.filter(o=>o.position[0]===x&&o.position[1]===y&&o.position[2]===this.layer);this.onInspect({x,y,terrain:TERRAIN_NAMES[t[0]],objects:objects.map(o=>this.map.types[o.type].filename)});}
  buildMinimap(){this.miniLayers=[];for(let z=0;z<this.map.layers;z++){const c=document.createElement('canvas');c.width=c.height=this.map.size;const ctx=c.getContext('2d');for(let y=0;y<this.map.size;y++)for(let x=0;x<this.map.size;x++){ctx.fillStyle=COLORS[this.map.terrain[(z*this.map.size+y)*this.map.size+x][0]]||'#000';ctx.fillRect(x,y,1,1);}this.miniLayers.push(c);}}
  frame(name,index=0){const a=this.assets.get(name?.toLowerCase());return a?.frames[index%a.frames.length];}
  sprite(frame,x,y,flipX=false,flipY=false){if(!frame)return;const c=this.ctx;c.save();c.translate(x,y);if(flipX||flipY){c.translate(flipX?frame.width:0,flipY?frame.height:0);c.scale(flipX?-1:1,flipY?-1:1);}c.drawImage(frame.canvas,frame.x,frame.y);c.restore();}
  draw(time=0){
    const c=this.ctx;c.setTransform(this.ratio||1,0,0,this.ratio||1,0,0);c.fillStyle='#161b18';c.fillRect(0,0,this.w,this.h);
    if(!this.map)return;
    c.imageSmoothingEnabled=false;c.scale(this.zoom,this.zoom);c.translate(-this.x,-this.y);
    const n=this.map.size, x0=Math.max(0,Math.floor(this.x/32)-1), y0=Math.max(0,Math.floor(this.y/32)-1), x1=Math.min(n,Math.ceil((this.x+this.w/this.zoom)/32)+1), y1=Math.min(n,Math.ceil((this.y+this.h/this.zoom)/32)+1);
    for(let pass=0;pass<3;pass++)for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){
      const t=this.map.terrain[(this.layer*n+y)*n+x],flags=t[6];
      if(pass===0)this.sprite(this.frame(GROUND[t[0]],t[1]),x*32,y*32,flags&1,flags&2);
      if(pass===1&&t[2])this.sprite(this.frame(RIVERS[t[2]],t[3]),x*32,y*32,flags&4,flags&8);
      if(pass===2&&t[4])this.sprite(this.frame(ROADS[t[4]],t[5]),x*32,y*32+16,flags&16,flags&32);
    }
    if(this.objects)for(const [i,o] of this.sorted.entries()){
      if(o.position[2]!==this.layer)continue;
      const type=this.map.types[o.type];if(type.hidden)continue;
      const a=this.assets.get(type.filename.toLowerCase());if(!a)continue;
      const frame=a.frames[this.animate?(Math.floor(time/150)+i)%a.frames.length:0];
      const x=(o.position[0]+1)*32-frame.width,y=(o.position[1]+1)*32-frame.height;
      if(x+frame.width<this.x||y+frame.height<this.y||x>this.x+this.w/this.zoom||y>this.y+this.h/this.zoom)continue;
      this.sprite(frame,x,y);
    }
    if(this.grid){c.strokeStyle='#ffffff30';c.lineWidth=1/this.zoom;c.beginPath();for(let x=x0;x<=x1;x++){c.moveTo(x*32,y0*32);c.lineTo(x*32,y1*32);}for(let y=y0;y<=y1;y++){c.moveTo(x0*32,y*32);c.lineTo(x1*32,y*32);}c.stroke();}
    if(this.selected){c.strokeStyle='#f5d695';c.lineWidth=2/this.zoom;c.strokeRect(this.selected[0]*32+1,this.selected[1]*32+1,30,30);}
    const m=this.mctx;m.imageSmoothingEnabled=false;m.clearRect(0,0,220,220);m.drawImage(this.miniLayers[this.layer],0,0,220,220);m.strokeStyle='#fff3c9';m.lineWidth=1.5;m.strokeRect(this.x/(n*32)*220,this.y/(n*32)*220,this.w/this.zoom/(n*32)*220,this.h/this.zoom/(n*32)*220);
  }
}
