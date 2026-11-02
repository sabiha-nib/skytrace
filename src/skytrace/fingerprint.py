"""FINGERPRINT-1: the discovery sensitivity fingerprint — how much each conclusion depends on the choices behind it.

For each of a run's three questions, six dimensions. Each is recomputed from the recorded inputs with an existing method,
or marked 'not tested' with what would test it; nothing is estimated:

  F1 thresholds        ASSESS-2 re-run at the lower and upper bounds a reader might choose (|z| ≥ 3 and ≥ 8 for brightness,
                       3σ and 8σ for motion) — CF-1 re-assessment, exact (re-assessment with no change reproduces the record)
  F2 calibration       brightness re-assessed with the reference calibration removed (PAIRDIFF-1 values only)
  F3 error model       re-assessed with photometric uncertainties × 1.5 and × 2 (simulated perturbations)
  F4 preprocessing     STAB-1: the analysis re-run under five small parameter perturbations (aperture, fit box, wavelength
                       tolerance); available when a stability result is given, otherwise 'not tested'
  F5 model selection   MODELS-1: whether the static or the linear model has the lower AIC, and whether that agrees with the
                       motion category
  F6 data selection    MODELS-1 leave-one-visit-out: the largest change in the fitted motion when one visit is dropped,
                       relative to the recorded σ (motion only)

States: 'stable' (the category does not change), 'changes' (the category changes: the conclusion depends on this choice),
'not tested' and 'not applicable'. No overall robustness score is computed.
"""

from __future__ import annotations

import math

from . import counterfactual as cf, modelarena

METHOD = "FINGERPRINT-1"
DIMENSIONS = [("F1", "thresholds"), ("F2", "calibration"), ("F3", "error model"), ("F4", "preprocessing"), ("F5", "model selection"),
              ("F6", "data selection")]
STATES = ["stable", "changes", "not tested", "not applicable"]
THR = {"variability": ("variability_z", (3.0, 8.0)), "motion": ("motion_detect_sigma", (3.0, 8.0))}
POSITIVE_MOTION = ("motion_detected", "motion_inconsistent")


def _cat(outs: dict, q: str):
    return (outs.get(q) or {}).get("category")


def fingerprint(record: dict, stability: dict | None = None) -> dict:
    base = {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}
    ev = cf._ev(record)
    pairs = (ev.get("variability", {}).get("data") or {}).get("pairs")
    arena = modelarena.arena(record)
    out = []
    for q in ("data_quality", "motion", "variability"):
        if q not in base:
            continue
        b = _cat(base, q)
        dims = []

        def dim(did, state, detail, runs=None):
            dims.append({"id": did, "name": dict(DIMENSIONS)[did], "state": state, "detail": detail, "runs": runs or []})
        # F1
        if q in THR:
            key, (lo, hi) = THR[q]
            runs = [{"setting": f"{key} = {v:g}", "category": _cat(cf.reassess(record, thresholds={key: v}), q)} for v in (lo, hi)]
            ch = [r for r in runs if r["category"] != b]
            dim("F1", "changes" if ch else "stable", (f"category becomes {', '.join(r['category'] + ' at ' + r['setting'] for r in ch)}" if ch
                                                      else f"same category at {key} = {lo:g} and {hi:g}"), runs)
        else:
            dim("F1", "not applicable", "data quality has no significance threshold")
        # F2, F3
        if q == "variability" and pairs:
            r2 = _cat(cf.reassess(record, flux_pairs=cf._raw_only(pairs)), q)
            dim("F2", "changes" if r2 != b else "stable", f"without reference calibration: {r2}", [{"setting": "PAIRDIFF-1 values only", "category": r2}])
            runs = [{"setting": f"photometric errors × {k:g}", "category": _cat(cf.reassess(record, flux_pairs=cf._scale_pairs(pairs, k)), q)} for k in (1.5, 2.0)]
            ch = [r for r in runs if r["category"] != b]
            dim("F3", "changes" if ch else "stable", "; ".join(f"{r['setting']}: {r['category']}" for r in runs), runs)
        else:
            dim("F2", "not applicable", "calibration enters brightness comparisons only")
            dim("F3", "not applicable" if q != "motion" else "not tested",
                "photometric errors do not enter this outcome" if q != "motion" else
                "astrometric error scaling is not a registered scenario; MODELS-1 χ²ν shows how well the recorded errors describe the visits")
        # F4
        if stability and stability.get("runs"):
            ch = [r["label"] for r in stability["runs"] if q in (r.get("changed") or {})]
            dim("F4", "changes" if ch else "stable", (f"category changes under {', '.join(ch)}" if ch else f"same category under all {len(stability['runs'])} perturbations"),
                [{"setting": r["label"], "category": (r.get("categories") or {}).get(q)} for r in stability["runs"]])
        else:
            dim("F4", "not tested", "run the stability check (STAB-1) to fill this dimension")
        # F5, F6
        if q == "motion" and arena.get("available"):
            prefer = {ax: ("M1 linear" if A["delta_aic"] > 0 else "M0 static") for ax, A in arena["axes"].items()}
            moving = any(p.startswith("M1") for p in prefer.values())
            agrees = moving == (b in POSITIVE_MOTION)
            dim("F5", "stable" if agrees else "changes",
                f"lower AIC: {', '.join(f'{ax} {p}' for ax, p in prefer.items())}; " + ("agrees with" if agrees else "differs from") + f" the category {b}",
                [{"setting": f"axis {ax}", "category": p} for ax, p in prefer.items()])
            sig = next((e for e in record["events"] if e["step"] == "astrometry"), {}).get("data", {}).get("fit", {})
            worst = []
            for ax, A in arena["axes"].items():
                s = sig.get(f"sig_{ax}")
                rec = A["validation"]["refit_pm"]
                for r in A["leave_one_out"]:
                    if s:
                        worst.append((abs(r["pm"] - rec) / s, ax, r["dropped_visit"]))
            if worst:
                w = max(worst)
                dim("F6", "changes" if w[0] >= 1 else "stable",
                    f"dropping visit {w[2]} moves the {w[1]} motion by {w[0]:.2f} σ" + (" (≥ 1σ: the fit leans on single visits)" if w[0] >= 1 else ""),
                    [{"setting": f"drop visit {d} ({ax})", "shift_sigma": round(x, 3)} for x, ax, d in sorted(worst, reverse=True)[:6]])
            else:
                dim("F6", "not tested", "leave-one-visit-out needs at least three visits")
        else:
            dim("F5", "not applicable", "model comparison is registered for motion only (no brightness model)")
            dim("F6", "not applicable" if q != "motion" else "not tested", "visit selection is tested for the motion fit only" if q != "motion" else arena.get("reason", ""))
        out.append({"question": q, "category": b, "dimensions": dims, "counts": {s: sum(d["state"] == s for d in dims) for s in STATES},
                    "depends_on": [d["name"] for d in dims if d["state"] == "changes"]})
    return {"method": METHOD, "dimensions": DIMENSIONS, "states": STATES, "record": record.get("content_hash"), "questions": out,
            "note": "Each dimension is a recomputation from recorded inputs. 'Changes' names a choice the conclusion depends on; it does not say "
                    "which choice is right. No robustness score is computed."}


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
