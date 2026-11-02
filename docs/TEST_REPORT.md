# Test report: v0.9.0 (2026-11-02)

Statuses: **PASS** means executed and met. **FAIL** means executed and not met. **BLOCKED** means it could not be executed here, and
the reason is named. **NOT RUN** means it was not attempted. **PARTIAL** says which part ran.

## Gates (v0.9.0, at release commit `7bf7c38`)

| # | Gate (§9 of the Phase 9 brief) | Command / evidence | Status |
|---|---|---|---|
| G1 | Repository baseline inspected; existing functionality intact (§9.1) | `docs/PHASE9_AUDIT.md` §1–2: 0.8.0 at `9c76db1`, clean tree, 323 passed / 2 skipped, e2e 107. Every earlier test still runs and passes; record hashes unchanged | PASS |
| G2 | Unit, integration, robustness and parity tests (§9.11) | `verify.py`: **348 passed, 2 skipped** (astropy not installed). New: `test_intelligence.py` (21), `test_phase9_catalogue.py` (3), `test_api.py::test_phase9_intelligence_corpus_oracle_whatif_reproduction` | PASS |
| G3 | Python/browser parity (§8) | `test_intelligence.py::test_browser_intelligence_functions_match_python` runs `tests/js/intel_parity.mjs` in Node: recall, failure warnings, ledger and gate overlays, oracle spec and evaluation, motion refit and hypothetical visit, reproduction validation and comparison, session entities, causal warnings | PASS |
| G4 | Shared architecture, provenance and epistemic status (§9.2, 9.4, 9.5) | `test_entities_have_ids_versions_provenance_and_statuses` (zero unresolved provenance references on both fixtures); `test_memory_statuses_never_promote_explanations_and_flag_tampering` | PASS |
| G5 | Counterfactual isolation (§9.6) | `test_whatif_is_isolated_validated_and_refuses_without_a_method` (record hash unchanged, baseline recomputed, refusals where no method exists); Phase 7 `test_counterfactuals_are_isolated_and_labelled` | PASS |
| G6 | Permissions and audit logs for autonomous actions (§9.7) | `test_research_cycle_proposes_registered_actions_by_rule_and_levels_bound_execution` (no level allows network or write; restricted workflow within the allowed classes); e2e `i5` (advisory runs nothing, supervised runs an approved step, restricted needs authorization; every step logged in the session) | PASS |
| G7 | Reproduction packages validated (§9.8) | `test_reproduction_manifests_validate_and_comparison_classes` (tampered digest rejected; all six classes produced); e2e `i6` | PASS |
| G8 | Browser workflows, both modes (§9.3, 9.10) | `pytest -m e2e tests/e2e`: **119 passed** (baseline 107; `i1`–`i6` added in server and static mode); `test_r` and `test_y` extended to the new workspace | PASS |
| G9 | Responsive behaviour inspected | e2e `test_r` (no horizontal page scroll at 820 and 390 px, including Scientific Intelligence); `phase9_screenshots.py` checks scrollWidth = clientWidth at 390 px. Inspecting the phone screenshots **found a defect**: the gate's requirement column wrapped to one letter per line. Fixed (`7bf7c38`) and re-inspected: tables keep whole words and scroll inside their frame | PASS (defect found and fixed) |
| G10 | Local preview launched and inspected (§9.13) | `dist/preview` served on 127.0.0.1 and opened in Chromium (Playwright, headless, in this workspace): all twelve panels captured at 1440 px and two at 390 px (`docs/screenshots/phase9-*.png`), images looked at, **no console errors**. The static-mode e2e run exercised the same build | PASS |
| G11 | Whole-system verification (§9.11) | `python scripts/verify.py --e2e` at `7bf7c38`: **VERIFIED 18/18**, 4 warnings (no astropy, no real bundles, no Meta key, smoke test never run) | PASS |
| G12 | Static preview integrity | `verify.py`: 231 files match `PREVIEW_MANIFEST.json` (built from `7bf7c38`) | PASS |
| G13 | Accessibility (automated) | `test_accessibility.py`; e2e `test_y` (every visible control named, including the twelve panels), the Unknown Universe bands are keyboard buttons (e2e `i2` uses focus and Enter) | PASS |
| G14 | Accessibility with a screen reader | — | NOT RUN |
| G15 | Performance measured | `python scripts/measure_performance.py` → `docs/performance.json` (below) | PASS |
| G16 | Documentation updated (§9.12) | Phase 9 audit, architecture, scientific methods (pointer), generated intelligence methods, limitations, traceability, provenance, reproducibility, preview (availability classes), troubleshooting, feature catalogue (pointer), Phase 9 catalogue, release notes, README, CLAUDE.md, this report | PASS |
| G17 | Release artifacts validated (§9.14) | `scripts/make_release.py`: RELEASE OK (below). Earlier artifacts 0.2.0–0.8.0 untouched (0.8.0 still `fcde43a0…`) | PASS |
| G18 | Hosted preview | Published as **version 8** of the hosted artifact. `data/status.json` (0.9.0, commit `7bf7c38`), `js/intelui.js`, `css/app.css`, `data/corpus.json` and `data/t/syn-var-1/run/724e4a3cdd8ef4d9/intelligence.json` read back with SHA-256 identical to the local build. The hosted page was **not opened in a browser**: the computer linked to this session was not connected, so no browser outside this workspace was reachable. Per §9, the hosted preview is not claimed to work; the identical files were rendered locally (G10) | PARTIAL (files verified; hosted page not opened) |
| G19 | Real SPHEREx acquisition, live archive tests, astropy cross-check | `diagnose_environment.py` (2026-11-02): IRSA SIA/TAP, SIMBAD, Gaia, Meta, PyPI and npm refused (proxy 403); astropy not installable | BLOCKED |
| G20 | Live Meta API; multi-agent research; semantic recall with embeddings; dependency review | No key; API host, PyPI and OSV refused | BLOCKED |
| G21 | Dockerfile build | Base images cannot be pulled | NOT RUN |

Every Phase 9 result is computed on synthetic fixtures. A synthetic test is not evidence of an astronomical discovery; a gate
marked "ready" is not a statement that the conclusions are true; a repeated calculation is not a valid physical interpretation.

## Release (0.9.0)

