# Upstream provenance

Repository: https://github.com/sushi-shi/homm3-decomp

Revision: `e12906accf96c2662b1abadbc49ddc111991bf21`

Branch: `decomp-complete-4.0`

License: CC0 1.0 for reconstructed source/tooling. The complete upstream license
is retained in `upstream/homm3-decomp/LICENSE`; a copy is in `licenses/`.
Third-party vendor directories in upstream have their own licenses. No legacy
Miles/DirectDraw/Smacker/Bink runtime from those directories is linked by this port.

## Portable C++ client

`port/sources.json` lists the recovered source modules compiled directly for
native and WebAssembly. `port/patches/0001-portability.patch` records every change
against the pinned revision. `prepare-port.py` additionally extracts eight unchanged
platform-independent helper bodies from `kbwin.cpp`, `wingraph.cpp`, `kb.cpp`
and `misc.cpp`. The original main/game-type menu handlers execute directly.
The game target (`port/game-sources.json`) includes 131 recovered translation
units, including kb startup/data helpers, scenario selection, game, adventure,
town, battle, AI and serialization. Its original `normalDialog` executes directly.
The text-only `normalDialog` adapter in `port/frontend/dialogs.cpp` assembles
original dialog widgets using the recovered sizing algorithm; it does not
implement the full game/item dialog dispatcher and is used only by the menu
regression target.
The new SDL/file/media adapters and bootstrap are in `port/`; they do not replace
the game with independently implemented rules. The five small Victor PCX APIs
are implemented portably in `port/platform/pcx.cpp`; no original binary is linked.

SDL2 2.32.10 (zlib license) and zlib are used by the native/wasm builds;
Emscripten 6.0.13 is the browser toolchain. Their source licenses are copied to
`licenses/`. The SDK, generated binaries and retail resources are not committed.

## Earlier map viewer (separate utility)

The viewer compiles unmodified `tools/homm3-map/src/lib.rs` and
`tools/homm3-def/src/lib.rs` using rustc for `wasm32-unknown-unknown`.
No upstream generated data or retail EXE bytes are embedded into WASM.

Renderer reference: `src/advmgr.cpp`:

- `g_groundTilesetNames` at `0x0065f55c`
- `g_riverTilesetNames` at `0x0065f584`
- `g_roadTilesetNames` at `0x0065f598`
- `drawGround` at `0x00412900`
- `drawRiver` at `0x00411b80`
- `drawRoad` at `0x00411d60` (vertical offset of 16 pixels)

The browser renderer and its RGBA compositing are new implementations, not
byte-matched exports of these C++ functions. In particular, shadow blending,
palette cycling, flag recoloring and tile-level object ordering need more work.

Heroes III game data belongs to its respective rights holders and remains in
the user's existing installation. No LOD, music, maps, executable or other
original game resource is included in the public source tree. Optional original
UI fonts and hosted resource catalogs are generated separately and excluded from Git.

- Native MP3 playback: `port/vendor/dr_mp3.h`, [dr_libs](https://github.com/mackron/dr_libs), commit `a466dbe88fe2576d46c43877d602f3d66b8561a7`. MIT-0 / public-domain dual license reproduced in the header. Browser playback uses Web Audio.

## Website and room relay

The site credits the original creators and the reconstructed source explicitly.
The standalone Rust server distributes only `web/`; each player supplies their
own retail files through browser folder selection. Files remain local File
objects; the room protocol transfers game state, not the original asset library.
The Node development server can serve an existing local installation for local
and LAN testing and must not be used as a public retail-resource distribution.

The room relay uses Axum/Tokio/tower-http (MIT), Serde, UUID and futures-util
(MIT OR Apache-2.0). Exact direct and transitive versions are in
the private relay repository’s `Cargo.lock`. The relay replaces the DirectPlay transport boundary;
no Microsoft DirectPlay runtime or new independent game rules are linked.

## HD-style interface

The expanded adventure viewport and army/recruitment shortcuts are independently implemented in the portable C++ engine, inspired by the documented [Heroes III HD Mod interface](https://sites.google.com/site/heroes3hd/eng/functionality). No HD Mod binaries or code are bundled. Original interface artwork still comes from the user’s game installation.
