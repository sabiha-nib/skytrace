# Limitations

## Not yet verified

- **No real SPHEREx data has been processed.** The build environment could not reach IRSA, SIMBAD or the Gaia archive (proxy `403 Forbidden`), and access to a networked computer was not granted. Every scientific statement in this repository rests on synthetic tests.
- **The native FITS/WCS reader has not been compared with astropy on a real SPHEREx file.** Since v0.3 it is validated against 14 independent astropy/wcslib test files (see [FITS_WCS_VALIDATION.md](FITS_WCS_VALIDATION.md)), which found and fixed six defects. `tests/live` performs the decisive real-file comparison. Install astropy to use astropy for reading in the meantime.
- **The real FLAGS bit layout and time keywords are unknown.** Only `MP_TRANSIENT` (bit 0) and `MP_SOURCE` (bit 21) are documented in what was available. Other flags are applied only when the file's header defines them; otherwise they are reported as unresolved.
- **No Meta Model API call has been made.** The request format follows the documentation, but tool-call and structured-output behaviour of `muse-spark-1.3` are untested. Pricing, rate limits and availability in your country are unknown.
- **The Dockerfile has not been built.**

## Scientific

- Wavelengths come from the `WCS-WAVE` lookup, which IRSA describes as ~1 nm accurate and intended for visualisation. Sub-nm matching decisions would need the Spectral WCS product (CWAVE/CBAND).
- Aperture fluxes are not aperture-corrected. Fluxes from different detectors are not on a common scale, so the spectrum's shape across detectors is approximate.
- Gaussian centroids approximate the SPHEREx PSF. The file's PSF extension (121 zone PSFs) is not used yet.
- Parallax is modelled since v0.3 with a low-precision ephemeris (residual ≤ 0.01ϖ, e.g. ≤ 5.5 mas for Barnard's Star); SPHEREx's orbit around Earth (< 10⁻⁵ AU) is neglected.
- Chromatic PSF and distortion differences between wavelengths are not modelled; positions from different detectors are combined.
- Exposure-level calibration changes are removed with reference stars (PAIRDIFF-2) only when ≥ 3 wavelength-matched references exist; otherwise a significant difference is reported as `calibration_limited`. The CALCHECK error scale corrects the error model only on average. On SYN-VAR-1 the reference stars scatter 1.56× their stated errors, most likely from sub-pixel aperture losses with an undersampled PSF (hypothesis, not isolated).
- Multi-epoch photometry across QR2 and QR3 is refused by default, which may leave some targets without a testable pair until a single release covers several epochs.
- Reference stars with a catalogue error but no Gaia quality flag are caught only per exposure (leave-one-out); in low-S/N exposures some survive.
- Unresolved companions (RW Aur B at 1.4″, ε Indi Ba/Bb at 0.6″) contribute to every flux and centroid at 6.2″ pixels.
- Bright targets (Barnard's Star, likely R Draconis) may be flagged as overflow or non-linear in most exposures; flagged photometry is not measured.
- WISE 0855 is expected to be undetectable below ~3 µm and possibly in single exposures at all. Stacking within a visit is not implemented.

## Discovery environment (v0.5)

- The Discovery Engine, Hypothesis Arena and next steps are **rules over recorded values**, not inference. A rule can be
  wrong for a case it was not designed for; each rule is printed beside its result so it can be judged.
- Several explanations have **no implemented test** (wavelength-tolerance slope, unresolved neighbour blend, chromatic
  offsets). They are shown as *not tested*; their absence of a contradiction is not support.
- The uncertainty decomposition shows only components the methods logged; aperture correction, PSF variation,
  chromatic offsets and uncatalogued neighbours are named but not quantified.
- Registration diagnostics use the linear part of each plate solution; distortion residuals enter only through the
  plate RMS.
- The feature catalogue's scores are judgements by the developer, not measurements; its domain list and dimensions are
  this project's own breakdown.
- In the static preview, the discovery report, the hypothesis tests, the uncertainty decomposition and the package were
  computed by the Python pipeline when the preview was built; the browser does not re-execute them (it says so).
- Accessibility was checked by automated tests (accessible names, dialog semantics, contrast of every text token, focus
  return, keyboard paths). No screen-reader session with assistive technology has been run.

## Research operating system (v0.6)

- **Planning is rule-based.** PLAN-1 matches questions with a fixed table; a question phrased outside it is reported as
  unplannable, and a question that matches the wrong rule gets the wrong template (the intent is shown so this is visible).
  No language model has proposed an intent in this environment (no key; the API is refused).
- **Sessions are single-writer.** Two browser tabs editing one session overwrite each other (last save wins); there is no
  merge. Branching makes an independent copy; nothing is merged back. In the static preview sessions live in this browser's
  storage only and can be lost if site data is cleared — export to keep them.
- **Sequences and playback show recorded frames only.** With two visits a sequence is a pair, and the interface says so;
  nothing is interpolated, and no motion between frames is implied.
- **Data-quality outcomes are per check.** `valid` means valid under the tested rule, not that the data are good for every
  purpose; `not checked` (e.g. file hashes through the copilot) and `not available` are not passes. There is no overall score
  on purpose.
- **The ledger counts, it does not weigh.** Support counts say how many items link to a claim, not how strong they are. Only
  the four contradiction rules C1–C4 are checked.
- **Radar order is a convention.** RADAR-1 ranks by a stated signal order with runnable items first; it is not an estimate of
  scientific value.
- **Experiments say what ran, not what is true.** A met criterion means the stated criterion held for the tried settings.
  Negative controls need a *different* fixture without the effect: with two fixtures, syn-var-1 has no motion control and
  syn-hpm-1 no variability control (reported as not available). Robustness covers six bound settings only.
- **Missions do not enforce task order.** Tasks are listed in a recommended order; each is checked independently.
- **Connectors are previews.** All four services are refused here; previews show the exact request the acquisition code
  would send. No archive response has been received in this release.
- **Knowledge graph.** KG-1 links only saved records and sessions in this installation (or browser), by five stored-fact rules.
- **Figures.** FIG-2 exports SVG only; no PDF writer was available that could be validated, so none is offered. Axis ranges are
  set by the data.
- **Static preview.** Copilot answers are recorded for one question per intent; when your wording differs the answer says which
  question was recorded. Custom experiments, provenance re-runs and connector previews need the local server.
- **Catalogue.** 64 Phase 6 concepts are deferred, 1 blocked (dependency audit: PyPI/OSV refused) and 5 out of scope; see
  [PHASE6_CATALOGUE.md](PHASE6_CATALOGUE.md). Group assignments are the developer's judgement.

## Frontier laboratory (v0.7)

- **Everything frontier runs on synthetic data here.** Counterfactuals, challenges, reviews, twins and horizon cards use the two
  synthetic fixtures. Synthetic Observatory scenarios are generated. Nothing in 0.7 has run on a real SPHEREx observation.
- **Counterfactuals are bounded.** There are five kinds (parameter, exclusion, threshold, error scale, method), one change per
  scenario. Threshold bounds are 2–10 σ (catalogue consistency 1–5), the error factor is (1, 5] and at most 40 observation keys
  can be excluded. Error scaling affects photometry only. The only method substitution is PAIRDIFF-1 for brightness. A scenario
  says what would follow under the stated change. It is not an alternative observation, and its "simulated" and "assumed" values
  are labelled as such.
- **The synthetic generator is simple.** It uses a Gaussian PSF, a constant sky, Gaussian noise with a simple signal-dependent term,
  three detector positions and up to six passes. Agreement with ground truth tests the software against its own generator. It does not establish completeness,
  false-positive rates or performance on real data, and no completeness curve is computed. The noise model in the Observation
  Design Lab is illustrative. Schedules are hypothetical and say nothing about SPHEREx availability or instrument performance.
- **Challenges come from a fixed rule set.** ASL-1 checks the documented rules (H, M, E, Q, S, B, R and A families) and nothing
  else. A missing challenge does not mean the analysis is free of problems. Severity is per rule, not a measure of importance in
  context. Acknowledging a challenge records your note; it does not resolve the challenge.
- **No information gain is computed.** HYPO-1 statuses are rules, not probabilities, so INFO-1 orders tests by feasibility and by
  the explanations they bear on. The order is a convention.
- **The causality workbench does not test causation.** It lists data-flow dependencies (model-derived), competing explanations
  (assumption-based) and your proposals (user-proposed). It does not check temporal order, compare causal models or draw causal
  diagrams.
- **The reproducibility verdict is local.** "Reproduced" means re-executed here with an identical content hash. It says nothing
  about another machine or platform. In the static preview only the default run's replay is recorded.
- **Review Room roles are rule sets.** The five reviewers apply fixed checks. They do not read prose for meaning, beyond flagging a
  fixed list of causal or discovery words in your notes.
- **Twins are records.** A twin is a hashed computational record, not a physical model. Twins are version 1 only: there is no
  twin history and no restoring the application from a twin. Observation twins exist in the Python API but are not shown in the
  interface.
- **The autopilot is the planner plus permissions.** Objectives match PLAN-1's fixed rules. A failed run stops and is not resumed.
  Batch levels exist in the registry, but the autopilot runs one plan at a time.
- **The atlas is angular.** It shows positions, angular separations, galactic coordinates and a field view. A distance appears only
  from a recorded parallax, labelled as inferred. No physical separation and no 3-D view is computed. There are no footprint maps
  or spatial filters.
- **Knowledge search is exact.** It is multi-word substring matching over stored items. Semantic indexing is BLOCKED because no
  embedding model is reachable.
- **Multi-agent research is BLOCKED.** No model provider is verified. See [MULTI_AGENT_DESIGN.md](MULTI_AGENT_DESIGN.md).
- **The story reports, it does not interpret.** Chapters come from recorded outcomes and statements. It has no figures, no
  hypothesis histories and no slide export.
- **Static preview.** Edited counterfactuals, synthetic scenarios and schedules are refused with a reason. Only prepared ones are
  recorded.
- **Catalogue.** 74 Phase 7 concepts are deferred, 6 blocked and 4 out of scope. See [PHASE7_CATALOGUE.md](PHASE7_CATALOGUE.md).
  Group assignments are the developer's judgement.

## Epistemic layer (v0.8)

- **Synthetic data only, again.** Every Phase 8 result (graphs, compilations, boundaries, stress tests, lineage, models,
  reproductions) was computed on the two synthetic fixtures. None has run on a real SPHEREx observation.
- **The graph is as fine as the record.** EPI-1 builds objects from recorded events. Steps the pipeline does not record as
  separate events (for example the individual pixels of an aperture) are not objects. Statuses come from ten fixed rules about
  origin and method. They say how a statement was produced, not whether it is true.
- **A compilation is not proof.** SCICOMP-1 checks the structure and the documented preconditions it knows about. Its checks are a
  fixed list. Passing them says nothing about calibration systematics, unmodelled physics or anything the record does not contain.
  The wording check (C1) recognises a fixed list of outcome words and negators within four words in the same sentence. Unusual
  phrasing can escape it or trigger it.
- **The debugger recomputes what was recorded.** It does not re-read pixels. A breakpoint whose stage records decisions but no
  separate result shows its events only. Differential debugging in the server needs two runs attached to your session; the static
  preview compares its recorded runs.
- **Boundaries and stress tests are rule sets.** The four regions follow rules B1–B4 and the ten stress modes follow one rule each.
  A claim with no failing mode is not thereby correct. "Not tested" means exactly that.
- **Negative space and blindspots cover what is defined.** NEG-1 lists failures the record and your session contain. BLIND-1
  counts eleven defined checks; an investigation can have blindspots outside them. No completeness percentage is computed.
- **The method genome describes; it does not validate.** Known-answer tests check the software against generated truth. Health
  reports whether those tests are defined, not whether the method is right for real SPHEREx data.
- **Uncertainty flow shows what the methods propagate.** Calibration systematics, PSF model error, reference-star variability and
  parameter sensitivity are listed as not propagated. No combined error budget is computed.
- **Model arena is two models.** It compares a static and a linear motion model per axis, assuming independent Gaussian errors.
  You cannot register your own model. There are no brightness models. AIC differences are reported without significance levels.
- **FutureLab is hypothetical.** The slope-error formula assumes white, independent errors at the recorded precision. It is used
  only after it reproduces the recorded σ. Scenarios say nothing about SPHEREx scheduling.
- **Reproduction is local.** "Exact reproduction" means re-executed here with identical outputs and a record whose hash
  recomputes. Dependency comparison covers recorded versions, not a full package lock.
- **The integrity firewall is advice.** Its twelve checks match numbers against recorded values at the precision written, and words
  against fixed lists. It cannot tell a misleading sentence built from true numbers. It never blocks an export or edits text.
- **The evidence vault is tamper-evident, not tamper-proof.** Anyone who rewrites an entry and recomputes every later link can hide
  the edit. Entries trimmed by the history limit are gone; the first remaining entry is reported as unverifiable.
- **Protocols and blinding are local discipline.** A lock is a content hash and a time in your session, not an external registry,
  and it is not preregistration. A lock made after results were visible is labelled so. Blind analysis hides outcomes in the
  interface. The record and the server still contain them, so it guards against accidental viewing, not against deliberate access.
- **The Reasoning Lab checks form, not truth.** Validity means every step has premises and a rule from the fixed list. Empirical
  standing repeats the statuses of the linked objects.
- **The review board is automated.** Its eight perspectives regroup compiler checks, stress results, the report check and the
  genome. It is not peer review, and there are no reviewer accounts.
- **The copilot does not use the epistemic report.** Its sixteen tools are unchanged.
- **Static preview.** Lineage for results other than the claims and the motion fit, reproduction of runs other than the default,
  and audits of other scenarios are refused with a reason.
- **Catalogue.** 79 Phase 8 concepts are deferred, 1 blocked and 5 out of scope. See [PHASE8_CATALOGUE.md](PHASE8_CATALOGUE.md).

## Scientific intelligence layer (v0.9)

- **Synthetic data only, still.** Every Phase 9 result (memory, genomes, the unknown map, the ledger, the gate, causal criteria,
  oracle plans, network relations, reproduction comparisons, what-if scenarios) was computed on the two synthetic fixtures. None
  is evidence about the sky, and agreement on generated data does not validate real-data performance.
- **A small corpus.** Memory and the multi-discovery network see only the investigations the server holds: runs made in this
  process and saved records whose bundle exists (the preview records the fixture runs). With two targets, cross-investigation
  relations are exercised but cannot show real patterns. Memory is per installation; nothing is shared between machines or users.
- **Memory statuses are rules.** *Verified* means a recorded value from a record whose content hash recomputes, not that the value is
  right. Explanations are never promoted, however often they are remembered as consistent. Recall uses a fixed vocabulary of
  concepts; a word outside it is matched only literally. No embeddings are used (no verified provider).
- **Genomes and network relations are structural.** A genome comparison lists shared fields; a network edge needs one of nine
  rules. Neither says two sources are physically alike, and there is no similarity score.
- **The unknown map is a map of defined rules.** It places items the record and the reports contain. Unknowns no rule describes are
  not on it, and no completeness percentage is computed. *Unexplored parameter regions* use the documented ranges of the analysis
  parameters, not physical parameter space.
- **The adversary raises what its rules raise.** Absence of a challenge is not support. Severity is fixed per rule.
- **The gate is a checklist.** *Ready to mark complete* means its eight requirements are met. It is not peer review and does not mean
  the conclusions are true. Three requirements (reproducibility, wording, challenges examined) need your action in the session.
- **The causal graph is an assumption.** It documents how the measurement process is believed to work; it was not learned and is
  not tested. C5 (experimentally supported) is never met, because archival data allow no intervention on the sky. Interventions
  listed are re-analyses.
- **The oracle plans under one model.** Plans are evaluated under the measurement model that reproduces the recorded fit (white,
  independent errors). Information gain in bits is not computed, because no defensible prior exists. Plans are hypothetical; Skytrace
  has no telescope or survey-scheduling integration.
- **What-if answers only where a method exists.** W3 (background model) has no valid method here; W4 and W5 are routed to the
  instrumental check and the hypotheses rather than recomputed. Hypothetical visits are labelled and never stored as observations.
- **The fingerprint, the instrumental check and the budget cover what they list.** Six dimensions, nine checks and three classes.
  Ruling out every listed instrumental explanation does not make a signal astrophysical. No total error budget is computed while
  effects remain unquantified.
- **Bounded autonomy is local and small.** The research cycle proposes and runs only registered actions in the browser, with the
  permission classes inspect and analysis. It cannot stop a running step part-way, has no step or time budget, and has no
  scheduler: nothing runs when the page is closed.
- **Time capsules, handoffs and knowledge packages are exports.** A capsule's digest makes later edits detectable; it is not a
  signature. There is no importer that validates a knowledge package or a capsule yet. A handoff is a Markdown file; there is no
  live collaboration.
- **The copilot does not read the intelligence report.** Its sixteen tools are unchanged.
- **Catalogue.** Of 600 Phase 9 concepts, 286 are implemented and tested (most from earlier phases), 114 implementable now but not
  built, 127 need data or infrastructure, and 73 are speculative or out of scope. See [PHASE9_CATALOGUE.md](PHASE9_CATALOGUE.md).

## Six languages and the universal frontier (v0.10)

- **The translations are AI-made and unreviewed.** All five non-English languages were translated by an AI model (Claude). No
  native speaker or astronomer working in those languages has read them. Automated checks (completeness, placeholders, numbers,
  identifiers, script, terminology consistency) cannot judge fluency, idiom or whether a term is the one a community uses.
- **Engine narrative stays in English.** Outcome statements, rule details, reasons and limitations recorded by the engines are
  scientific content and are shown unchanged (marked `lang="en"`) inside translated views and reports. A translated page
  therefore still contains English sentences by design. Text assembled from several separately rendered pieces may stay partly
  in English where no catalogue message covers the whole.
- **Cross-language search is not semantic.** It matches exact text, the 48 TERM-1 terms and their synonyms, and shared word stems.
  A query that uses a word outside the terminology base in another language finds nothing in English text.
- No right-to-left scripts; Hindi uses Western digits (its CLDR default); Bangla digits are the default for Bangla, switchable.
- **Signal Intelligence on the bundled data is mostly refusals.** Every synthetic series has four points, so the periodogram,
  Fourier, wavelet, DCF and change-point methods correctly do not apply and BIC is not reported. The methods are validated on
  generated series with known answers, not on real observations. No false-alarm probability is computed. Photometry series are raw
  (not reference-calibrated) fluxes.
- **Convergence, leads and agents are rule-based over one record.** Independence is judged only by shared exposures and shared
  reference stars; other kinds of dependence (the same calibration pipeline, the same instrument model) are stated, not measured.
  The five agents are rule sets sharing one model of the data: their agreement is not independent confirmation.
- **Novelty is local.** "New to this collection" means no other investigation held here produced the same kind of signal. No
  literature or catalogue index is connected, so nothing is called globally new or underexplored.
- **External sources are not connected.** IRSA releases, Gaia alerts, TNS, ATel, arXiv and ADS are listed with that status. Nothing
  is monitored and no update is shown; "note interest" only records an interest in the session.
- **The director and the marketplace run nothing new.** Executing a director step opens a recorded result; the marketplace
  recommends only items with a known-answer test on synthetic data.
- **The flight recorder is tamper-evident, not immutable.** The VAULT-1 chain has no signature or external anchor.
- **The open science gateway publishes nothing.** It builds a local ZIP; the repository declares no licence, and the checklist
  says so. Handoffs describe recorded work; importing one is not a reproduction.
- **Not built in Phase 10**: semantic search, live monitoring, a literature novelty check, information-gain values, a validated
  physical digital twin, multi-user collaboration. See [PHASE10_AUDIT.md](PHASE10_AUDIT.md).
- **Catalogue.** Of 800 Phase 10 ideas, 372 are implemented and tested (most from earlier phases), 163 implementable now, 177 need
  data or infrastructure, and 88 are speculative or out of scope. See [PHASE10_CATALOGUE.md](PHASE10_CATALOGUE.md).

## Product

- Single-user: no accounts, and saved investigations are visible to anyone who can reach the server.
- Investigations are cached in server memory. A restart forgets unsaved runs, but saved records reopen and replay.
- The evidence guard is heuristic. It checks numbers, dates, wavelengths, identifiers, uncertainties, sources, tool use, causal and certainty wording, and synthetic labelling against tool outputs. It does not understand meaning, so a sentence that combines correct numbers misleadingly can still pass.
- The local assistant answers with fixed templates. It routes questions by keywords (15 intents) and cannot answer arbitrary questions.
