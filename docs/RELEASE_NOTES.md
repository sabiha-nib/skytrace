# Release notes

## 0.10.0 — 2026-11-03 · the universal frontier

Skytrace now works in six languages — English, বাংলা (Bangla), हिन्दी (Hindi), Español, Français and Deutsch — and adds a signal
workbench, a world model of each investigation, a multilingual research workspace and an open science gateway. All five
translations were written by an AI model (Claude) and **have not been reviewed by native speakers**; every translated view and
report says so. Translation changes wording only: numbers, units, identifiers, method names and the statements recorded by the
scientific engines are kept unchanged in English. Nothing in this release measures anything new from images, invents a
probability, scores a discovery or calls a model, and the bundled data are still synthetic. Real-data acquisition, the Meta
model, semantic search and external monitoring are still blocked in the build environment.

**Six languages** (I18N-1, see [I18N.md](I18N.md))
* Language selector in the navigation and in Settings; the choice persists (`localStorage`, `?lang=`, the session's
  `preferences`). Number formatting per language, with a Western-digits option. Noto Sans Bengali and Devanagari fonts bundled.
* 3,668 interface messages and 16 keyed messages with plural forms, all translated in all five languages; a release-blocking test
  fails if any is missing or if a translation drops a number, a placeholder or a method identifier.
* Terminology base (TERM-1): 48 scientific terms with definitions, synonyms and Bangla/Hindi pronunciation.
* Reports in six languages (`report.md?lang=xx`) with a language header; every number identical to English (tested).
* **Cross-language search** (XSEARCH-1): exact text, terminology mapping and lexical matching across scripts, in Multilingual
  Research and the command palette. The method is labelled in the results: **it is not semantic search**.
* **Translation Quality Observatory** (I18N-Q1): completeness, placeholder, Unicode, number, identifier, script and terminology
  checks and text expansion per language, plus a live check for clipped text. Counts, never percentages.
* Explanations in eight layers (EXPLAIN-1) written as keyed messages in all six languages.

**New workspaces** (methods in [UNIVERSAL_METHODS.md](UNIVERSAL_METHODS.md))
* **Signal Intelligence** (SIGNAL-1): per-detector, wavelength-matched photometry series and astrometry series, never
  interpolated; ten methods (sampling, window, noise check, generalised Lomb–Scargle, Fourier, Haar, DCF, Theil–Sen, change point,
  model comparison), each listed as applicable or not with the reason. BIC is reported only when its assumptions hold; no
  false-alarm probabilities.
* **World Model** (WORLD-1) with a structured query, **discovery convergence** (CONV-1; exposure-independent lines only; repeated
  use of the same data is never confirmation), **research leads** from contradictions (LEAD-1; a lead is not a paradox), one
  multimodal measurement table (MODAL-1) and a **timeline** that keeps observation, processing, publication and event time apart
  (TIMES-1).
* **Multilingual Research**: language, cross-language search, terminology, explanations and translation quality.
* **Open Science Gateway** (OSG-1): the discovery handoff protocol (HANDOFF-1, `skytrace.handoff/1` with validation and digest),
  the research flight recorder (FLIGHT-1, tamper-evident replay, not cryptographic), a reproducibility checklist and ZIP bundle,
  and reports in any language. Nothing is uploaded or published.

**Added to existing workspaces**
* Negative Space: nine distinctions (NEGX-1), each saying what it does not mean.
* Scientific Compiler: Passed / Passed with warnings / Incomplete / Failed / Not evaluated (KCOMP-1).
* Discovery Radar: opportunities in ten fields with a bounded novelty scope (OPP-2; "new to this collection" at most); external
  sources registered and shown as **not connected** (EXTSRC-1).
* Research Autopilot: the investigation director (DIRECT-1), every step approved before it runs, with an audit log.
* Review & Story: five role agents and their debate record (AGENTS-1); shared model, data and assumptions, so agreement is not
  independent confirmation.
* Experiments: the experiment marketplace (EXPMKT-1); "recommended" only with a known-answer test.
* Levels renamed Explorer / Researcher / Advanced.
* API: `GET /api/investigations/{iid}/universal`; `report.md?lang=`. The static preview records the universal report for every run.
* Session fields `preferences`, `monitors`, `director`, `debates`, `handoffs`; earlier sessions stay valid.
* [Phase 10 catalogue](PHASE10_CATALOGUE.md): 800 ideas in 65 domains with ten fields each (A 372 implemented and tested, B 163
  implementable now, C 177 need data or infrastructure, D 88 speculative or out of scope); and the [Phase 10 audit](PHASE10_AUDIT.md).

