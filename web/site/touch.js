/* Touch-to-mouse boundary for the original SDL client. No game rules here. */
(() => {
  window.Homm3Touch = class {
    constructor(canvas, ring) {
      this.canvas = canvas;
      this.ring = ring;
      this.points = new Map();
      this.gesture = null;
      this.buttons = 0;
      this.generation = 0;
      this.lastTap = null;
      // SDL also listens for legacy TouchEvents. Consume these before SDL can
      // turn one finger into a second, premature left-click.
      for (const type of ['touchstart','touchmove','touchend','touchcancel']) {
        window.addEventListener(type, e => {
          if (e.target === canvas) { if(e.cancelable)e.preventDefault(); e.stopImmediatePropagation(); }
        }, {capture:true, passive:false});
      }
      canvas.addEventListener('pointerdown', e => this.down(e));
      canvas.addEventListener('pointermove', e => this.move(e));
      canvas.addEventListener('pointerup', e => this.up(e));
      canvas.addEventListener('pointercancel', e => this.up(e, true));
      canvas.addEventListener('lostpointercapture', e => {
        if (this.points.has(e.pointerId)) this.up(e, true);
      });
      window.addEventListener('blur', () => this.cancel());
      document.addEventListener('visibilitychange', () => { if (document.hidden) this.cancel(); });
    }
    point(e) { return {x:e.clientX, y:e.clientY}; }
    consume(e) { if(e.cancelable)e.preventDefault(); e.stopImmediatePropagation(); }
    mouse(type, point, button=0, detail=1) {
      if (type==='mousedown') this.buttons |= button===2?2:1;
      if (type==='mouseup') this.buttons &= ~(button===2?2:1);
      window.homm3TouchPointerActive = true;
      clearTimeout(this.pointerOff);
      this.canvas.dispatchEvent(new MouseEvent(type, {
        bubbles:true, cancelable:true, view:window, clientX:point.x, clientY:point.y,
        button, buttons:this.buttons, detail
      }));
    }
    idlePointer() {
      this.pointerOff = setTimeout(() => {
        if (!this.points.size && !this.buttons) window.homm3TouchPointerActive = false;
      }, 80);
    }
    clearHold() { clearTimeout(this.hold); this.ring.hidden=true; }
    release(point) {
      if (this.buttons & 1) this.mouse('mouseup', point, 0);
      if (this.buttons & 2) {this.mouse('mouseup', point, 2);}
    }
    down(e) {
      if (e.pointerType==='mouse') return;
      this.consume(e);
      this.points.set(e.pointerId, this.point(e));
      this.canvas.setPointerCapture(e.pointerId);
      if (this.points.size===1) {
        this.release(this.point(e));
        ++this.generation;
        const point=this.point(e);
        this.gesture={kind:'pending', start:point, point};
        this.mouse('mousemove', point);
        this.hold=setTimeout(() => {
          if (this.gesture?.kind!=='pending' || this.points.size!==1) return;
          this.gesture.kind='right';
          this.lastTap=null;
          this.ring.style.left=point.x+'px'; this.ring.style.top=point.y+'px';
          this.ring.hidden=false;
          this.mouse('mousedown', point, 2);
        }, 500);
      } else {
        this.clearHold(); this.lastTap=null;
        this.release(this.gesture?.point || this.point(e));
        this.gesture={kind:'cancelled'};
      }
    }
    move(e) {
      if (!this.points.has(e.pointerId)) return;
      this.consume(e); this.points.set(e.pointerId,this.point(e));
      const g=this.gesture;
      if (!g) return;
      if (g.kind==='cancelled') return;
      g.point=this.point(e);
      if (g.kind==='pending' && Math.hypot(e.clientX-g.start.x,e.clientY-g.start.y)>10) {
        this.clearHold(); this.lastTap=null; g.kind='drag';
        this.mouse('mousedown',g.start);
      }
      if (g.kind==='drag') this.mouse('mousemove',g.point);
    }
    up(e, cancelled=false) {
      if (!this.points.has(e.pointerId)) return;
      this.consume(e);this.points.delete(e.pointerId);this.clearHold();
      const g=this.gesture;
      if (g?.kind==='pending' && !cancelled) {
        const now=performance.now(), point=g.start;
        const double=this.lastTap && now-this.lastTap.time<350 && Math.hypot(point.x-this.lastTap.x,point.y-this.lastTap.y)<20;
        const detail=double?2:1;
        this.mouse('mousemove',point);
        this.mouse('mousedown',point,0,detail);
        // Let the original nested button pump see the down before the up.
        const generation=this.generation;
        setTimeout(() => {
          if (generation!==this.generation) return;
          this.mouse('mouseup',point,0,detail);
          this.canvas.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:point.x,clientY:point.y,detail}));
          if (double) this.canvas.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,clientX:point.x,clientY:point.y,detail:2}));
          this.idlePointer();
        }, 30);
        this.lastTap=double?null:{...point,time:now};
      } else if (g && g.kind!=='cancelled') {
        this.release(g.kind==='right'?g.start:g.point);
      }
      if (cancelled) this.lastTap=null;
      this.gesture=this.points.size?{kind:'cancelled'}:null;
      this.idlePointer();
    }
    cancel() {
      ++this.generation;this.clearHold();this.lastTap=null;
      this.release(this.gesture?.point || this.gesture?.start || {x:0,y:0});
      this.points.clear();this.gesture=null;this.idlePointer();
    }
  };
})();
