"""BUDGET-1: the scientific uncertainty budget — which sources contribute to a result, which are measured, which are estimated
and which remain unquantified.

Read from UNC-1 (the recorded components) and UFLOW-1 (what is not propagated). Classes:
  measured       a σ computed from the data by a recorded method (per-exposure flux errors, the motion fit's statistical error)
  estimated      a correction or scale derived from other measurements (CALCHECK-1's error scale from reference stars, the
                 reference-ratio scatter, the √χ²ν inflation, the parallax systematic bound — a bound, not a σ)
  unquantified   an effect no method here puts a number on (UNC-1 'unquantified', UFLOW-1 'not propagated')

Shares of variance are given only where the components add in quadrature in the method itself: the PAIRDIFF-2 denominator
of the most significant matched pair (UNC-1 recomputes it from logged inputs). Nowhere else is a share computed; the motion
fit's σ is one measured term, and the bound and unquantified effects have no share.
"""

from __future__ import annotations

from . import uncertainty

METHOD = "BUDGET-1"
CLASSES = ["measured", "estimated", "unquantified"]
TERM_CLASS = {"exposure_a": "measured", "exposure_b": "measured", "exposure_b_scaled": "measured", "calibration_ratio": "estimated"}


def budget(record: dict, uflow: dict) -> dict:
    u = uncertainty.decompose(record)
    out = {}
    v = u["variability"]
    if v.get("available") and v["pairs"]:
        top = v["pairs"][0]
        rows = [{"source": k, "class": TERM_CLASS.get(k, "measured"), "value": val, "unit": "µJy", "variance_share": (top.get("variance_share") or {}).get(k)}
                for k, val in (top.get("terms_ujy") or {}).items()]
        sc = (v.get("calibration_check") or {}).get("error_scale")
        if sc:
            rows.append({"source": "CALCHECK-1 error scale (divides z)", "class": "estimated", "value": sc, "unit": "×", "variance_share": None})
        out["variability"] = {"available": True, "pair": f"{top['a']} ↔ {top['b']}", "z_used": top.get("z_used"), "rows": rows,
                              "share_rule": "variance shares of the PAIRDIFF-2 denominator, which adds its terms in quadrature"}
    else:
        out["variability"] = {"available": False, "why": v.get("reason")}
    m = u["motion"]
    if m.get("available"):
        rows = []
        for r in m["rows"]:
            if r["kind"] == "sigma" and r["component"].startswith("Statistical"):
                rows.append({"source": r["component"], "class": "measured", "value": r["values"], "unit": r["unit"], "variance_share": None})
                infl = (r.get("detail") or {}).get("inflation_factor")
                if infl and infl > 1:
                    rows.append({"source": "√χ²ν inflation (included above)", "class": "estimated", "value": infl, "unit": "×", "variance_share": None})
            elif r["kind"] == "bound":
                rows.append({"source": r["component"], "class": "estimated", "value": r["values"], "unit": r["unit"], "variance_share": None,
                             "note": "an upper bound on a systematic, not a σ"})
        out["motion"] = {"available": True, "rows": rows, "share_rule": "no shares: the fit's σ is a single measured term"}
    else:
        out["motion"] = {"available": False, "why": m.get("reason")}
    unq = [{"source": x["name"], "class": "unquantified", "why": x["why"]} for x in u["unquantified"]]
    unq += [{"source": f"{x['step']}: {x['what']}", "class": "unquantified", "why": f"recorded as {x['recorded_as']}"} for x in uflow.get("not_propagated", [])]
    counts = {c: 0 for c in CLASSES}
    for q in ("variability", "motion"):
        for r in out[q].get("rows", []):
            counts[r["class"]] += 1
    counts["unquantified"] = len(unq)
    return {"method": METHOD, "classes": CLASSES, "record": record.get("content_hash"), "questions": out, "unquantified": unq, "counts": counts,
            "note": "Measured and estimated terms come from recorded values; unquantified effects have no number, and no total including them is computed."}
