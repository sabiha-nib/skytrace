# Phase 10 methods (v0.10.0)

Every Phase 10 engine reads a finished investigation record and the reports already computed from it. None measures anything new
from images, calls a model or reaches the network, and none produces a probability or a score. Each method has an identifier that
appears in its output. Server: `src/skytrace/sigintel.py`, `src/skytrace/universal.py`, `src/skytrace/handoff.py`,
`src/skytrace/xsearch.py`, `src/skytrace/i18n.py`; API `GET /api/investigations/{iid}/universal` (cached by content hash and the
set of sibling runs); browser `web/js/universalui.js`, `web/js/languagesui.js`, `web/js/xsearch.js`, `web/js/handoff.js`.
Six-language architecture: see [I18N.md](I18N.md).

## SIGNAL-1 — the signal workbench (Signal Intelligence)

**Series.** Only what the record contains, never interpolated, filled or resampled:
- *photometry groups*: APPHOT-1 fluxes of the target on one detector whose wavelengths at the target lie within the WLMATCH-2
  tolerance (half a channel minus 2 nm) of the group's first member. Because each SPHEREx detector sits behind a linear variable
  filter, this is the only way to follow brightness at one wavelength. The fluxes are raw: exposure-level calibration changes are
  removed by PAIRDIFF-2 only pair by pair, not in a series;
- *astrometry*: the visit-averaged ξ and η offsets (LINFIT-EPOCH-1) with their errors.

**Method selection is part of the result.** Every method is listed for every series as applicable or not, with the reason:

| Method | Applies when | Assumptions | Limits |
|---|---|---|---|
| Sampling diagnostics | N ≥ 2 | recorded mid-exposure or visit-mean times | describes when, not what happened between |
| Spectral window | N ≥ 3 | sampling times only | a peak where the window is high can come from the sampling |
| Noise model check | stated errors | independent Gaussian errors | χ² of a constant tests errors and model together |
| Generalised Lomb–Scargle (Zechmeister & Kürster 2009) | N ≥ 12 | one sinusoid + constant, Gaussian errors | **no false-alarm probability is computed**; only periods between the span and 0.5/median spacing are tested |
| Discrete Fourier transform | N ≥ 8 and uniform sampling (cadence CV < 0.1) | uniform sampling | with uneven sampling it mixes signal and window |
| Haar wavelet | N ≥ 8 and uniform sampling | power-of-two prefix (truncated, never padded) | energy by scale, no significance; no known-answer test (marked unvalidated) |
| Discrete correlation function (Edelson & Krolik 1988) | N ≥ 6 and scatter above the errors | stationarity | sparse lag bins are noisy; pair counts shown |
| Robust trend (Theil–Sen, beside weighted least squares) | N ≥ 3 | monotonic linear trend | a trend says nothing about what happened between observations |
| Single change point | N ≥ 6 (≥ 3 per segment) | two constant levels | one change point, located only between observations |
| Model comparison | N ≥ 3 | Gaussian errors, nested models | **BIC is shown only if N > k + 2 for every model and the best model's reduced χ² is in [0.5, 2]**; never a single ranking |

A Lomb–Scargle peak is called a *periodicity candidate* only if its power is ≥ 0.5 and the spectral window there is ≤ 0.5. The
frequency grid spans 1/span to 0.5/median spacing with spacing 1/(5·span), at most 2,000 frequencies; for uneven sampling the
upper limit is a heuristic, not a Nyquist frequency.

With the bundled synthetic data every series has four points, so the periodogram, Fourier, wavelet, DCF and change-point methods
correctly decline, and BIC is not reported. Known answers (tests/unit/test_phase10.py): a 23-day sinusoid sampled unevenly is
recovered to 0.5 d; Theil–Sen ignores a wild point that pulls least squares; a step between samples 9 and 10 is located; the DCF
of a sinusoid is positive at short lags and negative near half a period; the window of uniform sampling is 1 at multiples of the
sampling frequency and 0 between; BIC favours the linear model on linear data and is withheld when errors are understated.

## WORLD-1 — the world model

Nodes: the target, observations, detectors, measurements, outcomes, methods and hypotheses. Relations: *observes*, *taken with*,
*measured in*, *compared with* (WLMATCH-2 pairs), *about*, *decided with*, *consistent so far with* / *contradicted by* / *not
decided by* (HYPO-1 overall status). Every edge carries its basis: the rule and the recorded field it comes from. A structured
query filters by source kind, relation, target kind and exact text (Python `world_query`, browser `worldQuery`). No physical
relationship between objects is inferred, and the graph is not a model of the universe.

## CONV-1 — discovery convergence

For a positive variability outcome the significant reference-calibrated pairs (|z_cal| ≥ 5) are grouped so that pairs sharing an
exposure fall in one group (union–find); only groups that share no exposure count as independent lines. Groups that share
reference stars share their calibration, and all lines share one method (APPHOT-1 + PAIRDIFF-2) — both are stated. Motion rests
on one fit. Other runs of the same target reuse the same data bundle: their agreement shows stability under parameter choices and
is never counted as independent confirmation.

## LEAD-1 — contradictions as research leads

Rules: PAIRDIFF-1 and PAIRDIFF-2 on opposite sides of |z| = 5 for a pair; exposure-level and visit-level proper motions differing
by more than 3√(σ₁² + σ₂²) on an axis; the measured motion more than 3σ from the catalogue; a hypothesis with both consistent and
contradicting tests. Each lead lists its evidence, the kinds of resolution still open and the rule. A lead is not a paradox.

## NEGX-1 — negative space in nine distinctions

