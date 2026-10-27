# Contributing

Issues and focused pull requests are welcome. Describe the expected behavior,
what happens instead, your browser/OS, and reproducible steps. Remove private
room links, credentials and personal paths from logs before attaching them.

Build instructions and test commands are in README.md. Preserve the recovered
engine's rules; place platform adaptations in `port/` and keep upstream changes
in `port/patches/0001-portability.patch`. Do not edit the upstream checkout.

For UI changes check desktop, portrait and landscape layouts, touch input,
keyboard entry, and that only the sidebar content scrolls. For networking changes
exercise two independent clients. State what was actually tested and any gaps.

Never commit retail archives, fonts, sprites, maps, music, saves, generated WASM,
SDKs, screenshots containing private information, configuration secrets or logs.
Original assets must come from each tester's own installation.

The Rust room relay is maintained separately in a private repository. Its public
protocol is documented in docs/NETWORK.md. Client contributions remain welcome
without access to it.

Changes do not deploy automatically. Maintainers review the diff and test results
before choosing a revision for a manual release. Repository visibility does not
replace code review or server isolation.
