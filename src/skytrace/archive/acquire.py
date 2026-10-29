"""Acquire a real target bundle from IRSA (SPHEREx), SIMBAD and Gaia DR3.

This is the only module that writes archive bundles. It needs network access;
with OFFLINE=1 it can only rebuild a bundle from the local request cache.

Selection criteria SEL-1 (recorded in discovery.json):
  1. the image is returned by IRSA SIA2 for the target position propagated to the
     survey midpoint (QR3 first; a QR2 image is used only if the same
     observation/detector is absent from QR3);
  2. its detector is in the requested set and it has t_min/t_max;
  3. after download, the target (propagated to that image's epoch) lies at least
     edge_px inside the cutout according to the image's own WCS;
  4. at most max_images per target, chosen evenly in time if more exist, and
     at most max_total_mb of downloads (both limits are reported if reached).
Every image that fails a criterion is kept in discovery.json with its reason.
Downloaded files are stored byte-for-byte; nothing is modified.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import bundle as bmod
from ..provenance import Provenance
from ..science.coords import Astrometry, angular_separation_deg, mjd_to_jyear, parse_dec, parse_ra, propagate
from . import references as refs_mod
from . import spherex
from .net import Fetcher, FetchError, OfflineError
from .products import ProductError, inspect_product, load_product

ACQ_ERRORS = (FetchError, OfflineError, LookupError, ValueError)
GENERATOR = "scripts/acquire_targets.py"


def mjd_to_iso(mjd: float) -> str:
    return (datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=mjd)).isoformat(timespec="seconds")


class AcquisitionLog:
    def __init__(self):
        self.lines: list[dict] = []

    def __call__(self, step: str, status: str, detail: str, **data):
        self.lines.append({"step": step, "status": status, "detail": detail, **data})
        print(f"[{status:>8}] {step}: {detail}")


def resolve(fetcher: Fetcher, cfg: dict, log: AcquisitionLog) -> tuple[dict, list[Provenance]] | None:
    """SIMBAD identity + Gaia DR3 astrometry (matched by position and proper motion)."""
    try:
        row, prov = refs_mod.resolve_simbad(fetcher, cfg["simbad_id"])
    except ACQ_ERRORS as e:
        log("resolve:simbad", "failed", str(e))
        return None
    log("resolve:simbad", "ok", f"{row['main_id']} ({prov.origin})")
    simbad = Astrometry(float(row["ra"]), float(row["dec"]), 2000.0, float(row.get("pmra") or 0),
                        float(row.get("pmdec") or 0), float(row.get("plx_value") or 0), source="SIMBAD")
    identity = {"catalogue": "SIMBAD", "main_id": row["main_id"], "otype": row.get("otype"), "sp_type": row.get("sp_type"),
                "simbad_ra_deg": row["ra"], "simbad_dec_deg": row["dec"], "coo_bibcode": row.get("coo_bibcode"),
                "pm_bibcode": row.get("pm_bibcode"), "frame": "ICRS", "simbad_epoch": "J2000"}
    if cfg.get("supplied_coords"):
        sc = cfg["supplied_coords"]
        sep = float(angular_separation_deg(parse_ra(sc["ra"]), parse_dec(sc["dec"]), simbad.ra, simbad.dec)) * 3600
        identity["supplied_coords"] = {**sc, "separation_from_simbad_arcsec": sep}
        log("resolve:supplied", "info", f"supplied coordinates are {sep:.2f}\" from SIMBAD J2000")
    provs = [prov]
    ra16, dec16 = propagate(simbad, 2016.0)
    try:
        rows, gprov = refs_mod.gaia_cone(fetcher, ra16, dec16, 5 / 3600, g_min=-5, g_max=25, limit=20)
        provs.append(gprov)
    except ACQ_ERRORS as e:
        log("resolve:gaia", "failed", f"{e}; using SIMBAD astrometry")
        rows = []
    best = None
    for r in rows:
        if r.get("pmra") is None:
            continue
        dpm = math.hypot(r["pmra"] - simbad.pmra, r["pmdec"] - simbad.pmdec)
        if dpm <= max(50.0, 0.05 * math.hypot(simbad.pmra, simbad.pmdec)) and (best is None or dpm < best[0]):
            best = (dpm, r)
    if best:
        g = best[1]
        log("resolve:gaia", "ok", f"Gaia DR3 {g['source_id']} (|Δpm| vs SIMBAD {best[0]:.1f} mas/yr)")
        ast = {"ra": g["ra"], "dec": g["dec"], "ref_epoch": g.get("ref_epoch") or 2016.0, "pmra": g["pmra"], "pmdec": g["pmdec"],
               "pmra_error": g.get("pmra_error"), "pmdec_error": g.get("pmdec_error"), "parallax": g.get("parallax") or 0.0,
               "radial_velocity": g.get("radial_velocity") or 0.0, "ruwe": g.get("ruwe"),
               "source": f"{refs_mod.GAIA_DR3} source_id={g['source_id']}"}
        identity["gaia_dr3_source_id"] = g["source_id"]
    else:
        log("resolve:gaia", "rejected", "no Gaia DR3 source within 5\" with matching proper motion; using SIMBAD astrometry")
        ast = {"ra": simbad.ra, "dec": simbad.dec, "ref_epoch": 2000.0, "pmra": simbad.pmra, "pmdec": simbad.pmdec,
               "parallax": simbad.parallax, "radial_velocity": 0.0, "source": "SIMBAD"}
    return {"identity": identity, "astrometry": ast}, provs


def _even(items: list, n: int) -> list:
    if len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def acquire(fetcher: Fetcher, cfg: dict, out_root: Path = bmod.ARCHIVE_ROOT, *, detectors=(1, 2, 3, 4, 5, 6),
            size_deg: float = 0.1, edge_px: float = 6.0, max_images: int = 300, max_total_mb: float = 2000.0,
            survey_mid_jyear: float = 2026.0) -> dict:
    log = AcquisitionLog()
    tid = cfg["target_id"]
    bdir = out_root / tid
    previous = {}
    if (bdir / "discovery.json").exists():
        import json
        for o in json.loads((bdir / "discovery.json").read_text()).get("observations", []):
            if o.get("file") and o.get("sha256"):
                previous[o["key"]] = o

    res = resolve(fetcher, cfg, log)
    if res is None:
        return {"target_id": tid, "status": "BLOCKED: target resolution failed", "log": log.lines}
    tinfo, tprovs = res
    (bdir / "images").mkdir(parents=True, exist_ok=True)
    ast = Astrometry(**{k: tinfo["astrometry"][k] for k in ("ra", "dec", "ref_epoch", "pmra", "pmdec", "parallax", "radial_velocity")})
    ra_m, dec_m = propagate(ast, survey_mid_jyear)
    radius = (math.hypot(ast.pmra, ast.pmdec) / 1000 * 1.5 + 2.0) / 3600

    # ---- discovery
    found: dict[tuple, spherex.Observation] = {}
    disc_prov = []
    search = {}
    for rel in ("QR3", "QR2"):
        try:
            obs, prov = spherex.discover_sia(fetcher, ra_m, dec_m, rel, radius)
        except ACQ_ERRORS as e:
            log(f"discover:{rel}", "failed", str(e))
            search[rel] = {"status": "failed", "error": str(e)}
            continue
        disc_prov.append(prov)
        new = 0
        for o in obs:
            if (o.obs_id, o.detector) not in found:
                found[(o.obs_id, o.detector)] = o
                new += 1
        search[rel] = {"status": "ok", "n_returned": len(obs), "n_new": new, "source_url": prov.source_url,
                       "retrieved_at": prov.retrieved_at, "origin": prov.origin}
        log(f"discover:{rel}", "ok", f"{len(obs)} images ({new} not already in a preferred release)")

    records, candidates = [], []
    for o in sorted(found.values(), key=lambda o: (o.t_mid_mjd or 0, o.detector or 0)):
        rec = {"key": f"{o.release}:{o.obs_id}:D{o.detector}", "release": o.release, "obs_id": o.obs_id,
               "detector": o.detector, "t_min_mjd": o.t_min_mjd, "t_max_mjd": o.t_max_mjd, "t_mid_mjd": o.t_mid_mjd,
               "t_mid_iso": mjd_to_iso(o.t_mid_mjd) if o.t_mid_mjd else None, "em_min_um": o.em_min_um,
               "em_max_um": o.em_max_um, "access_url": o.access_url, "discovered_via": o.discovered_via,
               "file": None, "included": False}
        if o.detector not in detectors:
            rec["exclusion_reason"] = f"detector D{o.detector} not requested"
        elif o.t_mid_mjd is None:
            rec["exclusion_reason"] = "no observation time in SIA metadata"
        else:
            candidates.append(rec)
        records.append(rec)
    chosen = _even(candidates, max_images)
    for rec in candidates:
        if rec not in chosen:
            rec["exclusion_reason"] = f"over the per-target limit of {max_images} images (even-in-time subsample)"

    # ---- download + per-image checks
    files: dict[str, dict] = {}
    total = 0
    inspected: dict[str, dict] = {}
    for rec in chosen:
        if total > max_total_mb * 1e6:
            rec["exclusion_reason"] = f"download budget of {max_total_mb} MB reached"
            continue
        epoch = float(mjd_to_jyear(rec["t_mid_mjd"]))
        tra, tdec = propagate(ast, epoch)
        rel = f"images/{rec['release']}_{rec['obs_id']}_D{rec['detector']}.fits"
        path = bdir / rel
        prev = previous.get(rec["key"])
        try:
            if prev and path.exists() and bmod.sha256_file(path) == prev["sha256"]:
                content = path.read_bytes()
                prov = Provenance.from_dict(prev["provenance"])
                log("download", "ok", f"{rec['key']}: already present (resumed)")
            else:
                obs = spherex.Observation(rec["release"], rec["obs_id"], rec["detector"], rec["t_mid_mjd"], rec["t_min_mjd"],
                                          rec["t_max_mjd"], rec["em_min_um"], rec["em_max_um"], rec["access_url"], rec["discovered_via"])
                r = spherex.fetch_cutout(fetcher, obs, tra, tdec, size_deg)
                content, prov = r.content, r.provenance
                tmp = path.with_suffix(".fits.part")
                tmp.write_bytes(content)
                tmp.replace(path)
                log("download", "ok", f"{rec['key']}: {len(content) / 1e3:.0f} kB ({prov.origin})")
        except ACQ_ERRORS as e:
            rec["exclusion_reason"] = f"download failed: {e}"
            log("download", "failed", f"{rec['key']}: {e}")
            continue
        total += len(content)
        rec["file"], rec["sha256"], rec["bytes"] = rel, bmod.sha256_file(path), len(content)
        rec["provenance"] = prov.to_dict()
        rec["cutout_url"] = prov.source_url
        files[rel] = {"role": "image", "obs_key": rec["key"], "provenance": prov.to_dict()}
        try:
            prod = load_product(path)
            x, y = prod.sky_to_pixel(tra, tdec)
            ny, nx = prod.image.shape
            margin = min(x, y, nx - 1 - x, ny - 1 - y)
            ik = f"{rec['release']}:D{rec['detector']}"
            if ik not in inspected:
                inspected[ik] = {"key": rec["key"], **inspect_product(prod)}
        except ProductError as e:
            rec["exclusion_reason"] = f"unreadable product: {e}"
            log("inspect", "failed", f"{rec['key']}: {e}")
            continue
        if margin < edge_px:
            rec["exclusion_reason"] = f"target {margin:.1f} px from the cutout edge (< {edge_px} px)"
            continue
        rec["included"] = True

    # ---- reference stars
    try:
        rows, rprov = refs_mod.gaia_cone(fetcher, *propagate(ast, 2016.0), size_deg * 0.75, 10.0, 17.5, limit=800)
        stars = [{"source_id": str(r["source_id"]), "ra": r["ra"], "dec": r["dec"], "ref_epoch": r.get("ref_epoch") or 2016.0,
                  "pmra": r.get("pmra"), "pmdec": r.get("pmdec"), "pmra_error": r.get("pmra_error"),
                  "pmdec_error": r.get("pmdec_error"), "g_mag": r.get("phot_g_mean_mag"), "ruwe": r.get("ruwe")}
                 for r in rows if r.get("pmra") is not None
                 and str(r["source_id"]) != str(tinfo["identity"].get("gaia_dr3_source_id"))]
        bmod.write_json(bdir / "references.json", {"catalogue": refs_mod.GAIA_DR3, "query": rprov.source_url,
                                                   "criteria": "G 10-17.5, five-parameter astrometry, within 0.75 x cutout size",
                                                   "stars": stars})
        files["references.json"] = {"role": "references", "provenance": rprov.to_dict()}
        log("references", "ok", f"{len(stars)} Gaia DR3 reference stars")
    except ACQ_ERRORS as e:
        log("references", "failed", str(e))

    target = {"target_id": tid, "name": cfg["name"], "kind": "archive", "role": cfg.get("role", ""), **tinfo}
    bmod.write_json(bdir / "target.json", target)
    files["target.json"] = {"role": "target", "provenance": tprovs[-1].to_dict()}
    bmod.write_json(bdir / "discovery.json", {
        "search": search, "observations": records,
        "selection": {"rules": "SEL-1", "criteria": [
            "returned by IRSA SIA2 at the target position (QR3 preferred; QR2 only for observations absent from QR3)",
            f"detector in {list(detectors)} and observation time present",
            f"target at least {edge_px} px inside the {size_deg} deg cutout at the image epoch",
            f"at most {max_images} images (even-in-time) and {max_total_mb} MB"]}})
    files["discovery.json"] = {"role": "discovery", "provenance": (disc_prov[0] if disc_prov else tprovs[0]).to_dict()}
    if inspected:
        bmod.write_json(bdir / "inspection.json", inspected)
        files["inspection.json"] = {"role": "inspection", "provenance": (disc_prov[0] if disc_prov else tprovs[0]).to_dict()}
    # stale files from a previous run that are no longer referenced are removed from the bundle directory
    keep = set(files)
    for p in (bdir / "images").glob("*.fits"):
        if str(p.relative_to(bdir)) not in keep:
            p.unlink()
    m = bmod.write_manifest(bdir, tid, "archive", files, GENERATOR,
                            notes="Real SPHEREx archive products retrieved from IRSA. Files are stored unmodified.")
    n_inc = sum(r["included"] for r in records)
    status = "OK" if n_inc else "NO USABLE IMAGES"
    return {"target_id": tid, "status": status, "n_found": len(records), "n_included": n_inc,
            "total_bytes": m["total_bytes"], "log": log.lines}
