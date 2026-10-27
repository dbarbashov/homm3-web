/* A playback backend for C++ decoded PCM. No event names or game rules here. */
(() => {
  const buffers = new Map(), voices = new Map();
  const stats = { started: 0, stopped: 0, active: 0, maxActive: 0, errors: [], recent: [], byName: {} };
  let analyser;
  function context() { return window.homm3Music.context(); }
  function output() {
    if (!analyser) { analyser = context().createAnalyser();analyser.connect(context().destination); }
    return analyser;
  }
  function update() { stats.active = [...voices.values()].filter(v => v.source).length;stats.maxActive = Math.max(stats.maxActive, stats.active); }
  function detach(v, remember) {
    if (!v?.source) return;
    if (remember) v.offset = (v.offset + context().currentTime - v.started) % v.buffer.duration;
    v.source.onended = null;v.source.stop();v.source.disconnect();v.gain.disconnect();v.source = null;update();
  }
  function start(v) {
    const ctx = context();v.source = ctx.createBufferSource();v.gain = ctx.createGain();
    v.source.buffer = v.buffer;v.source.loop = v.remaining === 0;v.gain.gain.value = v.volume;
    v.source.connect(v.gain);v.gain.connect(output());v.started = ctx.currentTime;
    v.source.onended = () => {
      v.source.disconnect();v.gain.disconnect();v.source = null;v.offset = 0;
      if (v.remaining > 1) { --v.remaining;start(v); }else update();
    };
    v.source.start(0, v.offset);update();
  }
  window.homm3Sfx = {
    stats,
    load(id, name, heap) {
      const count = heap.length;
      const buffer = context().createBuffer(2, count / 2, 44100);
      // Read the current heap each time: WASM memory can grow during gameplay.
      for (let ch = 0; ch < 2; ++ch) { const out = buffer.getChannelData(ch);for (let i = 0; i < out.length; ++i) out[i] = heap[i * 2 + ch]; }
      buffers.set(id, { buffer, name });
    },
    drop(id) { buffers.delete(id); },
    play(slot, id, loops, volume) {
      const clip = buffers.get(id);if (!clip) { stats.errors.push('Missing PCM buffer ' + id);return; }
      detach(voices.get(slot), false);
      const v = { ...clip, loops, remaining: loops, volume, offset: 0, source: null };voices.set(slot, v);start(v);
      ++stats.started;stats.byName[v.name] = (stats.byName[v.name] || 0) + 1;
      stats.recent.push({ name: v.name, slot, loops, volume });if (stats.recent.length > 64) stats.recent.shift();
    },
    stop(slot) { detach(voices.get(slot), false);voices.delete(slot);++stats.stopped; },
    pause(slot) { detach(voices.get(slot), true); },
    resume(slot) { const v = voices.get(slot);if (v && !v.source) start(v); },
    restart(slot) { const v = voices.get(slot);if (v) { detach(v, false);v.offset = 0;v.remaining = v.loops;start(v); } },
    playing(slot) { return !!voices.get(slot)?.source; },
    volume(slot, value) { const v = voices.get(slot);if (v) { v.volume = value;if (v.gain) v.gain.gain.value = value; } },
    samplePeak() { if (!analyser) return 0;const data = new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(data);return data.reduce((p, n) => Math.max(p, Math.abs(n)), 0); },
    close() { for (const v of voices.values()) detach(v, false);voices.clear();buffers.clear();if (analyser) analyser.disconnect();analyser = null;update(); }
  };
})();
