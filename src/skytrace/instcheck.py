"""INSTCHECK-1: the instrumental reality check — could the apparent signal come from the measurement process?

For each question, the instrumental explanations Skytrace knows (HYPO-1) and three direct checks on recorded values. Each
check gives 'ruled out by rule', 'not ruled out', 'not testable here' or 'not applicable'. The check never concludes that a
signal is astrophysical: at best every instrumental explanation it knows is ruled out by its rule, and the list is finite.

  I1 detector dependence    brightness: the detectors whose wavelength-matched, reference-calibrated pairs reach |z| ≥ the
                            threshold. A change seen on one detector only is 'not ruled out' as detector-specific; seen on
                            two or more detectors, a single-detector artefact is ruled out (other shared causes are not)
  I2 calibration            HYPO-1 V-CALIB (reference-star ratios) and CALCHECK-1's error scale on constant reference stars
  I3 error model            HYPO-1 V-ERRMODEL (CALCHECK-1)
  I4 wavelength sampling    HYPO-1 V-WAVELENGTH
  I5 blending               HYPO-1 V-BLEND
  I6 registration           HYPO-1 M-REGISTRATION
  I7 reference frame        HYPO-1 M-REFS
  I8 chromatic offsets      HYPO-1 M-CHROMATIC (per-detector motion fits are not implemented: not testable here)
  I9 excluded exposures     the share of exposures the pipeline refused (flags, edges, blends); a large share makes the
                            remaining sample a selection
"""

from __future__ import annotations

METHOD = "INSTCHECK-1"
STATES = ["ruled out by rule", "not ruled out", "not testable here", "not applicable"]
HYP = {"I2": "V-CALIB", "I3": "V-ERRMODEL", "I4": "V-WAVELENGTH", "I5": "V-BLEND", "I6": "M-REGISTRATION", "I7": "M-REFS", "I8": "M-CHROMATIC"}
NAMES = {"I1": "detector dependence", "I2": "calibration", "I3": "error model", "I4": "wavelength sampling", "I5": "blending", "I6": "registration",
         "I7": "reference frame", "I8": "chromatic offsets", "I9": "excluded exposures"}
QUESTION = {"I1": "variability", "I2": "variability", "I3": "variability", "I4": "variability", "I5": "variability", "I6": "motion", "I7": "motion",
            "I8": "motion", "I9": None}
EXCLUDED_SHARE = 0.25


def _det(key: str):
    s = str(key or "")
    return int(s[-1]) if len(s) > 2 and s[-2] == "D" and s[-1].isdigit() else None


def check(record: dict, hypotheses: dict, threshold: float = 5.0) -> dict:
    hyp = {h["id"]: h for q in (hypotheses or {}).get("questions", []) for h in q["hypotheses"]}
    outs = {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}
    var = next((e for e in record["events"] if e["step"] == "variability"), {}).get("data") or {}
    rows = []

    def row(cid, state, detail, cites):
        rows.append({"id": cid, "name": NAMES[cid], "question": QUESTION[cid], "state": state, "detail": detail, "cites": cites})
    sig_dets = {}
    for p in var.get("pairs", []):
        d = p.get("differential") or {}
        z = d.get("z_cal_scaled", d.get("z_cal"))
        if d.get("calibrated") and isinstance(z, (int, float)) and abs(z) >= threshold:
            det = _det(p.get("a"))
            sig_dets.setdefault(det, 0)
            sig_dets[det] += 1
    if not var.get("pairs"):
        row("I1", "not applicable", "no wavelength-matched pair was compared", [])
    elif not sig_dets:
        row("I1", "not applicable", f"no calibrated pair reaches |z| ≥ {threshold:g}: there is no signal to localise", ["$.events[variability].data.pairs"])
    elif len(sig_dets) == 1:
        d = next(iter(sig_dets))
        row("I1", "not ruled out", f"significant calibrated pairs on D{d} only ({sig_dets[d]}): a detector-specific effect is not ruled out",
            ["$.events[variability].data.pairs"])
    else:
        row("I1", "ruled out by rule", "significant calibrated pairs on " + ", ".join(f"D{d} ({n})" for d, n in sorted(sig_dets.items(), key=lambda x: str(x[0])))
            + ": a single-detector artefact is ruled out; causes shared by detectors are not", ["$.events[variability].data.pairs"])
    for cid, hid in HYP.items():
        h = hyp.get(hid)
        if not h:
            row(cid, "not applicable", f"{hid} is not evaluated for this run", [])
            continue
        st = h.get("overall")
        state = ("ruled out by rule" if st == "contradicted" else "not testable here" if st == "untested" and all(
            t["status"] in ("not_tested", "untested", "evidence_unavailable") for t in h.get("tests", [])) and hid == "M-CHROMATIC" else
                 "not ruled out")
        tests = "; ".join(f"{t['id']} {t['status']}" for t in h.get("tests", []))
        extra = ""
        if cid == "I2":
            cc = var.get("calibration_check") or {}
            if cc.get("error_scale"):
                extra = f"; CALCHECK-1 error scale {cc['error_scale']:.3g} on {cc.get('n_ref_z')} reference comparisons ({cc.get('status')})"
        row(cid, state, f"HYPO-1 {hid}: {st} ({tests}){extra}", [f"HYPO-1:{hid}"])
    dq = (outs.get("data_quality") or {}).get("evidence") or {}
    frac = dq.get("rejected_fraction")
    if isinstance(frac, (int, float)):
        row("I9", "not ruled out" if frac >= EXCLUDED_SHARE else "ruled out by rule",
            f"{frac:.0%} of exposures refused ({', '.join(f'{k} {v}' for k, v in sorted((dq.get('reason_codes') or {}).items()))})"
            + (f": at least {EXCLUDED_SHARE:.0%}, so the measured sample is a selection" if frac >= EXCLUDED_SHARE else f": under {EXCLUDED_SHARE:.0%}"),
            ["claim:data_quality"])
    else:
        row("I9", "not testable here", "the data-quality outcome records no rejected fraction", [])
    by_q = {}
    for q in ("variability", "motion"):
        xs = [r for r in rows if r["question"] in (q, None)]
        by_q[q] = {"category": (outs.get(q) or {}).get("category"), "counts": {s: sum(r["state"] == s for r in xs) for s in STATES},
                   "open": [r["name"] for r in xs if r["state"] in ("not ruled out", "not testable here")]}
    return {"method": METHOD, "record": record.get("content_hash"), "states": STATES, "checks": rows, "by_question": by_q, "threshold": threshold,
            "note": "The check lists the instrumental explanations Skytrace knows. Ruling all of them out does not make a signal astrophysical; "
                    "an unlisted effect can still produce it."}
