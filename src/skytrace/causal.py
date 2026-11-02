"""CAUSAL-1: the causality lab — competing causal models of each recorded effect, their confounders, temporal inspection and the
computational interventions that probe them.

The directed graph below is an assumption, documented here: how the measurement process can produce a flux difference or a
position change. It is not learned from the data. Each HYPO-1 explanation is read as a causal model: one cause node with a
directed path to the observed effect. For each model the lab reports five separate criteria — never a single verdict:

  C1 correlation                the effect is recorded (significant matched pairs; a motion fit with |μ|/σ ≥ 2)
  C2 temporal association       the per-visit values change monotonically with time: |Pearson r| ≥ 0.8 with ≥ 3 visits, on at
                                least one detector (descriptive; with so few points r is not a test)
  C3 mechanistic plausibility   a physical or instrumental mechanism is documented for the model (MECHANISM below)
  C4 causal hypothesis          the model is stated and HYPO-1 has not contradicted it
  C5 experimentally supported   requires an intervention on the cause itself. Archival sky observations allow none, so this
                                is never reached here; a counterfactual re-analysis intervenes on the analysis, not on the sky

Confounders of a model X → Y are the common ancestors of X and Y in the graph (a variable that influences both). Correlation
alone never establishes a causal relationship: a model meeting only C1 is labelled 'association only'.
"""

from __future__ import annotations

import math

METHOD = "CAUSAL-1"
VARIABLES = {
    "epoch": "time of the visit", "detector": "SPHEREx detector (D1–D6)", "wavelength": "wavelength at the target",
    "intrinsic_flux": "the source's own brightness", "calibration": "exposure-level photometric calibration", "neighbour": "light from an unresolved neighbour",
    "noise_model": "the per-pixel error model", "measured_flux": "aperture flux", "flux_difference": "matched-pair flux difference (the effect)",
    "proper_motion": "the source's proper motion", "parallax": "annual parallax", "registration": "per-exposure registration (plate solution)",
    "reference_frame": "motion of the reference stars", "chromatic": "colour- and detector-dependent centroid offsets",
    "true_position": "the source's true position", "measured_position": "measured position", "position_change": "fitted position change (the effect)"}
EDGES = [("epoch", "intrinsic_flux"), ("epoch", "calibration"), ("detector", "wavelength"), ("detector", "calibration"), ("wavelength", "measured_flux"),
         ("intrinsic_flux", "measured_flux"), ("calibration", "measured_flux"), ("neighbour", "measured_flux"), ("measured_flux", "flux_difference"),
         ("noise_model", "flux_difference"), ("epoch", "true_position"), ("proper_motion", "true_position"), ("parallax", "measured_position"),
         ("epoch", "parallax"), ("true_position", "measured_position"), ("registration", "measured_position"), ("reference_frame", "registration"),
         ("detector", "chromatic"), ("wavelength", "chromatic"), ("chromatic", "measured_position"), ("measured_position", "position_change"),
         ("epoch", "registration")]
EFFECT = {"variability": "flux_difference", "motion": "position_change"}
CAUSE = {"V-INTRINSIC": "intrinsic_flux", "V-CALIB": "calibration", "V-ERRMODEL": "noise_model", "V-WAVELENGTH": "wavelength", "V-BLEND": "neighbour",
         "M-CATALOGUE": "proper_motion", "M-STATIC": None, "M-REGISTRATION": "registration", "M-PARALLAX": "parallax", "M-REFS": "reference_frame",
         "M-CHROMATIC": "chromatic"}
MECHANISM = {"V-INTRINSIC": "stellar variability changes the emitted flux", "V-CALIB": "a zero-point change between exposures scales every flux",
             "V-ERRMODEL": "underestimated errors inflate |z| without any flux change", "V-WAVELENGTH": "a residual wavelength offset samples a different part of the spectrum",
             "V-BLEND": "a neighbour's light enters the aperture differently between exposures", "M-CATALOGUE": "the catalogued proper motion moves the source",
             "M-STATIC": "no motion: the null model", "M-REGISTRATION": "plate-solution errors shift measured positions",
             "M-PARALLAX": "annual parallax moves the apparent position with the Earth's orbit", "M-REFS": "moving reference stars shift the frame",
             "M-CHROMATIC": "colour-dependent centroids shift positions between detectors"}
