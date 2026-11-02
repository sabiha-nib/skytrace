"""Phase 9 API: the scientific intelligence layer.

One report per investigation (cached by content hash): the entity envelope of every object (SCI-ENTITY-1), discovery genomes
(DGENOME-1), the scientific adversary's challenge ledger (ADV-1), the integrity gate and research debt (GATE-1, DEBT-1), the
causality lab (CAUSAL-1), the observation oracle's context and example plans with evidence negotiation (ORACLE-1, EVNEG-1),
the instrumental reality check (INSTCHECK-1), the sensitivity fingerprint (FINGERPRINT-1), the uncertainty budget
(BUDGET-1), the what-if engine (WHATIF-1) and the reproduction manifest (REPRONET-1). The unknown-universe map (UNKNOWN-1)
is added per request because it reads the sibling runs of the same target.

One corpus over every investigation the server holds (runs in this process and saved records whose bundle exists): research
memory (MEMORY-1) and the multi-discovery network (MDNET-1), cached by the set of content hashes.

Everything is computed by deterministic modules from recorded investigations; no model is called. Session-dependent rules
(challenge statuses, the gate's session part, memory recall and failure warnings, oracle plans you edit, the hypothetical
visit, reproduction comparison, session entities, causal-proposal warnings) run in the browser in web/js/intelcore.js and are
parity-tested against these modules.
"""

from __future__ import annotations

import json

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from .. import (adversary, autonomy, budget, bundle as bmod, canon, causal, dgenome, discovery, entities as E, fingerprint, gate, instcheck, mdnet, memory,
                oracle, repronet, reprox, unknownmap, whatif)

_CACHE: dict[str, dict] = {}
_CORPUS: dict[str, dict] = {}
ORACLE_EXAMPLES = {"motion": [{"label": "one more visit a year after the last", "added_years_after_last": [1.0]},
                              {"label": "three more visits, one per year", "added_years_after_last": [1.0, 2.0, 3.0]},
                              {"label": "one visit at half the error, two years on", "added_years_after_last": [2.0], "error_factor": 0.5}],
                   "variability": [{"label": "1 % per-exposure precision", "fractional_error": 0.01},
                                   {"label": "0.5 % per-exposure precision", "fractional_error": 0.005}]}


def _app():
    from . import app as a
    return a


def _ctx(e: dict) -> dict:
    """The inputs every Phase 9 engine shares: the epistemic report, DISC-1 and the frontier report."""
    from . import epistemic as se, frontier as sf
    a = _app()
    v = a._view(e)
    return {"rep": se.epistemic_report(e), "disc": discovery.report(e["record"], v.discovery, v.manifest, a.availability()),
            "frontier": sf.frontier_report(e, None), "manifest": v.manifest}


