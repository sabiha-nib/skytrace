# Phase 6 audit — the research operating system (v0.6.0)

Phase 6 asked for Skytrace to grow from an investigation tool into a research environment: a persistent, integrity-checked
research session; one capability registry that the planner, copilot, workflows and missions all use; a deterministic
investigation planner; multi-epoch work that never interpolates; experiments, data-quality checks, an evidence ledger,
a notebook, a knowledge graph, a Discovery Radar of research opportunities, missions and bounded automation — without
weakening any earlier rule: no manufactured results, no blocked work reported as done, no decorative controls, no secrets
outside the server, no removed tests.

## 1. Baseline (before any Phase 6 change)

| Item | State at commit `6d42705` (v0.5.0) |
|---|---|
| Working tree | clean |
| `verify.py --e2e` | 18/18 checks, 4 warnings (no astropy, no real bundles, no Meta key, Meta smoke test never run) |
| Unit, integration and robustness tests | 225 passed, 2 skipped (astropy not installed) |
| Browser tests | 51 passed (journey plus every control, server and static mode) |
| Static preview | 121 files, hosted as https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT (version 3) |
| Release artifacts | `dist/skytrace-0.5.0.zip` (sha256 `1953d3e7…`), `dist/skytrace-preview-0.5.0.zip` (sha256 `8b1d706d…`), and the 0.4.0 pair |
| External services | IRSA, SIMBAD, Gaia, Meta API, PyPI, npm: refused by the proxy (403) |

## 2. What was preserved

Every 0.5 workspace (Explorer, Time Machine, Lab, Discovery Engine, Hypothesis Arena, Uncertainty Explorer, Evidence Graph,
Vault, Report Studio, copilot) works as before; every 0.5 test still runs and passes; no test was removed or weakened (two
assertions were updated where a registry version and a tool count legitimately changed: CAPREG-1 → CAPREG-2, 12 → 16 tools).
The investigation record and its content hash are unchanged by Phase 6 code, which only reads records. 0.4.0 and 0.5.0 release
artifacts are kept; `make_release.py` refuses to overwrite an existing version. Saved 0.5 records migrate into sessions and the
originals stay where they were.

## 3. Architecture decisions

* **One state object, validated and hashed.** A research session (SESSION-1) holds everything a person does; it is validated by a
  declarative schema interpreter (SCHEMA-1) that exists once in Python and once in JS, and hashed over a canonical JSON form
  (SKY-CANON-1) that both languages produce byte for byte. Parity tests cover the number spelling, key order, refusals, the
  schema and the hash. Imports with a different hash are refused; nothing overwrites an existing session.
* **One list of what can be executed.** CAPREG-2 adds ACTIONS (14) to the capability registry. The planner, workflows, radar and
  missions execute only these, through one browser executor; the copilot's new `plan_investigation` tool proposes them and runs
  none. Each action states preconditions, outputs, confirmation, cost and where it can run in the static preview.
* **Deterministic first.** PLAN-1 is a rule table (served from `/api/specs`, so browser and server use one table) plus templates;
  any model-proposed intent is used only after `validate_intent`. Radar ranking is a stated order, not a computed score. Data
  quality is eleven separate checks with five outcomes and no aggregate.
* **Readers of the record, again.** COMPAT-1, SEQ-1, DQ-1, LEDGER-1 and RADAR-1 read the finished record, bundle manifest and
  discovery index. They re-decide nothing (the compatibility matrix is the logged WLMATCH-2 decisions) and are cached by the
  record's content hash.
* **Human judgement stays human.** Inspection steps end as `needs review` and are excluded from batch runs; mission reviews need a
  written note; assistant drafts stay labelled until accepted; experiments state that running is not validity.
* **The preview stays honest.** Experiments, research reports and copilot answers are recorded by the server at build time; plans,
  sessions, notebook, figures, KG and workflows run in the browser; provenance re-runs, connector previews and custom experiments
  refuse with a reason.

## 4. What was built (summary; the full list is the Phase 6 catalogue)

Research sessions (new, open, rename, branch, export, verified import, migration) · Observatory Command Center (real values, missions) ·
Investigation Planner (intents, templates, statuses, confirmation, revisions, needs-review steps) · Data Quality Observatory (checks,
compatibility matrix, metadata diff, coverage, connectors) · multi-epoch sequences in the Time Machine (playback over compatible
sequences only, frame difference, sequence export) · Experiment Studio (six templates, negative controls on another fixture, bounded
robustness) and workflows (validated, batch, per-item records, cancel, retry, export/import) · Evidence Ledger (claims, contradictions,
provenance, methods, completeness, change history) with the evidence graph · Research Notebook (13 block types, resolved references,
versions, undo, Markdown and deterministic session package) · Figure Studio (FIG-2) and knowledge graph (KG-1) in the Vault ·
Discovery Radar (RADAR-1) · missions (MISSION-1, no gamification) · connectors (ACQ-2 request previews; nothing sent) · Copilot 2.0
(16 read-only tools, five new intents, answer-source labels, notebook drafts, plan hand-off).

Catalogue: [PHASE6_CATALOGUE.md](PHASE6_CATALOGUE.md) — 309 distinct concepts (300 from the brief, 15 synonyms merged, 24 added),
each with status, group, evidence and verifying test. Methods: [RESEARCH_METHODS.md](RESEARCH_METHODS.md), generated from code and
fixture runs.

## 5. Gates

Recorded in [TEST_REPORT.md](TEST_REPORT.md) (v0.6.0 section) with the commands and outputs. A gate is PASS only when its checks ran.

## 6. What Phase 6 did not do

Real-data acquisition is still BLOCKED (proxy 403 for IRSA, SIMBAD, Gaia); every result in the product is from the two synthetic
fixtures and is labelled so. The Meta model was never called (no key; the API is refused); the copilot's answers are the local
deterministic assistant's and are labelled so. 64 catalogue concepts are deferred, 1 blocked and 5 out of scope; see the catalogue
and [LIMITATIONS.md](LIMITATIONS.md).
