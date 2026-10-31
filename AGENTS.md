# Project boundaries

- Keep the website, JavaScript client, browser tests and protocol documentation here.
- Shared C++ rules, rendering, portability code and cross-runtime harnesses
  belong in `homm3-engine`. Keep service implementations outside this repository.
- Public documentation should explain usage and contributions, not internal
  repository organization or access policies.
- Update both consumers' `engine.lock.json` to the same tested engine commit.
  Use `npm run build` or `npm run engine:install`; packaging verifies the pin.
- Older mixed-source branches/worktrees are archives. Do not merge or push their
  history into this public repository. Transfer reviewed browser files only.
- Keep retail resources, private journals, room credentials and server artifacts
  out of Git and public bundles. Publish only the explicit browser-file allowlist.
- Run browser tests silently and use isolated rooms/services. Do not restart an
  existing user preview to run a test.
