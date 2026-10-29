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
