# Requirement traceability (v0.5.0, 2026-10-30)

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
| R18 | 12 read-only tools, guard, budgets, audit, local fallback | `ai/` | 40 tests | IMPLEMENTED | |
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

