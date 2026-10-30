"""Evidence Ledger (LEDGER-1): what supports each claim, what conflicts, where it came from, and what is missing.

Built from the investigation record, its evidence graph and the HYPO-1 results. Support is *counted by kind* (traced
observations, measurements, comparisons, distinct detectors and visits), never weighed into a verdict; a claim that
rests on a single comparison or measurement is flagged as such. Contradictions are found by fixed rules over logged
values. Provenance is traced from each claim to the files (and their SHA-256) behind it. Completeness lists missing
relationships rather than a percentage.

User-authored material (hypotheses, annotations, notebook) lives in the research session; the interface joins it to
the ledger by identifier and labels it as user-authored. It never changes what the ledger computes.
"""

from __future__ import annotations

from collections import defaultdict

from . import hypotheses as hmod
from .science.assess import T, pair_significance

METHOD = "LEDGER-1"
ABSENCE = {"no_motion_at_sensitivity", "no_significant_change", "spectral_difference_only", "insufficient_evidence"}
PARAM_ROLES = {
    "variability": ["aperture_radius_px", "wavelength_tolerance_channels", "wavelength_margin_um", "photometry_same_release"],
    "motion": ["fit_half_size_px", "epoch_clip_sigma", "epoch_gap_days", "apply_parallax", "reference_quality_cut"],
    "data_quality": ["aperture_radius_px", "fit_half_size_px"],
}


def _first(record, step):
    return next((e for e in record.get("events", []) if e.get("step") == step), None)


def _trace(graph: dict, start: str) -> set:
    """Nodes reachable from a claim along the support direction (claim → comparison → measurement → observation → source)."""
    steps = {"claim": {"comparison", "measurement", "reference", "target"}, "comparison": {"measurement"},
             "measurement": {"observation"}, "observation": {"source"}}
    kind = {n["id"]: n["kind"] for n in graph["nodes"]}
    out_adj = defaultdict(list)
    for e in graph["edges"]:
        out_adj[e["source"]].append(e["target"])
        out_adj[e["target"]].append(e["source"])
    seen, q = {start}, [start]
    while q:
        n = q.pop()
        for m in out_adj[n]:
            if m not in seen and kind.get(m) in steps.get(kind.get(n), set()):
                seen.add(m)
                q.append(m)
    return seen


def claims(record: dict, graph: dict, hyp: dict) -> list[dict]:
    nodes = {n["id"]: n for n in graph["nodes"]}
    params = record.get("parameters", {})
    methods = params.get("methods") or {}
    meas_ev = {e["data"].get("obs_id"): e for e in record.get("events", []) if e.get("step") == "measure"}
    out = []
    for o in ((_first(record, "assess") or {}).get("data") or {}).get("outcomes", []):
        cid = f"claim:{o['question']}"
        if cid not in nodes:
            continue
        reach = _trace(graph, cid)
        direct = [e for e in graph["edges"] if e["source"] == cid]
        comps = sorted(n for n in reach if n.startswith("pair:"))
        measures = sorted(n for n in reach if n.startswith("meas:"))
        obs = sorted(n for n in reach if n.startswith("obs:"))
        dets = sorted({nodes[n].get("detector") for n in obs if nodes[n].get("detector") is not None})
        dates = sorted({(nodes[n].get("t_mid_iso") or "")[:10] for n in obs if nodes[n].get("t_mid_iso")})
        files = []
        for n in obs:
            nd = nodes[n]
            files.append({"observation": nd["label"], "file": nd.get("file"), "sha256": nd.get("sha256"), "obs_id": nd.get("obs_id")})
        support_edges = [e for e in direct if e["rel"] in ("supported by", "raw difference (uncalibrated)", "counts rejection")]
        n_support = len(support_edges)
        flags = []
        if n_support == 0 and o["category"] in ABSENCE:
            flags.append("states an absence (or a lack of evidence) at the stated sensitivity: no positive evidence item is expected")
        elif n_support == 0:
            flags.append("no supporting comparison or measurement is linked")
        elif n_support == 1:
            flags.append("rests on a single evidence item")
        if any(e["rel"] == "raw difference (uncalibrated)" for e in support_edges):
            flags.append("some support is an uncalibrated difference")
        used_methods = sorted({e["target"].split(":", 1)[1] for e in direct if e["target"].startswith("method:")})
        hq = next((q for q in hyp["questions"] if q["question"] == o["question"]), None)
        out.append({"id": cid, "question": o["question"], "category": o["category"], "statement": o["statement"],
                    "support": {"direct": n_support, "comparisons": len(comps), "measurements": len(measures),
                                "observations": len(obs), "detectors": dets, "dates": dates,
                                "by_relation": dict(sorted(defaultdict(int, {r: sum(1 for e in direct if e["rel"] == r) for r in {e["rel"] for e in direct}}).items()))},
                    "flags": flags,
                    "provenance": {"files": files, "missing_sha256": [f["observation"] for f in files if not f["sha256"]]},
                    "methods": used_methods,
                    "method_roles": {k: v for k, v in methods.items()},
                    "parameters": {k: params.get(k) for k in PARAM_ROLES.get(o["question"], [])},
                    "criteria": o.get("criteria"), "limitations": o.get("limitations", []),
                    "explanations": [{"id": h["id"], "statement": h["statement"], "overall": h["overall"]} for h in (hq or {}).get("hypotheses", [])],
                    "support_note": "counts describe what is linked; they are not a measure of how well the claim is established"})
        _ = meas_ev
    return out


