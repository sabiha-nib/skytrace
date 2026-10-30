# Requirement traceability (v0.6.0, 2026-10-30)

`IMPLEMENTED` means the code exists and its deterministic tests pass. `VERIFIED` means it is also confirmed on real data or a live service. `BLOCKED` names the missing access. Hackathon submission requirements were retired when the project moved to Meta.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| R01 | Target search, coordinate parsing, URL state | `science/coords.py`, `web/js/state.js` | `test_coords.py`; e2e loads `#/explorer?target=…` | IMPLEMENTED | |
| R02 | Real SPHEREx acquisition (QR3, QR2 fallback), checksums, resume, inspection | `archive/acquire.py`, `scripts/acquire_targets.py` | `test_acquire.py` (mocked) | **BLOCKED** | no route to IRSA; run `scripts/acquire_targets.py --all` and `pytest -m live` |
| R02.1 | Bundle manifest from files that exist; verified checksums | `bundle.py`, `scripts/verify_data_bundle.py` | `test_acquire.py`, verify.py | IMPLEMENTED | synthetic bundles verify |
| R02.2 | Observation index | `scripts/build_observation_index.py` | run manually | IMPLEMENTED | |
| R03 | Time Machine: epochs, blink/fade/side-by-side, contrast, overlays, compatibility gating | `web/js/timemachine.js`, `/pair-image` | e2e `test_04` | IMPLEMENTED | |
| R04 | Wavelength-matching rule with reasons | `science/wavelength.py` | unit + e2e | IMPLEMENTED | on synthetic λ |
| R05 | Difference image only for matched pairs | `web/js/viewer.js` | e2e `test_04` | IMPLEMENTED | display only |
| R06 | FITS reading and WCS (astropy or native) | `fitsio.py`, `wcs.py`, `archive/products.py` | `test_fits_wcs.py`; `tests/live` cross-check | IMPLEMENTED, real-file check **BLOCKED** | |
| R07 | Spectrum from measurements | `analysis.py` (spectrum step), Lab › Spectrum | e2e `test_05` | IMPLEMENTED | aperture fluxes, mixed epochs, labelled |
| R08 | Detectors D1–D6 handled separately | throughout | unit | IMPLEMENTED | |
| R09 | Catalogue identity (SIMBAD) and Gaia DR3 astrometry/references | `archive/references.py`, `acquire.resolve` | mocked | **BLOCKED** live | |
| R10 | Five named targets | `config/targets.json` | e2e `test_01` (no-data state) | IMPLEMENTED, data **BLOCKED** | |
| R11 | Reproducible investigation records | `report.py`, records API | reproducibility tests, e2e replay | IMPLEMENTED | |
| R12 | Uncertainty propagation and missing data | science modules | pull tests, NaN→null | IMPLEMENTED | |
| R13 | Evidence graph from recorded facts only | `view.evidence_graph`, `web/js/graph.js` | `test_evidence_graph_only_has_recorded_nodes`, e2e `test_06` | IMPLEMENTED | |
| R14 | Failure modes: flags, blends, outlier references, missing wavelength, edge, wrong responses, tampering | science + archive | unit | IMPLEMENTED | |
| R15 | Method comparison / sensitivity | Lab › Re-run & compare; MOMENT-1 cross-check | e2e `test_05` | IMPLEMENTED | |
| R16 | Investigation history | event log; saved records with transcript | e2e `test_08` | IMPLEMENTED | |
| R17 | Meta Model API integration | `ai/meta_client.py`, `ai/copilot.py` | scripted client | **BLOCKED** live | no key, no route |
| R18 | Read-only tools (12 in 0.5, 16 in 0.6), guard, budgets, audit, local fallback | `ai/` | `test_tool_contracts.py`, `test_report_ai.py`, `test_copilot2.py` | IMPLEMENTED | |
| R19 | Offline mode with sockets blocked | `archive/net.py`, server design | `test_offline_workflow.py`, e2e `test_09` | IMPLEMENTED | |
| R20 | Live/cache/fixture/synthetic labels | `provenance.py`, UI pills/banners/watermark | unit, e2e `test_02` | IMPLEMENTED | |
| R21 | Interactive UI, responsive, keyboard, CSP | `web/` | e2e incl. mobile | IMPLEMENTED | |
| R22 | Security: secrets, path validation, no arbitrary execution | server, tools, verify.py | integration traversal tests, secret scan | IMPLEMENTED | |
| R23 | Tests and test report | `tests/`, `docs/TEST_REPORT.md` | — | IMPLEMENTED | |
| R24 | Documentation | `README.md`, `docs/` | — | IMPLEMENTED | |
| R25 | AI disclosure | `docs/AI_USE.md` | — | IMPLEMENTED | |
| R26 | Single start command, verification command, release archive | `run.py`, `scripts/verify.py`, `scripts/make_release.py` | run | IMPLEMENTED | Dockerfile not built |
| R27 | Environment diagnosis distinguishing DNS / proxy / TLS / HTTP / package failures | `scripts/diagnose_environment.py`, `archive/net.py` | `test_proxy_policy_denial_not_retried` | IMPLEMENTED | `ENVIRONMENT_REPORT.md` |
| R28 | Independent FITS/WCS validation with tolerances | `fitsio.py`, `wcs.py` | `test_fits_wcs_external.py` (22) | IMPLEMENTED, real-file check **BLOCKED** | `FITS_WCS_VALIDATION.md` |
| R29 | Calibration and uncertainty audit with classification | `science/ephemeris.py`, `refsel.py`, `variability.py`, `astrometry.py`, `wavelength.py` | `test_ephemeris.py`, `test_calibration_v2.py`, robustness | IMPLEMENTED | `CALIBRATION_AUDIT.md` |
| R30 | Defensible outcomes: sensitivity, non-detection ≠ static, failure ≠ no motion | `science/assess.py` (ASSESS-2) | `test_assess2.py` | IMPLEMENTED | `ASSESSMENT_ENGINE.md` |
| R31 | Structured reason codes; no free-text parsing for status | `measure.py`, `wavelength.py`, `analysis.py` | `test_pair_codes_structured`, PROVCHECK `status_codes` | IMPLEMENTED | |
| R32 | Provenance verification command | `provenance_check.py`, `scripts/verify_provenance.py` | `test_provenance_check.py`, verify.py | IMPLEMENTED | |
| R33 | Tool contracts (schemas, bounds, envelope, errors, evidence fields, cache) | `ai/tools.py` (TOOLS-2) | `test_tool_contracts.py` | IMPLEMENTED | `COPILOT_TOOLS.md` |
| R34 | Guard: identifiers and uncertainty in addition to claims, numbers, citations, limitations, synthetic status | `ai/guard.py` (GUARD-3) | `test_guard3_identifiers_and_uncertainty` | IMPLEMENTED | |
| R35 | Live Meta test | `scripts/meta_smoke_test.py` | — | **BLOCKED** | api.meta.ai refused; no key |
| R36 | Robustness and perturbation stability (synthetic, labelled) | `synthetic.py`, `stability.py`, `/api/targets/{id}/stability` | `tests/robustness` (12), e2e `test_05b` | IMPLEMENTED | `TEST_REPORT.md` |
| R37 | Previewable application without a server; honest gating of server-only features | `scripts/build_static.py`, `web/js/static/` | `tests/e2e/test_controls.py[static]` | IMPLEMENTED | hosted as a private claude.ai artifact; hosted copy not opened from the build environment (sign-in) |
| R38 | Browser computations equal the Python ones (pair comparison, record content hash) | `web/js/static/compare.js`, `hash.js` | `tests/unit/test_static_preview.py` (Node parity, mutation-checked) | IMPLEMENTED | |
| R39 | Every visible control works or is disabled with a reason; back/forward; keyboard; overlay dismissal | `web/js/*` | `tests/e2e/test_controls.py` (both modes) | IMPLEMENTED | |
| R40 | Record export and verified import | `/api/investigations/{id}/record.json`, `/api/records/import`, `records.js` | integration + e2e | IMPLEMENTED | |

