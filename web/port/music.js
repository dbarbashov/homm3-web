/* Playback only: track selection and music volume come from the C++ engine. */
(() => {
  let context, source, gain, analyser, catalog = [], generation = 0;
  let current = '', loops = 0, volume = 1, startedAt = 0, offset = 0;
  // Remove the obsolete host mute; the original in-game volume is authoritative.
  try { localStorage.removeItem('homm3.music.muted'); } catch {}
  const positions = new Map(), cache = new Map();
  const state = { track: '', playing: false, context: 'locked', error: '', volume: 1 };
  function update() {
    state.context = context?.state || 'locked';
    state.volume = volume;
    if (gain) gain.gain.value = state.volume;
  }
  function unlock() {
    if (!context) {
      context = new AudioContext(); gain = context.createGain(); analyser = context.createAnalyser();
      gain.connect(analyser); analyser.connect(context.destination);
      context.addEventListener('statechange', update);
    }
    context.resume().then(update).catch(error => { state.error = error.message; update(); });
    update();
  }
  function detach() {
    if (source) {
      const duration = source.buffer.duration;
      offset = (offset + context.currentTime - startedAt) % duration;
      positions.set(current, offset);source.onended = null;source.stop();source.disconnect();source = null;
    }
    state.playing = false;
  }
  async function play(name, count, level) {
    volume = Math.max(0, Math.min(1, level)); update();
    if (name === current && source) return;
    const request = ++generation;detach();current = name;loops = count;state.track = name;state.error = '';update();
    try {
      if (!context) throw new Error('Звук ещё не инициализирован');
      let buffer = cache.get(name);
      if (!buffer) {
        const filename = catalog.find(n => n.toLowerCase() === `${name}.mp3`.toLowerCase());
        if (!filename) throw new Error(`Музыка не найдена: ${name}.mp3`);
        const response = await (window.homm3Assets?.fetch || fetch)('/api/music?name=' + encodeURIComponent(filename));
        if (!response.ok) throw new Error(`Не удалось прочитать ${filename}`);
        buffer = await context.decodeAudioData(await response.arrayBuffer());
        cache.set(name, buffer);if (cache.size > 4) cache.delete(cache.keys().next().value);
      }
      if (request !== generation) return;
      offset = (positions.get(name) || 0) % buffer.duration;
      source = context.createBufferSource();source.buffer = buffer;source.loop = count === 0;source.connect(gain);
      const playingSource = source;
      source.onended = () => {
        if (source !== playingSource) return;
        source.disconnect();source = null;positions.set(name, 0);state.playing = false;
        if (count > 1) play(name, count - 1, volume);else update();
      };
      startedAt = context.currentTime;source.start(0, offset);state.playing = true;update();
    } catch (error) { if (request === generation) { state.error = error.message; update(); } }
  }
  window.homm3Music = {
    state, context: () => context, configure(names) { catalog = names; }, unlock, play,
    stop() { ++generation;detach();update(); },
    resume() { if (current) play(current, loops, volume); },
    volume(value) { volume = Math.max(0, Math.min(1, value));update(); },
    close() { ++generation;detach();current = '';state.track = '';cache.clear();update(); },
    // Audio output observation for browser integration checks, not game logic.
    samplePeak() { if (!analyser) return 0; const data = new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(data);return data.reduce((p, n) => Math.max(p, Math.abs(n)), 0); }
  };
  // A canvas gesture can resume audio after browser suspension without a second UI.
  document.querySelector('#canvas')?.addEventListener('pointerdown', () => {
    if (context?.state === 'suspended') unlock();
  });
  update();
})();
