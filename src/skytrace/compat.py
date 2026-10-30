"""Observation compatibility (COMPAT-1) and multi-epoch sequences (SEQ-1).

COMPAT-1 reads the decisions the pipeline already logged — every WLMATCH-2 acceptance and rejection with its reason
code — and lays them out as a matrix over the measured observations. Nothing is recomputed or inferred from image
appearance: two observations are comparable for brightness exactly when the record says the pair was accepted.

SEQ-1 groups observations into sequences in which every pair is WLMATCH-2-compatible (a clique of accepted pairs),
built greedily in time order per detector. A sequence lists the observed exposures and the visits they belong to;
nothing is interpolated, and a sequence with only two visits says so.

Also reported: per-observation metadata (with missing fields named), duplicate files (identical SHA-256 under different
observation keys), coverage gaps between visits, and grouping by detector and visit.
"""

from __future__ import annotations

from collections import defaultdict

METHOD = "COMPAT-1"
SEQ_METHOD = "SEQ-1"
CODES = {
    "accepted": "wavelength-matched: brightness may be compared (WLMATCH-2)",
    "wavelength_mismatch": "same detector, but the wavelengths at the target differ by more than the tolerance",
    "different_detectors": "different detectors sample different wavelength ranges",
    "different_release": "different archive releases are not combined for photometry",
    "unusable_measurement": "one of the two measurements is not usable (failed or flagged photometry)",
    "not_measured": "one of the two observations has no measurement in this run",
}
META_FIELDS = ["obs_id", "release", "detector", "t_mid_iso", "wavelength_um", "bandwidth_um", "file", "sha256", "access_url",
               "dataset_id"]


def _events(record, step):
    return [e for e in record.get("events", []) if e.get("step") == step]


def observations(record: dict, discovery: dict, manifest: dict) -> list[dict]:
    files = {f["path"]: f for f in (manifest or {}).get("files", [])}
    meas = {e["data"].get("obs_id"): e for e in _events(record, "measure")}
    out = []
    for o in (discovery or {}).get("observations", []):
        if not o.get("included"):
            continue
        m = meas.get(o["key"])
        d = (m or {}).get("data") or {}
        f = files.get(o.get("file") or "")
        prov = (f or {}).get("provenance") or {}
        row = {"key": o["key"], "obs_id": o.get("obs_id") or None, "release": o.get("release") or None, "detector": o.get("detector"),
               "t_mid_iso": o.get("t_mid_iso") or None, "t_mid_mjd": o.get("t_mid_mjd"),
               "wavelength_um": d.get("wavelength_um"), "bandwidth_um": d.get("bandwidth_um"),
               "file": o.get("file") or None, "sha256": (f or {}).get("sha256") or None, "access_url": o.get("access_url") or None,
               "dataset_id": prov.get("dataset_id") or None, "origin": prov.get("origin") or None,
               "measured": m is not None, "status": (m or {}).get("status"), "quality": d.get("quality")}
        row["missing"] = [k for k in META_FIELDS if row.get(k) in (None, "")]
        out.append(row)
    return sorted(out, key=lambda r: (r["detector"] or 0, r["t_mid_mjd"] or 0, r["key"]))


def pair_codes(record: dict) -> dict:
    """{(a, b): (code, reason)} for every pair decision the record logs (both orders)."""
    p = (_events(record, "pairs") or [{}])[0].get("data") or {}
    out = {}
    for d in p.get("accepted", []) + p.get("rejected_same_detector", []):
        out[(d["a"], d["b"])] = out[(d["b"], d["a"])] = (d.get("code") or ("accepted" if d.get("accepted") else "rejected"), d.get("reason", ""))
    return out


def matrix(obs: list[dict], codes: dict) -> dict:
    keys = [o["key"] for o in obs]
    by = {o["key"]: o for o in obs}
    cells, counts = [], defaultdict(int)
    for i, a in enumerate(keys):
        row = []
        for j, b in enumerate(keys):
            if i == j:
                row.append("self")
                continue
            oa, ob = by[a], by[b]
            if (a, b) in codes:
                c = codes[(a, b)][0]
            elif oa["detector"] != ob["detector"]:
                c = "different_detectors"
            elif oa["release"] != ob["release"]:
                c = "different_release"
            elif not (oa["measured"] and ob["measured"]):
                c = "not_measured"
            else:
                c = "unusable_measurement"
            row.append(c)
            if i < j:
                counts[c] += 1
        cells.append(row)
    return {"keys": keys, "cells": cells, "counts": dict(sorted(counts.items())), "codes": CODES}


def visits(obs: list[dict], gap_days: float) -> dict:
    """Visit index per observation: consecutive exposures of one detector closer than gap_days share a visit."""
    out = {}
    for det in sorted({o["detector"] for o in obs}):
        rows = sorted((o for o in obs if o["detector"] == det and o["t_mid_mjd"] is not None), key=lambda o: o["t_mid_mjd"])
        v, last = 0, None
        for o in rows:
            if last is not None and o["t_mid_mjd"] - last > gap_days:
                v += 1
            out[o["key"]] = v
            last = o["t_mid_mjd"]
    return out


