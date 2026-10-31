"""Scientific investigation debugger (SCIDEBUG-1).

Breakpoints are the execution stages the record actually contains (STAGES lists the mapping from stage to recorded steps);
a stage the record does not contain is not shown. For a selected result the debugger shows the computation that
produced it — method, formula, parameters, recorded inputs and output — and, where the output is a deterministic function
of recorded values, recomputes it and compares. Values the pipeline did not record (e.g. the pixel stamp behind a
centroid) are never reconstructed; recomputing those needs a replay (REPROX-1).

Differential debugging compares two records stage by stage in pipeline order and reports the earliest stage whose
recorded values differ, together with the input, version, parameter and metadata differences that could explain it.
`diff` is mirrored in web/js/epistemiccore.js (parity-tested) so the static preview can debug its recorded runs.
"""

from __future__ import annotations

import math

from . import canon, counterfactual as cf

METHOD = "SCIDEBUG-1"
STAGES = [("ingestion", "Data ingestion", ["discover", "select"]), ("validation", "File validation", ["inspect"]),
          ("registration", "Registration (reference catalogue and per-exposure plate solutions)", ["references", "measure.plate"]),
          ("measurement", "Measurement", ["measure"]), ("matching", "Wavelength matching", ["pairs"]),
          ("statistics", "Statistical calculation", ["variability", "spectral_context", "spectrum", "astrometry"]),
          ("assessment", "Assessment", ["assess"])]
READER_STAGES = [("hypotheses", "Hypothesis evaluation (HYPO-1, computed from the record on demand)"),
                 ("report", "Report generation (report.py, rendered from the record on demand)")]
REL_EQUIV = 1e-9


def _steps(record, names):
    out = []
    for i, e in enumerate(record.get("events", [])):
        for n in names:
            if n == "measure.plate" and e["step"] == "measure":
                out.append((i, {"step": "measure.plate", "key": (e.get("data") or {}).get("obs_id"), "data": (e.get("data") or {}).get("plate")}))
            elif e["step"] == n:
                out.append((i, e))
    return out


def breakpoints(record: dict) -> list:
    bps = []
    for sid, name, steps in STAGES:
        evs = _steps(record, steps)
        if not evs:
            continue
        status = {}
        for _, e in evs:
            status[e.get("status", "ok")] = status.get(e.get("status", "ok"), 0) + 1
        bps.append({"id": sid, "name": name, "steps": sorted({e["step"] for _, e in evs}), "n_events": len(evs), "events": [i for i, _ in evs][:400],
                    "status_counts": status})
    return bps


def _ev(record, step):
    return [(i, e) for i, e in enumerate(record["events"]) if e["step"] == step]


