# Heroes III browser client

Play Heroes III in the browser using your own original game files. Retail archives
are not included or uploaded by the browser.

This repository contains the website, JavaScript client and browser tests. Game
rules and rendering live in [homm3-engine](https://github.com/dbarbashov/homm3-engine).
The engine revision used by the client is recorded in `engine.lock.json`.

## Develop the website

Use Node.js 22+ and Python 3. No npm dependencies are required for unit tests:

```sh
npm test
npm start
```

The landing page and site UI work without an engine build. Playing requires
`web/port/game.js` and `game.wasm`, built or supplied separately.
`node server.mjs` starts only the development proxy. Multiplayer also requires a
room service; `HOMM3_LOBBY_ROOT` selects a local service checkout for `npm start`.

Select your original game folder in the browser. Local test asset configuration
is ignored by Git; never publish retail data from the development server.

## Build the engine

From this repository's root:

```sh
git clone https://github.com/dbarbashov/homm3-engine.git ../homm3-engine
git -C ../homm3-engine checkout "$(python3 -c 'import json; print(json.load(open("engine.lock.json"))["commit"])')"
(cd ../homm3-engine && python3 scripts/setup-port.py)
npm run build
```

The engine needs CMake, Clang, SDL2, zlib and its pinned Emscripten SDK. Set
`HOMM3_ENGINE_ROOT` for a non-sibling checkout. The build verifies the engine pin
and refuses a different or modified revision. No room service is needed to
build or play the standalone browser client.

Alternatively, install a trusted matching client bundle:

```sh
npm run engine:install -- --from-dir /path/to/client-bundle
```

The installer validates the revision and SHA-256 of `game.js` and `game.wasm`
against the bundle's `engine-build.json` before replacing files. These checks
detect corruption and mismatched versions; obtain bundles from a trusted source.

## Checks and packaging

```sh
npm test
npm run test:site
npm run test:mobile
python3 scripts/bundle-site.py --ffmpeg-source /path/to/ffmpeg-8.0.3.tar.xz
```

Browser checks require local assets, a built engine and Playwright. Native and
cross-runtime tests live in the engine repository. Packaging verifies the engine
revision and FFmpeg source archive, then exports an explicit browser-file allowlist.
Binary distribution must preserve the source and relinking materials described
in `THIRD_PARTY.md`.

See `CONTRIBUTING.md` for contributions, `docs/NETWORK.md` for browser protocol
information and `THIRD_PARTY.md` for credits.
