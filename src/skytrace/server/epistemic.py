"""Phase 8 API: the epistemic layer — reasoning graph (EPI-1), method genome (METHOD-DNA-1), scientific compiler
(SCICOMP-1), debugger (SCIDEBUG-1), knowledge boundary (KBOUND-1), claim stress tests (CLAIMX-1), negative knowledge
(NEG-1), blindspots (BLIND-1), uncertainty flow (UFLOW-1), data lineage (LINEAGE-1), model arena (MODELS-1), FutureLab
(FUTURE-1), decision support (NEXTX-1), question forge (QFORGE-1), integrity firewall facts (INTEG-1), review board
(REVIEWX-1), independent reproduction (REPROX-1) and simulation audit (SIMCHECK-1).

Every result is computed by deterministic modules from the recorded investigation (reproduction and simulation audits
re-run the unchanged pipeline). Session-dependent refinements are applied in the browser by web/js/epistemiccore.js,
parity-tested against these modules. No model is called.
"""

from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.routing import Route

from .. import (blindspot, claims, counterfactual as cf, decide, discovery, epistemic as epi, futurelab, infogain, integrity, lineage,
                methodgenome as mg, modelarena, negspace, reprox, reviewx, scicomp, scidebug, simcheck, synthobs, uflow)

_CACHE: dict[str, dict] = {}


def _app():
    from . import app as a
    return a


def epistemic_report(e: dict) -> dict:
    from . import research
    a = _app()
    rec = e["record"]
    key = rec["content_hash"]
    if key in _CACHE:
        return _CACHE[key]
    v = a._view(e)
    disc = discovery.report(rec, v.discovery, v.manifest, a.availability())
    res = research.research_report(e)
    L, Q = res["ledger"], res["quality"]
    G = epi.build(rec, disc, L, v.manifest)
    genome = mg.genome(rec)
    comp = scicomp.compile_investigation(rec, G, disc, L, v.manifest, Q)
    bnd = claims.boundary(rec, G, disc, L, comp)
    qs = [o for o in G["claims"]]
    stresses = {c[6:]: claims.stress(rec, G, disc, L, comp, Q, c[6:]) for c in qs}
    info = infogain.analyse(disc["hypotheses"], True)
    fut = futurelab.scenarios(rec, disc)
    ok_hash = cf.record_hash(rec) == rec["content_hash"]
    facts = integrity.facts(rec, ok_hash)
    report_check = integrity.check(a._report_md(e), facts)
    results = ["fit:motion"] + qs + [n["id"] for n in G["nodes"] if n["id"].startswith("pair:")]
    lin = {r: lineage.lineage(rec, v.manifest, G, r, reprox.environment()) for r in ["fit:motion"] + qs if any(n["id"] == r for n in G["nodes"])}
    insp = {r: scidebug.inspect(rec, r) for r in results + [n["id"] for n in G["nodes"] if n["id"].startswith("epoch:")] if any(n["id"] == r for n in G["nodes"])}
    out = {"content_hash": key, "synthetic": G["synthetic"], "graph": G, "genome": genome, "method_graph": mg.dependency_graph(), "compile": comp,
           "boundary": bnd, "stress": stresses, "negative": negspace.registry(rec, disc, L), "blindspot": blindspot.base(rec, disc, comp, Q, disc["uncertainty"]),
           "uflow": uflow.flow(rec, disc["uncertainty"]), "lineage": lin, "breakpoints": scidebug.breakpoints(rec), "inspect": insp,
           "models": modelarena.arena(rec), "future": fut, "next": decide.next_steps(bnd, info, stresses, comp, True),
           "questions": decide.questions(disc, bnd, fut), "facts": facts, "report_check": report_check,
           "review": reviewx.board(comp, stresses, report_check, genome)}
    if len(_CACHE) > 32:
        _CACHE.clear()
    _CACHE[key] = out
    return out


async def epistemic_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    return a._json(await run_in_threadpool(epistemic_report, e))


async def lineage_route(request: Request):
    """Lineage of any result of the run (a comparison, a measurement); claims and the motion fit are in the epistemic report."""
    a = _app()
    e = a._inv(request.path_params["iid"])
    rid = request.query_params.get("result", "")
    rep = await run_in_threadpool(epistemic_report, e)
    if not any(n["id"] == rid for n in rep["graph"]["nodes"]):
        raise a.APIError(404, "no such result in this run's reasoning graph")
    return a._json(lineage.lineage(e["record"], a._view(e).manifest, rep["graph"], rid, reprox.environment()))


