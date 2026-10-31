"""SKYTRACE HTTP API and static frontend (Starlette).

The server reads only verified bundles from disk and runs the deterministic
analysis; it never contacts the archives. The only outbound call it can make is
the copilot's Meta Model API request, which OFFLINE=1 disables.

Run:  python -m skytrace serve   (or: uvicorn skytrace.server.app:app)
"""

from __future__ import annotations

import base64
import json
import os
import platform
import re
import uuid
from functools import lru_cache
from pathlib import Path

import numpy as np
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .. import __version__, analysis, bundle as bmod
from ..ai import copilot
from ..ai.meta_client import MetaConfig
from ..archive.net import offline_enabled
from ..archive.products import ProductError, astropy_available, load_product
from ..provenance import stable_hash, utc_now_iso
from ..report import render_markdown
from ..science import flags as fl
from ..science.coords import mjd_to_jyear, propagate
from ..view import InvestigationView, evidence_graph

ROOT = bmod.ROOT
WEB = ROOT / "web"
RECORDS = Path(os.environ.get("SKYTRACE_RECORDS_DIR") or ROOT / "data" / "records")
TARGETS_CFG = ROOT / "config" / "targets.json"
_SAFE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_KEY = re.compile(r"^[A-Za-z0-9_:.\-]{3,96}$")

INVESTIGATIONS: dict[str, dict] = {}          # investigation_id -> {"record", "target_id"}


class APIError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def _json(obj, status=200):
    return JSONResponse(json.loads(json.dumps(obj, default=_default)), status_code=status)


def _default(o):
    if isinstance(o, (np.floating,)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def _bundle_dirs() -> dict[str, Path]:
    return {p.name: p for p in bmod.find_bundles()}


@lru_cache(maxsize=32)
def _verify_cached(path: str, mtime: float) -> dict:
    return bmod.verify(Path(path))


def _verify(p: Path) -> dict:
    return _verify_cached(str(p), (p / "manifest.json").stat().st_mtime)


def _bundle(tid: str) -> bmod.Bundle:
    if not _SAFE.match(tid):
        raise APIError(400, "invalid target id")
    d = _bundle_dirs().get(tid)
    if d is None:
        raise APIError(404, f"no data bundle for {tid}; acquire it with: python scripts/acquire_targets.py --target {tid}")
    v = _verify(d)
    if not v["ok"]:
        raise APIError(409, "bundle failed verification: " + "; ".join(v["problems"][:5]))
    return bmod.load(d)


def _inv(iid: str) -> dict:
    if not _SAFE.match(iid) or iid not in INVESTIGATIONS:
        raise APIError(404, "unknown investigation; run the analysis again")
    return INVESTIGATIONS[iid]


def _view(entry: dict) -> InvestigationView:
    b = bmod.load(_bundle_dirs()[entry["target_id"]])
    return InvestigationView(entry["record"], b.discovery, b.manifest, b.inspection)


# ------------------------------------------------------------------ status & targets
async def status(request: Request):
    cfg = MetaConfig.from_env()
    smoke = ROOT / "data" / "meta_smoke_test.json"
    smoke_d = json.loads(smoke.read_text()) if smoke.exists() else None
    return _json({
        "version": __version__, "offline": offline_enabled(), "python": platform.python_version(),
        "numpy": np.__version__, "astropy": astropy_available(),
        "fits_reader": "astropy" if astropy_available() else "native (astropy not installed)",
        "meta": {"configured": bool(cfg.api_key) and not offline_enabled(), "key_present": bool(cfg.api_key),
                 "model": cfg.model, "base_url": cfg.base_url,
                 "smoke_test": {"run_at": smoke_d["run_at"], "all_passed": all(r["ok"] for r in smoke_d["results"])} if smoke_d else None},
        "bundles": [{k: v for k, v in _verify(p).items() if k != "bundle"} for p in _bundle_dirs().values()],
        "time": utc_now_iso()})


async def targets(request: Request):
    cfg = json.loads(TARGETS_CFG.read_text())["targets"]
    dirs = _bundle_dirs()
    out = []

    def summary(tid, b, v):
        obs = b.observations()
        t = [o["t_mid_mjd"] for o in obs if o.get("t_mid_mjd")]
        return {"kind": b.kind, "verified": v["ok"], "problems": v["problems"][:3], "n_observations": len(b.all_observations()),
                "n_included": len(obs), "detectors": sorted({o["detector"] for o in obs}),
                "time_span_iso": [min(obs, key=lambda o: o["t_mid_mjd"])["t_mid_iso"], max(obs, key=lambda o: o["t_mid_mjd"])["t_mid_iso"]] if t else None,
                "total_bytes": b.manifest.get("total_bytes"), "astrometry": b.target.get("astrometry"),
                "identity": b.target.get("identity")}

    for c in cfg:
        item = {"target_id": c["target_id"], "name": c["name"], "role": c.get("role"), "real_target": True, "hint": c.get("hint"),
                "supplied_coords": c.get("supplied_coords"),
                "acquire_command": f"python scripts/acquire_targets.py --target {c['target_id']}"}
        if c["target_id"] in dirs:
            b = bmod.load(dirs[c["target_id"]])
            item.update(summary(c["target_id"], b, _verify(dirs[c["target_id"]])))
        else:
            item.update({"kind": None, "verified": False, "n_observations": 0, "n_included": 0})
        out.append(item)
    known = {c["target_id"] for c in cfg}
    for tid, d in dirs.items():
        if tid in known:
            continue
        b = bmod.load(d)
        out.append({"target_id": tid, "name": b.target.get("name", tid), "role": b.target.get("role"), "real_target": False,
                    **summary(tid, b, _verify(d))})
    return _json({"targets": out})


async def target_detail(request: Request):
    b = _bundle(request.path_params["tid"])
    return _json({"target": b.target, "kind": b.kind, "observations": b.all_observations(),
                  "selection": b.discovery.get("selection"), "search": b.discovery.get("search"),
                  "references": {"catalogue": b.references.get("catalogue"), "n": len(b.references.get("stars", [])),
                                 "stars": [{"source_id": r.get("source_id"), "ra": r.get("ra"), "dec": r.get("dec")}
                                           for r in b.references.get("stars", [])[:200]]},
                  "manifest": {k: b.manifest[k] for k in ("schema", "kind", "created_at", "generator", "notes", "total_bytes")},
                  "verification": _verify(b.path), "inspection": b.inspection})


# ------------------------------------------------------------------ images
def _b64(a: np.ndarray, dtype) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=dtype).tobytes()).decode()