INTERVENTION = {"V-CALIB": {"kind": "method", "change": {"variability_method": "PAIRDIFF-1"}, "what": "remove the reference calibration (PAIRDIFF-1)"},
                "V-ERRMODEL": {"kind": "error_scale", "change": {"factor": 1.5}, "what": "scale photometric errors by 1.5"},
                "V-WAVELENGTH": {"kind": "parameter", "change": {"wavelength_tolerance_channels": 0.3}, "what": "tighten wavelength matching to 0.3 channel"},
                "M-PARALLAX": {"kind": "parameter", "change": {"apply_parallax": False}, "what": "fit without the parallax correction"},
                "V-INTRINSIC": {"kind": "threshold", "change": {"variability_z": 8.0}, "what": "require |z| ≥ 8 (does the effect survive a stricter threshold?)"},
                "M-CATALOGUE": {"kind": "threshold", "change": {"motion_detect_sigma": 8.0}, "what": "require 8σ for detection"}}
R_TEMPORAL = 0.8
CRITERIA = [("C1", "correlation"), ("C2", "temporal association"), ("C3", "mechanistic plausibility"), ("C4", "causal hypothesis"),
            ("C5", "experimentally supported")]


def _parents():
    p = {v: set() for v in VARIABLES}
    for a, b in EDGES:
        p[b].add(a)
    return p


def ancestors(v: str) -> set:
    par = _parents()
    out, stack = set(), list(par.get(v, ()))
    while stack:
        x = stack.pop()
        if x not in out:
            out.add(x)
            stack.extend(par[x])
    return out


