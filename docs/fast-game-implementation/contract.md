# Fast game prototype integration contract

The simultaneous prototype runs on ordinary maps, including hiring and combat, with opt-in gameplay rules. The room switch defaults off. Legacy off paths remain unchanged. Prototype rule: original AI resolves all encounters and mandatory event/level choices automatically. All humans can submit commands at any time; one original C++ authority executes short commands against one canonical world. Players finish day individually; AI phase and new day run after all humans finish.

Host's existing visible WASM is authority after the original network scenario/start handshake. Native map, town, tavern and recruitment windows submit authenticated intents and wait for canonical confirmation instead of applying a second local mutation. The JavaScript bridge is transport only; it does not add controls or intercept native input. Selection and camera remain local. Guests import snapshots from the event pump, including while native town/recruitment dialogs are open. Original player context, selection, camera, dialog result and canvas are restored after each command. Canonical execution cannot publish another actor's pixels. Town pool addresses stay stable within a match; unsupported state-changing dialogs remain read-only or show an in-game explanation.

Returning to a friendly town opens its original window on the requesting client. It does not invoke AI purchasing for human players. Finishing the day uses the original end-turn control; waiting status appears in the original status bar.

Native bridge `window.homm3FastNative` (defined by fast-game.js before running):
- `take()`: returns next Int32 array `[opcode,actor,id,a,b,c,seq,day]` or null. Native polls from the event pump, including modal windows, with a reentrancy guard.
- opcodes: 1 MOVE (id=heroId,a=direction0..7); 2 BUILD (id=townId,a=buildingId); 3 HIRE (id=townId,a=heroId); 4 RECRUIT (id=townId,a=dwellingSlot,b=count); 5 NEXT_DAY (authority only, no user actor); 6 APPLY_SNAPSHOT (c=terminal flag, file `/runtime/fast-incoming.gm2` written by JS); 7 SELECT_HERO (local id); 8 SELECT_TOWN (local id); 9 PAN (a=dx,b=dy); 10 EXPORT (initial or local projection query).
- `request(op,id,a,b)` returns a ticket for a native UI intent; `result(ticket)` is pending (0), accepted (1), or rejected (-1). Guest acceptance waits for the matching snapshot revision, so native callers resume against committed world state. End-day acceptance uses the ready list/day transition.
- `started(localSlot,isAuthority)`: native called once after original network handshake at adventure entry, only if room.fastGame.
- `complete(meta, bytes)`: native command result. meta `{seq,ok,error,day,gameOver,view}`. `view` includes own-independent world stats below. bytes Uint8Array of valid canonical save, or null for view-only ops. Initial export seq0; command seq from backend. JS must copy bytes before WASM memory changes.
- `projection(view)`: view-only refresh after local select/pan or snapshot import.
- `fault(message)`: interrupt fast mode visibly; don't fall back to legacy.
- `canRun`: optional bool prevents processing engine command before room init.


View shape (initial goal): `{day,week,month,absoluteDay,localPlayer,mapSize,camera:{x,y,z},players:[{slot,dpid,human,alive,name,resources:[7]}],heroes:[{id,owner,name,x,y,z,movement,mana,portrait,army:[{type,count}]}],towns:[{id,owner,name,x,y,z,type,buildings:[{id,name,allowed,cost:[7]}],offers:[{id,name}],creatures:[{slot,type,name,available,cost:[7]}]}]}`. Reuse original CP1251 text, decode to JS Unicode via TextDecoder windows-1251. Keep snapshot lean; may emit only owned town action choices for local view plus full player mapping. All clients compute their own projection after import, backend only needs absoluteDay and alive player slots.

Server protocol, only fastGame rooms:
- Legacy setup/launch/initial binary handshake unchanged until host fast initialization.
- Client JSON `{type:'fast_command',id:<unique<=64char>,day:<absoluteDay>,command:{kind:'move'|'build'|'hire'|'recruit'|'end_day',id,a,b}}`. Server derives authenticated actor slot from initial host roster, ignores spoofed actor. Bounded queue, dedup per session/day, one in-flight authority command, timeout interrupts. end_day closes actor submissions and contributes to day barrier. Full roster may include AI; only live human seats participate in barrier.
- Host initial binary snapshot metadata seq0 includes roster(view.players), absoluteDay; validates mapping covers room membership exactly; initializes authority state. Guest sent snapshots rejected. Client always sends named version1 magic.
- Server -> authority JSON `{type:'fast_execute',seq,actor,day,command}`. `advance_day` synthesized only by server at day barrier after queued commands settle. Engine executes AI and perDay once.
- Host -> server binary: u32 LE magic 0x31545346 ('FST1'), u32 LE JSON metadata length, UTF8 JSON metadata `{seq,ok,error,day,gameOver,roster:[{slot,dpid,human,alive}]}`, then canonical save bytes. Bounded sizes. Server validates expected seq and day progression, emits revision record and relays canonical packet to all INCLUDING authority (authority doesn't reload its own save).
- Server -> all JSON `{type:'fast_state',revision,day,ready:[slots],pending,interrupted?}` plus binary snapshot with same format and added `revision`. Result errors private to requester; no raw arbitrary engine control to nonauthority.
- Cross-mode misuse rejected; once fast session active legacy binary messages cannot mutate it. Disconnect/authority timeout interrupts rather than divergent local play. Legacy command/relay paths unchanged for fastGame=false/missing.


## Prototype limits and validation

The host's browser owns the engine; Rust coordinates and authenticates commands but does not simulate C++ rules. Host departure, any interrupted connection, malformed imports or authority timeout end the session. No reconnect/resume or host migration while playing yet. Full snapshots are visible to participants as in legacy networking; this is not an anti-cheat design. Manual map spells, artifact/army rearrangement and manual tactical combat are not implemented in the simultaneous command set. Mandatory choices and combat run automatically. Original interactive interfaces remain fully available when fastGame is false.

The native probe exercises real command paths for ownership/economy, shared hero-offer races, PvP and terminal imports. The browser smoke drives two actual WASM clients through simultaneous movement, town actions, neutral combat and day advancement; transport acknowledgements and snapshot ordering are tested separately.

Run with the companion homm3-lobby simultaneous branch. Node development serving and deployment bundle allowlists include fast-game.js; the production reverse-proxy allowlist must include this path before publishing. Keep client JS/WASM and relay protocol in the same rollout. No production deployment is performed by these tests.