| Version | Commit | Archive (sha256) | Preview archive (sha256) | Hosted artifact |
|---|---|---|---|---|
| 0.9.0 | `7bf7c38` | `dist/skytrace-0.9.0.zip` (`1388418fe632fcaae798c5a92a690f5e7e6842993e986e82248b213afc1e9423`, 543 files, 31.6 MB; zip integrity verified, no forbidden files, bundle checksums OK) | `dist/skytrace-preview-0.9.0.zip` (`2db9f41f3a2c39c02da4917a565a118b3fec1fcce6283b330ba8fa019f023b15`, 6.7 MB) | version 8 (G18) |

The manifest is kept as `dist/RELEASE_MANIFEST-0.9.0.json`. Nothing was pushed.

## New tests in v0.9

Unit/API: `test_intelligence.py` (21 functions, including the Node parity test `tests/js/intel_parity.mjs`), `test_phase9_catalogue.py`
(3: 600 distinct concepts in 50 domains, every field present; every A concept cites existing evidence and an existing test function;
generated documents match the script), `integration/test_api.py::test_phase9_intelligence_corpus_oracle_whatif_reproduction`.
Browser (both modes, `e2e/test_controls.py`): `i1` command center, genome and fingerprint; `i2` unknown universe and network;
`i3` adversary and causality; `i4` what-if and oracle; `i5` research cycle permissions and gate; `i6` memory, reproduction and
preservation. `test_r` and `test_y` were extended to the new workspace. No assertion of an earlier test was changed.

## Performance (v0.9.0; this machine, 2 CPUs, median of 3; `docs/performance.json`)

| Fixture | Analysis | Intelligence report, first call | Intelligence report, cached | Corpus (memory, network, genome comparisons) |
|---|---|---|---|---|
| syn-var-1 | 5.651 s | 0.384 s | 0.02 s | 1.584 s |
| syn-hpm-1 | 4.963 s | 0.526 s | 0.021 s | 2.268 s |

| Phase 9 panel, click to rendered panel | Server mode | Static preview |
|---|---|---|
| Command Center | 0.093 s | 0.091 s |
| Discovery Genome | 0.11 s | 0.107 s |
| Unknown Universe | 0.107 s | 0.129 s |
| Multi-Discovery Network | 0.164 s | 0.201 s |
| Scientific Adversary | 0.112 s | 0.138 s |
| Causality Lab | 0.127 s | 0.113 s |
| What-if Lab | 0.109 s | 0.124 s |
| Observation Oracle | 0.109 s | 0.124 s |
| Research Cycle | 0.102 s | 0.097 s |
| Research Memory | 0.139 s | 0.128 s |
| Reproduction Network | 0.111 s | 0.119 s |
| Integrity Gate | 0.099 s | 0.129 s |

Page load: server 0.46 s, static 0.486 s; first result in the static preview 0.704 s. Static preview: 231 files plus its manifest,
29.4 MB. The corpus is computed once per set of records and cached. All earlier measurements are in `docs/performance.json`.

---

# Test report: v0.8.0 (2026-10-31)

## Gates (v0.8.0, at release commit `9af3ec4`)

| # | Gate (§35 of the Phase 8 brief) | Command / evidence | Status |
|---|---|---|---|
| G1 | Actual repository baseline inspected | `docs/PHASE8_AUDIT.md` §1: 0.7.0 at `948cd1c`, clean tree, 292 passed / 2 skipped, e2e 89, preview version 6 | PASS |
| G2 | Existing application preserved | Feature-preservation matrix (`PHASE8_AUDIT.md` §2). `analysis.py`, `science/`, `ai/`, `archive/` and every Phase 5–7 module are unchanged since 0.7.0; no test removed; the content hashes of all 12 recorded runs in the 0.8.0 preview are identical to the 0.7.0 preview archive | PASS |
| G3 | Unit, integration, robustness and parity tests (existing preserved; new scientific tests pass) | `python -m pytest` (via `verify.py`): **323 passed, 2 skipped** (astropy not installed). Baseline 292; added `test_epistemic.py` (25 cases including Node parity), `test_phase8_catalogue.py` (5), `integration/test_api.py::test_phase8_epistemic_reproduce_integrity` | PASS |
| G4 | Epistemic architecture, compiler, debugger, boundary, stress tests, negative knowledge, blindspots, genome, uncertainty lineage, data lineage, reproduction, integrity firewall | `test_epistemic.py`: grounded statuses and deterministic graph; claim lineage back to files, methods and assumptions and forward to claims; negation-aware wording; genome completeness with existing known-answer tests; every compiler stage and the precedence rule; injected unit, provenance and wording defects detected; breakpoints at real stages with exact recomputation; earliest divergence found; boundary rules; ten stress modes; negative registry; blindspot coverage without percentages; uncertainty flow with omissions; lineage from recorded stages only; model arena reproduces the pipeline fit; FutureLab validated first; decisions and questions cite sources; firewall flags without rewriting; review items linked; five reproduction verdicts incl. tampered, parameter, software and blocked cases; simulation-audit refusals; vault chain detects edits and keeps 0.7 sessions valid | PASS |
| G5 | Browser workflows (both modes; desktop, tablet, phone widths) | `pytest -m e2e tests/e2e`: **107 passed** (baseline 89; `e1`–`e9` added in server and static mode): graph trace and export, lineage; compiler filters, genome, comparison; boundary, stress, blindspots and export; debugger recomputation, differential debugging, reproduction feeding the stress test; models, uncertainty flow, FutureLab calculator; decisions and questions with Planner hand-off; negative-space search and entry, integrity firewall on report and pasted text; protocol, lock, amendment, blind cover, copilot pause, unblinding; Reasoning Lab, evidence vault correction, review board comment | PASS |
| G6 | Responsive behaviour inspected | e2e `test_r` (no horizontal page scroll at 820 and 390 px, extended to the twelve new workspaces); the twelve Phase 8 workspaces measured at 390 px (scrollWidth = clientWidth); phone-width screenshots `phase8-*-mobile.png` inspected; the reasoning-graph columns were clipping at desktop width and now scroll inside their panel | PASS |
| G7 | Offline behaviour verified | `verify.py` runs with `OFFLINE=1`; e2e `test_z_no_external_requests_no_errors` (no external request in either mode; the static preview calls no `/api/`); `test_offline_workflow.py` | PASS |
| G8 | No fabricated data or API calls | Every Phase 8 result is computed from the two synthetic fixtures and labelled synthetic; no model call anywhere in the epistemic layer; the copilot is unchanged; the live tests fail (proxy 403), and no real-data result is reported | PASS |
| G9 | 500 distinct catalogue concepts audited and deduplicated | `test_phase8_catalogue.py`: 500 brief concepts in 50 domains, **507 distinct** (31 merged, 38 added), 160 cite a real, implemented Phase 7 entry, no new concept cites Phase 7, every cited file and test function exists, deferred/blocked/out-of-scope items cite nothing and say why; generated files current | PASS |
| G10 | Whole-system verification | `python scripts/verify.py --e2e` at `9af3ec4`: **VERIFIED 18/18**, 4 warnings (no astropy, no real bundles, no Meta key, smoke test never run) | PASS |
| G11 | Static preview integrity | `verify.py`: 214 files match `PREVIEW_MANIFEST.json` | PASS |
| G12 | Accessibility (automated) | `test_accessibility.py` (contrast, reduced motion); e2e `test_y` (every visible control named, extended to the new workspaces), `test_k` (keyboard) | PASS |
| G13 | Accessibility with a screen reader | — | NOT RUN |
| G14 | Performance measured | `python scripts/measure_performance.py` → `docs/performance.json` (below) | PASS |
| G15 | Documentation updated | audit, architecture, scientific methods (pointer), generated epistemic methods, limitations, traceability, provenance, reproducibility, feature catalogue (pointer), Phase 8 catalogue, preview (§33 availability table), troubleshooting, release notes, README, CLAUDE.md, this report | PASS |
| G16 | Release artifacts validated | `scripts/make_release.py`: RELEASE OK (below). Earlier artifacts 0.2.0–0.7.0 untouched | PASS |
| G17 | Actual preview inspected where possible | Published as **version 7** of the hosted artifact. `data/status.json` (0.8.0, commit `9af3ec4`), `js/epistemiccore.js` and `data/t/syn-var-1/run/724e4a3cdd8ef4d9/reproducex.json` read back with SHA-256 identical to the local build. The hosted page was **not opened in a browser**: no browser on the desktop app was reachable from this session. The identical files were rendered by the static-mode e2e run (G5) and the Phase 8 screenshots (no console errors) | PARTIAL (files verified; hosted page not opened) |
| G18 | Real SPHEREx acquisition, live archive tests, astropy cross-check | `diagnose_environment.py`: IRSA SIA/TAP, SIMBAD, Gaia, Meta, PyPI and npm all refused (proxy 403). `pytest -m live tests/live`: 2 failed, 2 errors (proxy refused) | BLOCKED |
| G19 | Live Meta API; multi-agent research; semantic indexing; dependency review | No key; API host, PyPI and OSV refused | BLOCKED |
| G20 | Dockerfile build | Base images cannot be pulled | NOT RUN |

