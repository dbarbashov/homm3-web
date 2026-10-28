# Heroes III — browser client

[Play at homm3.xyz](https://homm3.xyz) · [Contributing](CONTRIBUTING.md) · [Third-party notices](THIRD_PARTY.md)

An experimental C++ / WebAssembly port of Heroes III, based on
[sushi-shi/homm3-decomp](https://github.com/sushi-shi/homm3-decomp).
The recovered game engine runs in the browser through Emscripten and SDL2;
JavaScript provides the browser shell, storage, audio and network transport.

## What works

- Single scenarios: adventure map, towns, heroes, battles, AI turns and browser saves.
- All 20 Complete campaigns (RoE, AB and SoD), original unlock conditions, starting
  bonuses, scenario transitions, hero carry-over and campaign saves. Custom `.h3c` files
  are read from your selected installation.
- Original campaign movies, narration and the Authors/Credits screen.
- Adaptive adventure viewport, stable overlays, keyboard shortcuts, quick recruitment
  and army splitting. Touch supports a long press for the right mouse button.
- Optional smooth camera following during hero movement, with a saved toggle in the
  browser menu. The original instant movement setting still skips animation.
- Public/private multiplayer rooms, invitation links, readiness and in-game room chat.
  Every player runs an independent client; this is network play, not hot-seat.
- A compact tavern sidebar with room and chat tables. The game fills the available
  viewport; on phones the sidebar overlays it. Adding the site to the iPhone Home
  Screen removes Safari's browser bars.

The hosted service is experimental. Account registration,
cloud saves and reconnecting to an active match are not implemented. The relay is
not an authoritative anti-cheat server. Long sessions, eight-player PvP and all
scenarios have not been comprehensively tested. Keep backups of important saves.

## Game resources

**No original game assets are included in this repository.** You need your own
Heroes III installation. Select its folder in the browser, or configure the local
server as described below. Browser-selected files stay on your device.

Required: `Data/h3bitmap.lod`, `h3sprite.lod`, `h3ab_bmp.lod`, `h3ab_spr.lod`,
`heroes3.snd`. `Maps/` supplies `.h3m` scenarios and optional `.h3c` campaigns.
`h3ab_ahd.snd` and `Mp3/` provide additional sound and music; `Data/VIDEO.VID`
and `Data/H3ab_ahd.vid` supply original movies. Browser folder selection reads
only the requested video from each archive, without uploading the installation.
Original fonts, maps, artwork, music,
executables and archives must not be added to pull requests.

Graphics archives are loaded before play. Music and movies load on demand.
Idle frames reuse the composed scene; the renderer uploads only changed screen
regions. A 16 MiB bounded cache avoids repeated archive decompression. Browser decompression yields between short slices.
For a repeatable local performance trace, run `npm start`, then
`RUN=current CPU=4 python3 scripts/performance-browser-probe.py` with no other
browser tests running. Python Playwright with Chromium is required. `CPU=4` is
an artificial stress test, not an estimate of any particular player's hardware.
For ranged combat, run `CPU=4 python3 scripts/combat-performance-probe.py`.
Combat/audio probes use Chromium's silent output device; the real Web Audio graph
still runs without depending on the test machine's speakers.
It verifies the original ranged-attack wait for the sound to finish after impact.
Music uses the original fade-out/fade-in timing; the engine controls track changes. New combat preferences default to
fast animations; existing saved speed settings are preserved.

## Build and run locally

Tested on macOS ARM64. Install Git, Python 3, Node.js 22+, CMake 3.20+, Clang,
SDL2, zlib, Make and xz. The browser SDK revision is pinned in `port/toolchain.lock.json`.

```sh
git clone https://github.com/dbarbashov/homm3-web.git
cd homm3-web
python3 scripts/setup-port.py
python3 scripts/build-game.py --target web
npm start
```

Open **http://127.0.0.1:8783/** and select your game folder. No npm dependencies
are required. The build downloads the pinned upstream source, applies the
reviewable portability patch and compiles the real game modules. It also builds
a pinned minimal LGPL FFmpeg decoder; see [the notices](THIRD_PARTY.md#original-video-decoding)
for its source, license and replacement/relinking instructions.

To serve your installed game to local devices, create the ignored file
`.local/game.json`:

```json
{"gameRoot":"/absolute/path/to/your/Heroes III installation"}
```

The development server binds to the local network by default. Use `HOST=127.0.0.1
npm start` for local-only access. Do not expose this development asset server to
the Internet. LAN peers use `http://YOUR_LAN_IP:8783/`.

The optional original browser UI fonts can be generated from that configured
installation while the local server is running:

```sh
python3 -m pip install 'fonttools[woff]'
python3 scripts/build-ui-fonts.py
```

This produces an ignored `web/site/fonts.css`. Without it the UI uses system fonts.
The font conversion assumes the Cyrillic CP1251 edition; see `--encoding` for
other editions. Generated original glyphs are not licensed by this repository.

The crest and leather/metal textures in `web/site/*.webp` are generated artwork,
created with imagegen using the original UI as a visual reference. Prompts are in
`output/imagegen/`. The red-and-gold panel frame can additionally be rendered
from your own installation:

```sh
python3 -m pip install Pillow
python3 scripts/build-ui-skin.py
```

This creates an ignored `web/site/skin.css` with embedded original-resource
images; the current theme uses its frame. Those extracted assets stay outside
Git. Without them the frame uses its CSS fallback; the generated crest and
textures still work. The bundle includes both optional stylesheets when present.

### Multiplayer development

The room relay lives in a **separate private repository**. It is deliberately not
a dependency or submodule of this public client. Single-player development works
without it. Maintainers with access can clone it as a sibling `../homm3-lobby`;
`npm start` then starts both services. Set `HOMM3_LOBBY_ROOT` to use another path.

The client uses same-origin `/lobby/rooms`, `/lobby/socket` and `/lobby/health`.
The development proxy forwards those routes to `127.0.0.1:8784`. The protocol and
limitations are documented in [docs/NETWORK.md](docs/NETWORK.md), so frontend
contributions do not require access to server implementation details.

### Native build

```sh
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel 6
HOMM3_NATIVE_BINARY="$PWD/build/native/homm3-game" python3 scripts/run-game.py
```

On Homebrew installations CMake may need `-DCMAKE_PREFIX_PATH="$(brew --prefix sdl2)"`.
Native macOS is tested; Windows and Linux native game builds are not yet validated.
Configure/build native and browser targets sequentially: their prepared source
folder is shared.

## Checks

```sh
# Unit tests (no game assets or WASM build required):
npm test

# Browser integration (requires your assets and a running local server):
python3 -m pip install playwright pillow
python3 -m playwright install chromium webkit
npm run test:game
npm run test:site       # requires the optional relay
npm run test:network    # two independent clients; requires relay and matching assets
```

Rust is only needed for the private room relay; the game engine is C++. Browser test output goes to ignored `test-results/`.

## Source layout

| Path | Purpose |
| --- | --- |
| `port/` | C++ platform adapters, game entry, HD features and portability patch |
| `web/port/` | Browser boot, sound/music and game document |
| `web/site/` | Tavern, resources adapter, touch controls and styles |
| `lib/`, `server.mjs` | Local installation reader and development server |
| `scripts/`, `tests/` | Build tools and regression checks |
| `upstream.lock.json` | Exact upstream source revision |

## Saves and controls

Browser saves use IndexedDB for the current site and browser profile. Clearing
site data deletes them; they are not cloud saves. Browser folder selection needs
to be repeated after reload. Compatibility with retail saves is not guaranteed.

`E` ends a turn, `S` saves, `L` loads, `Esc` goes back. `R` opens quick recruitment;
`B` opens the market, `G` the guild, `Space` the garrison and `F10` army exchange
where available. The on-screen Menu exposes touch equivalents. Long press shows
right-click help. Army modifiers: Shift splits, Ctrl takes one, Ctrl+Shift creates
single units, Alt gathers; the last required creature is retained.

## Contributing and licensing

Small, focused pull requests are welcome. Include reproduction steps and relevant
validation; do not upload game resources, saves, credentials or generated builds.
There is **no automatic deployment from pull requests or GitHub pushes**. A
maintainer reviews and manually releases a specific revision.

New code in this repository is MIT licensed; recovered upstream code retains
CC0-1.0 and third-party components retain their own licenses. See [LICENSE](LICENSE)
and [THIRD_PARTY.md](THIRD_PARTY.md). This is an unofficial project, unaffiliated
with the original creators or rights holders. Source licenses do not grant rights
to the original game data or trademarks.

## Experimental simultaneous play

Room creators can enable **Быстрая игра** (off by default). Everyone submits
movement, building and recruitment commands to one canonical original engine;
the Rust relay validates actors and sequences commits. The day advances after
all live humans finish. Combat and mandatory choices resolve automatically.
The original map renderer is paired with a separate browser command panel.

This prototype requires the matching relay implementation. It does not yet
provide manual map spells, army/artifact rearrangement, or reconnect/resume.
Legacy single-player, campaigns and ordinary network rooms keep their original
controls and turns. See [protocol and limits](docs/fast-game-implementation/contract.md).

Validation: `python3 scripts/test-fast-game.py`, `python3 scripts/test-fast-ui.py`,
and `SITE_URL=http://127.0.0.1:8800 python3 scripts/fast-game-browser-smoke.py`
(use `BROWSER=webkit` for WebKit). Browser runs use silent audio.
