"""Build data/observation_index.json from every bundle on disk (archive and synthetic).

The index lists, per target, the normalised observations (key, release, detector,
time, wavelength range, file, checksum, inclusion) and the bundle's verification
result. The application reads bundles directly; the index is a portable summary.

  python scripts/build_observation_index.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import bundle as bmod  # noqa: E402
from skytrace.provenance import utc_now_iso  # noqa: E402


def build() -> dict:
    out = {"schema": "skytrace.observation_index/1", "built_at": utc_now_iso(), "targets": []}
    for bdir in bmod.find_bundles():
        b = bmod.load(bdir)
        v = bmod.verify(bdir)
        sha = {f["path"]: f["sha256"] for f in b.manifest["files"]}
        obs = [{"key": o["key"], "release": o["release"], "obs_id": o["obs_id"], "detector": o["detector"],
                "t_mid_mjd": o.get("t_mid_mjd"), "t_mid_iso": o.get("t_mid_iso"), "em_min_um": o.get("em_min_um"),
                "em_max_um": o.get("em_max_um"), "file": o.get("file"), "sha256": sha.get(o.get("file")),
                "included": o.get("included"), "exclusion_reason": o.get("exclusion_reason")}
               for o in b.all_observations()]
        t = [o["t_mid_mjd"] for o in obs if o["included"] and o["t_mid_mjd"]]
        out["targets"].append({
            "target_id": b.target_id, "name": b.target.get("name"), "kind": b.kind, "bundle": str(bdir.relative_to(ROOT)),
            "verified": v["ok"], "problems": v["problems"], "total_bytes": b.manifest.get("total_bytes"),
            "n_observations": len(obs), "n_included": sum(1 for o in obs if o["included"]),
            "by_detector": dict(Counter(f"D{o['detector']}" for o in obs if o["included"])),
            "time_span_mjd": [min(t), max(t)] if t else None, "observations": obs})
    return out


if __name__ == "__main__":
    idx = build()
    p = ROOT / "data" / "observation_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(idx, indent=2))
    for t in idx["targets"]:
        print(f"{t['target_id']:<14} {t['kind']:<9} verified={t['verified']} included={t['n_included']}/{t['n_observations']}")
    print(f"wrote {p}")
