"""ORACLE-1: the observation oracle — which hypothetical measurements would best distinguish competing explanations.

The oracle schedules nothing. It evaluates candidate observation sets you define against two hypotheses with a stated
measurement model, using formulas that first reproduce the recorded fit (FUTURE-1's validation):

  motion       H0: the source is static; H1: it moves at |μ| (mas/yr, your value or the recorded estimate). For a set of visit
               times with per-visit errors σ_i, the weighted least-squares slope error σ_μ follows FUTURE-1. If H1 holds, the
               expected significance is S = |μ| / σ_μ (worse axis, conservative), and the expected Δχ² between the static and
               the linear model is S² (+1 for the extra parameter, under Gaussian errors). The pipeline's detection rule is S ≥ 5.
  variability  H0: no change; H1: a fractional change f between two epochs. For one wavelength-matched pair with fractional
               error e per exposure and the recorded CALCHECK scale k, S = f / (√2 · e · k); the pipeline's rule is |z| ≥ 5. The
               expected z² is S² + 1.

'Expected information gain' in bits needs prior probabilities for H0 and H1. The record contains none, so none is computed;
the expected discrimination S (and Δχ²) is reported instead. Feasibility is yours to state (times, precision); the oracle
only checks that the inputs are physical (positive errors, increasing times, at most 20 added visits).

Evidence negotiation (EVNEG-1): for each pair of HYPO-1 explanations of the same question that are both still viable, the
open tests of each — the evidence that would move one without moving the other — and the inputs they need.
"""

from __future__ import annotations

import math
import statistics

from . import futurelab

METHOD = "ORACLE-1"
METHOD_NEG = "EVNEG-1"
THRESHOLD = 5.0
MAX_ADDED = 20
VIABLE = ("consistent so far", "inconclusive", "untested")


def context(record: dict) -> dict:
    """What the oracle starts from: the recorded visits and their errors, the recorded motion estimate, flux and error scale."""
    eps, fit = futurelab._visits(record)
    val = futurelab.validate(record)
    vis = [{"t_yr": e["t_mjd"] / 365.25, "sigma_mas": max(e["sig_xi_mas"], e["sig_eta_mas"])} for e in eps]
    pm = None
    if fit.get("pm_xi_mas_yr") is not None and fit.get("pm_eta_mas_yr") is not None:
        pm = math.hypot(fit["pm_xi_mas_yr"], fit["pm_eta_mas_yr"])
    v = next((e for e in record["events"] if e["step"] == "variability"), None)
    vd = (v or {}).get("data") or {}
    pairs = vd.get("pairs", [])
    fl = [p["flux_a_ujy"] for p in pairs if isinstance(p.get("flux_a_ujy"), (int, float))]
    er = [p["err_a_ujy"] / p["flux_a_ujy"] for p in pairs if isinstance(p.get("err_a_ujy"), (int, float)) and p.get("flux_a_ujy")]
    return {"visits": vis, "validated": val["valid"], "validation": val, "recorded_pm_mas_yr": pm,
            "median_flux_ujy": statistics.median(fl) if fl else None, "median_fractional_error": statistics.median(er) if er else None,
            "error_scale": (vd.get("calibration_check") or {}).get("error_scale") or 1.0}


def validate_spec(spec) -> list[str]:
    errs = []
    if not isinstance(spec, dict):
        return ["the specification must be an object"]
    q = spec.get("question")
    if q not in ("motion", "variability"):
        errs.append("question must be 'motion' or 'variability'")
    cands = spec.get("candidates")
    if not isinstance(cands, list) or not 1 <= len(cands) <= 6:
        errs.append("give 1–6 candidate observation sets")
        return errs
    for i, c in enumerate(cands):
        if not isinstance(c, dict):
            errs.append(f"candidate {i + 1} must be an object")
            continue
        if q == "motion":
            add = c.get("added_years_after_last", [])
            if not isinstance(add, list) or len(add) > MAX_ADDED or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not 0 < x <= 20 for x in add):
                errs.append(f"candidate {i + 1}: added_years_after_last must be ≤ {MAX_ADDED} values in (0, 20] years")
            f = c.get("error_factor", 1.0)
            if not isinstance(f, (int, float)) or isinstance(f, bool) or not 0.1 <= f <= 10:
                errs.append(f"candidate {i + 1}: error_factor must be in [0.1, 10]")
        else:
            e = c.get("fractional_error")
            if not isinstance(e, (int, float)) or isinstance(e, bool) or not 1e-4 <= e <= 1:
                errs.append(f"candidate {i + 1}: fractional_error must be in [0.0001, 1]")
    h1 = spec.get("h1_value")
    if h1 is not None and (not isinstance(h1, (int, float)) or isinstance(h1, bool) or h1 <= 0):
        errs.append("h1_value must be positive (|μ| in mas/yr, or the fractional change f)")
    return errs


def evaluate(record: dict, spec: dict) -> dict:
    return evaluate_ctx(context(record), spec)


