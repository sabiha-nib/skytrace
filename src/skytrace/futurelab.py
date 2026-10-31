"""FutureLab (FUTURE-1): hypothetical scenarios for future measurements, computed with validated formulas.

Every scenario is hypothetical: it states its assumptions and never describes a scheduled observation. Calculations:
  * motion sensitivity for a set of visit times with per-visit errors σ_i: σ_pm = √(Σw / (Σw·Σwt² − (Σwt)²)), w = 1/σ²
    (the weighted least-squares slope error). The formula is validated by reproducing the recorded fit's σ from the
    recorded visits (`validate`), before any hypothetical visit is added; 5σ sensitivity = 5 σ_pm.
  * pair precision: to detect a fractional change f at |z| ≥ 5 in one matched pair with equal errors, each flux needs
    σ ≤ f F / (5 √2 × scale), where scale is the recorded CALCHECK error scale (≥ 1).
  * metadata scenarios: which missing inputs (DISC-1, HYPO-1) would make which question or test evaluable.
Mirrored in web/js/epistemiccore.js for interactive use (parity-tested).
"""

from __future__ import annotations

import math
import statistics

METHOD = "FUTURE-1"


def sigma_pm(times_yr: list, sigmas: list) -> float | None:
    if len(times_yr) < 2:
        return None
    w = [1 / s ** 2 for s in sigmas]
    sw = sum(w)
    st = sum(wi * t for wi, t in zip(w, times_yr))
    stt = sum(wi * t * t for wi, t in zip(w, times_yr))
    det = sw * stt - st * st
    return math.sqrt(sw / det) if det > 0 else None


def pair_precision(fraction: float, flux_ujy: float, scale: float = 1.0) -> float:
    return fraction * flux_ujy / (5 * math.sqrt(2) * max(1.0, scale))


def _visits(record):
    a = next((e for e in record["events"] if e["step"] == "astrometry"), None)
    ad = (a or {}).get("data") or {}
    fit = ad.get("fit") or {}
    rej = set(fit.get("rejected") or [])
    eps = [e for j, e in enumerate(ad.get("epochs", [])) if j not in rej]
    return eps, fit


def validate(record: dict) -> dict:
    eps, fit = _visits(record)
    if len(eps) < 2:
        return {"valid": False, "reason": "fewer than two visits"}
    t = [e["t_mjd"] / 365.25 for e in eps]
    out = {}
    for ax, key in (("xi", "sig_xi"), ("eta", "sig_eta")):
        s = sigma_pm(t, [e[f"sig_{ax}_mas"] for e in eps])
        infl = max(1.0, math.sqrt(fit.get("reduced_chi2") or 0)) if fit.get("reduced_chi2") else 1.0
        rec = fit.get(key)
        out[ax] = {"formula": s, "formula_inflated": s * infl if s else None, "recorded": rec,
                   "agrees": bool(rec and s and abs(s * infl - rec) <= 1e-6 * rec)}
    return {"valid": all(v["agrees"] for v in out.values()), "axes": out,
            "rule": "the formula with the recorded visits (and the recorded √χ²ν inflation when χ²ν > 1) must reproduce the recorded σ within 1e-6"}


def scenarios(record: dict, disc: dict) -> dict:
    eps, fit = _visits(record)
    val = validate(record)
    out = {"method": METHOD, "hypothetical": True, "validation": val, "scenarios": []}
    if len(eps) >= 2 and val["valid"]:
        t = [e["t_mjd"] / 365.25 for e in eps]
        sig = statistics.median([max(e["sig_xi_mas"], e["sig_eta_mas"]) for e in eps])
        base = max(sigma_pm(t, [e["sig_xi_mas"] for e in eps]), sigma_pm(t, [e["sig_eta_mas"] for e in eps]))
        rows = [{"label": "recorded visits", "added": 0, "baseline_yr": max(t) - min(t), "sigma_pm": base, "sensitivity_5sigma": 5 * base, "hypothetical": False}]
        for extra_yr in (0.5, 1.0, 2.0, 4.0):
            tt = t + [max(t) + extra_yr]
            ss = [max(e["sig_xi_mas"], e["sig_eta_mas"]) for e in eps] + [sig]
            s = sigma_pm(tt, ss)
            rows.append({"label": f"one more visit {extra_yr:g} yr after the last", "added": 1, "baseline_yr": max(tt) - min(tt), "sigma_pm": s,
                         "sensitivity_5sigma": 5 * s, "hypothetical": True})
        out["scenarios"].append({"id": "baseline", "title": "How would a longer time baseline change motion sensitivity?", "rows": rows,
                                 "assumptions": [f"a hypothetical visit has the median recorded per-visit error ({sig:.1f} mas, worse axis)",
                                                 "motion stays linear", "no χ²ν inflation (the recorded errors describe the scatter)", "no telescope schedule is implied"]})
        T = max(t) - min(t)
        cad = []
        for n in range(2, 7):
            tt = [min(t) + T * i / (n - 1) for i in range(n)]
            s = sigma_pm(tt, [sig] * n)
            cad.append({"label": f"{n} evenly spaced visits over {T:.2f} yr", "visits": n, "sigma_pm": s, "sensitivity_5sigma": 5 * s, "hypothetical": True})
        out["scenarios"].append({"id": "cadence", "title": "How would the number of visits over the same baseline change it?", "rows": cad,
                                 "assumptions": [f"every visit has error {sig:.1f} mas", "the recorded baseline", "no schedule is implied"]})
    v = next((e for e in record["events"] if e["step"] == "variability"), None)
    if v:
        vd = v.get("data") or {}
        flux = statistics.median([p["flux_a_ujy"] for p in vd.get("pairs", []) if isinstance(p.get("flux_a_ujy"), (int, float))] or [0]) or None
        scale = (vd.get("calibration_check") or {}).get("error_scale") or 1.0
        errs = [p["err_a_ujy"] for p in vd.get("pairs", []) if isinstance(p.get("err_a_ujy"), (int, float))]
        rec_err = statistics.median(errs) if errs else None
        if flux:
            rows = [{"label": f"detect a {f * 100:g}% change in one pair", "fraction": f, "required_flux_err_ujy": pair_precision(f, flux, scale),
                     "recorded_median_flux_err_ujy": rec_err, "met_now": bool(rec_err and rec_err <= pair_precision(f, flux, scale)), "hypothetical": True}
                    for f in (0.01, 0.02, 0.05, 0.1, 0.25)]
            out["scenarios"].append({"id": "precision", "title": "What measurement precision would reveal a given brightness change?", "rows": rows,
                                     "assumptions": [f"median target flux {flux:.0f} µJy", f"recorded error scale {scale:.3f} applied", "equal errors in both exposures", "|z| ≥ 5 threshold (ASSESS-2)"]})
    miss = []
    for q in disc.get("questions", []):
        for m in (q.get("plan") or {}).get("missing_inputs", []):
            miss.append({"input": m.get("input") if isinstance(m, dict) else str(m), "unblocks": q["id"], "kind": "question"})
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q.get("hypotheses", []):
            for tt in h.get("tests", []):
                if tt["status"] == "evidence_unavailable":
                    miss.append({"input": tt.get("detail", "")[:160], "unblocks": f"{h['id']} / {tt['id']}", "kind": "test"})
    out["scenarios"].append({"id": "metadata", "title": "Which missing inputs would unblock a question or test?", "rows": miss[:20],
                             "assumptions": ["the listed input becomes available with the same quality as the recorded data"]})
    out["note"] = "Hypothetical scenarios only. They state what the formulas give under their assumptions; no observation is scheduled or implied."
    return out