def sequences(obs: list[dict], codes: dict, visit_of: dict) -> list[dict]:
    seqs = []
    for det in sorted({o["detector"] for o in obs}):
        rows = [o for o in obs if o["detector"] == det and o["t_mid_mjd"] is not None]
        rows.sort(key=lambda o: (o["t_mid_mjd"], o["key"]))
        used = set()
        for anchor in rows:
            if anchor["key"] in used:
                continue
            members = [anchor]
            for o in rows:
                if o["key"] == anchor["key"] or o["key"] in used:
                    continue
                if all(codes.get((o["key"], m["key"]), ("",))[0] == "accepted" for m in members):
                    members.append(o)
            if len(members) < 2:
                continue
            members.sort(key=lambda o: (o["t_mid_mjd"], o["key"]))
            used.update(m["key"] for m in members)
            vs = sorted({visit_of.get(m["key"]) for m in members if visit_of.get(m["key"]) is not None})
            vt = {}
            for m in members:
                vt.setdefault(visit_of.get(m["key"]), []).append(m["t_mid_mjd"])
            centers = [sum(t) / len(t) for _, t in sorted(vt.items())]
            gaps = [round(b - a, 3) for a, b in zip(centers, centers[1:])]
            wl = [m["wavelength_um"] for m in members if m["wavelength_um"] is not None]
            seqs.append({"id": f"SEQ-D{det}-{len(seqs) + 1}", "detector": det, "release": anchor["release"],
                         "members": [m["key"] for m in members], "n_frames": len(members), "n_visits": len(vs),
                         "t_first_iso": members[0]["t_mid_iso"], "t_last_iso": members[-1]["t_mid_iso"],
                         "span_days": round(members[-1]["t_mid_mjd"] - members[0]["t_mid_mjd"], 3), "visit_gaps_days": gaps,
                         "wavelength_range_um": [min(wl), max(wl)] if wl else None,
                         "note": (f"only {len(vs)} visits" if len(vs) <= 2 else f"{len(vs)} visits") +
                                 "; frames are the observed exposures only — nothing between them was observed or interpolated",
                         "rule": "every pair of members is accepted by WLMATCH-2 in this run"})
    return seqs


def coverage(obs: list[dict], visit_of: dict, min_gap_days: float = 30.0) -> dict:
    per = {}
    for det in sorted({o["detector"] for o in obs}):
        rows = sorted((o for o in obs if o["detector"] == det and o["t_mid_mjd"] is not None), key=lambda o: o["t_mid_mjd"])
        groups = {}
        for o in rows:
            groups.setdefault(visit_of.get(o["key"]), []).append(o)
        vlist = [{"visit": v, "n": len(g), "t_first_iso": g[0]["t_mid_iso"], "t_last_iso": g[-1]["t_mid_iso"],
                  "t_mid_mjd": sum(x["t_mid_mjd"] for x in g) / len(g)} for v, g in sorted(groups.items())]
        gaps = [{"after_visit": a["visit"], "days": round(b["t_mid_mjd"] - a["t_mid_mjd"], 2)}
                for a, b in zip(vlist, vlist[1:]) if b["t_mid_mjd"] - a["t_mid_mjd"] >= min_gap_days]
        per[str(det)] = {"visits": vlist, "gaps": gaps}
    return {"per_detector": per, "gap_threshold_days": min_gap_days}


def duplicates(obs: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for o in obs:
        if o["sha256"]:
            by[o["sha256"]].append(o["key"])
    return [{"sha256": h, "keys": ks} for h, ks in sorted(by.items()) if len(ks) > 1]


def report(record: dict, discovery: dict, manifest: dict) -> dict:
    obs = observations(record, discovery, manifest)
    codes = pair_codes(record)
    gap = float(record.get("parameters", {}).get("epoch_gap_days") or 5.0)
    vis = visits(obs, gap)
    for o in obs:
        o["visit"] = vis.get(o["key"])
    missing = defaultdict(int)
    for o in obs:
        for k in o["missing"]:
            missing[k] += 1
    return {"method": METHOD, "sequence_method": SEQ_METHOD, "content_hash": record.get("content_hash"),
            "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic",
            "observations": obs, "matrix": matrix(obs, codes), "sequences": sequences(obs, codes, vis),
            "coverage": coverage(obs, vis), "duplicates": duplicates(obs),
            "metadata": {"fields": META_FIELDS, "missing_counts": dict(sorted(missing.items())), "n_observations": len(obs)},
            "visit_rule": f"exposures of one detector closer than {gap:g} days (epoch_gap_days) form one visit"}
