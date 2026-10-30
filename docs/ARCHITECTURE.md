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
never in `data/bundles/` or `fixtures/`. Methods: [FRONTIER_METHODS.md](FRONTIER_METHODS.md).

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