def confounders(x: str, y: str) -> list[str]:
    """Common ancestors of x and y, not counting x itself or anything only reachable through x."""
    ax = ancestors(x)
    par = _parents()
    # ancestors of y via paths that avoid x
    out, stack = set(), [p for p in par[y] if p != x]
    while stack:
        z = stack.pop()
        if z not in out and z != x:
            out.add(z)
            stack.extend(p for p in par[z] if p != x)
    return sorted(ax & out)


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def temporal(record: dict) -> dict:
    """Per-detector values against visit time: median aperture flux per visit (variability) and epoch positions (motion)."""
    meas = [e["data"] for e in record["events"] if e["step"] == "measure" and e["status"] == "ok" and isinstance((e.get("data") or {}).get("photometry"), dict)]
    by = {}
    for d in meas:
        f = (d.get("photometry") or {}).get("flux_ujy")
        t = d.get("mjd")
        if isinstance(f, (int, float)) and isinstance(t, (int, float)):
            by.setdefault(d.get("detector"), []).append((t, f))
    rows = []
    for det in sorted(k for k in by if k is not None):
        pts = sorted(by[det])
        groups = []
        for t, f in pts:                                                  # exposures less than 5 days apart form one visit
            if groups and t - groups[-1][-1][0] < 5.0:
                groups[-1].append((t, f))
            else:
                groups.append([(t, f)])
        vt = [sum(t for t, _ in v) / len(v) for v in groups]
        vf = [sorted(f for _, f in v)[len(v) // 2] for v in groups]
        r = _pearson(vt, vf)
        rows.append({"detector": det, "visits": len(vt), "t_mjd": vt, "flux_ujy": vf, "r": r,
                     "association": r is not None and abs(r) >= R_TEMPORAL and len(vt) >= 3})
    a = next((e for e in record["events"] if e["step"] == "astrometry" and e["status"] == "ok"), None)
    mot = None
    if a:
        eps = a["data"].get("epochs", [])
        t = [e["t_mjd"] for e in eps]
        xi = [e.get("xi_mas") for e in eps]
        eta = [e.get("eta_mas") for e in eps]
        if all(isinstance(v, (int, float)) for v in xi + eta) and len(t) >= 3:
            rx, ry = _pearson(t, xi), _pearson(t, eta)
            mot = {"visits": len(t), "r_xi": rx, "r_eta": ry,
                   "association": any(r is not None and abs(r) >= R_TEMPORAL for r in (rx, ry))}
        else:
            mot = {"visits": len(t), "r_xi": None, "r_eta": None, "association": False}
    return {"variability": rows, "motion": mot, "rule": f"|Pearson r| ≥ {R_TEMPORAL} with ≥ 3 visits (descriptive, not a test)"}


def lab(record: dict, disc: dict) -> dict:
    outs = {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}
    tmp = temporal(record)
    models = []
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        qq = q["question"]
        if qq not in EFFECT:
            continue
        o = outs.get(qq) or {}
        ev = o.get("evidence") or {}
        if qq == "variability":
            c1 = bool((ev.get("n_calibrated_above_threshold") or 0) > 0)
            c2 = any(r["association"] for r in tmp["variability"])
        else:
            pm, sg = ev.get("pm_measured_mas_yr"), ev.get("pm_sigma_mas_yr")
            c1 = bool(isinstance(pm, (int, float)) and isinstance(sg, (int, float)) and sg > 0 and abs(pm) / sg >= 2)
            c2 = bool(tmp["motion"] and tmp["motion"]["association"])
        for h in q["hypotheses"]:
            cause = CAUSE.get(h["id"])
            contradicted = h.get("overall") == "contradicted"
            crit = {"C1": c1 and cause is not None, "C2": c2 and cause is not None, "C3": cause is not None and h["id"] in MECHANISM, "C4": cause is not None and not contradicted, "C5": False}
            label = ("contradicted by HYPO-1" if contradicted else "null model" if cause is None else
                     "association only" if crit["C1"] and not (crit["C2"] or crit["C3"]) else "causal hypothesis (not established)")
            models.append({"id": h["id"], "question": qq, "statement": h["statement"], "cause": cause, "effect": EFFECT[qq],
                           "mechanism": MECHANISM.get(h["id"]), "hypo_status": h.get("overall"), "criteria": crit, "label": label,
                           "confounders": confounders(cause, EFFECT[qq]) if cause else [],
                           "intervention": INTERVENTION.get(h["id"]), "C5_note": "no intervention on the sky is possible with archival observations"})
    return {"method": METHOD, "record": record.get("content_hash"), "variables": VARIABLES, "edges": [{"source": a, "target": b} for a, b in EDGES],
            "criteria": CRITERIA, "models": models, "temporal": tmp,
            "assumption": "The directed graph is a documented assumption about the measurement process, not learned from the data.",
            "note": "Each model is a causal hypothesis. Correlation (C1) never establishes causation; C5 is not reachable with archival data. An "
                    "intervention listed here is a re-analysis (Counterfactual Lab), not an intervention on the source."}


CAUSAL_WORDS = ("causes", "caused", "causing", "drives", "driven", "produces", "produced", "leads to", "due to", "because of", "results in")


def warnings(session: dict | None, models: list[dict]) -> list[dict]:
    """Your causal proposals (session 'causal') that use causal language. Each is labelled user-proposed; the warning says
    which criteria the matching model meets, so a proposal resting on correlation alone is flagged."""
    out = []
    by_cause = {}
    for m in models:
        if m["cause"]:
            by_cause.setdefault(m["cause"], []).append(m)
    for k, p in enumerate((session or {}).get("causal") or []):
        if not isinstance(p, dict):
            continue
        rel = str(p.get("rel") or "").lower()
        if not any(w in rel for w in CAUSAL_WORDS) and rel not in ("causal", "cause"):
            continue
        ms = by_cause.get(str(p.get("from") or ""), [])
        met = sorted({c for m in ms for c, v in m["criteria"].items() if v})
        out.append({"index": k, "proposal": f"{p.get('from')} — {p.get('rel')} — {p.get('to')}", "criteria_met": met,
                    "warning": "user-proposed causal claim; " + ("the matching model meets correlation only" if met == ["C1"] else
                               "no model in the lab has this cause" if not ms else f"the matching model meets {', '.join(met) or 'no criterion'}")
                    + "; experimental support (C5) is not possible with archival data"})
    return out
