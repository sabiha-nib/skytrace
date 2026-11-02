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
  `python scripts/phase7_catalogue.py` (0.7) · `python scripts/phase8_catalogue.py` (0.8) · `python scripts/phase9_catalogue.py` (0.9) · `python scripts/gen_intelligence_methods.py` · `python scripts/gen_discovery_methods.py` · `python scripts/gen_research_methods.py` ·
  `python scripts/gen_frontier_methods.py` · `python scripts/gen_epistemic_methods.py` · `python scripts/measure_performance.py`
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
- v0.7 frontier (no probabilities, no scores, no model calls): `counterfactual.py` CF-1 (isolated scenarios, exact re-assessment),
  `synthobs.py` SYNOBS-1/OBSDES-1 (data/synthlab, fixed stamp), `adversarial.py` ASL-1, `infogain.py` INFO-1, `repro.py` REPRO-1,
  `review.py` REVIEW-1, `twin.py` TWIN-1, `possibility.py` SPE-1/HORIZON-1, CAPREG-3 permissions; routes in `server/frontier.py`;
  session-dependent rules in `web/js/frontiercore.js` (parity-tested).
- v0.8 epistemic layer (readers; no probabilities, no scores, no model calls): `epistemic.py` EPI-1 (graph, statuses S1–S10 from
  origin and method, trace), `methodgenome.py` METHOD-DNA-1, `scicomp.py` SCICOMP-1, `scidebug.py` SCIDEBUG-1, `claims.py`
  KBOUND-1/CLAIMX-1, `negspace.py` NEG-1, `blindspot.py` BLIND-1, `uflow.py` UFLOW-1, `lineage.py` LINEAGE-1, `modelarena.py`
  MODELS-1, `futurelab.py` FUTURE-1, `decide.py` NEXTX-1/QFORGE-1, `integrity.py` INTEG-1, `reviewx.py` REVIEWX-1, `reprox.py`
  REPROX-1, `simcheck.py` SIMCHECK-1; session hash chain VAULT-1; routes in `server/epistemic.py` (one report per record, cached
  by hash); browser rules in `web/js/epistemiccore.js` (parity-tested); protocols, blind analysis and arguments in the browser.
- v0.9 intelligence layer (readers; no probabilities, no scores, no model calls): `entities.py` SCI-ENTITY-1, `memory.py` MEMORY-1,
  `dgenome.py` DGENOME-1, `unknownmap.py` UNKNOWN-1, `adversary.py` ADV-1, `gate.py` GATE-1/DEBT-1, `oracle.py` ORACLE-1/EVNEG-1,
  `causal.py` CAUSAL-1, `mdnet.py` MDNET-1, `repronet.py` REPRONET-1, `whatif.py` WHATIF-1, `fingerprint.py`, `instcheck.py`,
  `budget.py`, `autonomy.py` CYCLE-1 (levels in `capabilities.AUTONOMY_LEVELS`); routes in `server/intelligence.py` (report per
  record, corpus over all held investigations); browser rules in `web/js/intelcore.js` (parity-tested); UI `intelui.js`, `intelui2.js`.
- `server/app.py` (Starlette) + `web/` (ES modules, no build, strict CSP, no external requests).

## Rules
- SPHEREx QR3 by default (doi:10.26131/IRSA662), QR2 fallback (10.26131/IRSA652). Never QR1.
- Use only documented IRSA interfaces; never invent endpoints.
- Flux comparisons only for wavelength-matched pairs (WLMATCH-2); log every rejection with a reason.
- Never fill missing values. Never call a candidate a discovery. z is not a probability; hypothesis statuses are rules, not likelihoods.
- Browser ports of Python logic (hash, pair comparison, registration, overall rule, intent routing, canon, schema, session,
  planner, missions, workflows) must keep their parity tests.
- Plans, workflows, radar items and missions execute only registered ACTIONS; nothing expensive runs without confirmation.
- Synthetic data: `fixtures/synthetic/` (fixtures) or `data/synthlab/` (Synthetic Observatory), `SYNTHETIC = T`, origin `synthetic`,
  SYN-* names. Never in `data/bundles/`. Agreement on generated data never validates real-data performance.
- A counterfactual never modifies its baseline; a challenge needs a rule; import is not reproduction; no 3-D from 2-D sky positions.
- Keys only from the environment; never in code, logs, records or the browser.
- Statuses come from origin and method, never wording; a compilation is not proof; the debugger never reconstructs unrecorded
  values; boundary regions are not confidence levels; failed work is never erased; no completeness percentages; tests are not
  scientific validity; the firewall advises, never blocks or rewrites; a hash chain is tamper-evident, not a signature; a lock is
  not preregistration; FutureLab is hypothetical.
- Memory never promotes an explanation; genome and network matches are structural, never physical similarity; what-ifs and oracle
  plans are hypothetical; C5 (experimentally supported) is never met on archival data; every challenge and edge names its rule;
  autonomy levels never grant network or write; repeating a calculation is not validity.
- A gate passes only when its acceptance checks were executed and recorded (docs/TEST_REPORT.md).
