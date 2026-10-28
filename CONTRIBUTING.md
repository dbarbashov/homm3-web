# Contributing

Issues and focused pull requests are welcome. Use the
[bug report form](https://github.com/dbarbashov/homm3-web/issues/new?template=bug_report.yml)
or **Report a bug / Сообщить об ошибке** on the home page or in the game menu.
Reports in English or Russian are welcome. Include the expected behavior,
what happens instead, reproducible steps, and the map/campaign when relevant.
GitHub sign-in is required and submitted reports are public.

Website links prefill only the page category, browser user-agent, viewport,
pixel ratio, touch availability, canvas size and, when ready, the combined
engine/resource fingerprint. The form can be reviewed and edited before sending.
It does not collect room invitations, chat, logs, saves or game files. Remove
private room links, credentials and personal paths from any manual attachments.

Maintainers and coding agents can read the same issue queue using GitHub or
`gh issue list --repo dbarbashov/homm3-web --label bug`. To inspect a report and
its discussion, use `gh issue view NUMBER --repo dbarbashov/homm3-web --comments`.
Issue access does not imply background monitoring or automatic changes.

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
