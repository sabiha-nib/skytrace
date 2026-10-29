"""Deterministic assessment of an investigation (rules ASSESS-2).

Turns measurements into one of a fixed set of outcomes per question. Every
outcome carries: the statement, the evidence values it was decided from, the
criteria (with thresholds), the inputs used, the sensitivity of this data set,
and the limitations. Thresholds are fixed constants chosen before any data
were examined (Phase 1 design, ASSESS-1) and are not tuned per target; their
provenance is reported with every result.

Outcome categories. Each question has its own set; the distinctions the
project requires are kept apart explicitly:

  motion
    motion_detected             significant motion (|pm|/σ ≥ 5), consistent with the catalogue
    motion_inconsistent         measured motion disagrees with the catalogue beyond 3σ (systematic suspected)
    no_motion_at_sensitivity    no significant motion; states the 5σ minimum detectable motion.
                                A non-detection is NOT proof that the source is static.
    registration_limited        the registration scatter is as large as the expected shift: motion cannot be tested
    measurement_failed          enough exposures, but the motion fit failed. A failed measurement is NOT
                                evidence of no motion.
    insufficient_evidence       too few usable exposures/visits to measure motion

  variability
    variability_candidate       ≥ 1 wavelength-matched, reference-calibrated pair with |z| ≥ 5 (after the
                                CALCHECK error scale). A candidate, never a discovery.
    no_variability_at_sensitivity  matched pairs exist and none is significant; states the 5σ minimum
                                detectable fractional change. Not proof of constancy.
    calibration_limited         a raw difference exists but cannot be separated from a calibration change
                                (no reference calibration), or the error model is unreliable
                                (CALCHECK scatter > 3)
    spectral_difference_only    large differences only between unmatched wavelengths (the spectrum)
    insufficient_evidence       no wavelength-matched pair of usable measurements

  data_quality
    all_usable / partially_usable / instrumental / insufficient_evidence

z values are significances of differences under the stated errors, not probabilities.
"""

from __future__ import annotations

import math
from statistics import median

RULES = "ASSESS-2"
T = {
    "motion_detect_sigma": 5.0,        # |pm| / sigma for a detection
    "catalogue_consistency_sigma": 3.0,
    "min_astrometric_exposures": 2,
    "registration_ratio": 1.0,         # median plate RMS vs expected shift between consecutive visits
    "variability_z": 5.0,
    "min_matched_pairs": 1,
    "calcheck_unreliable_scale": 3.0,  # reference-star scatter above this -> error model unreliable
    "instrumental_fraction": 0.5,      # > this fraction of exposures rejected -> instrumental
}
THRESHOLD_PROVENANCE = ("Fixed in the Phase 1 design (ASSESS-1) before any data were examined; ASSESS-2 adds "
                        "calcheck_unreliable_scale. Not tuned per target. 5σ is the conventional detection "
                        "threshold for many trials; 3σ is used only for consistency with an external value.")


def _outcome(question: str, category: str, statement: str, evidence: dict, criteria: list[str],
             limitations: list[str], inputs: dict, sensitivity: dict | None = None) -> dict:
    return {"question": question, "category": category, "statement": statement, "evidence": evidence,
            "criteria": criteria, "limitations": limitations, "inputs": inputs, "sensitivity": sensitivity or {},
            "rules": RULES, "threshold_provenance": THRESHOLD_PROVENANCE}


