"""Independent reproduction (REPROX-1): repeat an analysis under control and say exactly how close the repeat came.

Steps: inspect the original run; fingerprint the environment and compare it with the record; inspect dependencies;
verify the inputs (bundle files against the manifest); verify method versions; restore the recorded parameters; replay
the pipeline; compare every stage numerically (SCIDEBUG-1 `diff`); analyse tolerances; localise the earliest difference.

Verdicts (VERDICTS), by one rule: exact = identical content hash; numerically equivalent = every stage identical or within
a relative 1e-9 though the hash differs; with documented differences = stages differ and the record shows why (software,
parameters or inputs changed); failed = stages differ with no recorded explanation; blocked = the replay could not run
(bundle missing or unreadable). Importing a record is never a reproduction.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from pathlib import Path

from . import __version__, analysis, bundle as bmod, counterfactual as cf, scidebug

METHOD = "REPROX-1"
VERDICTS = ["exact reproduction", "numerically equivalent reproduction", "reproduction with documented differences", "failed reproduction", "blocked reproduction"]


def environment() -> dict:
    def v(p):
        try:
            return importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            return None
    return {"skytrace": __version__, "python": platform.python_version(), "numpy": v("numpy"), "scipy": v("scipy"), "astropy": v("astropy"),
            "platform": platform.platform(), "implementation": sys.implementation.name}


def reproduce(record: dict, bundle_dir: Path | None) -> dict:
    steps = []
    env = environment()
    soft = record.get("software") or {}
    env_rows = [{"package": k, "recorded": soft.get(k), "now": env.get(k), "same": soft.get(k) == env.get(k)} for k in ("skytrace", "python", "numpy", "scipy", "astropy")]
    intact = cf.record_hash(record) == record.get("content_hash")
    steps.append({"step": "original run", "ok": intact, "detail": f"content hash {str(record.get('content_hash'))[:12]}…, {len(record.get('events', []))} events, recorded {record.get('created_at')}"
                  + ("" if intact else "; the record's content does not match its stated hash (edited after it was made)")})
    steps.append({"step": "environment fingerprint", "ok": all(r["same"] for r in env_rows),
                  "detail": "; ".join(f"{r['package']} {r['recorded']} → {r['now']}" for r in env_rows if not r["same"]) or "same versions as recorded"})
    deps = {k: env.get(k) for k in ("numpy", "scipy", "astropy")}
    steps.append({"step": "dependency inspection", "ok": bool(deps["numpy"] and deps["scipy"]), "detail": ", ".join(f"{k} {v or 'not installed'}" for k, v in deps.items())})
    P = record.get("parameters", {})
    if not bundle_dir or not Path(bundle_dir).exists():
        steps.append({"step": "input verification", "ok": False, "detail": f"bundle {P.get('bundle')} is not available here"})
        return _out(record, env, env_rows, steps, None, "blocked reproduction", "the inputs are not available on this machine")
    try:
        b = bmod.load(Path(bundle_dir))
        problems = bmod.verify(Path(bundle_dir)).get("problems", [])
    except Exception as e:      # noqa: BLE001 - a broken bundle blocks the replay; it is reported
        steps.append({"step": "input verification", "ok": False, "detail": f"bundle unreadable: {e}"})
        return _out(record, env, env_rows, steps, None, "blocked reproduction", "the inputs could not be read")
    mh = bmod.sha256_file(Path(bundle_dir) / "manifest.json")
    same_input = mh == P.get("bundle_manifest_sha256")
    steps.append({"step": "input verification", "ok": not problems and same_input,
                  "detail": (f"{len(problems)} file problem(s)" if problems else "bundle files verify") + ("" if same_input else "; manifest differs from the recorded one")})
    rec_methods = P.get("methods") or {}
    cur_methods = analysis.methods()
    mdiff = [k for k in set(rec_methods) | set(cur_methods) if rec_methods.get(k) != cur_methods.get(k)]
    steps.append({"step": "method-version verification", "ok": not mdiff, "detail": ("differs: " + ", ".join(sorted(mdiff))) if mdiff else
                  f"{len(rec_methods)} method roles as recorded ({P.get('analysis_version')})"})
    params = {k: v for k, v in P.items() if k not in ("methods", "analysis_version", "bundle", "bundle_kind", "bundle_manifest_sha256")}
    steps.append({"step": "parameter restoration", "ok": True, "detail": f"{len(params)} parameters restored from the record"})
    try:
        new = json.loads(json.dumps(analysis.run(b, params).to_dict(), default=str))
    except Exception as e:      # noqa: BLE001
        steps.append({"step": "independent replay", "ok": False, "detail": f"replay failed: {e}"})
        return _out(record, env, env_rows, steps, None, "blocked reproduction", "the replay raised an error")
    steps.append({"step": "independent replay", "ok": True, "detail": f"new content hash {new['content_hash'][:12]}…"})
    d = scidebug.diff(record, new)
    tol = [{"stage": s["id"], "kind": s["kind"], "max_rel": s["max_rel"], "numeric": s["numeric"], "structural": s["structural"], "other": s["other"]} for s in d["stages"]]
    steps.append({"step": "numerical comparison", "ok": all(s["kind"] != "different" for s in d["stages"]),
                  "detail": "; ".join(f"{s['id']}: {s['kind']}" for s in d["stages"])})
    steps.append({"step": "difference localization", "ok": d["earliest_divergence"] is None, "detail": f"earliest divergence: {d['earliest_divergence'] or 'none'}"})
    if new["content_hash"] == record.get("content_hash") and intact:
        verdict, why = "exact reproduction", "the replay produced the identical content hash"
    elif all(s["kind"] in ("identical", "numerically equivalent") for s in d["stages"]):
        verdict, why = "numerically equivalent reproduction", "every stage agrees within a relative 1e-9; the hash differs by floating-point detail"
    elif d["software"] or d["parameters"] or not d["inputs"]["same"]:
        verdict, why = "reproduction with documented differences", "; ".join(d["explanation"])
    else:
        verdict, why = "failed reproduction", "stages differ and neither software, parameters nor inputs explain it"
    return _out(record, env, env_rows, steps, {"diff": d, "tolerance": tol, "new_content_hash": new["content_hash"]}, verdict, why)


def _out(record, env, env_rows, steps, comparison, verdict, why):
    return {"method": METHOD, "content_hash": record.get("content_hash"), "verdict": verdict, "why": why, "verdicts": VERDICTS, "environment": env,
            "environment_comparison": env_rows, "steps": steps, "comparison": comparison, "tolerance_rule": f"relative {scidebug.REL_EQUIV:g} per numeric value",
            "note": "Reproduction here shows the calculation repeats on this machine. It does not show the result is physically correct."}
