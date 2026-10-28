"""Gate C: run the end-to-end investigation for one target and write the report.

  python scripts/run_pipeline.py "Barnard's Star"
  OFFLINE=1 python scripts/run_pipeline.py "Barnard's Star"   # replay from cache only

Outputs data/runs/<slug>/investigation.json and report.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import pipeline  # noqa: E402
from skytrace.archive.net import Fetcher  # noqa: E402
from skytrace.report import render_markdown  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    name = sys.argv[1].lower()
    cfgs = json.loads((ROOT / "config" / "targets.json").read_text())["targets"]
    cfg = next((c for c in cfgs if name in (c["name"].lower(), c["simbad_id"].lower())), None)
    if cfg is None:
        print(f"unknown target {sys.argv[1]!r}")
        return 2
    inv = pipeline.run(Fetcher(ROOT / "cache"), cfg)
    out = ROOT / "data" / "runs" / re.sub(r"[^a-z0-9]+", "-", cfg["name"].lower()).strip("-")
    out.mkdir(parents=True, exist_ok=True)
    (out / "investigation.json").write_text(json.dumps(inv.to_dict(), indent=2))
    (out / "report.md").write_text(render_markdown(inv))
    for e in inv.events:
        print(f"[{e.status:>8}] {e.step}: {e.detail}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
