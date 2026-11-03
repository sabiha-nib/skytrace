# Architecture

```
            ┌──────────────── network (only here) ────────────────┐
            │ IRSA SIA2/TAP/cutouts   SIMBAD TAP   Gaia DR3 TAP     │
            └───────────────┬─────────────────────────────────────┘
                            │ archive/net.py: timeouts, retries, size cap, atomic cache, OFFLINE=1
scripts/acquire_targets.py ─┤ archive/acquire.py (selection SEL-1, resume, inspection)
                            ▼
                 data/bundles/<target>/      fixtures/synthetic/<target>/
                 manifest.json (sha256 + provenance per file), target.json, references.json,
                 discovery.json (every image found, included or excluded with reason), inspection.json, images/*.fits
                            │  bundle.verify(): checksums, completeness, kind markers
                            ▼
   analysis.run(bundle, params) ── science/ (deterministic, no network, no model)
        coords · ephemeris (EPHEM-AA-LP-1) · wavelength (WLMATCH-2) · flags (FLAGPOL-1) · centroid (CENTROID-G2D-1, NBMASK-1, TGT-1)
        photometry (APPHOT-1) · astrometry (REFSEL-1/2, PLATE-LOO-1, LINFIT-EPOCH-1, LINFIT-LOO-1) · variability (PAIRDIFF-1/2, CALCHECK-1) · assess (ASSESS-2)
        + stability.py (STAB-1) · provenance_check.py (PROVCHECK-1) · synthetic.py (generator)
                            ▼
   report.Investigation: every step logged (ok / rejected / failed / skipped / info) with provenance; content hash
                            ▼
   v0.5 readers of the record (deterministic, no network, no model):
        capabilities.py (CAPREG-1) · discovery.py (DISC-1) · hypotheses.py (HYPO-1) · uncertainty.py (UNC-1)
        view.registration_diagnostics (REGDIAG-1) · package.py (PKG-1)
                            ▼
   v0.6 research OS readers (deterministic, no network, no model, no scores):
        compat.py (COMPAT-1, SEQ-1) · quality.py (DQ-1) · ledger.py (LEDGER-1) · radar.py (RADAR-1)
        planner.py (PLAN-1) · experiments.py (EXP-1: re-runs analysis.run) · missions.py · workflows.py · connectors.py (ACQ-2)
        session.py (SESSION-1) over canon.py (SKY-CANON-1) + schema.py (SCHEMA-1)      ── all served by server/research.py
                            ▼
   view.InvestigationView + evidence_graph  ◄── ai/tools.py (16 read-only tools) ◄── ai/copilot.py ──► Meta Model API
                            │                                ai/guard.py (GUARD-3)     ai/local.py (fallback)
                            ▼
   server/app.py (Starlette): JSON API + static web/        ──►  browser (web/js: no build, no CDN, strict CSP)
                            │
   scripts/build_static.py: records the server's responses ──►  dist/preview/ (static backend web/js/static/, same interface)
```

## Capability registry (CAPREG-1)

`src/skytrace/capabilities.py` lists every capability with its methods, inputs, bounded parameters (the same bounds the
server enforces: `analysis.PARAM_BOUNDS`), outputs, limitations, tests and where it executes (`local` = wherever the
record is present, `server` = needs the running server, `network` = needs external services). `registry(availability)`
adds whether each is available here. It is served at `GET /api/capabilities`, given to the copilot as the
`list_capabilities` tool, used by the Discovery Engine to decide which next steps can run, and packaged with every
reproducibility package. The static preview publishes its own view: server-only capabilities unavailable, browser ports
named, precomputed results said to be precomputed. Generated table: [DISCOVERY_METHODS.md](DISCOVERY_METHODS.md).

## Phase 5 additions (v0.5)

