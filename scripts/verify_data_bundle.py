"""Verify every data bundle against its manifest (checksums, completeness, kind markers).

  python scripts/verify_data_bundle.py            # all bundles
  python scripts/verify_data_bundle.py data/bundles/barnards-star

Exit status 0 only if every bundle verifies. Writes data/bundle_verification.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import bundle as bmod  # noqa: E402
from skytrace.provenance import utc_now_iso  # noqa: E402


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv] or bmod.find_bundles()
    results = [bmod.verify(d) for d in dirs]
    for r in results:
        print(f"{'OK  ' if r['ok'] else 'FAIL'} {r.get('kind') or '?':<9} {r.get('target_id') or r['bundle']}: "
              f"{r.get('n_files', 0)} files, {r.get('total_bytes', 0) / 1e6:.1f} MB")
        for p in r["problems"]:
            print(f"       - {p}")
    if not results:
        print("no bundles found")
    out = ROOT / "data" / "bundle_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"checked_at": utc_now_iso(), "results": results}, indent=2))
    return 0 if results and all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
