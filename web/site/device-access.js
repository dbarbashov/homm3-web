/* Explicit, one-time access transfer. Credentials never appear in links. */
(() => {
  const $=id=>document.getElementById(id);
  if(!$('device-access'))return;
  let api, timer, pending=false;
  const buttons=['device-create','device-revoke','device-submit'];
  function status(message){$('device-status').textContent=message;}
  function busy(value){pending=value;for(const id of buttons)$(id).disabled=value;}
  function finish(message){clearTimeout(timer);busy(false);status(message);}
  async function command(type){
    if(pending)return;
    busy(true);status('Соединяемся…');
    timer=setTimeout(()=>finish('Сервер не ответил. Попробуйте ещё раз.'),15000);
    try{await api.command(type);}catch(error){finish(error.message);}
  }
  window.homm3Devices={
    available(value){$('device-owner').hidden=!value;},
    init(callbacks){api=callbacks;},
    receive(data){
      if(data.type==='device_code'){
        $('device-code').value=data.code.match(/.{1,8}/g).join('-');$('device-issued').hidden=false;
        $('device-expiry').textContent=`Действует до ${new Date(data.expires*1000).toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'})}. Использовать можно только один раз.`;
        finish('Введите этот код на новом устройстве.');
      }else if(data.type==='device_revoked'){
        $('device-issued').hidden=true;$('device-code').value='';finish('Доступ остальных устройств и выданные коды отозваны.');
      }else if(data.type==='device_error')finish(data.message);
    }
  };
  $('device-create').onclick=()=>command('device_create');
  $('device-revoke').onclick=()=>command('device_revoke');
  $('device-copy').onclick=async()=>{
    try{await navigator.clipboard.writeText($('device-code').value);status('Код скопирован.');}
    catch{$('device-code').select();status('Скопируйте выделенный код.');}
  };
  $('device-claim').onsubmit=async event=>{
    event.preventDefault();if(pending)return;
    const code=$('device-input').value.replace(/[\s-]/g,'').toLowerCase();
    if(!/^[0-9a-f]{32}$/.test(code)){status('Введите весь код из 32 символов.');$('device-input').focus();return;}
    busy(true);status('Переносим доступ…');
    try{await api.claim(code);$('device-input').value='';finish('Доступ перенесён. Выберите партию в «Моих партиях».');}
    catch(error){finish(error.message);}
  };
})();
