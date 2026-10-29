"""Provenance verification of an investigation record against its bundle (PROVCHECK-1).

Answers: can every number in this record be traced to a specific stored file whose
bytes are unchanged, and does the record say truthfully what kind of data it rests on?

Checks (each reported with an id, pass/fail and detail; nothing is parsed from free text):
  bundle_integrity     the bundle verifies against its manifest (sizes, SHA-256, origins, SYNTHETIC flags)
  bundle_identity      the record was made from this exact manifest (manifest SHA-256 matches)
  record_hash          the record's content hash recomputes
  file_provenance      every provenance entry carrying a content hash matches a file in the manifest,
                       and every measured file is listed with that hash
  data_origin          synthetic bundles produce only synthetic provenance; archive bundles only live/cache
  observation_keys     every measured observation exists in the bundle's discovery index and was included
  status_codes         every quality / astrometry / pair code and outcome category is a known code
  methods              the record names the method version of each step (v2 records)
  outcome_consistency  outcome evidence agrees with the step data it summarises
  determinism          (optional) re-running the analysis reproduces the content hash
"""

from __future__ import annotations

import math
from pathlib import Path

from . import bundle as bmod
from .provenance import stable_hash
from .science import assess
from .science.measure import ASTRO_CODES, QUALITY_CODES
from .science.wavelength import PAIR_CODES

METHOD = "PROVCHECK-1"
FAILURE_CODES = {"unreadable", "measurement_error", "no_time"}
SYNTHETIC_ORIGINS = {"synthetic"}
ARCHIVE_ORIGINS = {"live", "cache"}


def _check(out: list, cid: str, ok: bool, detail: str, **extra) -> None:
    out.append({"id": cid, "ok": bool(ok), "detail": detail, **extra})


