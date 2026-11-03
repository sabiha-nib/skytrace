"""Phase 10 API: the signature systems of src/skytrace/universal.py and the signal workbench (SIGNAL-1), one report per
investigation, cached by content hash. Readers of recorded results: no network, no model calls, no probabilities."""

from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.routing import Route

from .. import universal

_CACHE: dict[str, dict] = {}


def _app():
    from . import app as a
    return a


def universal_report(e: dict) -> dict:
    from . import intelligence as si, research as sr
    rec = e["record"]
    entries = si.corpus_entries()
    sib = [x["e"]["record"]["content_hash"] for x in entries if x["e"]["target_id"] == e["target_id"]]
    key = rec["content_hash"] + "|" + ",".join(sorted(sib))
    if key in _CACHE:
        return _CACHE[key]
    a = _app()
    c = si._ctx(e)
    radar = sr.research_report(e)["radar"]
    other = set()
    for x in entries:
        if x["e"]["target_id"] == e["target_id"]:
            continue
        try:
            other |= {i.get("signal") for i in sr.research_report(x["e"])["radar"].get("items") or []}
        except (KeyError, OSError):
            continue
    out = universal.report(rec, c["disc"]["hypotheses"], c["rep"]["negative"], c["rep"]["compile"], radar, a.availability()["network"], sib, other)
    if len(_CACHE) > 32:
        _CACHE.clear()
    _CACHE[key] = out
    return out


async def universal_route(request: Request):
    a = _app()
    e = a._inv(request.path_params["iid"])
    return a._json(await run_in_threadpool(universal_report, e))


routes = [Route("/api/investigations/{iid}/universal", universal_route, methods=["GET"])]
