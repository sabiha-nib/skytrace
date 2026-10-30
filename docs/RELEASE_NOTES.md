# Release notes

## 0.6.1 — 2026-10-30 · top-bar fix

* **Fixed**: between 861 and 1180 px wide, the top bar did not wrap and pushed *Run analysis*, *Copilot* and the status
  pills past the right edge. Found by opening the hosted 0.6.0 preview in an 800-px-wide browser pane. The bar now wraps at
  those widths, and `test_j_levels` checks every visible top-bar control at nine widths from 390 to 1440 px in both modes.
* No other change; 0.6.0 artifacts are kept.

## 0.6.0 — 2026-10-30 · the research operating system

Skytrace now keeps a whole line of research in one validated, hash-checked session and offers a set of research tools
around it — planner, data-quality observatory, evidence ledger, experiment studio, notebook, radar, missions, automation —
all executing the same registered actions and none producing a probability or a score. The bundled data are still
synthetic, and real-data acquisition and the Meta model are still blocked in the build environment.

**New**
* **Research sessions** (SESSION-1): question, runs, hypotheses (with versions), notebook, plans, experiments, missions,
  workflows and an append-only history in one session; validated by a schema interpreter shared by Python and JS (SCHEMA-1)
  and hashed over canonical JSON (SKY-CANON-1). Open, rename, branch, export, import (hash-verified, never overwriting);
  0.5 saved records migrate.
* **Capability registry with actions** (CAPREG-2): 14 executable actions with preconditions, outputs, confirmation, cost and
  static-preview availability; one browser executor for the planner, workflows, radar and missions.
* **Observatory Command Center**: data state, session, outcomes, quality, radar and missions from real values.
* **Investigation Planner** (PLAN-1): plain-language questions → plans of registered actions with statuses, dependencies,
  confirmation for expensive steps, `needs review` for inspection steps, revisions, and honest refusals.
* **Multi-epoch sequences** (SEQ-1) in the Time Machine: playback over compatible sequences only, frame differences,
  sequence export; never interpolated; says when only two visits exist.
* **Data Quality Observatory** (DQ-1, COMPAT-1): eleven checks with rules and five outcomes (no score), the full compatibility
  matrix with reason codes, metadata diff, duplicate detection, time coverage, connector previews (ACQ-2; nothing is sent).
* **Evidence Ledger** (LEDGER-1): support counted per claim, single-item support flagged, contradictions by rules C1–C4,
  provenance, methods, completeness and change history.
* **Experiment Studio** (EXP-1): parameter, sensitivity, method comparison, reproducibility, negative control (on another
  fixture) and robustness experiments, each with its criterion and a validity note; **workflows** (WF-1): validated, bounded,
  batch over targets, per-item records, cancel, retry, export/import.
* **Discovery Radar** (RADAR-1): research opportunities with what / why / evidence / data needed / method / cannot establish /
  can run now, in a stated order.
* **Research Notebook**: 13 block types, references resolved against recorded values, authorship labels, versions, undo,
  search, Markdown export and a deterministic session package (ZIP).
* **Figure Studio** (FIG-2) and **knowledge graph** (KG-1) in the Vault; **missions** (MISSION-1) without gamification.
* **Copilot 2.0**: 16 read-only tools (new: plan_investigation, get_data_quality, get_evidence_ledger, get_hypothesis_tests),
  five new local intents, the source of every answer labelled, *Add to notebook as draft*, *Plan this question in the Planner*.
