# SKYTRACE — Requirement Traceability Matrix

Updated 2026-10-29 (end of Phase 1 work in the offline workspace). `IMPLEMENTED` = code exists and its deterministic tests pass; `VERIFIED` = additionally confirmed on real data or a live service. Nothing is `VERIFIED` yet. Hackathon-specific requirements are retired (project now built for Meta).

Statuses: `NOT_STARTED` · `IN_PROGRESS` · `IMPLEMENTED` · `VERIFIED` · `BLOCKED` · `DEFERRED`.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| R01.1 | RA/Dec parsing (decimal, sexagesimal, Unicode minus), range validation | `science/coords.py` | `test_coords.py` (16 cases incl. WISE 0855 string) | IMPLEMENTED | astropy cross-check test skipped (astropy absent) |
| R01.2 | URL-addressable view | — | — | NOT_STARTED | Gate F |
| R01.3 | Target identities resolved from SIMBAD + Gaia DR3 | `config/targets.json`, `pipeline.resolve_target` | live test | BLOCKED | no network |
| R02 | SPHEREx discovery (SIA2 per release, TAP cross-check), cutouts | `archive/spherex.py` | `test_archive.py` parsing; `tests/live` | IMPLEMENTED | live tests not run (no network) |
| R02.1 | QR3 default, QR2 fallback, releases cached separately | `archive/spherex.py`, `archive/net.py` | `test_releases_are_cached_separately` | IMPLEMENTED | |
| R02.2 | Provenance on every acquisition | `provenance.py`, `archive/net.py` | `test_archive.py` (labels, fixture sidecar required) | IMPLEMENTED | |
| R02.3 | Bounded downloads | `net.py` (size cap), `spherex.cutout_url` (≤0.5°) | `test_size_bound`, `test_cutout_url_rules` | IMPLEMENTED | |
| R02.4 | Product structure inspected before measuring | `archive/products.py` | live test | BLOCKED | astropy + network unavailable |
| R03 | Time Machine UI | — | — | NOT_STARTED | Gate F |
| R04.1 | Wavelength-matched pairing with reasons | `science/wavelength.py` | `test_wavelength_flags.py`, e2e synthetic | IMPLEMENTED | needs real λ-at-pixel values |
| R05 | Difference images | — | — | NOT_STARTED | after Gate C; pair rule already defines valid inputs |
| R06 | Field of view / WCS handling | `products.Product.sky_to_pixel` (astropy, SIP) | — | IN_PROGRESS | untested on real header |
| R07 | Spectrum from real measurements | per-exposure λ + photometry in `measure.py` | — | IN_PROGRESS | spectrum assembly/plot not built; no real data |
| R08 | Detector arrays D1–D6 | `spherex.DETECTOR_BANDS_UM`, detector parsing | `test_observations_from_sia_rows` | IMPLEMENTED | each detector handled as its own product; no co-adding |
| R09 | Catalogue matching | `references.gaia_cone`, `resolve_target` (pm-consistency match) | — | IN_PROGRESS | live untested |
| R10 | Five named targets | `scripts/feasibility.py`, `config/targets.json` | ran 2026-10-29 | BLOCKED | every target stopped at SIMBAD (proxy 403); see DATA_FEASIBILITY_REPORT |
| R11 | Reproducible investigation records | `report.py` (content hash, params, versions) | `test_report_is_deterministic_and_marks_synthetic` | IMPLEMENTED | |
| R12 | Uncertainty and missing data | centroid/photometry/astrometry covariances; NaN→null | pull tests (centroid, photometry), motion fit | IMPLEMENTED | calibrated on synthetic only |
| R13 | Evidence graph | event log + provenance per event | — | IN_PROGRESS | graph view is Gate F |
| R14 | Failure modes | flagged pixels, hot pixel, edge truncation, outlier reference, invalid responses, corrupted cache | unit tests | IN_PROGRESS | misregistration/gradient/normalisation cases not yet written |
| R15 | Method Arena | CENTROID-G2D-1 vs MOMENT-1 | `test_moment_centroid_cross_check` | IN_PROGRESS | PSF-extension fit planned |
| R16 | Discovery trajectory | `Investigation` events incl. rejections | report tests | IMPLEMENTED | persistence store (SQLite) not built |
| R17 | Meta integration | `ai/meta_client.py`, `scripts/meta_smoke_test.py` | scripted-client tests | BLOCKED | no network, no key |
| R18 | Guardrails: typed tools, budgets, guard, audit | `ai/tools.py`, `ai/guard.py`, `ai/copilot.py` | `test_report_ai.py` (11 tests) | IMPLEMENTED | |
| R19 | Offline mode with sockets blocked | `archive/net.py`, `MetaClient` | `test_offline_never_touches_network` (socket guard) | IMPLEMENTED | |
| R20 | Cache + fixtures with truthful labels | `archive/net.py` | 5 tests | IMPLEMENTED | no real fixtures yet (none can be legitimately created without data) |
| R21 | Interactive UI | — | — | NOT_STARTED | Gate F |
| R22 | Secrets via env; no arbitrary execution | `.env.example`, `.gitignore`, tools registry | `test_tools_validate_arguments` | IMPLEMENTED | |
| R23 | Tests: deterministic + live split | `tests/unit`, `tests/live` | 66 pass, 1 skip | IMPLEMENTED | |
| R24 | Documentation | README, CLAUDE.md, AGENTS.md, docs/* | — | IN_PROGRESS | SCIENTIFIC_METHODS content currently in module docstrings |
| R25 | AI disclosure | README §AI, MODEL_INTEGRATION.md | — | IN_PROGRESS | |
| R26 | Public repository | — | — | NOT_STARTED | needs your GitHub decision |
| R27 | Hackathon submission | — | — | DEFERRED | retired: project is for Meta |
