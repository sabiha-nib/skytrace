# CLAUDE.md — Skytrace

Evidence-first investigation of repeated SPHEREx observations. Built for Meta (not a hackathon submission).

## Commands
- Start: `python run.py` (add `OFFLINE=1` to forbid network use) → http://127.0.0.1:8600
- Verify everything: `python scripts/verify.py [--e2e]`
- Tests: `pytest` (unit + API) · `pytest -m e2e tests/e2e` (browser) · `pytest -m live tests/live` (real services)
- Real data: `python scripts/acquire_targets.py --all` → `scripts/build_observation_index.py` → `scripts/verify_data_bundle.py`
- Analyse a bundle from the CLI: `python scripts/analyze_target.py <target_id>`
- Synthetic fixtures: `python scripts/make_synthetic_fixtures.py`
- Meta check: `python scripts/meta_smoke_test.py` (needs `META_API_KEY` or `MODEL_API_KEY`)
- Release: commit, then `python scripts/make_release.py`

## Architecture (see docs/ARCHITECTURE.md)
- Acquisition (`archive/acquire.py`, network) writes bundles; analysis (`analysis.py`, offline) reads only verified bundles.
- `science/` is deterministic: no network, no model calls. Every method has a version ID recorded in results.
- `ai/`: 12 read-only tools, GUARD-3, copilot loop, local fallback. The model never measures.
- `server/app.py` (Starlette) + `web/` (ES modules, no build, strict CSP, no external requests).

## Rules
- SPHEREx QR3 by default (doi:10.26131/IRSA662), QR2 fallback (10.26131/IRSA652). Never QR1.
- Use only documented IRSA interfaces; never invent endpoints.
- Flux comparisons only for wavelength-matched pairs (WLMATCH-2); log every rejection with a reason.
- Never fill missing values. Never call a candidate a discovery. z is not a probability.
- Synthetic data: `fixtures/synthetic/`, `SYNTHETIC = T`, origin `synthetic`, SYN-* names. Never in `data/bundles/`.
- Keys only from the environment; never in code, logs, records or the browser.
- A gate passes only when its acceptance checks were executed and recorded (docs/TEST_REPORT.md).