**Not done** (see the audit): native-speaker review; semantic search; live monitoring of external sources; a digital twin beyond
the Phase 7 instrument twin; information gain without priors; multi-user collaboration; right-to-left scripts.

**Unchanged**: the pipeline and record hashes, English reports byte for byte, the copilot's tools and guard, and every earlier
workspace and test. Earlier release artifacts are kept.

## 0.9.0 — 2026-11-02 · the scientific intelligence layer

Skytrace now connects what it knows across investigations and helps decide what to do next, within stated rules. One new
workspace, *Scientific Intelligence*, holds twelve panels in six layers (observation, discovery, reasoning, experimental,
knowledge, integrity) over one shared entity model. Every panel labels what it shows as real data, synthetic data, simulated
output, hypothetical scenario, unverified interpretation or verified computation. Nothing in this release measures anything new,
invents a probability, scores a discovery or calls a model, and the bundled data are still synthetic. Real-data acquisition, the
Meta model, multi-agent research and semantic search are still blocked in the build environment.

**New**
* **Shared entity envelope** (SCI-ENTITY-1): every object has a stable id, version, provenance, creation time, epistemic status
  and validation. Status rules E1–E6 cover objects outside the reasoning graph.
* **Research Memory** (MEMORY-1): remembered observations, conclusions, explanations, failures, questions and assumptions across
  the investigations the server holds, with statuses M1–M6. Explanations are never promoted to facts. Recall uses a fixed concept
  vocabulary; **memory of failure** quotes the recorded reason before you repeat an action that failed on the same target;
  superseded conclusions are marked outdated; knowledge evolution shows how each conclusion moved between runs.
* **Discovery Genome** (DGENOME-1): thirteen cited fields per question, structural comparison without a score, a **sensitivity
  fingerprint** (FINGERPRINT-1, six recomputed dimensions) and an **uncertainty budget** (BUDGET-1: measured, estimated and
  unquantified terms).
* **Unknown Universe** (UNKNOWN-1): eight regions placed by rules U1–U8, each item with its basis, keyboard-operable.
* **Multi-Discovery Network** (MDNET-1): nine relationship rules, each edge with its basis and limitation; shared keywords never
  create an edge.
* **Scientific Adversary** (ADV-1): a challenge ledger organised by eight questions, every entry backed by a rule, resolved only
  with a reference; with the **instrumental reality check** (INSTCHECK-1, nine checks).
* **Causality Lab** (CAUSAL-1): a documented causal graph of the measurement process, confounders, temporal association,
  interventions as re-analyses and five separate criteria; "experimentally supported" is never met on archival data. Your
  proposed relations are checked for causal wording.
* **What-if Lab** (WHATIF-1): the six questions of the brief, answered only where a method exists, with a hypothetical extra visit
  for motion; the baseline is never modified.
* **Observation Oracle** (ORACLE-1, EVNEG-1): hypothetical observation plans under the validated measurement model, expected
  significance and Δχ², no information gain without defensible priors, and evidence negotiation between explanations. Never
  presented as scheduled.
* **Research Cycle** (CYCLE-1): registered actions proposed by rules A1–A6 under three autonomy levels (advisory, supervised,
  restricted automation), every step logged in the session. New registered action `reproduce_independent`.
* **Reproduction Network** (REPRONET-1): reproduction manifests with validation and six comparison classes; execution is not
  validity.
* **Integrity Gate** (GATE-1, DEBT-1, CAPSULE-1): eight requirements before marking complete ("ready" is not "true"), research debt,
  time capsules with a digest, Markdown handoffs and a `skytrace.knowledge/1` export.
* API: `GET /api/investigations/{iid}/intelligence`, `GET …/reproduction-manifest`, `GET /api/intelligence/corpus`,
  `POST /api/oracle`, `POST /api/whatif/visit`, `POST /api/reproduction/compare`. The static preview records the intelligence
  report for every run and the corpus.
* Session fields `challenges`, `completion`, `capsules` and `cycles`; 0.5–0.8 sessions stay valid.
* Generated documentation: [INTELLIGENCE_METHODS.md](INTELLIGENCE_METHODS.md), the [Phase 9 catalogue](PHASE9_CATALOGUE.md) (600
  concepts in 50 domains: 286 implemented and tested, 114 implementable now, 127 needing data or infrastructure, 73 speculative or
  out of scope) and the [Phase 9 audit](PHASE9_AUDIT.md) with build, compose and defer decisions for systems A–X.

**Partial or deferred** (see the audit): decision-theory workbench (K), per-event hypothesis timeline (U), importers for knowledge
packages and capsules (W, N), a stop control and budgets for automation.

