/* Simultaneous transport only. All interaction stays in the original C++ UI. */
(() => {
  'use strict';
  const OP = {move:1, build:2, hire:3, recruit:4, advance_day:5};
  let active=false, stopped=false, authority=false, localSlot=-1;
  let view=null, state=null, localSeq=-1, commandCounter=0, initialSent=false;
  let lastRevision=-1, appliedRevision=-1, nativeCurrent=null, pendingPacket=null, endRequested=false;
  const nativeQueue=[], queuedSequences=new Set(), requests=new Map();
  const transport=()=>window.homm3FastTransport;
  const int=n=>Number.isSafeInteger(n)&&n>=-2147483648&&n<=2147483647;
  const day=()=>Number(view?.absoluteDay??state?.day??0);
  const isReady=()=>endRequested||(state?.ready||[]).includes(localSlot);
  const syncing=()=>!view || (state && day()!==Number(state.day)) ||
    Boolean(nativeCurrent?.snapshot) || nativeQueue.some(item=>item.snapshot);
  const canAct=()=>active&&!stopped&&!requests.size&&!view?.gameOver&&!isReady()&&!syncing()&&
    !(view?.players||[]).some(p=>p.slot===localSlot&&!p.alive);
  function setMessage(message,error=false) {
    window.homm3FastStatus={message:String(message||''),error};
  }
  function refreshStatus() {
    window.homm3FastState={active,stopped,ready:isReady(),canAct:canAct(),day:day(),state};
  }
  function applyView(nextView) {
    if (!nextView) return;
    if (view && view.absoluteDay!==nextView.absoluteDay) endRequested=false;
    view=nextView;
    window.homm3FastView=view;
    refreshStatus();
  }
  function fault(message) {
    if(stopped)return;
    stopped=true;window.homm3FastNative.canRun=false;
    setMessage(message,true);refreshStatus();
    transport()?.interrupt?.(String(message||'Fast engine interrupted'));
    window.homm3Boot?.fail(String(message||'Сетевая партия прервана.'));
  }
  function queueSnapshot(packet) {
    if(!packet?.meta || !(packet.bytes instanceof Uint8Array) || !packet.bytes.length) {
      fault('Получено неполное состояние игры.');return;
    }
    const revision=Number(packet.meta.revision??packet.meta.seq);
    if(!Number.isSafeInteger(revision)||revision<0||revision<=lastRevision)return;
    lastRevision=revision;
    for(let i=nativeQueue.length-1;i>=0;--i)if(nativeQueue[i].snapshot)nativeQueue.splice(i,1);
    nativeQueue.push({values:[6,localSlot,0,0,0,packet.meta.gameOver?1:0,localSeq--,Number(packet.meta.day)],
      snapshot:packet.bytes.slice(),revision,local:true});
    refreshStatus();
  }
  window.homm3FastNative = {
    canRun: true,
    request(op, id, a, b) {
      if (!canAct()) return 0;
      const kind = ({1:'move',2:'build',3:'hire',4:'recruit',5:'end_day'})[op];
      if (!kind) return 0;
      const ticket = ++commandCounter;
      const request = `native-${localSlot}-${Date.now().toString(36)}-${ticket}`;
      requests.set(request, {ticket, kind, day:day(), result:null});
      try {
        const command=op===5?{kind}:op===4?{kind,id,a,b}:{kind,id,a};
        transport().sendCommand(command, request, day());
        if (kind==='end_day') endRequested=true;
        refreshStatus();
      } catch (error) { requests.delete(request); fault(error.message); return 0; }
      return ticket;
    },
    result(ticket) {
      for (const [id, item] of requests) {
        if (item.ticket!==ticket) continue;
        const done = item.kind==='end_day' && ((state?.ready||[]).includes(localSlot) || day()>item.day);
        if (stopped || done || (item.result && (!item.result.ok || authority || appliedRevision>=item.result.revision))) {
          requests.delete(id); refreshStatus(); return !stopped && (done || item.result?.ok) ? 1 : -1;
        }
        return 0;
      }
      return -1;
    },
    started(slot, isAuthority) {
      if (active) return;
      if (!int(slot) || slot < 0 || slot > 7) return fault('Некорректный номер игрока.');
      active = true; localSlot = slot; authority = Boolean(isAuthority);
      refreshStatus();
      if (authority) nativeQueue.push({ values: [10, slot, 0, 0, 0, 0, 0, 0], initial: true });
      else if (pendingPacket) { queueSnapshot(pendingPacket); pendingPacket = null; }
    },
    take() {
      if (!active || stopped || nativeCurrent || !nativeQueue.length) return null;
      nativeCurrent = nativeQueue.shift();
      try {
        if (nativeCurrent.snapshot) {
          if (!window.Module?.FS) throw new Error('Файловая система игры недоступна.');
          window.Module.FS.writeFile('/runtime/fast-incoming.gm2', nativeCurrent.snapshot);
        }
        return new Int32Array(nativeCurrent.values);
      } catch (error) { nativeCurrent = null; fault(error.message); return null; }
    },
    complete(meta, bytes) {
      if (!active || stopped) return;
      if (!meta || !nativeCurrent || meta.seq !== nativeCurrent.values[6]) return fault('Нарушен порядок команд игрового движка.');
      const item = nativeCurrent;
      nativeCurrent = null;
      if (meta.view) applyView(meta.view);
      if (item.snapshot) appliedRevision = Math.max(appliedRevision, item.revision);
      if (item.snapshot) {
        try { window.Module?.FS?.unlink('/runtime/fast-incoming.gm2'); } catch (_) { /* Import can remove its input. */ }
        if (!meta.ok) return fault(meta.error || 'Не удалось загрузить общий мир.');
      } else if (!item.local && authority) {
        if (!(bytes instanceof Uint8Array) || !bytes.length) return fault('Движок не создал состояние мира.');
        try {
          if (!transport()?.sendSnapshot) throw new Error('Канал состояния мира недоступен.');
          const packet = { seq: meta.seq, ok: Boolean(meta.ok), error: String(meta.error || ''), day: Number(meta.day ?? meta.view?.absoluteDay), gameOver: Boolean(meta.gameOver ?? meta.view?.gameOver), roster: (meta.view?.players || view?.players || []).map(p => ({ slot: p.slot, dpid: p.dpid, human: Boolean(p.human), alive: Boolean(p.alive) })) };
          if (transport().sendSnapshot(packet, bytes.slice()) === false) throw new Error('Не удалось отправить состояние мира.');
          if (item.initial) initialSent = true;
        } catch (error) { return fault(error.message); }
      }
      // World-command feedback arrives privately from the relay as fast_result.
      // Executing another player's command must not overwrite the host's message.
      if (!meta.ok && item.local && !item.snapshot) setMessage(meta.error || 'Действие недоступно.', true);
      refreshStatus();
    },
    projection(nextView) { if (active && !stopped) applyView(nextView); },
    fault
  };
  window.addEventListener('homm3-fast-packet', event => {
    const packet = event.detail;
    if (authority && active) return; // Canonical authority never reloads its own save.
    if (!active) {
      if (packet?.bytes instanceof Uint8Array) pendingPacket = { meta: packet.meta, bytes: packet.bytes.slice() };
      return;
    }
    queueSnapshot(packet);
  });
  window.addEventListener('homm3-fast-control', event => {
    const message = event.detail;
    if (!message || typeof message !== 'object') return;
    if (message.type === 'fast_state') {
      const previousDay = state?.day;
      state = message;
      if (previousDay !== undefined && previousDay !== state.day) endRequested = false;
      if (message.interrupted) fault(typeof message.interrupted === 'string' ? message.interrupted : message.message || 'Сетевая партия прервана.');
      refreshStatus();
    } else if (message.type === 'fast_result') {
      if (!active || stopped) return;
      const pending = requests.get(message.id);
      if (pending) pending.result = message;
      const ok = message.ok === true;
      setMessage(message.message || message.error || (ok ? 'Команда выполнена.' : 'Команда отклонена.'), !ok);
      refreshStatus();
    } else if (message.type === 'fast_error') {
      const pending = requests.get(message.id);
      if (pending) pending.result = {ok:false, revision:0};
      endRequested = (state?.ready || []).includes(localSlot);
      setMessage(message.message || message.error || 'Команда отклонена.', true);
      refreshStatus();
    } else if (message.type === 'fast_execute') {
      if (!active || !authority || !initialSent || stopped) return fault('Команда поступила до готовности ведущего.');
      const command = message.command, opcode = OP[command?.kind];
      const actor = command?.kind === 'advance_day' ? -1 : message.actor;
      const values = [opcode, actor, command?.id ?? 0, command?.a ?? 0, command?.b ?? 0, 0, message.seq, message.day];
      if (!opcode || !values.every(int) || message.seq <= 0) return fault('Получена некорректная команда.');
      if (queuedSequences.has(message.seq)) return;
      if (queuedSequences.size >= 4096) queuedSequences.clear();
      queuedSequences.add(message.seq);
      if (nativeQueue.length >= 128) return fault('Очередь команд переполнена.');
      nativeQueue.push({ values });
    }
  });
})();
