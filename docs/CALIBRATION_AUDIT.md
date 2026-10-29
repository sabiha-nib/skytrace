# Calibration and uncertainty audit (Phase 3)

Status: **synthetic validation only.** No real SPHEREx product has been processed in this
environment (Gate B blocked; see `docs/ENVIRONMENT_REPORT.md`). Each item below says what was
changed, how it was tested, and what remains unverified against real data.

Classification used:

| Class | Meaning |
|---|---|
| **C — correctness-critical** | a wrong result is likely without it; must be fixed before any real-data claim |
| **R — required for the claim** | needed before the specific claim (motion vs catalogue, variability) can be stated |
| **D — desirable** | improves precision or diagnostics; results are valid without it if the limitation is stated |
| **A — acceptable** | the effect cancels or is far below the error budget; documented only |

## Summary

| # | Effect | Class | Status in v0.3 | Method ID |
|---|---|---|---|---|
| 1 | Annual parallax of target and references | C (for catalogue comparison) | **Fixed**: apparent positions; target parallax removed before the motion fit | EPHEM-AA-LP-1 |
| 2 | Products not checked against an independent reader | C | **Partly**: native reader validated on independent astropy test files (Gate C); real-file comparison blocked | — |
| 3 | Brightness comparison across releases (QR2 vs QR3) | C | **Fixed**: refused by default, reason `different_releases` | WLMATCH-2 |
| 4 | Wavelength-solution accuracy (~1 nm) at the match boundary | R | **Fixed**: 2 nm margin; pairs inside it rejected as `wavelength_ambiguous` | WLMATCH-2 |
| 5 | Exposure-to-exposure calibration change | R | **Fixed**: reference-normalised flux ratio (≥ 3 matched references) | PAIRDIFF-2 |
| 6 | Error model for photometry | R | **Checked**: scatter of constant reference stars; errors scaled when it exceeds 1.5 | CALCHECK-1 |
| 7 | Correlated astrometric errors within one visit | R | **Fixed**: visit-averaged epochs with empirical error floor; per-exposure fit kept as cross-check | LINFIT-EPOCH-1 |
| 8 | Poor reference-star astrometry (binaries, duplicates, 2-p solutions) | R | **Fixed**: RUWE ≤ 1.4, not duplicated, 5/6-parameter solution; missing flags counted | REFSEL-2 |
| 9 | Catalogue proper-motion uncertainty | R | **Fixed**: included in the measured − catalogue significance | — |
| 10 | Aperture correction | A for matched pairs / D for spectra | Documented; spectrum labelled "not aperture-corrected" | APPHOT-1 |
| 11 | Gaussian PSF model for centroids | D | Documented; 0.02 px floor added to every centroid error | CENTROID-G2D-1 |
| 12 | Chromatic PSF / distortion between detectors | D | Documented; per-detector residual diagnostic planned | — |
| 13 | Aberration, light deflection | A | Common to the 0.1° field; cancel in differential astrometry | — |
| 14 | Barycentric vs heliocentric observer | A | ≤ 0.01 × parallax; recorded as a systematic bound with every motion result | EPHEM-AA-LP-1 |

## Details

### 1. Parallax (C)

Barnard's Star has ϖ = 547 mas; WISE 0855 ≈ 439 mas; ε Ind B ≈ 270 mas. Over SPHEREx's
six-month survey cadence the annual parallax displaces the target by up to 2ϖ ≈ 1.1″ (0.18 px)
— comparable to a year of proper motion for slower targets and not separable from it with
two or three epochs. Version 1 left this as a "systematic bound". Version 2:

* computes Earth's position from the Astronomical Almanac low-precision solar coordinates
  (`science/ephemeris.py`), validated in `tests/unit/test_ephemeris.py` against the published
  2026 perihelion/aphelion distances (tolerance 2×10⁻⁴ AU) and the 2026 March-equinox time
  (solar longitude within 0.02°), and against the geometric parallax ellipse (radius and
  obliquity split);
* places target **and** reference stars at their apparent positions for each exposure
  (references use their Gaia parallax);
* subtracts the target's parallax displacement from its measured tangent-plane position before
  the motion fit, so the fitted rate is comparable to the catalogue proper motion.

Remaining systematic: ≤ 0.01ϖ (Sun–barycentre offset), e.g. ≤ 5.5 mas for Barnard's Star,
recorded as `parallax.systematic_bound_mas`. SPHEREx single-exposure errors are hundreds of mas.

### 3–4. Releases and wavelength accuracy (C, R)

