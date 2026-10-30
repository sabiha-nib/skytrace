"""Reproducibility Challenge (REPRO-1): an audit of whether an investigation can be reproduced, check by check.

Every check reports pass, fail, not checked (it needs something this context does not have — usually the server, for
a re-execution) or not available (the record lacks what the check reads). The verdict follows one stated rule and
is never "reproducible" because a JSON record merely imports:

  reproduced                         R1–R9 pass, including an actual re-execution with an identical content hash
  replayable, not replayed here      R1–R8 pass; R9 (re-execution) was not run in this context
  not reproducible as recorded       any of R1–R9 fails (the failing checks are listed)
  incomplete                         otherwise (a check could not be evaluated)

R10–R11 (figures traceable, limitations included) are reported but do not change the verdict.
The tolerance for R9 is exact equality of the content hash: the pipeline is deterministic, so any difference is a
difference.
"""

from __future__ import annotations

from pathlib import Path

from . import analysis, bundle as bmod, provenance_check

METHOD = "REPRO-1"
CHECKS = [("R1", "Original inputs identifiable", "the record names its bundle and the manifest SHA-256 it was made from"),
          ("R2", "Input files available", "the bundle directory exists here"),
          ("R3", "Checksums valid", "every bundle file's SHA-256 equals its manifest entry (PROVCHECK-1 bundle_integrity, bundle_identity)"),
          ("R4", "Method versions recorded", "the record lists the analysis version and every method version (PROVCHECK-1 methods)"),
          ("R5", "Parameters recorded", "every analysis parameter is stated in the record"),
          ("R6", "Dependencies documented", "software versions (Skytrace, Python, NumPy) are in the record"),
          ("R7", "Execution environment described", "the FITS reader used and the platform versions are recorded"),
          ("R8", "Record integrity", "the record's content hash recomputes (PROVCHECK-1 record_hash)"),
          ("R9", "Replay matches", "a re-execution gives the identical content hash (PROVCHECK-1 determinism)"),
          ("R10", "Figures traceable", "exported figures in the session carry this run's content hash"),
          ("R11", "Limitations included", "every outcome states its limitations")]


def audit(record: dict, bundle_dir: Path | None, rerun: bool, session: dict | None = None) -> dict:
    res = {}
    params = record.get("parameters", {})
    res["R1"] = ("pass", f"bundle {params.get('bundle')} · manifest {str(params.get('bundle_manifest_sha256'))[:12]}…") \
        if params.get("bundle") and params.get("bundle_manifest_sha256") else ("fail", "bundle or manifest hash not stated")
    pc = None
    if bundle_dir is None or not Path(bundle_dir).exists():
        res["R2"] = ("fail" if bundle_dir is not None else "not checked", "the bundle is not present here" if bundle_dir is not None else
                     "this context cannot read bundle files (static preview)")
    else:
        res["R2"] = ("pass", f"{Path(bundle_dir).name}: {len(bmod.load(bundle_dir).manifest['files'])} files")
        pc = provenance_check.verify_record(record, Path(bundle_dir), rerun=rerun)
    byid = {c["id"]: c for c in (pc or {}).get("checks", [])}
    if pc:
        ok = byid["bundle_integrity"]["ok"] and byid["bundle_identity"]["ok"]
        res["R3"] = ("pass" if ok else "fail", byid["bundle_integrity"]["detail"] + "; " + byid["bundle_identity"]["detail"])
        res["R4"] = ("pass" if byid["methods"]["ok"] else "fail", byid["methods"]["detail"])
        res["R8"] = ("pass" if byid["record_hash"]["ok"] else "fail", byid["record_hash"]["detail"])
        if "determinism" in byid:
            res["R9"] = ("pass" if byid["determinism"]["ok"] else "fail", byid["determinism"]["detail"])
        else:
            res["R9"] = ("not checked", "re-execution needs the server (or was not requested)")
    else:
        res["R3"] = ("not checked", "needs the bundle files")
        mv = params.get("methods") and params.get("analysis_version")
        res["R4"] = ("pass" if mv else "fail", f"analysis {params.get('analysis_version')}; {len(params.get('methods') or {})} method entries" if mv else "method versions missing")
        from .counterfactual import record_hash
        res["R8"] = ("pass", "content hash recomputes") if record_hash(record) == record.get("content_hash") else ("fail", "record content was modified")
        res["R9"] = ("not checked", "re-execution needs the server")
    missing = [k for k in analysis.DEFAULTS if k not in params]
    res["R5"] = ("pass", f"{len(analysis.DEFAULTS)} parameters stated") if not missing else ("fail", "missing: " + ", ".join(missing))
    sw = record.get("software") or {}
    res["R6"] = ("pass", ", ".join(f"{k} {v}" for k, v in sorted(sw.items()))) if sw.get("skytrace") and sw.get("python") else ("fail", "software versions missing")
    res["R7"] = ("pass", f"reader {params.get('reader')}; python {sw.get('python')}; numpy {sw.get('numpy')}") \
        if params.get("reader") and sw.get("numpy") else ("not available", "reader or platform versions not recorded")
    figs = [b for b in (session or {}).get("notebook", []) if b.get("type") == "figure"]
    if not figs:
        res["R10"] = ("not available", "no figures in the session")
    else:
        h = record.get("content_hash", "")
        tied = [b for b in figs if h[:12] in str(b.get("ref") or "") or h[:12] in str(b.get("text") or "")]
        res["R10"] = ("pass" if len(tied) == len(figs) else "fail", f"{len(tied)} of {len(figs)} figure block(s) cite this run")
    outs = next((e for e in record["events"] if e["step"] == "assess"), {}).get("data", {}).get("outcomes", [])
    res["R11"] = ("pass", f"{len(outs)} outcomes, each with limitations") if outs and all(o.get("limitations") for o in outs) else ("fail", "an outcome has no limitations")
    rows = [{"id": cid, "name": n, "rule": rule, "outcome": res[cid][0], "detail": res[cid][1]} for cid, n, rule in CHECKS]
    core = [r for r in rows if r["id"] in [f"R{i}" for i in range(1, 10)]]
    if all(r["outcome"] == "pass" for r in core):
        verdict = "reproduced"
    elif any(r["outcome"] == "fail" for r in core):
        verdict = "not reproducible as recorded"
    elif all(r["outcome"] == "pass" for r in core if r["id"] != "R9") and next(r for r in core if r["id"] == "R9")["outcome"] == "not checked":
        verdict = "replayable, not replayed here"
    else:
        verdict = "incomplete"
    return {"method": METHOD, "content_hash": record.get("content_hash"), "checks": rows, "verdict": verdict,
            "verdict_rule": __doc__.split("never \"reproducible\" because a JSON record merely imports:")[1].split("R10–R11")[0].strip(),
            "tolerance": "exact content-hash equality (deterministic pipeline)", "provcheck": pc and {"ok": pc["ok"], "checks": pc["checks"]}}