def _image_payload(prod, obs, b, extra=None) -> dict:
    img = prod.image
    finite = img[np.isfinite(img)]
    pct = {str(p): float(np.percentile(finite, p)) for p in (0.5, 1, 5, 25, 50, 75, 95, 99, 99.5, 99.9)} if finite.size else {}
    fmap = fl.resolve_bits(prod.headers.get("FLAGS"))
    reject = fmap.mask(prod.flags, fl.REJECT)
    ast = analysis.target_astrometry(b)
    tra, tdec = propagate(ast, float(mjd_to_jyear(obs["t_mid_mjd"]))) if obs.get("t_mid_mjd") else (ast.ra, ast.dec)
    px, py = prod.sky_to_pixel(tra, tdec)
    ny, nx = img.shape
    cx, cy = (nx - 1) / 2, (ny - 1) / 2
    ra0, dec0 = prod.pixel_to_sky(cx, cy)
    rax, decx = prod.pixel_to_sky(cx + 1, cy)
    ray, decy = prod.pixel_to_sky(cx, cy + 1)
    cosd = np.cos(np.radians(dec0))
    cd = [[(rax - ra0) * cosd, (ray - ra0) * cosd], [decx - dec0, decy - dec0]]  # deg per pixel, local
    try:
        wl, bw = prod.wavelength_at(px, py)
    except ProductError:
        wl = bw = None
    fe = b.file_entry(obs["file"])
    return {"key": obs["key"], "width": nx, "height": ny, "data": _b64(np.nan_to_num(img, nan=np.nan), "<f4"),
            "reject_mask": _b64(reject.astype(np.uint8), "u1"), "percentiles": pct, "bunit": prod.headers["IMAGE"].get("BUNIT"),
            "synthetic": prod.is_synthetic() or b.kind == "synthetic", "reader": prod.reader,
            "predicted_target_xy": [px, py], "predicted_target_radec": [tra, tdec], "wavelength_at_target_um": wl, "bandwidth_at_target_um": bw,
            "linear_wcs": {"center_xy": [cx, cy], "center_radec": [ra0, dec0], "cd_deg": cd,
                           "note": "local linear approximation for the cursor readout; measurements use the full WCS"},
            "pixel_scale_arcsec": list(prod.pixel_scale_arcsec()), "observation": obs,
            "file": {"path": obs["file"], "sha256": fe["sha256"] if fe else None, "provenance": (fe or {}).get("provenance")},
            "flag_bits": {"origin": fmap.origin, "reject_names_resolved": [n for n in fl.REJECT if n in fmap.bits]},
            **(extra or {})}


