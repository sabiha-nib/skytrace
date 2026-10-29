"""Uncertainty decomposition (UNC-1): what the recorded uncertainties are made of.

Reads a finished investigation record and reports, for each quantity, only the components that the methods
actually computed and logged. Nothing is estimated here: the only arithmetic is the PAIRDIFF-2 denominator, which
is recomputed from its logged inputs and checked against the logged z (a consistency check), and the conversion of
the parallax systematic bound (mas) to a rate bound over the baseline (mas/yr), labelled as a bound, not a σ.

Parameter sensitivity (STAB-1) is a different thing and is reported separately; it is never added to a σ.
"""

from __future__ import annotations

import math

METHOD = "UNC-1"
UNQUANTIFIED = [
    {"name": "Aperture correction", "why": "aperture fluxes are compared only between matched pairs, where it cancels to first order; the residual sub-pixel term is not modelled (the calibration check measures its effect on reference stars)"},
    {"name": "PSF variation across the detector", "why": "a Gaussian PSF is fitted; no PSF-model uncertainty is propagated"},
    {"name": "Chromatic centroid offsets", "why": "per-detector motion fits are not implemented, so detector-dependent offsets are not separated"},
    {"name": "Unresolved, uncatalogued neighbours", "why": "only catalogued neighbours are masked; others contribute to flux and centroid without an error term"},
]


def _first(record: dict, step: str) -> dict | None:
    return next((e for e in record["events"] if e["step"] == step), None)


def motion(record: dict) -> dict:
    a = _first(record, "astrometry")
    if not a or a["status"] != "ok":
        return {"available": False, "reason": (a or {}).get("detail", "no astrometry step recorded")}
    d = a["data"]
    fit = d["fit"]
    rchi2 = fit.get("reduced_chi2")
    infl = math.sqrt(max(1.0, rchi2)) if rchi2 is not None else None
    cat = d.get("catalogue", {})
    comp = d.get("comparison", {})
    plx = d.get("parallax") or {}
    base = fit.get("baseline_yr") or 0.0
    rows = [
        {"component": "Statistical error of the primary fit", "kind": "sigma", "unit": "mas/yr",
         "values": {"east": fit["sig_xi"], "north": fit["sig_eta"]},
         "source": f"{fit.get('method')} on {d.get('fit_kind')} positions; includes the √χ²ν inflation when χ²ν > 1",
         "detail": {"reduced_chi2": rchi2, "inflation_factor": infl, "n_points": fit.get("n_epochs")}},
    ]
    ef = d.get("exposure_fit")
    if ef and d.get("fit_kind") == "epoch":
        rows.append({"component": "Per-exposure fit (cross-check)", "kind": "sigma", "unit": "mas/yr",
                     "values": {"east": ef["sig_xi"], "north": ef["sig_eta"]},
                     "source": "same data, every exposure treated as independent",
                     "detail": {"note": "optimistic: exposures within a visit share reference stars and detector region"}})
    eps = d.get("epochs") or []
    if eps:
        floor = sum(1 for e in eps if max(e["empirical_sig_mas"]) > max(e["formal_sig_mas"]))
        rows.append({"component": "Within-visit scatter floor", "kind": "count", "unit": "visits",
                     "values": {"visits_using_empirical_scatter": floor, "visits": len(eps)},
                     "source": "LINFIT-EPOCH-1: each visit's error is max(formal, empirical scatter/√n)",
                     "detail": {"per_visit": [{"t_mjd": e["t_mjd"], "n": e["n_exposures"], "formal_mas": e["formal_sig_mas"],
                                               "empirical_mas": e["empirical_sig_mas"]} for e in eps]}})
    rows.append({"component": "Catalogue proper-motion error", "kind": "sigma", "unit": "mas/yr",
                 "values": {"east": cat.get("pmra_error"), "north": cat.get("pmdec_error")},
                 "source": cat.get("source"),
                 "detail": {"note": "enters the measured − catalogue comparison, not the measurement",
                            "combined_sigma_east": comp.get("sigma_pmra_mas_yr"), "combined_sigma_north": comp.get("sigma_pmdec_mas_yr")}})
    if plx:
        bound = plx.get("systematic_bound_mas")
        rows.append({"component": "Parallax residual (systematic bound)", "kind": "bound", "unit": "mas/yr",
                     "values": {"rate_bound": (bound / base) if bound is not None and base > 0 else None},
                     "source": f"{plx.get('method') or 'not modelled'}: bound {bound} mas over a {base:.2f} yr baseline",
                     "detail": {"applied": plx.get("applied"), "parallax_mas": plx.get("parallax_mas"),
                                "note": "an upper bound on a systematic, not a standard deviation"}})
    return {"available": True, "rows": rows, "fit_kind": d.get("fit_kind")}


def pair_terms(p: dict, scale: float | None) -> dict:
    """Denominator terms of one matched pair (µJy), recomputed from logged inputs."""
    sa, sb, fa, fb = p.get("err_a_ujy"), p.get("err_b_ujy"), p.get("flux_a_ujy"), p.get("flux_b_ujy")
    d = p.get("differential") or {}
    out = {"a": p["a"], "b": p["b"], "z_raw": p.get("z"), "calibrated": bool(d.get("calibrated")), "n_refs": d.get("n_refs")}
    if d.get("calibrated") and None not in (sa, sb, fa, fb) and d.get("ratio_median"):
        m, sm = d["ratio_median"], d.get("ratio_sigma") or 0.0
        terms = {"exposure_a": sa, "exposure_b_scaled": sb / m, "calibration_ratio": fb * sm / m ** 2}
        denom = math.sqrt(sum(v ** 2 for v in terms.values()))
        z = (fb / m - fa) / denom if denom > 0 else None
        out.update({"terms_ujy": terms, "denominator_ujy": denom, "z_calibrated": d.get("z_cal"), "z_recomputed": z,
                    "consistent_with_log": z is not None and d.get("z_cal") is not None and abs(z - d["z_cal"]) <= 1e-9 * max(1.0, abs(z)),
                    "error_scale": scale, "z_used": d.get("z_cal_scaled", d.get("z_cal")),
                    "variance_share": {k: v ** 2 / denom ** 2 for k, v in terms.items()} if denom > 0 else None})
    elif None not in (sa, sb):
        denom = math.hypot(sa, sb)
        out.update({"terms_ujy": {"exposure_a": sa, "exposure_b": sb}, "denominator_ujy": denom,
                    "variance_share": {"exposure_a": sa ** 2 / denom ** 2, "exposure_b": sb ** 2 / denom ** 2} if denom > 0 else None,
                    "error_scale": scale, "z_used": (p.get("z") / scale) if p.get("z") is not None and scale else p.get("z")})
    return out


def variability(record: dict, top: int = 8) -> dict:
    v = _first(record, "variability")
    if not v or not v["data"].get("pairs"):
        return {"available": False, "reason": "no wavelength-matched pair was compared"}
    cal = v["data"].get("calibration_check") or {}
    scale = cal.get("error_scale")
    pairs = sorted(v["data"]["pairs"], key=lambda p: -abs(p.get("z") or 0.0))
    return {"available": True, "calibration_check": cal,
            "pairs": [pair_terms(p, scale) for p in pairs[:top]], "n_pairs": len(pairs),
            "note": "z_used is the significance the assessment used: reference-calibrated and divided by the calibration-check scale when available"}


def decompose(record: dict) -> dict:
    return {"method": METHOD, "motion": motion(record), "variability": variability(record), "unquantified": UNQUANTIFIED,
            "sensitivity_note": "Parameter sensitivity (STAB-1) is shown separately and is not a statistical uncertainty."}