def verify_record(record: dict, bundle_dir: Path, rerun: bool = False) -> dict:
    checks: list[dict] = []
    bundle_dir = Path(bundle_dir)
    v = bmod.verify(bundle_dir)
    _check(checks, "bundle_integrity", v["ok"], "bundle verifies against its manifest" if v["ok"] else
           f"{len(v['problems'])} problem(s): " + "; ".join(v["problems"][:5]))
    b = bmod.load(bundle_dir)
    params = record.get("parameters", {})

    mhash = bmod.sha256_file(bundle_dir / "manifest.json")
    _check(checks, "bundle_identity", params.get("bundle_manifest_sha256") == mhash,
           "record was made from this manifest" if params.get("bundle_manifest_sha256") == mhash else
           "manifest has changed since the record was made (re-run the analysis)")

    body = {k: v_ for k, v_ in record.items() if k not in ("created_at", "software", "content_hash")}
    _check(checks, "record_hash", stable_hash(body) == record.get("content_hash"),
           "content hash recomputes" if stable_hash(body) == record.get("content_hash") else "record content was modified")

    shas = {f["sha256"]: f["path"] for f in b.manifest["files"]}
    by_path = {f["path"]: f for f in b.manifest["files"]}
    bad_prov, origins, n_prov = [], set(), 0
    for i, e in enumerate(record.get("events", [])):
        for p in e.get("provenance", []):
            n_prov += 1
            origins.add(p.get("origin"))
            h = p.get("content_sha256")
            if h and h not in shas:
                bad_prov.append(f"event {i} ({e['step']}): hash {h[:12]}… not in manifest")
        f = (e.get("data") or {}).get("file")
        if e["step"] == "measure" and f:
            fe = by_path.get(f)
            if fe is None:
                bad_prov.append(f"event {i}: measured file {f} not in manifest")
            elif e.get("provenance") and e["provenance"][0].get("content_sha256") != fe["sha256"]:
                bad_prov.append(f"event {i}: provenance hash of {f} differs from the manifest")
    _check(checks, "file_provenance", not bad_prov,
           f"{n_prov} provenance entries trace to manifest files" if not bad_prov else "; ".join(bad_prov[:5]),
           n_problems=len(bad_prov))

    allowed = SYNTHETIC_ORIGINS if b.kind == "synthetic" else ARCHIVE_ORIGINS
    stray = sorted(o for o in origins if o not in allowed)
    kind_ok = params.get("bundle_kind") == b.kind
    _check(checks, "data_origin", not stray and kind_ok,
           f"{b.kind} bundle; provenance origins {sorted(origins)}" if not stray and kind_ok else
           f"{b.kind} bundle but origins {stray} / record kind {params.get('bundle_kind')!r}")

    obs_keys = {o["key"]: o for o in b.all_observations()}
    missing, excluded = [], []
    for e in record.get("events", []):
        if e["step"] != "measure":
            continue
        k = (e.get("data") or {}).get("key")
        if k not in obs_keys:
            missing.append(k)
        elif not obs_keys[k].get("included"):
            excluded.append(k)
    _check(checks, "observation_keys", not missing and not excluded,
           "every measured observation is in the discovery index and was included" if not missing and not excluded
           else f"unknown keys {missing[:3]}; excluded but measured {excluded[:3]}")

    unknown = []
    for e in record.get("events", []):
        d = e.get("data") or {}
        if e["step"] == "measure" and "quality_code" in d:
            if d["quality_code"] not in QUALITY_CODES | FAILURE_CODES:
                unknown.append(f"quality_code {d['quality_code']}")
            if d.get("astro_code") not in ASTRO_CODES | FAILURE_CODES:
                unknown.append(f"astro_code {d.get('astro_code')}")
        if e["step"] == "pairs":
            for code in d.get("rejection_reasons", {}):
                if code not in PAIR_CODES:
                    unknown.append(f"pair code {code}")
        if e["step"] == "assess":
            for o in d.get("outcomes", []):
                if o.get("rules") == assess.RULES and o["category"] not in assess.CATEGORIES.get(o["question"], ()):
                    unknown.append(f"category {o['category']}")
    v1 = params.get("analysis_version") == "skytrace-analysis/1"
    _check(checks, "status_codes", not unknown,
           ("all codes are known" + (" (v1 record: free-text statuses, codes not present)" if v1 else ""))
           if not unknown else "; ".join(sorted(set(unknown))[:6]))

    meth = params.get("methods")
    need = ("wavelength_match", "reference_selection", "ephemeris", "variability", "motion_primary", "assessment")
    _check(checks, "methods", bool(meth) and all(k in meth for k in need),
           f"methods recorded: {meth}" if meth else "record does not name its method versions (pre-v2 record)")

    ev = {e["step"]: e for e in record.get("events", [])}
    problems = []
    outs = {o["question"]: o for o in (ev.get("assess", {}).get("data", {}) or {}).get("outcomes", [])}
    if "variability" in outs and "variability" in ev:
        n_pairs = len(ev["variability"]["data"].get("pairs", []))
        if outs["variability"]["evidence"].get("n_matched_pairs", 0) > n_pairs:
            problems.append("variability outcome counts more pairs than were compared")
    if "motion" in outs and ev.get("astrometry", {}).get("status") == "ok":
        f = ev["astrometry"]["data"]["fit"]
        pm = math.hypot(f["pm_xi_mas_yr"], f["pm_eta_mas_yr"])
        pm_o = outs["motion"]["evidence"].get("pm_measured_mas_yr")
        if pm_o is not None and abs(pm_o - pm) > 1e-6 * max(1.0, pm):
            problems.append("motion outcome pm differs from the astrometry fit")
    _check(checks, "outcome_consistency", not problems, "outcomes agree with step data" if not problems else "; ".join(problems))

    if rerun:
        from . import analysis
        p = {k: params[k] for k in analysis.DEFAULTS if k in params}
        again = analysis.run(b, p).to_dict()
        same = again["content_hash"] == record.get("content_hash")
        _check(checks, "determinism", same, "re-run reproduces the content hash" if same else
               f"re-run produced {again['content_hash'][:12]}… (analysis version {analysis.ANALYSIS_VERSION})")

    return {"method": METHOD, "ok": all(c["ok"] for c in checks), "target": b.target_id, "bundle_kind": b.kind,
            "record_hash": record.get("content_hash"), "checks": checks}