def inspect(record: dict, result_id: str) -> dict:
    """The computation behind one result, with recomputation where the record determines it."""
    P = record.get("parameters", {})
    meas = {(e.get("data") or {}).get("obs_id"): (i, e) for i, e in _ev(record, "measure")}
    if result_id.startswith("pair:"):
        a, b = result_id[5:].split("|", 1)
        vi, ve = (_ev(record, "variability") or [(None, {"data": {}})])[0]
        p = next((x for x in (ve.get("data") or {}).get("pairs", []) if x["a"] == a and x["b"] == b), None)
        if not p:
            return {"result": result_id, "error": "no such comparison in the record"}
        missing = [k for k in (a, b) if k not in meas]
        fa, fb = p.get("flux_a_ujy"), p.get("flux_b_ujy")
        ea, eb = p.get("err_a_ujy"), p.get("err_b_ujy")
        rec_in = {k: ((meas[k][1].get("data") or {}).get("photometry") or {}) for k in (a, b) if k in meas}
        inconsistent = [k for k, f, e in ((a, fa, ea), (b, fb, eb)) if k in rec_in and (rec_in[k].get("flux_ujy") != f or rec_in[k].get("flux_err_ujy") != e)]
        sigma = math.sqrt(ea ** 2 + eb ** 2)
        rows = [_cmp("Δ (µJy)", fb - fa, p["delta_ujy"]), _cmp("σ (µJy)", sigma, p["sigma_ujy"]), _cmp("z", (fb - fa) / sigma, p["z"]),
                _cmp("ratio", fb / fa if fa else None, p.get("ratio"))]
        dif = p.get("differential") or {}
        return {"result": result_id, "stage": "statistics", "event": vi, "method": p.get("method"), "formula": "Δ = f_b − f_a; σ = √(σ_a² + σ_b²); z = Δ/σ; ratio = f_b/f_a",
                "parameters": {k: P.get(k) for k in ("wavelength_tolerance_channels", "wavelength_margin_um", "photometry_same_release", "aperture_radius_px")},
                "inputs": [{"id": f"meas:{k}", "event": meas[k][0] if k in meas else None, "flux_ujy": (rec_in.get(k) or {}).get("flux_ujy"),
                            "flux_err_ujy": (rec_in.get(k) or {}).get("flux_err_ujy")} for k in (a, b)],
                "recomputed": rows, "intermediate": {"delta_lambda_um": p.get("delta_lambda_um"), "delta_t_days": p.get("delta_t_days")},
                "calibrated": {"method": dif.get("method"), "n_refs": dif.get("n_refs"), "z_cal": dif.get("z_cal"), "z_cal_scaled": dif.get("z_cal_scaled"),
                               "note": "PAIRDIFF-2 uses reference-star fluxes that are not stored per star in the record, so z_cal is shown, not recomputed"} if dif else None,
                "missing_dependencies": [f"meas:{k}" for k in missing], "inconsistent_values": [f"meas:{k}" for k in inconsistent],
                "verdict": _verdict(rows, missing, inconsistent)}
    if result_id.startswith("claim:"):
        q = result_id[6:]
        si, se = (_ev(record, "assess") or [(None, {"data": {}})])[0]
        o = next((x for x in (se.get("data") or {}).get("outcomes", []) if x["question"] == q), None)
        if not o:
            return {"result": result_id, "error": "no such outcome"}
        re = cf.reassess(record).get(q) or {}
        rows = [_cmp("category", re.get("category"), o.get("category")), _cmp("statement", re.get("statement"), o.get("statement"))]
        return {"result": result_id, "stage": "assessment", "event": si, "method": o.get("rules"), "formula": "; ".join(o.get("criteria") or []),
                "parameters": (se.get("data") or {}).get("thresholds"), "inputs": [{"id": "evidence", **{k: v for k, v in (o.get("evidence") or {}).items() if not isinstance(v, (dict, list))}}],
                "recomputed": rows, "intermediate": {"sensitivity": o.get("sensitivity")}, "missing_dependencies": [], "inconsistent_values": [],
                "verdict": _verdict(rows, [], [])}
    if result_id.startswith("epoch:") or result_id == "fit:motion":
        ai, ae = (_ev(record, "astrometry") or [(None, {"data": {}})])[0]
        ad = ae.get("data") or {}
        eps = ad.get("epochs", [])
        if result_id == "fit:motion":
            fit = ad.get("fit") or {}
            rec = _wls(eps, ad)
            rows = [_cmp("pm ξ (mas/yr)", rec[0] if rec else None, fit.get("pm_xi_mas_yr"), tol=1e-6), _cmp("pm η (mas/yr)", rec[1] if rec else None, fit.get("pm_eta_mas_yr"), tol=1e-6)]
            return {"result": result_id, "stage": "statistics", "event": ai, "method": fit.get("method"), "formula": "weighted least squares of visit-mean position vs time (weights 1/σ²), per axis",
                    "parameters": {k: P.get(k) for k in ("epoch_gap_days", "epoch_clip_sigma", "apply_parallax")},
                    "inputs": [{"id": f"epoch:{j}", "t_mjd": e.get("t_mjd"), "xi_mas": e.get("xi_mas"), "eta_mas": e.get("eta_mas"), "sig_xi_mas": e.get("sig_xi_mas"),
                                "sig_eta_mas": e.get("sig_eta_mas")} for j, e in enumerate(eps)],
                    "recomputed": rows, "intermediate": {"reduced_chi2": fit.get("reduced_chi2"), "rejected_visits": fit.get("rejected"), "t_ref": fit.get("t_ref")},
                    "missing_dependencies": [] if len(eps) >= 2 else ["≥ 2 visits"], "inconsistent_values": [],
                    "note": "recomputed from the recorded visit means; with rejected visits the recomputation uses only the kept visits",
                    "verdict": _verdict(rows, [] if len(eps) >= 2 else ["visits"], [])}
        j = int(result_id[6:])
        if j >= len(eps):
            return {"result": result_id, "error": "no such visit"}
        e = eps[j]
        series = ad.get("series", [])
        mem = [series[k] for k in e.get("members") or [] if isinstance(k, int) and k < len(series)]
        rows = []
        for ax in ("xi", "eta"):
            w = [1 / s[f"sig_{ax}_mas"] ** 2 for s in mem if s.get(f"sig_{ax}_mas")]
            mean = sum(wi * s[f"{ax}_mas"] for wi, s in zip(w, mem)) / sum(w) if w else None
            rows.append(_cmp(f"{ax} (mas)", mean, e.get(f"{ax}_mas"), tol=1e-6))
        return {"result": result_id, "stage": "statistics", "event": ai, "method": "LINFIT-EPOCH-1", "formula": "weighted mean of the visit's exposure positions (weights 1/σ²)",
                "parameters": {"epoch_gap_days": P.get("epoch_gap_days")}, "inputs": [{"id": f"pos:{s.get('key')}", "xi_mas": s.get("xi_mas"), "eta_mas": s.get("eta_mas")} for s in mem],
                "recomputed": rows, "intermediate": {"formal_sig_mas": e.get("formal_sig_mas"), "empirical_sig_mas": e.get("empirical_sig_mas")},
                "missing_dependencies": [] if mem else ["visit members"], "inconsistent_values": [], "verdict": _verdict(rows, [] if mem else ["members"], [])}
    if result_id.startswith("meas:"):
        k = result_id[5:]
        if k not in meas:
            return {"result": result_id, "error": "no such measurement"}
        i, e = meas[k]
        d = e.get("data") or {}
        return {"result": result_id, "stage": "measurement", "event": i, "method": f"{(d.get('centroid') or {}).get('method')} + {(d.get('photometry') or {}).get('method')}",
                "formula": "centroid: 2-D Gaussian fit; flux: Σ w (I − sky) Ω_pix", "parameters": {k2: P.get(k2) for k2 in ("aperture_radius_px", "fit_half_size_px")},
                "inputs": [{"id": f"file:{k}", "sha256": ((e.get("provenance") or [{}])[0]).get("content_sha256")}],
                "recorded": {"centroid": d.get("centroid"), "photometry": d.get("photometry"), "flags": d.get("flag_summary"), "quality": d.get("quality")},
                "recomputed": [], "missing_dependencies": [], "inconsistent_values": [],
                "note": "the pixel stamp is not stored in the record; re-measuring needs a replay of the pipeline on the file (Reproduce)",
                "verdict": "not recomputable from the record alone"}
    return {"result": result_id, "error": "unsupported result type (use pair:, claim:, epoch:, fit:motion or meas:)"}