## Phase 5 (v0.5)

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P5.01 | Discovery loop and persistent investigation context | `web/js/main.js`, `state.context` | e2e `test_l_discovery_engine`, `test_p_vault_and_studio` | IMPLEMENTED | question and hypotheses survive navigation and reopen |
| P5.02 | Three levels (Explore / Investigate / Research) | CSS `body[data-level]`, `web/js/lab.js` | e2e `test_j_levels` | IMPLEMENTED | |
| P5.03 | Command palette, keyboard shortcuts, glossary, undo, back/forward | `web/js/palette.js`, `main.js`, `arena.js` | e2e `test_k_palette_help_shortcuts`, `test_m_hypothesis_arena`, `test_f_back_forward` | IMPLEMENTED | undo covers hypothesis removal only |
| P5.04 | Feature catalogue ≥ 250 concepts, 25 domains, 7 scores, tiers | `scripts/feature_catalogue.py` → `docs/FEATURE_CATALOGUE.md` | `test_feature_catalogue.py` | IMPLEMENTED | counts computed |
| P5.05 | Discovery engine stages A–G | `discovery.py`, `web/js/discovery.js` | `test_discovery.py`; e2e | IMPLEMENTED | on synthetic data |
| P5.06 | Hypothesis Arena, rule-driven, no probabilities | `hypotheses.py`, `arena.js`, `rules.js` | `test_discovery.py`, parity test, e2e | IMPLEMENTED | three explanations have no implemented test (shown as not tested) |
| P5.07 | Uncertainty Explorer; sensitivity separate | `uncertainty.py`, `uncertainty.js` | `test_discovery.py`, e2e `test_n` | IMPLEMENTED | |
| P5.08 | Evidence Graph improvements | `view.evidence_graph` (explanation nodes), `graph.js` | `test_discovery.py`, e2e `test_e` | IMPLEMENTED | |
| P5.09 | Advanced Time Machine: registration diagnostics | `view.registration_diagnostics`, `compare.js`, `timemachine.js` | known-answer + parity tests, e2e `test_o` | IMPLEMENTED | |
| P5.10 | Copilot capability registry and evidence-structured answers | `capabilities.py`, tool `list_capabilities`, `copilot.js` | `test_tool_contracts.py`, e2e `test_q` | IMPLEMENTED; Meta model **BLOCKED** | no key, no route |
| P5.11 | Report and figure studio | `records.js` (studio), `figures.js`, `package.py` | e2e `test_n`, `test_p`; package determinism | IMPLEMENTED | PDF export deferred |
| P5.12 | Vault: search, tags, clone, rename, compare, import preview, delete confirmation | `records.js`, `PATCH`/`clone` routes | `test_api.py`, e2e `test_g`, `test_p` | IMPLEMENTED | |
| P5.13 | Offline first-class | OFFLINE=1, static preview with precomputed Phase 5 outputs | `test_offline_workflow.py`, e2e static mode | IMPLEMENTED | |
| P5.14 | Live-data program | `scripts/diagnose_environment.py` | re-run 2026-10-29 | **BLOCKED** | IRSA, SIMBAD, Gaia, Meta, PyPI, npm: proxy 403 |
| P5.15 | Performance and accessibility audit | `scripts/measure_performance.py`, `test_accessibility.py`, e2e `test_y`, `test_r` | as listed | IMPLEMENTED | no assistive-technology session |
| P5.16 | Security: untrusted imports, no secrets in frontend, no telemetry | `state.sanitizeContext`, import preview, verify.py secret scan | e2e, verify.py | IMPLEMENTED | |
| P5.17 | New release without overwriting 0.4.0 | `scripts/make_release.py` (refuses to overwrite) | release run | see TEST_REPORT | |