A structurally valid investigation is not automatically scientifically correct, and a reproducible calculation is not
automatically a valid physical interpretation. Both fixtures compile to "requires scientific review".

## Release (0.8.0)

| Version | Commit | Archive (sha256) | Preview archive (sha256) | Hosted artifact |
|---|---|---|---|---|
| 0.8.0 | `9af3ec4` | `dist/skytrace-0.8.0.zip` (`fcde43a0bb5a80d6fde788656c66fbe4bef25f173967f015db4e1bd00916965d`, 499 files, 24.4 MB; zip integrity verified, no forbidden files, bundle checksums OK) | `dist/skytrace-preview-0.8.0.zip` (`8f6e723eb33124bc76c8a9017e74e97c2670b842d410d002deee1c0f5ef1de0f`, 6.1 MB) | version 7 (G17) |

The manifest is kept as `dist/RELEASE_MANIFEST-0.8.0.json`. Nothing was pushed.

## New tests in v0.8

Unit/API: `test_epistemic.py` (23 functions, 25 cases, including the Node parity test `tests/js/epistemic_parity.mjs`),
`test_phase8_catalogue.py` (5), `integration/test_api.py::test_phase8_epistemic_reproduce_integrity`.
Browser (both modes, `e2e/test_controls.py`): `e1`–`e9` as listed in G5. `test_r` and `test_y` were extended to the new
workspaces. No assertion of an earlier test was changed.

## Performance (v0.8.0; this machine, 2 CPUs, median of 3; `docs/performance.json`)

| Fixture | Analysis | Epistemic report, first call | Epistemic report, cached | Independent reproduction (re-execution) |
|---|---|---|---|---|
| syn-var-1 | 4.007 s | 0.243 s | 0.02 s | 3.842 s |
| syn-hpm-1 | 4.063 s | 0.211 s | 0.019 s | 3.385 s |

| Phase 8 workspace, click to first rendered element | Server mode | Static preview |
|---|---|---|
| Reasoning Graph (fetches the epistemic report) | 0.161 s (first 0.267 s) | 0.117 s |
| Scientific Compiler | 0.081 s (first 0.083 s) | 0.072 s |
| Claims | 0.071 s (first 0.09 s) | 0.064 s |
| Scientific Debugger | 0.094 s (first 0.094 s) | 0.068 s |
| Model Arena | 0.059 s (first 0.096 s) | 0.065 s |
| Uncertainty Flow | 0.055 s (first 0.055 s) | 0.072 s |
| FutureLab | 0.052 s (first 0.094 s) | 0.069 s |
| Questions & Next Steps | 0.053 s (first 0.066 s) | 0.082 s |
| Negative Space | 0.092 s (first 0.092 s) | 0.094 s |
| Integrity check of the report (in the browser) | 0.134 s (first 0.143 s) | 0.102 s |
| Protocol & Blind Analysis | 0.097 s (first 0.097 s) | 0.102 s |
| Reasoning Lab | 0.098 s (first 0.07 s) | 0.075 s |

Page load: server 0.34 s, static 0.256 s; first result in the static preview 0.427 s. Static
preview: 215 files, 24.7 MB. All earlier measurements are in `docs/performance.json`.

---

## Gates (v0.7.0, at release commit `da5ab0f`)

