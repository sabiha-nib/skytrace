"""Deterministic assessment of an investigation (rules ASSESS-1).

Turns measurements into one of a fixed set of outcomes per question, with the
criteria written down here and reported alongside every outcome. Thresholds
are fixed constants chosen before looking at any data; they are not tuned per
target and are recorded in each result.

Outcome categories (the six distinctions SKYTRACE must keep apart):
  motion_detected                 significant motion, consistent with the catalogue
  motion_inconsistent             significant motion that disagrees with the catalogue (systematic suspected)
  registration_limited            apparent position changes not distinguishable from registration error
  variability_candidate           significant flux change between wavelength-matched observations
  spectral_difference_only        flux differences appear only between unmatched wavelengths
  instrumental                    the observations are dominated by flagged/unusable data
  partially_usable                some exposures were rejected, most are usable
  insufficient_evidence           not enough usable observations to decide
  no_significant_change           enough data, and no significant change found

A candidate is never called a discovery. z values are significances of
differences under the stated errors, not probabilities.
"""

from __future__ import annotations

import math
from statistics import median

RULES = "ASSESS-1"
T = {
    "motion_detect_sigma": 5.0,        # |pm| / sigma for a detection
    "catalogue_consistency_sigma": 3.0,
    "min_astrometric_epochs": 2,
    "min_refs_per_plate": 4,
    "registration_ratio": 1.0,         # median plate RMS vs expected shift between consecutive epochs
    "variability_z": 5.0,
    "min_matched_pairs": 1,
    "instrumental_fraction": 0.5,      # > this fraction of exposures rejected -> instrumental
}


def _outcome(question: str, category: str, statement: str, evidence: dict, criteria: list[str],
             limitations: list[str]) -> dict:
    return {"question": question, "category": category, "statement": statement, "evidence": evidence,
            "criteria": criteria, "limitations": limitations, "rules": RULES}


def assess_motion(motion: dict | None, catalogue: dict, n_plate_epochs: int, plate_rms: list[float],
                  epoch_gaps_yr: list[float]) -> dict:
    pm_cat = math.hypot(catalogue.get("pmra", 0.0), catalogue.get("pmdec", 0.0))
    lim = ["Parallax displacement is not modelled (bounded by the catalogue parallax).",
           "Chromatic PSF and distortion differences between wavelengths are not modelled.",
           "Gaussian centroids approximate the SPHEREx PSF."]
    crit = [f"detection: |pm|/σ ≥ {T['motion_detect_sigma']}",
            f"consistency: |measured − catalogue| ≤ {T['catalogue_consistency_sigma']}σ per axis",
            f"registration: median plate RMS < {T['registration_ratio']} × expected shift between epochs"]
    if motion is None or n_plate_epochs < T["min_astrometric_epochs"]:
        return _outcome("motion", "insufficient_evidence",
                        f"Only {n_plate_epochs} exposure(s) have a reference-star plate solution; at least "
                        f"{T['min_astrometric_epochs']} are needed to measure motion.",
                        {"n_plate_epochs": n_plate_epochs}, crit, lim)
    fit, cmp = motion["fit"], motion["comparison"]
    pm = math.hypot(fit["pm_xi_mas_yr"], fit["pm_eta_mas_yr"])
    sig = math.hypot(fit["sig_xi"] * fit["pm_xi_mas_yr"], fit["sig_eta"] * fit["pm_eta_mas_yr"]) / pm if pm > 0 else float("inf")
    snr = pm / sig if sig > 0 else 0.0
    med_rms = median(plate_rms) if plate_rms else float("nan")
    typical_gap = median([g for g in epoch_gaps_yr if g > 0]) if any(g > 0 for g in epoch_gaps_yr) else 0.0
    expected_step = pm_cat * typical_gap
    ev = {"pm_measured_mas_yr": pm, "pm_sigma_mas_yr": sig, "detection_snr": snr,
          "pm_catalogue_mas_yr": pm_cat, "median_plate_rms_mas": med_rms,
          "expected_shift_between_epochs_mas": expected_step, "n_plate_epochs": n_plate_epochs,
          "z_pmra": cmp["z_pmra"], "z_pmdec": cmp["z_pmdec"], "baseline_yr": fit["baseline_yr"]}
    if snr < T["motion_detect_sigma"]:
        if pm_cat < T["catalogue_consistency_sigma"] * sig:
            return _outcome("motion", "no_significant_change",
                            "No significant motion is measured. The catalogue proper motion is smaller than three times "
                            "this data set's sensitivity, so no detectable motion was expected.", ev, crit, lim)
        if expected_step > 0 and med_rms >= T["registration_ratio"] * expected_step:
            return _outcome("motion", "registration_limited",
                            "No significant motion is measured, and the registration scatter is as large as the "
                            "catalogue-predicted shift between epochs, so this data set cannot test the motion.", ev, crit, lim)
        return _outcome("motion", "no_significant_change",
                        "No significant motion is measured over the available baseline.", ev, crit, lim)
    if cmp["consistent_within_3sigma"]:
        return _outcome("motion", "motion_detected",
                        "Motion is detected and agrees with the catalogue proper motion within the stated "
                        "uncertainties.", ev, crit, lim)
    if expected_step > 0 and med_rms >= T["registration_ratio"] * expected_step:
        return _outcome("motion", "registration_limited",
                        "A position change is measured but it disagrees with the catalogue and the registration "
                        "scatter is comparable to the expected shift: the apparent motion may be a registration error.",
                        ev, crit, lim)
    return _outcome("motion", "motion_inconsistent",
                    "Motion is detected but disagrees with the catalogue beyond the stated uncertainties; an "
                    "unmodelled systematic (parallax, blending, chromatic effects) is the first explanation to test.",
                    ev, crit, lim)