async def reproducex_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    return a._json(await run_in_threadpool(reprox.reproduce, e["record"], a._bundle_dirs().get(e["target_id"])))


async def simcheck_route(request: Request):
    a = _app()
    body = await a._body(request)
    sc = body.get("scenario")
    seeds = body.get("seeds")
    if seeds is not None and not (isinstance(seeds, list) and 1 <= len(seeds) <= simcheck.MAX_SEEDS and all(isinstance(s, int) and 0 <= s < 2 ** 31 for s in seeds)):
        raise a.APIError(400, f"seeds must be a list of 1–{simcheck.MAX_SEEDS} integers")
    errs = synthobs.validate(sc)
    if errs:
        raise a.APIError(400, "; ".join(errs))
    return a._json(await run_in_threadpool(simcheck.audit, sc, seeds))


async def integrity_route(request: Request):
    """Check a text the browser composed (notebook export, story, argument) against one investigation's facts."""
    a = _app()
    body = await a._body(request)
    text = body.get("text")
    if not isinstance(text, str) or len(text) > 200_000:
        raise a.APIError(400, "text must be a string of at most 200000 characters")
    e = a._inv(str(body.get("investigation_id") or ""))
    rep = await run_in_threadpool(epistemic_report, e)
    return a._json(integrity.check(text, rep["facts"]))


def specs() -> dict:
    return {"statuses": epi.STATUSES, "kinds": epi.KINDS, "status_rules": epi.STATUS_RULES, "compiler": {"stages": scicomp.STAGES, "outcomes": scicomp.OUTCOMES,
            "rule": scicomp.OUTCOME_RULE}, "boundary": {"regions": claims.REGIONS, "labels": claims.REGION_LABEL, "rules": claims.REGION_RULES},
            "stress": {"modes": claims.MODES, "results": claims.RESULTS}, "negative": {"categories": negspace.CATEGORIES, "distinctions": negspace.DISTINCTIONS},
            "blindspot": {"states": blindspot.STATES, "checks": blindspot.CHECKS}, "debugger": {"stages": scidebug.STAGES, "reader_stages": scidebug.READER_STAGES,
            "tolerance": scidebug.REL_EQUIV}, "reproduction": {"verdicts": reprox.VERDICTS}, "integrity": {"checks": integrity.CHECKS, "overstate": list(integrity.OVERSTATE),
            "prob_words": list(integrity.PROB_WORDS), "phrases": integrity.PHRASES, "units": list(integrity.UNITS), "dimless": list(integrity.DIMLESS)},
            "negators": list(epi.NEGATORS), "questions": decide.CATEGORIES, "next_rule": decide.ORDER_RULE, "review_perspectives": [(p[0], p[1]) for p in reviewx.PERSPECTIVES],
            "simcheck_max_seeds": simcheck.MAX_SEEDS,
            "methods": {"epistemic": epi.METHOD, "genome": mg.METHOD, "compiler": scicomp.METHOD, "debugger": scidebug.METHOD, "boundary": claims.METHOD_BOUNDARY,
                        "stress": claims.METHOD_STRESS, "negative": negspace.METHOD, "blindspot": blindspot.METHOD, "uflow": uflow.METHOD, "lineage": lineage.METHOD,
                        "models": modelarena.METHOD, "future": futurelab.METHOD, "next": decide.METHOD_NEXT, "questions": decide.METHOD_Q,
                        "integrity": integrity.METHOD, "review": reviewx.METHOD, "reproduction": reprox.METHOD, "simcheck": simcheck.METHOD}}


routes = [
    Route("/api/investigations/{iid}/epistemic", epistemic_route, methods=["GET"]),
    Route("/api/investigations/{iid}/reproduce-x", reproducex_route, methods=["POST"]),
    Route("/api/investigations/{iid}/lineage", lineage_route, methods=["GET"]),
    Route("/api/integrity", integrity_route, methods=["POST"]),
    Route("/api/simulation-audit", simcheck_route, methods=["POST"]),
]