| # | Gate | Command / evidence | Status |
|---|---|---|---|
| G1 | Unit, integration, robustness and parity tests | `python -m pytest` (via `verify.py`): **292 passed, 2 skipped** (astropy not installed). The 0.6.1 baseline was 269 passed; no test was removed | PASS |
| G2 | Every control, both modes, desktop/tablet/phone widths | `pytest -m e2e tests/e2e`: **89 passed**. The baseline was 73; `t1`–`t8` were added in both modes | PASS |
| G3 | Browser ports equal Python | `test_frontier.py`: horizon, challenge and review overlays, twin comparison, investigation twin, angular separation, galactic coordinates and sexagesimal parsing, run under Node against Python on the same inputs. All earlier parity tests still run | PASS |
| G4 | Known-answer and rule tests of the Phase 7 methods | `test_frontier.py` (18 tests). Re-assessment with no change reproduces the record exactly (both fixtures). Counterfactuals are isolated: bundle file hashes and the baseline object are unchanged. Validation refusals are tested. Synthetic scenarios are byte-deterministic and labelled, with known-answer verdicts and refusals. Schedule comparison is tested. ASL-1 rules and statuses, INFO-1 has no probabilities, REPRO-1 verdicts are tested and a tampered record fails R8. REVIEW-1 findings cite sources. Twin integrity and comparison are tested. Possibility layers and horizon cards are tested. Every action has a permission class, the executor implements every registered action, and v0.7 session fields are accepted while 0.6 sessions stay valid. Plus `integration/test_api.py::test_phase7_frontier_counterfactual_reproduce_synthetic` | PASS |
| G5 | Whole-system verification | `python scripts/verify.py --e2e` at `da5ab0f`: **VERIFIED 18/18**, with 4 warnings (no astropy, no real bundles, no Meta key, smoke test never run) | PASS |
| G6 | Static preview integrity | `verify.py`: 184 files match `PREVIEW_MANIFEST.json` | PASS |
| G7 | Provenance of the fixture investigations | `verify.py`: 10 checks per fixture | PASS |
| G8 | Catalogue consistency | `test_phase7_catalogue.py` (4 tests). It checks 400 brief concepts in 40 domains, 406 distinct, synonyms that point to counted concepts, and that every cited file, test function and Phase 6 entry exists. Deferred items must cite nothing and the generated files must be current. The 0.5 and 0.6 catalogue tests are unchanged | PASS |
| G9 | Records unchanged by Phase 7 | The content hashes of all 12 recorded runs (6 per fixture) in the 0.7.0 preview are identical to the 0.6.1 preview archive | PASS |
| G10 | Accessibility (automated) | `test_accessibility.py`. e2e `test_y` covers accessible names, extended to the eight new workspaces. e2e `test_r` (no horizontal scroll at 820 and 390 px) and `test_k` (Alt+1…9 over the new navigation) | PASS |
| G11 | Accessibility with a screen reader | — | NOT RUN |
| G12 | Performance measured | `python scripts/measure_performance.py` writes `docs/performance.json` (results below) | PASS |
| G13 | Real SPHEREx acquisition and live archive tests | `diagnose_environment.py` re-run: IRSA SIA/TAP, SIMBAD, Gaia, Meta, PyPI and npm all get a proxy 403. `pytest -m live tests/live`: 2 failed and 2 errors, each `proxy_refused (proxy answered 403 to CONNECT; host not allowed)` | BLOCKED |
| G14 | Native reader vs astropy on a real SPHEREx file | Needs network and astropy (PyPI 403) | BLOCKED |
| G15 | Live Meta Model API call; multi-agent research; semantic indexing | No key; the API host is refused (403). No embedding model is reachable | BLOCKED |
| G16 | Dockerfile build | Base images cannot be pulled | NOT RUN |
| G17 | Hosted preview after republishing | Published as version 6 of the hosted artifact. `data/status.json` (0.7.0, commit `da5ab0f`), `js/autopilotui.js` and `data/t/syn-var-1/counterfactuals.json` were read back from the hosted artifact with SHA-256 identical to the local build. The page was **not opened in a browser**: no browser on the desktop app was reachable from this session. The same files were exercised by the static-mode e2e run (G2) and the Phase 7 screenshots | PARTIAL (files verified; not opened) |
| G18 | Release artifacts | `scripts/make_release.py`: archives verified (release section below). Earlier artifacts (0.2.0–0.6.1) untouched | PASS |

## Release (0.7.0)

| Version | Commit | Archive (sha256) | Preview archive (sha256) | Hosted artifact |
|---|---|---|---|---|
| 0.7.0 | `da5ab0f` | `dist/skytrace-0.7.0.zip` (`57e962d8a08d9bf1efde42d3c8529a7272cc57adcd105fa569d9d7c82c97676a`, 434 files, 17.5 MB; zip integrity verified, no forbidden files, bundle checksums OK) | `dist/skytrace-preview-0.7.0.zip` (`fbd0b9954294d2289507e33fe8466769ced25b9d5d54f20d7af20309b598e48c`) | version 6 (G17) |

The manifest is kept as `dist/RELEASE_MANIFEST-0.7.0.json`. Nothing was pushed.

## New tests in v0.7

Unit/API:
- `test_frontier.py` (18, including two Node parity tests and the executor/registry coverage test)
- `test_phase7_catalogue.py` (4)
- `integration/test_api.py::test_phase7_frontier_counterfactual_reproduce_synthetic`

One assertion changed because the fact changed: the registry version, from CAPREG-2 to CAPREG-3.

Browser (both modes, `e2e/test_controls.py`):
- `t1` Discovery Horizon: six layers, the nine card fields, category filter, map, export, plan hand-off.
- `t2` Counterfactual Lab: preset with assumed label and baseline-intact indicator, lineage, export. Server: custom error-scale scenario labelled simulated. Static: refusal.
- `t3` Adversarial Lab: challenge with rule, acknowledgement note, ranking with no numerical gain, user-proposed and model-derived relationships.
- `t4` Synthetic Observatory and Observation Design: template run labelled synthetic, schedule comparison, brief export.
- `t5` Autopilot: plan-only level cannot run, authorization required, steps completed, proposed next step.
- `t6` Cosmic Atlas: table, field view.
- `t7` Knowledge Atlas and twins: search results, integrity recomputes, different kinds not comparable.
- `t8` Review Room: reviewers are not people, verdict "reproduced", ten story chapters, export.

`test_k`, `test_r` and `test_y` were extended to the new workspaces.

## Performance (v0.7.0; this machine, 2 CPUs, median of 3; `docs/performance.json`)

| Measurement | Server mode | Static preview |
|---|---:|---:|
| Page load | 0.272 s | 0.203 s |
| First result (server: runs the analysis; preview: loads the precomputed run) | 4.294 s | 0.374 s |
| Discovery Horizon, first cards | 0.095 s | 0.113 s |
| Adversarial Lab, first challenge | 0.077 s | 0.090 s |
| Review Room, first finding | 0.060 s | 0.051 s |
| Counterfactual preset (threshold re-assessment) → result | 0.081 s | 0.075 s |
| Synthetic template → result (server: verify or write the bundle and run the full analysis) | 4.437 s | 0.064 s |
| Autopilot, objective → plan | 0.082 s | 0.061 s |
| Cosmic Atlas, Knowledge Atlas | 0.076 s, 0.115 s | 0.071 s, 0.070 s |

