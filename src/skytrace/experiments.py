"""Experiment Studio (EXP-1): bounded, configured experiments with stated evaluation criteria.

Templates
  parameter          up to 6 user-chosen parameter sets (within the server's bounds) against the default baseline
  sensitivity        the fixed STAB-1 perturbation set against the baseline
  reproducibility    the baseline executed twice, independently; content hashes compared
  method_comparison  compatible methods on the same inputs: PAIRDIFF-1 vs PAIRDIFF-2 decisions per calibrated pair, and
                     the primary (visit-averaged, LINFIT-EPOCH-1) vs cross-check (per-exposure, LINFIT-LOO-1) motion fits
  negative_control   the same analysis on the other synthetic fixture, where the effect is absent by construction
                     (generator input in `synthetic.SPECS`): no brightness change for SYN-HPM-1; a true motion of
                     27 mas/yr for SYN-VAR-1, far below the method's 5σ sensitivity, so it must not be detected
  robustness         the parameter bounds themselves (aperture 1 and 5 px, tolerance 0.1 and 1 channel, clip 2σ and 10σ):
                     every run must complete and report all outcomes
At most 8 analyses per experiment. Each run is summarised by its content hash, outcome categories and key numbers.
A completed experiment is evaluated only against its stated criteria; the result says explicitly that software that
ran is not, by itself, a valid scientific experiment.
"""

from __future__ import annotations

import time

from . import analysis, stability, synthetic

METHOD = "EXP-1"
MAX_RUNS = 8
TEMPLATES = {
    "parameter": {"title": "Parameter experiment", "criterion": "each run's outcome categories equal the baseline's"},
    "sensitivity": {"title": "Sensitivity (STAB-1 set)", "criterion": "each run's outcome categories equal the baseline's"},
    "reproducibility": {"title": "Reproducibility", "criterion": "two independent executions give identical content hashes"},
    "method_comparison": {"title": "Method comparison", "criterion": "PAIRDIFF-1 and PAIRDIFF-2 agree on detection for each calibrated pair; the two motion fits agree within 3σ per axis"},
    "negative_control": {"title": "Negative control", "criterion": "the effect absent by construction is not detected"},
    "robustness": {"title": "Robustness at parameter bounds", "criterion": "every run completes and reports all three outcomes"},
}
ROBUSTNESS = [("aperture 1.0 px (lower bound)", {"aperture_radius_px": 1.0}), ("aperture 5.0 px (upper bound)", {"aperture_radius_px": 5.0}),
              ("tolerance 0.1 channel (lower bound)", {"wavelength_tolerance_channels": 0.1}),
              ("tolerance 1.0 channel (upper bound)", {"wavelength_tolerance_channels": 1.0}),
              ("epoch clip 2σ (lower bound)", {"epoch_clip_sigma": 2.0}), ("epoch clip 10σ (upper bound)", {"epoch_clip_sigma": 10.0})]
VALIDITY = ("An experiment that ran is not thereby a valid experiment: judge its design (inputs, controls, criteria) and "
            "read the limitations. These are synthetic fixtures; nothing here is an astronomical result.")


def validate(cfg: dict) -> list[str]:
    errs = []
    if not isinstance(cfg, dict):
        return ["configuration must be an object"]
    t = cfg.get("template")
    if t not in TEMPLATES:
        return [f"unknown template {t!r}; choose one of {', '.join(TEMPLATES)}"]
    if t == "parameter":
        sets = cfg.get("configs")
        if not isinstance(sets, list) or not sets:
            return ["a parameter experiment needs at least one parameter set in 'configs'"]
        if len(sets) > MAX_RUNS - 2:
            errs.append(f"at most {MAX_RUNS - 2} parameter sets")
        for i, s in enumerate(sets):
            if not isinstance(s, dict) or not s:
                errs.append(f"configs[{i}]: must be a non-empty object of parameters")
                continue
            for k, v in s.items():
                if k in analysis.PARAM_BOUNDS:
                    lo, hi = analysis.PARAM_BOUNDS[k]
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
                        errs.append(f"configs[{i}].{k}: must be a number in [{lo}, {hi}]")
                elif k in analysis.PARAM_BOOLEANS:
                    if not isinstance(v, bool):
                        errs.append(f"configs[{i}].{k}: must be true or false")
                else:
                    errs.append(f"configs[{i}].{k}: not an adjustable parameter")
    if t == "negative_control" and cfg.get("question") not in ("variability", "motion"):
        errs.append("a negative control needs question 'variability' or 'motion'")
    return errs


def control_for(target_id: str, question: str) -> dict | None:
    """The fixture in which `question`'s effect is absent by construction, other than `target_id` (generator input)."""
    for s in synthetic.SPECS:
        if s["target_id"] == target_id:
            continue
        if question == "variability" and all(f == 1.0 for f in s["variability"]):
            return {"target_id": s["target_id"], "truth": "constant brightness in every pass (generator input)", "absent_category": "variability_candidate"}
        if question == "motion" and (s["pmra"] ** 2 + s["pmdec"] ** 2) ** 0.5 < 100.0:
            return {"target_id": s["target_id"], "truth": f"true proper motion {(s['pmra'] ** 2 + s['pmdec'] ** 2) ** 0.5:.0f} mas/yr (generator input), far below the 5σ sensitivity",
                    "absent_category": "motion_detected"}
    return None


