/* Opt-in simultaneous commands. The native engine remains the only world writer. */
(() => {
  'use strict';
  const OP = { move: 1, build: 2, hire: 3, recruit: 4, advance_day: 5 };
  const resourceNames = ['Дерево', 'Ртуть', 'Руда', 'Сера', 'Кристаллы', 'Самоцветы', 'Золото'];
  const directions = [
    ['↖', 'Северо-запад', 7], ['↑', 'Север', 0], ['↗', 'Северо-восток', 1],
    ['←', 'Запад', 6], ['◎', 'Показать героя', null], ['→', 'Восток', 2],
    ['↙', 'Юго-запад', 5], ['↓', 'Юг', 4], ['↘', 'Юго-восток', 3]
  ];
  let active = false, stopped = false, authority = false, localSlot = -1;
  let view = null, state = null, panel = null, heroId = null, townId = null;
  let localSeq = -1, commandCounter = 0, initialSent = false, lastRevision = -1;
  let nativeCurrent = null, pendingPacket = null, endRequested = false;
  const nativeQueue = [], queuedSequences = new Set(), recruitCounts = new Map();
  const byId = id => document.getElementById(id);
  const transport = () => window.homm3FastTransport;
  const int = n => Number.isSafeInteger(n) && n >= -2147483648 && n <= 2147483647;
  const day = () => Number(view?.absoluteDay ?? state?.day ?? 0);
  const ownHeroes = () => (view?.heroes || []).filter(h => h.owner === localSlot);
  const ownTowns = () => (view?.towns || []).filter(t => t.owner === localSlot);
  const isReady = () => endRequested || (state?.ready || []).includes(localSlot);
  const syncing = () => !view || (state && day() !== Number(state.day)) ||
    Boolean(nativeCurrent?.snapshot) || nativeQueue.some(item => item.snapshot);
  const canAct = () => active && !stopped && !view?.gameOver && !isReady() && !syncing() &&
    !(view?.players || []).some(p => p.slot === localSlot && !p.alive);
  const fmt = n => Number.isFinite(Number(n)) ? Number(n).toLocaleString('ru-RU') : '—';

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function fault(message) {
    if (stopped) return;
    stopped = true;
    window.homm3FastNative.canRun = false;
    if (active) {
      setMessage(String(message || 'Связь с миром игры потеряна.'), true);
      refreshStatus();
    }
    transport()?.interrupt?.(String(message || 'Fast engine interrupted'));
  }
  function setMessage(message, error = false) {
    if (!panel) return;
    const node = byId('fast-message');
    node.textContent = message || '';
    node.classList.toggle('fast-error', error);
  }
  function queueLocal(opcode, id = 0, a = 0, b = 0) {
    if (!active || stopped) return;
    // Camera repetitions need not create an unbounded queue while a battle resolves.
    if (nativeQueue.filter(item => item.local).length >= 24) return;
    nativeQueue.push({ values: [opcode, localSlot, id, a, b, 0, localSeq--, day()], local: true });
  }
  function queueSnapshot(packet) {
    if (!packet?.meta || !(packet.bytes instanceof Uint8Array) || !packet.bytes.length) {
      fault('Получено неполное состояние игры.');
      return;
    }
    const revision = Number(packet.meta.revision ?? packet.meta.seq);
    if (!Number.isSafeInteger(revision) || revision < 0 || revision <= lastRevision) return;
    lastRevision = revision;
    // Saves are complete worlds; a newer waiting save replaces older waiting saves.
    for (let i = nativeQueue.length - 1; i >= 0; --i) {
      if (nativeQueue[i].snapshot) nativeQueue.splice(i, 1);
    }
    nativeQueue.push({
      values: [6, localSlot, 0, 0, 0, packet.meta.gameOver ? 1 : 0, localSeq--, Number(packet.meta.day)],
      snapshot: packet.bytes.slice(), local: true
    });
    refreshStatus();
  }
  function submit(command) {
    if (!canAct()) return;
    if (!transport()?.sendCommand) return fault('Потерян канал команд быстрой игры.');
    const id = `fast-${localSlot}-${Date.now().toString(36)}-${++commandCounter}`;
    try {
      const result = transport().sendCommand(command, id, day());
      if (result === false) return setMessage('Команда не отправлена. Проверьте соединение.', true);
      if (command.kind === 'end_day') endRequested = true;
      setMessage(command.kind === 'end_day' ? 'День завершён. Ожидаем остальных игроков.' : 'Команда отправлена…');
      refreshStatus();
    } catch (error) { fault(error.message); }
  }
  function selectHero(value) {
    heroId = Number(value);
    if (!ownHeroes().some(h => h.id === heroId)) return;
    queueLocal(7, heroId);
    renderHero();
  }
  function selectTown(value) {
    townId = Number(value);
    if (!ownTowns().some(t => t.id === townId)) return;
    queueLocal(8, townId);
    renderTown();
  }
  function move(direction) {
    if (ownHeroes().some(h => h.id === heroId)) submit({ kind: 'move', id: heroId, a: direction });
  }
  function actionButton(text, command, enabled = true) {
    const button = el('button', text);
    button.type = 'button';
    button.dataset.fastAction = '';
    button.dataset.available = String(Boolean(enabled));
    button.disabled = !enabled || !canAct();
    button.addEventListener('click', () => submit(typeof command === 'function' ? command() : command));
    return button;
  }
  function buildPanel() {
    panel = el('aside', undefined, 'fast-panel');
    panel.id = 'fast-panel';
    panel.setAttribute('aria-label', 'Управление быстрой игрой');
    panel.innerHTML = `
      <header class="fast-heading"><div><h2>Быстрая игра</h2><span class="fast-badge">Прототип</span></div><button id="fast-collapse" class="secondary" type="button" aria-expanded="true" aria-controls="fast-content" aria-label="Свернуть панель">−</button></header>
      <div id="fast-content"><p id="fast-date" class="fast-date"></p>
      <p id="fast-status" role="status" aria-live="polite"></p><p id="fast-message" role="status" aria-live="polite"></p>
      <div id="fast-resources" class="fast-resources" aria-label="Ваши ресурсы"></div>
      <section class="fast-section"><label for="fast-hero">Ваш герой</label><select id="fast-hero"></select><p id="fast-hero-stats" class="fast-muted"></p><div id="fast-army" class="fast-army"></div><div class="fast-movement"><div id="fast-directions" class="fast-directions" role="group" aria-label="Движение героя на одну клетку"></div><p class="fast-muted">Шаг: стрелки или кнопки.<br>Камера: Shift + стрелки.</p></div></section>
      <section class="fast-section"><label for="fast-town">Ваш город</label><select id="fast-town"></select><div id="fast-town-actions"></div></section>
      <details class="fast-section"><summary>Камера</summary><div id="fast-camera" class="fast-camera" role="group" aria-label="Перемещение камеры"></div></details>
      <details class="fast-section fast-rules"><summary>Правила прототипа</summary><p>Все игроки отдают команды одновременно. Команды выполняются по одной, без конфликтующих изменений мира. День меняется, когда все живые игроки нажмут «Завершить день».</p><p>Бои, встречи и обязательные решения выполняет ИИ. Заклинания на карте, ручное управление армией и инвентарём пока недоступны. Действуйте через эту панель; игровое поле показывает мир.</p></details>
      </div><footer class="fast-footer"><button id="fast-end-day" type="button">Завершить день</button><span id="fast-ready-count" class="fast-muted"></span></footer>`;
    byId('game-shell').append(panel);
    document.body.classList.add('fast-game-active');
    byId('fast-collapse').addEventListener('click', () => {
      const content = byId('fast-content'), button = byId('fast-collapse');
      content.hidden = !content.hidden;
      panel.classList.toggle('fast-collapsed', content.hidden);
      button.setAttribute('aria-expanded', String(!content.hidden));
      button.setAttribute('aria-label', content.hidden ? 'Развернуть панель' : 'Свернуть панель');
      button.textContent = content.hidden ? '+' : '−';
      window.dispatchEvent(new Event('resize'));
    });
    byId('fast-hero').addEventListener('change', e => selectHero(e.target.value));
    byId('fast-town').addEventListener('change', e => selectTown(e.target.value));
    byId('fast-end-day').addEventListener('click', () => submit({ kind: 'end_day' }));
    for (const [symbol, title, direction] of directions) {
      const button = el('button', symbol, direction === null ? 'secondary' : '');
      button.type = 'button'; button.title = title; button.setAttribute('aria-label', title);
      if (direction !== null) { button.dataset.fastMove = ''; button.addEventListener('click', () => move(direction)); }
      else { button.id = 'fast-center'; button.addEventListener('click', () => selectHero(heroId)); }
      byId('fast-directions').append(button);
    }
    for (const [symbol, title, dx, dy] of [['←', 'Камера влево', -4, 0], ['↑', 'Камера вверх', 0, -4], ['↓', 'Камера вниз', 0, 4], ['→', 'Камера вправо', 4, 0]]) {
      const button = el('button', symbol, 'secondary');
      button.type = 'button'; button.setAttribute('aria-label', title);
      button.addEventListener('click', () => queueLocal(9, 0, dx, dy));
      byId('fast-camera').append(button);
    }
    // Native SDL listens globally. Panel keyboard/pointer events stay in the UI.
    for (const name of ['keydown', 'keyup', 'keypress', 'mousedown', 'mouseup', 'pointerdown', 'pointerup', 'touchstart', 'touchend']) {
      panel.addEventListener(name, event => event.stopPropagation());
    }
    installInputGuard();
    window.dispatchEvent(new Event('resize'));
  }
  function installInputGuard() {
    const canvas = byId('canvas');
    const guard = event => {
      if (!active || event.target !== canvas) return;
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();
    };
    for (const type of ['pointerdown', 'pointerup', 'pointermove', 'mousedown', 'mouseup', 'mousemove', 'click', 'dblclick', 'contextmenu', 'touchstart', 'touchmove', 'touchend', 'wheel']) {
      window.addEventListener(type, guard, { capture: true, passive: false });
    }
    window.addEventListener('keydown', event => {
      if (!active || event.target.closest?.('input,textarea,select,a,[contenteditable="true"]')) return;
      if (event.target.closest?.('button') && (!panel.contains(event.target) || !['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft', 'Home', 'PageUp', 'End', 'PageDown'].includes(event.key))) return;
      if (!event.target.matches?.('body,canvas,#fast-panel') && !panel.contains(event.target)) return;
      if (event.key === 'Tab') return;
      if (event.cancelable) event.preventDefault();
      event.stopImmediatePropagation();
      if (event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
      const keys = { ArrowUp: [0, 0, -4], ArrowRight: [2, 4, 0], ArrowDown: [4, 0, 4], ArrowLeft: [6, -4, 0], Home: [7, -4, -4], PageUp: [1, 4, -4], End: [5, -4, 4], PageDown: [3, 4, 4] };
      const step = keys[event.key];
      if (step) event.shiftKey ? queueLocal(9, 0, step[1], step[2]) : move(step[0]);
    }, true);
    window.addEventListener('keyup', event => {
      if (!active || event.target.closest?.('input,textarea,select,button,a,[contenteditable="true"]')) return;
      if (event.target === canvas || event.target === document.body) event.stopImmediatePropagation();
    }, true);
  }
  function fillSelect(select, items, selected, emptyLabel) {
    select.replaceChildren();
    if (!items.length) {
      const option = el('option', emptyLabel); option.value = ''; select.append(option);
    } else for (const item of items) {
      const option = el('option', item.name || `#${item.id}`); option.value = item.id;
      option.selected = item.id === selected; select.append(option);
    }
    select.disabled = !items.length || stopped;
  }
  function renderHero() {
    const heroes = ownHeroes();
    if (!heroes.some(h => h.id === heroId)) heroId = heroes[0]?.id ?? null;
    fillSelect(byId('fast-hero'), heroes, heroId, 'Героев нет');
    const hero = heroes.find(h => h.id === heroId);
    byId('fast-hero-stats').textContent = hero ? `Ход ${fmt(hero.movement)} · мана ${fmt(hero.mana)} · ${hero.x}, ${hero.y}${hero.z ? ' · подземелье' : ''}` : 'Нанять героя можно в своём городе.';
    const army = byId('fast-army'); army.replaceChildren();
    for (const stack of hero?.army || []) {
      if (stack.count > 0) army.append(el('span', `${stack.name || `Отряд ${stack.type}`} × ${fmt(stack.count)}`));
    }
    byId('fast-center').disabled = !hero || stopped;
    refreshStatus();
  }
  function costLabel(cost) {
    const parts = (cost || []).map((n, i) => Number(n) > 0 ? `${resourceNames[i] || i}: ${fmt(n)}` : '').filter(Boolean);
    return parts.length ? parts.join(' · ') : 'Без затрат';
  }
  function actionRow(name, cost, button) {
    const row = el('div', undefined, 'fast-action-row'), description = el('div');
    description.append(el('strong', name), el('span', cost, 'fast-muted'));
    row.append(description, button); return row;
  }
  function renderTown() {
    const towns = ownTowns();
    if (!towns.some(t => t.id === townId)) townId = towns[0]?.id ?? null;
    fillSelect(byId('fast-town'), towns, townId, 'Городов нет');
    const town = towns.find(t => t.id === townId), container = byId('fast-town-actions');
    const opened = new Set([...container.querySelectorAll('details[open]')].map(n => n.dataset.section));
    const focus = document.activeElement;
    const focusKey = container.contains(focus) ? focus?.dataset.focusKey : null;
    container.replaceChildren();
    if (!town) { container.append(el('p', 'Захватите город, чтобы строить и нанимать войска.', 'fast-muted')); return; }
    const section = (title, key) => {
      const details = el('details', undefined, 'fast-town-section'); details.dataset.section = key;
      details.open = opened.has(key); details.append(el('summary', title)); container.append(details); return details;
    };
    const buildings = town.buildings || [], available = buildings.filter(b => b.allowed);
    const build = section(`Строительство · ${available.length} доступно`, 'build');
    if (!buildings.length) build.append(el('p', 'Нет доступных построек.', 'fast-muted'));
    for (const building of buildings) {
      const button = actionButton('Построить', { kind: 'build', id: town.id, a: building.id }, building.allowed);
      button.dataset.focusKey = `build-${building.id}`;
      const row = actionRow(building.name || `Постройка ${building.id}`, costLabel(building.cost), button);
      if (!building.allowed) row.classList.add('fast-unavailable');
      build.append(row);
    }
    const offers = town.offers || [], tavern = section(`Герои · ${offers.length}`, 'hire');
    if (!offers.length) tavern.append(el('p', 'Нет доступных героев.', 'fast-muted'));
    for (const offer of offers) {
      const button = actionButton('Нанять', { kind: 'hire', id: town.id, a: offer.id });
      button.dataset.focusKey = `hire-${offer.id}`;
      tavern.append(actionRow(offer.name || `Герой ${offer.id}`, offer.cost ? costLabel(offer.cost) : '2 500 золота', button));
    }
    const creatures = town.creatures || [], recruitment = section('Войска', 'recruit');
    if (!creatures.length) recruitment.append(el('p', 'Нет доступных войск.', 'fast-muted'));
    for (const creature of creatures) {
      const key = `${town.id}-${creature.slot}`, controls = el('div', undefined, 'fast-recruit-controls');
      const count = el('input'); count.type = 'number'; count.min = '1'; count.max = String(Math.max(1, creature.available)); count.step = '1';
      count.value = String(Math.min(Math.max(1, recruitCounts.get(key) || 1), Math.max(1, creature.available)));
      count.inputMode = 'numeric'; count.dataset.focusKey = `count-${key}`;
      count.setAttribute('aria-label', `Количество: ${creature.name || `отряд ${creature.type}`}`);
      const button = actionButton('Нанять', () => ({ kind: 'recruit', id: town.id, a: creature.slot, b: Number(count.value) }), creature.available > 0);
      button.dataset.focusKey = `recruit-${key}`;
      const validate = () => {
        const n = Number(count.value), valid = Number.isInteger(n) && n > 0 && n <= creature.available;
        button.dataset.available = String(valid);
        button.disabled = !valid || !canAct();
        if (valid) recruitCounts.set(key, n);
        count.setAttribute('aria-invalid', String(!valid));
      };
      count.addEventListener('input', validate);
      controls.append(count, button);
      const row = actionRow(`${creature.name || `Отряд ${creature.type}`} · ${fmt(creature.available)}`, `${costLabel(creature.cost)} / ед.`, controls);
      recruitment.append(row);
    }
    if (focusKey) [...container.querySelectorAll('[data-focus-key]')].find(n => n.dataset.focusKey === focusKey)?.focus({ preventScroll: true });
  }
  function applyView(nextView) {
    if (!nextView || !panel) return;
    const previousDay = view?.absoluteDay;
    view = nextView;
    if (previousDay !== undefined && view.absoluteDay !== previousDay) {
      endRequested = false;
      setMessage('Новый день. Можно отдавать команды.');
    }
    byId('fast-date').textContent = `Месяц ${fmt(view.month)} · неделя ${fmt(view.week)} · день ${fmt(view.day)}`;
    const resources = byId('fast-resources'); resources.replaceChildren();
    const player = (view.players || []).find(p => p.slot === localSlot);
    for (const [i, amount] of (player?.resources || []).entries()) {
      const node = el('span'); node.append(el('small', resourceNames[i]), el('strong', fmt(amount))); resources.append(node);
    }
    renderHero(); renderTown(); refreshStatus();
  }
  function refreshStatus() {
    if (!panel) return;
    const player = (view?.players || []).find(p => p.slot === localSlot);
    const eliminated = Boolean(player && !player.alive);
    let status = stopped ? 'Партия прервана' : syncing() ? 'Синхронизация мира…' : view?.gameOver ? 'Партия завершена' : eliminated ? 'Выбыли из партии' : isReady() ? 'Ваш день завершён' : 'Можно действовать';
    if (!stopped && Number(state?.pending) > 0) status += ` · команд в очереди: ${state.pending}`;
    byId('fast-status').textContent = status;
    panel.classList.toggle('fast-stopped', stopped);
    const humans = (view?.players || []).filter(p => p.human && p.alive);
    byId('fast-ready-count').textContent = view ? `Завершили день: ${(state?.ready || []).length} / ${humans.length}` : 'Подготовка мира';
    const ready = byId('fast-end-day'); ready.disabled = !canAct() || eliminated;
    ready.textContent = isReady() ? 'День завершён' : 'Завершить день';
    for (const button of panel.querySelectorAll('[data-fast-action]')) button.disabled = !canAct() || eliminated || button.dataset.available !== 'true';
    const hero = ownHeroes().find(h => h.id === heroId);
    for (const button of panel.querySelectorAll('[data-fast-move]')) button.disabled = !canAct() || eliminated || !hero || !(hero.movement > 0);
    for (const button of panel.querySelectorAll('#fast-camera button')) button.disabled = stopped || !view;
  }

  window.homm3FastNative = {
    canRun: true,
    started(slot, isAuthority) {
      if (active) return;
      if (!int(slot) || slot < 0 || slot > 7) return fault('Некорректный номер игрока.');
      active = true; localSlot = slot; authority = Boolean(isAuthority);
      buildPanel(); refreshStatus();
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
      const ok = message.ok === true;
      setMessage(message.message || message.error || (ok ? 'Команда выполнена.' : 'Команда отклонена.'), !ok);
      refreshStatus();
    } else if (message.type === 'fast_error') {
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