| Piece | Server | Interface | Static preview |
|---|---|---|---|
| Discovery Engine (DISC-1, stages A–G) | `GET /api/investigations/{id}/discovery` | `web/js/discovery.js` | `data/t/<target>/run/<id>/discovery.json` |
| Hypothesis Arena (HYPO-1) | inside the discovery report | `web/js/arena.js`, overall rule `web/js/rules.js` (parity-tested) | same file |
| Uncertainty Explorer (UNC-1) | inside the discovery report | `web/js/uncertainty.js` (Lab tab) | same file |
| Registration diagnostics (REGDIAG-1) | in the pair comparison | `web/js/timemachine.js` | browser port `web/js/static/compare.js` (parity-tested) |
| Evidence graph: competing explanations | `view.evidence_graph` | `web/js/graph.js` | `graph.json` |
| Reproducibility package (PKG-1) | `GET /api/investigations/{id}/package.zip` | Report Studio (`web/js/records.js`) | `package.json`: the server-built zip as base64 with its SHA-256, checked in the browser before download (static hosts may not serve .zip) |
| Vault: rename, retag, notes, context, duplicate | `PATCH /api/records/{rid}`, `POST /api/records/{rid}/clone` | `web/js/records.js` | browser storage (`web/js/static/backend.js`) |
| Investigation context (question, user hypotheses) | stored with a record (`context`, ≤ 50 kB) | `state.context`, sanitised on reopen (`state.sanitizeContext`) | browser storage |
| Command palette, glossary, shortcuts, levels, loop bar | — | `web/js/palette.js`, `web/js/main.js`, CSS `body[data-level]` | same |
| Figure export (SVG) | — | `web/js/figures.js` | same |

The levels (Explore / Investigate / Research) are CSS views over the same state: nothing is computed differently.
User hypotheses are interpretations: they can cite recorded tests by id, and their overall line uses the published
rule; they never enter the evidence matrix, the graph or the record's content hash.

## Phase 6 additions (v0.6): the research operating system

```
 browser                                                         server (server/research.py)
 ┌────────────────────────────────────────────────────────┐     ┌────────────────────────────────────────────┐
 │ session.js ── sessioncore.js (validate, verify, hash)   │ PUT │ /api/sessions, /api/sessions/{sid}         │
 │   state.session: question, runs, hypotheses, notebook,  │────►│ session.validate + verify; data/sessions/  │
 │   plans, experiments, missions, workflows, history      │     │ import refuses hash mismatch, never        │
 │        ▲                                                │     │ overwrites an id; unreadable files kept    │
 │        │ S.update(kind, summary, fn) → logEvent         │     ├────────────────────────────────────────────┤
 │ executor.js ── runs one registered ACTION ───────────────┼────►│ /api/plan (server forces its own facts)    │
 │   ▲ plannerui · experimentsui (workflows) · radarui ·   │     │ /api/experiments (EXP-1, bounded)          │
 │   │ commandcenter (missions)                            │     │ /api/investigations/{id}/research          │
 │ qualityui · ledgerui · notebook · figurestudio · kg ·   │◄────│   COMPAT-1 + DQ-1 + LEDGER-1 + RADAR-1,    │
 │ timemachine (sequences) · copilot (16 tools, labels)    │     │   cached by record content hash            │
 └────────────────────────────────────────────────────────┘     │ /api/specs (planner table, missions,       │
   static preview: web/js/static/backend.js serves recorded       │   templates, schemas, citations)           │
   research.json / experiments.json / specs.json; sessions in     │ /api/connectors (+ preview: nothing sent)  │
   localStorage; plans by the browser planner; refusals named     │ /api/workflows/validate                    │
                                                                  └────────────────────────────────────────────┘
```

