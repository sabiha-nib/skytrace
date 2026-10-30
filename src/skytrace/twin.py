"""Astro-Twins (TWIN-1): explicit, versioned computational records of an observation, a target, an analysis, a
scenario or an investigation — with provenance, an integrity hash and deterministic comparison.

Semantics (stated on every twin): a twin is a structured *record* of what Skytrace knows and did. None of these twins
models the physics of an astronomical object; "twin" here means a faithful, comparable digital record, not a
physical simulation. Every twin has:

  schema        skytrace.twin/1
  kind          observation | target | analysis | scenario | investigation
  id            stable identifier of the thing it represents
  sections      inputs · parameters · methods · measurements · outputs · assumptions · provenance (each may be empty)
  derived_from  content hashes / SHA-256s of the records it was built from
  version       1 + number of earlier twins of the same id in the caller's history (the caller decides; default 1)
  content_hash  SHA-256 of the SKY-CANON-1 text of the twin without content_hash

compare(a, b) returns every differing leaf path per section, in sorted order, with both values; it is a plain
structural diff (no tolerance), so "differs" means "differs".
"""

from __future__ import annotations

from . import canon

METHOD = "TWIN-1"
SCHEMA_ID = "skytrace.twin/1"
KINDS = ("observation", "target", "analysis", "scenario", "investigation")
SECTIONS = ("inputs", "parameters", "methods", "measurements", "outputs", "assumptions", "provenance")
SEMANTICS = ("A computational record of what Skytrace knows and did, not a physical model of an astronomical object.")


def _fin(kind, tid, sections, derived, version=1):
    assert kind in KINDS
    body = {"schema": SCHEMA_ID, "method": METHOD, "kind": kind, "id": str(tid), "version": int(version), "semantics": SEMANTICS,
            "sections": {s: _clean(sections.get(s, {})) for s in SECTIONS}, "derived_from": sorted(set(derived))}
    body["content_hash"] = canon.digest(body)
    return body


def _clean(v):
    """Make a value representable in SKY-CANON-1 (non-finite numbers become null; large integers become text)."""
    import math
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, int) and not isinstance(v, bool) and abs(v) > 2 ** 53:
        return str(v)
    if isinstance(v, float) and v.is_integer() and abs(v) > 2 ** 53:
        return str(v)
    return v


def verify(t: dict) -> bool:
    return canon.digest({k: v for k, v in t.items() if k != "content_hash"}) == t.get("content_hash")


def _ev(record):
    out = {}
    for e in record["events"]:
        out.setdefault(e["step"], e)
    return out


def observation(record: dict, discovery: dict, manifest: dict, key: str) -> dict:
    o = next((x for x in discovery.get("observations", []) if x["key"] == key), None)
    if o is None:
        raise KeyError(key)
    f = next((x for x in manifest.get("files", []) if x["path"] == o.get("file")), {}) if o.get("file") else {}
    steps = [{"step": e["step"], "status": e["status"], "detail": str(e.get("detail", ""))[:200]} for e in record["events"]
             if (e.get("data") or {}).get("key") == key or (e.get("data") or {}).get("obs_key") == key or key in str(e.get("detail", ""))][:20]
    meas = next((m for m in ((_ev(record).get("spectrum") or {}).get("data") or {}).get("points", []) if m["key"] == key), None)
    return _fin("observation", key, {
        "inputs": {"file": o.get("file"), "sha256": f.get("sha256"), "release": o.get("release"), "detector": o.get("detector"),
                   "t_mid_iso": o.get("t_mid_iso"), "included": o.get("included"), "exclusion_reason": o.get("exclusion_reason")},
        "measurements": meas or {}, "outputs": {"processing_steps": steps},
        "provenance": f.get("provenance") or {}}, [record["content_hash"]] + ([f["sha256"]] if f.get("sha256") else []))


def target(target_json: dict, record: dict | None = None) -> dict:
    outs = {o["question"]: o["category"] for o in _ev(record)["assess"]["data"]["outcomes"]} if record else {}
    return _fin("target", target_json.get("target_id"), {
        "inputs": {"name": target_json.get("name"), "kind": target_json.get("kind"), "identity": target_json.get("identity")},
        "parameters": {"astrometry": target_json.get("astrometry")}, "outputs": {"outcomes": outs},
        "assumptions": {"catalogue": (target_json.get("astrometry") or {}).get("source")}},
        [record["content_hash"]] if record else [])