**Unchanged**: the pipeline and record hashes, the copilot's tools and guard, and every earlier workspace and test. Earlier
release artifacts are kept.

## 0.8.0 — 2026-10-31 · the epistemic frontier

Skytrace can now show how each conclusion is built and test it the way software is tested. Every claim traces back to its files,
methods and assumptions. Investigations compile and can be debugged. Claims are stress-tested, failed work is kept, blindspots
are named, and uncertainty is followed through the pipeline. Reports are checked before they leave. Nothing in this release
measures anything new, invents a probability or calls a model, and the bundled data are still synthetic. Real-data acquisition,
the Meta model, multi-agent research and semantic search are still blocked in the build environment.

**New**
* **Reasoning graph** (EPI-1): fifteen kinds of scientific object with stable identifiers and ten epistemic statuses. Each status
  comes from one rule about origin and method (S1–S10), never from wording. Trace backward to files, measurements, methods and
  assumptions, or forward to dependent claims, with export. **Lineage-X** (LINEAGE-1) shows the nine stages of a claim or of the
  motion fit, with SHA-256 fingerprints, unit and coordinate conversions, and missing stages reported as missing.
* **Scientific compiler** (SCICOMP-1): ten stages (parse, types, dependencies, assumptions, methods, evidence, uncertainty,
  provenance, conclusions, report), each check stating its rule. Seven outcomes under one precedence rule. Every result says that
  passing is not proof. **Method genome** (METHOD-DNA-1) covers thirteen methods with typed inputs and outputs (units),
  assumptions, formula, dependencies, applicability, limitations, version chain and real known-answer tests, plus comparison, a
  dependency graph and health. Tests are labelled as software evidence, not scientific validity.
* **Scientific debugger** (SCIDEBUG-1): breakpoints only at stages the record contains. Results are recomputed from recorded
  inputs; nothing unrecorded is reconstructed. **Differential debugging** compares two runs stage by stage and finds the
  earliest divergence. **Independent reproduction** (REPROX-1) gives one of five verdicts; "exact" requires identical outputs and
  an intact record.
* **Claims**: a knowledge boundary (KBOUND-1) with four regions under rules B1–B4 and no confidence numbers; claim stress tests
  (CLAIMX-1) in ten documented modes, each returning pass, warning, fail, inconclusive, not tested or blocked; and blindspots
  (BLIND-1) over eleven defined checks, with no percentage. All three can be exported.
* **Negative Space** (NEG-1): failed, inconclusive, unavailable, unsupported, contradictory, unreproduced, missing, invalid,
  abandoned and limiting work, each with every required field and one of seven distinctions. Searchable, and you can add your own.
* **Model Arena** (MODELS-1): static against linear motion per axis, with residuals, χ², χ²ν, Δχ², AIC and leave-one-out. It checks
  that it reproduces the pipeline's fit, and reports no p-values or scores. **Uncertainty Flow** (UFLOW-1) shows only the
  categories the methods propagate and lists what they do not. **FutureLab** (FUTURE-1) validates its formula against the
  recorded σ before showing hypothetical scenarios, and has an interactive calculator.
* **Questions & Next Steps** (NEXTX-1, QFORGE-1): decision records with action, reasoning, evidence, inputs, limitations and why
  each item is not ranked higher, with no optimality claims. Questions in seven categories, each citing what prompted it.
* **Integrity Firewall** (INTEG-1): twelve export-readiness checks on the investigation report, your notebook or any text. It
  never blocks and never rewrites. It found a real gap: the investigation report had no limitations section. The report now
  states outcomes, criteria, sensitivities with units, and limitations.
* **Protocol & Blind Analysis** (PROTOCOL-1, BLINDLAB-1): a protocol can be locked with a content hash. A late lock is labelled as
  made after results were visible, and amendments are append-only. None of this is called preregistration. Blind analysis has a
  commitment hash; it covers outcome-bearing workspaces, pauses the copilot and stops ruler emphasis. Unblinding needs a locked
  protocol and a typed confirmation.
* **Reasoning Lab** (ARG-1): arguments built from graph objects, with inference rules, branching, comparison, disputes and a
  Markdown export that separates logical validity from empirical standing.
* **New tabs in existing workspaces**:
  - **Evidence vault** (VAULT-1, Knowledge Atlas): the session history is hash-chained. Edits are detected and refused on save,
    and corrections are appended. Described as tamper-evident, not as a signature.
  - **Simulation audit** (SIMCHECK-1, Synthetic Observatory): repeated-seed stability, assumptions and validity domain.
  - **Review board** (REVIEWX-1, Review Room): eight automated perspectives, every item linked to its evidence, with your
    comments, responses and resolutions.
