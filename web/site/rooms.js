(() => {
  const $ = id => document.getElementById(id);
  const tavern = $('tavern'), colors = ['#db5650','#538fd4','#c6ae82','#65ae58','#e49b46','#b782c5','#58b6b6','#d08eaa'];
  let socket, connecting, me, room, token = sessionStorage.getItem('homm3.session') || '', rooms = [], reconnect, selectedRoom = null;
  const incoming = []; let queuedBytes=0;
  let pendingChat = null, chatBlockedUntil = 0, chatTimer;
  function updateChatButton() {
    const seconds = Math.ceil((chatBlockedUntil - Date.now()) / 1000);
    $('chat-send').disabled = !room || socket?.readyState !== WebSocket.OPEN || pendingChat !== null || seconds > 0;
    $('chat-send-icon').toggleAttribute('hidden', seconds > 0);
    $('chat-send-countdown').hidden = seconds <= 0;
    $('chat-send-countdown').textContent = seconds > 0 ? `${seconds}с` : '';
    clearTimeout(chatTimer);
    if (seconds > 0) chatTimer = setTimeout(updateChatButton, 250);
  }
  const params = new URLSearchParams(location.hash.slice(1));
  const invitation = params.has('room') ? {room:params.get('room'),invite:params.get('invite') || ''} : null;
  $('player-name').value = localStorage.getItem('homm3.nickname') || '';
  function notice(message) { $('room-notice').textContent = message; $('tavern-error').textContent = message; }
  function send(data) { if (socket?.readyState !== WebSocket.OPEN) throw new Error('Нет соединения с таверной'); socket.send(JSON.stringify(data)); }
  function appendChat(msg) {
    const log=$('chat-log'), nearBottom=log.scrollHeight-log.scrollTop-log.clientHeight<60;
    $('chat-empty')?.remove(); const row=document.createElement('tr');
    const time=document.createElement('td'),name=document.createElement('td'),body=document.createElement('td');
    const stamp=Number(msg.time || msg.timestamp || 0);
    time.textContent=stamp ? new Date(stamp).toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'}) : new Date().toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'});
    name.textContent=msg.name;body.textContent=msg.text;row.append(time,name,body);$('chat-rows').append(row);
    while($('chat-rows').children.length>100)$('chat-rows').firstChild.remove();
    if(nearBottom) log.scrollTop=log.scrollHeight;
  }
  function renderRoom(next) {
    const previousPhase=room?.phase;
    room=next; window.homm3Room=room;
    $('room-browser').hidden=!!room; $('room-info').hidden=!room;
    $('chat-input').disabled=!room; updateChatButton();
    if(!room) { $('chat-rows').replaceChildren(); $('connection').textContent='Одиночная игра'; refresh(); return; }
    $('create-room').hidden=true; $('join-invite').hidden=true;$('create-title').textContent='Создать комнату'; $('room-title').textContent=room.title;
    const phase={waiting:'Ожидаем игроков',setup:'Выбор сценария',playing:'Идёт партия',interrupted:'Соединение партии прервано'}[room.phase] || room.phase;
    $('room-meta').textContent=`${room.private?'По приглашению':'Публичная'} · ${room.players.length}/${room.capacity} · ${phase}`;
    $('players').replaceChildren();
    room.players.forEach((p,i)=>{
      const li=document.createElement('li'), flag=document.createElement('span'), label=document.createElement('span'), state=document.createElement('small');
      flag.className='flag'; flag.style.setProperty('--flag',colors[i]);
      label.textContent=p.name+(p.id===me?' · вы':'')+(p.id===room.host?' ♔':'');
      state.textContent=!p.online?'Нет связи':p.ready?'Готов':'В комнате';
      li.append(flag,label,state); $('players').append(li);
    });
    const self=room.players.find(p=>p.id===me);
    $('ready').textContent=self?.ready?'Не готов':'Готов'; $('ready').disabled=room.phase!=='waiting';
    $('ready').hidden=room.phase!=='waiting';
    $('launch-room').hidden=me!==room.host||room.phase!=='waiting';
    $('launch-room').disabled=room.phase!=='waiting'||room.players.length<2||room.players.some(p=>!p.ready||!p.online);
    $('chat-rows').replaceChildren(); room.chat.forEach(appendChat);
    if(!room.chat.length) { const empty=document.createElement('tr'),cell=document.createElement('td');empty.id='chat-empty';cell.colSpan=3;cell.textContent='Поздоровайтесь с другими игроками.';empty.append(cell);$('chat-rows').append(empty); }
    $('invite-link').value=location.origin+'/port/game.html#'+new URLSearchParams({room:room.id,...(room.private?{invite:room.invite}:{})});
    $('start').disabled=true;
    if(room.phase==='waiting') $('source-hint').textContent='Вы в сетевой комнате. Нажмите «Готов» после выбора файлов игры.';
    if(room.phase==='playing' && previousPhase!=='playing') notice('Партия началась. У каждого игрока свой ход и своя карта видимости.');
    if(room.phase==='interrupted') notice('Партия прервана. Сохраните игру, если возможно, и создайте новую комнату. Автоматическое восстановление партии ещё недоступно.');
    $('connection').textContent=`Таверна · ${room.title}`;
  }
  async function connect() {
    if(socket?.readyState===WebSocket.OPEN && me) return;
    if(connecting) return connecting;
    const name=$('player-name').value.trim();
    if(!token && !name) { $('player-name').focus(); throw new Error('Укажите имя героя'); }
    localStorage.setItem('homm3.nickname',name);
    connecting=new Promise((resolve,reject)=>{
      socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/lobby/socket`); socket.binaryType='arraybuffer';
      const timeout=setTimeout(()=>{socket.close();reject(new Error('Таверна не отвечает'));},10000);
      socket.onopen=()=>send({type:'hello',token,name});
      socket.onmessage=event=>{
        if(event.data instanceof ArrayBuffer) {
          if(queuedBytes+event.data.byteLength>32*1024*1024) { notice('Очередь сетевых сообщений переполнена'); socket.close(); return; }
          incoming.push(new Uint8Array(event.data)); queuedBytes+=event.data.byteLength; return;
        }
        const data=JSON.parse(event.data);
        if(data.type==='hello') { clearTimeout(timeout);me=data.id;token=data.token;sessionStorage.setItem('homm3.session',token);$('connection').dataset.online='true';$('connection').textContent='Соединение с таверной установлено';resolve(); }
        if(data.type==='error') {
          if(data.code==='chat_rejected') {
            pendingChat=null; $('chat-error').textContent=data.message;
            chatBlockedUntil=Date.now()+Math.min(60000,Math.max(0,Number(data.retryAfterMs)||0)); updateChatButton();
          } else notice(data.message);
          if(!me) { clearTimeout(timeout);reject(new Error(data.message)); }
        }
        if(data.type==='room') renderRoom(data.room);
        if(data.type==='chat') {
          if(data.message.player===me && pendingChat!==null) {
            if($('chat-input').value.trim()===pendingChat) $('chat-input').value='';
            $('chat-count').textContent=Array.from($('chat-input').value).length+'/300';
            pendingChat=null; $('chat-error').textContent=''; chatBlockedUntil=Date.now()+2000; updateChatButton();
          }
          if(room) {room.chat.push(data.message);if(room.chat.length>100)room.chat.shift();} appendChat(data.message);
        }
        if(data.type==='left') { renderRoom(null); location.hash='multiplayer'; if(window.homm3Boot.running) location.reload(); else { $('start').disabled=false; openTavern(); } }
        if(data.type==='launch') { closeTavern(); notice('Все готовы. Выбираем сценарий…'); window.homm3Boot.run(true); }
      };
      socket.onerror=()=>{ clearTimeout(timeout); reject(new Error('Сервер таверны недоступен')); };
      socket.onclose=()=>{ pendingChat=null; updateChatButton(); clearTimeout(timeout);$('connection').dataset.online='false';$('connection').textContent='Связь с таверной потеряна';$('ready').disabled=true;$('launch-room').disabled=true;$('chat-send').disabled=true;connecting=null;me=null;reject(new Error('Соединение закрыто'));clearTimeout(reconnect);reconnect=setTimeout(()=>connect().catch(e=>notice(e.message)),3000); };
    });
    try { await connecting; } finally { connecting=null; }
  }
  async function refresh() {
    try { const response=await fetch('/lobby/rooms'); if(!response.ok)throw Error(); const data=await response.json();rooms=data.rooms;renderList();$('browser-status').textContent=`Комнат: ${rooms.length} · обновлено ${new Date().toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'})}`; }
    catch { $('browser-status').textContent='Нет связи с сервером таверны. Попробуйте обновить список.'; }
  }
  function renderList() {
    const q=$('room-filter').value.toLowerCase(), list=$('room-list');list.replaceChildren();
    const filtered=rooms.filter(r=>(r.title+' '+r.host).toLowerCase().includes(q)&&($('phase-filter').value==='all'||r.phase==='waiting'));
    if(!filtered.some(r=>r.id===selectedRoom))selectedRoom=null;
    const selected=filtered.find(r=>r.id===selectedRoom);
    $('join-selected').disabled=!selected||selected.phase!=='waiting'||selected.players>=selected.capacity;
    if(!filtered.length) { const row=document.createElement('tr'),cell=document.createElement('td');cell.colSpan=3;cell.className='empty-cell';cell.textContent=q?'Комнаты не найдены':'Нет ожидающих комнат. Создайте свою.';row.append(cell);list.append(row); }
    filtered.forEach(r=>{
      const row=document.createElement('tr');row.className='room-card';row.tabIndex=0;
      row.setAttribute('aria-selected',String(r.id===selectedRoom));row.dataset.unavailable=String(r.phase!=='waiting'||r.players>=r.capacity);
      for(const text of [r.title,`${r.players}/${r.capacity}`,r.phase==='waiting'?(r.players>=r.capacity?'Полная':'Ожидает'):r.phase==='interrupted'?'Прервана':'Игра']) { const cell=document.createElement('td');cell.textContent=text;row.append(cell); }
      row.title=`${r.title} · ${r.host}`;
      row.onclick=()=>{selectedRoom=r.id;renderList();};
      row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectedRoom=r.id;renderList();$('join-selected').focus();}};
      row.ondblclick=()=>{selectedRoom=r.id;joinSelected();};list.append(row);
    });
  }
  async function joinSelected() {
    const selected=rooms.find(r=>r.id===selectedRoom);
    if(!selected||selected.phase!=='waiting'||selected.players>=selected.capacity)return;
    try { await connect();send({type:'join',room:selected.id}); } catch(e) {notice(e.message);}
  }
  function openTavern() { tavern.hidden=false;document.body.classList.add('tavern-open');$('open-tavern').setAttribute('aria-expanded','true');refresh(); }
  function closeTavern() { tavern.hidden=true;document.body.classList.remove('tavern-open');$('open-tavern').setAttribute('aria-expanded','false');$('canvas').focus({preventScroll:true}); }
  $('open-tavern').onclick=()=>tavern.hidden?openTavern():closeTavern();
  $('close-tavern').onclick=closeTavern;$('refresh-rooms').onclick=refresh;$('room-filter').oninput=renderList;$('phase-filter').onchange=renderList;
  $('join-selected').onclick=joinSelected;
  $('show-create').onclick=()=>{$('create-room').hidden=false;$('room-name').focus();};
  $('cancel-create').onclick=()=>{$('create-room').hidden=true;};
  $('create-room').onsubmit=async e=>{e.preventDefault();try{await connect();send({type:'create',title:$('room-name').value,capacity:Number($('capacity').value),private:$('visibility').value==='private'});}catch(e){notice(e.message);}};
  $('join-invite').onclick=async()=>{try{await connect();send({type:'join',...invitation});}catch(e){notice(e.message);}};
  $('copy-invite').onclick=async()=>{ $('invite-link').hidden=false; try{await navigator.clipboard.writeText($('invite-link').value);notice('Приглашение скопировано');}catch{$('invite-link').select();notice('Скопируйте выделенную ссылку');} };
  $('leave-room').onclick=()=>{try{send({type:'leave'});}catch(e){notice(e.message);}};
  $('ready').onclick=async()=>{
    $('ready').disabled=true;
    try { if(window.homm3Boot.running)throw new Error('Для сетевой партии откройте игру заново. Текущую одиночную игру сначала сохраните.');
      const ready=!room.players.find(p=>p.id===me)?.ready;
      if(ready) { notice('Готовим ваши ресурсы и проверяем версию…'); await window.homm3Boot.prepare(); }
      send({type:'ready',ready,build:window.homm3Build || ''});notice(ready?'Готовы. Хозяин комнаты может начать выбор сценария.':'');
    }catch(e){notice(e.message);$('ready').disabled=false;}
  };
  $('launch-room').onclick=()=>{try{send({type:'launch'});}catch(e){notice(e.message);}};
  // JS and Rust both count Unicode code points; HTML maxlength counts UTF-16 units.
  $('chat-input').oninput=()=>{ const chars=Array.from($('chat-input').value); if(chars.length>300)$('chat-input').value=chars.slice(0,300).join('');$('chat-count').textContent=Math.min(300,chars.length)+'/300'; };
  $('chat-form').onsubmit=e=>{
    e.preventDefault(); const text=$('chat-input').value.trim();
    if(!text || pendingChat!==null || Date.now()<chatBlockedUntil)return;
    if(Array.from(text).length>300){$('chat-error').textContent='Не больше 300 символов';return;}
    try{send({type:'chat',text});pendingChat=text;updateChatButton();}catch(e){$('chat-error').textContent=e.message;}
  };
  // Keep browser text entry out of SDL's global keyboard handlers.
  for(const event of ['keydown','keyup','keypress']) window.addEventListener(event,e=>{if(e.target.closest('#tavern') || e.target.matches('input,textarea,select,button,a'))e.stopImmediatePropagation();},true);
  setInterval(()=>{if(socket?.readyState===WebSocket.OPEN)send({type:'ping'});},15000);
  setInterval(()=>{if(!tavern.hidden)refresh();},5000);
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
  if(invitation){$('join-invite').hidden=false;$('create-title').textContent='Вас пригласили в игру';openTavern();}
  else if(location.hash==='#multiplayer')openTavern();
  if(token)connect().catch(e=>notice(e.message));
})();
