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
- Static preview: `python scripts/build_static.py` (`--web-only` to re-copy the interface) → `dist/preview/`
- Docs generated from code: `python scripts/feature_catalogue.py` (0.5) · `python scripts/phase6_catalogue.py` (0.6) ·
  `python scripts/gen_discovery_methods.py` · `python scripts/gen_research_methods.py` · `python scripts/measure_performance.py`
- Release: commit, rebuild the preview, then `python scripts/make_release.py` (never overwrites an earlier version)

## Architecture (see docs/ARCHITECTURE.md)
- Acquisition (`archive/acquire.py`, network) writes bundles; analysis (`analysis.py`, offline) reads only verified bundles.
- `science/` is deterministic: no network, no model calls. Every method has a version ID recorded in results.
- `ai/`: 16 read-only tools, GUARD-3, copilot loop, local fallback. The model never measures.
- v0.5 readers of a finished record (no network, no model, no probabilities): `capabilities.py` CAPREG-1, `discovery.py` DISC-1,
  `hypotheses.py` HYPO-1, `uncertainty.py` UNC-1, `view.registration_diagnostics` REGDIAG-1, `package.py` PKG-1.
- v0.6 research OS (no probabilities, no scores): `session.py` SESSION-1 (validated, hashed sessions; `canon.py` SKY-CANON-1,
  `schema.py` SCHEMA-1, both ported to JS), `capabilities.py` CAPREG-2 (ACTIONS), `planner.py` PLAN-1, `compat.py` COMPAT-1/SEQ-1,
  `quality.py` DQ-1, `ledger.py` LEDGER-1, `radar.py` RADAR-1, `experiments.py` EXP-1, `missions.py` MISSION-1,
  `workflows.py` WF-1, `connectors.py` ACQ-2; routes in `server/research.py`. Browser: executor, notebook, figure studio, KG.
- `server/app.py` (Starlette) + `web/` (ES modules, no build, strict CSP, no external requests).

## Rules
- SPHEREx QR3 by default (doi:10.26131/IRSA662), QR2 fallback (10.26131/IRSA652). Never QR1.
- Use only documented IRSA interfaces; never invent endpoints.
- Flux comparisons only for wavelength-matched pairs (WLMATCH-2); log every rejection with a reason.
- Never fill missing values. Never call a candidate a discovery. z is not a probability; hypothesis statuses are rules, not likelihoods.
- Browser ports of Python logic (hash, pair comparison, registration, overall rule, intent routing, canon, schema, session,
  planner, missions, workflows) must keep their parity tests.
- Plans, workflows, radar items and missions execute only registered ACTIONS; nothing expensive runs without confirmation.
- Synthetic data: `fixtures/synthetic/`, `SYNTHETIC = T`, origin `synthetic`, SYN-* names. Never in `data/bundles/`.
- Keys only from the environment; never in code, logs, records or the browser.
- A gate passes only when its acceptance checks were executed and recorded (docs/TEST_REPORT.md).
