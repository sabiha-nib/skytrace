"""Archive connectors (ACQ-2): one registry of the external services, with validated request previews.

Each connector states its service identity, documented endpoint, query parameters (SCHEMA-1), request lifecycle
(timeouts, retries, back-off, Retry-After), response validation, provenance and integrity handling, and its current
availability from the last environment diagnosis (`data/environment_report.json`) — never a live probe from the page.

`preview(connector, params)` validates the parameters and returns the exact request acquisition would send. It does
this by calling the real query builders (`archive/spherex.py`, `archive/references.py`) with a recording fetcher that
captures the request and stops before anything is sent, so the preview cannot drift from what acquisition does.
A preview is not a search: nothing is contacted, and the result says so.
"""

from __future__ import annotations

import json
from pathlib import Path

from .archive import net, references, spherex
from .schema import NUM, O, S, check

METHOD = "ACQ-2"


class _Captured(Exception):
    pass


class _Recorder:
    """A fetcher stand-in that records the request and stops before sending it."""

    def __init__(self):
        self.request = None

    def get(self, url, params=None, **kw):
        self.request = {"method": "GET", "url": url, "params": dict(params or {}), "full_url": net.full_url(url, params),
                        "source": kw.get("source"), "kind": kw.get("kind"), "release": kw.get("release", ""),
                        "dataset_id": kw.get("dataset_id", ""), "validation": getattr(kw.get("validate"), "__name__", None)}
        raise _Captured()


RADEC = {"ra": (NUM(0, 360), True), "dec": (NUM(-90, 90), True)}
CONNECTORS = [
    {"id": "spherex_sia", "service": "IRSA SIA (SPHEREx)", "endpoint": spherex.SIA_URL, "documented_by": "IRSA SPHEREx SIA2 interface (spherex.py)",
     "params": O({**RADEC, "release": (S(enum=["QR3", "QR2"]), True), "radius_arcsec": (NUM(0.1, 60), True)}),
     "build": lambda f, p: spherex.discover_sia(f, p["ra"], p["dec"], p["release"], p["radius_arcsec"] / 3600.0),
     "response": "VOTable, parsed and validated (validate_votable)", "provides": "SPHEREx spectral-image records covering the position"},
    {"id": "spherex_tap", "service": "IRSA TAP", "endpoint": spherex.TAP_URL, "documented_by": "IRSA TAP, tables spherex.plane / spherex.artifact",
     "params": O(RADEC), "build": lambda f, p: spherex.discover_tap(f, p["ra"], p["dec"]),
     "response": "CSV, validated (validate_csv)", "provides": "cross-check of the SIA discovery"},
    {"id": "simbad_resolve", "service": "SIMBAD TAP", "endpoint": references.SIMBAD_TAP, "documented_by": "SIMBAD TAP (basic + ident tables)",
     "params": O({"identifier": (S(80, 1, r"^[A-Za-z0-9 +._*'-]{1,80}$"), True)}),
     "build": lambda f, p: references.resolve_simbad(f, p["identifier"]),
     "response": "CSV, validated; exactly one object required", "provides": "identity, position, proper motion and parallax"},
    {"id": "gaia_cone", "service": "Gaia archive TAP", "endpoint": references.GAIA_TAP, "documented_by": "ESA Gaia archive TAP, gaiadr3.gaia_source",
     "params": O({**RADEC, "radius_deg": (NUM(0.001, 0.2), True), "g_min": (NUM(3, 21), True), "g_max": (NUM(3, 21), True)}),
     "build": lambda f, p: references.gaia_cone(f, p["ra"], p["dec"], p["radius_deg"], p["g_min"], p["g_max"]),
     "response": "CSV, validated", "provides": "reference stars for plate solutions"},
]
BY_ID = {c["id"]: c for c in CONNECTORS}
LIFECYCLE = {"timeouts_s": {"connect": 10.0, "read": 120.0}, "retries": 3, "backoff": "2 s × 2^attempt",
             "transient_status": sorted(net.TRANSIENT_STATUS), "retry_after": f"honoured, at most {net.MAX_RETRY_AFTER_S:g} s",
             "max_bytes": net.DEFAULT_MAX_BYTES, "proxy_refusal": "recorded and never retried or routed around",
             "offline": "OFFLINE=1 opens no socket: cache, then fixture, then a clear error",
             "provenance": "every response is stored with source, URL, retrieval time, origin (live/cache/fixture), release, dataset DOI and SHA-256",
             "integrity": "cached entries whose SHA-256 no longer matches are ignored; bundle files are checked against the manifest"}


def availability(report_path: Path) -> dict:
    """{service: verdict} from the last environment diagnosis, with its date; None when never diagnosed."""
    try:
        rep = json.loads(Path(report_path).read_text())
    except (OSError, ValueError):
        return {"diagnosed_at": None, "services": {}}
    return {"diagnosed_at": rep.get("run_at"),
            "services": {s["service"]: s["verdict"] for s in rep.get("services", [])}}


def registry(report_path: Path, offline: bool) -> dict:
    av = availability(report_path)
    out = []
    for c in CONNECTORS:
        verdict = av["services"].get(c["service"])
        usable = (not offline) and verdict is not None and (verdict == "ok" or str(verdict).startswith("http_2"))
        out.append({k: v for k, v in c.items() if k != "build"} | {"last_verdict": verdict, "usable_now": usable,
                    "usable_note": "OFFLINE=1" if offline else ("never diagnosed" if verdict is None else ("reachable at the last diagnosis" if usable else f"blocked at the last diagnosis: {verdict}"))})
    return {"method": METHOD, "connectors": out, "lifecycle": LIFECYCLE, "diagnosed_at": av["diagnosed_at"], "offline": offline}


def preview(cid: str, params: dict) -> dict:
    c = BY_ID.get(cid)
    if c is None:
        return {"ok": False, "errors": [f"unknown connector {cid!r}"]}
    errs = check(c["params"], params)
    if not errs and cid == "gaia_cone" and params["g_min"] >= params["g_max"]:
        errs = ["$.g_min: must be smaller than g_max"]
    if errs:
        return {"ok": False, "errors": errs}
    rec = _Recorder()
    try:
        c["build"](rec, params)
    except _Captured:
        pass
    return {"ok": True, "connector": cid, "service": c["service"], "request": rec.request, "sent": False,
            "note": "validated request preview: nothing was sent. Sending it is acquisition (scripts/acquire_targets.py), which needs network access."}
