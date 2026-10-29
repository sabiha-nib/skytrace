# Scientific methods

Phase 5 methods that read finished investigations (CAPREG-1, DISC-1, HYPO-1, UNC-1, REGDIAG-1, PKG-1) are in
[DISCOVERY_METHODS.md](DISCOVERY_METHODS.md).

Every method has a version ID. Each ID is written into every result that uses it, so a result always names the exact rule that produced it. Thresholds are fixed constants, not tuned per target. All numbers below come from runs of the code at commit time (see [TEST_REPORT.md](TEST_REPORT.md)).

## Data and coordinates

- **Input:** SPHEREx Level-2 Spectral Images, as IRSA cutouts of 0.1° (58 px at 6.2″/px), one file per detector per pointing. `IMAGE` is calibrated surface brightness in MJy/sr with zodiacal light *not* subtracted; `VARIANCE` is in (MJy/sr)²; `FLAGS` is a bitmap; `WCS-WAVE` backs the spectral WCS.
- **Celestial WCS:** TAN with SIP distortion. astropy is used when installed; otherwise `src/skytrace/wcs.py`.
- **Wavelength at a pixel:** the alternate spectral WCS (key `W`, `-TAB` lookup into `WCS-WAVE`), exactly as in IRSA's tutorial. IRSA describes it as ~1 nm accurate and intended for visualisation; the separate Spectral WCS product (CWAVE/CBAND) is the science-grade reference. The bandwidth is read the same way.
- **Target positions:** catalogue astrometry is propagated to each exposure's mid-time with rigorous linear space motion (ESA 1997, Hipparcos vol. 1, §1.5.5). Gaia DR3 is preferred (matched to SIMBAD by position and proper motion); SIMBAD is the fallback. **Parallax displacement is not applied:** it needs the observer's position per exposure (`coords.parallax_offset_mas` is ready for an ephemeris). Its size is bounded by the catalogue parallax and reported with every motion result.

## Quality flags — FLAGPOL-1

Bit numbers come only from the file's `FLAGS` header (keywords `MP_*` or `BITnn = 'MP_*'`) or from IRSA's documentation (`MP_TRANSIENT` = 0, `MP_SOURCE` = 21). An unknown bit is reported, never guessed. Rejected: transient, overflow, SUR error, non-functional, missing data, hot, cold, persistence, outlier and phantom flags. Warnings only: non-linear, dichroic, full-sample, reference. Informational: source.

## Centroids — CENTROID-G2D-1, NBMASK-1, TGT-1

- Weighted least-squares fit of an elliptical 2-D Gaussian plus a constant to a 9 × 9 stamp. Weights come from `VARIANCE`; pixels rejected by FLAGPOL-1 are excluded. Errors come from the Jacobian, scaled up by the reduced χ² when it exceeds 1, never down.
- **NBMASK-1:** pixels within 2.5 px of any other catalogue source near the star are excluded before fitting. Without this, neighbours 4–6 px away (inside the stamp) inflated χ² and biased fits. This was found on the synthetic data.
- **TGT-1:** the target's fit is confined to ±1.5 px (9.3″) of its catalogue-predicted position, so it cannot wander to a brighter neighbour. Deviations from the catalogue motion up to that size remain measurable. An exposure is used for astrometry only if the target's aperture S/N is ≥ 5 and no catalogue source lies within 3 px. Otherwise it is logged as below S/N or blended.
- A 0.02 px floor is added in quadrature to every centroid error, because a Gaussian only approximates the SPHEREx PSF.
- **Calibration** (synthetic, 150 noise realisations): the pull distribution has mean |μ| < 0.25 and σ in 0.8–1.25 (`test_centroid_uncertainty_is_calibrated`).

## Photometry — APPHOT-1

Circular aperture of 2 px radius, with 10 × 10 sub-pixel sampling at the edge. Local sky is the 3σ-clipped median of an unflagged 4–7 px annulus, which also removes zodiacal light. Flux density = Σ w(I − sky) · Ω_pix. Variance = Σ w² VARIANCE + (Σw)² (π/2) σ_sky² / N_sky. Any rejected or invalid pixel inside the aperture gives NaN with status `flagged`; nothing is measured around the damage. The result is an aperture flux with no aperture correction. Pull test over 100 realisations: mean |μ| < 0.3, σ in 0.75–1.3.