Measured absence (an outcome bounded by its sensitivity), non-detection (S/N < 5), missing measurement, unavailable dataset,
failed method, insufficient sensitivity, unexplored region (wavelength gaps > 0.25 µm within 0.75–5.0 µm; time gaps > 60 d),
unresolved explanation (HYPO-1 inconclusive or untested), unknown quantity (parallax not measured here; the time of any physical
change). Items come from the outcomes, the measurements, NEG-1 entries (mapped by category) and the environment. Each states what
it does **not** mean; a non-detection never proves that something does not exist. Shown inside the existing Negative Space
workspace.

## MODAL-1 — one representation for every measurement

Rows: modality, quantity, unit, time, wavelength, detector, value, error, source, method — photometry (µJy), astrometry (ξ, η in
mas), spectrum points (µJy at λ) and image counts. Compatibility rules: photometry only with wavelength-matched photometry;
spectrum points are photometry seen another way (not independent); photometry and astrometry are compared only by time alignment,
never by value; images by registration and visual inspection, never as physical similarity.

## OPP-2 — research opportunities with novelty scope

The Discovery Radar's opportunities (RADAR-1) in ten fields — question, motivation, evidence, data needed, method, expected
output, what it cannot establish, feasibility, dependencies, novelty — with a novelty scope that never exceeds what Skytrace can
know: *new to this collection* when no other investigation held here produced the same kind of signal, otherwise *new to this
investigation*. *Underexplored in indexed sources* and *independently verified* are "not evaluated": no literature index is
connected and only an outside reproduction could establish them.

## KCOMP-1 — knowledge-compiler statuses

SCICOMP-1's ten stages mapped to Passed / Passed with warnings / Incomplete / Failed / Not evaluated: no executed check → Not
evaluated; any failed check → Failed; only checks that ask for review → Incomplete; any warning → Passed with warnings; otherwise
Passed. Passing means the defined checks were satisfied; it does not prove a conclusion. Shown in the Scientific Compiler.

## EXTSRC-1 — external sources

IRSA SPHEREx releases, Gaia Science Alerts, the Transient Name Server, ATel, arXiv astro-ph and NASA ADS are registered with their
provider and shown as **not connected**, with the reason (this environment cannot reach external services; no connector is
implemented). No monitoring runs and no update is ever shown. Researchers can note an interest in a source; the interest is stored
in the session (`monitors`) and nothing is contacted.

## AGENTS-1 — role agents and their debate

Observer, Skeptic, Methodologist, Statistician and Archivist are five rule sets reading the same record. For each outcome they post
a claim, challenges (convergence dependencies, open research leads, limitations), qualifications (method applicability, BIC
assumption checks) and provenance, each citing what it rests on. A round stays open while a lead is open or fewer than two
exposure-independent lines support a positive outcome. The agents share one model of the data, the same data and the same
assumptions: their agreement is not independent confirmation, and no agent is a person. The debate can be recorded in the session
(`debates`). Shown in Review & Story.

## EXPLAIN-1 — explanations in eight layers

For each outcome: what was observed, what was measured, how (methods in order), what was compared, the result, how certain
(thresholds, sensitivities, criteria — none a probability), what else could explain it (HYPO-1 hypotheses with their statuses), and
what it does not mean (recorded limitations). Wording is a keyed message with parameters (`explain.*`) translated into six
languages; values and engine statements are shown unchanged in English and marked as such.

## TIMES-1 — the discovery timeline

Four lanes never merged: observation (mid-exposure times, UTC), processing (when the record was computed), publication (retrieval
times and release identifiers; release dates are not recorded) and event (when a physical change happened — *not determined*:
observation times bound when a change was seen, not when it happened).

## DIRECT-1 — the investigation director

A proposed plan ordered by a fixed rule — data quality, research leads, the highest-ranked runnable opportunity, method
applicability, unresolved explanations, compilation, handoff — each step with its reason and the workspace that holds its result.
Starting a run records it in the session (`director`) with an audit log; each step must be approved before it can be executed, and
executing opens the recorded result. The director never acquires data, changes a record or publishes. Shown in Research Autopilot.

## EXPMKT-1 — the experiment marketplace

A catalogue (not a store) of experiment templates and signal methods. An item is shown as recommended only when a named test
checks it against a known answer (the test file and function are cited and checked to exist); others are listed as "available, not
recommended". Validation is on synthetic data, not on real observations, and says so.

## HANDOFF-1 — the discovery handoff protocol

Schema `skytrace.handoff/1`, version 1.0: `schema, version, created_at, generator, language {interface, content: "en",
translation {status, translator, reviewed}}, investigation {target, content_hash, synthetic, record_schema}, established, open,
unknown, evidence_needed, provenance, limitations, reproduction {content_hash, parameters, instruction}, note, digest`. `digest` is
the SKY-CANON-1 SHA-256 of the document without it. Validation refuses: another schema, unknown versions, missing or extra fields,
wrong types, an invalid time, unknown languages, content not in English, a missing translation status, a malformed content hash,
synthetic provenance without the synthetic label, more than 200 items in a list, a reproduction hash that differs from the
investigation's, and a digest that does not recompute. An imported handoff describes recorded work; it is not a reproduction and
implies no live collaboration. Python and browser implementations are parity-tested.

## FLIGHT-1 — the research flight recorder

Replays a session's append-only history event by event (slider and playback), with counts by kind of activity and the VAULT-1
chain verification (links verified, broken links, older unchained entries). Tamper-evident, not cryptographically immutable: there
is no signature and no external anchor, and whoever holds the file can rewrite the whole chain.

## OSG-1 — the open science gateway

A checklist (content hash, checksums, archive URLs, synthetic label, stated limitations, machine-readable handoff, declared
licence) and a ZIP bundle: README, record, the report in English and in the interface language, the handoff and the checklist.
Nothing is published, uploaded or sent. The repository declares no licence, and the checklist says so.
