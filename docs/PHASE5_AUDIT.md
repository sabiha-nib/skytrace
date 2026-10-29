# Phase 5 audit — the discovery environment (v0.5.0)

Phase 5 asked for Skytrace to become a scientific discovery environment built around one loop (explore → observe →
compare → detect → test → explain → verify → preserve → share), without weakening any rule of the earlier phases:
no manufactured results, no blocked work reported as done, no decorative controls, no secrets outside the server.

## 1. Baseline (before any Phase 5 change)

| Item | State at commit `62b5956` (v0.4.0) |
|---|---|
| Working tree | clean |
| Unit, integration and robustness tests | 199 passed, 2 skipped (astropy not installed) |
| Browser tests | 31 passed (11-step journey; every control in server and static mode) |
| `verify.py --e2e` | 18/18 checks |
| Static preview | 90 files, hosted as https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT (version 2) |
| Release artifacts | `dist/skytrace-0.4.0.zip` (sha256 `346228…`), `dist/skytrace-preview-0.4.0.zip` (sha256 `1403f2…`) |
| External services | IRSA, SIMBAD, Gaia, Meta API, PyPI: refused by the proxy (403) |

## 2. Architecture decisions

* **New results are readers of the record.** The Discovery Engine (DISC-1), hypothesis tests (HYPO-1), uncertainty
  decomposition (UNC-1), registration diagnostics (REGDIAG-1), capability registry (CAPREG-1) and package (PKG-1) read a
  finished investigation record and its bundle manifest. They do not measure, use the network, call a model or produce
  probabilities; the record's content hash is unchanged by them. This kept every Phase 3/4 result and test intact.
* **One registry of capabilities** drives the copilot's `list_capabilities` tool, the engine's next steps, the API and
  the package, so the product cannot describe a capability differently in different places.
* **Rules, published and ported.** The overall-status rule of the Hypothesis Arena exists once in Python and once in
  `web/js/rules.js`, and a test compares them over all 258 combinations of up to three statuses. The same pattern
  covers the content hash, pair comparison, registration and question routing.
* **Levels are views.** Explore / Investigate / Research change what is shown (CSS on `body[data-level]` and the Lab's
  tab list), never what is computed.
* **User context is untrusted.** A research question and user hypotheses are stored with a record (≤ 50 kB), sanitised
  to known fields on reopen, and can only cite recorded tests by id. They never enter the evidence matrix, the graph or
  the content hash.
* **The static preview stays honest.** Phase 5 outputs are precomputed by the server at build time; the preview's
  capability registry marks server-only capabilities unavailable and says which results are precomputed and which are
  computed in the browser.

Details: [ARCHITECTURE.md](ARCHITECTURE.md), [DISCOVERY_METHODS.md](DISCOVERY_METHODS.md).

## 3. Preservation checklist

| Phase ≤ 4 capability | Still works | Evidence |
|---|---|---|
| Analysis pipeline and content hashes | yes; fixture hashes unchanged | `test_offline_workflow.py`, `verify.py` provenance checks |
| Synthetic fixtures reproducible | yes | `verify.py` ("identical") |
| Sky Explorer controls | yes | e2e `test_b` (both modes) |
| Time Machine controls and compatibility gating | yes | e2e `test_c` |
| Discovery Lab, re-run, stability | yes | e2e `test_d` |
| Evidence Graph tracing | yes | e2e `test_e` |
| Back/forward history | yes | e2e `test_f` |
| Records: save, export, verified import, refusal of a tampered record, replay/check, reopen, delete | yes (import now previews before storing) | e2e `test_g` |
| Copilot: suggestions, tool activity, evidence chips, refusal of named-observation questions in the preview | yes | e2e `test_h` |
| Narrow-screen copilot overlay and Escape | yes | e2e `test_i` |
| No external requests; no console errors | yes | e2e `test_z` |
| 11-step user journey | yes | `tests/e2e/test_app.py` |
| Secret scan, bundle checksums, preview manifest | yes | `verify.py` |
| 0.4.0 release artifacts | untouched; `make_release.py` now refuses to overwrite an existing version, and the 0.4.0 manifest was kept as `dist/RELEASE_MANIFEST-0.4.0.json` | `scripts/make_release.py` |

## 4. What was built

