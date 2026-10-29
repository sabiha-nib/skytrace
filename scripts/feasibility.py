"""Gate B: real-archive feasibility survey for the SKYTRACE targets.

For each target: resolve (SIMBAD + Gaia DR3), enumerate SPHEREx images in QR3
and QR2 (SIA2), and, with --wavelengths, fetch a small cutout per image to read
the wavelength at the target's pixel and its quality flags. Writes:

  data/feasibility/feasibility_matrix.csv   one row per (target, image)
  data/feasibility/feasibility_matrix.json  same, plus per-target summaries

Nothing is invented: when a query fails, the row records the failure.

Usage:
  python scripts/feasibility.py                    # metadata only
  python scripts/feasibility.py --wavelengths      # + small cutouts (needs astropy)
  python scripts/feasibility.py --target "R Dra"   # one target
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace.archive import spherex  # noqa: E402
from skytrace.archive.net import Fetcher, offline_enabled  # noqa: E402
from skytrace.archive.products import ProductError, load_product  # noqa: E402
from skytrace.archive.acquire import ACQ_ERRORS, AcquisitionLog, resolve  # noqa: E402
from skytrace.science.coords import Astrometry  # noqa: E402
from skytrace.science import flags as fl  # noqa: E402
from skytrace.science.coords import mjd_to_jyear, propagate  # noqa: E402
from skytrace.science.wavelength import SourceSample, match_pairs  # noqa: E402

FIELDS = ["target", "release", "observation_id", "observation_time", "detector", "product_type",
          "wavelength_coverage", "quality_status", "retrieval_status", "scientific_use", "limitations", "source_url"]


def survey_passes(mjds: list[float], gap_days: float = 30.0) -> list[tuple[float, float, int]]:
    """Group observation times into visits separated by > gap_days (empirical, not a mission definition)."""
    out = []
    for t in sorted(mjds):
        if out and t - out[-1][1] <= gap_days:
            out[-1] = (out[-1][0], t, out[-1][2] + 1)
        else:
            out.append((t, t, 1))
    return out


def run_target(fetcher: Fetcher, cfg: dict, wavelengths: bool) -> tuple[list[dict], dict]:
    log = AcquisitionLog()
    res = resolve(fetcher, cfg, log)
    base = {"target": cfg["name"], "scientific_use": cfg.get("role", "")}
    if res is None:
        err = log.lines[-1]["detail"]
        return [{**base, "release": "", "retrieval_status": f"BLOCKED: target resolution failed: {err}"}], \
               {"target": cfg["name"], "resolved": False, "events": log.lines}
    a = res[0]["astrometry"]
    ast = Astrometry(a["ra"], a["dec"], a["ref_epoch"], a["pmra"], a["pmdec"], a.get("parallax") or 0.0, source=a["source"])
    rows, obs_all = [], []
    ra, dec = propagate(ast, 2026.0)
    radius = (math.hypot(ast.pmra, ast.pmdec) / 1000 * 1.5 + 2.0) / 3600
    for rel in ("QR3", "QR2"):
        try:
            obs, prov = spherex.discover_sia(fetcher, ra, dec, rel, radius)
        except ACQ_ERRORS as e:
            rows.append({**base, "release": rel, "retrieval_status": f"BLOCKED: discovery failed: {e}"})
            continue
        if not obs:
            rows.append({**base, "release": rel, "retrieval_status": f"NO DATA: SIA returned 0 images ({prov.origin})",
                         "source_url": prov.source_url})
        for o in obs:
            obs_all.append(o)
            row = {**base, "release": rel, "observation_id": o.obs_id, "observation_time": o.t_mid_mjd,
                   "detector": f"D{o.detector}" if o.detector else "", "product_type": "Level 2 Spectral Image (MEF)",
                   "wavelength_coverage": f"{o.em_min_um:.3f}-{o.em_max_um:.3f} um (image-wide)" if o.em_min_um else "",
                   "quality_status": "not inspected", "retrieval_status": f"metadata {prov.origin}",
                   "limitations": "", "source_url": o.access_url}
            if wavelengths and o.t_mid_mjd and o.detector:
                tra, tdec = propagate(ast, float(mjd_to_jyear(o.t_mid_mjd)))
                try:
                    res = spherex.fetch_cutout(fetcher, o, tra, tdec, 0.02)
                    prod = load_product(res.content)
                    x, y = prod.sky_to_pixel(tra, tdec)
                    wl, bw = prod.wavelength_at(x, y)
                    fmap = fl.resolve_bits(prod.headers.get("FLAGS"))
                    yy, xx = __import__("numpy").indices(prod.image.shape)
                    s = fl.summarize(prod.flags, ((xx - x) ** 2 + (yy - y) ** 2) <= 9, fmap)
                    row["wavelength_coverage"] += f"; at target {wl:.4f} um (bw {bw:.4f})"
                    row["quality_status"] = "ok" if s.n_reject == 0 else f"flagged: {','.join(s.reject_names)}"
                    if s.warn_names:
                        row["quality_status"] += f"; warn: {','.join(s.warn_names)}"
                    row["retrieval_status"] = f"cutout {res.provenance.origin}"
                    row["_wl"], row["_bw"] = wl, bw
                except (*ACQ_ERRORS, ProductError) as e:
                    row["retrieval_status"] = f"cutout FAILED: {e}"
            rows.append(row)

    # summary
    summary = {"target": cfg["name"], "resolved": True, "astrometry_source": ast.source,
               "pm_mas_yr": [ast.pmra, ast.pmdec], "n_images": len(obs_all),
               "by_release_detector": dict(Counter(f"{o.release} D{o.detector}" for o in obs_all)),
               "visits": [{"start_mjd": a, "end_mjd": b, "n": n} for a, b, n in
                          survey_passes([o.t_mid_mjd for o in obs_all if o.t_mid_mjd])]}
    if obs_all:
        t = [o.t_mid_mjd for o in obs_all if o.t_mid_mjd]
        span = (max(t) - min(t)) / 365.25 if t else 0
        summary["baseline_yr"] = span
        summary["expected_shift_arcsec"] = math.hypot(ast.pmra, ast.pmdec) / 1000 * span
        summary["expected_shift_px_at_6.2arcsec"] = summary["expected_shift_arcsec"] / 6.2
    wl_rows = [r for r in rows if "_wl" in r]
    if wl_rows:
        samples = [SourceSample(r["observation_id"] + r["detector"], int(r["detector"][1]), r["observation_time"],
                                r["_wl"], r["_bw"], "ok" if r["quality_status"].startswith("ok") else "flagged")
                   for r in wl_rows]
        dec_ = match_pairs(samples)
        summary["wavelength_matched_pairs"] = sum(d.accepted for d in dec_)
        summary["pairs_considered"] = len(dec_)
    for r in rows:
        r.pop("_wl", None), r.pop("_bw", None)
    summary["events"] = log.lines
    return rows, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wavelengths", action="store_true", help="fetch small cutouts to read λ at the target")
    ap.add_argument("--target", help="SIMBAD id or name of a single target")
    ap.add_argument("--out", default=str(ROOT / "data" / "feasibility"))
    a = ap.parse_args()
    cfgs = json.loads((ROOT / "config" / "targets.json").read_text())["targets"]
    if a.target:
        cfgs = [c for c in cfgs if a.target.lower() in (c["name"].lower(), c["simbad_id"].lower())]
    fetcher = Fetcher(ROOT / "cache")
    print(f"OFFLINE={int(offline_enabled())}", file=sys.stderr)
    all_rows, summaries = [], []
    for c in cfgs:
        rows, summ = run_target(fetcher, c, a.wavelengths)
        all_rows += rows
        summaries.append(summ)
        print(f"{c['name']}: {summ.get('n_images', 0)} images; {summ.get('by_release_detector', {})}", file=sys.stderr)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "feasibility_matrix.csv", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    (out / "feasibility_matrix.json").write_text(json.dumps({"rows": all_rows, "summaries": summaries}, indent=2, default=str))
    print(f"wrote {out}/feasibility_matrix.csv and .json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