def intelligence_report(e: dict) -> dict:
    rec = e["record"]
    key = rec["content_hash"]
    if key in _CACHE:
        return _CACHE[key]
    a = _app()
    c = _ctx(e)
    rep, disc, fr = c["rep"], c["disc"], c["frontier"]
    ents = E.investigation_entities(rec, rep["graph"], fr)
    led = adversary.ledger(rec, rep, fr, disc)
    lab = causal.lab(rec, disc)
    neg = oracle.negotiation(disc)
    inst = instcheck.check(rec, disc["hypotheses"])
    octx = oracle.context(rec)
    plans = {}
    for q, cands in ORACLE_EXAMPLES.items():
        spec = {"question": q, "candidates": cands}
        plans[q] = oracle.evaluate_ctx(octx, spec) if not oracle.validate_spec(spec) else None
    bdir = a._bundle_dirs().get(e["target_id"])
    man = repronet.manifest(rec, json.loads((bdir / "manifest.json").read_text()) if bdir else None, reprox.environment(),
                            seed=(rec.get("parameters") or {}).get("seed"),
                            limitations=[l for o in (x for ev in rec["events"] if ev["step"] == "assess" for x in ev["data"].get("outcomes", []))
                                         for l in (o.get("limitations") or [])])
    out = {"content_hash": key, "synthetic": rep["synthetic"], "target_id": e["target_id"],
           "entities": {"summary": E.summary(ents), "errors": E.validate(ents, E.resolver(rec, rep["graph"], fr)), "items": ents},
           "genomes": dgenome.genomes(rec, rep, disc["hypotheses"]), "adversary": led, "gate": gate.base(rec, rep, led), "debt": gate.debt(rec, rep, disc),
           "causal": lab, "oracle": {"context": {k: v for k, v in octx.items() if k != "validation"}, "validation": octx.get("validation"), "examples": plans,
                                     "threshold": oracle.THRESHOLD, "max_added": oracle.MAX_ADDED},
           "negotiation": neg, "instrumental": inst, "fingerprint": fingerprint.fingerprint(rec), "budget": budget.budget(rec, rep["uflow"]),
           "whatif": whatif.engine(rec, disc, inst, lab, neg), "reproduction": man}
    if len(_CACHE) > 32:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def corpus_entries() -> list[dict]:
    """Every investigation the server holds: runs in this process, then saved records whose bundle is available."""
    a = _app()
    seen, out = set(), []
    for iid, e in list(a.INVESTIGATIONS.items()):
        h = e["record"]["content_hash"]
        if h not in seen:
            seen.add(h)
            out.append({"iid": iid, "e": e, "origin": "run in this session", "saved": None})
    a.RECORDS.mkdir(parents=True, exist_ok=True)
    dirs = a._bundle_dirs()
    for p in sorted(a.RECORDS.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        rec, tid = d.get("investigation"), d.get("target_id")
        if not isinstance(rec, dict) or tid not in dirs or rec.get("content_hash") in seen:
            continue
        seen.add(rec["content_hash"])
        out.append({"iid": d.get("record_id"), "e": {"record": rec, "target_id": tid}, "origin": "saved record", "saved": {"name": d.get("name")}})
    return out


def corpus_from(entries: list[dict]) -> dict:
    key = canon.digest(sorted(x["e"]["record"]["content_hash"] for x in entries))
    if key in _CORPUS:
        return _CORPUS[key]
    items = []
    for x in entries:
        c = _ctx(x["e"])
        items.append({"iid": x["iid"], "record": x["e"]["record"], "epistemic": c["rep"], "hypotheses": c["disc"]["hypotheses"], "origin": x["origin"],
                      "saved": x.get("saved")})
    gen = {x["record"]["content_hash"]: {g["question"]: g for g in dgenome.genomes(x["record"], x["epistemic"], x["hypotheses"])} for x in items}
    steps = {x["record"]["content_hash"]: {ev["step"] for ev in x["record"]["events"]} for x in items}
    hs = sorted(gen)
    cmps = {}
    for i, ha in enumerate(hs):
        for hb in hs[i + 1:]:
            for q in dgenome.QUESTIONS:
                ga, gb = gen[ha].get(q), gen[hb].get(q)
                if ga and gb and ga.get("available") and gb.get("available"):
                    cmps[f"{ha[:16]}|{hb[:16]}|{q}"] = dgenome.compare(ga, gb, steps[hb], steps[ha])
    out = {"key": key, "memory": memory.build(items), "network": mdnet.build(items), "n": len(items), "genome_comparisons": cmps}
    if len(_CORPUS) > 8:
        _CORPUS.clear()
    _CORPUS[key] = out
    return out


def unknown_for(e: dict, entries: list[dict]) -> dict:
    c = _ctx(e)
    sib = [x["e"]["record"]["parameters"] for x in entries if x["e"]["target_id"] == e["target_id"]] or [e["record"]["parameters"]]
    env = None
    a = _app()
    p = a.ROOT / "data" / "environment_report.json"
    if p.exists():
        try:
            env = json.loads(p.read_text())
        except ValueError:
            env = None
    return unknownmap.build(e["record"], c["rep"], c["disc"], sib, env)


# ------------------------------------------------------------------ routes
async def intelligence_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])

    def work():
        r = intelligence_report(e)
        u = unknown_for(e, corpus_entries())
        return {**r, "unknown": u, "cycle": autonomy.propose(r, u)}
    return a._json(await run_in_threadpool(work))


async def corpus_route(request: Request):
    a = _app()
    return a._json(await run_in_threadpool(lambda: corpus_from(corpus_entries())))


async def oracle_route(request: Request):
    a = _app()
    body = await a._body(request)
    e = a._inv(str(body.get("investigation_id") or ""))
    spec = body.get("spec")
    errs = oracle.validate_spec(spec)
    if errs:
        raise a.APIError(400, "; ".join(errs))
    return a._json(await run_in_threadpool(oracle.evaluate, e["record"], spec))


