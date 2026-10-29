# Test report — v0.2.0 (2026-10-29)

## Environment

| Item | Value |
|---|---|
| OS | Linux 6.18.44 (cloud build container) |
| Python | 3.13.18 |
| Packages | numpy 2.5.3, scipy 1.18.1, pydantic 2.13.5, starlette 1.7.0, uvicorn 0.54.0, requests 2.34.2, playwright 1.63.0 |
| Browser | Chromium 153.0.8010.12 (Playwright) |
| Node.js | v22.23.4 (not used: the interface has no build step) |
| astropy | **not installed**: no package index reachable; a source build from GitHub was refused by the environment's safety policy |
| Network | IRSA, SIMBAD, Gaia archive, api.meta.ai, PyPI and npm unreachable (proxy `403` / `connect_rejected`) |

## Commands and results

| Command | Result |
|---|---|
| `python -m pytest` (unit + integration) | **121 passed, 2 skipped** in 29 s. The skips are the two astropy cross-checks |
| `python -m pytest -m e2e tests/e2e` | **10 passed** in 14 s |
| `python -m pytest -m live tests/live` | **2 failed, 2 errors**: every request refused by the proxy (`FetchError: data unavailable … ProxyError … 403`). Expected here; must be run on a networked machine |
| `python scripts/verify.py --e2e` | **VERIFIED, 14/14 checks**, with 4 warnings: astropy missing, no archive bundles, no Meta key, smoke test never run |
| `python scripts/acquire_targets.py --target barnards-star` | stopped at the SIMBAD request (proxy 403) and reported `BLOCKED: target resolution failed`; no bundle written |
| `python scripts/meta_smoke_test.py` | not run: no key, no route |
| `pip install --no-build-isolation --no-deps -e .` in a fresh venv | installs; the `skytrace` command works |

## Test suites

| File | Tests | Covers |
|---|---|---|
| `tests/unit/test_coords.py` | 24 | parsing (decimal, sexagesimal, Unicode minus, WISE 0855 string), bounds, separations, gnomonic, epochs, space motion, parallax term |
| `tests/unit/test_wavelength_flags.py` | 7 | WLMATCH-1 accept/reject reasons, order independence, flag-bit resolution from header/documentation |
| `tests/unit/test_measurement.py` | 12 | centroid accuracy and **error calibration** (pull tests), masking, failure reporting, photometry pulls, flagged/no-sky/off-image, plate solution with outlier, motion fit, end-to-end high-proper-motion recovery, **blend detection** |
| `tests/unit/test_fits_wcs.py` | 10 (1 skipped) | hand-built standard FITS (BZERO unsigned, quoted strings, D exponents), round trip incl. TDIM tables, truncation, TAN, SIP inverse, -TAB with cutout offset, astropy cross-check (skipped) |
| `tests/unit/test_archive.py` | 15 | live→cache→fixture labels, release separation, **OFFLINE with sockets blocked**, fixture provenance required, retries, validation, size cap, corrupted cache, SPHEREx metadata parsing, VOTable/CSV |
| `tests/unit/test_acquire.py` | 4 | acquisition against a **mocked archive**: bundle written and verified, Gaia preferred over SIMBAD, resume without re-download, failed downloads reported not substituted, tamper detection, synthetic data cannot pass as archive |
| `tests/unit/test_report_ai.py` | 40 | report determinism, analysis reproducibility, 11 tools (validation, path injection, unknown tools), incompatible-pair flux refusal, graph integrity, **guard (11 block cases, allowed hedged discussion)**, copilot loop with scripted Meta client, withholding + fallback, budgets, 429 handling, local answers pass the guard for 8 questions × 2 targets |
| `tests/unit/test_offline_workflow.py` | 3 | full workflow with sockets blocked; **outcomes match the synthetic truth** |
| `tests/integration/test_api.py` | 8 | real server process: status, CSP headers, real targets without data, path traversal, parameter bounds, full API cycle incl. records save/replay/open/delete |
| `tests/e2e/test_app.py` | 10 | browser journey under `OFFLINE=1` (below) |
| `tests/live/test_live_archive.py` | 4 | real SIA/TAP/SIMBAD/Gaia, real cutout structure, **native vs astropy** pixels/WCS/wavelength. Not runnable here |

## Required acceptance tests

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Application starts | **Pass** | e2e `test_01`, integration fixture start `run.py` |
| 2 | Frontend loads and talks to the backend | **Pass** | e2e `test_01`–`test_08` |
| 3 | At least one **real** SPHEREx investigation completes end to end | **Not met (blocked)** | no network route to IRSA. The same chain completes end to end on SPHEREx-format synthetic bundles (e2e `test_03`, `test_offline_workflow`) and on mocked archive responses (`test_acquire`) |
| 4 | Real archive products read successfully | **Not met (blocked)** | as above; `tests/live::test_cutout_structure_and_native_reader_matches_astropy` is the check to run |
| 5 | Metadata and provenance preserved | **Pass** (synthetic + mocked archive) | `test_acquire`, `test_archive`, provenance shown in Explorer and reports |
| 6 | Wavelength rules applied and explained | **Pass** | e2e `test_04` (matched banner, incompatible banner, difference disabled), `test_compare_refuses_flux_for_incompatible_pair` |
| 7 | Measurements and uncertainties displayed | **Pass** | e2e `test_03` (aperture flux ± error), `test_05` (charts with error bars, tables) |
| 8 | Copilot invokes approved read-only tools | **Pass** (local mode, scripted Meta client) | e2e `test_07`, `test_copilot_meta_mode_with_tools_and_guard`. **Live Meta: not tested** |
| 9 | Guard blocks unsupported claims | **Pass** | `test_guard_blocks` (9 cases), synthetic rules, withholding test |
| 10 | Trace a result to its observations | **Pass** | e2e `test_06` (claim → highlighted comparisons/measurements/observations) |
| 11 | Works offline with the bundled dataset | **Pass** | e2e under `OFFLINE=1` with zero non-local requests (`test_09`); socket-blocked workflow test. The bundled dataset is synthetic |
| 12 | Fixtures cannot be mistaken for real observations | **Pass** | e2e `test_02` (pill, banner), watermark on every synthetic image, verifier rejects mixed bundles, guard requires "synthetic" in answers |
| 13 | Saved investigations reopen and reproduce | **Pass** | e2e `test_08` ("reproduced: identical content hash", reopen), integration replay |
| 14 | Major UI actions work | **Pass** for those exercised: target switch, run/re-run, row selection, compare modes, partner choice, tabs, parameter re-run, graph selection, suggestion chips, free-text ask, save/replay/open. Not exercised: blink speed slider, fade slider, stretch sliders, report download (API endpoint tested), delete (API tested) |
| 15 | Installable and launchable from the instructions | **Pass** (editable install without dependency download; `python run.py`) | dependency download from PyPI not exercised (no access) |

## Screenshots

Captured by the browser test in `docs/screenshots/`: `real-target-no-data`, `explorer`, `time-machine-matched`, `time-machine-incompatible`, `lab-outcomes`, `lab-rerun`, `evidence-graph`, `copilot`, `records`, `mobile`.
