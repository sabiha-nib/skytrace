"""Target data bundles: the only input the analysis and the application read.

Layout (one directory per target):

    manifest.json     schema, kind ("archive" | "synthetic"), every file with sha256, bytes, role, provenance
    target.json       catalogue identity and astrometry, with provenance
    references.json   astrometric reference stars (Gaia DR3 for archive bundles)
    discovery.json    archive search results per release, selection criteria, included/excluded images
    inspection.json   real FITS structure per release/detector (written by acquisition)
    images/*.fits     original products, byte-for-byte as retrieved (never modified)

Archive bundles are written by scripts/acquire_targets.py from live services.
Synthetic bundles are written by scripts/make_synthetic_fixtures.py, live
under fixtures/synthetic/, carry SYNTHETIC = T in every FITS header and
"synthetic" provenance, and are refused by the verifier if either marker is
missing or contradicted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import fitsio
from .provenance import utc_now_iso

SCHEMA = "skytrace.bundle/1"
KINDS = ("archive", "synthetic")
ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ROOT = ROOT / "data" / "bundles"
SYNTHETIC_ROOT = ROOT / "fixtures" / "synthetic"


class BundleError(ValueError):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(p)


def write_manifest(bdir: Path, target_id: str, kind: str, file_meta: dict[str, dict], generator: str,
                   notes: str = "") -> dict:
    """Generate the manifest from files that actually exist; file_meta maps relative path -> role/provenance."""
    if kind not in KINDS:
        raise BundleError(f"kind must be one of {KINDS}")
    files = []
    for rel in sorted(file_meta):
        p = bdir / rel
        if not p.is_file():
            raise BundleError(f"manifest entry {rel} does not exist")
        files.append({"path": rel, "sha256": sha256_file(p), "bytes": p.stat().st_size, **file_meta[rel]})
    m = {"schema": SCHEMA, "target_id": target_id, "kind": kind, "created_at": utc_now_iso(),
         "generator": generator, "notes": notes, "files": files,
         "total_bytes": sum(f["bytes"] for f in files)}
    write_json(bdir / "manifest.json", m)
    return m


def verify(bdir: Path) -> dict:
    """Checks a bundle against its manifest. Returns {"ok": bool, "problems": [...], ...}."""
    problems: list[str] = []
    mp = bdir / "manifest.json"
    if not mp.exists():
        return {"ok": False, "problems": ["manifest.json missing"], "bundle": str(bdir)}
    m = json.loads(mp.read_text())
    if m.get("schema") != SCHEMA:
        problems.append(f"unknown schema {m.get('schema')!r}")
    kind = m.get("kind")
    if kind not in KINDS:
        problems.append(f"invalid kind {kind!r}")
    listed = set()
    for f in m.get("files", []):
        p = bdir / f["path"]
        listed.add(f["path"])
        if not p.is_file():
            problems.append(f"missing file {f['path']}")
            continue
        if p.stat().st_size != f["bytes"] or sha256_file(p) != f["sha256"]:
            problems.append(f"checksum mismatch {f['path']}")
        origin = (f.get("provenance") or {}).get("origin")
        if kind == "synthetic" and origin != "synthetic":
            problems.append(f"{f['path']}: synthetic bundle file has provenance origin {origin!r}")
        if kind == "archive" and origin not in ("live", "cache"):
            problems.append(f"{f['path']}: archive bundle file has provenance origin {origin!r}")
        if p.suffix == ".fits" and p.is_file():
            try:
                syn = any(bool(h.header.get("SYNTHETIC")) for h in fitsio.read(p))
            except fitsio.FITSError as e:
                problems.append(f"{f['path']}: unreadable FITS ({e})")
                continue
            if kind == "synthetic" and not syn:
                problems.append(f"{f['path']}: synthetic bundle FITS lacks SYNTHETIC = T")
            if kind == "archive" and syn:
                problems.append(f"{f['path']}: archive bundle contains a SYNTHETIC FITS file")
    present = {str(p.relative_to(bdir)) for p in bdir.rglob("*") if p.is_file() and p.name != "manifest.json"
               and not p.name.endswith(".part")}
    for extra in sorted(present - listed):
        problems.append(f"unlisted file {extra}")
    for req in ("target.json", "discovery.json"):
        if req not in listed:
            problems.append(f"required file {req} not in manifest")
    if kind == "archive" and "inspection.json" not in listed:
        problems.append("archive bundle has no inspection.json (real FITS structure not recorded)")
    return {"ok": not problems, "problems": problems, "bundle": str(bdir), "kind": kind,
            "target_id": m.get("target_id"), "n_files": len(listed), "total_bytes": m.get("total_bytes", 0)}


@dataclass
class Bundle:
    path: Path
    manifest: dict
    target: dict
    references: dict
    discovery: dict
    inspection: dict

    @property
    def kind(self) -> str:
        return self.manifest["kind"]

    @property
    def target_id(self) -> str:
        return self.manifest["target_id"]

    def observations(self) -> list[dict]:
        """Included observations with a local file, sorted by time then detector."""
        obs = [o for o in self.discovery.get("observations", []) if o.get("included") and o.get("file")]
        return sorted(obs, key=lambda o: (o.get("t_mid_mjd") or 0, o.get("detector") or 0))

    def all_observations(self) -> list[dict]:
        return sorted(self.discovery.get("observations", []), key=lambda o: (o.get("t_mid_mjd") or 0, o.get("detector") or 0))

    def file_entry(self, rel: str) -> dict | None:
        return next((f for f in self.manifest["files"] if f["path"] == rel), None)

    def observation(self, key: str) -> dict:
        for o in self.discovery.get("observations", []):
            if o["key"] == key:
                return o
        raise KeyError(key)


def load(bdir: Path) -> Bundle:
    bdir = Path(bdir)
    rd = lambda n, default=None: json.loads((bdir / n).read_text()) if (bdir / n).exists() else default
    m = rd("manifest.json")
    if m is None:
        raise BundleError(f"{bdir} has no manifest.json")
    return Bundle(bdir, m, rd("target.json", {}), rd("references.json", {"stars": []}),
                  rd("discovery.json", {"observations": []}), rd("inspection.json", {}))


def find_bundles(roots: tuple[Path, ...] = (ARCHIVE_ROOT, SYNTHETIC_ROOT)) -> list[Path]:
    out = []
    for r in roots:
        if r.exists():
            out += sorted(p.parent for p in r.glob("*/manifest.json"))
    return out