def analysis_twin(record: dict) -> dict:
    ev = _ev(record)
    p = record.get("parameters", {})
    outs = ev["assess"]["data"]["outcomes"]
    a = (ev.get("astrometry") or {}).get("data") or {}
    fit = a.get("fit") or {}
    var = (ev.get("variability") or {}).get("data") or {}
    return _fin("analysis", record["content_hash"][:16], {
        "inputs": {"bundle": p.get("bundle"), "bundle_kind": p.get("bundle_kind"), "bundle_manifest_sha256": p.get("bundle_manifest_sha256"),
                   "observations_total": (ev.get("discover") or {}).get("data", {}).get("n_total"),
                   "observations_excluded": (ev.get("discover") or {}).get("data", {}).get("n_excluded")},
        "parameters": {k: v for k, v in p.items() if k not in ("methods", "bundle", "bundle_kind", "bundle_manifest_sha256", "analysis_version")},
        "methods": {"analysis_version": p.get("analysis_version"), **(p.get("methods") or {})},
        "measurements": {"pm_xi_mas_yr": fit.get("pm_xi_mas_yr"), "pm_eta_mas_yr": fit.get("pm_eta_mas_yr"), "sig_xi": fit.get("sig_xi"),
                         "sig_eta": fit.get("sig_eta"), "n_flux_pairs": len(var.get("pairs", [])),
                         "calcheck_error_scale": (var.get("calibration_check") or {}).get("error_scale")},
        "outputs": {o["question"]: o["category"] for o in outs},
        "assumptions": {"thresholds": ev["assess"]["data"].get("thresholds"), "rules": ev["assess"]["data"].get("rules")},
        "provenance": {"content_hash": record["content_hash"], "software": record.get("software")}}, [record["content_hash"]])


def scenario_twin(cf: dict) -> dict:
    s = cf["scenario"]
    return _fin("scenario", cf["scenario_hash"][:16], {
        "inputs": {"baseline_hash": s["baseline_hash"], "target_id": s["target_id"]},
        "parameters": {"kind": s["kind"], "change": s["change"], "baseline_params": s["baseline_params"]},
        "methods": {"method": cf["method"], "value_label": cf["value_label"], "rerun": cf["rerun"]},
        "outputs": cf["counterfactual"]["categories"],
        "assumptions": {"caveat": cf["caveat"]}, "provenance": {"scenario_hash": cf["scenario_hash"]}},
        [s["baseline_hash"]] + ([cf["counterfactual"]["content_hash"]] if cf["counterfactual"].get("content_hash") else []))


def investigation(session: dict) -> dict:
    return _fin("investigation", session["session_id"], {
        "inputs": {"target_id": session.get("target_id"), "runs": [{"content_hash": r["content_hash"], "label": r["label"]} for r in session.get("runs", [])]},
        "parameters": {"question": (session.get("question") or {}).get("text")},
        "outputs": {"n_notes": len(session.get("notebook", [])), "n_plans": len(session.get("plans", [])),
                    "n_experiments": len(session.get("experiments", [])), "n_hypotheses": len(session.get("hypotheses", []))},
        "assumptions": {"hypotheses": [h["statement"] for h in session.get("hypotheses", [])][:20]},
        "provenance": {"session_hash": session.get("content_hash"), "history_events": len(session.get("history", []))}},
        [r["content_hash"] for r in session.get("runs", [])] + ([session["content_hash"]] if session.get("content_hash") else []))


def _leaves(v, path=""):
    if isinstance(v, dict):
        if not v:
            yield path, {}
        for k in sorted(v):
            yield from _leaves(v[k], f"{path}.{k}" if path else k)
    elif isinstance(v, list):
        if not v:
            yield path, []
        for i, x in enumerate(v):
            yield from _leaves(x, f"{path}[{i}]")
    else:
        yield path, v


def compare(a: dict, b: dict) -> dict:
    if a.get("kind") != b.get("kind"):
        return {"method": METHOD, "comparable": False, "reason": f"different kinds ({a.get('kind')} vs {b.get('kind')})"}
    out = {}
    for s in SECTIONS:
        la, lb = dict(_leaves(a["sections"].get(s, {}))), dict(_leaves(b["sections"].get(s, {})))
        diffs = [{"path": k, "a": la.get(k), "b": lb.get(k)} for k in sorted(set(la) | set(lb)) if la.get(k) != lb.get(k) or (k in la) != (k in lb)]
        out[s] = diffs
    return {"method": METHOD, "comparable": True, "kind": a["kind"], "a": a["id"], "b": b["id"],
            "identical": a["content_hash"] == b["content_hash"] or not any(out.values()), "differences": out,
            "counts": {s: len(v) for s, v in out.items()}}