## Phase 6 (v0.6)

Section numbers refer to the Phase 6 brief. Tests named `s1`–`s10`, `h2` are in `tests/e2e/test_controls.py` and run in server and static mode.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P6.01 | Audit the 0.5 repository first; preserve what works | `docs/PHASE6_AUDIT.md` | baseline `verify.py --e2e` 18/18 | DONE | no 0.5 test removed |
| P6.02 | Persistent, integrity-checked research session; versioned schema; migration | `session.py`, `canon.py`, `schema.py`, `web/js/session*.js`, `server/research.py` | `test_research_session.py` (7, incl. parity), e2e `s2`, `s9` | IMPLEMENTED | old records migrate; never discarded |
| P6.03 | Unified capability registry with actions used by planner, copilot, workflows, missions | `capabilities.py` (CAPREG-2), `web/js/executor.js` | `test_registry_actions_and_capabilities_are_consistent` | IMPLEMENTED | |
| P6.04 | Adaptive Investigation Planner: deterministic, validated, statuses, confirmation, no simulation | `planner.py`, `planner.js`, `plannerui.js` | `test_planner_known_plans`, parity, e2e `s2` | IMPLEMENTED | rule-based; no model intent used (no key) |
| P6.05 | Observatory Command Center with real values only | `commandcenter.js` | e2e `s1` | IMPLEMENTED | |
| P6.06 | Multi-epoch discovery: never interpolate; say when only two epochs | `compat.py` (SEQ-1), `timemachine.js` | `test_sequences_are_cliques…`, e2e `s3` | IMPLEMENTED | |
| P6.07 | Experiment Studio (parameter, sensitivity, method comparison, reproducibility, negative control, robustness); validity note | `experiments.py`, `experimentsui.js` | `test_experiment_validation_and_negative_control`, API, e2e `s8` | IMPLEMENTED | custom parameters need the server |
| P6.08 | Compatibility matrix with explicit rules; metadata diff; duplicates | `compat.py`, `qualityui.js` | `test_matrix_is_the_logged_decisions`, `test_duplicate_files_are_detected`, e2e `s3` | IMPLEMENTED | |
| P6.09 | Evidence Ledger: claims, contradictions, provenance, methods, completeness, history; one item ≠ full support | `ledger.py`, `ledgerui.js` | `test_ledger_counts_support_and_flags_conflicts`, e2e `s6` | IMPLEMENTED | |
| P6.10 | Knowledge graph only from stored relationships; empty state | `kg.js`, `records.js` | e2e `test_p_vault_and_studio` | IMPLEMENTED | |
| P6.11 | Visualization Studio with titles, units, provenance, export; PDF only if valid | `figurestudio.js` | e2e `s10` (SVG parses) | IMPLEMENTED | no PDF offered |
| P6.12 | Research Notebook: blocks, provenance links, authorship, export to package | `notebook.js`, `zipstore.js` | `test_zipstore_output_is_valid_and_deterministic`, e2e `s7`, `h2` | IMPLEMENTED | |
| P6.13 | Data Quality Observatory: five outcomes, no universal score | `quality.py`, `qualityui.js` | `test_quality_outcomes_and_injected_defects`, e2e `s3` | IMPLEMENTED | |
| P6.14 | Connectors: testable boundary, never claim success | `connectors.py`, `archive/net.py` | `test_connector_previews_match_acquisition_and_send_nothing`, `test_retry_after_is_honoured_and_bounded`, e2e `s4` | IMPLEMENTED; live use **BLOCKED** | proxy 403 |
| P6.15 | Copilot 2.0: registry-only, validated plans, answer-source labels | `ai/tools.py`, `ai/local.py`, `copilot.js` | `test_copilot2.py`, `test_tool_contracts.py`, intent parity, e2e `h2` | IMPLEMENTED; Meta model **BLOCKED** | |
| P6.16 | Discovery Radar: opportunities with what / why / evidence / data / method / cannot / can-run-now | `radar.py`, `radarui.js` | `test_radar_items_are_explained_and_ranked_by_the_stated_rule`, e2e `s5` | IMPLEMENTED | |
| P6.17 | Missions without gamification | `missions.py`, `missions.js`, `commandcenter.js` | `test_missions_read_completion_from_the_session`, e2e `s1` | IMPLEMENTED | task order not enforced |
| P6.18 | Research automation: workflows, batch, per-item records, cancel, retry, export/import, bounds | `workflows.py`, `workflows.js`, `experimentsui.js` | `test_workflow_validation`, parity, e2e `s8` (cancel/retry in server mode) | IMPLEMENTED | |
| P6.19 | Catalogue ≥ 300 distinct concepts in the brief's 30 domains, statuses, no synonyms | `scripts/phase6_catalogue.py` → `docs/PHASE6_CATALOGUE.md` | `test_phase6_catalogue.py` | IMPLEMENTED | 309 distinct; 15 merged |
| P6.20 | Prioritisation (Foundation / High Impact / Signature / Frontier) with the §20 fields | same | same | IMPLEMENTED | |
| P6.21 | UI: levels alter visibility only; empty states and disabled actions explain; real loading; responsive | `main.js`, CSS | e2e `test_j_levels`, `test_r_new_workspaces_narrow`, `test_y_accessible_names`, `test_z_no_external_requests_no_errors` | IMPLEMENTED | |
| P6.22 | Versioned schemas, migration, never discard records | `session.py` (`skytrace.research_session/1`), `workflows.py` (`skytrace.workflow/1`) | `test_migration_from_v05_saved_record` | IMPLEMENTED | |
| P6.23 | Tests for every Phase 6 area; BLOCKED reported as blocked; none removed | `tests/` | see TEST_REPORT v0.6.0 | IMPLEMENTED | live tests BLOCKED |
| P6.24 | Release: metadata, docs, methods generated from code, new version only, commit, no push | `scripts/gen_research_methods.py`, `make_release.py` | release run | see TEST_REPORT | not pushed |
| P6.25 | Hosted preview, tested as rendered | `dist/preview/`, hosted artifact | see TEST_REPORT | see TEST_REPORT | |
