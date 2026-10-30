"""Phase 6 API: research sessions, planner, research reports (compatibility, quality, ledger, radar), experiments,
provenance verification, connectors, workflows and the specification documents the browser interprets.

Every route validates its input with the same schemas the browser uses (served at /api/specs) and computes results
with the deterministic modules; nothing here contacts an external service.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from .. import (bundle as bmod, capabilities, compat, connectors, experiments, hypotheses, ledger, missions, planner, quality,
                radar, schema, session, workflows)
from ..archive.net import offline_enabled
from ..provenance_check import verify_record

SESSIONS = Path(os.environ.get("SKYTRACE_SESSIONS_DIR") or bmod.ROOT / "data" / "sessions")
_SID = re.compile(r"^[a-z0-9]{12}$")
_CACHE: dict[str, dict] = {}


def _app():
    from . import app as a
    return a


def specs() -> dict:
    """Everything the browser needs to interpret, validate and plan exactly as the server does."""
    return {"version": capabilities.REGISTRY_VERSION, "session_schema": session.SESSION_SCHEMA, "session_schema_id": session.SCHEMA_ID,
            "workflow_schema": workflows.WORKFLOW_SCHEMA, "workflow_limits": {"max_targets": workflows.MAX_TARGETS, "max_steps": workflows.MAX_STEPS,
                                                                              "max_executions": workflows.MAX_EXECUTIONS},
            "workflow_templates": workflows.TEMPLATES, "action_inputs": {a["id"]: a["inputs"] for a in capabilities.ACTIONS},
            "planner": planner.SPEC, "missions": missions.MISSIONS, "experiment_templates": experiments.TEMPLATES,
            "experiment_max_runs": experiments.MAX_RUNS, "block_types": session.BLOCK_TYPES, "ref_kinds": session.REF_KINDS,
            "step_status": session.STEP_STATUS, "citations": citations(), "methods": {"session": session.METHOD, "canon": "SKY-CANON-1", "schema": schema.METHOD,
                                                           "planner": planner.METHOD, "missions": missions.METHOD, "workflows": workflows.METHOD,
                                                           "experiments": experiments.METHOD}}


def citations() -> list[dict]:
    """The only citations a notebook can insert: the datasets and catalogues this software actually uses."""
    from ..archive import references, spherex
    out = [{"id": f"spherex-{r.lower()}", "text": f"SPHEREx Quick Release {r[-1]} Spectral Images, NASA/IPAC Infrared Science Archive",
            "doi": v["doi"]} for r, v in spherex.RELEASES.items()]
    out.append({"id": "gaia-dr3", "text": "Gaia Data Release 3 (ESA; Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1)",
                "doi": references.GAIA_DR3.split("doi:")[1].rstrip(")")})
    out.append({"id": "simbad", "text": "SIMBAD astronomical database, CDS, Strasbourg", "doi": None})
    return out


def research_report(e: dict) -> dict:
    """COMPAT-1, DQ-1, LEDGER-1 and RADAR-1 for one investigation (cached by content hash)."""
    a = _app()
    h = e["record"]["content_hash"]
    if h in _CACHE:
        return _CACHE[h]
    bdir = a._bundle_dirs()[e["target_id"]]
    b = bmod.load(bdir)
    rec = e["record"]
    g = a.evidence_graph(a._view(e), e["target_id"])
    c = compat.report(rec, b.discovery, b.manifest)
    q = quality.checks(rec, b.manifest, b.discovery, bdir)
    led = ledger.build(rec, g, b.discovery)
    rad = radar.scan(rec, c, q, led, hypotheses.evaluate(rec), network=a.availability().get("network"))
    from ..science.assess import T, pair_significance
    var = next((ev["data"] for ev in rec["events"] if ev["step"] == "variability"), {}) or {}
    scale = (var.get("calibration_check") or {}).get("error_scale")
    sig = []
    for p in var.get("pairs", []):
        z, cal = pair_significance(p, scale)
        sig.append({"a": p["a"], "b": p["b"], "z_raw": p.get("z"), "z_used": z, "calibrated": cal, "delta_t_days": p.get("delta_t_days")})
    out = {"content_hash": h, "compat": c, "quality": q, "ledger": led, "radar": rad,
           "significance": {"method": "ASSESS-2 pair_significance (PAIRDIFF-2 when calibrated, divided by the CALCHECK scale)",
                            "threshold": T["variability_z"], "error_scale": scale, "pairs": sig}}
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[h] = out
    return out


async def specs_route(request: Request):
    return _app()._json(specs())


async def research_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    return a._json(await run_in_threadpool(research_report, e))


async def plan_route(request: Request):
    a = _app()
    body = await a._body(request)
    q = body.get("question")
    facts = body.get("facts") if isinstance(body.get("facts"), dict) else {}
    if not isinstance(q, str) or not q.strip():
        raise a.APIError(400, "question is required")
    facts = {k: facts.get(k) for k in ("has_target_data", "has_run", "run_hash", "pair", "server", "static", "network", "targets", "has_question")}
    facts["server"], facts["static"] = True, False          # the server knows where it runs
    facts["network"] = a.availability().get("network")
    if facts.get("pair") is not None and not (isinstance(facts["pair"], list) and len(facts["pair"]) == 2 and all(isinstance(x, str) for x in facts["pair"])):
        raise a.APIError(400, "facts.pair must be two observation keys")
    return a._json(planner.plan(q[:500], facts))


async def provenance_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    body = await a._body(request)
    rerun = bool(body.get("rerun", True))
    res = await run_in_threadpool(verify_record, e["record"], a._bundle_dirs()[e["target_id"]], rerun)
    return a._json(res)


async def experiment_route(request: Request):
    a = _app()
    body = await a._body(request)
    tid = str(body.get("target_id") or "")
    cfg = {k: body[k] for k in ("template", "configs", "question") if k in body}
    errs = experiments.validate(cfg)
    if errs:
        raise a.APIError(400, "; ".join(errs))
    a._bundle(tid)                                           # 404/409 for unknown or failing bundles
    load = lambda t: a._bundle(t)  # noqa: E731
    return a._json(await run_in_threadpool(experiments.run, load, tid, cfg))


async def connectors_route(request: Request):
    a = _app()
    return a._json(connectors.registry(bmod.ROOT / "data" / "environment_report.json", offline_enabled()))


async def connector_preview_route(request: Request):
    a = _app()
    body = await a._body(request)
    return a._json(connectors.preview(request.path_params["cid"], body.get("params") if isinstance(body.get("params"), dict) else {}))


async def workflow_validate_route(request: Request):
    a = _app()
    body = await a._body(request)
    errs = workflows.validate(body.get("workflow"))
    return a._json({"valid": not errs, "errors": errs})


# ------------------------------------------------------------------ sessions
def _spath(sid: str) -> Path:
    if not _SID.match(sid or ""):
        raise _app().APIError(400, "invalid session id")
    return SESSIONS / f"{sid}.json"


def _store(s: dict) -> dict:
    a = _app()
    errs = session.validate(s)
    if errs:
        raise a.APIError(400, "invalid session: " + "; ".join(errs[:5]))
    s = session.finalize(s)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    tmp = _spath(s["session_id"]).with_suffix(".part")
    tmp.write_text(json.dumps(s, ensure_ascii=False))
    os.replace(tmp, _spath(s["session_id"]))
    return s


async def sessions_list(request: Request):
    a = _app()
    SESSIONS.mkdir(parents=True, exist_ok=True)
    out, bad = [], []
    for p in sorted(SESSIONS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            s = json.loads(p.read_text())
            v = session.verify(s)
            out.append(session.summary(s) | {"integrity": "ok" if v["hash_ok"] else ("invalid" if not v["valid"] else "hash mismatch")})
        except (ValueError, KeyError, TypeError):
            bad.append(p.name)          # an unreadable file is reported, never deleted
    return a._json({"sessions": out, "unreadable": bad, "storage": "server"})


async def sessions_create(request: Request):
    a = _app()
    body = await a._body(request)
    tid = body.get("target_id")
    if tid is not None and not (isinstance(tid, str) and a._SAFE.match(tid)):
        raise a.APIError(400, "invalid target id")
    return a._json(_store(session.new(str(body.get("name") or "Research session"), tid)))


async def sessions_get(request: Request):
    a = _app()
    p = _spath(request.path_params["sid"])
    if not p.exists():
        raise a.APIError(404, "unknown session")
    s = json.loads(p.read_text())
    return a._json(s | {"_verification": session.verify(s)})


async def sessions_put(request: Request):
    a = _app()
    sid = request.path_params["sid"]
    p = _spath(sid)
    if not p.exists():
        raise a.APIError(404, "unknown session")
    body = await a._body(request)
    s = body.get("session")
    if not isinstance(s, dict) or s.get("session_id") != sid:
        raise a.APIError(400, "body.session must be the session with this id")
    return a._json(_store({k: v for k, v in s.items() if k != "_verification"}))


async def sessions_delete(request: Request):
    a = _app()
    p = _spath(request.path_params["sid"])
    if not p.exists():
        raise a.APIError(404, "unknown session")
    p.unlink()
    return a._json({"deleted": request.path_params["sid"]})


async def sessions_import(request: Request):
    """Import an exported session. Refused when invalid or when its stated content hash does not recompute."""
    a = _app()
    body = await a._body(request)
    s = body.get("session")
    v = session.verify(s)
    if not v["valid"]:
        raise a.APIError(400, "not a valid research session: " + "; ".join(v["errors"][:5]))
    if v["hash_ok"] is False:
        raise a.APIError(400, "the session's content hash does not match: it was modified or is incomplete")
    if _spath(s["session_id"]).exists():
        s = dict(s, session_id=session.new("x")["session_id"])         # never overwrite an existing session on import
    s = session.log(s, "session.import", "Imported (content hash verified)" if v["hash_ok"] else "Imported (no hash was stated)")
    return a._json(_store(s) | {"hash_verified": bool(v["hash_ok"])})


async def sessions_from_record(request: Request):
    a = _app()
    rid = request.path_params["rid"]
    p = a._record_path(rid)
    if not p.exists():
        raise a.APIError(404, "unknown record")
    saved = json.loads(p.read_text())
    iid = a._store(saved["target_id"], saved["investigation"]) if saved["target_id"] in a._bundle_dirs() else None
    saved = dict(saved, investigation_id=iid)
    return a._json(_store(session.from_saved_record(saved)))


routes = [
    Route("/api/specs", specs_route),
    Route("/api/investigations/{iid}/research", research_route),
    Route("/api/investigations/{iid}/provenance", provenance_route, methods=["POST"]),
    Route("/api/plan", plan_route, methods=["POST"]),
    Route("/api/experiments", experiment_route, methods=["POST"]),
    Route("/api/connectors", connectors_route),
    Route("/api/connectors/{cid}/preview", connector_preview_route, methods=["POST"]),
    Route("/api/workflows/validate", workflow_validate_route, methods=["POST"]),
    Route("/api/sessions", sessions_list),
    Route("/api/sessions", sessions_create, methods=["POST"]),
    Route("/api/sessions/import", sessions_import, methods=["POST"]),
    Route("/api/sessions/from-record/{rid}", sessions_from_record, methods=["POST"]),
    Route("/api/sessions/{sid}", sessions_get),
    Route("/api/sessions/{sid}", sessions_put, methods=["PUT"]),
    Route("/api/sessions/{sid}", sessions_delete, methods=["DELETE"]),
]
_ = Response
