/* The original C++ windows own presentation. This module carries only typed
 * commands, filtered server projections, and server-issued decision tokens. */
(() => {
  'use strict';
  const i32 = v => Number.isInteger(v) && v >= -2147483648 && v <= 2147483647;
  const revision = v => Number.isSafeInteger(v) && v >= 0;
  let active = false, stopped = false, ready = false, actor = -1, connected=true, lastError='';
  let appliedRevision = -1, nextRevision = -1, packet = null, copying = null;
  let sequence = 0, transport = null, choice = null, presenting = null, generation = null;
  const randomWords=new Uint32Array(4);
  if(window.crypto?.getRandomValues)window.crypto.getRandomValues(randomWords);
  else for(let i=0;i<4;++i)randomWords[i]=Math.floor(Math.random()*4294967296);
  const pageNonce=Array.from(randomWords,n=>n.toString(16).padStart(8,'0')).join('');
  const diagnosticEvents=[];
  function diagnostic(kind,details={}){diagnosticEvents.push({at:Math.round(globalThis.performance?.now?.()??Date.now()),kind,...details});if(diagnosticEvents.length>24)diagnosticEvents.shift();}
  const requests = new Map(), wireTickets=new Map();
  const uiEvents=[], seenUIResults=new Set(), answers=new Map();let choiceError='';
  const notices=[],seenNotices=new Set();let showingNotice=null;
  const adventureSounds=[];let lastAdventureSound=0;
  const combatResults=[], seenCombatResults=new Set();let currentCombatResult=null, preparedCombatResult=false, combatEnded=false, combatView=null, combatPresentedAt=0, combatStopRequested=false, combatRendererIsReady=false;
  let combatAnimating=false, combatOpening=null, preparedOpening=false;
  let restoringOwnChoice=false, freshCombatResume=false;
  let battleRevision=-1, combatPacket=null, heldSpell=null, combatObservation=null, combatPreparedChoice=false;
  function fail(message) {
    stopped = true;lastError=String(message);
    window.homm3AuthorityStatus = {error: true, message: String(message)};
    for (const request of requests.values()) request.result = -1;
    window.homm3Boot?.fail?.(String(message));
  }
  function receive(message) {
    if (!active || stopped || !message || typeof message !== 'object') return false;
    const type = message.type;
    diagnostic(type,{revision:message.revision??message.state?.revision,choice:message.kind,token:message.token});
    if(type!=='authority_ready' && generation!==null && message.generation!==generation) return false;
    if (type === 'authority_ready') {
      if (!i32(message.actor) || message.actor<0 || message.actor>7 || message.generation==null) {fail('Invalid authority session');return false;}
      if(generation!==null && generation!==message.generation){fail('Authoritative session changed; reload the selected map');return false;}
      if(actor>=0 && actor!==message.actor){fail('Authoritative seat changed');return false;}
      // A new page restores the pending choice; a transport reconnect keeps
      // the existing renderer and its animation watermark. Older relays send
      // a stale opening before the owner's current battle choice.
      if(generation===null){
        freshCombatResume=message.phase==='choice'||message.phase==='combat';
        restoringOwnChoice=message.choiceActor===message.actor && message.choiceKind==='combat';
      }
      actor=message.actor;generation=message.generation;connected=true;
      window.homm3AuthorityStatus={...window.homm3AuthorityStatus,error:false,phase:message.phase??window.homm3AuthorityStatus?.phase,activeActor:message.activeActor??window.homm3AuthorityStatus?.activeActor,revision:message.revision??appliedRevision,actor};
      return true;
    }
    if (type === 'authority_status') {
      window.homm3AuthorityStatus={...window.homm3AuthorityStatus,error:false,phase:message.phase,activeActor:message.activeActor,revision:message.revision};return true;
    }
    if (type === 'authority_state' || type === 'state') {
      const data = message.state || message;
      if (data.schema !== 1 || !revision(data.revision) || !Array.isArray(data.words) ||
          data.words.length < 17 || data.words.length > 4000000 || !data.words.every(i32) ||
          data.words[0] !== 1 || !i32(data.actor) || data.actor < 0 || data.actor > 7 ||
          data.words[1] !== data.actor || (actor >= 0 && actor !== data.actor)) {
        fail('Invalid authoritative projection'); return false;
      }
      if (data.revision < Math.max(appliedRevision, nextRevision)) return true;
      actor = data.actor; nextRevision = data.revision; packet = data;
      return true;
    }
    if (type === 'authority_result' || type === 'authority_answer_result') {
      const resultKey=String(message.id);
      const answered=answers.get(resultKey);
      if(answered){answers.delete(resultKey);if(!message.ok){lastError=choiceError=String(message.error||'Decision rejected');if(!choice&&!presenting)choice=answered;}}
      if(message.ok && Array.isArray(message.uiEvents) && !seenUIResults.has(resultKey)){
        seenUIResults.add(resultKey);if(seenUIResults.size>2048)seenUIResults.delete(seenUIResults.values().next().value);
        for(const event of message.uiEvents){
          if(event.actor!==actor || !['open_town','hero_exchange','resource'].includes(event.kind) || !i32(event.id) || !i32(event.other??-1)){fail('Invalid deferred interface event');return false;}
          if(event.kind==='resource' && (event.id<0 || event.id>6 || typeof event.text!=='string' || event.text.length>65536 || [...event.text].some(c=>c.charCodeAt(0)>255))){fail('Invalid resource presentation');return false;}
          uiEvents.push(event);
        }
      }
      const request = requests.get(wireTickets.get(String(message.id)));
      if (request) {
        if (message.ok && !revision(message.revision)) {fail('Invalid command revision'); return false;}
        request.result = message.ok ? 1 : -1;
        request.revision = message.revision;request.error=String(message.error||'Command rejected');
        if (!message.ok) window.homm3AuthorityStatus = {error: true, message: String(message.error || 'Command rejected')};
      }
      return true;
    }
    if(type==='authority_combat_result') {
      if(message.actor!==actor || typeof message.id!=='string' || !message.data || message.data.schema!==1){fail('Invalid combat result');return false;}
      if(seenCombatResults.has(message.id)){transport({type:'authority_seen',generation,id:message.id});return true;}
      if(currentCombatResult?.id===message.id||combatResults.some(event=>event.id===message.id))return true;
      if(combatResults.length>=32){fail('Too many pending combat results');return false;}
      combatResults.push(message);return true;
    }
    if(type==='authority_combat_state') {
      const data=message.state||message;
      if(data.actor!==actor || !data.data || data.data.schema!==1 || data.data.canAct!==false){fail('Invalid combat observation');return false;}
      if(battleRevision<0&&!combatOpening)combatOpening=data;
      combatObservation=data;return true;
    }
    if (type === 'authority_choice') {
      const data = message.choice || message;
      if (!revision(data.token) || data.actor !== actor || !Array.isArray(data.options) ||
          !data.options.length || !data.options.every(i32) || typeof data.kind !== 'string') {
        fail('Invalid authoritative choice'); return false;
      }
      if (presenting?.token === data.token || choice?.token === data.token) return true;
      if(freshCombatResume){
        if(data.kind==='combat' && battleRevision<0){combatOpening=null;combatObservation=null;}
        restoringOwnChoice=false;freshCombatResume=false;
      }
      choice = data;
      if (data.kind==='combat_spell' && heldSpell) {
        presenting=choice;choice=null;
        const action=(presenting.data?.actions||[]).find(a=>a.action===heldSpell[0] && a.hex===heldSpell[1] && a.extra===heldSpell[2] && a.hex2===heldSpell[3]);
        heldSpell=null;
        if(action) window.homm3Authority.answer(action.id);
        else {const cancel=(presenting.data?.actions||[]).find(a=>a.action===102);if(cancel)window.homm3Authority.answer(cancel.id);else fail('Spell target no longer available');}
      }
      return true;
    }
    if (type === 'authority_error' || type === 'authority_fault') {fail(message.error || message.message || 'Authority disconnected'); return true;}
    return false;
  }
  function send(op, id=0, a=0, b=0, c=0, d=0, e=0) {
    if (!active || stopped || !connected || !ready || appliedRevision < 0 || requests.size || generation==null || window.homm3AuthorityStatus?.eliminated || window.homm3AuthorityStatus?.finished ||
        ![op,id,a,b,c,d,e].every(i32)) return 0;
    const ticket = ++sequence;
    if (!Number.isSafeInteger(ticket)) {fail('Command counter exhausted'); return 0;}
    const wireId=pageNonce+':'+ticket;wireTickets.set(wireId,String(ticket));
    requests.set(String(ticket), {result: 0, revision: null, started: Date.now(),wireId,op});
    diagnostic('command',{op,id,a,b,c,d,e});
    try {transport({type:'authority_command', generation, id:wireId, revision:appliedRevision, command:{op,id,a,b,c,d,e}});}
    catch (error) {fail(error.message);}
    return ticket;
  }
  window.homm3Authority = {
    get active() {return active;},
    get fatal(){return stopped;},
    get eliminated(){return !!(copying||packet||window.homm3AuthorityStatus)?.eliminated;},
    get finished(){return !!(copying||packet||window.homm3AuthorityStatus)?.finished;},
    get lastError(){return lastError;},
    get actor() {return actor;},
    get turnTransfer() {
      if(!connected)return 2;
      // End-turn acknowledgement can be delayed by the next player's choice.
      // Once the server names a different actor, display that actor, not a
      // fictitious transfer that lasts for their entire turn.
      if(window.homm3AuthorityStatus?.activeActor!==actor)return 0;
      return [...requests.values()].some(r=>r.op===5&&!r.result)?1:0;
    },
    get revision() {return appliedRevision;},
    get pendingChoice(){return presenting?{token:presenting.token,kind:presenting.kind,presenting:true}:choice?{token:choice.token,kind:choice.kind,presenting:false}:null;},
    start(sendMessage) {
      if (active) throw new Error('Authority client already started');
      if (typeof sendMessage !== 'function') throw new Error('Missing authority transport');
      transport=sendMessage;active=true;stopped=false;
    },
    receive, send, fail,
    diagnostics(){
      return {schema:1,build:typeof window.homm3Build==='string'?window.homm3Build.slice(0,128):null,
        browser:navigator.userAgent.slice(0,300),viewport:[innerWidth,innerHeight,devicePixelRatio],
        actor,revision:appliedRevision,nextRevision,connected,stopped,lastError:lastError.slice(0,300),
        choice:this.pendingChoice,battleRevision,combatAnimating,combatRendererIsReady,
        combatRound:combatView?.round,combatSerial:combatView?.serial,requests:requests.size,
        queues:{state:!!packet,copying:!!copying,results:combatResults.length,ui:uiEvents.length},events:diagnosticEvents.slice()};
    },
    nativeReady(map, setup) {
      ready=true;
      const n=window.homm3Network;
      if(generation===null && n && n.self===n.host) transport({type:'authority_start',map:String(map||''),setup});
    },
    pendingLength() {return stopped || !packet || copying ? 0 : packet.words.length;},
    copyPending(heap, offset) {
      if (!packet || copying) throw new Error('No pending projection');
      copying=packet;packet=null;heap.set(copying.words, offset);
    },
    applied() {
      if (!copying) {fail('Projection acknowledgement without state');return;}
      for(const sound of copying.adventureSounds||[]){
        if(!Number.isSafeInteger(sound.id)||sound.id<1||typeof sound.name!=='string'||!/^[-A-Za-z0-9_.]{1,80}$/.test(sound.name)){fail('Invalid adventure sound');return;}
        if(sound.id>lastAdventureSound){if(appliedRevision>=0)adventureSounds.push(sound.name);lastAdventureSound=sound.id;}
      }
      if(adventureSounds.length>128){fail('Adventure sound queue overflow');return;}
      for(const notice of copying.notices||[]){
        if(!Number.isSafeInteger(notice.id)||notice.id<1||!Array.isArray(notice.textBytes)||notice.textBytes.length>65536||!notice.textBytes.every(v=>Number.isInteger(v)&&v>=0&&v<=255)){fail('Invalid outcome notice');return;}
        if(!seenNotices.has(notice.id)){seenNotices.add(notice.id);notices.push(notice);}
      }
      diagnostic('applied',{revision:copying.revision});
      const outcome=copying.outcome||0;
      const activeActor=copying.words[2],eliminated=!!copying.eliminated,finished=!!copying.finished;appliedRevision=copying.revision;copying=null;
      window.homm3AuthorityStatus={...window.homm3AuthorityStatus,error:false,message:'',revision:appliedRevision,actor,activeActor,eliminated,finished,outcome};
    },
    takeAdventureSound(bytes,capacity) {
      if(stopped||packet||copying||!adventureSounds.length)return 0;
      const name=adventureSounds[0];if(capacity<=name.length)return 0;
      adventureSounds.shift();for(let i=0;i<name.length;++i)bytes[i]=name.charCodeAt(i);bytes[name.length]=0;return 1;
    },
    result(ticket) {
      const request=requests.get(String(ticket));
      if (!request) return -1;
      // A command can wait for another human's battle or encounter choice
      // for an arbitrary time. Worker faults and transport reconnection own
      // liveness; a local wall-clock deadline must not abort that decision.
      if (!request.result || (request.result===1 && appliedRevision<request.revision)) return 0;
      if(request.result<0)lastError=request.error||lastError;requests.delete(String(ticket));wireTickets.delete(request.wireId);return request.result;
    },
    takeChoice(heap, offset, text, capacity, fieldsCapacity=16) {
      if (!choice || presenting || packet || copying || appliedRevision<0 || combatResults.length || currentCombatResult) return 0;
      if (!['normal','level_up','recruit','university','army_exchange','world_view','market','hill_fort','map_tavern','sacrifice','guild','hero_exchange','puzzle','shipyard'].includes(choice.kind)) {if(!['combat','combat_spell'].includes(choice.kind))fail('Unknown authoritative choice: '+choice.kind);return 0;}
      presenting=choice;choice=null;
      const d=presenting.data || {};let fields;
      if (presenting.kind==='normal') fields=Array.isArray(d.icons)&&d.icons.length>3?[11]:[1,d.mbType??1,d.special??-1,...Array.from({length:3},(_,i)=>d.icons?.[i]||[-1,0]).flat(),d.x??-1,d.y??-1];
      else if(presenting.kind==='level_up') fields=[2,d.hero,d.primary,...(d.skills||[])];
      else if(presenting.kind==='recruit'){
        if(!Array.isArray(d.creatures)||d.creatures.length<1||d.creatures.length>4){fail('Invalid recruitment offers');return 0;}
        fields=[3,d.heroId,+!!d.warMachines,d.creatures.length];
        for(let i=0;i<4;++i)fields.push(d.creatures[i]?.id??-1,Math.min(32767,d.creatures[i]?.available??0));
      }else if(presenting.kind==='university') fields=[4,d.heroId,d.cost,...(d.skills||[]),+(d.townUniversity===true)];
      else if(presenting.kind==='army_exchange'){
        if(!Array.isArray(d.other)||d.other.length!==7){fail('Invalid army exchange');return 0;}
        fields=[5,d.heroId,+(d.window==='join'),d.flags??0,d.otherOwner??-1,+!!d.canTake,+!!d.canGive,...d.other.flat()];
      }else if(presenting.kind==='market'){
        if(!Array.isArray(d.artifacts)||d.artifacts.length!==7){fail('Invalid market inventory');return 0;}
        fields=[7,d.heroId,d.townId,d.source,d.count,d.window,...d.artifacts];
      }else if(presenting.kind==='hill_fort')fields=[8,d.heroId];
      else if(presenting.kind==='map_tavern')fields=[9,d.heroId];
      else if(presenting.kind==='sacrifice')fields=[10,d.heroId];
      else if(presenting.kind==='hero_exchange')fields=[13,d.leftHero,d.rightHero,d.giver,+!!d.finalPass];
      else if(presenting.kind==='shipyard'){if(!i32(d.townType)||d.townType<0||d.townType>8){fail('Invalid shipyard type');return 0;}fields=[16,d.townType];}
      else if(presenting.kind==='guild')fields=[14,0];
      else if(presenting.kind==='puzzle'){if(!Number.isInteger(d.revealed)||d.revealed<0||d.revealed>48){fail('Invalid puzzle reveal count');return 0;}fields=[15,d.alignment,592,544,d.revealed];}
      else fields=[6,d.spell,d.level];
      if (!fields.every(i32) || !Number.isInteger(fieldsCapacity) || fieldsCapacity<1 || fieldsCapacity>64 || fields.length>fieldsCapacity) {fail('Invalid choice fields');return 0;}
      heap.fill(0,offset,offset+fieldsCapacity);heap.set(fields,offset);
      // Source text is encoded as byte-valued code points by the worker's
      // JSON quoting. Preserve the game's CP1251 bytes, not UTF-8 bytes.
      const value=String(presenting.text||'');
      const n=Math.min(value.length,capacity-1);
      for(let i=0;i<n;++i)text[i]=value.charCodeAt(i)&255;text[n]=0;
      return fields[0];
    },
    combatLength() {
      if(stopped || currentCombatResult || copying || (battleRevision<0&&packet) || (presenting && !combatResults.length)) return 0;
      if(restoringOwnChoice && combatOpening && !combatResults.length)return 0;
      const candidate=combatOpening || combatResults[0] || (choice?.kind==='combat'?choice:combatObservation);
      if(!candidate)return 0;
      // A running battle owns its own projection. World snapshots queued at
      // choice boundaries are applied after closing the battle window.
      const d=candidate.data;preparedOpening=candidate===combatOpening;combatPreparedChoice=candidate===choice;preparedCombatResult=candidate===combatResults[0];
      if(!d || d.schema!==1 || !Array.isArray(d.cells) || d.cells.length!==187) {fail('Invalid battle projection');return 0;}
      const out=[d.round,d.side,d.actingSide,d.actingSlot,+d.tactics,...d.point,d.terrain,d.magicTerrain,d.town,d.fortification,d.drawbridge,+d.surrounded,d.largeObstacle,...d.players];
      for(const h of d.heroes){
        out.push(h.id,h.mana,h.class??0,h.owner??-1,h.level??0,h.portrait??0,h.formation??0,...(h.stats||[0,0,0,0]));
        const own=Array.isArray(h.skills);out.push(+own);
        if(own){out.push(...h.skills,...h.spellbook,...h.available);for(const artifact of h.equipped)out.push(...artifact);}
      }
      out.push(...d.spellsCast,d.placementDepth,d.stacks.length);
      for(const a of d.stacks){
        out.push(a.side,a.slot,a.creature,a.count,a.hex,a.damage,a.flags|0,a.facing,a.originalIndex,a.originalCount,a.attack,a.defense,a.speed,a.hp,a.shots,a.morale,a.luck,a.retaliations,a.effects.length);
        for(const effect of a.effects)out.push(...effect);
        const modifiers=a.modifiers||Array(25).fill(0),order=a.effectOrder||a.effects.map(effect=>effect[0]);
        if(!Array.isArray(modifiers)||modifiers.length!==25||!modifiers.every(i32)||!Array.isArray(order)||order.length>81||!order.every(spell=>i32(spell)&&spell>=0&&spell<81)){fail('Invalid combat display modifiers');return 0;}
        out.push(...modifiers,order.length,...order);
      }
      out.push(d.walls.length,...d.walls,d.obstacles.length);
      for(const o of d.obstacles){out.push(o.hex,o.owner,o.duration,o.sprite.length);for(const ch of o.sprite)out.push(ch.charCodeAt(0));}
      out.push(d.cells.length);for(const cell of d.cells){if(cell.length!==49){fail('Invalid combat cell');return 0;}out.push(...cell);}
      const events=d.presentation||[];
      if(![1,2].includes(d.presentationVersion??1)||!Array.isArray(events)||events.length>256||!events.every((e,i)=>Array.isArray(e)&&e.length===12&&e.every(i32)&&e[0]>0&&(i===0||e[0]===events[i-1][0]+1)&&e[1]>=1&&e[1]<=((d.presentationVersion??1)===2?12:9)&&(e[1]!==9||(e[6]>=0&&e[6]<81))&&(e[1]!==10||(e[6]===0||e[6]===1))&&(e[1]!==12||(e[6]>=-1&&e[6]<83&&(e[7]===0||e[7]===1)&&e[8]>=0&&e[8]<2097152&&e[9]>=0&&e[9]<2097152))&&e[2]>=0&&e[2]<=1&&e[3]>=0&&e[3]<21)){fail('Invalid battle presentation journal');return 0;}
      out.push(events.length,...events.flat());
      if(out.length>65536 || !out.every(i32)){fail('Invalid battle integer');return 0;}
      combatPacket=out;combatView=d;return out.length;
    },
    takeCombat(heap,offset) {
      if(!combatPacket)throw new Error('No battle projection');
      if(preparedOpening){if(combatObservation===combatOpening)combatObservation=null;combatOpening=null;}
      else if(preparedCombatResult){currentCombatResult=combatResults.shift();if(presenting?.kind==='combat')presenting=null;}
      else if(combatPreparedChoice){presenting=choice;choice=null;}else combatObservation=null;
      heap.set(combatPacket,offset);combatPacket=null;freshCombatResume=false;
      combatPresentedAt=Date.now();combatEnded=false;if(battleRevision<0)battleRevision=appliedRevision;
    },
    get combatRendererReady(){return combatRendererIsReady;},
    get combatTactics(){return !!combatView?.tactics;},
    get combatPresentationVersion(){return combatView?.presentationVersion??1;},
    get combatSecondPhase(){return !!combatView?.secondPhase;},
    rendererReady(value){combatRendererIsReady=!!value;},
    presentationBusy(value){combatAnimating=!!value;diagnostic('animation',{busy:combatAnimating});},
    combatOffers(action){return !!presenting&&presenting.kind==='combat'&&presenting.data.actions.some(item=>item.action===action);},
    combatAuto(){return !!combatView?.autoCombat;},
    combatCanAuto(){return this.combatAuto()||!!combatView?.actions?.some(action=>action.action===103||action.action===104);},
    combatToggleAuto(){if(this.combatAuto()){combatStopRequested=true;if(this.combatCanAct()&&this.combatAction(104,-1,-1,-1)){combatStopRequested=false;return true;}return true;}return this.combatAction(103,-1,-1,-1);},
    combatAutoStep(){if(this.combatAuto() && this.combatCanAct() && this.combatOffers(combatStopRequested?104:103) && Date.now()-combatPresentedAt>=80){const sent=this.combatAction(combatStopRequested?104:103,-1,-1,-1);if(sent)combatStopRequested=false;return sent;}return false;},
    copyCombatSpellState(side,slot,heap,offset){const stack=combatView?.stacks?.find(s=>s.side===side&&s.slot===slot);if(!stack||!i32(stack.faerieDragonSpell)||!i32(stack.hasSpell))return 0;heap.set([stack.faerieDragonSpell,stack.hasSpell],offset);return 1;},
    copyCombatHeroName(side,bytes,capacity){const name=combatView?.heroes?.[side]?.nameBytes;if(!Array.isArray(name)||name.length>=capacity||!name.every(v=>i32(v)&&v>=0&&v<=255))return 0;bytes.set(name);bytes[name.length]=0;return 1;},
    combatResultLength(){
      if(!currentCombatResult)return 0;const d=currentCombatResult.data;
      const words=[d.winner,d.mySide,+d.siege,d.experience,+d.retreated,+d.surrendered];
      for(const h of d.heroes){const name=h.nameBytes||[];if(name.length>63||!name.every(v=>i32(v)&&v>=0&&v<=255)){fail('Invalid hero name');return 0;}words.push(name.length,...name);}
      const loot=d.loot||[],spells=d.eagleEye||[],raised=d.necromancy||{creature:-1,count:0};
      words.push(loot.length,...loot.flat(),spells.length,...spells,raised.creature,raised.count);
      if(words.length>512||!words.every(i32)){fail('Invalid combat result fields');return 0;}return words.length;
    },
    copyCombatResult(heap,offset){
      const d=currentCombatResult.data,words=[d.winner,d.mySide,+d.siege,d.experience,+d.retreated,+d.surrendered];
      for(const h of d.heroes){const name=h.nameBytes||[];words.push(name.length,...name);}
      words.push(d.loot.length,...d.loot.flat(),d.eagleEye.length,...d.eagleEye,d.necromancy.creature,d.necromancy.count);heap.set(words,offset);
    },
    combatResultShown(){
      if(!currentCombatResult)return;const id=currentCombatResult.id;seenCombatResults.add(id);
      if(seenCombatResults.size>128)seenCombatResults.delete(seenCombatResults.values().next().value);
      currentCombatResult=null;combatEnded=true;combatObservation=null;heldSpell=null;combatStopRequested=false;
      transport({type:'authority_seen',generation,id});
    },
    combatCanAct() {return connected && !combatAnimating && !!presenting && presenting.kind==='combat' && !stopped && !currentCombatResult && !combatResults.length;},
    combatWindowClosed() {
      // Results return straight out of the native modal, bypassing the next
      // combatFinished poll. Never carry that battle's revision into a new one.
      battleRevision=-1;combatEnded=false;combatAnimating=false;combatRendererIsReady=false;
      combatView=null;combatObservation=null;combatOpening=null;combatPacket=null;heldSpell=null;
      preparedOpening=false;preparedCombatResult=false;combatPreparedChoice=false;combatStopRequested=false;
    },
    combatFinished() {
      if(!stopped&&(combatResults.length||currentCombatResult))return false;
      const done=stopped || combatEnded || (choice && !['combat','combat_spell'].includes(choice.kind)) || (packet && packet.revision>battleRevision);
      if(done){battleRevision=-1;heldSpell=null;combatObservation=null;}return !!done;
    },
    combatAction(action,hex,extra,hex2) {
      if(!this.combatCanAct())return false;
      const offered=presenting.data.actions;
      if([3,4,8,100,103,104].includes(action)){hex=-1;extra=-1;hex2=-1;}
      if([2,6,7,9,10,11].includes(action))hex2=-1;
      if(action===5){hex=-1;hex2=-1;}
      if(action===1){
        // Teleport and Sacrifice use the second target. Reflection belongs
        // to the authority; never submit a locally randomized mirror target.
        if(![63,40].includes(extra))hex2=-1;
        const select=offered.find(a=>a.action===101 && a.extra===extra);
        if(select){heldSpell=[action,hex,extra,hex2];return this.answer(select.id);}
      }
      const selected=offered.find(a=>a.action===action && a.hex===hex && a.extra===extra && a.hex2===hex2);
      if(!selected){window.homm3AuthorityStatus={error:true,message:'Action is not available in the current server battle state'};return false;}
      return this.answer(selected.id);
    },
    normalIconsLength(){const icons=presenting?.data?.icons;if(!Array.isArray(icons)||icons.length>2048||!icons.every(pair=>Array.isArray(pair)&&pair.length===2&&pair.every(i32))){fail('Invalid extended dialog resources');return -1;}return icons.length*2;},
    copyNormalIcons(heap,offset){heap.set(presenting.data.icons.flat(),offset);},
    guildWordsLength(){const words=presenting?.kind==='guild'?presenting.data?.words:null;if(!Array.isArray(words)||words.length>65536||!words.every(i32)){fail('Invalid guild projection');return 0;}return words.length;},
    copyGuildWords(heap,offset){heap.set(presenting.data.words,offset);},
    worldSpell(){return presenting?.kind==='world_view'?presenting.data.spell:-1;},
    copyPuzzlePixels(heap,offset,capacity){
      const d=presenting?.kind==='puzzle'?presenting.data:null;
      if(!d||d.width!==592||d.height!==544||d.encoding!=='rgb565le-base64'||typeof d.pixels!=='string'||d.pixels.length!==858796||capacity!==592*544||offset<0||offset+capacity>heap.length||!/^[A-Za-z0-9+/]+=$/.test(d.pixels))return 0;
      const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';let value=0,bits=0,bytes=0,low=0;
      for(let i=0;i<d.pixels.length-1;++i){value=(value<<6)|alphabet.indexOf(d.pixels[i]);bits+=6;if(bits>=8){bits-=8;const byte=(value>>>bits)&255;if(bytes&1)heap[offset+(bytes>>1)]=low|(byte<<8);else low=byte;++bytes;}}
      return bytes===capacity*2?capacity:0;
    },
    worldMarkersLength(){return presenting?.kind==='world_view' ? presenting.data.markers.length : 0;},
    copyWorldMarkers(heap,offset){const markers=presenting?.data?.markers;if(!Array.isArray(markers)||markers.length>1000000||!markers.every(i32))throw new Error('Invalid world markers');heap.set(markers,offset);},
    takeNotice(text,capacity){
      if(showingNotice||!notices.length||choice||presenting||packet||copying||combatResults.length||currentCombatResult||combatObservation||combatPacket)return 0;
      showingNotice=notices.shift();const bytes=showingNotice.textBytes,n=Math.min(bytes.length,capacity-1);text.set(bytes.slice(0,n));text[n]=0;return 1;
    },
    noticeShown(){showingNotice=null;},
    takeChoiceError(text,capacity){if(!choiceError)return 0;const value=choiceError;choiceError='';const n=Math.min(value.length,capacity-1);for(let i=0;i<n;++i)text[i]=value.charCodeAt(i)&255;text[n]=0;return 1;},
    takeUIEvent(heap,offset,text,capacity) {
      if(stopped || requests.size || packet || copying || choice || presenting || battleRevision>=0 || !uiEvents.length)return 0;
      const event=uiEvents[0];
      if(event.kind==='resource'&&(!text||!Number.isInteger(capacity)||capacity<=event.text.length||capacity>text.length)){fail('Resource presentation buffer too small');return 0;}
      uiEvents.shift();heap.set([event.kind==='open_town'?1:event.kind==='resource'?3:2,event.id,event.other??-1],offset);
      if(event.kind==='resource'){for(let i=0;i<event.text.length;++i)text[i]=event.text.charCodeAt(i);text[event.text.length]=0;}return 1;
    },
    answer(value,a=0,b=0) {
      if (!presenting || !presenting.options.includes(value) || !i32(a) || !i32(b)) {fail('Choice outside server options');return false;}
      const token=presenting.token,id=pageNonce+':'+(++sequence);answers.set(id,presenting);presenting=null;
      diagnostic('answer',{token,value,a,b});transport({type:'authority_answer',generation,id,token,value,a,b});return true;
    },
    disconnect() {connected=false;window.homm3AuthorityStatus={error:true,message:'Connection lost; waiting to reconnect'};}
  };
})();