async def observation_image(request: Request):
    b = _bundle(request.path_params["tid"])
    key = request.path_params["key"]
    if not _KEY.match(key):
        raise APIError(400, "invalid observation key")
    try:
        obs = b.observation(key)
    except KeyError:
        raise APIError(404, f"unknown observation {key}")
    if not obs.get("file"):
        raise APIError(404, f"{key} has no stored image ({obs.get('exclusion_reason', 'excluded')})")
    prod = await run_in_threadpool(load_product, b.path / obs["file"])
    return _json(_image_payload(prod, obs, b))


def _affine(coeffs):
    a0, a1, a2, b0, b1, b2 = coeffs
    M = np.array([[a1, a2], [b1, b2]])
    return np.array([a0, b0]), M


async def pair_image(request: Request):
    """Image B resampled onto image A's pixel grid, for display only."""
    from scipy.ndimage import map_coordinates
    tid = request.path_params["tid"]
    b = _bundle(tid)
    ka, kb, iid = request.query_params.get("a", ""), request.query_params.get("b", ""), request.query_params.get("inv", "")
    if not (_KEY.match(ka) and _KEY.match(kb)):
        raise APIError(400, "invalid observation keys")
    try:
        oa, ob = b.observation(ka), b.observation(kb)
    except KeyError as e:
        raise APIError(404, f"unknown observation {e}")
    pa, pb = await run_in_threadpool(load_product, b.path / oa["file"]), await run_in_threadpool(load_product, b.path / ob["file"])
    ny, nx = pa.image.shape
    yy, xx = np.indices((ny, nx), dtype=float)
    method, comparison = "header WCS (pixel -> sky -> pixel)", None
    entry = INVESTIGATIONS.get(iid) if _SAFE.match(iid or "x") else None
    if entry:
        v = _view(entry)
        comparison = v.pair_comparison(ka, kb)
        ma, mb = v.measurements.get(ka), v.measurements.get(kb)
        if ma and mb and (ma.get("plate") or {}).get("coeffs_deg") and (mb.get("plate") or {}).get("coeffs_deg"):
            ta, Ma = _affine(ma["plate"]["coeffs_deg"])
            tb, Mb = _affine(mb["plate"]["coeffs_deg"])
            xi = ta[0] + Ma[0, 0] * xx + Ma[0, 1] * yy
            eta = ta[1] + Ma[1, 0] * xx + Ma[1, 1] * yy
            inv = np.linalg.inv(Mb)
            bx = inv[0, 0] * (xi - tb[0]) + inv[0, 1] * (eta - tb[1])
            by = inv[1, 0] * (xi - tb[0]) + inv[1, 1] * (eta - tb[1])
            method = "per-exposure Gaia-referenced plate solutions (affine, DIFFAST-1)"
        else:
            entry = None
    if not entry:
        ra, dec = (pa._celestial().all_pix2world(np.column_stack([xx.ravel(), yy.ravel()]), 0).T if pa.reader == "astropy"
                   else pa._celestial().pixel_to_world(xx.ravel(), yy.ravel()))
        if pb.reader == "astropy":
            bx, by = pb._celestial().all_world2pix(np.column_stack([ra, dec]), 0).T
        else:
            bx, by = pb._celestial().world_to_pixel(ra, dec)
        bx, by = np.asarray(bx).reshape(ny, nx), np.asarray(by).reshape(ny, nx)
    resampled = map_coordinates(pb.image, [by, bx], order=1, cval=np.nan, mode="constant")
    pa_payload = _image_payload(pa, oa, b)
    pb_payload = _image_payload(pb, ob, b)
    pb_payload["data"] = _b64(resampled, "<f4")
    pb_payload["resampled_onto"] = ka
    # B's catalogue position at B's epoch, drawn in A's pixel frame (A's WCS)
    ast = analysis.target_astrometry(b)
    pb_payload["predicted_target_xy"] = list(pa.sky_to_pixel(*propagate(ast, float(mjd_to_jyear(ob["t_mid_mjd"])))))
    pb_payload["centroid_in_a"] = None
    if entry:
        mb = v.measurements.get(kb) or {}
        cb = mb.get("centroid") or {}
        if cb.get("converged"):
            xi = tb[0] + Mb[0, 0] * cb["x"] + Mb[0, 1] * cb["y"]
            eta = tb[1] + Mb[1, 0] * cb["x"] + Mb[1, 1] * cb["y"]
            ia = np.linalg.inv(Ma)
            pb_payload["centroid_in_a"] = [float(ia[0, 0] * (xi - ta[0]) + ia[0, 1] * (eta - ta[1])),
                                           float(ia[1, 0] * (xi - ta[0]) + ia[1, 1] * (eta - ta[1]))]
    return _json({"a": pa_payload, "b": pb_payload, "registration": method,
                  "note": "B is resampled onto A's pixel grid by bilinear interpolation for display only; "
                          "all measurements use the original pixels.", "comparison": comparison})


