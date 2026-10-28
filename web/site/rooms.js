/* Browser lobby: browse first, choose an identity before joining, then prepare. */
(() => {
  const $ = id => document.getElementById(id);
  const tavern = $('tavern'), colors = ['#db5650','#538fd4','#c6ae82','#65ae58','#e49b46','#b782c5','#58b6b6','#d08eaa'];
  function read(store, key) { try { return window[store].getItem(key) || ''; } catch { return ''; } }
  function write(store, key, value) { try { window[store].setItem(key, value); return true; } catch { return false; } }
  const params = new URLSearchParams(location.hash.slice(1));
  let invitation = params.has('room') ? {room:params.get('room'),invite:params.get('invite') || ''} : null;
  let socket, connecting, me, room, token = read('sessionStorage','homm3.session'), rooms = [], reconnect;
  let nickname = read('localStorage','homm3.nickname'), view = invitation ? 'invite' : 'browser', pendingAction = null;
  let busy = false, preparing = false, pendingChat = null, chatBlockedUntil = 0, chatTimer;
  const incoming = []; let queuedBytes = 0;
  const phaseLabel = r => ({waiting:r.players>=r.capacity?'Нет мест':'Ждём игроков',setup:'Выбор карты',playing:'Идёт игра',interrupted:'Прервана'}[r.phase] || r.phase);
  const canJoin = r => r.phase === 'waiting' && r.players < r.capacity;
  const validName = name => name.length > 0 && Array.from(name).length <= 20 && !/[\u0000-\u001f\u007f-\u009f]/u.test(name);
  if (!validName(nickname)) nickname = '';
  $('player-name').value = nickname;

  function notice(message) { $('room-notice').textContent = message; $('tavern-error').textContent = room ? '' : message; }
  function send(data) { if (socket?.readyState !== WebSocket.OPEN) throw new Error('Нет соединения с сервером'); socket.send(JSON.stringify(data)); }
  function setBusy(value) {
    busy = value;
    for (const id of ['create-submit','join-invite','identity-submit','show-create','edit-name']) $(id).disabled = value;
    for (const button of document.querySelectorAll('[data-join-room]')) button.disabled = value;
  }
  function renderIdentity() {
    $('nickname-summary').textContent = nickname ? `Вы: ${nickname}` : 'Имя ещё не выбрано';
    $('edit-name').textContent = nickname ? 'Изменить' : 'Выбрать имя';
    $('create-as').textContent = `Вы войдёте как ${nickname}`;
    $('invite-as').textContent = nickname ? `Вы войдёте как ${nickname}` : 'На следующем шаге выберите имя игрока.';
  }
  function syncPanels() {
    const playing = !!window.homm3Boot?.running;
    document.body.classList.toggle('network-setup', !tavern.hidden && !playing);
    tavern.classList.toggle('in-game', playing);
    $('network-title').textContent = playing ? 'Игроки и чат' : view === 'identity' ? 'Имя игрока' : room ? 'Ваша комната' : 'Сетевая игра';
    $('network-back').hidden = playing || !!room;
    $('close-tavern').hidden = !playing;
    for (const [id,state] of [['room-browser','browser'],['identity-form','identity'],['create-room','create'],['invite-panel','invite'],['room-info','room'],['chat-panel','chat']]) $(id).hidden = view !== state;
    $('view-tavern').hidden = !room;
    renderIdentity();
  }
  function show(next) { view = next; notice(''); syncPanels(); }
  function updateChatButton() {
    const seconds = Math.ceil((chatBlockedUntil - Date.now()) / 1000);
    $('chat-send').disabled = !room || socket?.readyState !== WebSocket.OPEN || pendingChat !== null || seconds > 0;
    $('chat-send-icon').toggleAttribute('hidden', seconds > 0);
    $('chat-send-countdown').hidden = seconds <= 0;
    $('chat-send-countdown').textContent = seconds > 0 ? `${seconds}с` : '';
    clearTimeout(chatTimer);
    if (seconds > 0) chatTimer = setTimeout(updateChatButton, 250);
  }
  function appendChat(msg) {
    const log=$('chat-log'), nearBottom=log.scrollHeight-log.scrollTop-log.clientHeight<60;
    $('chat-empty')?.remove(); const row=document.createElement('tr');
    const time=document.createElement('td'),name=document.createElement('td'),body=document.createElement('td');
    const stamp=Number(msg.time || msg.timestamp || 0);
    time.textContent=new Date(stamp || Date.now()).toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'});
    name.textContent=msg.name;body.textContent=msg.text;row.append(time,name,body);$('chat-rows').append(row);
    while($('chat-rows').children.length>100)$('chat-rows').firstChild.remove();
    if(nearBottom) log.scrollTop=log.scrollHeight;
    if(view!=='chat') $('room-chat').textContent='Чат · новое сообщение';
  }
  function renderRoom(next) {
    const previous=room; room=next; window.homm3Room=room; setBusy(false);
    $('chat-input').disabled=!room; updateChatButton();
    if(!room) {
      $('chat-rows').replaceChildren(); $('connection').textContent='Список открытых комнат';
      pendingChat=null; incoming.length=0; queuedBytes=0; show('browser'); refresh(); return;
    }
    invitation=null;
    if(!previous || view!=='chat') view='room';
    $('room-title').textContent=room.title;
    $('room-meta').textContent=`${room.private?'По приглашению':'Открытая'} · ${room.players.length}/${room.capacity} · ${phaseLabel({...room,players:room.players.length})}`;
    $('players').replaceChildren();
    room.players.forEach((p,i)=>{
      const li=document.createElement('li'), flag=document.createElement('span'), label=document.createElement('span'), state=document.createElement('small');
      flag.className='flag';flag.style.setProperty('--flag',colors[i]);
      label.textContent=p.name+(p.id===me?' · вы':'')+(p.id===room.host?' · организатор':'');
      state.textContent=!p.online?'Нет связи':room.phase==='playing'?'В игре':p.ready?'Готов':'Не готов';
      li.append(flag,label,state);$('players').append(li);
    });
    const self=room.players.find(p=>p.id===me), everyone=room.players.length>=2 && room.players.every(p=>p.ready && p.online);
    $('ready').textContent=preparing?'Подготовка…':self?.ready?'Отменить готовность':'Подготовить игру';
    $('ready').classList.toggle('secondary',!!self?.ready);
    $('ready').disabled=!window.homm3Boot.ready || preparing || room.phase!=='waiting' || socket?.readyState!==WebSocket.OPEN;
    $('ready').hidden=room.phase!=='waiting';
    $('launch-room').hidden=me!==room.host || room.phase!=='waiting' || !self?.ready;
    $('launch-room').disabled=!everyone || socket?.readyState!==WebSocket.OPEN;
    $('preparation').hidden=room.phase!=='waiting';
    $('copy-invite').hidden=room.phase!=='waiting';
    $('room-next').textContent=room.phase==='waiting'
      ? !window.homm3Boot.ready?'Загружаем движок… Подготовка станет доступна через несколько секунд.'
      : preparing?'Загружаем файлы игры и проверяем версию…'
      : !self?.ready?'Подготовьте игру. Затем организатор сможет выбрать карту.'
      : room.players.length<2?(room.private?'Отправьте приглашение второму игроку.':'Ждём ещё одного игрока. Комната видна в общем списке.')
      : !everyone?'Ждём готовности: '+room.players.filter(p=>!p.ready || !p.online).map(p=>p.name).join(', ')
      : me===room.host?'Все готовы. Перейдите к выбору карты.':'Вы готовы. Ждём организатора: он выбирает карту.'
      : room.phase==='setup'?(me===room.host?'Выберите карту и запустите партию в игре.':'Организатор выбирает карту.')
      : room.phase==='interrupted'?'Партия прервана. Сохраните игру, если возможно. Восстановление матча пока недоступно.':'Партия идёт.';
    $('chat-rows').replaceChildren();room.chat.forEach(appendChat);
    if(!room.chat.length) {
      const row=document.createElement('tr'),cell=document.createElement('td');row.id='chat-empty';cell.colSpan=3;cell.textContent='Поздоровайтесь с другими игроками.';row.append(cell);$('chat-rows').append(row);
    }
    $('invite-link').value=location.origin+'/port/game.html#'+new URLSearchParams({room:room.id,...(room.private?{invite:room.invite}:{})});
    $('start').disabled=true;
    $('connection').textContent=socket?.readyState===WebSocket.OPEN?'На связи':'Восстанавливаем соединение…';
    syncPanels();
  }
  function discardSession() {
    clearTimeout(reconnect); const previous=socket; socket=null; connecting=null;me=null;token='';
    write('sessionStorage','homm3.session','');previous?.close();
  }
  async function connect() {
    if(socket?.readyState===WebSocket.OPEN && me) return;
    if(connecting) return connecting;
    if(!token && !validName(nickname)) throw new Error('Выберите имя игрока');
    connecting=new Promise((resolve,reject)=>{
      const ws=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/lobby/socket`);
      socket=ws;ws.binaryType='arraybuffer';
      const timeout=setTimeout(()=>{ws.close();reject(new Error('Сервер не отвечает. Попробуйте ещё раз.'));},10000);
      ws.onopen=()=>ws.send(JSON.stringify({type:'hello',token,name:nickname}));
      ws.onmessage=event=>{
        if(socket!==ws)return;
        if(event.data instanceof ArrayBuffer) {
          if(queuedBytes+event.data.byteLength>32*1024*1024){notice('Очередь сетевых сообщений переполнена');ws.close();return;}
          incoming.push(new Uint8Array(event.data));queuedBytes+=event.data.byteLength;return;
        }
        const data=JSON.parse(event.data);
        if(data.type==='hello') {
          clearTimeout(timeout);me=data.id;token=data.token;write('sessionStorage','homm3.session',token);
          nickname=data.name;write('localStorage','homm3.nickname',nickname);$('player-name').value=nickname;renderIdentity();
          $('connection').textContent='На связи';$('connection').dataset.online='true';resolve();
        }
        if(data.type==='error') {
          setBusy(false);
          if(data.code==='chat_rejected') {
            pendingChat=null;$('chat-error').textContent=data.message;
            chatBlockedUntil=Date.now()+Math.min(60000,Math.max(0,Number(data.retryAfterMs)||0));updateChatButton();
          } else notice(data.message);
          if(!me){clearTimeout(timeout);reject(new Error(data.message));}
        }
        if(data.type==='room')renderRoom(data.room);
        if(data.type==='chat') {
          if(data.message.player===me && pendingChat!==null){
            if($('chat-input').value.trim()===pendingChat)$('chat-input').value='';
            $('chat-count').textContent=Array.from($('chat-input').value).length+'/300';pendingChat=null;$('chat-error').textContent='';chatBlockedUntil=Date.now()+2000;updateChatButton();
          }
          if(room){room.chat.push(data.message);if(room.chat.length>100)room.chat.shift();}appendChat(data.message);
        }
        if(data.type==='left') {
          renderRoom(null);location.hash='multiplayer';
          if(window.homm3Boot.running)location.reload();else{$('start').disabled=false;openTavern();}
        }
        if(data.type==='launch') {
          closeTavern();notice('Все готовы. Организатор выбирает карту…');window.homm3Boot.run(true);
        }
      };
      ws.onerror=()=>{clearTimeout(timeout);reject(new Error('Сервер сетевой игры недоступен'));};
      ws.onclose=()=>{
        clearTimeout(timeout);if(socket!==ws)return;
        pendingChat=null;connecting=null;me=null;setBusy(false);updateChatButton();
        $('connection').dataset.online='false';$('connection').textContent='Связь потеряна';$('ready').disabled=true;$('launch-room').disabled=true;
        reject(new Error('Соединение закрыто'));clearTimeout(reconnect);
        if(room) reconnect=setTimeout(()=>connect().catch(e=>notice(e.message)),3000);
      };
    });
    try{await connecting;}finally{connecting=null;}
  }
  async function refresh() {
    try {
      const response=await fetch('/lobby/rooms');if(!response.ok)throw Error();const data=await response.json();rooms=data.rooms;renderList();
      $('browser-status').textContent=`Комнат: ${rooms.length} · обновлено ${new Date().toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'})}`;
    }catch{$('browser-status').textContent='Список недоступен. Попробуйте обновить.';}
  }
  function renderList() {
    const focused=document.activeElement?.dataset.joinRoom;
    const q=$('room-filter').value.toLowerCase(),list=$('room-list');list.replaceChildren();
    const filtered=rooms.filter(r=>(r.title+' '+r.host).toLowerCase().includes(q)&&($('phase-filter').value==='all'||r.phase==='waiting'));
    if(!filtered.length){const row=list.insertRow(),cell=row.insertCell();cell.colSpan=5;cell.className='empty-cell';cell.textContent=q?'Комнаты не найдены. Измените поиск.':'Открытых комнат пока нет. Создайте первую.';}
    for(const r of filtered){
      const row=list.insertRow();row.className='room-card';row.dataset.unavailable=String(!canJoin(r));
      const name=row.insertCell(),title=document.createElement('span'),status=document.createElement('small');
      title.className='room-name';title.textContent=r.title;title.title=r.title;status.className='room-mobile-phase';status.textContent=phaseLabel(r);name.append(title,status);
      const host=row.insertCell();host.className='room-host';host.textContent=r.host;
      const count=row.insertCell();count.className='room-count';count.textContent=`${r.players}/${r.capacity}`;
      const phase=row.insertCell();phase.className='room-phase';phase.textContent=phaseLabel(r);
      const action=row.insertCell();action.className='room-join';
      if(canJoin(r)){
        const button=document.createElement('button');button.textContent='Войти';button.dataset.joinRoom=r.id;button.disabled=busy;
        button.setAttribute('aria-label',`Войти: ${r.title}`);button.onclick=()=>requestEntry({type:'join',room:r.id,title:r.title});action.append(button);
        if(focused===r.id)button.focus({preventScroll:true});
      }else{action.textContent='—';action.setAttribute('aria-label',phaseLabel(r));}
    }
  }
  function requestEntry(action, force=false) {
    if(busy)return;
    pendingAction=action;
    if(force || !validName(nickname)) {
      show('identity');$('player-name').value=nickname;$('identity-error').textContent='';
      $('identity-context').textContent=action?.title?`Вход в комнату «${action.title}»`:action?.type==='create'?'Перед созданием комнаты выберите имя.':'Имя видно другим игрокам в комнате и чате.';
      $('identity-submit').textContent=action?.type==='join'?'Войти в комнату':action?.type==='create'?'Продолжить':'Сохранить имя';
      $('player-name').focus();return;
    }
    proceed(action);
  }
  async function proceed(action) {
    pendingAction=null;
    if(!action){show(invitation?'invite':'browser');return;}
    if(action.type==='create'){show('create');$('room-name').focus();return;}
    show(invitation?'invite':'browser');setBusy(true);notice('Входим в комнату…');
    try{await connect();if(room){notice('Вы уже находитесь в комнате. Сначала покиньте её.');setBusy(false);return;}send({type:'join',room:action.room,...(action.invite?{invite:action.invite}:{})});}
    catch(e){setBusy(false);notice(e.message);}
  }
  $('identity-form').onsubmit=e=>{
    e.preventDefault();const name=$('player-name').value.trim();
    if(!validName(name)){$('identity-error').textContent='Введите от 1 до 20 символов без управляющих знаков.';$('player-name').focus();return;}
    if(name!==nickname)discardSession();nickname=name;
    const saved=write('localStorage','homm3.nickname',nickname);renderIdentity();proceed(pendingAction);
    if(!saved)notice('Имя выбрано на эту сессию. Браузер не разрешил сохранить его.');
  };
  $('identity-cancel').onclick=()=>{pendingAction=null;show(invitation?'invite':'browser');};
  $('edit-name').onclick=()=>requestEntry(null,true);
  $('edit-invite-name').onclick=()=>requestEntry(null,true);
  $('show-create').onclick=()=>requestEntry({type:'create'});
  $('cancel-create').onclick=()=>show('browser');
  $('visibility').onchange=()=>{$('visibility-hint').textContent=$('visibility').value==='private'?'Комнату не видно в списке. Вход только по вашей ссылке.':'Комната появится в общем списке. Любой игрок сможет войти.';};
  $('create-room').onsubmit=async e=>{
    e.preventDefault();if(busy)return;setBusy(true);
    try{await connect();if(room){setBusy(false);notice('Вы уже находитесь в комнате.');return;}send({type:'create',title:$('room-name').value,capacity:Number($('capacity').value),private:$('visibility').value==='private'});}
    catch(e){setBusy(false);notice(e.message);}
  };
  $('join-invite').onclick=()=>requestEntry({type:'join',...invitation});
  $('refresh-rooms').onclick=refresh;$('room-filter').oninput=renderList;$('phase-filter').onchange=renderList;
  $('network-back').onclick=()=>{if(view==='browser')location.href='/';else {pendingAction=null;show('browser');}};
  function openTavern() {
    if(window.homm3Boot.running && !room)return;
    tavern.hidden=false;document.body.classList.add('tavern-open');syncPanels();
    if(!room)refresh();$('network-title').tabIndex=-1;$('network-title').focus({preventScroll:true});
  }
  function closeTavern() {
    tavern.hidden=true;document.body.classList.remove('tavern-open','network-setup');$('canvas').focus({preventScroll:true});
  }
  $('close-tavern').onclick=closeTavern;
  window.homm3Lobby={open:openTavern,close:closeTavern};
  window.addEventListener('homm3-running',syncPanels);
  window.addEventListener('homm3-boot-ready',()=>{if(room)renderRoom(room);});
  $('copy-invite').onclick=async()=>{
    $('invite-link').hidden=false;
    try{await navigator.clipboard.writeText($('invite-link').value);notice('Приглашение скопировано');}
    catch{$('invite-link').select();notice('Скопируйте выделенную ссылку');}
  };
  $('room-chat').onclick=()=>{show('chat');$('room-chat').textContent='Чат комнаты';$('chat-log').scrollTop=$('chat-log').scrollHeight;$('chat-input').focus();};
  $('chat-back').onclick=()=>show('room');
  $('leave-room').onclick=()=>{
    if(window.homm3Boot.running && !confirm('Покинуть партию? Сначала сохраните игру. Восстановление сетевой партии недоступно.'))return;
    try{send({type:'leave'});}catch(e){notice(e.message);}
  };
  function syncPreparation() {
    $('room-progress-wrap').hidden=!preparing;
    $('room-progress').value=$('progress').value;
    $('room-progress-status').textContent=$('status').textContent;
  }
  new MutationObserver(syncPreparation).observe($('status'),{childList:true,subtree:true,characterData:true});
  new MutationObserver(syncPreparation).observe($('progress'),{attributes:true});
  $('ready').onclick=async()=>{
    if(preparing || !room)return;
    try {
      if(window.homm3Boot.running)throw new Error('Игра уже запущена.');
      const targetRoom=room.id,ready=!room.players.find(p=>p.id===me)?.ready;
      if(ready){preparing=true;renderRoom(room);syncPreparation();await window.homm3Boot.prepare();}
      if(room?.id!==targetRoom)return;
      send({type:'ready',ready,build:window.homm3Build || ''});notice(ready?'Файлы готовы.':'');
    }catch(e){notice(e.message);}finally{preparing=false;if(room)renderRoom(room);syncPreparation();}
  };
  $('launch-room').onclick=()=>{try{send({type:'launch'});}catch(e){notice(e.message);}};
  $('chat-input').oninput=()=>{const chars=Array.from($('chat-input').value);if(chars.length>300)$('chat-input').value=chars.slice(0,300).join('');$('chat-count').textContent=Math.min(300,chars.length)+'/300';};
  $('chat-form').onsubmit=e=>{
    e.preventDefault();const text=$('chat-input').value.trim();
    if(!text || pendingChat!==null || Date.now()<chatBlockedUntil)return;
    if(Array.from(text).length>300){$('chat-error').textContent='Не больше 300 символов';return;}
    try{send({type:'chat',text});pendingChat=text;updateChatButton();}catch(e){$('chat-error').textContent=e.message;}
  };
  for(const event of ['keydown','keyup','keypress'])window.addEventListener(event,e=>{if(e.target.closest('#tavern,dialog') || e.target.matches('input,textarea,select,button,a'))e.stopImmediatePropagation();},true);
  setInterval(()=>{if(socket?.readyState===WebSocket.OPEN)send({type:'ping'});},15000);
  setInterval(()=>{if(!tavern.hidden && view==='browser')refresh();},5000);
  window.homm3Network={
    get self(){return room?.players.find(p=>p.id===me)?.dpid || 0;},
    get host(){return room?.players.find(p=>p.id===room.host)?.dpid || 0;},
    get players(){return room?.players || [];},
    get connected(){return socket?.readyState===WebSocket.OPEN && room && ['setup','playing'].includes(room.phase);},
    send(to,data){if(!this.connected || socket.bufferedAmount>16*1024*1024)return false;const packet=new Uint8Array(data.length+4);new DataView(packet.buffer).setUint32(0,to,true);packet.set(data,4);socket.send(packet);return true;},
    peek(){return incoming[0]?.length || 0;},
    pop(){const data=incoming.shift();if(data)queuedBytes-=data.length;return data;},
    playing(){if(me===room?.host)send({type:'playing'});}
  };
  window.addEventListener('homm3-ready',()=>{if(window.homm3PortDiagnostics?.screen==='adventure' && room?.phase==='setup')window.homm3Network.playing();});
  renderIdentity();syncPanels();
  if(invitation || location.hash==='#multiplayer') {
    openTavern();
    if(token){setBusy(true);connect().catch(e=>notice(e.message)).finally(()=>setBusy(false));}
  }
})();