| Piece | Server | Interface | Static preview |
|---|---|---|---|
| Research session (SESSION-1) | `GET/POST /api/sessions`, `GET/PUT/DELETE /api/sessions/{sid}`, `POST /api/sessions/import`, `POST /api/sessions/from-record/{rid}` | `session.js`, `sessioncore.js`, `sessionsui.js` | browser storage `skytrace.preview.sessions.v1`, same validation and hash in JS |
| Capability registry + ACTIONS (CAPREG-2) | `GET /api/capabilities`, `/api/specs` | `executor.js` | `specs.json` |
| Planner (PLAN-1) | `POST /api/plan` | `plannerui.js`, browser port `planner.js` | browser planner over the same rule table |
| Compatibility, sequences, coverage (COMPAT-1, SEQ-1) | in `/research` | `qualityui.js`, `timemachine.js` | `research.json` |
| Data quality (DQ-1) | in `/research` | `qualityui.js` | `research.json` |
| Evidence ledger (LEDGER-1) | in `/research` | `ledgerui.js` | `research.json` |
| Discovery Radar (RADAR-1) | in `/research` | `radarui.js` | `research.json` |
| Experiments (EXP-1) | `POST /api/experiments` | `experimentsui.js` | `experiments.json` (standard set recorded at build time; custom parameters refused) |
| Workflows (WF-1) | `POST /api/workflows/validate` | `experimentsui.js`, port `workflows.js` | browser validation |
| Missions (MISSION-1) | in `/api/specs` | `commandcenter.js`, port `missions.js` | same |
| Connectors (ACQ-2) | `GET /api/connectors`, `POST /api/connectors/{cid}/preview` | `qualityui.js` | registry recorded; previews refused (need the server's builders) |
| Notebook (NOTE-1), figures (FIG-2), knowledge graph (KG-1) | — | `notebook.js`, `figurestudio.js`, `kg.js` | same |
| Copilot 2.0 | 16 tools (`ai/tools.py`), 15 local intents (`ai/local.py`) | `copilot.js` | `ask.json` per intent with the recorded question |

Workspaces are grouped Observe (Command Center, Explorer, Time Machine) · Investigate (Planner, Lab, Experiment Studio) ·
Verify (Data Quality, Evidence Ledger, Discovery Radar) · Record (Notebook, Vault/Report Studio). Levels gate visibility through
`data-min-level`; opening a deeper workspace raises the level and says so. Render tokens (`util.renderToken`) discard stale
asynchronous renders so a fast series of events never duplicates a panel.

## Phase 7 additions (v0.7): the frontier laboratory

```
 browser                                                         server (server/frontier.py)
 ┌────────────────────────────────────────────────────────┐     ┌──────────────────────────────────────────────┐
 │ state.getFrontier(iid, stability) ───────────────────────┼────►│ GET/POST /api/investigations/{iid}/frontier  │
 │   frontiercore.js (session rules, parity-tested):       │◄────│   SPE-1 layers + HORIZON-1 cards, ASL-1,     │
 │   overlayHorizon · overlayChallenges · overlayReview ·  │     │   INFO-1, REVIEW-1, REPRO-1 (no replay),     │
 │   twinCompare · investigationTwin · coordinates         │     │   TWIN-1 analysis + target twins;            │
 │ horizonui · adversarialui · reviewui · knowledgeui ·    │     │   cached by content hash (+ stability)       │
 │ atlasui                                                 │     ├──────────────────────────────────────────────┤
 │ counterfactualui ─────────────────────────────────────────┼────►│ POST /api/counterfactuals (CF-1; baseline    │
 │ synthobsui ───────────────────────────────────────────────┼────►│   recomputed + hash-checked; scenario twin)  │
 │ reviewui (re-execute) ────────────────────────────────────┼────►│ POST /api/synthetic (SYNOBS-1, data/synthlab)│
 │ autopilotui ── executor.js (registered ACTIONS only,    │     │ POST /api/observation-design (OBSDES-1)      │
 │   permission class ≤ level, after authorization)        │     │ POST /api/investigations/{iid}/reproduce     │
 └────────────────────────────────────────────────────────┘     └──────────────────────────────────────────────┘
   static preview: frontier.json per run, reproduce.json + counterfactuals.json (default run), synthetic.json and design.json,
   looked up by canonical keys (SKY-CANON-1); anything not recorded is refused with a reason
```

| Piece | Module | Server | Interface | Static preview |
|---|---|---|---|---|
| Counterfactual Universe Lab (CF-1) | `counterfactual.py`; `assess.thresholds_with` | `POST /api/counterfactuals` | `counterfactualui.js` | nine prepared scenarios on the default run |
| Synthetic Observatory (SYNOBS-1) | `synthobs.py` (uses `synthetic.py` with a fixed stamp) | `POST /api/synthetic` | `synthobsui.js` | six templates |
| Observation Design Lab (OBSDES-1) | `synthobs.design` | `POST /api/observation-design` | `synthobsui.js` | one comparison |
| Adversarial Science Lab (ASL-1) | `adversarial.py` | in `/frontier` | `adversarialui.js` + `overlayChallenges` | `frontier.json` |
| Information analysis (INFO-1) | `infogain.py` | in `/frontier` | `adversarialui.js` (ranking tab) | `frontier.json` |
| Causality workbench | — (data flow, HYPO-1 explanations, session `causal`) | — | `adversarialui.js` (causal tab) | same |
| Reproducibility challenge (REPRO-1) | `repro.py` (uses PROVCHECK-1) | in `/frontier` (no replay); `POST …/reproduce` (replay) | `reviewui.js` | default run's replay recorded |
| Review Room (REVIEW-1) | `review.py` | in `/frontier` | `reviewui.js` + `overlayReview` | `frontier.json` |
| Discovery story | — (recorded outcomes only) | — | `reviewui.js` | same |
| Astro-twins (TWIN-1) | `twin.py` | in `/frontier`; scenario twin in `/counterfactuals` | `knowledgeui.js` + `investigationTwin`, `twinCompare` | same |
| Possibility engine, horizon (SPE-1, HORIZON-1) | `possibility.py` | in `/frontier` | `horizonui.js` + `overlayHorizon` | `frontier.json` |
| Autopilot (CAPREG-3 levels) | `capabilities.py` `PERMISSION`, `AUTOPILOT_LEVELS` | `/api/specs` | `autopilotui.js`, `executor.js` | browser planner + executor |
| Cosmic Atlas | — (bundle `target.json`, reference stars) | target detail includes `stars` | `atlasui.js` + `angularSeparationDeg`, `icrsToGalactic` | same |
| Knowledge Atlas | — | — | `knowledgeui.js` (exact search) | same |

Navigation is grouped in eight research modes: Observatory (Command Center, Sky Explorer, Time Machine, Cosmic Atlas) · Discover
(Discovery Horizon, Discovery Engine, Discovery Radar) · Investigate (Discovery Lab, Hypothesis Arena, Evidence Ledger) · Experiment
(Counterfactual Lab, Experiment Studio, Synthetic Observatory) · Understand (Data Quality, Adversarial Lab) · Orchestrate
(Investigation Planner, Research Autopilot) · Knowledge (Research Notebook, Knowledge Atlas, Vault & Reports) · Publish (Review & Story). The session gained optional `scenarios`, `synthetic`, `causal` and `autopilot`
fields. Sessions written by 0.6 still validate. Synthetic Observatory bundles live in `data/synthlab/` (or `SKYTRACE_SYNTHLAB_DIR`),
never in `data/bundles/` or `fixtures/`. Methods: [FRONTIER_METHODS.md](FRONTIER_METHODS.md). (Phase 8 regrouped this navigation;
see below.)

## Phase 8 additions (v0.8): the epistemic layer

Every Phase 8 engine is a deterministic reader of a finished record. None of them changes a record, calls a model or uses a
probability. They share one graph (EPI-1), built once per record.

```
 browser                                                          server (server/epistemic.py)
 ┌─────────────────────────────────────────────────────────┐     ┌───────────────────────────────────────────────────┐
 │ state.getEpistemic() ─────────────────────────────────────┼────►│ GET /api/investigations/{iid}/epistemic            │
 │   epistemiccore.js (parity-tested): trace ·             │◄────│   EPI-1 graph → METHOD-DNA-1 genome, SCICOMP-1,    │
 │   assertedWords · compareValues · diff (differential    │     │   KBOUND-1, CLAIMX-1, NEG-1, BLIND-1 base,         │
 │   debugging) · overlayBlindspots · sigmaPm ·            │     │   UFLOW-1, LINEAGE-1 (claims, fit), SCIDEBUG-1     │
 │   pairPrecision · integrityCheck                        │     │   breakpoints + inspections, MODELS-1, FUTURE-1,   │
 │ reasoningui · compilerui · claimsui · debuggerui ·      │     │   NEXTX-1, QFORGE-1, INTEG-1 facts + report check, │
 │ modelsui · uflowui · futureui · decideui · negativeui · │     │   REVIEWX-1; cached by content hash                │
 │ integrityui · protocolui · argueui · epitabs            │     ├───────────────────────────────────────────────────┤
 │ debuggerui (reproduce) ───────────────────────────────────┼────►│ POST …/reproduce-x (REPROX-1, re-execution)       │
 │ reasoningui (any comparison) ─────────────────────────────┼────►│ GET  …/lineage?result= (LINEAGE-1)                │
 │ epitabs (simulation audit) ───────────────────────────────┼────►│ POST /api/simulation-audit (SIMCHECK-1)           │
 │ sessioncore.js: VAULT-1 chain; protocol, blind, args    │     │ POST /api/integrity (INTEG-1 on any text)         │
 └─────────────────────────────────────────────────────────┘     └───────────────────────────────────────────────────┘
   static preview: epistemic.json per recorded run, reproducex.json (default run), simaudit.json; lineage of results
   other than claims and the motion fit, and audits of edited scenarios, are refused with a reason
```

| Piece | Module | Server | Interface | Static preview |
|---|---|---|---|---|
| Reasoning graph, statuses, trace (EPI-1) | `epistemic.py` | in `/epistemic` | `reasoningui.js` + `trace` | `epistemic.json` |
| Method genome (METHOD-DNA-1) | `methodgenome.py` | in `/epistemic`; specs | `compilerui.js` (genome tab) | same |
| Scientific compiler (SCICOMP-1) | `scicomp.py` | in `/epistemic` | `compilerui.js` | same |
| Scientific debugger (SCIDEBUG-1) | `scidebug.py` | in `/epistemic` (breakpoints, inspections) | `debuggerui.js` + `diff` | inspections and differential debugging between recorded runs |
| Knowledge boundary (KBOUND-1), claim stress tests (CLAIMX-1) | `claims.py` | in `/epistemic` | `claimsui.js` | same; the reproducibility mode uses a reproduction you ran |
| Negative knowledge (NEG-1) | `negspace.py` | in `/epistemic` | `negativeui.js` (plus your session entries) | same |
| Blindspots (BLIND-1) | `blindspot.py` | base in `/epistemic` | `claimsui.js` + `overlayBlindspots` | same |
| Uncertainty flow (UFLOW-1) | `uflow.py` | in `/epistemic` | `uflowui.js` | same |
| Data lineage (LINEAGE-1) | `lineage.py` | in `/epistemic` (claims, fit); `GET …/lineage` | `reasoningui.js` (Lineage-X tab) | claims and fit |
| Model arena (MODELS-1) | `modelarena.py` | in `/epistemic` | `modelsui.js` | same |
| FutureLab (FUTURE-1) | `futurelab.py` | in `/epistemic` | `futureui.js` + `sigmaPm`, `pairPrecision` | same; calculator interactive |
| Next steps, questions (NEXTX-1, QFORGE-1) | `decide.py` | in `/epistemic` | `decideui.js` | same |
| Integrity firewall (INTEG-1) | `integrity.py` | facts and report check in `/epistemic`; `POST /api/integrity` | `integrityui.js` + `integrityCheck` | interactive in the browser |
| Review board (REVIEWX-1) | `reviewx.py` | in `/epistemic` | `epitabs.js` (Review Room tab) | same; comments in the session |
| Independent reproduction (REPROX-1) | `reprox.py` | `POST …/reproduce-x` | `debuggerui.js` | default run recorded |
| Simulation audit (SIMCHECK-1) | `simcheck.py` (uses SYNOBS-1) | `POST /api/simulation-audit` | `epitabs.js` (Synthetic Observatory tab) | one audit recorded |
| Evidence vault (VAULT-1) | `session.py`, `sessioncore.js` | — | `epitabs.js` (Knowledge Atlas tab) | interactive |
| Protocols, blind analysis (PROTOCOL-1, BLINDLAB-1) | `protocolui.js`, `main.js` | — | `protocolui.js` | interactive |
| Reasoning Lab (ARG-1) | `argueui.js` | — | `argueui.js` | interactive |

Navigation now follows the eight modes of the Phase 8 brief:

| Mode | Workspaces |
|---|---|
| Observatory | Command Center, Sky Explorer, Time Machine, Cosmic Atlas |
| Evidence | Evidence Ledger, Reasoning Graph, Data Quality, Negative Space |
| Analyze | Discovery Lab, Discovery Engine, Hypothesis Arena, Model Arena, Uncertainty Flow, Scientific Debugger |
| Challenge | Scientific Compiler, Claims, Adversarial Lab, Review Room |
| Experiment | Counterfactual Lab, Experiment Studio, Synthetic Observatory, FutureLab |
| Plan | Questions & Next Steps, Discovery Horizon, Discovery Radar, Investigation Planner, Autopilot, Protocol & Blind Analysis |
| Knowledge | Research Notebook, Knowledge Atlas, Reasoning Lab |
| Publish | Integrity Firewall, Vault & Reports |

The session gained optional `negative`, `reviews`, `protocol`, `blind`, `arguments` and `debug` fields, and the reference kinds
`node`, `argument`, `negative`, `review_item` and `check`. History entries carry a hash-chain link `h`. Sessions written by 0.7
still validate and are chained on their next save. While a blind analysis is active, the shell does three things:
- It covers every workspace except Protocol, Sky Explorer, Data Quality and the Notebook; the covered renderers are not called.
- It pauses the copilot.
- The evidence ruler stops emphasising significant pairs.

Methods: [EPISTEMIC_METHODS.md](EPISTEMIC_METHODS.md).

## Phase 9 additions (v0.9): the scientific intelligence layer

Phase 9 engines are deterministic readers too. They read the record, the epistemic report (EPI-1 and its readers), DISC-1 and
the frontier report, built once per record; none of them changes a record, calls a model, uses a probability or produces a
score. Every object they expose shares one envelope (SCI-ENTITY-1: stable id, version, provenance, creation time, epistemic
status, validation), so memory, genomes, the unknown map, the ledger and the gate refer to the same objects.

```
 browser (Scientific Intelligence workspace)                     server (server/intelligence.py)
 ┌──────────────────────────────────────────────────────────┐   ┌──────────────────────────────────────────────────────┐
 │ state.getIntelligence() ─────────────────────────────────────┼──►│ GET /api/investigations/{iid}/intelligence           │
 │                                                          │◄──│   SCI-ENTITY-1, DGENOME-1, ADV-1, GATE-1 + DEBT-1,     │
 │ intelcore.js (parity-tested): recall · failureWarnings · │   │   CAUSAL-1, ORACLE-1 context + examples, EVNEG-1,     │
 │   overlayLedger · overlayGate · oracleEvaluate ·         │   │   INSTCHECK-1, FINGERPRINT-1, BUDGET-1, WHATIF-1,     │
 │   motionRefit · hypotheticalVisit · reproCompare ·       │   │   REPRONET-1 manifest (cached by content hash);       │
 │   sessionEntities · causalWarnings                       │   │   + UNKNOWN-1 (reads sibling runs) + CYCLE-1          │
 │ state.getCorpus() ───────────────────────────────────────────┼──►│ GET /api/intelligence/corpus: MEMORY-1, MDNET-1,     │
 │                                                          │   │   genome comparisons (cached by the set of hashes)    │
 │ intelui.js · intelui2.js · intelbits.js (12 panels)      │   │ POST /api/oracle · /api/whatif/visit ·                │
 │ executor.reproduce_independent ──────────────────────────────┼──►│   /api/reproduction/compare; GET …/reproduction-manifest│
 └──────────────────────────────────────────────────────────┘   └──────────────────────────────────────────────────────┘
   static preview: intelligence.json per recorded run and corpus.json; the browser core answers edited plans, hypothetical
   visits, reproduction comparison and session overlays with the same rules
```

| Layer | Panels | Engines |
|---|---|---|
| 1 Observation | Command Center, Discovery Genome (with sensitivity fingerprint and uncertainty budget) | DGENOME-1, FINGERPRINT-1, BUDGET-1 |
| 2 Discovery | Unknown Universe, Multi-Discovery Network | UNKNOWN-1, MDNET-1 |
| 3 Reasoning | Scientific Adversary (with instrumental reality check), Causality Lab | ADV-1, INSTCHECK-1, CAUSAL-1 |
| 4 Experimental | What-if Lab, Observation Oracle (with evidence negotiation), Research Cycle | WHATIF-1, ORACLE-1, EVNEG-1, CYCLE-1 |
| 5 Knowledge | Research Memory, Reproduction Network | MEMORY-1, REPRONET-1 |
| 6 Integrity | Integrity Gate (research debt, time capsule, handoff, knowledge export) | GATE-1, DEBT-1, CAPSULE-1 |

Every panel carries the data-kind legend: real data, synthetic data, simulated output, hypothetical scenario, unverified
interpretation, verified computation. The workspace sits after Command Center in the navigation (research level).

Bounded autonomy: CYCLE-1 proposes registered actions by rules A1–A6. `capabilities.AUTONOMY_LEVELS` binds execution: advisory
executes nothing; supervised runs each approved step; restricted automation runs `RESTRICTED_WORKFLOW` after one authorization.
No level allows the network or write permission classes. Each step is logged in the session (`cycles`) with level, approval and
times. The session gained optional `challenges`, `completion`, `capsules` and `cycles` fields and the reference kinds `entity`,
`memory` and `capsule`; earlier sessions still validate.

Methods: [INTELLIGENCE_METHODS.md](INTELLIGENCE_METHODS.md). Audit and decisions: [PHASE9_AUDIT.md](PHASE9_AUDIT.md).

## Phase 10 additions (v0.10): six languages and the universal frontier

**Internationalisation** (I18N-1, full description in [I18N.md](I18N.md)). The English text in the code is the message id. A
generated catalogue (`web/i18n/catalog.json`, `scripts/i18n_extract.py`) holds every interface message; language files hold the
translations by key. In the browser, `i18n.js` translates the rendered document and everything rendered later (a
`MutationObserver`), formats numbers and dates per language, and gives keyed messages with plurals (`t(key, params)`). On the
server, `i18n.py` translates marked report wording (`_t("…")`). Engine narrative text, numbers, units, identifiers and JSON exports
are never translated. The language persists in the browser, the URL (`?lang=`) and the session's `preferences`.

```
 web/i18n/catalog.json  ◄── scripts/i18n_extract.py  (index.html, web/js/**, _t("…") in src/, engine vocabularies)
 web/i18n/{bn,hi,es,fr,de}.json  ◄── scripts/i18n_merge.py (TSV batches; refuses placeholder mismatches)
 web/i18n/terms.json    ◄── scripts/i18n_terms.py   (TERM-1, 48 terms × 6 languages)
 web/i18n/quality.json  ◄── scripts/i18n_quality.py (I18N-Q1 counts)
        │                                   │
        ▼                                   ▼
 browser: i18n.js (DOM translator, Intl)    server: i18n.py → report.render_markdown(inv, lang) → report.md?lang=xx
          xsearch.js (XSEARCH-1)                    xsearch.py (parity-tested)
```

**Universal report.** Phase 10 engines are deterministic readers of a finished record, like those of Phases 5–9: no network, no
model, no probability, no score. `server/universal.py` builds one report per record (cached by content hash and the hashes of the
target's other runs) from the record, HYPO-1, NEG-1, SCICOMP-1 and RADAR-1:

| Engine | Module | Shown in |
|---|---|---|
| SIGNAL-1 signal workbench | `sigintel.py` | Signal Intelligence (Analyze) |
| WORLD-1, CONV-1, LEAD-1, MODAL-1, TIMES-1 | `universal.py` | World Model (Evidence) |
| NEGX-1, KCOMP-1, OPP-2 + EXTSRC-1, DIRECT-1, AGENTS-1, EXPMKT-1 | `universal.py` | Negative Space, Scientific Compiler, Discovery Radar, Research Autopilot, Review & Story, Experiments |
| EXPLAIN-1 | `universal.py` (keyed messages `explain.*`) | Multilingual Research (Knowledge) |
| HANDOFF-1 | `handoff.py`, `web/js/handoff.js` (parity-tested) | Open Science Gateway (Publish) |
| FLIGHT-1, OSG-1 | browser (`universalui.js`) over the session and the record | Open Science Gateway |

API: `GET /api/investigations/{iid}/universal`; `GET /api/investigations/{iid}/report.md?lang=xx`. The static preview stores the
universal report inside each run's `intelligence.json` (key `universal`), which keeps the preview under the artifact's file
limit. The session gained optional `preferences`, `monitors`, `director`, `debates` and `handoffs`; earlier sessions still
validate. Methods: [UNIVERSAL_METHODS.md](UNIVERSAL_METHODS.md). Audit and decisions: [PHASE10_AUDIT.md](PHASE10_AUDIT.md).

## Layers and their rules

| Layer | Code | May | May not |
|---|---|---|---|
| Data | `archive/`, `bundle.py`, `fitsio.py`, `wcs.py` | fetch (acquisition only), cache, verify, read FITS | modify downloaded files; substitute unrelated data; label cache as live |
| Science | `science/`, `analysis.py` | measure, compare, classify with fixed rules | use the network; call a model; fill missing values |
| Interpretation | `ai/` | read logged evidence through tools, explain, suggest | measure; fetch; run code; read files; reach arbitrary URLs |
| Application | `server/`, `web/` | serve verified bundles, run analyses, mediate the copilot | contact archives; expose the API key |

## Key decisions

- **Bundles as the only analysis input.** Acquisition (network) and analysis (offline) are separate programs. Offline operation is therefore structural, not a mode bolted on: the server never calls an archive.
- **Native FITS/WCS fallback.** astropy could not be installed in the build environment. `fitsio.py` and `wcs.py` implement the subset SPHEREx products use: image and binary-table HDUs, TAN-SIP, and the `-TAB` spectral WCS. astropy is used whenever installed. The two are compared on synthetic files when astropy is present, and on a real cutout by `tests/live`.
- **Starlette, not FastAPI.** FastAPI was not installable here (no package index); Starlette and uvicorn were. The API is small enough that FastAPI's extras are not needed.
- **No frontend build.** Plain ES modules and an SVG/canvas implementation keep the interface installable and runnable offline with zero JavaScript dependencies. A strict Content-Security-Policy (`script-src 'self'`, no eval, no inline scripts) is enforced.
- **In-memory investigations, file-based records.** Analysis results are cached in memory by content hash. Saved investigations are JSON files in `data/records/`. That is enough for a single-user instrument; a multi-user deployment would need accounts and a database.
- **Not introduced:** agent frameworks, MCP servers, vector databases, task queues. Nothing in the requirements needed them.

## Request flow for one copilot question

1. `POST /api/investigations/{id}/ask` → `copilot.ask` builds a `ToolSession` over the stored record.
2. With a Meta key and `OFFLINE` unset, the model receives the system rules, a compact context (target, kind, outcome categories) and 16 tool schemas. It calls tools; each call is validated by pydantic and recorded.
3. The final JSON answer goes through `guard.check` against the outputs of the tools actually called. On failure, one repair round runs. A second failure withholds the draft and returns the local assistant's grounded answer instead.
4. Without a key, offline, or on any API error, the local assistant answers through the same tools and the same guard. The response always states which mode produced it.
