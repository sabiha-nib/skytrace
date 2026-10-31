# Phase 8 audit: the epistemic frontier (v0.8.0)

Phase 8 asked Skytrace to make the structure of its own knowledge inspectable. Every claim should be traceable to its files,
methods and assumptions. Investigations should be compiled and debugged like programs, and claims stress-tested. Failed work
should be preserved, blindspots shown, methods described by their genome, and uncertainty followed through the pipeline. Analysis
choices should be fixable before outcomes are seen, and reports checked before they leave.

Every earlier rule still applied: no manufactured results, no blocked work reported as done, no removed or weakened tests, no
secrets outside the server, no destructive Git operations. Phase 8 added its own rules:

- Statuses come from source and method, never from wording.
- A compilation is not proof.
- The debugger never invents intermediate values.
- Boundary regions are not confidence levels.
- Failed work is never erased.
- Blindspot coverage is not a completeness percentage.
- Test coverage is not scientific validity.
- There is no invented propagation model.
- There is no exact-reproduction claim when the environment differs.
- There are no optimality claims and no arbitrary model scores.
- A checksum is not cryptographic immutability.
- Scientific text is never rewritten silently.
- A saved plan is not preregistration.
- Hypothetical observations are never presented as scheduled.
- A language model is never the authority for a computation.

## 1. Repository audit (before any Phase 8 change)

| Item | State at commit `948cd1c` (v0.7.0 plus its test report) |
|---|---|
| Version | 0.7.0 (`src/skytrace/__init__.py`, `pyproject.toml`) |
| Working tree | clean |
| Unit, integration, robustness and parity tests | 292 passed, 2 skipped (astropy not installed), re-run before the first Phase 8 edit |
| Browser tests | 89 passed (TEST_REPORT v0.7.0) |
| Static preview | https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT, version 6 (0.7.0) |
| Release artifacts | 0.2.0–0.7.0 archives with `.sha256` and `RELEASE_MANIFEST-<ver>.json`. 0.7.0: `57e962d8…` (code, 434 files), preview `fbd0b995…` |
| External services | IRSA, SIMBAD, Gaia, the Meta API, PyPI and npm are refused by the proxy (403). No astropy, no Meta key |
| Data | Two synthetic fixtures (`syn-hpm-1`, `syn-var-1`). No real SPHEREx bundle |

