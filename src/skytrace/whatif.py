"""WHATIF-1: the cosmic what-if engine — the six counterfactual questions of the Phase 9 brief, each answered only where a valid
method exists.

Each question states the assumption it changes, keeps the baseline untouched, and is then one of:

  computed here     recalculated now from the recorded inputs with an existing method (ASSESS-2 re-assessment through
                    CF-1, or the weighted least-squares refit that reproduces the recorded motion fit), with the conclusions
                    that changed and those that stayed
  scenario          a CF-1 scenario that re-runs the pipeline (Counterfactual Lab); the spec is given, nothing is guessed
  routed            answered by another engine that already holds the method (INSTCHECK-1, HYPO-1 with EVNEG-1)
  no valid method   refused, with the reason: nothing is approximated

  W1 larger measurement uncertainty     computed: brightness re-assessed with photometric errors × 1.5 and × 2 (simulated)
  W2 an observation excluded            computed: brightness re-assessed without the pairs of one detector (the remaining
                                        recorded pairs; references and calibration unchanged — the full re-run is the
                                        Counterfactual Lab's exclusion scenario), and the motion refit without one visit
  W3 the background model is wrong      no valid method: APPHOT-1 has one background estimator (annulus median) and no
                                        alternative is registered
  W4 the signal is instrumental         routed: INSTCHECK-1, plus the re-analysis that removes each instrumental cause
                                        (CAUSAL-1 interventions, CF-1 scenarios)
  W5 another hypothesis explains it     routed: HYPO-1 statuses of the competing explanations and EVNEG-1's distinguishing tests
  W6 a new observation contradicts it   computed for motion: a hypothetical visit at the static position (or on the fitted
                                        track), refit with the validated formula; for brightness, no valid method (a new pair
                                        needs fluxes, errors and reference ratios for an exposure that does not exist)

Every computed result is hypothetical, never stored as an observation, and never written into the record.
"""

from __future__ import annotations

import math

from . import counterfactual as cf, modelarena

METHOD = "WHATIF-1"
KINDS = ["computed here", "scenario", "routed", "no valid method"]
QUESTIONS = [("W1", "What if the measurement uncertainty were larger?"), ("W2", "What if a particular observation were excluded?"),
             ("W3", "What if the assumed background model were incorrect?"), ("W4", "What if the signal were produced by an instrumental effect?"),
             ("W5", "What if another hypothesis explained the same measurements?"), ("W6", "What if an additional observation contradicted the current interpretation?")]
DETECT = 5.0


def _outs(record):
    return {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}


def changes(base: dict, new: dict) -> dict:
    """Which conclusions changed category and which stayed."""
    ch, st = [], []
    for q in sorted(set(base) | set(new)):
        a, b = (base.get(q) or {}).get("category"), (new.get(q) or {}).get("category")
        (ch if a != b else st).append({"question": q, "baseline": a, "scenario": b})
    return {"changed": ch, "stable": st}


def _det(key):
    s = str(key or "")
    return int(s[-1]) if len(s) > 2 and s[-2] == "D" and s[-1].isdigit() else None


# ---------------------------------------------------------------------------- motion refit (validated before use)
def _visits(record):
    a = next((e for e in record["events"] if e["step"] == "astrometry"), None)
    ad = (a or {}).get("data") or {}
    fit = ad.get("fit") or {}
    rej = set(fit.get("rejected") or [])
    return [(j, e) for j, e in enumerate(ad.get("epochs", [])) if j not in rej], fit


def refit(t_yr: list, xi: list, sxi: list, eta: list, seta: list) -> dict:
    """LINFIT-style weighted least squares per axis with √χ²ν inflation when χ²ν > 1, and the ASSESS-2 significance."""
    out = {}
    for ax, y, s in (("xi", xi, sxi), ("eta", eta, seta)):
        r = modelarena._wls(t_yr, y, s)
        dof = len(y) - 2
        rc = r["chi2"] / dof if dof > 0 else None
        out[ax] = {"pm": r["params"]["pm"], "sigma": r["sigma_pm"] * math.sqrt(max(1.0, rc)) if rc is not None else r["sigma_pm"], "reduced_chi2": rc}
    px, pe, sx, se = out["xi"]["pm"], out["eta"]["pm"], out["xi"]["sigma"], out["eta"]["sigma"]
    pm = math.hypot(px, pe)
    sig = math.hypot(sx * px, se * pe) / pm if pm > 0 else math.sqrt((sx ** 2 + se ** 2) / 2)
    return {"axes": out, "pm_mas_yr": pm, "sigma_mas_yr": sig, "snr": pm / sig if sig > 0 else 0.0}