* **Phase 6 catalogue**: 309 distinct concepts (the brief's 300 in 30 domains, 15 synonyms merged, 24 added) with status,
  group, evidence and verifying test; **research methods** document generated from code and fixture runs.

**Changed**
* Navigation grouped Observe · Investigate · Verify · Record; Alt+1…9 over the visible workspaces; the default workspace is
  the Command Center. Levels still change visibility only; opening a deeper workspace raises the level and says so.
* Retry-After from archives is honoured up to 60 s. Copilot routing gained five intents (parity-tested in the preview).

**Not changed**
* The analysis pipeline (`skytrace-analysis/2`) and every 0.5 result and content hash. All 0.5 tests still pass; none removed.

**Still blocked**
* Real SPHEREx/SIMBAD/Gaia access and the Meta Model API (proxy 403, re-checked 2026-10-30). Live tests fail for that reason.

## 0.5.0 — 2026-10-30 · the discovery environment

Skytrace now walks an investigation through one loop — explore, observe, compare, detect, test, explain, verify,
preserve, share — and says at each step what the data can and cannot establish. All new results are computed by
versioned, deterministic methods from the recorded investigation; none is a probability. The bundled data are still
synthetic, and real-data acquisition is still blocked in the build environment.

**New**
* **Discovery Engine** (DISC-1): evidence inventory with checksums and counted unknowns; research questions marked
  answerable, answerable with limits or not answerable (and why); a test plan for each; evidence review; rule-based
  next steps that state what each can and cannot establish and which unavailable service it needs.
* **Hypothesis Arena** (HYPO-1): 11 competing explanations × 12 recorded tests, six statuses, one published overall
  rule (identical in the browser, parity-tested). Your own hypotheses, labelled as interpretations, can cite recorded
  tests; removal can be undone.
* **Uncertainty Explorer** (UNC-1): components of the motion and brightness uncertainties, bounds kept as bounds, a
  recompute check of every calibrated z, parameter sensitivity kept separate, and the effects nothing here quantifies.
* **Registration diagnostics** (REGDIAG-1) in the Time Machine, computed in Python and in the browser.
* **Evidence Graph**: competing explanations appear as nodes linked to the claims they would explain.
* **Capability registry** (CAPREG-1): one list of what Skytrace can do and where; the copilot can answer from it.
* **Copilot answers** laid out as Answer · Evidence · Method · Limitations · Next step.
* **Report Studio**: report, record, evidence graph, discovery report and a deterministic reproducibility package
  (PKG-1, with SHA256SUMS); any chart exports as an SVG carrying its target, investigation hash and method versions.
* **Vault**: search, tags and tag filter, rename, duplicate, compare two investigations, import preview with a
  browser-side content-hash check before anything is stored.
* **Interaction**: discovery-loop bar, command palette (Ctrl/⌘+K or /), glossary and shortcuts (?), Alt+1…7, three
  levels of detail (Explore, Investigate, Research).
* **Feature catalogue**: 267 concepts in 25 domains, scored and tiered, generated from data with computed counts.

**Changed**
* Saved records store tags, the investigation context and an outcome summary; the server gains `PATCH /api/records/{id}`,
  `POST /api/records/{id}/clone`, `GET /api/capabilities`, `GET /api/investigations/{id}/discovery` and
  `GET /api/investigations/{id}/package.zip`.
* The faint text colour was raised to meet 4.5:1 contrast on every surface.
* `make_release.py` refuses to overwrite an existing version's artifacts and zips the static preview only when it was
  built from the release commit.

**Unchanged on purpose**: the analysis pipeline, its methods and the content hashes of the fixture investigations.

**Still blocked**: IRSA, SIMBAD, Gaia, the Meta Model API and package indexes are refused by this environment's
network policy. See [LIMITATIONS.md](LIMITATIONS.md).

## 0.4.0 — 2026-10-29 · previewable application

Static preview recorded from the real server, hosted preview, browser parity for pair comparison and content hashes,
verified record import/export, graph provenance, history navigation, every control tested in both modes.
[PHASE4_AUDIT.md](PHASE4_AUDIT.md)

## 0.3.0 — 2026-10-29 · validation

FITS/WCS validation against independent files, calibration audit, ASSESS-2, provenance verification, TOOLS-2 and
GUARD-3, robustness scenarios. [PHASE3_GATES.md](PHASE3_GATES.md)