def _run(load, tid, label, params):
    t0 = time.perf_counter()
    try:
        rec = analysis.run(load(tid), params).to_dict()
    except Exception as e:  # a failing configuration is a result, recorded as such
        return {"label": label, "target": tid, "params": params, "ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}",
                "seconds": round(time.perf_counter() - t0, 3)}
    s = stability._summary(rec)
    return {"label": label, "target": tid, "params": params, "ok": True, "seconds": round(time.perf_counter() - t0, 3), **s, "_record": rec}


def _strip(r):
    return {k: v for k, v in r.items() if k != "_record"}


def method_comparison(rec: dict) -> dict:
    from .science.assess import T, pair_significance
    var = next((e["data"] for e in rec["events"] if e["step"] == "variability"), {}) or {}
    scale = (var.get("calibration_check") or {}).get("error_scale")
    rows, agree = [], 0
    for p in var.get("pairs", []):
        d = p.get("differential") or {}
        if not d.get("calibrated") or p.get("z") is None:
            continue
        zc, _ = pair_significance(p, scale)
        a, b = abs(p["z"]) >= T["variability_z"], zc is not None and abs(zc) >= T["variability_z"]
        agree += a == b
        rows.append({"pair": f"{p['a']} → {p['b']}", "z_pairdiff1": p["z"], "z_pairdiff2_scaled": zc, "agree": a == b})
    a = next((e["data"] for e in rec["events"] if e["step"] == "astrometry"), {}) or {}
    motion = None
    if a.get("exposure_fit") and a.get("epoch_fit"):
        ef, pf = a["exposure_fit"], a["epoch_fit"]
        axes = {}
        for ax, s in (("xi", "sig_xi"), ("eta", "sig_eta")):
            sig = (ef[s] ** 2 + pf[s] ** 2) ** 0.5
            axes[ax] = {"epoch_fit": pf[f"pm_{ax}_mas_yr"], "exposure_fit": ef[f"pm_{ax}_mas_yr"],
                        "difference_sigma": abs(ef[f"pm_{ax}_mas_yr"] - pf[f"pm_{ax}_mas_yr"]) / sig if sig else None}
        motion = {"axes": axes, "agree_within_3sigma": all((v["difference_sigma"] or 0) <= 3 for v in axes.values()),
                  "note": "the two fits share exposures, so they are correlated; the combined σ ignores that and is conservative for agreement"}
    return {"pairs": rows, "n_pairs": len(rows), "n_agree": agree, "motion": motion,
            "passed": (not rows or agree == len(rows)) and (motion is None or motion["agree_within_3sigma"])}


def run(load, target_id: str, cfg: dict) -> dict:
    """Execute a validated configuration. `load(target_id)` returns a bundle."""
    errs = validate(cfg)
    if errs:
        return {"method": METHOD, "status": "refused", "errors": errs, "config": cfg}
    t = cfg["template"]
    base = _run(load, target_id, "baseline (default parameters)", {})
    runs, evaluation = [base], {}
    if t in ("parameter", "sensitivity", "robustness"):
        sets = ([(f"set {i + 1}", s) for i, s in enumerate(cfg["configs"])] if t == "parameter" else
                [(l, p) for l, p in stability.perturbations({})] if t == "sensitivity" else ROBUSTNESS)
        for label, params in sets[:MAX_RUNS - 1]:
            runs.append(_run(load, target_id, label, params))
        rows = []
        for r in runs[1:]:
            if not r["ok"]:
                rows.append({"label": r["label"], "passed": False, "detail": "did not complete: " + r["error"]})
            elif t == "robustness":
                ok = len(r["categories"]) == 3
                rows.append({"label": r["label"], "passed": ok, "detail": "completed; outcomes: " + ", ".join(f"{q} {c}" for q, c in sorted(r["categories"].items()))})
            else:
                changed = {q: [base["categories"].get(q), c] for q, c in r["categories"].items() if c != base["categories"].get(q)}
                rows.append({"label": r["label"], "passed": not changed, "changed": changed,
                             "detail": "same outcome categories as the baseline" if not changed else
                                       "changed: " + "; ".join(f"{q} {a} → {b}" for q, (a, b) in changed.items())})
        evaluation = {"rows": rows, "passed": all(x["passed"] for x in rows) if base["ok"] else False}
    elif t == "reproducibility":
        again = _run(load, target_id, "repeat (independent execution)", {})
        runs.append(again)
        same = base["ok"] and again["ok"] and base["content_hash"] == again["content_hash"]
        evaluation = {"passed": same, "detail": "identical content hashes" if same else "content hashes differ",
                      "hashes": [base.get("content_hash"), again.get("content_hash")]}
    elif t == "method_comparison":
        evaluation = method_comparison(base["_record"]) if base["ok"] else {"passed": False, "detail": "baseline failed"}
    elif t == "negative_control":
        c = control_for(target_id, cfg["question"])
        if c is None:
            evaluation = {"passed": None, "detail": "no fixture has this effect absent by construction"}
        else:
            ctrl = _run(load, c["target_id"], f"control {c['target_id']}", {})
            runs.append(ctrl)
            got = (ctrl.get("categories") or {}).get(cfg["question"])
            evaluation = {"passed": ctrl["ok"] and got != c["absent_category"], "control": c, "control_category": got,
                          "detail": f"control outcome '{got}'; the method must not report '{c['absent_category']}' here"}
    return {"method": METHOD, "status": "completed", "template": t, "title": TEMPLATES[t]["title"], "criterion": TEMPLATES[t]["criterion"],
            "target": target_id, "config": cfg, "runs": [_strip(r) for r in runs], "evaluation": evaluation,
            "n_analyses": len(runs), "validity_note": VALIDITY}