def motion_context(record: dict) -> dict:
    pts, fit = _visits(record)
    if len(pts) < 3:
        return {"available": False, "why": f"{len(pts)} usable visit(s): a refit with one visit added or removed needs at least three"}
    t0 = sum(e["t_mjd"] for _, e in pts) / len(pts)
    t = [(e["t_mjd"] - t0) / 365.25 for _, e in pts]
    cols = {k: [e[k] for _, e in pts] for k in ("xi_mas", "sig_xi_mas", "eta_mas", "sig_eta_mas")}
    r = refit(t, cols["xi_mas"], cols["sig_xi_mas"], cols["eta_mas"], cols["sig_eta_mas"])
    ok = all(fit.get(f"pm_{ax}_mas_yr") is not None and abs(r["axes"][ax]["pm"] - fit[f"pm_{ax}_mas_yr"]) <= 1e-6 * max(1, abs(fit[f"pm_{ax}_mas_yr"]))
             and fit.get(f"sig_{ax}") is not None and abs(r["axes"][ax]["sigma"] - fit[f"sig_{ax}"]) <= 1e-6 * max(1, abs(fit[f"sig_{ax}"])) for ax in ("xi", "eta"))
    return {"available": True, "validated": ok, "visits": [{"index": j, "t_yr": ti, "xi_mas": e["xi_mas"], "sig_xi_mas": e["sig_xi_mas"], "eta_mas": e["eta_mas"],
            "sig_eta_mas": e["sig_eta_mas"]} for (j, e), ti in zip(pts, t)], "refit": r,
            "recorded": {ax: {"pm": fit.get(f"pm_{ax}_mas_yr"), "sigma": fit.get(f"sig_{ax}")} for ax in ("xi", "eta")},
            "rule": "the refit must reproduce the recorded proper motion and σ on both axes (relative 1e-6) before any what-if is computed"}


