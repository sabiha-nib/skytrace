"""Build a release archive from the committed tree and verify its contents.

  python scripts/make_release.py

Creates dist/skytrace-<version>.zip with `git archive` (so only committed files are
included: no .env, caches, downloads, saved records or .git), then reopens the
archive and checks it: required files present, no secrets, bundle files intact.
Writes dist/skytrace-<version>.zip.sha256 and dist/RELEASE_MANIFEST.json.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import __version__  # noqa: E402

REQUIRED = ["README.md", "run.py", "pyproject.toml", ".env.example", "src/skytrace/server/app.py", "web/index.html",
            "scripts/acquire_targets.py", "scripts/verify.py", "fixtures/synthetic/syn-hpm-1/manifest.json",
            "fixtures/synthetic/syn-var-1/manifest.json", "docs/TEST_REPORT.md"]


def main() -> int:
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        print("working tree has uncommitted changes; commit first so the release matches a commit")
        return 1
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"skytrace-{__version__}.zip"
    if out.exists() and "--force" not in sys.argv:
        print(f"{out.name} already exists; earlier release artifacts are never overwritten (bump the version, or pass --force "
              "to rebuild this same version deliberately)")
        return 1
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=skytrace-{__version__}/", "-o", str(out), "HEAD"], cwd=ROOT, check=True)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        bad = z.testzip()
        prefix = f"skytrace-{__version__}/"
        missing = [r for r in REQUIRED if prefix + r not in names]
        files = [n for n in names if not n.endswith("/")]
        forbidden = [n for n in files if n.endswith("/.env") or "/.git/" in n or ("/cache/" in n and not n.endswith(".gitkeep"))
                     or "/data/records/" in n]
        # bundle checksums inside the archive
        problems = []
        for mf in [n for n in names if n.endswith("manifest.json") and "/fixtures/" in n or "/data/bundles/" in n and n.endswith("manifest.json")]:
            m = json.loads(z.read(mf))
            base = mf.rsplit("/", 1)[0] + "/"
            for f in m["files"]:
                if hashlib.sha256(z.read(base + f["path"])).hexdigest() != f["sha256"]:
                    problems.append(base + f["path"])
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (dist / f"{out.name}.sha256").write_text(f"{digest}  {out.name}\n")
    rep = {"archive": str(out.relative_to(ROOT)), "version": __version__, "commit": commit, "sha256": digest, "bytes": out.stat().st_size,
           "n_files": len(names), "zip_integrity": bad is None, "missing_required": missing, "forbidden_files": forbidden,
           "bundle_checksum_failures": problems}
    # the static preview, zipped, only when it was built from this exact commit
    prev = dist / "preview"
    pst = prev / "data" / "status.json"
    if pst.exists():
        built = json.loads(pst.read_text()).get("commit", "")
        if built and commit.startswith(built):
            pz = dist / f"skytrace-preview-{__version__}.zip"
            with zipfile.ZipFile(pz, "w", zipfile.ZIP_DEFLATED) as z:
                for f in sorted(p for p in prev.rglob("*") if p.is_file()):
                    zi = zipfile.ZipInfo(f"skytrace-preview-{__version__}/{f.relative_to(prev)}", (2020, 1, 1, 0, 0, 0))
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(zi, f.read_bytes())
            pd = hashlib.sha256(pz.read_bytes()).hexdigest()
            (dist / f"{pz.name}.sha256").write_text(f"{pd}  {pz.name}\n")
            rep["preview"] = {"archive": str(pz.relative_to(ROOT)), "sha256": pd, "bytes": pz.stat().st_size, "built_from_commit": built}
        else:
            rep["preview"] = {"skipped": f"dist/preview was built from {built or 'an unknown commit'}, not {commit[:7]}; rebuild it first"}
    (dist / f"RELEASE_MANIFEST-{__version__}.json").write_text(json.dumps(rep, indent=2))
    (dist / "RELEASE_MANIFEST.json").write_text(json.dumps(rep, indent=2))
    ok = bad is None and not missing and not forbidden and not problems
    print(json.dumps(rep, indent=2))
    print("RELEASE OK" if ok else "RELEASE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
