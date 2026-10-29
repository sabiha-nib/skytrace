"""Read-only views over a finished investigation record (and its bundle).

Shared by the copilot tools, the API and the evidence graph so that every
consumer reads the same logged facts. Nothing here computes a new measurement
except `pair_comparison`, which applies the already-defined deterministic rules
(WLMATCH-2, PAIRDIFF-1/2) to two logged measurements.
"""

from __future__ import annotations

import hashlib
import math

from .science.wavelength import SourceSample, compare_pair


class InvestigationView:
    def __init__(self, record: dict, discovery: dict | None = None, manifest: dict | None = None,
                 inspection: dict | None = None):
        self.r = record
        self.discovery = discovery or {"observations": []}
        self.manifest = manifest or {"files": []}
        self.inspection = inspection or {}
        self.events = record["events"]
        self.measurements: dict[str, dict] = {}
        self.measure_events: dict[str, dict] = {}
        for i, e in enumerate(self.events):
            if e["step"] == "measure" and "key" in e["data"]:
                self.measure_events[e["data"]["key"]] = {**e, "index": i}
                if "centroid" in e["data"]:
                    self.measurements[e["data"]["key"]] = e["data"]

    # ------------------------------------------------------------- basics
    def first(self, step: str) -> dict | None:
        return next((e for e in self.events if e["step"] == step), None)

    def outcomes(self) -> list[dict]:
        e = self.first("assess")
        return e["data"].get("outcomes", []) if e else []

    def data_origins(self) -> list[str]:
        return sorted({p["origin"] for e in self.events for p in e["provenance"]})

    def is_synthetic(self) -> bool:
        return self.r["parameters"].get("bundle_kind") == "synthetic" or "synthetic" in self.data_origins()

    def observations(self) -> list[dict]:
        return sorted(self.discovery.get("observations", []), key=lambda o: (o.get("t_mid_mjd") or 0, o.get("detector") or 0))

    def observation(self, key: str) -> dict | None:
        return next((o for o in self.discovery.get("observations", []) if o["key"] == key), None)

    def file_entry(self, rel: str | None) -> dict | None:
        return next((f for f in self.manifest.get("files", []) if f["path"] == rel), None) if rel else None

    def accepted_pairs(self) -> list[dict]:
        e = self.first("pairs")
        return e["data"].get("accepted", []) if e else []

    def flux_pairs(self) -> list[dict]:
        e = self.first("variability")
        return e["data"].get("pairs", []) if e else []

    def astrometry(self) -> dict | None:
        e = self.first("astrometry")
        return e["data"] if e and e["status"] == "ok" else None

    # ------------------------------------------------------------- derived (rules only)
    def pair_comparison(self, a: str, b: str) -> dict:
        ma, mb = self.measurements.get(a), self.measurements.get(b)
        missing = [k for k, m in ((a, ma), (b, mb)) if m is None]
        if missing:
            return {"error": f"no logged measurement for {', '.join(missing)}"}
        def sample(k, m):
            q = m.get("quality_code") or ("ok" if m.get("quality") == "ok" else str(m.get("quality")))
            return SourceSample(k, m["detector"], m["mjd"], m.get("wavelength_um") or float("nan"),
                                m.get("bandwidth_um") or float("nan"), q, m.get("release", ""))
        prm = self.r["parameters"]
        tol = prm.get("wavelength_tolerance_channels", 0.5)
        d = compare_pair(sample(a, ma), sample(b, mb), tol, margin_um=prm.get("wavelength_margin_um", 0.0),
                         same_release=prm.get("photometry_same_release", False))
        first, second = (ma, mb) if ma["mjd"] <= mb["mjd"] else (mb, ma)
        out = {"a": d.a, "b": d.b, "compatible_for_photometry": d.accepted, "reason": d.reason, "reason_code": d.code,
               "rule": d.rule if "wavelength_margin_um" in prm else "WLMATCH-1",
               "delta_t_days": d.delta_t_days, "delta_lambda_um": d.delta_lambda_um,
               "wavelength_a_um": first.get("wavelength_um"), "wavelength_b_um": second.get("wavelength_um"),
               "tolerance_um": tol * min(first.get("bandwidth_um") or float("nan"), second.get("bandwidth_um") or float("nan")),
               "t_a_iso": first.get("t_mid_iso"), "t_b_iso": second.get("t_mid_iso")}
        pa, pb = first.get("photometry") or {}, second.get("photometry") or {}
        if d.accepted and pa.get("status") == pb.get("status") == "ok":
            s = math.hypot(pa["flux_err_ujy"], pb["flux_err_ujy"])
            out["flux"] = {"flux_a_ujy": pa["flux_ujy"], "flux_b_ujy": pb["flux_ujy"], "delta_ujy": pb["flux_ujy"] - pa["flux_ujy"],
                           "sigma_ujy": s, "z": (pb["flux_ujy"] - pa["flux_ujy"]) / s if s > 0 else None,
                           "method": "PAIRDIFF-1", "note": "z is a significance under the stated errors, not a probability"}
            logged = next((p for p in self.flux_pairs() if (p["a"], p["b"]) == (d.a, d.b)), None)
            if logged and logged.get("differential"):
                out["flux"]["reference_calibrated"] = logged["differential"]
        else:
            out["flux"] = None
            out["flux_note"] = ("flux comparison not valid: " + d.reason) if not d.accepted else "photometry not usable in one or both"
        if first.get("target_xi_eta_mas") and second.get("target_xi_eta_mas"):
            dx = second["target_xi_eta_mas"][0] - first["target_xi_eta_mas"][0]
            dy = second["target_xi_eta_mas"][1] - first["target_xi_eta_mas"][1]
            sx = math.sqrt(first["target_cov_mas2"][0] + second["target_cov_mas2"][0])
            sy = math.sqrt(first["target_cov_mas2"][1] + second["target_cov_mas2"][1])
            out["position"] = {"d_xi_mas": dx, "d_eta_mas": dy, "sigma_xi_mas": sx, "sigma_eta_mas": sy,
                               "separation_mas": math.hypot(dx, dy),
                               "note": "positions from per-exposure Gaia-referenced plate solutions, before parallax removal; "
                                       "chromatic effects not modelled"
                                       + ("" if d.accepted else "; the two exposures are at different wavelengths")}
        else:
            out["position"] = None
        return out


