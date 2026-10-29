"""Acquire real SPHEREx target bundles (needs network access to IRSA, SIMBAD and the Gaia archive).

  python scripts/acquire_targets.py --all
  python scripts/acquire_targets.py --target barnards-star [--max-images 120] [--size 0.1]

Writes data/bundles/<target_id>/ (see src/skytrace/bundle.py), then verifies it.
Re-running resumes: files already present with a matching checksum are not downloaded again.
A summary is written to data/acquisition_report.json. Failures are reported, never hidden.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import bundle as bmod  # noqa: E402
from skytrace.archive.acquire import acquire  # noqa: E402
from skytrace.archive.net import Fetcher, offline_enabled  # noqa: E402
from skytrace.provenance import utc_now_iso  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--target", help="target_id from config/targets.json (e.g. barnards-star)")
    ap.add_argument("--max-images", type=int, default=300)
    ap.add_argument("--max-total-mb", type=float, default=2000.0)
    ap.add_argument("--size", type=float, default=0.1, help="cutout size in degrees (<= 0.5)")
    ap.add_argument("--detectors", default="1,2,3,4,5,6")
    a = ap.parse_args()
    cfgs = json.loads((ROOT / "config" / "targets.json").read_text())["targets"]
    if a.target:
        cfgs = [c for c in cfgs if c["target_id"] == a.target]
        if not cfgs:
            print(f"unknown target {a.target!r}")
            return 2
    print(f"OFFLINE={int(offline_enabled())}")
    fetcher = Fetcher(ROOT / "cache")
    report = {"run_at": utc_now_iso(), "offline": offline_enabled(), "targets": []}
    for c in cfgs:
        print(f"\n=== {c['name']} ===")
        r = acquire(fetcher, c, detectors=tuple(int(x) for x in a.detectors.split(",")), size_deg=a.size,
                    max_images=a.max_images, max_total_mb=a.max_total_mb)
        bdir = bmod.ARCHIVE_ROOT / c["target_id"]
        r["verification"] = bmod.verify(bdir) if (bdir / "manifest.json").exists() else {"ok": False, "problems": ["no manifest written"]}
        print(f"--> {r['status']}; verification ok={r['verification']['ok']} {r['verification'].get('problems', [])[:3]}")
        report["targets"].append(r)
    out = ROOT / "data" / "acquisition_report.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {out}")
    return 0 if all(t["verification"]["ok"] and t["status"] == "OK" for t in report["targets"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
