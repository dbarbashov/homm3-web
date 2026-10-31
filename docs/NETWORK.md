# Browser multiplayer

The site has a public room browser, capability-protected private rooms, invite
links, readiness, reconnect to a waiting lobby, and a persistent in-page chat
panel. Each participant runs a separate WASM engine with its own local player
and fog of war. There is no shared screen, remote input, or hot-seat substitute.

## Architecture

Browser UI → same-origin WebSocket → Rust Axum/Tokio room relay → other clients.
The existing C++ `CDPlayHeroes`, `CNetMsg`, scenario selection, save transfer,
adventure and combat handlers retain the game protocol and rules.
`port/platform/network.cpp` replaces the DirectPlay transport boundary. Legacy
modem/IPX/group/Windows lobby APIs explicitly report unsupported operations.

The server owns room membership, visibility, capacity, host permission, readiness,
phase and transport sender identity. It does not simulate Heroes III or implement
an authoritative anti-cheat engine. Only clients with the same SHA-256 fingerprint
of WASM and their LOD/SND files can start together. Maps are selected and initial
state is transmitted by the original C++ network flow.

JSON control protocol: hello, create, join, leave, chat, ready, launch, playing,
ping. Binary engine envelope: client `[destination:u32le, CNetMsg bytes]`; server
`[authenticated sender:u32le, destination:u32le, CNetMsg bytes]`. Destination 0
broadcasts to other members; 1–8 addresses a frozen participant roster. The
server never forwards to another room. Private invitation secrets occur in URL
fragments and authenticated room snapshots, never in the public room index.

Connections use bounded queues; oversized/rate-limited traffic closes the socket.
A full engine relay queue or a participant disconnect interrupts the match instead
of silently discarding a reliable message. Lobby reconnection uses a random token
in sessionStorage and a 90-second reservation. Match reconnection/recovery and
host migration during a running match are not implemented. The waiting lobby
can transfer its host when the original host leaves. Room/chat state is in memory
and disappears on server restart; the last 100 chat messages are retained.

Beta limits: 50 rooms, 256 simultaneous WebSockets; outgoing payload budgets of
8 MiB per socket and 64 MiB globally, including a write in flight. Payload storage
is shared across recipients. A socket write has a 15-second timeout. These limits
bound queues, not all process memory, and are not a 50-room capacity benchmark.

Chat accepts 1–300 Unicode code points, one attempt per 2 seconds and up to ten
accepted messages per rolling minute. Repeated messages (case/spacing/punctuation
ignored), 12 identical consecutive characters, hidden/control characters and more
than two explicit URL tokens are rejected. A room also has a shared budget of 20
messages per ten seconds. Session limits survive reconnects and room changes;
new guest identities can reset the individual limit, but not the shared room limit.
This is a simple flood filter, not semantic moderation or protection against a
distributed attack. Rejections are private and preserve the user's draft.

## Local development and deployment

The relay is a separate private repository. Maintainers may clone it next to this
client as `../homm3-lobby`, or set `HOMM3_LOBBY_ROOT`. `npm start` starts it when
present; otherwise the single-player client runs on its own. The development
proxy expects the relay at `127.0.0.1:8784`.

Use same-origin HTTP and WebSocket routes behind HTTPS in production. The public
client contains no server credentials, hosting configuration or deployment keys.
No GitHub action deploys to production. The maintainers release reviewed revisions
manually. Do not expose the Node development resource server to the Internet.

Create a room, share its invitation, and have each player click Ready. The host
starts the original network scenario selector and chooses a scenario that supports
enough human players. Some turn transitions require acknowledging the original
turn-start dialog. The tavern and room chat remain accessible from the game.

Optional `web/site/resources.json` defaults to `{"baseUrl":null}`. Hosted resource
catalogs are deployment configuration and must never be committed. Selecting a
local game folder overrides remote resources.

## Validation

`npm run test:site` covers public/private room UI, invitations, plain-text chat,
waiting-host migration and mobile layout. `npm run test:network` drives two
independent WASM clients through movement, turns, AI, battle and state transfer.
Both require a local relay, matching assets and a running frontend.

`python3 scripts/test-network-headers.py` checks 21 save-header round trips over
seven allocator patterns, including empty lobby headers and actual campaign data.
It requires the native SDL/FFmpeg build dependencies, but no game assets. Use
`--video-root` to point at an existing native FFmpeg installation.
`scripts/network-startup-smoke.py` checks two-client startup with `BROWSER=webkit`
or `chromium`, `HEADFUL=1`, `HD=1`, and `FAST=1` as optional switches. `FAULT=1`
injects the native-error event and checks visible failure, peer notification and
reload into a fresh room browser. `AUDIO_SINK=device` runs the real audio clock
through a zero-gain output; all test configurations remain inaudible.

Lobby map rows carry a save header even for new maps. Its campaign flag and
serialized defaults must be initialized: allocator garbage can make the writer
omit campaign bytes while the reader expects them, killing the guest and leaving
the host waiting at 98%. Native exceptions now show a reload screen and disconnect
the failed client. An interrupted setup also shows an error to the other players.

The relay's unit, isolation and capacity tests live with its private source.
Full eight-player PvP, long sessions and recovery after a dropped match remain
open validation areas. The relay verifies room membership and transport identity;
it does not validate every legacy C++ game message or prevent cheating by clients.

## Protocol notes

Control messages use UTF-8 JSON. `hello` supplies a nickname or reconnect token;
the response provides `id` and `token`. `create` accepts `title`, `capacity` and
`private`. `join` supplies a room ID and, for private rooms, its `invite` capability.
Room snapshots include players, readiness, host, phase and the last 100 messages.
A chat message includes `id`, `player`, `name`, `text` and server Unix `time` in
milliseconds. Clients render text without HTML interpretation. `chat_rejected`
errors contain a message and `retryAfterMs`, preserving the user's draft.

A `ready` message includes a build/asset fingerprint. Only the host can `launch`
a room with at least two ready online players. `ping` receives `pong`.
See `web/site/rooms.js` and `port/platform/network.cpp` for the client boundary.

## Fast-game room setting (development only)

The `fastGame` boolean defaults to false when absent. Room discovery, snapshots,
join/reconnect and host migration preserve the setting; it is fixed at creation.
The client exposes an unchecked “Быстрая игра” switch with an explanation.

Enabled rooms run the simultaneous prototype on ordinary maps. A host C++/WASM
engine applies authenticated commands ordered by the matching relay; snapshots
update each client. Players move, build and recruit during the same day. The next
day starts after all live human players finish. Combat and mandatory choices are
automatic. Fast rooms use the original map, town, tavern, recruitment and end-turn
controls; JavaScript only transports commands. The native event pump services
commands while dialogs remain open. Legacy rooms retain sequential turns.

The prototype remains opt-in and requires the companion relay branch. Manual
adventure spells, army/artifact rearrangement, reconnect/resume and long-session
validation remain open. See the README for the current implementation scope.