def contradictions(record: dict, hyp: dict) -> list[dict]:
    out = []
    var = (_first(record, "variability") or {}).get("data") or {}
    scale = (var.get("calibration_check") or {}).get("error_scale")
    thr = T["variability_z"]
    for p in var.get("pairs", []):
        d = p.get("differential") or {}
        if not d.get("calibrated") or p.get("z") is None:
            continue
        zc, _ = pair_significance(p, scale)
        raw = abs(p["z"]) >= thr
        cal = zc is not None and abs(zc) >= thr
        if raw != cal:
            out.append({"rule": "C1", "kind": "raw vs calibrated", "items": [p["a"], p["b"]],
                        "detail": f"raw |z| = {abs(p['z']):.1f} {'≥' if raw else '<'} {thr:g} but reference-calibrated, error-scaled |z| = {abs(zc):.1f} {'≥' if cal else '<'} {thr:g}",
                        "meaning": "the difference depends on whether exposure-level calibration is removed"})
    a = (_first(record, "astrometry") or {}).get("data") or {}
    ef, pf = a.get("exposure_fit"), a.get("epoch_fit")
    if ef and pf:
        for ax, s in (("xi", "sig_xi"), ("eta", "sig_eta")):
            d = abs(ef[f"pm_{ax}_mas_yr"] - pf[f"pm_{ax}_mas_yr"])
            sig = (ef[s] ** 2 + pf[s] ** 2) ** 0.5
            if sig > 0 and d > 3 * sig:
                out.append({"rule": "C2", "kind": "primary vs cross-check motion fit", "items": ["LINFIT-EPOCH-1", "LINFIT-LOO-1"],
                            "detail": f"{ax}: the two fits differ by {d:.0f} mas/yr = {d / sig:.1f}σ (combined, ignoring their correlation)",
                            "meaning": "the motion estimate depends on how exposures are combined"})
    comp = a.get("comparison") or {}
    outcomes = {o["question"]: o["category"] for o in ((_first(record, "assess") or {}).get("data") or {}).get("outcomes", [])}
    if outcomes.get("motion") == "motion_detected" and comp and comp.get("consistent_within_3sigma") is False:
        out.append({"rule": "C3", "kind": "motion vs catalogue", "items": ["claim:motion", "catalogue"],
                    "detail": "motion is detected but disagrees with the catalogue proper motion by more than 3σ",
                    "meaning": "either the measurement or the catalogue value is in question"})
    for q in hyp["questions"]:
        for h in q["hypotheses"]:
            st = {t["status"] for t in h["tests"]}
            if "consistent" in st and "contradicted" in st:
                out.append({"rule": "C4", "kind": "tests of one explanation disagree", "items": [h["id"]] + [t["id"] for t in h["tests"]],
                            "detail": f"{h['id']}: " + "; ".join(f"{t['id']} {t['status']}" for t in h["tests"]),
                            "meaning": "the explanation is contradicted by one test and supported by another; the published rule makes it contradicted"})
    return out


def completeness(record: dict, graph: dict, discovery: dict) -> dict:
    nodes = {n["id"]: n for n in graph["nodes"]}
    linked = set()
    for e in graph["edges"]:
        linked.add(e["source"])
        linked.add(e["target"])
    meas_keys = {e["data"].get("obs_id") for e in record.get("events", []) if e.get("step") == "measure"}
    included = [o["key"] for o in (discovery or {}).get("observations", []) if o.get("included")]
    gaps = []
    for k in included:
        if k not in meas_keys:
            gaps.append({"kind": "observation without measurement", "id": k})
    for nid, n in nodes.items():
        if nid not in linked:
            gaps.append({"kind": "node without relationships", "id": nid})
        if n["kind"] == "observation" and not n.get("sha256"):
            gaps.append({"kind": "observation without a file checksum", "id": nid})
        if n["kind"] == "observation" and not n.get("source_url"):
            gaps.append({"kind": "observation without an archive URL", "id": nid, "expected": record.get("parameters", {}).get("bundle_kind") == "synthetic"})
    absent = {f"claim:{o['question']}" for o in ((_first(record, "assess") or {}).get("data") or {}).get("outcomes", []) if o["category"] in ABSENCE}
    claims_without = [n for n in nodes if n.startswith("claim:") and n not in absent and not any(e["source"] == n and e["rel"] in ("supported by", "raw difference (uncalibrated)", "counts rejection") for e in graph["edges"])]
    for c in claims_without:
        gaps.append({"kind": "claim without linked support", "id": c})
    by = defaultdict(int)
    for g in gaps:
        by[g["kind"]] += 1
    return {"gaps": gaps[:500], "counts": dict(sorted(by.items())), "n_nodes": len(nodes), "n_edges": len(graph["edges"]),
            "note": "missing relationships are listed, not scored; synthetic observations have no archive URL by construction"}


def build(record: dict, graph: dict, discovery: dict) -> dict:
    hyp = hmod.evaluate(record)
    return {"method": METHOD, "content_hash": record.get("content_hash"),
            "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic",
            "claims": claims(record, graph, hyp), "contradictions": contradictions(record, hyp),
            "completeness": completeness(record, graph, discovery),
            "rules": {"C1": "a calibrated pair whose raw and calibrated significance fall on opposite sides of the detection threshold",
                      "C2": "the primary and cross-check motion fits differ by more than 3σ on an axis",
                      "C3": "motion detected but inconsistent with the catalogue at 3σ",
                      "C4": "one explanation has both a consistent and a contradicted test"}}
