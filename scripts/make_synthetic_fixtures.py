"""Generate the SYNTHETIC fixture bundles used by tests and the offline demo.

These are NOT observations (see src/skytrace/synthetic.py). The generator lives in the package so the
robustness tests can build variants (parallax, calibration offsets, release mixing, distortion, bad
reference stars, low S/N) in temporary directories.

    python scripts/make_synthetic_fixtures.py          # writes fixtures/synthetic/{syn-hpm-1,syn-var-1}
    python scripts/make_synthetic_fixtures.py --check  # regenerate into a temp dir and compare image bytes
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import bundle as bmod  # noqa: E402
from skytrace.synthetic import SPECS, build  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.check:
        for s in SPECS:
            print("wrote", build(s))
        return 0
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for s in SPECS:
            new = build(s, Path(td) / s["target_id"])
            old = bmod.SYNTHETIC_ROOT / s["target_id"]
            for f in sorted((old / "images").glob("*.fits")):
                same = bmod.sha256_file(f) == bmod.sha256_file(new / "images" / f.name)
                bad += not same
            for n in ("target.json", "references.json", "discovery.json"):
                bad += (old / n).read_bytes() != (new / n).read_bytes()
            print(f"{s['target_id']}: {'identical' if not bad else f'{bad} file(s) differ'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