def assess_variability(flux_pairs: list[dict], spectral_pairs: list[dict], n_pairs_considered: int) -> dict:
    lim = ["Aperture fluxes are not aperture-corrected; only matched pairs are compared.",
           "Errors include photon/read noise and sky; PSF variation across the detector and calibration drift are not in the error model.",
           "Unresolved neighbours contribute to every aperture flux."]
    crit = [f"wavelength match: rule WLMATCH-1 (same detector, |Δλ| ≤ 0.5 × bandwidth)",
            f"candidate: |z| ≥ {T['variability_z']} in at least one matched pair of unflagged measurements"]
    zs = [abs(p["z"]) for p in flux_pairs if p.get("z") is not None and math.isfinite(p["z"])]
    ev = {"n_matched_pairs": len(zs), "n_pairs_considered": n_pairs_considered,
          "max_abs_z": max(zs) if zs else None,
          "n_pairs_above_threshold": sum(z >= T["variability_z"] for z in zs),
          "n_spectral_context_pairs": len(spectral_pairs),
          "max_abs_z_unmatched_wavelength": max((abs(p["z"]) for p in spectral_pairs if p.get("z") is not None
                                                 and math.isfinite(p["z"])), default=None)}
    if len(zs) < T["min_matched_pairs"]:
        if ev["max_abs_z_unmatched_wavelength"] is not None and ev["max_abs_z_unmatched_wavelength"] >= T["variability_z"]:
            return _outcome("variability", "spectral_difference_only",
                            "Flux differences are large only between observations at different wavelengths, which "
                            "reflects the source spectrum; no wavelength-matched pair exists to test variability.",
                            ev, crit, lim)
        return _outcome("variability", "insufficient_evidence",
                        "No wavelength-matched pair of usable measurements exists, so variability cannot be tested.",
                        ev, crit, lim)
    if ev["n_pairs_above_threshold"]:
        return _outcome("variability", "variability_candidate",
                        f"{ev['n_pairs_above_threshold']} wavelength-matched pair(s) differ significantly. This is a "
                        "variability candidate, not a confirmed physical change.", ev, crit, lim)
    if ev["max_abs_z_unmatched_wavelength"] is not None and ev["max_abs_z_unmatched_wavelength"] >= T["variability_z"]:
        return _outcome("variability", "spectral_difference_only",
                        "Matched pairs show no significant change; the large differences occur only between "
                        "unmatched wavelengths and reflect the source spectrum.", ev, crit, lim)
    return _outcome("variability", "no_significant_change",
                    "No significant flux change between wavelength-matched observations.", ev, crit, lim)


def assess_quality(n_total: int, n_rejected: int, reasons: dict[str, int]) -> dict:
    frac = n_rejected / n_total if n_total else 1.0
    ev = {"n_exposures": n_total, "n_rejected": n_rejected, "rejected_fraction": frac, "reasons": reasons}
    crit = [f"instrumental if more than {T['instrumental_fraction']:.0%} of exposures are unusable"]
    lim = ["Flag bits are applied only when their numbers are known from the file header or IRSA documentation."]
    if n_total == 0:
        return _outcome("data_quality", "insufficient_evidence", "No exposures could be measured.", ev, crit, lim)
    if frac > T["instrumental_fraction"]:
        return _outcome("data_quality", "instrumental",
                        "Most exposures are unusable (flags, missing wavelength or failed fits); results rest on few observations.",
                        ev, crit, lim)
    return _outcome("data_quality", "no_significant_change" if n_rejected == 0 else "partially_usable",
                    f"{n_total - n_rejected} of {n_total} exposures are usable.", ev, crit, lim)