async def visit_route(request: Request):
    a = _app()
    body = await a._body(request)
    e = a._inv(str(body.get("investigation_id") or ""))
    dt, pos, k = body.get("dt_years", 1.0), body.get("position", "static"), body.get("error_factor", 1.0)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (dt, k)) or not isinstance(pos, str):
        raise a.APIError(400, "dt_years and error_factor must be numbers; position 'static' or 'track'")
    r = whatif.hypothetical_visit(whatif.motion_context(e["record"]), float(dt), pos, float(k))
    if not r.get("available"):
        raise a.APIError(400, r["why"])
    return a._json(r)


async def manifest_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    m = (await run_in_threadpool(intelligence_report, e))["reproduction"]
    return Response(canon.dumps(m), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="skytrace-reproduction-{m["record"][:12]}.json"'})


async def compare_route(request: Request):
    a = _app()
    body = await a._body(request)
    ma, mb = body.get("a"), body.get("b")
    for name, m in (("a", ma), ("b", mb)):
        errs = repronet.validate(m)
        if errs:
            raise a.APIError(400, f"manifest {name}: " + "; ".join(errs))
    return a._json(repronet.compare(ma, mb))


def specs() -> dict:
    return {"entity": {"types": E.TYPES, "statuses": E.STATUSES, "rules": E.RULES, "sources": E.SOURCES},
            "memory": {"statuses": memory.STATUSES, "rules": memory.STATUS_RULES, "kinds": memory.KINDS,
                       "concepts": {k: {"label": v[0], "terms": v[1]} for k, v in memory.CONCEPTS.items()}},
            "genome": {"fields": dgenome.FIELDS, "baseline_factor": dgenome.BASELINE_FACTOR},
            "unknown": {"regions": unknownmap.REGIONS, "rules": unknownmap.RULES},
            "adversary": {"questions": adversary.QUESTIONS, "statuses": adversary.STATUSES},
            "gate": {"requirements": gate.REQUIREMENTS, "states": gate.STATES, "good_repro": list(gate.GOOD_REPRO)},
            "causal": {"criteria": causal.CRITERIA, "causal_words": list(causal.CAUSAL_WORDS)},
            "network": {"rules": {k: {"name": v[0], "limitation": v[1]} for k, v in mdnet.RULES.items()}},
            "reproduction": {"schema": repronet.SCHEMA, "classes": repronet.CLASSES, "required": repronet.REQUIRED, "rel": repronet.REL},
            "whatif": {"questions": whatif.QUESTIONS, "kinds": whatif.KINDS, "detect": whatif.DETECT},
            "fingerprint": {"dimensions": fingerprint.DIMENSIONS, "states": fingerprint.STATES},
            "instrumental": {"states": instcheck.STATES}, "budget": {"classes": budget.CLASSES},
            "oracle": {"threshold": oracle.THRESHOLD, "max_added": oracle.MAX_ADDED},
            "methods": {"entity": E.METHOD, "memory": memory.METHOD, "genome": dgenome.METHOD, "unknown": unknownmap.METHOD, "adversary": adversary.METHOD,
                        "gate": gate.METHOD, "debt": gate.METHOD_DEBT, "causal": causal.METHOD, "oracle": oracle.METHOD, "negotiation": oracle.METHOD_NEG,
                        "network": mdnet.METHOD, "reproduction": repronet.METHOD, "whatif": whatif.METHOD, "fingerprint": fingerprint.METHOD,
                        "instrumental": instcheck.METHOD, "budget": budget.METHOD, "cycle": autonomy.METHOD}}


_ = bmod  # bundles are reached through app._bundle_dirs

routes = [
    Route("/api/investigations/{iid}/intelligence", intelligence_route, methods=["GET"]),
    Route("/api/investigations/{iid}/reproduction-manifest", manifest_route, methods=["GET"]),
    Route("/api/intelligence/corpus", corpus_route, methods=["GET"]),
    Route("/api/oracle", oracle_route, methods=["POST"]),
    Route("/api/whatif/visit", visit_route, methods=["POST"]),
    Route("/api/reproduction/compare", compare_route, methods=["POST"]),
]
