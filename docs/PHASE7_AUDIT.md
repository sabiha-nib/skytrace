# Phase 7 audit: the frontier laboratory (v0.7.0)

Phase 7 asked for capabilities that go past investigating a record: counterfactual scenarios, digital twins of what Skytrace
knows, a map of research opportunities, an adversarial laboratory, a synthetic observatory and observation-design lab,
information-guided test selection, a causality workbench, a controlled autopilot, sky and knowledge atlases, a review room, an
evidence-bound discovery story and a reproducibility challenge. Every earlier rule still applied: no manufactured results, no
blocked work reported as done, no removed tests, no secrets outside the server. Phase 7 added its own rules. A simulated value is
never an observation. A counterfactual never overwrites the original. No flaw is claimed unless a rule establishes it. There is no
numerical information gain without a probability model, and no causation from correlation. No 3-D relationships come from 2-D
coordinates, and no semantic similarity is fabricated. No agent conversations are simulated, and importing a record is not
reproduction.

## 1. Repository audit (before any Phase 7 change)

| Item | State at commit `fb03e93` (v0.6.1 plus its test report) |
|---|---|
| Version | 0.6.1 (`src/skytrace/__init__.py`, `pyproject.toml`). The brief assumed 0.5.0; the repository was already at 0.6.1 |
| Working tree | clean |
| `verify.py --e2e` | 18/18 checks, with warnings for no astropy, no real bundles, no Meta key and Meta smoke test not run |
| Unit, integration, robustness and parity tests | 269 passed, 2 skipped (astropy not installed) |
| Browser tests | 73 passed (31 control steps × 2 modes, plus an 11-step journey) |
| Static preview | hosted at https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT (version 5, 0.6.1) |
| Release artifacts | 0.2.0–0.6.1 archives with `.sha256` files and `RELEASE_MANIFEST-<ver>.json`. 0.6.1: `14bfeec5…` (code, 389 files), preview `b6f58b3d…` |
| External services | IRSA, SIMBAD, Gaia, Meta API, PyPI and npm are refused by the proxy (403). No astropy, no Meta key |
| Data | Two synthetic fixtures (`syn-hpm-1`, `syn-var-1`). No real SPHEREx bundle |

Already present and reused, not rebuilt:
- research sessions (SESSION-1, SKY-CANON-1, SCHEMA-1, with Python/JS parity)
- capability registry and actions (CAPREG-2)
- planner (PLAN-1)
- compatibility and sequences (COMPAT-1/SEQ-1)
- data quality (DQ-1), evidence ledger (LEDGER-1) and radar (RADAR-1)
- experiments (EXP-1, including stability and negative controls)
- workflows (WF-1, never auto-run on import)
- hypotheses (HYPO-1, rule statuses, no probabilities) and uncertainty (UNC-1)
- provenance re-check (PROVCHECK-1)
- notebook, Figure Studio and knowledge graph
- the static preview's recorded-response backend

Not present: anything that changes an analysis and compares it with the original, synthetic data beyond the two fixed fixtures,
twins, an opportunity map beyond the radar, challenge rules, a reproducibility verdict, review roles, an autopilot with
permission levels, coordinate tools, and a story view.

## 2. What was preserved

Every 0.6 workspace, route and test runs unchanged. No test was removed or weakened. Two assertions changed for legitimate
reasons: the registry version moved from CAPREG-2 to CAPREG-3, and the action count grew. The pipeline (`analysis.py`,
`science/`) is unchanged in behaviour. `assess_motion` and `assess_variability` gained an optional `thresholds=` argument that
the pipeline never passes. Investigation records and their content hashes are identical to 0.6.1 for the same inputs. Sessions
written by 0.6 stay valid: the new session fields are optional, and a test covers this. Earlier release artifacts are kept, and
`make_release.py` still refuses to overwrite a version.

## 3. Architecture decisions

* **Change a copy, never the original.** CF-1 recomputes the baseline from its parameters and refuses if the content hash
  differs from the one stated. Exclusions act on a copy of the bundle index and are logged as selection rejections; the files on
  disk are untouched. Threshold, error-scale and method scenarios re-assess the recorded inputs with explicit overrides. A test
  shows that re-assessment with no change reproduces every recorded outcome exactly, on both fixtures, so any difference comes
  from the stated change alone. Every value carries a label: observed, derived, simulated, assumed or hypothetical.
* **Synthetic data in its own place, reproducible to the byte.** SYNOBS-1 writes bounded scenarios to `data/synthlab/`, which is
  gitignored and can be set with `SKYTRACE_SYNTHLAB_DIR`. It never writes to `data/bundles/` or `fixtures/`. Files carry
  `SYNTHETIC = T` and a fixed provenance stamp, so the same scenario and seed give identical bytes and the same record hash. Each
  expected outcome is a stated rule applied to the ground truth and the pipeline's own reported sensitivity. Verdicts are
  "agrees", "disagrees" or "not determinable", or "not confirmed" when the result is calibration-limited. Every result states that
  agreement on generated data does not validate real-data performance. OBSDES-1 compares hypothetical schedules with the same
  truth and seed. It does not schedule a telescope and does not claim instrument performance.
