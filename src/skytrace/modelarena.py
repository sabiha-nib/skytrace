"""Model arena (MODELS-1): competing models fitted to the same recorded visit positions.

Models: M0 static position (weighted mean per axis, 1 parameter) and M1 linear motion (weighted least squares per axis,
2 parameters), both on the visit means and their recorded errors (LINFIT-EPOCH-1), with the visits the pipeline rejected
left out. Comparison criteria, all standard for Gaussian errors: χ², degrees of freedom, χ²ν, Δχ² between the nested models
with its Δk, and AIC = χ² + 2k. No p-value or probability is reported, and a model is never "ranked" by a score of
our own: lower AIC is preferred under AIC's assumptions (independent Gaussian errors, correct error scale). The better-
fitting model is not thereby the physical explanation. M1 is validated by reproducing the pipeline's fit.
Leave-one-visit-out refits show model sensitivity. Brightness models are not implemented (the pipeline compares pairs;
no light-curve model is registered).
"""

from __future__ import annotations

METHOD = "MODELS-1"


def _wmean(t, y, s):
    w = [1 / x ** 2 for x in s]
    m = sum(wi * yi for wi, yi in zip(w, y)) / sum(w)
    chi2 = sum(((yi - m) / si) ** 2 for yi, si in zip(y, s))
    return {"params": {"position": m}, "chi2": chi2, "residuals": [yi - m for yi in y], "pred": [m] * len(y)}


def _wls(t, y, s):
    w = [1 / x ** 2 for x in s]
    sw, st, sy = sum(w), sum(wi * ti for wi, ti in zip(w, t)), sum(wi * yi for wi, yi in zip(w, y))
    stt, sty = sum(wi * ti * ti for wi, ti in zip(w, t)), sum(wi * ti * yi for wi, ti, yi in zip(w, t, y))
    det = sw * stt - st * st
    b = (sw * sty - st * sy) / det
    a = (sy - b * st) / sw
    pred = [a + b * ti for ti in t]
    chi2 = sum(((yi - pi) / si) ** 2 for yi, pi, si in zip(y, pred, s))
    return {"params": {"position": a, "pm": b}, "sigma_pm": (sw / det) ** 0.5, "chi2": chi2, "residuals": [yi - pi for yi, pi in zip(y, pred)], "pred": pred}


def arena(record: dict) -> dict:
    a = next((e for e in record["events"] if e["step"] == "astrometry"), None)
    ad = (a or {}).get("data") or {}
    eps = ad.get("epochs", [])
    fit = ad.get("fit") or {}
    rej = set(fit.get("rejected") or [])
    pts = [(j, e) for j, e in enumerate(eps) if j not in rej]
    if len(pts) < 2:
        return {"method": METHOD, "available": False, "reason": f"{len(pts)} usable visit(s); comparing a static and a moving model needs at least two"}
    t0 = sum(e["t_mjd"] for _, e in pts) / len(pts)
    t = [(e["t_mjd"] - t0) / 365.25 for _, e in pts]
    axes = {}
    for ax, label in (("xi", "ξ (east)"), ("eta", "η (north)")):
        y = [e[f"{ax}_mas"] for _, e in pts]
        s = [e[f"sig_{ax}_mas"] for _, e in pts]
        m0, m1 = _wmean(t, y, s), _wls(t, y, s)
        n = len(y)
        rows = []
        for mid, name, k, m in (("M0", "static position", 1, m0), ("M1", "linear motion", 2, m1)):
            dof = n - k
            rows.append({"model": mid, "name": name, "k": k, "params": m["params"], "chi2": m["chi2"], "dof": dof,
                         "reduced_chi2": (m["chi2"] / dof) if dof > 0 else None, "aic": m["chi2"] + 2 * k,
                         "residuals_mas": m["residuals"], "sigma_pm": m.get("sigma_pm")})
        sens = []
        if n >= 3:
            for drop in range(n):
                keep = [i for i in range(n) if i != drop]
                r = _wls([t[i] for i in keep], [y[i] for i in keep], [s[i] for i in keep])
                sens.append({"dropped_visit": pts[drop][0], "pm": r["params"]["pm"]})
        rec_pm = fit.get(f"pm_{ax}_mas_yr")
        axes[ax] = {"label": label, "models": rows, "delta_chi2": m0["chi2"] - m1["chi2"], "delta_k": 1,
                    "delta_aic": rows[0]["aic"] - rows[1]["aic"], "leave_one_out": sens,
                    "validation": {"pipeline_pm": rec_pm, "refit_pm": m1["params"]["pm"],
                                   "agrees": rec_pm is not None and abs(rec_pm - m1["params"]["pm"]) <= 1e-6 * max(1.0, abs(rec_pm))}}
    return {"method": METHOD, "available": True, "visits": [{"index": j, "t_mjd": e["t_mjd"], "t_yr": ti} for (j, e), ti in zip(pts, t)],
            "rejected_visits": sorted(rej), "axes": axes,
            "criteria": ["χ² and χ²ν (fit quality given the recorded errors)", "Δχ² between nested models with Δk = 1",
                         "AIC = χ² + 2k (lower preferred under its assumptions)", "leave-one-visit-out refits (sensitivity)"],
            "brightness_models": "not implemented: no light-curve model is registered; brightness is compared pairwise (PAIRDIFF-1/2)",
            "note": "The better-fitting model is the better description of these points under these errors, not necessarily the physical explanation."}
