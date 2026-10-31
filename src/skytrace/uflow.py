"""Uncertainty lineage (UFLOW-1): how uncertainty travels through the analysis, transformation by transformation.

Only categories the methods actually represent appear (UNC-1 and METHOD-DNA-1): input measurement uncertainty
(per-pixel VARIANCE), transformation uncertainty (centroid and plate covariance, quadrature sums, least squares),
calibration uncertainty (reference-ratio scatter, CALCHECK scale), model uncertainty (√χ²ν inflation) and output
uncertainty (sensitivities stated by ASSESS-2). Parameter sensitivity is examined separately (stability and counterfactual
runs) and is not propagated into any σ. Steps that do not propagate uncertainty are listed as such, with what is recorded
instead. Representative values are medians of recorded values; nothing is re-estimated.
"""

from __future__ import annotations

import statistics

from . import methodgenome as mg

METHOD = "UFLOW-1"
CATEGORIES = ["input", "transformation", "calibration", "model", "output"]


def _med(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and x == x]
    return statistics.median(xs) if xs else None


def flow(record: dict, unc: dict | None) -> dict:
    ev = {}
    for i, e in enumerate(record["events"]):
        ev.setdefault(e["step"], []).append((i, e))
    meas = [(e.get("data") or {}) for _, e in ev.get("measure", []) if e.get("status") == "ok"]
    astro = ((ev.get("astrometry") or [(0, {"data": {}})])[0][1].get("data") or {})
    var = ((ev.get("variability") or [(0, {"data": {}})])[0][1].get("data") or {})
    assess = {o["question"]: o for o in (((ev.get("assess") or [(0, {"data": {}})])[0][1].get("data") or {}).get("outcomes", []))}
    pairs = var.get("pairs", [])
    fit = astro.get("fit") or {}
    cc = var.get("calibration_check") or {}
    tests = lambda mid: mg.health(mg.BY_ID[mid], True)["known_answer_tests"] if mid in mg.BY_ID else []  # noqa: E731
    N = [
        {"id": "u:variance", "category": "input", "quantity": "per-pixel VARIANCE", "unit": "(MJy/sr)²", "method": "recorded in the file",
         "inputs": [], "propagation": "read, not computed", "assumptions": ["the pipeline's VARIANCE describes the pixel noise"], "result": None, "validation": []},
        {"id": "u:centroid", "category": "transformation", "quantity": "centroid σx, σy", "unit": "px", "method": "CENTROID-G2D-1", "inputs": ["u:variance"],
         "propagation": mg.BY_ID["CENTROID-G2D-1"]["uncertainty_propagation"], "assumptions": mg.BY_ID["CENTROID-G2D-1"]["assumptions"],
         "result": {"median_sigma_x_px": _med([(m.get("centroid") or {}).get("sigma_x") for m in meas])}, "validation": tests("CENTROID-G2D-1")},
        {"id": "u:flux", "category": "transformation", "quantity": "flux error", "unit": "µJy", "method": "APPHOT-1", "inputs": ["u:variance"],
         "propagation": mg.BY_ID["APPHOT-1"]["uncertainty_propagation"], "assumptions": mg.BY_ID["APPHOT-1"]["assumptions"],
         "result": {"median_flux_err_ujy": _med([(m.get("photometry") or {}).get("flux_err_ujy") for m in meas])}, "validation": tests("APPHOT-1")},
        {"id": "u:position", "category": "transformation", "quantity": "sky position σξ, ση", "unit": "mas", "method": "DIFFAST-1/PLATE-LOO-1", "inputs": ["u:centroid"],
         "propagation": mg.BY_ID["DIFFAST-1/PLATE-LOO-1"]["uncertainty_propagation"], "assumptions": mg.BY_ID["DIFFAST-1/PLATE-LOO-1"]["assumptions"],
         "result": {"median_sigma_xi_mas": _med([s.get("sig_xi_mas") for s in astro.get("series", [])]), "median_plate_rms_mas": _med([s.get("plate_rms_mas") for s in astro.get("series", [])])},
         "validation": tests("DIFFAST-1/PLATE-LOO-1")},
        {"id": "u:visit", "category": "transformation", "quantity": "visit-mean σ", "unit": "mas", "method": "LINFIT-EPOCH-1", "inputs": ["u:position"],
         "propagation": "max(formal error of the mean, empirical scatter/√n) per axis", "assumptions": mg.BY_ID["LINFIT-EPOCH-1"]["assumptions"],
         "result": {"visits": len(astro.get("epochs", [])), "median_sigma_xi_mas": _med([e.get("sig_xi_mas") for e in astro.get("epochs", [])])}, "validation": tests("LINFIT-EPOCH-1")},
        {"id": "u:pm", "category": "model", "quantity": "proper-motion σ", "unit": "mas/yr", "method": fit.get("method") or "LINFIT-EPOCH-1", "inputs": ["u:visit"],
         "propagation": mg.BY_ID["LINFIT-EPOCH-1"]["uncertainty_propagation"], "assumptions": ["motion is linear over the baseline"],
         "result": {"sig_xi": fit.get("sig_xi"), "sig_eta": fit.get("sig_eta"), "reduced_chi2": fit.get("reduced_chi2"),
                    "inflated": bool(fit.get("reduced_chi2") and fit["reduced_chi2"] > 1)} if fit else None, "validation": tests("LINFIT-EPOCH-1")},
        {"id": "u:pair", "category": "transformation", "quantity": "pair σ", "unit": "µJy", "method": "PAIRDIFF-1", "inputs": ["u:flux"],
         "propagation": mg.BY_ID["PAIRDIFF-1"]["uncertainty_propagation"], "assumptions": mg.BY_ID["PAIRDIFF-1"]["assumptions"],
         "result": {"median_sigma_ujy": _med([p.get("sigma_ujy") for p in pairs]), "n_pairs": len(pairs)}, "validation": tests("PAIRDIFF-1")},
        {"id": "u:zcal", "category": "calibration", "quantity": "calibrated significance z_cal", "unit": "σ", "method": "PAIRDIFF-2", "inputs": ["u:pair", "u:flux"],
         "propagation": mg.BY_ID["PAIRDIFF-2"]["uncertainty_propagation"], "assumptions": mg.BY_ID["PAIRDIFF-2"]["assumptions"],
         "result": {"n_calibrated": sum(1 for p in pairs if (p.get("differential") or {}).get("calibrated")),
                    "median_ratio_sigma": _med([(p.get("differential") or {}).get("ratio_sigma") for p in pairs])}, "validation": tests("PAIRDIFF-2")},
        {"id": "u:scale", "category": "calibration", "quantity": "photometric error scale", "unit": "dimensionless", "method": "CALCHECK-1", "inputs": ["u:zcal"],
         "propagation": mg.BY_ID["CALCHECK-1"]["uncertainty_propagation"], "assumptions": mg.BY_ID["CALCHECK-1"]["assumptions"],
         "result": {"error_scale": cc.get("error_scale"), "status": cc.get("status"), "n_ref_z": cc.get("n_ref_z")} if cc else None, "validation": tests("CALCHECK-1")},
        {"id": "u:out:variability", "category": "output", "quantity": "brightness sensitivity", "unit": "fraction", "method": "ASSESS-2", "inputs": ["u:zcal", "u:scale", "u:pair"],
         "propagation": "z divided by the error scale; the minimum detectable fractional change at the threshold is stated", "assumptions": ["thresholds fixed before data were examined"],
         "result": (assess.get("variability") or {}).get("sensitivity"), "validation": tests("ASSESS-2")},
        {"id": "u:out:motion", "category": "output", "quantity": "motion sensitivity", "unit": "mas/yr", "method": "ASSESS-2", "inputs": ["u:pm"],
         "propagation": "5σ minimum detectable proper motion = 5 × σ", "assumptions": ["thresholds fixed before data were examined"],
         "result": (assess.get("motion") or {}).get("sensitivity"), "validation": tests("ASSESS-2")},
    ]
    if not fit:
        N = [n for n in N if n["id"] not in ("u:pm", "u:out:motion")]
    if not pairs:
        N = [n for n in N if n["id"] not in ("u:pair", "u:zcal", "u:scale", "u:out:variability")]
    edges = [{"source": i, "target": n["id"]} for n in N for i in n["inputs"] if any(m["id"] == i for m in N)]
    gaps = [
        {"step": "WLMATCH-2", "what": "residual wavelength difference within the tolerance", "recorded_as": "Δλ per pair (µm), not propagated into σ"},
        {"step": "EPHEM-AA-LP-1", "what": "heliocentric vs barycentric observer position", "recorded_as": "systematic bound 0.01 × parallax, not a σ"},
        {"step": "APPHOT-1", "what": "aperture correction", "recorded_as": "not applied; only matched pairs are compared"},
        {"step": "catalogue", "what": "catalogue proper-motion error", "recorded_as": "enters the measured − catalogue comparison, not the measurement"},
    ] + [{"step": "unquantified", "what": u.get("effect") if isinstance(u, dict) else str(u), "recorded_as": (u.get("why") if isinstance(u, dict) else "") or "not quantified by any method here"}
         for u in (unc or {}).get("unquantified", [])]
    return {"method": METHOD, "categories": CATEGORIES, "nodes": N, "edges": edges, "not_propagated": gaps,
            "parameter_uncertainty": "examined separately by the stability check and counterfactual scenarios; never added to a σ",
            "note": "Only uncertainty the methods represent is shown. A step listed under 'not propagated' contributes an effect that no σ here includes."}
