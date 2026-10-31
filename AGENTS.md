# Project boundaries

- This is the only public project repository. Keep the website, browser JavaScript,
  browser tests and public protocol documentation here.
- Shared C++ rules, rendering, portability patches and cross-runtime harnesses
  belong in the private sibling `homm3-engine` repository. Rust and native worker
  implementations belong in the private sibling `homm3-lobby` repository.
- Update both consumers' `engine.lock.json` to the same tested engine commit.
  Use `npm run build` or `npm run engine:install`; packaging verifies the pin.
- Older mixed-source branches/worktrees are archives. Do not merge or push their
  history into this public repository. Transfer reviewed browser files only.
- Keep retail resources, private journals, room credentials and server artifacts
  out of Git and public bundles. Publish only the explicit browser-file allowlist.
- Run browser tests silently and use isolated rooms/services. Do not restart an
  existing user preview to run a test.