What already existed and was reused rather than rebuilt:
- the record's event log, which every Phase 8 engine reads
- the evidence ledger (LEDGER-1, contradiction rules C1–C4)
- data quality (DQ-1) and compatibility (COMPAT-1)
- hypotheses (HYPO-1) and uncertainty (UNC-1)
- provenance re-check (PROVCHECK-1) and the bundle manifest
- the counterfactual re-assessment (CF-1, used for the threshold stress mode and the compiler's E1 check)
- the stability check, experiments (EXP-1) and the synthetic observatory (SYNOBS-1, used by the simulation audit)
- review roles (REVIEW-1)
- sessions (SESSION-1, SKY-CANON-1, SCHEMA-1, history)
- the capability registry and the static preview's recorded backend

What did not exist:
- a typed graph of scientific objects
- epistemic statuses
- structural compilation
- breakpoints and recomputation
- differential debugging between runs
- a knowledge boundary or claim stress testing
- a negative-knowledge registry or blindspot coverage
- method descriptions with typed I/O and tests
- an uncertainty flow or stage lineage
- model comparison
- future-measurement planning with a validated formula
- decision records, question generation or a report integrity check
- review comments, a graded reproduction verdict or a simulation audit
- a hash-chained history
- protocols, locks, blind analysis or argument maps

## 2. Feature-preservation matrix

The matrix lists every earlier capability family. "Unchanged" means no line of its code changed; "extended" means code was
added without changing existing behaviour. Each family has a verifying test that still runs.

| Capability (phase) | Code | Phase 8 change | Still verified by |
|---|---|---|---|
| Pipeline: selection, references, measurement, pairs, variability, astrometry, assessment (1–3) | `analysis.py`, `science/` | unchanged; records and content hashes identical for the same inputs | `test_measurement`, `test_offline_workflow`, `test_assess*` |
| Acquisition, bundles, provenance re-check (1–4) | `archive/`, `bundle.py`, `provenance_check.py` | unchanged | `test_acquire`, `test_provenance_check` |
| Copilot, 16 tools, GUARD-3, local fallback (2–5) | `ai/` | unchanged in Python; the browser pauses the copilot during a blind analysis | `test_tool_contracts`, `test_report_ai`, `test_h*` (e2e) |
| Discovery, hypotheses, uncertainty, registration, package (5) | `discovery.py`, `hypotheses.py`, `uncertainty.py`, `view.py`, `package.py` | unchanged | `test_discovery` |
| Sessions, canon, schema (6) | `session.py`, `canon.py`, `schema.py`, `sessioncore.js` | extended with optional fields (`negative`, `reviews`, `protocol`, `blind`, `arguments`, `debug`), five reference kinds and the history hash chain. 0.7 sessions stay valid and are chained on their next save | `test_research_session` (incl. migration), `test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid` |
| Planner, compat, quality, ledger, radar, experiments, missions, workflows, connectors (6) | `planner.py` … `connectors.py` | unchanged | `test_research_os` |
| Counterfactual, synthetic observatory, adversarial, information, reproducibility, review, twins, possibility (7) | `counterfactual.py` … `possibility.py`, `server/frontier.py` | unchanged; read by the new engines | `test_frontier`, `test_phase7_frontier_counterfactual_reproduce_synthetic` |
| Investigation report (2) | `report.py` | extended: a new "Outcomes and limitations" section (criteria, sensitivities with units, limitations). Found by the integrity firewall: the report stated no limitations | `test_integrity_firewall_flags_problems_without_rewriting`, API test |
| API specs (6–7) | `server/research.py` | extended with an `epistemic` key | `test_phase8_epistemic_reproduce_integrity` |
| All 21 earlier workspaces (2–7) | `web/js/*` | unchanged renderers. Navigation was regrouped into the eight §27 modes; every workspace keeps its button, its keyboard route and its level | e2e `test_r`, `test_y` and every earlier e2e step, in both modes |
| Evidence ruler (3) | `ruler.js` | while a blind analysis is active it stops emphasising significant pairs | e2e `test_b`, `test_e8` |
| Knowledge Atlas, Synthetic Observatory, Review Room (7) | `knowledgeui.js`, `synthobsui.js`, `reviewui.js` | one new tab each (evidence vault, simulation audit, review board); the existing tabs are unchanged | e2e `test_t7`, `test_t4`, `test_t8`, `test_e9` |
| Static preview (4–7) | `build_static.py`, `static/backend.js` | extended: per-run `epistemic.json`, the default run's reproduction and the simulation audit | `test_static_preview`, e2e static mode |
| Release tooling (4–7) | `make_release.py`, `verify.py` | unchanged; still refuses to overwrite a version | release gate |

No test was removed. Phase 8 changed two existing tests, both by extending lists: the e2e workspace lists in `test_r` and `test_y`
gained the twelve new workspaces, and a comment about the `Alt+8` level was corrected.

## 3. Architecture decisions

* **One graph, built from the record.** EPI-1 builds the reasoning graph from the record's events, the discovery reading, the
  ledger and the manifest. It has fifteen kinds of object, each with a stable identifier. Statuses come from ten rules, S1–S10,
  that read origin and method (a synthetic file is *simulated*; a measurement is *directly measured*; a decided inference is
  *derived*). Procedures (transformations, methods) carry no status. Wording is used in only one place, the negation-aware
  check of a sentence's outcome words (C1 in the compiler, the claim-wording stress mode, I12 in the firewall). Even there it
  can only flag a sentence for review; it never assigns a status. Traces are breadth-first searches over data edges.
* **Every engine is a reader.** The compiler, debugger, boundary, stress tests, negative space, blindspots, uncertainty flow,
  lineage, model arena, FutureLab, decisions, questions, integrity checks, review board and reproduction read the record and the
  graph. None of them changes a record. `server/epistemic.py` builds one report per record, caches it by content hash and serves
  it to every Phase 8 workspace. The static preview records the same report for every recorded run.
* **Recompute or say so.** The debugger offers breakpoints only at stages the record contains. Inspecting a result recomputes it
  from recorded inputs with the method's formula. A value that was not recorded is reported as *not recorded*; it is never
  reconstructed. Differential debugging walks stages in pipeline order and reports the earliest divergence, with a relative
  tolerance of 1e-9 for "numerically equivalent".
* **Rules over impressions, never numbers over regions.** The compiler has ten stages and one stated precedence rule for its seven
  outcomes. Every result states that passing is not proof. The boundary has four regions with rules B1–B4 and no numeric
  confidence. Each of the ten stress modes has a documented rule and returns pass, warning, fail, inconclusive, not tested or
  blocked. Blindspot coverage counts eleven defined checks and gives no percentage.
* **Methods described, not validated by tests.** METHOD-DNA-1 describes thirteen methods: typed inputs and outputs (units),
  assumptions, parameters, formula, dependencies, applicability, limitations, validation data, version chain and the real
  known-answer tests. Health checks that those tests exist and that determinism is covered. Every view says that tests check the
  software against known answers and do not establish scientific validity.
* **Only what the methods propagate.** UFLOW-1 shows the uncertainty categories the methods actually represent: pixel variance,
  centroid, flux, visit mean, pair, reference scatter, the CALCHECK scale and χ²ν inflation. It lists, explicitly, what is not
  propagated (calibration systematics, PSF model error, reference-star variability, parameter sensitivity).
* **Graded reproduction.** REPROX-1 re-executes the recorded analysis and compares every stage. It returns one of five verdicts:
  exact reproduction, numerically equivalent, documented differences, failed or blocked. "Exact" requires an identical
  re-execution *and* a record whose hash recomputes. "Documented differences" needs a recorded cause (software, parameters or
  inputs).
* **Models and futures within the data.** MODELS-1 compares a static and a linear motion model per axis on the same visits, using
  χ², degrees of freedom, AIC, Δχ² and leave-one-out. It reports no p-values and no scores, and first checks that the linear model
  reproduces the pipeline's fit. FUTURE-1 uses the weighted least-squares slope error. It first checks that the formula reproduces
  the recorded σ, and only then shows hypothetical scenarios, each with its assumptions.
* **Advice, not enforcement.** INTEG-1 has twelve checks on the report, your notebook or pasted text. It reports ready, ready with
  warnings or needs attention. It never blocks an export and never changes a character.
* **Append-only, honestly described.** VAULT-1 chains the session history: each entry's link is the SHA-256 of the previous link
  and the entry. Edits are detected and refused on save. Corrections are new entries that point at the old one. The interface
  says that a hash chain is tamper-evident, not a signature.
* **Protocols and blinding in the browser.** A protocol records hypotheses, inputs, exclusions, parameters, expected outcomes and
  robustness tests, and can be locked with a content hash and a time. A lock made after results were visible is labelled so.
  Amendments are append-only and are flagged when results were visible. None of this is called preregistration.
  A blind analysis records a commitment hash of the hidden values. While blind, it covers every workspace that would show
  outcomes (without calling its renderer), pauses the copilot and turns off ruler emphasis. Unblinding requires a locked protocol
  and a typed confirmation.
* **Parity where the browser decides.** Session-dependent rules run in `epistemiccore.js`: traces, the wording check, value
  comparison and the differential debugger, the blindspot overlay, the FutureLab formula and the integrity check. They are tested
  against Python on the same inputs.

## 4. What was built (summary; the full list is the Phase 8 catalogue)

There are twelve new workspaces, arranged in the eight modes of §27 (Observatory · Evidence · Analyze · Challenge · Experiment ·
Plan · Knowledge · Publish):

| Workspace | What it does |
|---|---|
| Reasoning Graph & Lineage-X | The graph and a backward or forward trace from any object, plus the nine-stage lineage of claims and the motion fit |
| Scientific Compiler & Method Genome | A ten-stage compilation report that can be filtered and exported. Method cards, comparison, dependency graph and health |
| Claims | The knowledge boundary map, ten-mode stress tests and blindspot coverage, each exportable |
| Scientific Debugger | Breakpoints with recomputation, differential debugging between two runs, and independent reproduction |
| Model Arena | M0 against M1 per axis, with residuals, criteria and leave-one-out |
| Uncertainty Flow | The flow diagram with keyboard-reachable nodes and the list of what is not propagated |
| FutureLab | Validated scenarios and an interactive calculator, labelled hypothetical |
| Questions & Next Steps | Decision records with the reason each step is not ranked higher, and seven question categories |
| Negative Space | The registry with the seven distinctions, search, and your own entries |
| Integrity Firewall | Export-readiness checks on the report, your notebook or pasted text |
| Protocol & Blind Analysis | Protocol, lock, amendments, blind and unblind |
| Reasoning Lab | Arguments built from graph objects, with branching, comparison, disputes and a markdown export that separates validity from empirical standing |

Earlier workspaces gained three tabs: the evidence vault (Knowledge Atlas), the simulation audit (Synthetic Observatory) and the
review board with comments and responses (Review Room).

Catalogue: [PHASE8_CATALOGUE.md](PHASE8_CATALOGUE.md). It lists 507 distinct concepts in 50 domains: the brief's 500, minus 31
merged synonyms, plus 38 added. Of these, 174 are existing (160 cite their Phase 7 entry), 248 are new in 0.8, 79 are deferred,
1 is blocked and 5 are out of scope. Methods: [EPISTEMIC_METHODS.md](EPISTEMIC_METHODS.md), generated from the code and the fixture
runs.

## 5. Gates

The gates are recorded in [TEST_REPORT.md](TEST_REPORT.md) (v0.8.0 section) with their commands and outputs. A gate passes only
when its checks ran.

## 6. What Phase 8 did not do

* Real-data acquisition is still BLOCKED (proxy 403). Every Phase 8 result is computed on the synthetic fixtures and labelled.
* The copilot does not read the epistemic report: copilot routing, explanations and debugging assistance by epistemic object
  are deferred. The model remains unable to compute anything scientific.
* Deferred concepts include:
  - object and claim histories across runs, and boundary transitions
  - your own model registration
  - pixel profiles, region statistics and residual maps
  - question ranking
  - knowledge collections
  - queues and milestones
  - the eight learning exercises
  - FITS metadata exchange, VOTable and W3C PROV exports
  - property-based testing (no library installed)
* Dependency review is BLOCKED (PyPI and OSV refused). Reviewer identity, assignments, permissions and scheduling are out of
  scope: there are no accounts.

See the catalogue and [LIMITATIONS.md](LIMITATIONS.md).