Server API (`syn-var-1` / `syn-hpm-1`):

| Call | `syn-var-1` | `syn-hpm-1` |
|---|---:|---:|
| Frontier report, first call for a new record | 0.111 s | 0.105 s |
| Counterfactual exclusion (pipeline re-run) | 3.061 s | 2.910 s |
| Reproducibility challenge with replay | 3.597 s | 3.517 s |
| Analysis | 3.591 s | 3.357 s |
| Stability check | 21.2 s | 20.0 s |

The static preview is 184 files and 18.3 MB. Phase 6 workspace timings are unchanged within noise (see `performance.json`).

## Screenshots (v0.7)

`docs/screenshots/phase7-*.png` (16), taken from the static preview by `python scripts/phase7_screenshots.py`:
- discovery-horizon, discovery-horizon-mobile, opportunity-map
- counterfactual-lab
- adversarial-lab, test-ranking, causality-workbench
- synthetic-observatory, observation-design
- autopilot
- cosmic-atlas
- knowledge-atlas, twins
- review-room, reproducibility, story

Every image shows synthetic test data and is labelled so. Looking at them found three defects, which were fixed before the
release commit:
- Long tables in the new workspaces clipped their right-hand columns.
- The reproducibility verdict rule ran past its card.
- At the plan-only level, the autopilot said "skipped (needs inspect)" for steps whose permission the level nominally allows.

---

# Test report — v0.6.0 and v0.6.1 (2026-10-30)

Statuses: **PASS** (executed, met), **FAIL** (executed, not met), **BLOCKED** (could not be executed here; the reason is
named), **NOT RUN** (not attempted).

## Gates (v0.6.0)

| # | Gate | Command / evidence | Status |
|---|---|---|---|
| G1 | Unit, integration, robustness, parity tests | `python -m pytest` (via `verify.py`) → **269 passed, 2 skipped** (astropy not installed); baseline at 0.5.0 was 225 passed — no test removed | PASS |
| G2 | Every control, both modes, desktop/tablet/phone widths | `pytest -m e2e tests/e2e` → **73 passed** (31 control steps × 2 modes + 11-step journey); baseline 51 | PASS |
| G3 | Browser ports equal Python | adds SKY-CANON-1 (number spelling, key order, refusals), SCHEMA-1, session validation and hash, PLAN-1, MISSION-1, WF-1 and the 15-intent copilot routing to the 0.5 parity set | PASS |
| G4 | Known-answer and rule tests of the Phase 6 methods | `test_research_os.py` (14: matrix = logged decisions, sequences, duplicates, DQ with injected defects, ledger, radar ranking, planner plans, missions, workflows, experiments incl. negative control, connectors send nothing, Retry-After bound, registry consistency), `test_research_session.py` (7), `test_notebook_package.py`, `test_copilot2.py` (12) | PASS |
| G5 | Whole-system verification | `python scripts/verify.py --e2e` → **VERIFIED 18/18**, 4 warnings (no astropy, no real bundles, no Meta key, smoke test never run) | PASS |
| G6 | Static preview integrity | `verify.py`: 157 files match `PREVIEW_MANIFEST.json` | PASS |
| G7 | Provenance of the fixture investigations | `verify.py`: 10 checks per fixture | PASS |
| G8 | Catalogue consistency | `test_feature_catalogue.py` (0.5, unchanged) and `test_phase6_catalogue.py`: 300 brief concepts in 30 domains, 309 distinct, synonyms point to counted concepts, every cited file and test function exists, deferred/out-of-scope items cite nothing, generated files current | PASS |
| G9 | Accessibility (automated) | `test_accessibility.py` (contrast of every text token; reduced motion disables animation); e2e `test_y` (accessible names over all workspaces and the session box), `test_k` (focus return, Alt+1…9), `test_r` (no horizontal scroll in nine workspaces at 820 and 390 px), sessions dialog Escape and focus trap (`s9`) | PASS |
| G10 | Accessibility with a screen reader | — | NOT RUN |
| G11 | Performance measured | `python scripts/measure_performance.py` → `docs/performance.json` (below) | PASS |
| G12 | Real SPHEREx acquisition and live archive tests | `diagnose_environment.py` re-run 2026-10-30: IRSA SIA/TAP, SIMBAD, Gaia, Meta, PyPI, npm → proxy 403. `pytest -m live tests/live` → 2 failed, 2 errors, each `proxy_refused (proxy answered 403 to CONNECT)` | BLOCKED |
| G13 | Native reader vs astropy on a real SPHEREx file | needs network and astropy (PyPI 403) | BLOCKED |
| G14 | Live Meta Model API call | no key in the environment; the API host is refused (403) | BLOCKED |
| G15 | Dockerfile build | base images cannot be pulled | NOT RUN |
| G16 | Hosted preview opened after republishing | 0.6.0 published as version 4 of the hosted artifact and opened in the built-in browser of the Claude desktop app (not signed in; the artifact is readable by link): page loaded with *Skytrace 0.6.0 · preview 70e3dc4*; Command Center, planner (plan, *Run 3 ready steps* → completed with results), copilot question with source label, *Add to notebook as draft* → two draft blocks in the notebook; only console error was the host's own `/api/account` 403. **Found a defect**: at 861–1180 px the top bar pushed *Run* and *Copilot* off-screen → fixed in 0.6.1 (see the release section) | PASS for 0.6.0 (defect found and fixed); 0.6.1 opened only as files (see below) |
| G17 | Release artifacts | `scripts/make_release.py` → 0.6.0 and 0.6.1 archives with verified contents (release section below); 0.4.0 and 0.5.0 artifacts untouched | PASS |

## Release (0.6.0, then 0.6.1)

