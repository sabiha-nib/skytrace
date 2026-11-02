"""REPRONET-1: the reproduction network — reproduction manifests that can travel between machines, and their comparison.

A manifest (schema skytrace.reproduction/1) holds what another researcher needs to repeat a run and compare: the input
dataset reference and the SHA-256 of every input file, software and dependency versions, the analysis configuration, every
method version, the generator seed (synthetic bundles), a digest of every intermediate stage (SCIDEBUG-1 stages over the
recorded events), the final outcomes and their metrics, the environment, and the known limitations. Its own digest (SKY-CANON-1
over everything except `manifest_digest`) lets anyone check it was not altered.

compare(a, b) classifies the differences, in this order:
  exact match              every stage digest and every outcome identical
  different input data     the dataset manifest digest or any input file hash differs
  methodological           parameters or method versions differ
  missing dependency       a dependency recorded in one manifest is absent (null) in the other
  numerical                outputs differ but every outcome metric agrees within a relative 1e-9 (floating point)
  unexplained divergence   outputs differ and none of the above explains it
A comparison names every class that applies; the status is the first. A successful reproduction says the calculation
repeats; it does not say the result is scientifically valid.
"""

from __future__ import annotations

from . import canon, counterfactual as cf, scidebug

METHOD = "REPRONET-1"
SCHEMA = "skytrace.reproduction/1"
CLASSES = ["exact match", "different input data", "methodological", "missing dependency", "numerical", "unexplained divergence"]
REL = 1e-9
REQUIRED = ["schema", "record", "dataset", "software", "configuration", "methods", "stages", "outcomes", "environment", "limitations"]


def manifest(record: dict, bundle_manifest: dict | None, environment: dict, seed=None, limitations: list | None = None) -> dict:
    p = record.get("parameters", {})
    files = sorted(((k, v.get("sha256")) for k, v in ((bundle_manifest or {}).get("files") or {}).items()), key=lambda x: x[0]) \
        if isinstance((bundle_manifest or {}).get("files"), dict) else \
        sorted(((f.get("key") or f.get("path"), f.get("sha256")) for f in ((bundle_manifest or {}).get("files") or [])), key=lambda x: str(x[0]))
    stages = []
    for sid, name, st in scidebug.STAGES:
        evs = [{"step": e.get("step"), "status": e.get("status"), "data": e.get("data")} for _, e in scidebug._steps(record, st)]
        if evs:
            stages.append({"id": sid, "name": name, "n_events": len(evs), "digest": canon.digest(evs)})
    outs = {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}
    m = {"schema": SCHEMA, "method": METHOD, "record": record.get("content_hash"), "record_hash_ok": cf.record_hash(record) == record.get("content_hash"),
         "target": record.get("target"), "synthetic": p.get("bundle_kind") == "synthetic",
         "dataset": {"bundle": p.get("bundle"), "kind": p.get("bundle_kind"), "manifest_sha256": p.get("bundle_manifest_sha256"),
                     "files": [{"key": k, "sha256": h} for k, h in files]},
         "software": record.get("software") or {}, "configuration": {k: v for k, v in p.items() if k not in ("methods",)},
         "methods": p.get("methods") or {}, "seed": seed, "stages": stages,
         "outcomes": {q: {"category": o.get("category"), "metrics": cf.metrics({q: o}).get(q, {}) if isinstance(cf.metrics({q: o}), dict) else {}}
                      for q, o in outs.items()},
         "environment": environment, "limitations": list(limitations or [])[:40],
         "note": "Reproducing these outputs shows the calculation repeats; it does not show the result is scientifically valid."}
    m["manifest_digest"] = canon.digest({k: v for k, v in m.items() if k != "manifest_digest"})
    return m


def validate(m) -> list[str]:
    if not isinstance(m, dict):
        return ["a manifest must be an object"]
    errs = [f"missing field {k}" for k in REQUIRED if k not in m]
    if m.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    if not errs:
        d = canon.digest({k: v for k, v in m.items() if k != "manifest_digest"})
        if d != m.get("manifest_digest"):
            errs.append("manifest digest does not match its content (altered or incomplete)")
    return errs


def _num_close(a, b):
    if isinstance(a, bool) or isinstance(b, bool) or not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return a == b
    return a == b or abs(a - b) <= REL * max(abs(a), abs(b), 1e-300)


def compare(a: dict, b: dict) -> dict:
    cls, detail = [], []
    sa = {s["id"]: s["digest"] for s in a["stages"]}
    sb = {s["id"]: s["digest"] for s in b["stages"]}
    stage_diff = sorted(k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k))
    order = [s["id"] for s in scidebug_stage_order() if s["id"] in set(sa) | set(sb)]
    earliest = next((k for k in order if k in stage_diff), None)
    oc = sorted(q for q in set(a["outcomes"]) | set(b["outcomes"]) if (a["outcomes"].get(q) or {}).get("category") != (b["outcomes"].get(q) or {}).get("category"))
    if not stage_diff and not oc:
        cls.append("exact match")
    else:
        fa = {f["key"]: f["sha256"] for f in a["dataset"]["files"]}
        fb = {f["key"]: f["sha256"] for f in b["dataset"]["files"]}
        fdiff = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
        if a["dataset"].get("manifest_sha256") != b["dataset"].get("manifest_sha256") or fdiff:
            cls.append("different input data")
            detail.append(f"input files differ: {len(fdiff)}" + (f" (e.g. {fdiff[0]})" if fdiff else ""))
        ca, cb = a["configuration"], b["configuration"]
        pdiff = sorted(k for k in set(ca) | set(cb) if k not in ("bundle_manifest_sha256",) and ca.get(k) != cb.get(k))
        mdiff = sorted(k for k in set(a["methods"]) | set(b["methods"]) if a["methods"].get(k) != b["methods"].get(k))
        if pdiff or mdiff:
            cls.append("methodological")
            detail.append("parameters differ: " + ", ".join(pdiff) if pdiff else "methods differ: " + ", ".join(mdiff))
        ea, eb = a.get("environment") or {}, b.get("environment") or {}
        miss = sorted(k for k in set(ea) | set(eb) if (ea.get(k) is None) != (eb.get(k) is None))
        if miss:
            cls.append("missing dependency")
            detail.append("present in one environment only: " + ", ".join(miss))
        if not oc and all(_num_close(v, ((b["outcomes"].get(q) or {}).get("metrics") or {}).get(k))
                          for q, o in a["outcomes"].items() for k, v in (o.get("metrics") or {}).items()):
            if not any(c in cls for c in ("different input data", "methodological")):
                cls.append("numerical")
                detail.append("outcome metrics agree within relative 1e-9")
        if not cls:
            cls.append("unexplained divergence")
            detail.append("outputs differ with identical inputs, configuration, methods and dependencies")
    env_diff = sorted(k for k in set(a.get("environment") or {}) | set(b.get("environment") or {})
                      if (a.get("environment") or {}).get(k) != (b.get("environment") or {}).get(k))
    return {"method": METHOD, "a": a.get("record"), "b": b.get("record"), "status": cls[0], "classes": cls, "detail": detail,
            "stages_differing": stage_diff, "earliest_divergence": earliest, "outcomes_differing": oc, "environment_differences": env_diff,
            "valid_a": validate(a) == [], "valid_b": validate(b) == [],
            "note": "A match shows the calculation repeats. It does not show the result is scientifically valid."}


def scidebug_stage_order():
    return [{"id": s[0]} for s in scidebug.STAGES]
