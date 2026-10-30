"""Phase 7 API: Scientific Possibility Engine, Discovery Horizon, Adversarial Science Lab, information analysis,
Review Room, Reproducibility Challenge, Astro-Twins, Counterfactual Lab, Synthetic Observatory and Observation
Design Lab.

All results are computed by the deterministic modules from recorded values (or, for scenarios, by re-running the
unchanged pipeline). Session-dependent refinements (what you examined, which challenges you acknowledged, your notes)
are applied in the browser by web/js/frontiercore.js, whose rules are parity-tested against these modules.
"""

from __future__ import annotations

import json

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.routing import Route

from .. import (adversarial, canon, counterfactual, discovery, hypotheses, infogain, planner, possibility, repro, review, synthobs,
                twin, uncertainty)
from ..view import InvestigationView

_CACHE: dict[str, dict] = {}


def _app():
    from . import app as a
    return a


def frontier_report(e: dict, stability: dict | None, server: bool = True) -> dict:
    """Everything the Phase 7 workspaces show for one investigation, without session-specific refinements."""
    from . import research
    a = _app()
    rec = e["record"]
    key = rec["content_hash"] + (canon.digest(stability) if stability else "")
    if key in _CACHE:
        return _CACHE[key]
    bdir = a._bundle_dirs()[e["target_id"]]
    v: InvestigationView = a._view(e)
    disc = discovery.report(rec, v.discovery, v.manifest, a.availability())
    res = research.research_report(e)
    hyp = disc["hypotheses"]
    unc = disc["uncertainty"]
    asl = adversarial.challenges(rec, hyp, res["quality"], res["ledger"], unc, stability, None, None)
    info = infogain.analyse(hyp, server)
    spe = possibility.layers(rec, disc, res, info, asl, None, server, bool(stability))
    rp = repro.audit(rec, bdir, rerun=False)
    q = None
    rv = review.review(rec, res["quality"], res["ledger"], hyp, unc, rp, asl, None, q)
    target = a._bundle(e["target_id"]).target
    out = {"content_hash": rec["content_hash"], "spe": spe, "asl": asl, "info": info, "review": rv, "repro": rp,
           "twins": {"analysis": twin.analysis_twin(rec), "target": twin.target(target, rec)},
           "synthetic": v.is_synthetic(), "stability_used": bool(stability)}
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[key] = out
    return out


async def frontier_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    body = await a._body(request) if request.method == "POST" else {}
    st = body.get("stability")
    if st is not None and not (isinstance(st, dict) and isinstance(st.get("runs"), list) and len(json.dumps(st)) < 400_000):
        raise a.APIError(400, "stability must be a STAB-1 result")
    return a._json(await run_in_threadpool(frontier_report, e, st))


async def reproduce_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    res = await run_in_threadpool(repro.audit, e["record"], a._bundle_dirs()[e["target_id"]], True)
    return a._json(res)


async def counterfactual_route(request: Request):
    a = _app()
    body = await a._body(request)
    tid = str(body.get("target_id") or "")
    spec = body.get("scenario")
    errs = counterfactual.validate(spec)
    if errs:
        raise a.APIError(400, "; ".join(errs))
    a._bundle(tid)
    base = None
    iid = body.get("baseline_investigation_id")
    if iid:
        e = a._inv(str(iid))
        if e["target_id"] != tid:
            raise a.APIError(400, "the baseline investigation belongs to another target")
        base = e["record"]
        bp = {k: base["parameters"][k] for k in ("aperture_radius_px", "fit_half_size_px", "wavelength_tolerance_channels", "epoch_clip_sigma",
                                                  "wavelength_margin_um", "epoch_gap_days", "photometry_same_release", "apply_parallax",
                                                  "reference_quality_cut", "detectors") if k in base["parameters"]}
        spec = {**spec, "baseline_params": {k: v for k, v in bp.items() if v != counterfactual.analysis.DEFAULTS.get(k)},
                "baseline_hash": base["content_hash"]}
    res = await run_in_threadpool(counterfactual.run, lambda t: a._bundle(t), tid, spec, base)
    if res.get("status") == "completed":
        res["twin"] = twin.scenario_twin(res)
    return a._json(res)


async def synthetic_route(request: Request):
    a = _app()
    body = await a._body(request)
    sc = body.get("scenario")
    errs = synthobs.validate(sc) if isinstance(sc, dict) else ["scenario must be an object"]
    if errs:
        raise a.APIError(400, "; ".join(errs))
    return a._json(await run_in_threadpool(synthobs.run, sc))


async def design_route(request: Request):
    a = _app()
    body = await a._body(request)
    tr, sch = body.get("truth"), body.get("schedules")
    if not isinstance(tr, dict):
        raise a.APIError(400, "truth must be an object")
    res = await run_in_threadpool(synthobs.design, tr, sch)
    if res.get("status") == "refused":
        raise a.APIError(400, "; ".join(res["errors"]))
    return a._json(res)


def specs() -> dict:
    return {"counterfactual": {"kinds": list(counterfactual.KINDS), "labels": counterfactual.LABEL, "legend": counterfactual.LEGEND,
                               "threshold_bounds": counterfactual.THRESHOLD_BOUNDS, "error_scale_bounds": counterfactual.ERROR_SCALE_BOUNDS,
                               "param_bounds": counterfactual.analysis.PARAM_BOUNDS, "param_booleans": list(counterfactual.analysis.PARAM_BOOLEANS),
                               "max_excluded_keys": counterfactual.MAX_EXCLUDED_KEYS},
            "synthetic": {"templates": synthobs.TEMPLATES, "positions": synthobs.POSITIONS, "defaults": synthobs.DEFAULTS, "spec": synthobs.SPEC,
                          "design_max": synthobs.DESIGN_MAX},
            "twin": {"sections": list(twin.SECTIONS), "kinds": list(twin.KINDS), "semantics": twin.SEMANTICS},
            "horizon_categories": possibility.CATS, "asl_modes": adversarial.MODES, "asl_severity": adversarial.SEVERITY,
            "review_roles": review.ROLES, "review_causal_words": list(review.CAUSAL_WORDS), "repro_checks": repro.CHECKS,
            "methods": {"spe": possibility.METHOD, "horizon": possibility.HORIZON, "asl": adversarial.METHOD, "info": infogain.METHOD,
                        "review": review.METHOD, "repro": repro.METHOD, "twin": twin.METHOD, "counterfactual": counterfactual.METHOD,
                        "synthetic": synthobs.METHOD, "design": synthobs.DESIGN_METHOD}}


routes = [
    Route("/api/investigations/{iid}/frontier", frontier_route, methods=["GET", "POST"]),
    Route("/api/investigations/{iid}/reproduce", reproduce_route, methods=["POST"]),
    Route("/api/counterfactuals", counterfactual_route, methods=["POST"]),
    Route("/api/synthetic", synthetic_route, methods=["POST"]),
    Route("/api/observation-design", design_route, methods=["POST"]),
]