| Version | Commit | Archive (sha256) | Preview archive (sha256) | Hosted artifact |
|---|---|---|---|---|
| 0.6.0 | `70e3dc4` | `dist/skytrace-0.6.0.zip` (`cc6965deef0e…`, 389 files) | `dist/skytrace-preview-0.6.0.zip` (`2f7f8fd6f405…`) | version 4 — opened and exercised in a real browser (G16) |
| 0.6.1 | `4689ea2` | `dist/skytrace-0.6.1.zip` (`14bfeec56b72…`) | `dist/skytrace-preview-0.6.1.zip` (`b6f58b3d8795…`) | version 5 — `data/status.json` (0.6.1, commit 4689ea2) and `css/app.css` (sha256 identical to the local build) read back from the hosted artifact; the page was **not** re-opened in a browser after this publish (the link to the desktop app's browser dropped) |

0.6.1 gates: `verify.py --e2e` re-run at `4689ea2` → **VERIFIED 18/18** (269 passed / 2 skipped; browser 73 passed,
including the extended top-bar check at nine widths in both modes). Earlier archives (0.2.0–0.5.0 and their previews) were
not touched; manifests are kept as `dist/RELEASE_MANIFEST-<version>.json`. Nothing was pushed.

## New tests in v0.6

Unit/API: `test_research_session.py` (7, incl. Node parity), `test_research_os.py` (14), `test_notebook_package.py` (1),
`test_copilot2.py` (12), `test_phase6_catalogue.py` (4), `test_accessibility.py::test_reduced_motion_disables_animation`,
four new tool-contract cases (one per new tool), intent-routing parity extended to the five new intents,
`integration/test_api.py::test_phase6_research_planner_sessions_experiments_connectors`. Two assertions changed because the
facts changed: the registry version (CAPREG-1 → CAPREG-2) and the tool count (12 → 16).

Browser (both modes, `e2e/test_controls.py`): `s1` Command Center, session and mission progress; `s2` planner plans, runs,
needs-review, refusal, persistence across reload, revision 2; `s3` quality checks, matrix → metadata diff, coverage and
sequences; `s4` connectors (server: request preview; static: refusal); `s5` radar; `s6` ledger inspectors; `s7` notebook
blocks, versions, undo, exports; `s8` experiments and workflows (server mode also: cancel, then retry only the rest); `s9`
sessions export, verified import, tampered import refused, branch; `s10` figure studio (exported SVG parses); `h2` copilot
source labels, notebook draft, plan hand-off (static: the recorded question is disclosed). `test_k`, `test_r`, `test_y` were
extended to the new workspaces.

## Performance (v0.6.0; this machine, 2 CPUs, median of 3; `docs/performance.json`)

| Measurement | Server mode | Static preview |
|---|---:|---:|
| Page load | 0.221 s | 0.225 s |
| First result (server: runs the analysis; preview: loads the precomputed run) | 5.191 s | 0.431 s |
| Command Center first render | 0.096 s | 0.098 s |
| Planner: plan shown after *Plan* | 0.095 s | 0.076 s |
| Data Quality first render | 0.052 s | 0.051 s |
| Evidence Ledger (graph) first render | 0.090 s | 0.084 s |
| Discovery Radar first render | 0.088 s | 0.096 s |
| Notebook first render | 0.062 s | 0.061 s |
| Experiment Studio first render | 0.073 s | 0.046 s |
| Discovery Engine / Hypothesis Arena / Uncertainty tab | 0.077 / 0.051 / 0.078 s | 0.124 / 0.065 / 0.078 s |

Server API, syn-var-1 / syn-hpm-1: analysis 4.427 / 3.807 s; research report (compatibility, quality, ledger, radar; first,
uncached call) 0.067 / 0.058 s; plan 0.003 / 0.002 s; discovery report 0.009 / 0.010 s; package 0.058 / 0.058 s;
stability check 27.3 / 23.7 s. Static preview: 158 files, 16.8 MB. The analysis pipeline is unchanged since 0.5 (2.6 s
measured then); the slower times were measured on the same 2-CPU container under different load and are not attributed to
Phase 6, whose readers add the listed milliseconds.

## Screenshots (v0.6)

`docs/screenshots/phase6-command-center.png`, `phase6-command-center-mobile.png`, `phase6-planner.png`,
`phase6-data-quality.png`, `phase6-compatibility-matrix.png`, `phase6-evidence-ledger.png`, `phase6-claim-inspector.png`,
`phase6-discovery-radar.png`, `phase6-experiment-studio.png`, `phase6-notebook.png` (from the static preview,
`python scripts/phase6_screenshots.py`).

---

# Test report — v0.5.0 (2026-10-30)

Statuses: **PASS** (executed, met), **FAIL** (executed, not met), **BLOCKED** (could not be executed here; the reason is
named), **NOT RUN** (not attempted).

## Gates

| # | Gate | Command / evidence | Status |
|---|---|---|---|
| G1 | Unit, integration, robustness, parity tests | `python -m pytest` → **225 passed, 2 skipped** (astropy not installed) | PASS |
| G2 | Every control, both modes (server and static preview), desktop/tablet/phone widths | `pytest -m e2e tests/e2e` → **51 passed** (20 control steps × 2 modes + 11-step journey) | PASS |
| G3 | Browser ports equal Python | content hash, pair comparison (all pairs of both fixtures), registration diagnostics, overall hypothesis rule (258 combinations), question routing | PASS |
| G4 | Known-answer tests of the Phase 5 methods | `tests/unit/test_discovery.py` (17 tests: injected motion, injected gain change, recompute of every calibrated z, package determinism, registry integrity, graph explanations) | PASS |
| G5 | Whole-system verification | `python scripts/verify.py --e2e` → **VERIFIED 18/18**, 4 warnings (no astropy, no real bundles, no Meta key, smoke test never run) | PASS |
| G6 | Static preview integrity | `verify.py`: preview files match `PREVIEW_MANIFEST.json` | PASS |
| G7 | Provenance of the fixture investigations | `verify.py`: 10 checks per fixture | PASS |
| G8 | Feature catalogue consistency | `tests/unit/test_feature_catalogue.py` (≥ 250 concepts, 25 domains, tiers recomputed, every implemented concept cites an existing verification file, generated files current) | PASS |
| G9 | Accessibility (automated) | `tests/unit/test_accessibility.py` (contrast of every text token on every surface ≥ 4.5:1); e2e `test_y` (accessible names, dialog semantics), `test_k` (focus return), `test_r` (no horizontal scroll at 820/390 px) | PASS |
| G10 | Accessibility with a screen reader | — | NOT RUN |
| G11 | Performance measured | `python scripts/measure_performance.py` → `docs/performance.json` (below) | PASS |
| G12 | Real SPHEREx acquisition and live archive tests | `pytest -m live tests/live` → 2 failed, 2 errors: proxy 403 for IRSA, SIMBAD, Gaia | BLOCKED |
| G13 | Native reader vs astropy on a real SPHEREx file | needs network and astropy (PyPI 403) | BLOCKED |
| G14 | Live Meta Model API call | no key in the environment; api.meta.ai refused (403) | BLOCKED |
| G15 | Dockerfile build | base images cannot be pulled | NOT RUN |
| G16 | Hosted preview opened after republishing | the artifact page requires a sign-in the build environment does not have; the identical files pass G2 in static mode | NOT RUN |
| G17 | Release artifacts | `scripts/make_release.py` → `dist/skytrace-0.5.0.zip`, `dist/skytrace-preview-0.5.0.zip`, `dist/RELEASE_MANIFEST-0.5.0.json`; 0.4.0 artifacts untouched | see the manifest |

## New tests in v0.5

`unit/test_discovery.py` (17), `unit/test_feature_catalogue.py` (3), `unit/test_accessibility.py` (2),
`unit/test_static_preview.py::test_js_overall_rule_matches_python` and `::test_js_intent_routing_matches_python`,
`integration/test_api.py::test_phase5_discovery_package_capabilities_and_vault`, and in `e2e/test_controls.py`
(both modes): levels and top-bar fit (`j`), palette, help and shortcuts (`k`), Discovery Engine (`l`), Hypothesis Arena
with add, remove and undo (`m`), uncertainty tab and SVG figure export (`n`), registration diagnostics (`o`), vault and
studio: tags, search, filter, rename, duplicate, compare, reopen with saved hypotheses, every studio download including
the package's integrity (`p`), capability question and answer sections (`q`), new workspaces at tablet and phone widths
(`r`), accessible names (`y`). Existing steps were extended: graph explanation nodes (`e`), import preview and refusal of
a tampered record before storing (`g`).

## Performance (this machine, median of 3; `docs/performance.json`)

| Measurement | Server mode | Static preview |
|---|---:|---:|
| Page load | 0.172 s | 0.151 s |
| First result (server: runs the analysis; preview: loads the precomputed run) | 3.611 s | 0.286 s |
| Discovery Engine first render | 0.078 s | 0.098 s |
| Hypothesis Arena render | 0.063 s | 0.068 s |
| Uncertainty tab render | 0.075 s | 0.072 s |

Server API, syn-var-1 / syn-hpm-1: analysis 2.603 / 2.705 s; discovery report
0.007 / 0.007 s; evidence graph 0.006 / 0.006 s;
package 0.034 / 0.039 s (110,666 / 113,739 bytes);
stability check 16.246 / 15.341 s. Static preview: 122 files,
12.9 MB.

## Screenshots (v0.5)

`docs/screenshots/phase5-discovery.png`, `phase5-arena.png`, `phase5-uncertainty.png`, `phase5-graph-explanations.png`,
`phase5-studio.png`, `phase5-palette.png`, `preview-mobile-discovery.png`, `preview-tablet-discovery.png`.

The sections below are the v0.4.0 and v0.3.0 reports, unchanged.

# Test report — v0.4.0 (2026-10-29)

## Phase 4 additions (previewable application)

| Command | Result |
|---|---|
| `python scripts/verify.py --e2e` | **VERIFIED, 18/18 checks** (new: static preview build matches its manifest) |
| `python -m pytest tests/unit tests/integration tests/robustness` | **199 passed, 2 skipped** |
| `python -m pytest -m e2e tests/e2e` | **31 passed**: the 11-step journey plus `test_controls.py` (10 steps) in the server **and** the static-preview mode |
| `python scripts/build_static.py` | 90 files, 10.4 MB, from the real server (OFFLINE=1) |
| Hosted artifact | published (version 2); opening it from the build environment: **NOT RUN** (sign-in required) |

New tests: `unit/test_static_preview.py` (Node: browser pair comparison equals Python for all 2,260 pairs of both fixtures; browser content hash equals Python and detects edits; both mutation-checked), `integration/test_api.py::test_record_export_and_verified_import`, `unit/test_report_ai.py::test_evidence_graph_names_every_recorded_method_and_uses_assessed_significance`, `e2e/test_controls.py` (every visible control, back/forward, keyboard selection, overlay dismissal with Escape, tablet and mobile widths, downloads, import of an intact and a tampered record, no external requests).

The sections below are the Phase 3 report (v0.3.0), unchanged.

# Test report — v0.3.0 (2026-10-29)

Phase 3 (validation and scientific completion). Everything below was executed in the cloud build
container on 2026-10-29. **All data processed are synthetic**; no real SPHEREx file was available (see
`docs/ENVIRONMENT_REPORT.md`).

## Environment

| Item | Value |
|---|---|
| OS | Linux 6.18.44 (cloud build container) |
| Python | 3.13.18 |
| Packages | numpy 2.5.3, scipy 1.18.1, pydantic 2.13.5, starlette 1.7.0, uvicorn 0.54.0, requests 2.34.2, playwright 1.63.0 |
| Browser | Chromium 153.0.8010.12 (Playwright) |
| astropy | **not installed**: PyPI unreachable by either route (direct DNS fails; proxy 403) |
| Network | IRSA, SIMBAD, Gaia, api.meta.ai, PyPI, npm refused by the egress proxy (`403` at CONNECT) |

## Commands and results

| Command | Result |
|---|---|
| `python scripts/verify.py --e2e` | **VERIFIED, 17/17 checks**, 4 warnings (astropy missing, no archive bundles, no Meta key, smoke test never run) |
| `python -m pytest tests/unit tests/integration tests/robustness` | **193 passed, 2 skipped** (the two astropy cross-checks) |
| `python -m pytest -m e2e tests/e2e` | **11 passed** |
| `python -m pytest -m live tests/live` | **2 failed, 2 errors**: every request refused by the proxy (expected here) |
| `python scripts/verify_provenance.py --all --rerun` | **PASS** for syn-hpm-1 and syn-var-1 (10/10 checks each, including re-run determinism) |
| `python scripts/make_synthetic_fixtures.py --check` | fixtures regenerate **byte-identically** from the package generator |
| `python scripts/acquire_targets.py --target barnards-star` | `BLOCKED: target resolution failed` — `live#1: proxy_refused`; no bundle written, nothing substituted |
| `python scripts/meta_smoke_test.py` | not run: no API key and no route |
| `python scripts/diagnose_environment.py` | written to `data/environment_report.json` |

## Test suites

| File | Tests | Covers |
|---|---|---|
| `unit/test_coords.py` | 24 | coordinate parsing, geometry, epochs, space motion, parallax term |
| `unit/test_ephemeris.py` | 5 | **new**: Earth position vs 2026 perihelion/aphelion (2×10⁻⁴ AU) and equinox (0.02°); parallax ellipse radius and obliquity split |
| `unit/test_wavelength_flags.py` | 7 | WLMATCH accept/reject, flag-bit resolution |
| `unit/test_calibration_v2.py` | 8 | **new**: REFSEL-2 cuts and counts, epoch grouping and error floor, correlated-error protection, structured pair codes incl. margin and release, PAIRDIFF-2 removes a 5 % gain change, ≥ 3-reference requirement, robust scatter, SIA detector from `obs_publisher_did` |
| `unit/test_measurement.py` | 12 | centroid/photometry error calibration (pulls), masking, plate solution, motion fit, blends |
| `unit/test_fits_wcs.py` | 10 (1 skipped) | standard FITS, round trip, TAN, SIP, -TAB, astropy cross-check (skipped) |
| `unit/test_fits_wcs_external.py` | 22 | **new (Gate C)**: independent astropy/wcslib files, see `FITS_WCS_VALIDATION.md` |
| `unit/test_archive.py` | 16 | live→cache→fixture labels, offline, retries; **new**: proxy policy denial is not retried |
| `unit/test_acquire.py` | 4 | acquisition against a mocked archive |
| `unit/test_assess2.py` | 3 | **new**: every ASSESS-2 category reachable; non-detection and failure statements; sensitivity; self-documentation fields |
| `unit/test_provenance_check.py` | 5 | **new**: clean record passes incl. determinism; edited number, foreign bundle, modified file, unknown code and wrong origin all detected |
| `unit/test_tool_contracts.py` | 14 | **new**: TOOLS-2 envelope for all 11 tools with sockets disabled, size bound, typed error codes, failed calls not citable, no side effects |
| `unit/test_report_ai.py` | 41 | report, tools, graph, guard (incl. **new GUARD-3 identifier and uncertainty checks**), copilot loop with a **scripted stand-in client** (not a model), fallback |
| `unit/test_offline_workflow.py` | 3 | full workflow with sockets blocked; outcomes match synthetic truth |
| `integration/test_api.py` | 9 | real server process; **new**: Phase 3 parameter validation and the stability endpoint |
| `robustness/test_robustness.py` | 12 | **new**, synthetic variants with known truth (below) |
| `e2e/test_app.py` | 11 | browser journey offline; **new** step 05b: sensitivity, calibrated z, calibration check, parallax/visit display, status codes, stability check |
| `live/test_live_archive.py` | 4 | real services; not runnable here |

## Robustness results (synthetic, labelled)

| Scenario | Truth | Result |
|---|---|---|
| Parallax 800 mas on a 4.67″/yr star | pm (3200, −3400) | corrected: (3329 ± 326, −3463 ± 302) mas/yr, `motion_detected`, z = 0.40/−0.21; **uncorrected: 4063 ± 652 mas/yr in RA** (bias 860 mas/yr) |
| 25 % gain change in one pass, constant star | no variability | PAIRDIFF-1 max \|z\| = 6.2 (would be a false candidate); PAIRDIFF-2 max \|z\| = 1.8 → **not a candidate**; gain measured by reference ratio |
| Same gain change + real 38 % dimming | variable | still `variability_candidate` |
| Passes split across two releases | dimming only testable across releases | refused by default (`different_releases`), **no candidate claimed**; with mixing allowed → candidate |
| 4 offset reference stars with RUWE > 1.4 | pm unchanged | REFSEL-2 removes all 4; `motion_detected` |
| 2 offset reference stars without RUWE | pm unchanged | removed per exposure by leave-one-out plate rejection |
| Unmodelled distortion (SIP +3×10⁻⁴) | pm unchanged | median plate RMS rises 301 → 421 mas (visible); `motion_detected` |
| Target 33× fainter | — | no candidate; motion `insufficient_evidence`; sensitivity reported |
| Single visit (2.5 d) | — | per-exposure fit, labelled "single visit" |
| Two passes 6 months apart | — | 2-epoch visit fit |
| Stability (STAB-1) on both fixtures | — | all 3 outcomes stable under all 5 perturbations |
| Determinism | — | identical image bytes for identical options |

## Required acceptance tests

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Application starts | **Pass** | e2e `test_01`, integration fixture |
| 2 | Frontend talks to the backend | **Pass** | e2e `test_01`–`test_08` |
| 3 | A **real** SPHEREx investigation completes end to end | **Not met (blocked)** | no route to IRSA; the chain completes on SPHEREx-format synthetic bundles and mocked archive responses |
| 4 | Real archive products read successfully | **Not met (blocked)** | native reader validated on independent files instead (Gate C) |
| 5 | Metadata and provenance preserved | **Pass** (synthetic + mocked) | `test_acquire`, PROVCHECK-1 |
| 6 | Wavelength rules applied and explained | **Pass** | e2e `test_04`, pair codes |
| 7 | Measurements and uncertainties displayed | **Pass** | e2e `test_03`, `test_05`, `test_05b` |
| 8 | Copilot invokes approved read-only tools | **Pass** (local mode; scripted client) | **Live Meta: not tested (blocked)** |
| 9 | Guard blocks unsupported claims | **Pass** | `test_guard_blocks`, `test_guard3_identifiers_and_uncertainty` |
| 10 | Trace a result to its observations | **Pass** | e2e `test_06`; PROVCHECK-1 file-level trace |
| 11 | Works offline | **Pass** | e2e `test_09` (zero non-local requests) |
| 12 | Fixtures cannot be mistaken for real observations | **Pass** | e2e `test_02`; PROVCHECK `data_origin`; tool envelope `data_status` |
| 13 | Saved investigations reopen and reproduce | **Pass** | e2e `test_08`; PROVCHECK `determinism` |
| 14 | Major UI actions work | **Pass** for those exercised (now incl. stability check and Phase 3 toggles) |
| 15 | Installable and launchable | **Pass** (editable install; `python run.py`) | PyPI download not exercised |

## Screenshots

`docs/screenshots/`: `real-target-no-data`, `explorer`, `time-machine-matched`, `time-machine-incompatible`,
`lab-outcomes`, `lab-rerun`, `lab-stability` (new), `evidence-graph`, `copilot`, `records`, `mobile`.