def _wls(eps, ad):
    fit = ad.get("fit") or {}
    rej = set(fit.get("rejected") or [])
    pts = [(e, j) for j, e in enumerate(eps) if j not in rej]
    if len(pts) < 2:
        return None
    t0 = sum(e["t_mjd"] for e, _ in pts) / len(pts)
    out = []
    for ax in ("xi", "eta"):
        w = [1 / e[f"sig_{ax}_mas"] ** 2 for e, _ in pts]
        t = [(e["t_mjd"] - t0) / 365.25 for e, _ in pts]
        y = [e[f"{ax}_mas"] for e, _ in pts]
        sw, st, sy = sum(w), sum(wi * ti for wi, ti in zip(w, t)), sum(wi * yi for wi, yi in zip(w, y))
        stt, sty = sum(wi * ti * ti for wi, ti in zip(w, t)), sum(wi * ti * yi for wi, ti, yi in zip(w, t, y))
        out.append((sw * sty - st * sy) / (sw * stt - st * st))
    return out


def _cmp(name, recomputed, recorded, tol=REL_EQUIV):
    if recomputed is None or recorded is None:
        return {"quantity": name, "recomputed": recomputed, "recorded": recorded, "agreement": "not computable"}
    if isinstance(recomputed, str) or isinstance(recorded, str):
        return {"quantity": name, "recomputed": recomputed, "recorded": recorded, "agreement": "identical" if recomputed == recorded else "different"}
    if recomputed == recorded:
        ag = "identical"
    elif math.isclose(recomputed, recorded, rel_tol=tol, abs_tol=1e-12):
        ag = "equivalent within tolerance"
    else:
        ag = "different"
    return {"quantity": name, "recomputed": recomputed, "recorded": recorded, "agreement": ag, "tolerance": tol}


def _verdict(rows, missing, inconsistent):
    if missing:
        return "missing dependencies"
    if inconsistent:
        return "inconsistent recorded values"
    ags = {r["agreement"] for r in rows}
    if "different" in ags:
        return "recomputation differs"
    if ags <= {"identical"}:
        return "recomputes identically"
    if "not computable" in ags and len(ags) == 1:
        return "not recomputable from the record alone"
    return "recomputes within tolerance"


# --------------------------------------------------------------------------- differential debugging
def _leaves(a, b, path, out, stats):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                stats["structural"] += 1
                if len(out) < 20:
                    out.append({"path": f"{path}.{k}", "a": _brief(a.get(k)), "b": _brief(b.get(k)), "kind": "only in " + ("b" if k not in a else "a")})
            else:
                _leaves(a[k], b[k], f"{path}.{k}", out, stats)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            stats["structural"] += 1
            if len(out) < 20:
                out.append({"path": path, "a": f"{len(a)} items", "b": f"{len(b)} items", "kind": "length"})
        for j, (x, y) in enumerate(zip(a, b)):
            _leaves(x, y, f"{path}[{j}]", out, stats)
        return
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)  # noqa: E731
    if num(a) and num(b):
        if a == b or (a != a and b != b):
            return
        rel = abs(a - b) / max(abs(a), abs(b), 1e-300)
        stats["numeric"] += 1
        stats["max_rel"] = max(stats["max_rel"], rel)
        if len(out) < 20:
            out.append({"path": path, "a": a, "b": b, "kind": "numeric", "rel": rel})
        return
    if a != b:
        stats["other"] += 1
        if len(out) < 20:
            out.append({"path": path, "a": _brief(a), "b": _brief(b), "kind": "value"})


