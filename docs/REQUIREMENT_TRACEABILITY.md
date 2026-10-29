# Requirement traceability (v0.2.0, 2026-10-29)

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
| R18 | 11 read-only tools, guard, budgets, audit, local fallback | `ai/` | 40 tests | IMPLEMENTED | |
| R19 | Offline mode with sockets blocked | `archive/net.py`, server design | `test_offline_workflow.py`, e2e `test_09` | IMPLEMENTED | |
| R20 | Live/cache/fixture/synthetic labels | `provenance.py`, UI pills/banners/watermark | unit, e2e `test_02` | IMPLEMENTED | |
| R21 | Interactive UI, responsive, keyboard, CSP | `web/` | e2e incl. mobile | IMPLEMENTED | |
| R22 | Security: secrets, path validation, no arbitrary execution | server, tools, verify.py | integration traversal tests, secret scan | IMPLEMENTED | |
| R23 | Tests and test report | `tests/`, `docs/TEST_REPORT.md` | — | IMPLEMENTED | |
| R24 | Documentation | `README.md`, `docs/` | — | IMPLEMENTED | |
| R25 | AI disclosure | `docs/AI_USE.md` | — | IMPLEMENTED | |
| R26 | Single start command, verification command, release archive | `run.py`, `scripts/verify.py`, `scripts/make_release.py` | run | IMPLEMENTED | Dockerfile not built |