* Navigation in the eight modes of the brief. New session fields `negative`, `reviews`, `protocol`, `blind`, `arguments` and
  `debug`, and the history chain; 0.7 sessions stay valid.
* API: `GET /api/investigations/{iid}/epistemic`, `POST …/reproduce-x`, `GET …/lineage`, `POST /api/integrity`,
  `POST /api/simulation-audit`. The static preview records the epistemic report for every run.
* Generated documentation: [EPISTEMIC_METHODS.md](EPISTEMIC_METHODS.md), the [Phase 8 catalogue](PHASE8_CATALOGUE.md) (507
  distinct concepts in 50 domains, deduplicated against Phase 7) and the [Phase 8 audit](PHASE8_AUDIT.md) with a
  feature-preservation matrix.

**Changed**: the investigation report has a new "Outcomes and limitations" section. Records and their content hashes are
unchanged. Navigation groups were renamed; every workspace keeps its button and route.

**Unchanged**: the pipeline, the copilot's tools and guard, and every earlier workspace and test. Earlier release artifacts are
kept.

## 0.7.0 — 2026-10-31 · the frontier laboratory

Skytrace can now ask "what if", generate and test against known answers, challenge its own interpretation, and say which
research is possible next. None of this measures anything new, invents probabilities or calls a model. Bundled data are still
synthetic. Real-data acquisition, the Meta model, multi-agent research and semantic search are still blocked in the build
environment.

**New**
* **Counterfactual Universe Lab** (CF-1): one stated change against a named baseline. The change can be an analysis parameter,
  excluded observations, a threshold, photometric error scale or PAIRDIFF-1 for brightness. You get a side-by-side comparison
  with value labels (observed, derived, simulated, assumed, hypothetical), an explanation, session lineage and JSON export. The
  baseline is recomputed and hash-checked. The original run and bundle are never modified. Nine prepared scenarios are included.
* **Synthetic Observatory** (SYNOBS-1): bounded, seeded scenarios generated as SYNTHETIC bundles in `data/synthlab/`. They are
  reproducible to the byte and analysed by the unchanged pipeline. Each run compares ground truth, the stated expected rule and
  the output, gives a verdict and lists failure behaviour. Six templates, including a deliberate blend failure case.
* **Observation Design Lab** (OBSDES-1): compare up to three hypothetical schedules with the same truth and export a planning
  brief. No telescope is scheduled.
* **Adversarial Science Lab** (ASL-1): rule-based challenges in eight modes with fixed severities. Each states issue, evidence,
  rule, why it matters, verification and status, and you can acknowledge one with a note. **Test ranking** (INFO-1) orders open
  tests by feasibility and the explanations they bear on; no numerical information gain is computed. A **causality workbench**
  separates model-derived dependencies, assumption-based explanations and user-proposed relationships, and warns about causal
  language in your notes.
* **Discovery Horizon** (SPE-1, HORIZON-1): six investigation layers and research-opportunity cards with all nine fields, a
  feasibility class and a stated ranking reason. Includes an opportunity map, tracking, export and plan hand-off.
* **Review Room** (REVIEW-1): five software reviewers (methods, evidence, data, reproducibility, interpretation) whose findings
  cite the record, with Markdown export. **Reproducibility challenge** (REPRO-1): eleven checks and four verdicts, plus
  re-execution; import never counts. **Discovery story**: ten chapters written only from recorded outcomes, where inconclusive
  results stay inconclusive.
* **Astro-twins** (TWIN-1): hashed computational records of an analysis, target, scenario and session (observation twins in the
  API), with integrity checked in both languages and structural comparison.
* **Research Autopilot** (CAPREG-3): permission classes for every action and five levels. Plans run only after authorization,
  can be cancelled and are recorded in the session. Network access is never granted.
* **Cosmic Atlas**: sky map, field view, galactic coordinates and angular separations. Distance appears only from a recorded
  parallax.
* **Knowledge Atlas**: exact multi-word search across everything stored, with the source of each hit.
* Navigation in eight research modes. Session fields `scenarios`, `synthetic`, `causal`, `autopilot` (0.6 sessions stay valid).
* Generated documentation: [FRONTIER_METHODS.md](FRONTIER_METHODS.md), the [Phase 7 catalogue](PHASE7_CATALOGUE.md) (406
  distinct concepts in 40 domains), the [Phase 7 audit](PHASE7_AUDIT.md) and the [multi-agent design](MULTI_AGENT_DESIGN.md)
  (implementation blocked).

**Unchanged**: the pipeline and its records. The same inputs give the same content hash as 0.6.1. Every earlier workspace and
test is unchanged, and earlier release artifacts are kept.

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