| Area | Delivered | Not delivered (and why) |
|---|---|---|
| Discovery loop and context | loop bar on every workspace; research question and user hypotheses kept across workspaces and saved | — |
| Levels | Explore / Investigate / Research | — |
| Interaction | command palette (Ctrl/⌘+K, /), glossary and shortcut dialog (?), Alt+1…7, Escape everywhere, undo for hypothesis removal | undo for every action (deferred) |
| Discovery Engine | stages A–G: inventory, 8 answerable + 3 unanswerable questions with test plans, review, rule-based next steps | survey across many targets (needs real data) |
| Hypothesis Arena | 11 explanations, 12 tests, 6 statuses, published overall rule, user hypotheses with attached tests | slope, blend and chromatic tests (need models not built; shown as not tested) |
| Uncertainty Explorer | motion components, bound shown as a bound, z-denominator shares with recompute check, sensitivity separate, unquantified effects named | bootstrap intervals (too few epochs) |
| Evidence Graph | competing explanations as nodes linked to claims, with their tests | graph diff (deferred) |
| Time Machine | registration diagnostics per pair (Python and browser, parity-tested) | multi-epoch animation (deferred) |
| Copilot | capability registry tool; answers laid out as Answer · Evidence · Method · Limitations · Next step | live Meta model (**BLOCKED**: no key, no route) |
| Report and figure studio | report, record, graph, discovery report, deterministic package; SVG figure export with context | PDF (deferred) |
| Vault | search, tags and filter, rename, duplicate, compare two, import preview with hash check, two-step delete | shared vault (out of scope for a single-user tool) |
| Offline | everything above works with `OFFLINE=1` and in the static preview | — |
| Feature catalogue | 267 concepts in 25 domains, scored on 7 dimensions, tiers computed: [FEATURE_CATALOGUE.md](FEATURE_CATALOGUE.md) | — |

## 5. Live-data program

`scripts/diagnose_environment.py` was re-run on 2026-10-29: IRSA SIA, IRSA TAP, SIMBAD TAP, Gaia TAP, the Meta Model API,
PyPI and npm are all refused by the proxy (403). Real-data acquisition, the astropy comparison on a real SPHEREx file and
the first Meta API call remain **BLOCKED**. Nothing in v0.5 is a real-data result; every screen and export of the bundled
targets says *synthetic*. To unblock: allowlist the hosts in [ENVIRONMENT_REPORT.md](ENVIRONMENT_REPORT.md), set
`META_API_KEY` in the environment (never in the conversation, code or browser), then run `scripts/acquire_targets.py --all`,
`pytest -m live tests/live` and `scripts/meta_smoke_test.py`.

## 6. Security and privacy review

| Check | Result |
|---|---|
| Secrets in tracked files | none (`verify.py` secret scan PASS) |
| Keys reaching the browser, records, logs, the preview or the hosted page | none: the key is read only by `ai/meta_client.py` on the server; the preview is built with the key variables emptied |
| Content security policy | `default-src 'self'`, no inline scripts, no eval (the browser tests run under it) |
| External requests while using the app | none (asserted in both modes) |
| Imported records | size-limited (2 MB); content hash recomputed in the browser before the import is offered; context sanitised to known, bounded fields on reopen |
| Server inputs | parameter bounds from `analysis.PARAM_BOUNDS`; context ≤ 50 kB (413 above); empty names refused; record ids path-safe |
| Telemetry | none |
| Destructive git operations, force pushes, publishing outside the existing artifact | none |

## 7. Performance and accessibility

Measured on this machine (`docs/performance.json`, median of 3): static preview page load 0.15 s and first result
0.29 s; server page load 0.17 s and first result 3.6 s (running the full analysis); Discovery Engine, Arena and
Uncertainty tab render in under 0.1 s; discovery report 7 ms and package 34–39 ms on the server; stability check 15–16 s.

Accessibility, checked by tests: accessible names on every visible button, field and chart in every workspace; dialogs
with `aria-modal`, labels, focus kept inside and returned to the opener; every text colour token ≥ 4.5:1 on every
surface (the faint grey was raised from 3.7:1 to 4.65:1); status never carried by colour alone; keyboard paths for every
new feature; no horizontal scroll at 820 px and 390 px. **NOT RUN:** a session with a screen reader.

## 8. Gates

Results: [TEST_REPORT.md](TEST_REPORT.md) (v0.5.0 section).
