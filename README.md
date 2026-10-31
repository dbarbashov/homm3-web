# Heroes III browser client

Public website and browser shell for Heroes III. Play using your own original
game files; retail archives are not included or uploaded by the browser.

## Repository boundaries

`homm3-web` and [homm3-engine](https://github.com/dbarbashov/homm3-engine) are public.
The shared C++ runtime lives in `homm3-engine`; the Rust service and native authoritative
worker are maintained in private `homm3-lobby`. Both consumers pin the same full
engine commit in `engine.lock.json`. This repository contains no native worker
implementation, engine patches, private match journals or server deployment data.
The public issue tracker remains the entry point for bugs and reproduction links.

The browser runs compiled WASM. Website JavaScript and the resulting WASM can be
inspected by players; server-side authority, not source secrecy, validates moves.

## Develop the website

Use Node.js 22+ and Python 3. No npm dependencies are required for unit tests:

```sh
npm test
npm start
```

The landing page and site UI work without an engine checkout. Playing
requires `web/port/game.js` and `game.wasm`, built or supplied separately.
`npm start` optionally starts a sibling `homm3-lobby`; use `HOMM3_LOBBY_ROOT` for
another checkout. `node server.mjs` starts only the client development proxy.
Select your original game folder in the browser. Local test asset configuration
is private and ignored; never publish retail data from the development server.

## Install the pinned engine

Anyone can clone and build the matching engine:

```sh
git clone https://github.com/dbarbashov/homm3-engine.git ../homm3-engine
git -C ../homm3-engine checkout "$(python3 -c 'import json; print(json.load(open("engine.lock.json"))["commit"])')"
(cd ../homm3-engine && python3 scripts/setup-port.py)
npm run build
```

This verifies `engine.lock.json` and refuses a different or modified revision.
The engine checkout needs its pinned Emscripten SDK, CMake and media build.
Alternatively, obtain a trusted matching client bundle and install its directory:

```sh
npm run engine:install -- --from-dir /path/to/client-bundle
```

The installer validates revision and SHA-256 for `game.js` and `game.wasm` before
copying anything. The bundle includes `engine-build.json`. These checks detect
corruption and mismatched versions; they do not authenticate an untrusted bundle
publisher. Both public checkouts are sufficient to build the browser game;
the private server is not required. Set `HOMM3_ENGINE_ROOT` for a non-sibling checkout.
No new binary download is published as part of the repository split.

## Checks and packaging

```sh
npm test
npm run test:site
npm run test:mobile
python3 scripts/bundle-site.py --ffmpeg-source /path/to/ffmpeg-8.0.3.tar.xz
```

Browser checks require local assets, a built engine and Playwright. Native and
legacy/authority parity tests live in the engine repository; full authority checks also need the private server. Packaging
uses a public-file allowlist; it never archives a repository root.
The packager verifies the matching FFmpeg source archive before including it.
Packaging locally is not a binary release; distribution must preserve the
source and relinking materials described in `THIRD_PARTY.md`.

See `docs/NETWORK.md` for browser protocol details and `THIRD_PARTY.md` for credits.
Historical public commits remain available; this change does not retract source
that was already published or rewrite Git history.