def _brief(v):
    """A short, language-independent description of a value (mirrored in epistemiccore.js)."""
    if isinstance(v, str):
        return v[:80]
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        try:
            return canon.dumps(v)
        except canon.CanonError:
            return str(v)
    if isinstance(v, list):
        return f"[{len(v)} items]"
    return f"{{{len(v)} keys}}"


def compare_values(a, b) -> dict:
    out, stats = [], {"numeric": 0, "structural": 0, "other": 0, "max_rel": 0.0}
    _leaves(a, b, "$", out, stats)
    if not (stats["numeric"] or stats["structural"] or stats["other"]):
        kind = "identical"
    elif not stats["structural"] and not stats["other"] and stats["max_rel"] <= REL_EQUIV:
        kind = "numerically equivalent"
    else:
        kind = "different"
    return {"kind": kind, "differences": out, **stats}


def diff(a: dict, b: dict) -> dict:
    """Stage-by-stage comparison of two investigation records (pipeline order); earliest divergence first."""
    pa, pb = a.get("parameters", {}), b.get("parameters", {})
    params = [{"key": k, "a": pa.get(k), "b": pb.get(k)} for k in sorted(set(pa) | set(pb)) if k not in ("methods",) and pa.get(k) != pb.get(k)]
    ma, mb = pa.get("methods") or {}, pb.get("methods") or {}
    methods = [{"role": k, "a": ma.get(k), "b": mb.get(k)} for k in sorted(set(ma) | set(mb)) if ma.get(k) != mb.get(k)]
    sa, sb = a.get("software") or {}, b.get("software") or {}
    software = [{"package": k, "a": sa.get(k), "b": sb.get(k)} for k in sorted(set(sa) | set(sb)) if sa.get(k) != sb.get(k)]
    inputs = {"bundle_a": pa.get("bundle"), "bundle_b": pb.get("bundle"), "manifest_a": pa.get("bundle_manifest_sha256"), "manifest_b": pb.get("bundle_manifest_sha256"),
              "same": pa.get("bundle_manifest_sha256") == pb.get("bundle_manifest_sha256")}
    stages, earliest = [], None
    for sid, name, steps in STAGES:
        ea = [e for _, e in _steps(a, steps)]
        eb = [e for _, e in _steps(b, steps)]
        if not ea and not eb:
            continue
        c = compare_values([{"step": e["step"], "status": e.get("status"), "data": e.get("data")} for e in ea],
                           [{"step": e["step"], "status": e.get("status"), "data": e.get("data")} for e in eb])
        stages.append({"id": sid, "name": name, "n_a": len(ea), "n_b": len(eb), **c})
        if earliest is None and c["kind"] != "identical":
            earliest = sid
    assumptions = [{"key": p["key"], "a": p["a"], "b": p["b"]} for p in params if p["key"] in ("aperture_radius_px", "fit_half_size_px", "wavelength_tolerance_channels",
                                                                                                 "wavelength_margin_um", "epoch_clip_sigma", "epoch_gap_days", "apply_parallax",
                                                                                                 "reference_quality_cut", "photometry_same_release", "detectors")]
    explanation = []
    if not inputs["same"]:
        explanation.append("the inputs differ (different bundle manifest)")
    if params:
        explanation.append(f"{len(params)} parameter(s) differ: " + ", ".join(p["key"] for p in params[:6]))
    if methods:
        explanation.append(f"{len(methods)} method version(s) differ")
    if software:
        explanation.append("software versions differ: " + ", ".join(f"{s['package']} {s['a']} → {s['b']}" for s in software))
    if earliest and not explanation:
        explanation.append("inputs, parameters, methods and software agree, so the difference arises from numerical behaviour or an unrecorded dependency")
    return {"method": METHOD, "a": a.get("content_hash"), "b": b.get("content_hash"), "identical_hash": a.get("content_hash") == b.get("content_hash"),
            "inputs": inputs, "parameters": params, "assumptions": assumptions, "methods": methods, "software": software,
            "metadata": [{"key": k, "a": a.get(k), "b": b.get(k)} for k in ("schema", "target") if a.get(k) != b.get(k)],
            "stages": stages, "earliest_divergence": earliest, "explanation": explanation}
