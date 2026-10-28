/* Playback only: track selection and music volume come from the C++ engine. */
(() => {
  let context, master, analyser, voice, catalog = [], generation = 0;
  let current = '', loops = 0, volume = 1, pendingName = '', pending;
  // Original soundmgr.cpp: nine 100 ms steps out, then (looping music only) in.
  const stepSeconds = 0.1, fadeSeconds = 0.9;
  try { localStorage.removeItem('homm3.music.muted'); } catch {}
  const positions = new Map(), cache = new Map(), loading = new Map();
  const state = { track: '', requestedTrack: '', playing: false, context: 'locked', error: '', volume: 1 };
  function update() {
    state.context = context?.state || 'locked';
    state.volume = volume;
    if (master) master.gain.value = volume;
  }
  function unlock() {
    if (!context) {
      context = new AudioContext(); master = context.createGain(); analyser = context.createAnalyser();
      master.connect(analyser); analyser.connect(context.destination);
      context.addEventListener('statechange', update);
    }
    context.resume().then(update).catch(error => { state.error = error.message; update(); });
    update();
  }
  function finish(v) {
    v.node.onended = null; v.node.disconnect(); v.gain.disconnect();
    if (voice === v) { voice = null; state.playing = false; }
    v.resolve?.();
  }
  function fadeOut(v) {
    if (!v) return Promise.resolve();
    if (v.stopping) return v.stopping;
    const now = context.currentTime;
    // The original saves the resume position BEFORE the fade, not after it.
    positions.set(v.name, (v.offset + now - v.startedAt) % v.node.buffer.duration);
    v.stopping = new Promise(resolve => { v.resolve = resolve; });
    const gain = v.gain.gain, level = gain.value;
    gain.cancelScheduledValues(now);
    for (let step = 1; step < 10; step++)
      gain.setValueAtTime(level * (1 - step / 10), now + (step - 1) * stepSeconds);
    v.node.stop(Math.min(v.endTime, now + (level ? fadeSeconds : 0)));
    return v.stopping;
  }
  async function load(name) {
    if (cache.has(name)) return cache.get(name);
    if (loading.has(name)) return loading.get(name);
    const request = (async () => {
      const filename = catalog.find(n => n.toLowerCase() === `${name}.mp3`.toLowerCase());
      if (!filename) throw new Error(`Музыка не найдена: ${name}.mp3`);
      const response = await (window.homm3Assets?.fetch || fetch)('/api/music?name=' + encodeURIComponent(filename));
      if (!response.ok) throw new Error(`Не удалось прочитать ${filename}`);
      const buffer = await context.decodeAudioData(await response.arrayBuffer());
      cache.set(name, buffer);
      if (cache.size > 4) cache.delete(cache.keys().next().value);
      return buffer;
    })();
    loading.set(name, request);
    try { return await request; } finally { loading.delete(name); }
  }
  function start(name, count, buffer) {
    const node = context.createBufferSource(), gain = context.createGain();
    const now = context.currentTime, offset = count === 0 ? (positions.get(name) || 0) % buffer.duration : 0;
    node.buffer = buffer; node.loop = count !== 1; node.connect(gain); gain.connect(master);
    const v = { node, gain, name, offset, startedAt: now, endTime: count > 0 ? now + buffer.duration * count : Infinity };
    voice = v;
    if (count === 0) {
      for (let step = 1; step < 10; step++)
        gain.gain.setValueAtTime(step / 10, now + (step - 1) * stepSeconds);
      gain.gain.setValueAtTime(1, now + fadeSeconds);
    } else gain.gain.value = 1;
    node.onended = () => finish(v);
    node.start(now, offset);
    if (count > 1) node.stop(v.endTime);
    state.track = name; state.playing = true; update();
  }
  function play(name, count, level) {
    volume = Math.max(0, Math.min(1, level)); update();
    if (name === pendingName) return pending;
    if (voice?.name === name && !voice.stopping) return Promise.resolve();
    const request = ++generation;
    current = name; loops = count; pendingName = name;
    state.requestedTrack = name; state.error = '';
    pending = (async () => {
      try {
        if (!context) throw new Error('Звук ещё не инициализирован');
        // Decode concurrently with fading, without overlapping two music streams.
        const [, buffer] = await Promise.all([fadeOut(voice), load(name)]);
        if (request === generation) start(name, count, buffer);
      } catch (error) {
        if (request === generation) state.error = error.message;
      } finally {
        if (request === generation) { pendingName = ''; update(); }
      }
    })();
    return pending;
  }
  window.homm3Music = {
    state, context: () => context, configure(names) { catalog = names; }, unlock, play,
    stop() { ++generation; pendingName = ''; state.requestedTrack = ''; return fadeOut(voice); },
    resume() { if (current) return play(current, loops, volume); },
    volume(value) { volume = Math.max(0, Math.min(1, value)); update(); },
    close() {
      ++generation; pendingName = ''; current = ''; state.track = state.requestedTrack = '';
      if (voice) { const v = voice; finish(v); v.node.stop(); }
      cache.clear(); positions.clear(); update();
    },
    // Audio output observation for browser integration checks, not game logic.
    samplePeak() { if (!analyser) return 0; const data = new Float32Array(analyser.fftSize); analyser.getFloatTimeDomainData(data); return data.reduce((p, n) => Math.max(p, Math.abs(n)), 0); }
  };
  document.querySelector('#canvas')?.addEventListener('pointerdown', () => {
    if (context?.state === 'suspended') unlock();
  });
  update();
})();