## Phase 3 methods (v0.3) — summary

v0.3 (`skytrace-analysis/2`) keeps the methods below and adds or supersedes, each recorded in every result's
`parameters.methods` (details and tests in [CALIBRATION_AUDIT.md](CALIBRATION_AUDIT.md) and
[ASSESSMENT_ENGINE.md](ASSESSMENT_ENGINE.md)):

| ID | Replaces | What it does |
|---|---|---|
| EPHEM-AA-LP-1 | — | Earth/SPHEREx position from the Astronomical Almanac low-precision Sun; annual parallax applied to target and references; target parallax removed before the motion fit (residual ≤ 0.01ϖ) |
| REFSEL-2 | adds to REFSEL-1 | catalogue cut: RUWE ≤ 1.4, not `duplicated_source`, 5/6-parameter solution; rejected stars are still masked as neighbours |
| WLMATCH-2 | WLMATCH-1 | adds a 2 nm wavelength-accuracy margin (`wavelength_ambiguous`) and same-release photometry by default (`different_releases`); structured reason codes |
| PAIRDIFF-2 | complements PAIRDIFF-1 | divides by the median flux ratio of ≥ 3 wavelength-matched reference stars measured in the same two exposures |
| CALCHECK-1 | — | robust scatter of the reference stars' normalised differences; errors scaled when > 1.5 |
| LINFIT-EPOCH-1 | primary instead of LINFIT-LOO-1 | visit-averaged positions with an empirical error floor, so correlated errors within a visit are not counted as independent; the per-exposure fit is kept as a cross-check |
| ASSESS-2 | ASSESS-1 | adds sensitivity to every outcome, separates non-detection, failure and calibration-limited cases |
| STAB-1, PROVCHECK-1 | — | perturbation stability; provenance verification of a record against its bundle |

## Wavelength matching — WLMATCH-1 (superseded by WLMATCH-2)

Two exposures can be compared for brightness only if they come from the same detector, |λ₁ − λ₂| ≤ 0.5 × min(bandwidth₁, bandwidth₂), and both measurements are usable. Every pair is evaluated, and every rejection keeps a categorised reason (different detectors, wavelength mismatch, unusable measurement…).

## Flux comparison — PAIRDIFF-1

For an accepted pair: Δ = f₂ − f₁, σ = √(σ₁² + σ₂²), z = Δ/σ. z is the significance of a difference under the stated errors. It is **not** a probability that the source varies, and it is not a classification. Same-detector pairs at different wavelengths are kept separately as "spectral context" and are never used as variability evidence.

## Differential astrometry — REFSEL-1, PLATE-LOO-1, LINFIT-LOO-1

1. **REFSEL-1** (per exposure): Gaia DR3 stars with G 10–17.5, propagated to the exposure epoch. A star is used only if it is inside the cutout, has no other catalogue source within 3 px, its fit converges with χ²ν ≤ 3, and the fit lands within 2 px of the catalogue position. Rejection counts by reason are logged.
2. **PLATE-LOO-1:** a weighted 6-parameter affine map from pixel to tangent plane (fixed tangent point: the target at the median epoch), requiring at least 6 references. Outliers are removed one at a time by **leave-one-out** testing: the worst star is compared with the solution fitted *without* it and dropped above 4σ. Simple median-based clipping failed on the synthetic data, because a single bad reference dragged the fit enough to hide itself. The plate is solved whenever references exist, independent of the target, and is reused to register images for display.
3. The target centroid goes through the plate, propagating both centroid and plate covariance.
4. **LINFIT-LOO-1:** weighted linear fit of position against time per axis, with leave-one-out epoch rejection at 4σ. Errors are scaled up by √χ²ν when it exceeds 1.
5. The result is compared with the catalogue proper motion per axis. The tangent-plane axes approximate (μα*, μδ) near the tangent point.

## Assessment — ASSESS-1 (superseded by ASSESS-2, see ASSESSMENT_ENGINE.md)