* **Rules, not opinions.** ASL-1 raises a challenge only when a documented rule's condition holds on recorded values. Severity is
  fixed per rule. An acknowledged challenge stays visible. INFO-1 has no probability model, so it orders tests by feasibility
  and by the viable explanations they bear on, and says so. REPRO-1 has eleven checks and four verdicts. "Reproduced" needs a
  re-execution with an identical content hash; a successful import is never enough. REVIEW-1's five roles are rule sets, not
  people or agents, and every finding cites a record field.
* **The server computes, the browser refines.** One `frontier_report` per record (and stability result) is cached by hash. Rules
  that depend on the session run in the browser in `frontiercore.js`: the horizon filter, challenge statuses, review of your
  notes, twin comparison and coordinates. Parity tests check them against Python on the same inputs.
* **Twins are records, not physics.** TWIN-1 produces hashed, sectioned computational records (inputs, parameters, methods,
  measurements, outputs, assumptions, provenance) with the hashes they derive from. Integrity is recomputed in both languages.
  Comparison is a structural diff that refuses to compare different kinds.
* **Controlled orchestration.** CAPREG-3 gives every action a permission class: inspect, analysis, export or network. The
  autopilot's five levels allow subsets of these, and none allows network. A plan runs only after you tick an authorization that
  lists its steps. It uses the shared executor, records every run in the session and can be cancelled. A model-proposed plan
  would pass the same validation.
* **Honest geometry and search.** The atlas computes angular separations and galactic coordinates. It shows a distance only from
  a recorded parallax, labelled as inferred, and says no physical separation is computed. Knowledge search is exact multi-word
  matching that names where each hit is stored. Semantic indexing is BLOCKED because no embedding model is reachable.
* **The preview stays honest.** At build time the static preview records the frontier reports, the default run's reproducibility
  audit, nine prepared counterfactuals, six synthetic templates and one schedule comparison. Edited scenarios and specifications
  are refused in the preview with a reason; they are never approximated.

## 4. What was built (summary; the full list is the Phase 7 catalogue)

Eight workspaces in eight research modes (Observatory · Discover · Investigate · Experiment · Understand · Orchestrate ·
Knowledge · Publish):

- **Discovery Horizon:** six layers, opportunity cards with all nine fields, and an opportunity map.
- **Counterfactual Lab:** presets, a custom builder, a labelled comparison, the baseline-intact indicator, session history and
  export.
- **Adversarial Lab:** challenges by mode and severity with acknowledgement notes, test ranking, and a causality workbench with
  model-derived, assumption-based and user-proposed relationships and warnings about causal language.
- **Synthetic Observatory and Observation Design Lab:** six templates including a deliberate failure case, a ground-truth table,
  failure behaviour, schedule comparison and a planning brief.
- **Autopilot:** objective, plan, level, authorization, run, cancel and history.
- **Cosmic Atlas:** sky map, field view, coordinates in two frames, angular separations and distance status.
- **Knowledge Atlas and twins:** exact search, analysis, target and session twins, integrity checks and comparison.
- **Review Room:** five reviewers, the reproducibility challenge (audit and re-execution) and a discovery story whose ten
  chapters come only from recorded outcomes.

Catalogue: [PHASE7_CATALOGUE.md](PHASE7_CATALOGUE.md), with 406 distinct concepts in 40 domains (400 from the brief, 36
synonyms merged, 42 added). Each concept has a status, group, evidence and verifying test, and 78 cite their Phase 6 entry.
Methods: [FRONTIER_METHODS.md](FRONTIER_METHODS.md), generated from the code and from fixture and scenario runs.

## 5. Gates

The gates are recorded in [TEST_REPORT.md](TEST_REPORT.md) (v0.7.0 section) with their commands and outputs. A gate passes only
when its checks ran.

## 6. What Phase 7 did not do

* Real-data acquisition is still BLOCKED (proxy 403). Every result is from the synthetic fixtures or generated scenarios and is
  labelled so.
* Multi-agent research is BLOCKED because no model provider is verified. The design is in
  [MULTI_AGENT_DESIGN.md](MULTI_AGENT_DESIGN.md), and no agent conversation is simulated anywhere.
* Semantic indexing is BLOCKED.
* 74 catalogue concepts are deferred and 4 are out of scope, including:
  - twin restoration and twin version history
  - region and pixel statistics
  - multi-target sessions
  - decision trees (these would need outcome probabilities)
  - temporal-order checks for causal claims
  - figure sequences and slide export in the story

See the catalogue and [LIMITATIONS.md](LIMITATIONS.md).