# ---------------------------------------------------------------------- evidence graph
def _lid(text: str) -> str:
    return "limit:" + hashlib.sha1(text.encode()).hexdigest()[:10]


def evidence_graph(v: InvestigationView, target_id: str) -> dict:
    """Nodes and edges derived only from recorded events, bundle manifest and discovery records."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid, kind, label, **data):
        nodes.setdefault(nid, {"id": nid, "kind": kind, "label": label, **data})
        return nid

    def edge(a, b, rel, **data):
        if a in nodes and b in nodes:
            edges.append({"source": a, "target": b, "rel": rel, **data})

    t_ev = v.first("target")
    tnode = node(f"target:{target_id}", "target", v.r["target"],
                 synthetic=v.is_synthetic(), event=v.events.index(t_ev) if t_ev else None)
    if t_ev:
        src = t_ev["data"]["astrometry"].get("source") or "catalogue"
        cnode = node(f"ref:{src}", "reference", src, event=v.events.index(t_ev))
        edge(tnode, cnode, "astrometry from")
    r_ev = v.first("references")
    if r_ev and r_ev["data"].get("n"):
        rnode = node("ref:references", "reference", f"{r_ev['data']['n']} reference stars ({r_ev['data'].get('catalogue')})",
                     event=v.events.index(r_ev))
        edge(tnode, rnode, "astrometric frame")
    for o in v.observations():
        if not o.get("included"):
            continue
        fe = v.file_entry(o.get("file"))
        onode = node(f"obs:{o['key']}", "observation", o["key"], release=o["release"], detector=o["detector"],
                     t_mid_iso=o.get("t_mid_iso"), obs_id=o.get("obs_id"), file=o.get("file"),
                     sha256=fe["sha256"] if fe else None, source_url=o.get("access_url") or None)
        edge(tnode, onode, "observed in")
        if fe:
            prov = fe.get("provenance") or {}
            sname = prov.get("source", "?") + (f" {prov.get('release')}" if prov.get("release") else "")
            snode = node(f"source:{sname}", "source", sname, origin=prov.get("origin"), dataset_id=prov.get("dataset_id") or None)
            edge(onode, snode, "retrieved from", sha256=fe["sha256"])
    for key, me in v.measure_events.items():
        m = me["data"]
        if f"obs:{key}" not in nodes:
            continue
        mnode = node(f"meas:{key}", "measurement", f"measurement {key}", status=me["status"], quality=m.get("quality"),
                     event=me["index"])
        edge(f"obs:{key}", mnode, "measured from")
        if m.get("centroid"):
            edge(mnode, node("method:" + m["centroid"]["method"], "method", m["centroid"]["method"]), "uses")
        if m.get("photometry"):
            edge(mnode, node("method:" + m["photometry"]["method"], "method", m["photometry"]["method"]), "uses")
        if m.get("plate") and m["plate"].get("n_refs"):
            edge(mnode, node("method:" + m["plate"]["method"], "method", m["plate"]["method"]), "uses")
            edge(mnode, "ref:references", "plate referenced to")
    pe = v.first("pairs")
    flux_by = {(p["a"], p["b"]): p for p in v.flux_pairs()}
    if pe:
        rule = pe["data"].get("rule", "WLMATCH-1")
        wl = node("method:" + rule, "method", rule)
        for d in v.accepted_pairs():
            fp = flux_by.get((d["a"], d["b"]))
            zc = (fp or {}).get("differential", {})
            pnode = node(f"pair:{d['a']}|{d['b']}", "comparison", f"{d['a']} ↔ {d['b']}", z=fp["z"] if fp else None,
                         z_calibrated=zc.get("z_cal_scaled", zc.get("z_cal")) if zc.get("calibrated") else None,
                         n_refs=zc.get("n_refs"), event=v.events.index(pe))
            edge(pnode, f"meas:{d['a']}", "compares")
            edge(pnode, f"meas:{d['b']}", "compares")
            edge(pnode, wl, "accepted by")
    ast = v.astrometry()
    from .science.assess import T, pair_significance
    methods = v.r["parameters"].get("methods") or {}
    var_ev = v.first("variability")
    cal_scale = ((var_ev or {}).get("data", {}).get("calibration_check") or {}).get("error_scale")
    per_question = {"motion": ("ephemeris", "reference_selection", "motion_primary", "motion_crosscheck"),
                    "variability": ("wavelength_match", "variability", "calibration_check")}
    for o in v.outcomes():
        cnode = node(f"claim:{o['question']}", "claim", f"{o['question']}: {o['category']}", statement=o["statement"],
                     category=o["category"], event=v.events.index(v.first("assess")))
        edge(cnode, node("method:" + o["rules"], "method", o["rules"]), "decided by")
        for role in per_question.get(o["question"], ()):   # method versions recorded in the record's parameters
            ids = methods.get(role)
            for mid in ([ids] if isinstance(ids, str) else ids or []):
                edge(cnode, node("method:" + mid, "method", mid, role=role), "computed with")
        if o["question"] == "motion" and ast:
            for s in ast["series"]:
                if s.get("used_in_fit", True):
                    edge(cnode, f"meas:{s['key']}", "supported by")
            edge(cnode, f"ref:{ast['catalogue']['source']}" if f"ref:{ast['catalogue']['source']}" in nodes else tnode, "compared with")
        if o["question"] == "variability":
            for d in v.accepted_pairs():   # the same significance the assessment used (calibrated when possible)
                fp = flux_by.get((d["a"], d["b"]))
                z, calibrated = pair_significance(fp, cal_scale) if fp else (None, False)
                if z is not None and abs(z) >= T["variability_z"]:
                    edge(cnode, f"pair:{d['a']}|{d['b']}", "supported by" if calibrated else "raw difference (uncalibrated)")
        if o["question"] == "data_quality":
            for key, me in v.measure_events.items():
                if me["status"] in ("rejected", "failed"):
                    edge(cnode, f"meas:{key}", "counts rejection")
        for lim in o.get("limitations", []):
            edge(cnode, node(_lid(lim), "limitation", lim), "limited by")
    return {"nodes": list(nodes.values()), "edges": edges,
            "counts": {k: sum(1 for n in nodes.values() if n["kind"] == k) for k in
                       ("target", "reference", "source", "observation", "measurement", "method", "comparison", "claim", "limitation")}}