def _finite(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


# ---------------------------------------------------------------------------- motion
def assess_motion(motion: dict | None, catalogue: dict, n_plate_exposures: int, plate_rms: list[float],
                  epoch_gaps_yr: list[float], fit_error: str | None = None) -> dict:
    pm_cat = math.hypot(catalogue.get("pmra", 0.0), catalogue.get("pmdec", 0.0))
    plx = (motion or {}).get("parallax") or {}
    lim = [("Annual parallax is removed with EPHEM-AA-LP-1; residual systematic ≤ "
            f"{plx.get('systematic_bound_mas', 0):.1f} mas." if plx.get("applied") else
            "Annual parallax is NOT modelled in this run (bounded by the catalogue parallax)."),
           "Chromatic PSF and distortion differences between wavelengths are absorbed per exposure by the plate solution only to first order.",
           "Gaussian centroids approximate the SPHEREx PSF (0.02 px floor added)."]
    crit = [f"detection: |pm|/σ ≥ {T['motion_detect_sigma']}",
            f"consistency: |measured − catalogue| ≤ {T['catalogue_consistency_sigma']}σ per axis (catalogue errors included)",
            f"registration: median plate RMS < {T['registration_ratio']} × catalogue-predicted shift between visits",
            f"minimum: {T['min_astrometric_exposures']} exposures with a usable target position and plate solution"]
    inputs = {"n_plate_exposures": n_plate_exposures, "fit_kind": (motion or {}).get("fit_kind"),
              "catalogue_pm_mas_yr": pm_cat, "catalogue_source": (motion or {}).get("catalogue", {}).get("source")}
    if motion is None:
        if n_plate_exposures >= T["min_astrometric_exposures"] and fit_error:
            return _outcome("motion", "measurement_failed",
                            f"The motion fit failed ({fit_error}). This is not evidence that the source is static.",
                            {"n_plate_exposures": n_plate_exposures, "error": fit_error}, crit, lim, inputs)
        return _outcome("motion", "insufficient_evidence",
                        f"Only {n_plate_exposures} exposure(s) have a usable target position and plate solution; at least "
                        f"{T['min_astrometric_exposures']} are needed to measure motion.",
                        {"n_plate_exposures": n_plate_exposures}, crit, lim, inputs)
    fit, cmp = motion["fit"], motion["comparison"]
    px, pe, sx, se = fit["pm_xi_mas_yr"], fit["pm_eta_mas_yr"], fit["sig_xi"], fit["sig_eta"]
    pm = math.hypot(px, pe)
    sig = math.hypot(sx * px, se * pe) / pm if pm > 0 else math.sqrt((sx ** 2 + se ** 2) / 2)
    snr = pm / sig if sig > 0 else 0.0
    min_det = T["motion_detect_sigma"] * math.sqrt((sx ** 2 + se ** 2) / 2)
    med_rms = median(plate_rms) if plate_rms else float("nan")
    gaps = [g for g in epoch_gaps_yr if g > 0]
    typical_gap = median(gaps) if gaps else 0.0
    expected_step = pm_cat * typical_gap
    ev = {"pm_measured_mas_yr": pm, "pm_sigma_mas_yr": sig, "detection_snr": snr,
          "pm_catalogue_mas_yr": pm_cat, "median_plate_rms_mas": med_rms,
          "expected_shift_between_visits_mas": expected_step, "n_fit_points": fit["n_epochs"],
          "z_pmra": cmp["z_pmra"], "z_pmdec": cmp["z_pmdec"], "baseline_yr": fit["baseline_yr"],
          "reduced_chi2": fit["reduced_chi2"]}
    sens = {"min_detectable_pm_mas_yr_5sigma": min_det, "baseline_yr": fit["baseline_yr"],
            "note": "Motion smaller than this would not be detected by this data set."}
    reg_limited = expected_step > 0 and _finite(med_rms) and med_rms >= T["registration_ratio"] * expected_step
    if snr < T["motion_detect_sigma"]:
        if not cmp["consistent_within_3sigma"] and pm_cat >= min_det:
            if reg_limited:
                return _outcome("motion", "registration_limited",
                                "The catalogue motion should be detectable but is not recovered, and the registration "
                                "scatter is as large as the expected shift between visits, so this data set cannot "
                                "test the motion.", ev, crit, lim, inputs, sens)
            return _outcome("motion", "motion_inconsistent",
                            f"The catalogue motion ({pm_cat:.0f} mas/yr) is above this data set's 5σ sensitivity "
                            f"({min_det:.0f} mas/yr) but is not recovered; an unmodelled systematic or a wrong "
                            "identification is the first explanation to test.", ev, crit, lim, inputs, sens)
        return _outcome("motion", "no_motion_at_sensitivity",
                        f"No motion is detected above {min_det:.0f} mas/yr (5σ) over {fit['baseline_yr']:.2f} yr. "
                        "This is not proof that the source is static.", ev, crit, lim, inputs, sens)
    if cmp["consistent_within_3sigma"]:
        return _outcome("motion", "motion_detected",
                        "Motion is detected and agrees with the catalogue proper motion within the stated "
                        "uncertainties.", ev, crit, lim, inputs, sens)
    if reg_limited:
        return _outcome("motion", "registration_limited",
                        "A position change is measured but it disagrees with the catalogue and the registration "
                        "scatter is comparable to the expected shift: the apparent motion may be a registration error.",
                        ev, crit, lim, inputs, sens)
    return _outcome("motion", "motion_inconsistent",
                    "Motion is detected but disagrees with the catalogue beyond the stated uncertainties; an "
                    "unmodelled systematic (blending, chromatic effects, wrong reference stars) is the first "
                    "explanation to test.", ev, crit, lim, inputs, sens)


# ---------------------------------------------------------------------------- variability
def pair_significance(p: dict, error_scale: float | None = None) -> tuple[float | None, bool]:
    """(z used for the decision, calibrated?) for one logged flux pair.

    Calibrated pairs use the PAIRDIFF-2 z; both kinds are divided by the CALCHECK error scale (≥ 1) when known.
    """
    k = max(1.0, error_scale) if _finite(error_scale) else 1.0
    d = p.get("differential") or {}
    if d.get("calibrated"):
        z = d.get("z_cal_scaled") if _finite(d.get("z_cal_scaled")) else (d["z_cal"] / k if _finite(d.get("z_cal")) else None)
        return z, True
    z = p.get("z")
    return (z / k if _finite(z) else None), False


def assess_variability(flux_pairs: list[dict], spectral_pairs: list[dict], n_pairs_considered: int,
                       calcheck: dict | None = None) -> dict:
    calcheck = calcheck or {}
    lim = ["Aperture fluxes are not aperture-corrected; only matched pairs are compared.",
           "Per-pixel errors plus a reference-star calibration term; the CALCHECK scale corrects the error model "
           "only on average.",
           "Unresolved neighbours contribute to every aperture flux."]
    crit = ["wavelength match: rule WLMATCH-2 (same detector, same release by default, |Δλ| + 2 nm ≤ 0.5 × bandwidth)",
            "calibration: PAIRDIFF-2 reference-normalised ratio (≥ 3 wavelength-matched reference stars)",
            f"candidate: |z| ≥ {T['variability_z']} in at least one calibrated matched pair (after the CALCHECK scale)",
            f"calibration-limited: uncalibrated |z| ≥ {T['variability_z']} only, or CALCHECK scatter > {T['calcheck_unreliable_scale']}"]
    cal_z, raw_z, frac = [], [], []
    for p in flux_pairs:
        z, calibrated = pair_significance(p, calcheck.get("error_scale"))
        if z is None:
            continue
        (cal_z if calibrated else raw_z).append(abs(z))
        if _finite(p.get("flux_a_ujy")) and p["flux_a_ujy"] > 0 and _finite(p.get("sigma_ujy")):
            frac.append(p["sigma_ujy"] / p["flux_a_ujy"] * max(1.0, calcheck.get("error_scale") or 1.0))
    unm = [abs(p["z"]) for p in spectral_pairs if _finite(p.get("z"))]
    raw_all = [abs(p["z"]) for p in flux_pairs if _finite(p.get("z"))]
    ev = {"n_matched_pairs": len(cal_z) + len(raw_z), "n_calibrated_pairs": len(cal_z),
          "n_pairs_considered": n_pairs_considered,
          "max_abs_z_calibrated": max(cal_z) if cal_z else None,
          "max_abs_z_uncalibrated": max(raw_z) if raw_z else None,
          "max_abs_z_pairdiff1": max(raw_all) if raw_all else None,   # before reference calibration, all matched pairs
          "n_calibrated_above_threshold": sum(z >= T["variability_z"] for z in cal_z),
          "n_uncalibrated_above_threshold": sum(z >= T["variability_z"] for z in raw_z),
          "calcheck_status": calcheck.get("status"), "calcheck_scale": calcheck.get("error_scale"),
          "n_spectral_context_pairs": len(spectral_pairs),
          "max_abs_z_unmatched_wavelength": max(unm) if unm else None}
    inputs = {"n_flux_pairs": len(flux_pairs), "calibration_check": calcheck.get("method")}
    sens = {}
    if frac:
        sens = {"min_detectable_fractional_change_5sigma": T["variability_z"] * median(frac),
                "min_detectable_fractional_change_5sigma_best_pair": T["variability_z"] * min(frac),
                "note": "5σ change detectable in a typical (median) matched pair and in the most sensitive pair; "
                        "sensitivity differs by detector and wavelength"}
    spectral_big = ev["max_abs_z_unmatched_wavelength"] is not None and ev["max_abs_z_unmatched_wavelength"] >= T["variability_z"]
    if not cal_z and not raw_z:
        if spectral_big:
            return _outcome("variability", "spectral_difference_only",
                            "Flux differences are large only between observations at different wavelengths, which "
                            "reflects the source spectrum; no wavelength-matched pair exists to test variability.",
                            ev, crit, lim, inputs, sens)
        return _outcome("variability", "insufficient_evidence",
                        "No wavelength-matched pair of usable measurements exists, so variability cannot be tested.",
                        ev, crit, lim, inputs, sens)
    if (calcheck.get("error_scale") or 0) > T["calcheck_unreliable_scale"]:
        return _outcome("variability", "calibration_limited",
                        f"Constant reference stars scatter {calcheck['error_scale']:.1f}× more than their stated errors, "
                        "so the error model is not reliable enough to test variability.", ev, crit, lim, inputs, sens)
    if ev["n_calibrated_above_threshold"]:
        return _outcome("variability", "variability_candidate",
                        f"{ev['n_calibrated_above_threshold']} wavelength-matched, reference-calibrated pair(s) differ "
                        "significantly. This is a variability candidate, not a confirmed physical change.",
                        ev, crit, lim, inputs, sens)
    if ev["n_uncalibrated_above_threshold"]:
        return _outcome("variability", "calibration_limited",
                        "Significant differences appear only in pairs without enough reference stars to measure the "
                        "calibration change between the exposures, so they cannot be attributed to the source.",
                        ev, crit, lim, inputs, sens)
    if spectral_big:
        return _outcome("variability", "spectral_difference_only",
                        "Matched pairs show no significant change; the large differences occur only between "
                        "unmatched wavelengths and reflect the source spectrum.", ev, crit, lim, inputs, sens)
    s = sens.get("min_detectable_fractional_change_5sigma")
    sb = sens.get("min_detectable_fractional_change_5sigma_best_pair")
    return _outcome("variability", "no_variability_at_sensitivity",
                    "No significant flux change between wavelength-matched observations"
                    + (f" (5σ sensitivity {sb:.1%} in the most sensitive pair, {s:.1%} in a typical pair)" if s else "")
                    + ". This is not proof that the source is constant.",
                    ev, crit, lim, inputs, sens)


# ---------------------------------------------------------------------------- data quality
def assess_quality(n_total: int, n_rejected: int, reasons: dict[str, int]) -> dict:
    frac = n_rejected / n_total if n_total else 1.0
    ev = {"n_exposures": n_total, "n_rejected": n_rejected, "rejected_fraction": frac, "reason_codes": reasons}
    crit = [f"instrumental if more than {T['instrumental_fraction']:.0%} of exposures are unusable for both photometry and astrometry"]
    lim = ["Flag bits are applied only when their numbers are known from the file header or IRSA documentation."]
    inputs = {"n_exposures": n_total}
    if n_total == 0:
        return _outcome("data_quality", "insufficient_evidence", "No exposures could be measured.", ev, crit, lim, inputs)
    if frac > T["instrumental_fraction"]:
        return _outcome("data_quality", "instrumental",
                        "Most exposures are unusable (flags, missing wavelength or failed fits); results rest on few observations.",
                        ev, crit, lim, inputs)
    return _outcome("data_quality", "all_usable" if n_rejected == 0 else "partially_usable",
                    f"{n_total - n_rejected} of {n_total} exposures are usable.", ev, crit, lim, inputs)


CATEGORIES = {
    "motion": ("motion_detected", "motion_inconsistent", "no_motion_at_sensitivity", "registration_limited",
               "measurement_failed", "insufficient_evidence"),
    "variability": ("variability_candidate", "no_variability_at_sensitivity", "calibration_limited",
                    "spectral_difference_only", "insufficient_evidence"),
    "data_quality": ("all_usable", "partially_usable", "instrumental", "insufficient_evidence"),
}