The IRSA SIA pre-check (model-mediated, unverified) indicated that multi-epoch coverage of the five
targets currently requires QR2 (processing l2b-v24) and QR3 (l2b-v27) together. Their
flux calibrations are not guaranteed identical, so a brightness change between releases could
be a processing change. WLMATCH-2 refuses such pairs by default (`photometry_same_release`,
override available and recorded). Astrometry may use both releases (positions are tied to Gaia
in every exposure independently).

IRSA states the WCS-WAVE wavelength lookup is accurate to about 1 nm. A pair whose |Δλ| sits within
2 nm of the half-channel limit could fall on either side, so it is rejected with code
`wavelength_ambiguous` rather than accepted.

### 5–6. Differential calibration and error-model check (R)

PAIRDIFF-1 compares the target's flux in two exposures using only per-pixel variance. Any
exposure-level calibration change (gain, zodiacal-light residual, aperture loss from PSF
change) appears as variability. PAIRDIFF-2 measures isolated reference stars (no catalogue
source within 7.5 px) in both exposures, keeps only those that are themselves
wavelength-matched under the same rule and have S/N ≥ 10, and divides the target's ratio by
their median ratio *m* (uncertainty 1.2533 × 1.4826 MAD/√n). At least 3 references are
required; otherwise the pair is marked `calibrated: false` and only PAIRDIFF-1 is available.

CALCHECK-1 uses the leave-one-out normalised differences of the reference stars themselves. If
the stated errors are right, their robust scatter is ≈ 1. Requires ≥ 10 reference comparisons.

**Finding on synthetic data.** For `syn-hpm-1` the scatter is 1.05 (status `ok`). For
`syn-var-1` it is 1.56 (status `underestimated`), so its calibrated z values are divided by 1.56.
Tightening the wavelength tolerance from 0.5 to 0.15 channel reduced it only to 1.36, so the
reference stars' spectral slope within a channel is not the main cause. The leading hypothesis
(not yet isolated) is sub-pixel-phase-dependent aperture loss: the synthetic PSF is
point-sampled and undersampled (σ = 0.67–1.27 px) and the aperture is 2 px, so bright stars
show percent-level aperture-fraction changes between exposures. Real SPHEREx PSFs are also
undersampled, so the same effect is expected on real data. This is exactly the case CALCHECK
exists for: the error scale is applied automatically and recorded.

### 7. Correlated astrometric errors (R)

Exposures within one visit share reference stars, detector region and PSF; their errors are
not independent, and a per-exposure least-squares fit would shrink σ(pm) by √(exposures per
visit) without justification. LINFIT-EPOCH-1 groups exposures into visits (new visit after a
gap > `epoch_gap_days`, default 3 d), averages each visit with error = max(formal, empirical
scatter/√n) (empirical term for n ≥ 3), and fits the visit means. The per-exposure fit is
recorded as `exposure_fit` for comparison. With a single visit the per-exposure fit is
used and labelled. Test: `test_epoch_fit_does_not_shrink_correlated_errors` injects a
200 mas per-visit offset; the epoch fit covers the true zero motion within 3σ.

### 8. Reference-star quality (R)

REFSEL-2 at the catalogue level (RUWE ≤ 1.4 after Lindegren et al. 2021; `duplicated_source`
false; `astrometric_params_solved` ≥ 31). Stars failing the cut are **still masked as neighbours**
when fitting other stars; they are only excluded from the plate solution. Bundles made before
v0.3 lack these columns; such stars are accepted and counted under `accepted_unchecked`.
Existing per-exposure checks (REFSEL-1: isolation, PSF fit χ², distance from catalogue position)
are unchanged.

### 10–12. Acceptable and desirable items

* **Aperture correction.** In a wavelength-matched pair the same detector, wavelength and
  aperture apply, so the aperture correction cancels to first order; the residual sub-pixel
  term is what CALCHECK measures. Spectra are labelled "not aperture-corrected" and are not
  used for absolute-flux claims.
* **PSF model.** Centroids use a 2-D Gaussian. A 0.02 px floor is added to every centroid
  error. Using the PSF extension of the product is desirable but not required.
* **Chromatic effects.** Different detectors image the field at different wavelengths;
  residual chromatic distortion is absorbed per exposure by the plate solution (references
  are at the same wavelength as the target in each exposure). A per-detector residual
  diagnostic is planned.

## Not verified (blocked)

All of the above has been exercised on synthetic fixtures and unit tests only. On real data
it remains to verify: (a) the IRSA flag bits and VARIANCE semantics in real l2b-v24/v27 headers;
(b) the reference-star count after REFSEL-2 in each 0.1° cutout; (c) the CALCHECK scatter;
(d) the per-visit structure of SPHEREx coverage for each target.