def hypothetical_visit(ctx: dict, dt_years: float, position: str = "static", error_factor: float = 1.0) -> dict:
    """A visit dt_years after the last one, at the static position (the weighted mean: contradicts motion) or on the fitted
    track (supports it), with the median recorded per-visit error × error_factor. Hypothetical; never stored."""
    if not ctx.get("available") or not ctx.get("validated"):
        return {"available": False, "why": ctx.get("why") or "the refit does not reproduce the recorded fit, so no what-if is computed"}
    if not (0 < dt_years <= 20) or not (0.1 <= error_factor <= 10) or position not in ("static", "track"):
        return {"available": False, "why": "dt_years must be in (0, 20], error_factor in [0.1, 10], position 'static' or 'track'"}
    v = ctx["visits"]
    t = [x["t_yr"] for x in v]
    tn = max(t) + dt_years
    new = {}
    for ax in ("xi", "eta"):
        y, s = [x[f"{ax}_mas"] for x in v], [x[f"sig_{ax}_mas"] for x in v]
        if position == "static":
            w = [1 / q ** 2 for q in s]
            new[ax] = sum(wi * yi for wi, yi in zip(w, y)) / sum(w)
        else:
            r = modelarena._wls(t, y, s)
            new[ax] = r["params"]["position"] + r["params"]["pm"] * tn
        new[f"sig_{ax}"] = sorted(s)[len(s) // 2] * error_factor
    r = refit(t + [tn], [x["xi_mas"] for x in v] + [new["xi"]], [x["sig_xi_mas"] for x in v] + [new["sig_xi"]],
              [x["eta_mas"] for x in v] + [new["eta"]], [x["sig_eta_mas"] for x in v] + [new["sig_eta"]])
    b = ctx["refit"]
    return {"available": True, "hypothetical": True, "visit": {"t_yr": tn, "position": position, **new},
            "before": {"pm_mas_yr": b["pm_mas_yr"], "sigma_mas_yr": b["sigma_mas_yr"], "snr": b["snr"], "detected": b["snr"] >= DETECT},
            "after": {"pm_mas_yr": r["pm_mas_yr"], "sigma_mas_yr": r["sigma_mas_yr"], "snr": r["snr"], "detected": r["snr"] >= DETECT,
                      "reduced_chi2": {ax: r["axes"][ax]["reduced_chi2"] for ax in ("xi", "eta")}},
            "rule": f"detection |μ|/σ ≥ {DETECT:g} (ASSESS-2); only the fit significance is recomputed: ASSESS-2's catalogue and registration checks need "
                    "fields a hypothetical visit does not have",
            "note": "Hypothetical: a visit that was not observed. It is never stored as an observation."}


# ---------------------------------------------------------------------------- the six questions
def engine(record: dict, disc: dict, inst: dict | None = None, causal_lab: dict | None = None, negotiation: dict | None = None) -> dict:
    base = _outs(record)
    ev = cf._ev(record)
    pairs = (ev.get("variability", {}).get("data") or {}).get("pairs") or []
    rows = []

    def q(wid, kind, changed_assumption, detail, **extra):
        rows.append({"id": wid, "question": dict(QUESTIONS)[wid], "kind": kind, "changed_assumption": changed_assumption, "detail": detail, **extra})
    # W1
    if pairs:
        runs = []
        for k in (1.5, 2.0):
            new = cf.reassess(record, flux_pairs=cf._scale_pairs(pairs, k))
            runs.append({"setting": f"photometric errors × {k:g}", "label": "simulated", **changes(base, new)})
        q("W1", "computed here", "the per-exposure photometric uncertainties are larger than recorded", "ASSESS-2 re-assessment of the recorded pairs (CF-1, exact)",
          runs=runs, scenario={"kind": "error_scale", "change": {"photometric_error_factor": 2.0}})
    else:
        q("W1", "no valid method", "larger photometric uncertainties", "no wavelength-matched pair was compared")
    # W2
    runs = []
    for d in sorted({_det(p.get("a")) for p in pairs} - {None}):
        keep = [p for p in pairs if _det(p.get("a")) != d and _det(p.get("b")) != d]
        new = cf.reassess(record, flux_pairs=keep)
        runs.append({"setting": f"without detector D{d}'s pairs ({len(pairs) - len(keep)} removed)", "label": "derived", "question": "variability",
                     **{k: [c for c in v if c["question"] == "variability"] for k, v in changes(base, new).items()}})
    mc = motion_context(record)
    if mc.get("available") and mc.get("validated"):
        v = mc["visits"]
        for i, x in enumerate(v):
            keep = [y for j, y in enumerate(v) if j != i]
            if len(keep) >= 3:
                r = refit([y["t_yr"] for y in keep], [y["xi_mas"] for y in keep], [y["sig_xi_mas"] for y in keep], [y["eta_mas"] for y in keep], [y["sig_eta_mas"] for y in keep])
                runs.append({"setting": f"without visit {x['index']}", "label": "derived", "question": "motion", "snr_before": mc["refit"]["snr"], "snr_after": r["snr"],
                             "detected_before": mc["refit"]["snr"] >= DETECT, "detected_after": r["snr"] >= DETECT})
    q("W2", "computed here" if runs else "no valid method", "an observation (one detector's exposures, or one visit) is left out",
      "brightness: ASSESS-2 on the remaining recorded pairs (the full pipeline re-run is the Counterfactual Lab's exclusion scenario); motion: the validated refit"
      if runs else "neither pairs nor at least three visits are recorded", runs=runs, scenario={"kind": "exclusion", "change": {"detectors": [1]}})
    # W3
    q("W3", "no valid method", "the sky background under the aperture is not the annulus median",
      "APPHOT-1 has one background estimator (annulus median) and no alternative is registered; a different background model cannot be recalculated "
      "here, so nothing is approximated. What would unblock it: a registered alternative background method with known-answer tests.")
    # W4
    ints = [{"explanation": m["id"], "re_analysis": m["intervention"]} for m in (causal_lab or {}).get("models", []) if m.get("intervention")
            and m["id"] in ("V-CALIB", "V-ERRMODEL", "V-WAVELENGTH", "M-PARALLAX")]
    q("W4", "routed", "the effect comes from the measurement process, not the source",
      "the instrumental reality check (INSTCHECK-1) lists each known instrumental explanation and whether a rule rules it out; the re-analyses below "
      "remove one instrumental cause each (Counterfactual Lab)", open=[r["name"] for r in (inst or {}).get("checks", []) if r["state"] in ("not ruled out", "not testable here")],
      re_analyses=ints)
    # W5
    alts = [{"question": qq["question"], "id": h["id"], "status": h.get("overall")} for qq in (disc.get("hypotheses") or {}).get("questions", []) for h in qq["hypotheses"]]
    q("W5", "routed", "a competing explanation accounts for the same measurements",
      "HYPO-1 evaluates every competing explanation by stated rules; for two that both remain viable, EVNEG-1 lists the tests that would separate them",
      alternatives=alts, n_pairs=len((negotiation or {}).get("pairs", [])))
    # W6
    if mc.get("available") and mc.get("validated"):
        q("W6", "computed here", "a new visit one year after the last finds the source at its mean (static) position",
          "the validated motion refit with one hypothetical visit added", motion=hypothetical_visit(mc, 1.0, "static"),
          variability="no valid method: a new pair needs fluxes, errors and reference ratios for an exposure that does not exist")
    else:
        q("W6", "no valid method", "a contradicting new observation", mc.get("why") or "the refit does not reproduce the recorded fit")
    return {"method": METHOD, "record": record.get("content_hash"), "kinds": KINDS, "questions": rows, "motion_context": mc, "detect_threshold": DETECT,
            "note": "Every result here is hypothetical and leaves the record untouched. A question is recalculated only where a valid method exists; "
                    "otherwise it is refused with the reason."}