# ------------------------------------------------------------------ analysis
def _store(target_id: str, record: dict) -> str:
    iid = record["content_hash"][:16]
    INVESTIGATIONS[iid] = {"record": record, "target_id": target_id}
    return iid


def _summary(iid: str, entry: dict) -> dict:
    v = _view(entry)
    return {"investigation_id": iid, "target_id": entry["target_id"], "record": entry["record"],
            "graph_counts": evidence_graph(v, entry["target_id"])["counts"], "synthetic": v.is_synthetic()}


def _clean_params(params: dict) -> dict:
    allowed = analysis.PARAM_BOUNDS
    booleans = set(analysis.PARAM_BOOLEANS)
    clean = {}
    for k, v in params.items():
        if k in booleans:
            if not isinstance(v, bool):
                raise APIError(400, f"{k} must be true or false")
            clean[k] = v
            continue
        if k == "detectors":
            if not (isinstance(v, list) and v and all(isinstance(d, int) and 1 <= d <= 6 for d in v)):
                raise APIError(400, "detectors must be a non-empty list of integers 1-6")
            clean[k] = sorted(set(v))
            continue
        if k not in allowed:
            raise APIError(400, f"unknown parameter {k}")
        lo, hi = allowed[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise APIError(400, f"{k} must be between {lo} and {hi}")
        clean[k] = int(v) if k == "fit_half_size_px" else float(v)
    return clean


async def analyze(request: Request):
    tid = request.path_params["tid"]
    b = _bundle(tid)
    body = await _body(request)
    clean = _clean_params(body.get("params") or {})
    record = (await run_in_threadpool(analysis.run, b, clean)).to_dict()
    iid = _store(tid, record)
    return _json(_summary(iid, INVESTIGATIONS[iid]))


async def stability_check(request: Request):
    """STAB-1: re-run the analysis under the fixed perturbation set and report outcome changes."""
    from .. import stability
    tid = request.path_params["tid"]
    b = _bundle(tid)
    body = await _body(request)
    clean = _clean_params(body.get("params") or {})
    return _json(await run_in_threadpool(stability.run, b, clean))


async def investigation(request: Request):
    iid = request.path_params["iid"]
    return _json(_summary(iid, _inv(iid)))


async def graph(request: Request):
    e = _inv(request.path_params["iid"])
    return _json(evidence_graph(_view(e), e["target_id"]))


def _report_md(e: dict) -> str:
    from ..report import Event, Investigation
    rec = e["record"]
    inv = Investigation(rec["target"], rec["parameters"])
    inv.events = [Event(**{k: ev[k] for k in ("step", "status", "detail", "data", "provenance")}) for ev in rec["events"]]
    inv.created_at = rec["created_at"]
    return render_markdown(inv)


def availability() -> dict:
    """What this server can reach: archives from the last environment diagnosis (None = never diagnosed)."""
    net = None
    if offline_enabled():
        net = False
    else:
        rep = ROOT / "data" / "environment_report.json"
        if rep.exists():
            try:
                sv = {s["service"]: s["verdict"] for s in json.loads(rep.read_text()).get("services", [])}
                irsa = [v for k, v in sv.items() if k.startswith("IRSA")]
                net = bool(irsa) and all(v == "ok" or v.startswith("http_2") for v in irsa)
            except (ValueError, KeyError):
                net = None
    return {"server": True, "network": net}


def _discovery(e: dict) -> dict:
    from .. import discovery
    b = bmod.load(_bundle_dirs()[e["target_id"]])
    return discovery.report(e["record"], b.discovery, b.manifest, availability())


async def capabilities_list(request: Request):
    from .. import capabilities
    return _json(capabilities.registry(availability()))


async def investigation_discovery(request: Request):
    e = _inv(request.path_params["iid"])
    return _json(await run_in_threadpool(_discovery, e))


async def investigation_package(request: Request):
    """PKG-1 reproducibility package (zip)."""
    from .. import capabilities, package
    iid = request.path_params["iid"]
    e = _inv(iid)
    b = bmod.load(_bundle_dirs()[e["target_id"]])
    rec_text = json.dumps(e["record"], indent=1, default=_default)
    data = await run_in_threadpool(package.build, rec_text, e["record"], _report_md(e), _discovery(e),
                                   evidence_graph(_view(e), e["target_id"]), capabilities.registry(availability()),
                                   b.manifest, __version__)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="skytrace-{e["target_id"]}-{iid}-package.zip"'})


async def report(request: Request):
    e = _inv(request.path_params["iid"])
    md = _report_md(e)
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="skytrace-{e["target_id"]}-{request.path_params["iid"]}.md"'})


async def ask(request: Request):
    e = _inv(request.path_params["iid"])
    body = await _body(request)
    q = body.get("question")
    if not isinstance(q, str) or not q.strip():
        raise APIError(400, "question is required")
    hist = body.get("history") if isinstance(body.get("history"), list) else []
    res = await run_in_threadpool(lambda: copilot.ask(q[:2000], _view(e), e["target_id"], hist, availability=availability()))
    return _json(res.to_dict())


# ------------------------------------------------------------------ records
def _record_path(rid: str) -> Path:
    if not _SAFE.match(rid):
        raise APIError(400, "invalid record id")
    return RECORDS / f"{rid}.json"


async def records_list(request: Request):
    RECORDS.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(RECORDS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        d = json.loads(p.read_text())
        out.append({k: d.get(k) for k in ("record_id", "name", "target_id", "saved_at", "content_hash", "bundle_kind", "notes",
                                          "last_replay", "imported", "tags", "outcomes", "modified_at", "analysis_version")})
    return _json({"records": out})


async def records_save(request: Request):
    body = await _body(request)
    e = _inv(str(body.get("investigation_id", "")))
    return _json(_save_record(e["target_id"], e["record"], body))


def _save_record(target_id: str, rec: dict, body: dict, imported: bool = False) -> dict:
    name = str(body.get("name") or "").strip()[:120] or f"{rec['target']} investigation"
    rid = uuid.uuid4().hex[:12]
    e = {"target_id": target_id}
    d = {"schema": "skytrace.saved_investigation/1", "record_id": rid, "name": name, "notes": str(body.get("notes") or "")[:2000],
         "target_id": e["target_id"], "saved_at": utc_now_iso(), "parameters": rec["parameters"],
         "bundle_kind": rec["parameters"].get("bundle_kind"), "bundle_manifest_sha256": rec["parameters"].get("bundle_manifest_sha256"),
         "analysis_version": rec["parameters"].get("analysis_version"), "software": rec.get("software"),
         "content_hash": rec["content_hash"], "investigation": rec,
         "copilot_transcript": body.get("transcript") if isinstance(body.get("transcript"), list) else [],
         "imported": imported, "tags": _clean_tags(body.get("tags")), "context": _clean_context(body.get("context")),
         "outcomes": _outcomes_summary(rec)}
    RECORDS.mkdir(parents=True, exist_ok=True)
    _record_path(rid).write_text(json.dumps(d, indent=1, default=_default))
    return {"record_id": rid, "name": name, "saved_at": d["saved_at"]}


def _clean_tags(tags) -> list[str]:
    if not isinstance(tags, list):
        return []
    return sorted({str(t).strip()[:40] for t in tags if isinstance(t, str) and str(t).strip()})[:20]


def _clean_context(ctx) -> dict:
    """User-written investigation context (question, own hypotheses, notes). Stored as given, size-bounded; never trusted
    as evidence: hypotheses can only cite recorded tests by id."""
    if not isinstance(ctx, dict):
        return {}
    text = json.dumps(ctx, default=str)
    if len(text) > 50_000:
        raise APIError(413, "investigation context is larger than 50 kB")
    return json.loads(text)


def _outcomes_summary(rec: dict) -> list[dict]:
    ev = next((e for e in rec.get("events", []) if e.get("step") == "assess"), None)
    return [{"question": o["question"], "category": o["category"]} for o in ((ev or {}).get("data") or {}).get("outcomes", [])]


async def records_update(request: Request):
    """Rename, retag or edit the notes/context of a saved record. The investigation itself is never changed."""
    p = _record_path(request.path_params["rid"])
    if not p.exists():
        raise APIError(404, "unknown record")
    body = await _body(request)
    d = json.loads(p.read_text())
    if "name" in body:
        name = str(body["name"] or "").strip()[:120]
        if not name:
            raise APIError(400, "name must not be empty")
        d["name"] = name
    if "notes" in body:
        d["notes"] = str(body["notes"] or "")[:2000]
    if "tags" in body:
        d["tags"] = _clean_tags(body["tags"])
    if "context" in body:
        d["context"] = _clean_context(body["context"])
    d["modified_at"] = utc_now_iso()
    p.write_text(json.dumps(d, indent=1, default=_default))
    return _json({k: d.get(k) for k in ("record_id", "name", "notes", "tags", "modified_at")})


async def records_clone(request: Request):
    p = _record_path(request.path_params["rid"])
    if not p.exists():
        raise APIError(404, "unknown record")
    d = json.loads(p.read_text())
    body = {"name": f"Copy of {d['name']}"[:120], "notes": d.get("notes", ""), "transcript": d.get("copilot_transcript", []),
            "tags": d.get("tags", []), "context": d.get("context", {})}
    out = _save_record(d["target_id"], d["investigation"], body)
    return _json({**out, "cloned_from": d["record_id"]})


def record_hash_ok(rec: dict) -> bool:
    """The content hash recomputes from the record body (same rule as report.Investigation.to_dict)."""
    body = {k: v for k, v in rec.items() if k not in ("created_at", "software", "content_hash")}
    return isinstance(rec.get("content_hash"), str) and stable_hash(body) == rec["content_hash"]


async def investigation_export(request: Request):
    """The investigation record exactly as the server holds it (JSON), for archiving or re-import."""
    iid = request.path_params["iid"]
    e = _inv(iid)
    return Response(json.dumps(e["record"], indent=1, default=_default), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="skytrace-{e["target_id"]}-{iid}.json"'})


async def records_import(request: Request):
    """Store an exported investigation record after checking its integrity. Nothing in it is trusted otherwise:
    the content hash must recompute, and its bundle must exist here (replay then re-executes it)."""
    body = await _body(request)
    rec = body.get("record")
    need = ("schema", "target", "parameters", "events", "content_hash")
    if not isinstance(rec, dict) or any(k not in rec for k in need) or not isinstance(rec["events"], list):
        raise APIError(400, "not a Skytrace investigation record (missing " +
                       ", ".join(k for k in need if not isinstance(rec, dict) or k not in rec) + ")")
    if not record_hash_ok(rec):
        raise APIError(400, "content hash does not match the record: it was modified or is incomplete")
    tid = str(rec["parameters"].get("bundle") or "")
    if tid not in _bundle_dirs():
        raise APIError(400, f"the data bundle {tid!r} for this record is not available on this machine")
    out = _save_record(tid, rec, body, imported=True)
    same = rec["parameters"].get("bundle_manifest_sha256") == bmod.sha256_file(_bundle_dirs()[tid] / "manifest.json")
    return _json({**out, "content_hash_verified": True, "same_bundle": same})


async def records_get(request: Request):
    p = _record_path(request.path_params["rid"])
    if not p.exists():
        raise APIError(404, "unknown record")
    d = json.loads(p.read_text())
    iid = _store(d["target_id"], d["investigation"]) if d["target_id"] in _bundle_dirs() else None
    return _json({**{k: v for k, v in d.items() if k != "investigation"}, "investigation_id": iid,
                  "bundle_available": d["target_id"] in _bundle_dirs()})


async def records_replay(request: Request):
    p = _record_path(request.path_params["rid"])
    if not p.exists():
        raise APIError(404, "unknown record")
    d = json.loads(p.read_text())
    b = _bundle(d["target_id"])
    params = {k: v for k, v in d["parameters"].items() if k in analysis.DEFAULTS}
    rec = (await run_in_threadpool(analysis.run, b, params)).to_dict()
    same_bundle = rec["parameters"]["bundle_manifest_sha256"] == d["bundle_manifest_sha256"]
    same = rec["content_hash"] == d["content_hash"]
    iid = _store(d["target_id"], rec)
    result = {"reproduced": same, "same_bundle": same_bundle, "saved_content_hash": d["content_hash"],
              "replay_content_hash": rec["content_hash"], "investigation_id": iid, "replayed_at": utc_now_iso(),
              "explanation": ("identical result" if same else
                              "bundle changed since the record was saved" if not same_bundle else
                              "same bundle but different result: software or environment differs (see software versions)")}
    d["last_replay"] = result
    p.write_text(json.dumps(d, indent=1, default=_default))
    return _json(result)


async def records_delete(request: Request):
    p = _record_path(request.path_params["rid"])
    if not p.exists():
        raise APIError(404, "unknown record")
    p.unlink()
    return _json({"deleted": request.path_params["rid"]})


# ------------------------------------------------------------------ plumbing
async def _body(request: Request) -> dict:
    try:
        raw = await request.body()
        if len(raw) > 2_000_000:
            raise APIError(413, "request too large")
        d = json.loads(raw or b"{}")
        if not isinstance(d, dict):
            raise ValueError
        return d
    except (ValueError, json.JSONDecodeError):
        raise APIError(400, "body must be a JSON object")


async def index(request: Request):
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})


async def api_error(request: Request, exc: APIError):
    return JSONResponse({"error": exc.message}, status_code=exc.status)


async def server_error(request: Request, exc: Exception):
    return JSONResponse({"error": f"internal error: {type(exc).__name__}: {str(exc)[:300]}"}, status_code=500)


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                h = message.setdefault("headers", [])
                h += [(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer"),
                      (b"content-security-policy", b"default-src 'self'; img-src 'self' data: blob:; style-src 'self'; "
                                                   b"script-src 'self'; connect-src 'self'; frame-ancestors 'none'")]
            await send(message)
        await self.app(scope, receive, send_wrapper)


routes = [
    Route("/", index),
    Route("/api/status", status),
    Route("/api/targets", targets),
    Route("/api/targets/{tid}", target_detail),
    Route("/api/targets/{tid}/observations/{key}/image", observation_image),
    Route("/api/targets/{tid}/pair-image", pair_image),
    Route("/api/targets/{tid}/analyze", analyze, methods=["POST"]),
    Route("/api/targets/{tid}/stability", stability_check, methods=["POST"]),
    Route("/api/investigations/{iid}", investigation),
    Route("/api/investigations/{iid}/graph", graph),
    Route("/api/investigations/{iid}/report.md", report),
    Route("/api/investigations/{iid}/record.json", investigation_export),
    Route("/api/investigations/{iid}/discovery", investigation_discovery),
    Route("/api/investigations/{iid}/package.zip", investigation_package),
    Route("/api/capabilities", capabilities_list),
    Route("/api/investigations/{iid}/ask", ask, methods=["POST"]),
    Route("/api/records", records_list),
    Route("/api/records", records_save, methods=["POST"]),
    Route("/api/records/import", records_import, methods=["POST"]),
    Route("/api/records/{rid}", records_get),
    Route("/api/records/{rid}", records_update, methods=["PATCH"]),
    Route("/api/records/{rid}/clone", records_clone, methods=["POST"]),
    Route("/api/records/{rid}", records_delete, methods=["DELETE"]),
    Route("/api/records/{rid}/replay", records_replay, methods=["POST"]),
    Mount("/static", StaticFiles(directory=str(WEB)), name="static"),
]
from . import research as _research  # noqa: E402  (Phase 6 routes; imports this module lazily)
routes[-1:-1] = _research.routes
from . import frontier as _frontier  # noqa: E402  (Phase 7 routes)
routes[-1:-1] = _frontier.routes
from . import epistemic as _epistemic  # noqa: E402  (Phase 8 routes)
routes[-1:-1] = _epistemic.routes

app = SecurityHeaders(Starlette(routes=routes, exception_handlers={APIError: api_error, Exception: server_error}))