def evaluate_ctx(ctx: dict, spec: dict) -> dict:
    """The same evaluation from a precomputed context (the browser runs this on the recorded context: intelcore.oracleEvaluate)."""
    q = spec["question"]
    rows, assumptions, warnings = [], [], []
    if q == "motion":
        if len(ctx["visits"]) < 2 or not ctx["validated"]:
            return {"method": METHOD, "available": False, "why": "the slope-error formula could not be validated against the recorded fit"}
        mu = spec.get("h1_value") or ctx["recorded_pm_mas_yr"]
        if not mu:
            return {"method": METHOD, "available": False, "why": "give |μ| for H1: the record has no motion estimate"}
        t = [v["t_yr"] for v in ctx["visits"]]
        s = [v["sigma_mas"] for v in ctx["visits"]]
        med = statistics.median(s)
        for i, c in enumerate([{"label": "recorded visits only", "added_years_after_last": []}] + spec["candidates"]):
            add = c.get("added_years_after_last", [])
            k = c.get("error_factor", 1.0)
            tt = t + [max(t) + x for x in add]
            ss = s + [med * k] * len(add)
            sp = futurelab.sigma_pm(tt, ss)
            S = mu / sp if sp else None
            rows.append({"id": "recorded" if i == 0 else f"c{i}", "label": c.get("label") or f"candidate {i}", "added_visits": len(add),
                         "baseline_yr": max(tt) - min(tt), "sigma_mu_mas_yr": sp, "expected_significance": S,
                         "expected_delta_chi2": (S * S + 1) if S is not None else None, "min_detectable_mu_mas_yr": THRESHOLD * sp if sp else None,
                         "discriminates": bool(S is not None and S >= THRESHOLD), "hypothetical": i > 0})
        assumptions = [f"H1: linear motion at |μ| = {mu:.4g} mas/yr ({'your value' if spec.get('h1_value') else 'the recorded estimate'})",
                       f"an added visit has the median recorded per-visit error × factor ({med:.4g} mas × factor, worse axis)",
                       "independent Gaussian errors; no χ²ν inflation", "the worse axis is used for S (conservative)",
                       "no telescope schedule, pointing or availability is implied"]
        if not spec.get("h1_value") and ctx["recorded_pm_mas_yr"]:
            warnings.append("H1 uses the recorded estimate of |μ|, which is itself uncertain; try a smaller |μ| to see what would still be detected")
    else:
        f = spec.get("h1_value") or 0.05
        k = max(1.0, ctx["error_scale"])
        for i, c in enumerate([{"label": "recorded precision", "fractional_error": ctx["median_fractional_error"]}] + spec["candidates"]):
            e = c.get("fractional_error")
            if not e:
                rows.append({"id": "recorded", "label": "recorded precision", "available": False})
                continue
            S = f / (math.sqrt(2) * e * k)
            rows.append({"id": "recorded" if i == 0 else f"c{i}", "label": c.get("label") or f"candidate {i}", "fractional_error": e,
                         "expected_significance": S, "expected_delta_chi2": S * S + 1, "max_error_for_detection": f / (THRESHOLD * math.sqrt(2) * k),
                         "discriminates": S >= THRESHOLD, "hypothetical": i > 0})
        assumptions = [f"H1: a fractional change f = {f:g} between two epochs", f"the recorded CALCHECK error scale {k:.4g} applies to new data",
                       "one wavelength-matched pair with equal fractional errors", "|z| ≥ 5 in one pair (ASSESS-2 also needs consistent pairs)",
                       "no schedule is implied"]
        if ctx["error_scale"] and ctx["error_scale"] > 1.5:
            warnings.append(f"the recorded error scale {ctx['error_scale']:.3g} exceeds 1.5: the error model underestimates the scatter (ASL M1)")
    ranked = sorted([r for r in rows if r.get("hypothetical") and r.get("expected_significance") is not None],
                    key=lambda r: (-r["expected_significance"], r.get("added_visits", 0), r["id"]))
    return {"method": METHOD, "available": True, "question": q, "hypotheses": {"H0": "static source" if q == "motion" else "no brightness change",
            "H1": assumptions[0]}, "rows": rows, "ranking": [r["id"] for r in ranked],
            "ranking_rule": "largest expected significance first; ties by fewer added visits; this is an ordering under the stated model, not an optimum",
            "assumptions": assumptions, "warnings": warnings, "information_gain": None,
            "information_gain_note": "not computed: bits of information need prior probabilities for H0 and H1, which the record does not contain",
            "context": {k: v for k, v in ctx.items() if k != "validation"}, "hypothetical": True,
            "note": "Hypothetical planning only. Nothing is scheduled; no instrument availability is implied."}


def negotiation(disc: dict) -> dict:
    out = []
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        viable = [h for h in q["hypotheses"] if h.get("overall") in VIABLE]
        for i, a in enumerate(viable):
            for b in viable[i + 1:]:
                ta = [t for t in a.get("tests", []) if t["status"] != "consistent"]
                tb = [t for t in b.get("tests", []) if t["status"] != "consistent"]
                ida, idb = {t["id"] for t in ta}, {t["id"] for t in tb}
                out.append({"question": q["question"], "a": a["id"], "b": b["id"], "a_status": a["overall"], "b_status": b["overall"],
                            "decides_a": [{"test": t["id"], "status": t["status"], "rule": t.get("rule"), "needs": t.get("detail")} for t in ta if t["id"] not in idb],
                            "decides_b": [{"test": t["id"], "status": t["status"], "rule": t.get("rule"), "needs": t.get("detail")} for t in tb if t["id"] not in ida],
                            "shared_open": sorted(ida & idb)})
    return {"method": METHOD_NEG, "pairs": out,
            "note": "For two viable explanations, the open tests unique to each are the evidence that would move one without the other. No "
                    "test is predicted to come out either way; the table says what to look at, not what will be found."}