| Question | Outcome categories and criteria |
|---|---|
| Data quality | `instrumental` if > 50 % of exposures are unusable; `partially_usable` if some are; `insufficient_evidence` if none could be measured |
| Motion | detection needs \|μ\|/σ ≥ 5. Consistent with the catalogue within 3σ per axis → `motion_detected`; otherwise → `motion_inconsistent`, or `registration_limited` if the median plate residual ≥ the expected shift between epochs. No detection: `no_significant_change` (catalogue motion < 3σ sensitivity, or a well-registered null) or `registration_limited`. Fewer than 2 plate-solved epochs → `insufficient_evidence` |
| Brightness | `variability_candidate` if any matched pair has \|z\| ≥ 5; `spectral_difference_only` if large differences occur only between unmatched wavelengths; `insufficient_evidence` with no matched pair; otherwise `no_significant_change` |

Outcomes carry their evidence numbers, criteria and limitations. The interface adds a fixed list of alternative explanations to consider for each category. That list is guidance, not computed results.

## Validation on synthetic data with known truth

> v0.3 results (analysis/2) on the same fixtures: SYN-HPM-1 (3325 ± 344, −3469 ± 307) mas/yr from 4 visit-averaged
> epochs, `motion_detected`; SYN-VAR-1 `no_motion_at_sensitivity` (5σ ≈ 492 mas/yr) and `variability_candidate`
> with reference-calibrated max |z| 8.86 after the CALCHECK scale of 1.56. The table below is the v0.2 run, kept for
> comparison; the per-exposure errors in it were optimistic because correlated errors within a visit were treated as
> independent. Further variants are in TEST_REPORT.md ("Robustness results").

These are software tests, not astronomical results. The generator ([scripts/make_synthetic_fixtures.py](../scripts/make_synthetic_fixtures.py)) writes SPHEREx-layout files: TAN-SIP celestial WCS, `-TAB` spectral WCS with an illustrative LVF gradient, PSF widening with wavelength, hot pixels, one reference star deliberately offset by 4″ in RA (≈ 3.5″ on the sky), one file without `WCS-WAVE`, one overflow-flagged core. Four passes of two visits each, six detectors: 48 files per target.

| Check | SYN-HPM-1 (truth: μ = 3200, −3400 mas/yr; constant flux) | SYN-VAR-1 (truth: μ = 3, −27 mas/yr; flux × 1.0, 1.0, 0.62, 0.8 by pass) |
|---|---|---|
| Measured proper motion | (3228 ± 124, −3525 ± 127) mas/yr; z = 0.22, −0.99; 40 exposures, 0 rejected, χ²ν 1.53 | (−86 ± 81, 17 ± 81) mas/yr; z = −1.09, 0.54 |
| Motion outcome | `motion_detected` ✓ | `no_significant_change` ✓ |
| Matched pairs | 43 of 1128 | 46 of 1128 |
| Pairs within a pass (truth: no change) | max \|z\| 3.14 (21 pairs) | max \|z\| 1.85 (22 pairs) |
| Brightness outcome | `spectral_difference_only` ✓ (unmatched pairs up to \|z\| 7.5) | `variability_candidate` ✓ (21 pairs ≥ 5; up to \|z\| 12.2) |
| Injected defects | missing WCS-WAVE → `no wavelength` ✓; hot pixels in aperture → `flagged` | overflow core → `flagged` (9 px) ✓ |
| Offset reference star | rejected in 16 plates, **used in 8** (long-wavelength detectors) | rejected in all 48 plates |
| Median plate residual | 301 mas (D1 181 → D6 762) | 536 mas (D1 212 → D6 1672) |

**What this shows:** the chain from FITS file to outcome works, and it recovers injected motion and dimming without false variability between unchanged epochs. **What it does not show:** that it works on real SPHEREx data. The synthetic PSF, noise, LVF and flag layout are illustrative choices, and the native reader agrees with the generator by construction. Real-data validation requires running `pytest -m live` and analysing a real bundle.

**Known weakness:** a reference star with a 0.5 px catalogue error is not always rejected in low-S/N, long-wavelength exposures. Its effect on the motion here is within the stated errors. v0.3 adds the Gaia RUWE cut (REFSEL-2), which removes such stars when the catalogue flags them; a catalogue error without a quality flag is still caught only by the per-exposure leave-one-out test.
