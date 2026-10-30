"""Data Quality Observatory (DQ-1): named checks with explicit outcomes, and no overall score.

Every check reports one of five outcomes, for the check as a whole and for each item it examined:
  valid          valid under the tested rules (the rule ran and found nothing wrong — not proof of correctness)
  invalid        the rule ran and found a violation
  incompatible   the items cannot be compared under the stated rule (e.g. WLMATCH-2 rejections)
  not_available  the information the rule needs is absent
  not_checked    the rule could not run here (e.g. file hashes without the files)
The aggregate outcome of a check is the most serious item outcome, in that order: invalid, incompatible, not_available,
not_checked, valid. No checks are combined into a score: there is no justified formula for one.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from . import bundle as bmod

METHOD = "DQ-1"
OUTCOMES = ["invalid", "incompatible", "not_available", "not_checked", "valid"]
LABEL = {"valid": "valid under the tested rules", "invalid": "invalid", "incompatible": "incompatible",
         "not_available": "data not available", "not_checked": "not checked"}


def _agg(items, default="valid"):
    present = {i["outcome"] for i in items}
    for o in OUTCOMES:
        if o in present:
            return o
    return default


def _check(cid, name, rule, items, scope, default="valid", note=""):
    return {"id": cid, "name": name, "rule": rule, "scope": scope, "outcome": _agg(items, default),
            "counts": dict(Counter(i["outcome"] for i in items)), "items": items, "note": note}


def _num_ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def checks(record: dict, manifest: dict, discovery: dict, bundle_dir: Path | None = None) -> dict:
    ev = record.get("events", [])
    meas = [e for e in ev if e.get("step") == "measure"]
    out = []

    # DQ-FILES: file integrity (needs the files)
    if bundle_dir is not None:
        v = bmod.verify(Path(bundle_dir))
        items = [{"id": p, "outcome": "invalid", "detail": p} for p in v["problems"]] or \
                [{"id": "bundle", "outcome": "valid", "detail": f"{len(manifest.get('files', []))} files match their SHA-256"}]
        out.append(_check("DQ-FILES", "File integrity", "every file's SHA-256 equals the manifest", items, "all bundle files"))
    else:
        out.append(_check("DQ-FILES", "File integrity", "every file's SHA-256 equals the manifest",
                          [{"id": "bundle", "outcome": "not_checked", "detail": "the files are not present here; hashes were not recomputed"}],
                          "all bundle files"))

    # DQ-META: required metadata per included observation
    files = {f["path"]: f for f in manifest.get("files", [])}
    req = ["obs_id", "release", "detector", "t_mid_iso", "file"]
    items = []
    for o in discovery.get("observations", []):
        if not o.get("included"):
            continue
        miss = [k for k in req if o.get(k) in (None, "")]
        if o.get("file") and o["file"] not in files:
            miss.append("manifest entry")
        items.append({"id": o["key"], "outcome": "not_available" if miss else "valid",
                      "detail": ("missing: " + ", ".join(miss)) if miss else "all required fields present"})
    out.append(_check("DQ-META", "Required observation metadata", "obs_id, release, detector, mid-time and file are present and the file is in the manifest",
                      items, f"{len(items)} included observations"))

    # DQ-VALUES: invalid measured values
    items = []
    for e in meas:
        d = e.get("data") or {}
        k = d.get("obs_id")
        bad = []
        ph = d.get("photometry") or {}
        if ph.get("status") == "ok":
            if not _num_ok(ph.get("flux_ujy")):
                bad.append("flux is not a finite number")
            if not _num_ok(ph.get("flux_err_ujy")) or ph.get("flux_err_ujy", 1) <= 0:
                bad.append("flux error is not a positive finite number")
        wl, bw = d.get("wavelength_um"), d.get("bandwidth_um")
        if wl is not None and (not _num_ok(wl) or not 0.7 <= wl <= 5.1):
            bad.append(f"wavelength {wl} µm outside 0.7–5.1 µm")
        if bw is not None and (not _num_ok(bw) or bw <= 0):
            bad.append("bandwidth is not positive")
        c = d.get("centroid") or {}
        if c.get("converged") and (not _num_ok(c.get("sigma_x")) or not _num_ok(c.get("sigma_y")) or c["sigma_x"] <= 0 or c["sigma_y"] <= 0):
            bad.append("centroid error is not positive")
        if wl is None:
            items.append({"id": k, "outcome": "not_available", "detail": "no wavelength at the target"})
        else:
            items.append({"id": k, "outcome": "invalid" if bad else "valid", "detail": "; ".join(bad) or "values in range"})
    out.append(_check("DQ-VALUES", "Measured values", "fluxes finite, errors positive, wavelength within the SPHEREx range, bandwidth and centroid errors positive",
                      items, f"{len(items)} measurements"))

    # DQ-UNITS: units declared by the inspected files
    insp = [e for e in ev if e.get("step") == "inspect"]
    bunits = Counter((e["data"].get("image_bunit"), e["data"].get("variance_bunit")) for e in insp)
    if not insp:
        items = [{"id": "files", "outcome": "not_available", "detail": "no file structure was inspected"}]
    else:
        ok_units = {("MJy/sr", "(MJy/sr)^2")}
        items = [{"id": f"{u[0]} / {u[1]}", "outcome": "valid" if u in ok_units else "invalid",
                  "detail": f"{n} inspected file(s) declare image {u[0]}, variance {u[1]}"} for u, n in bunits.items()]
    out.append(_check("DQ-UNITS", "Units", "image MJy/sr and variance (MJy/sr)^2, as the photometry assumes",
                      items, f"{len(insp)} inspected files (one per detector), of {len(meas)} measured",
                      note="only the inspected files were read for header units; the others are assumed to share their detector's product layout"))

    # DQ-FLAGS: flag bits applied and unresolved
    items = []
    for e in meas:
        fs = (e.get("data") or {}).get("flag_summary") or {}
        k = e["data"].get("obs_id")
        if fs.get("n_reject"):
            items.append({"id": k, "outcome": "invalid", "detail": f"{fs['n_reject']} aperture pixel(s) carry rejecting flags: {', '.join(fs.get('reject_names', []))}"})
        elif fs.get("unresolved"):
            items.append({"id": k, "outcome": "not_checked", "detail": "flag bits not defined in this file's header: " + ", ".join(fs["unresolved"])})
        else:
            items.append({"id": k, "outcome": "valid", "detail": "no rejecting flags in the aperture"})
    out.append(_check("DQ-FLAGS", "Quality flags", "FLAGPOL-1: no rejecting flag bits inside the aperture; bits the header does not define cannot be checked",
                      items, f"{len(items)} measurements"))

    # DQ-PAIRS: incompatible observation pairs
    p = next((e["data"] for e in ev if e.get("step") == "pairs"), None)
    if p is None:
        items = [{"id": "pairs", "outcome": "not_available", "detail": "no pairing step recorded"}]
    else:
        items = [{"id": "accepted", "outcome": "valid", "detail": f"{len(p.get('accepted', []))} pairs accepted by {p.get('rule')}"}]
        items += [{"id": code, "outcome": "incompatible", "detail": f"{n} pairs: {code.replace('_', ' ')}"} for code, n in sorted(p.get("rejection_reasons", {}).items())]
    out.append(_check("DQ-PAIRS", "Comparable observation pairs", "WLMATCH-2 decisions, with the reason for each rejection", items, "all pairs of measured observations",
                      note="incompatible pairs are expected: most pairs sample different wavelengths"))

    # DQ-CAL: calibration information for brightness comparisons
    var = next((e["data"] for e in ev if e.get("step") == "variability"), None) or {}
    pairs = var.get("pairs", [])
    items = []
    for q in pairs:
        dcal = q.get("differential") or {}
        pid = f"{q.get('a')} → {q.get('b')}"
        items.append({"id": pid, "outcome": "valid" if dcal.get("calibrated") else "not_available",
                      "detail": f"{dcal.get('n_refs', 0)} matched reference stars" + ("" if dcal.get("calibrated") else " (3 needed): calibrated comparison not possible")})
    cc = var.get("calibration_check") or {}
    if cc:
        items.append({"id": "CALCHECK-1", "outcome": "valid" if cc.get("status") not in (None, "insufficient") else "not_available",
                      "detail": f"reference scatter {cc.get('robust_scatter')}× stated errors; error scale {cc.get('error_scale')}" if cc.get("status") != "insufficient" else "too few reference stars"})
    out.append(_check("DQ-CAL", "Calibration information", "≥ 3 wavelength-matched reference stars per compared pair (PAIRDIFF-2), and a calibration check",
                      items or [{"id": "pairs", "outcome": "not_available", "detail": "no compared pairs"}], f"{len(pairs)} compared pairs"))

    # DQ-PROV: provenance fields of the stored files
    items = []
    for f in manifest.get("files", []):
        pv = f.get("provenance") or {}
        miss = [k for k in ("source", "origin", "retrieved_at") if not pv.get(k)]
        opt = [k for k in ("source_url", "dataset_id", "release") if not pv.get(k)]
        if miss:
            items.append({"id": f["path"], "outcome": "not_available", "detail": "missing: " + ", ".join(miss)})
        else:
            items.append({"id": f["path"], "outcome": "valid", "detail": f"origin {pv.get('origin')}" + (f"; not recorded: {', '.join(opt)}" if opt else "")})
    out.append(_check("DQ-PROV", "File provenance", "every manifest file records its source, origin and retrieval time", items, f"{len(items)} files",
                      note="synthetic files have no archive URL or dataset identifier, by construction"))

    # DQ-STEPS: processing steps that did not complete
    items = [{"id": f"{e['step']}:{(e.get('data') or {}).get('obs_id') or (e.get('data') or {}).get('key') or i}",
              "outcome": "not_available" if e["status"] in ("failed", "skipped") else "incompatible" if e["status"] == "rejected" else "valid",
              "detail": e.get("detail", "")} for i, e in enumerate(ev) if e.get("status") in ("failed", "skipped", "rejected")]
    out.append(_check("DQ-STEPS", "Processing steps", "every logged step completed; failed, skipped or rejected steps are listed with their reason",
                      items or [{"id": "all", "outcome": "valid", "detail": f"{len(ev)} steps completed"}], f"{len(ev)} logged steps"))

    # DQ-ASTRO: astrometric usability
    codes = Counter((e.get("data") or {}).get("astro_code") or "none" for e in meas)
    items = [{"id": c, "outcome": "valid" if c == "ok" else "not_available", "detail": f"{n} exposure(s): {c.replace('_', ' ')}"} for c, n in sorted(codes.items())]
    out.append(_check("DQ-ASTRO", "Astrometric usability", "an exposure is usable for the motion fit when its plate solution and target centroid succeed",
                      items, f"{len(meas)} measurements"))

    # DQ-RECORD: integrity of the record itself
    from .provenance import stable_hash
    body = {k: v for k, v in record.items() if k not in ("created_at", "software", "content_hash")}
    ok = stable_hash(body) == record.get("content_hash")
    out.append(_check("DQ-RECORD", "Record integrity", "the record's content hash recomputes", [{"id": "record", "outcome": "valid" if ok else "invalid",
                      "detail": "content hash recomputes" if ok else "the record was modified"}], "the investigation record"))

    totals = Counter(c["outcome"] for c in out)
    return {"method": METHOD, "content_hash": record.get("content_hash"), "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic",
            "outcomes": OUTCOMES, "labels": LABEL, "checks": out, "summary": {o: totals.get(o, 0) for o in OUTCOMES},
            "files_checked_here": bundle_dir is not None,
            "note": "no overall quality score: each check stands on its own rule"}
