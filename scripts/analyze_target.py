"""Run the offline investigation for one bundle and write its record and report.

  python scripts/analyze_target.py syn-hpm-1
  python scripts/analyze_target.py barnards-star --param aperture_radius_px=2.5

Never uses the network. Outputs data/runs/<target_id>/investigation.json and report.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import analysis, bundle as bmod  # noqa: E402
from skytrace.report import render_markdown  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target_id")
    ap.add_argument("--param", action="append", default=[], help="key=value (JSON value)")
    a = ap.parse_args()
    found = [d for d in bmod.find_bundles() if d.name == a.target_id]
    if not found:
        print(f"no bundle for {a.target_id!r}; run scripts/acquire_targets.py --target {a.target_id} first")
        return 2
    v = bmod.verify(found[0])
    if not v["ok"]:
        print("bundle failed verification:", *v["problems"], sep="\n  ")
        return 1
    params = {k: json.loads(val) for k, val in (p.split("=", 1) for p in a.param)}
    inv = analysis.run(bmod.load(found[0]), params)
    out = ROOT / "data" / "runs" / a.target_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "investigation.json").write_text(json.dumps(inv.to_dict(), indent=2))
    (out / "report.md").write_text(render_markdown(inv))
    for e in inv.events:
        if e.step != "measure" or e.status != "ok":
            print(f"[{e.status:>8}] {e.step}: {e.detail[:160]}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
