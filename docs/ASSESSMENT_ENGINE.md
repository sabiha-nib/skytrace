# Assessment engine (ASSESS-2)

Source: `src/skytrace/science/assess.py`. Tests: `tests/unit/test_assess2.py`, `tests/unit/test_offline_workflow.py`.

The assessment turns logged measurements into one outcome per question (motion, variability,
data quality). It is deterministic, takes no model input, and every outcome carries:

| Field | Content |
|---|---|
| `category` | one of the fixed categories below |
| `statement` | one plain sentence; non-detections always say they are not proof |
| `evidence` | the numbers the decision was made from |
| `criteria` | the rules, with thresholds |
| `inputs` | what was fed in (exposure counts, fit kind, catalogue source) |
| `sensitivity` | 5σ minimum detectable motion or fractional brightness change for this data set |
| `limitations` | the open systematics relevant to this outcome |
| `rules`, `threshold_provenance` | `ASSESS-2`; where the thresholds come from |

## Two rules that the categories enforce

1. **A non-detection is not proof of a static or constant source.** It is reported as
   `no_motion_at_sensitivity` / `no_variability_at_sensitivity` together with the smallest change
   that would have been detected.
2. **A failed measurement is not evidence of no motion.** A fit that fails with enough data is
   `measurement_failed`, never folded into a non-detection.

## Thresholds and their provenance

| Threshold | Value | Origin |
|---|---|---|
| detection | \|pm\|/σ ≥ 5, \|z\| ≥ 5 | Phase 1 design (ASSESS-1), fixed before data; conventional for many trials |
| catalogue consistency | ≤ 3σ per axis | Phase 1; used only for agreement with an external value |
| registration | median plate RMS < 1 × expected shift between visits | Phase 1 |
| minimum exposures for motion | 2 with usable target position and plate | Phase 1 |
| unreliable error model | CALCHECK scatter > 3 | new in ASSESS-2, set before running on any data |
| instrumental | > 50 % of exposures unusable for both photometry and astrometry | Phase 1 |

None are tuned per target. Changing any of them changes the `rules` ID.

## Motion

Inputs: the primary fit (LINFIT-EPOCH-1 when ≥ 2 visits, otherwise the per-exposure fit, labelled),
the measured − catalogue comparison including catalogue errors, plate residuals, gaps between visits.

σ(pm) along the motion direction: σ = √((σξ·μξ)² + (ση·μη)²)/|μ|. Sensitivity:
5·√((σξ² + ση²)/2).

| Order | Condition | Category |
|---|---|---|
| 1 | no fit, < 2 usable exposures | `insufficient_evidence` |
| 2 | no fit, ≥ 2 usable exposures, fit error recorded | `measurement_failed` |
| 3 | \|pm\|/σ < 5, catalogue motion ≥ sensitivity and inconsistent at 3σ, registration RMS ≥ expected shift | `registration_limited` |
| 4 | as 3 but registration adequate | `motion_inconsistent` |
| 5 | \|pm\|/σ < 5 otherwise | `no_motion_at_sensitivity` |
| 6 | \|pm\|/σ ≥ 5, consistent with catalogue | `motion_detected` |
| 7 | \|pm\|/σ ≥ 5, inconsistent, registration RMS ≥ expected shift | `registration_limited` |
| 8 | \|pm\|/σ ≥ 5, inconsistent | `motion_inconsistent` |

## Variability

Each matched pair contributes one significance: the PAIRDIFF-2 (reference-calibrated) z when ≥ 3
wavelength-matched reference stars exist, otherwise the PAIRDIFF-1 z marked uncalibrated. Both are
divided by the CALCHECK error scale (≥ 1) when it is known. Sensitivity: 5 × σ/f (σ of the pair difference,
times the CALCHECK scale), reported for a typical (median) pair and for the most sensitive pair. A change
can therefore be detected in the best pairs even when it is below the typical-pair sensitivity.

| Order | Condition | Category |
|---|---|---|
| 1 | no matched pair, unmatched-wavelength \|z\| ≥ 5 | `spectral_difference_only` |
| 2 | no matched pair | `insufficient_evidence` |
| 3 | CALCHECK scale > 3 | `calibration_limited` |
| 4 | ≥ 1 calibrated pair with \|z\| ≥ 5 | `variability_candidate` |
| 5 | only uncalibrated pairs reach \|z\| ≥ 5 | `calibration_limited` |
| 6 | no significant matched pair, unmatched \|z\| ≥ 5 | `spectral_difference_only` |
| 7 | otherwise | `no_variability_at_sensitivity` |

`variability_candidate` is never called a discovery; the statement says "not a confirmed physical change".

## Data quality

An exposure counts as rejected only if it is unusable for **both** photometry and astrometry
(it can still contribute to one of them). Reason codes come from `quality_code` / `astro_code`,
never from parsing text. Categories: `all_usable`, `partially_usable`, `instrumental` (> 50 %),
`insufficient_evidence` (no exposure measured).

## Stability (STAB-1)

`POST /api/targets/{id}/stability` (and the "Check stability" button in Discovery Lab → Re-run)
re-runs the analysis with aperture ±0.5 px, wavelength tolerance 0.3 channel and epoch clip 3σ/6σ, and
reports any outcome that changes as fragile. On the synthetic fixtures all three outcomes of both
targets are stable under all five perturbations (recorded in `docs/TEST_REPORT.md`).

## Synthetic results (labelled synthetic)

| Fixture | Injected truth | data_quality | motion | variability |
|---|---|---|---|---|
| syn-hpm-1 | pm (3200, −3400) mas/yr, constant flux | partially_usable | motion_detected | spectral_difference_only |
| syn-var-1 | 38 % dimming, small pm | partially_usable | no_motion_at_sensitivity (5σ ≈ 490 mas/yr) | variability_candidate |
