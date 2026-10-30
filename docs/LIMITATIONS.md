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

## Product

- Single-user: no accounts, and saved investigations are visible to anyone who can reach the server.
- Investigations are cached in server memory. A restart forgets unsaved runs, but saved records reopen and replay.
- The evidence guard is heuristic. It checks numbers, dates, wavelengths, identifiers, uncertainties, sources, tool use, causal and certainty wording, and synthetic labelling against tool outputs. It does not understand meaning, so a sentence that combines correct numbers misleadingly can still pass.
- The local assistant answers with fixed templates. It routes questions by keywords (15 intents) and cannot answer arbitrary questions.
