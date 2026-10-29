"""Verify that an investigation record traces to unchanged stored files (PROVCHECK-1).

  python scripts/verify_provenance.py syn-var-1                 # uses data/runs/<target>/investigation.json
  python scripts/verify_provenance.py syn-var-1 --record path.json --rerun
  python scripts/verify_provenance.py --all --rerun             # every bundle (runs the analysis if no record)

Never uses the network. Exit code 0 only if every check passes. Writes data/runs/<target>/provenance_check.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import analysis, bundle as bmod  # noqa: E402
from skytrace.provenance_check import verify_record  # noqa: E402


def one(bdir: Path, record_path: Path | None, rerun: bool) -> dict:
    tid = bdir.name
    rp = record_path or ROOT / "data" / "runs" / tid / "investigation.json"
    if rp.exists():
        record = json.loads(rp.read_text())
    else:
        print(f"[{tid}] no stored record; running the analysis first")
        record = analysis.run(bmod.load(bdir)).to_dict()
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(record, indent=2))
    res = verify_record(record, bdir, rerun=rerun)
    out = rp.parent / "provenance_check.json"
    out.write_text(json.dumps(res, indent=2))
    print(f"[{tid}] {'PASS' if res['ok'] else 'FAIL'} ({res['bundle_kind']} bundle, record {str(res['record_hash'])[:12]}…)")
    for c in res["checks"]:
        print(f"   {'ok ' if c['ok'] else 'FAIL'} {c['id']:<20} {c['detail']}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target_id", nargs="?")
    ap.add_argument("--record", type=Path)
    ap.add_argument("--rerun", action="store_true", help="also re-run the analysis and compare the content hash")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    dirs = bmod.find_bundles()
    if not a.all:
        dirs = [d for d in dirs if d.name == a.target_id]
        if not dirs:
            print(f"no bundle for {a.target_id!r}")
            return 2
    results = [one(d, a.record if not a.all else None, a.rerun) for d in dirs]
    return 0 if results and all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
