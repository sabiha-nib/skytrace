"""One command to check that this copy of Skytrace is complete and working.

  python scripts/verify.py              # dependencies, configuration, secrets, bundles, checksums, tests
  python scripts/verify.py --no-tests   # skip the test suite
  python scripts/verify.py --e2e        # also run the browser acceptance test (needs Playwright + Chromium)

Writes data/verification_report.json. Exit status 0 only if every required check passes.
Warnings (e.g. astropy missing, no archive data yet) do not fail verification but are listed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

REQUIRED = ["numpy", "scipy", "requests", "pydantic", "starlette", "uvicorn"]
OPTIONAL = {"astropy": "preferred FITS/WCS reader; the native reader is used without it",
            "playwright": "needed only for the browser acceptance test"}
SECRET_PATTERNS = [re.compile(r"(?:META|MODEL)_API_KEY\s*=\s*['\"]?[A-Za-z0-9_\-]{12,}"), re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
                   re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{24,}")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--e2e", action="store_true")
    a = ap.parse_args()
    checks, warnings = [], []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'}  {name}{': ' + detail if detail else ''}")

    def warn(msg):
        warnings.append(msg)
        print(f"WARN  {msg}")

    check("python >= 3.11", sys.version_info >= (3, 11), platform.python_version())
    versions = {}
    for m in REQUIRED:
        try:
            versions[m] = getattr(importlib.import_module(m), "__version__", "?")
            check(f"import {m}", True, versions[m])
        except ImportError as e:
            check(f"import {m}", False, str(e))
    for m, why in OPTIONAL.items():
        try:
            versions[m] = getattr(importlib.import_module(m), "__version__", "installed")
        except ImportError:
            warn(f"{m} not installed ({why})")

    try:
        cfg = json.loads((ROOT / "config" / "targets.json").read_text())
        ids = [t["target_id"] for t in cfg["targets"]]
        check("config/targets.json", len(ids) == len(set(ids)) and all(t.get("simbad_id") for t in cfg["targets"]), f"{len(ids)} targets")
    except Exception as e:
        check("config/targets.json", False, str(e))

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split() if (ROOT / ".git").exists() else \
        [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    check(".env not tracked", ".env" not in tracked)
    leaks = []
    for f in tracked:
        p = ROOT / f
        if p.suffix in (".fits", ".png") or not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if f != "scripts/verify.py" and any(r.search(text) for r in SECRET_PATTERNS):
            leaks.append(f)
    check("no API keys in tracked files", not leaks, ", ".join(leaks))

    from skytrace import bundle as bmod
    results = [bmod.verify(d) for d in bmod.find_bundles()]
    for r in results:
        check(f"bundle {r['target_id']} ({r['kind']})", r["ok"],
              f"{r.get('n_files')} files, {r.get('total_bytes', 0) / 1e6:.1f} MB" + ("" if r["ok"] else "; " + "; ".join(r["problems"][:3])))
    n_archive = sum(r["kind"] == "archive" and r["ok"] for r in results)

    # static preview build (if present): every file matches its manifest, and it carries no secrets
    pm = ROOT / "dist" / "preview" / "PREVIEW_MANIFEST.json"
    if pm.exists():
        man = json.loads(pm.read_text())
        import hashlib
        bad = [f["path"] for f in man["files"] if not (ROOT / "dist" / "preview" / f["path"]).is_file()
               or hashlib.sha256((ROOT / "dist" / "preview" / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
        leaks = [f["path"] for f in man["files"] if f["path"].endswith((".js", ".json", ".html", ".md")) and
                 any(r.search((ROOT / "dist" / "preview" / f["path"]).read_text(errors="ignore")) for r in SECRET_PATTERNS)]
        check("static preview build", not bad and not leaks,
              f"{len(man['files'])} files match PREVIEW_MANIFEST.json" if not bad and not leaks else f"mismatch {bad[:3]} secrets {leaks[:3]}")
    else:
        warn("no static preview build (python scripts/build_static.py)")

    # synthetic fixtures regenerate byte-identically from the package generator
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_synthetic_fixtures.py"), "--check"], cwd=ROOT,
                       capture_output=True, text=True)
    check("synthetic fixtures reproducible", r.returncode == 0, " ".join(r.stdout.split()))

    # every bundle: analysis record traces to unchanged files and re-runs to the same hash (PROVCHECK-1)
    from skytrace import analysis
    from skytrace.provenance_check import verify_record
    for d in bmod.find_bundles():
        try:
            pc = verify_record(analysis.run(bmod.load(d)).to_dict(), d, rerun=True)
            failed = [c["id"] for c in pc["checks"] if not c["ok"]]
            check(f"provenance {d.name}", pc["ok"], f"{len(pc['checks'])} checks" + (f"; failed {failed}" if failed else ""))
        except Exception as e:  # noqa: BLE001
            check(f"provenance {d.name}", False, f"{type(e).__name__}: {e}")
    if not n_archive:
        warn("no verified archive (real SPHEREx) bundles present: run `python scripts/acquire_targets.py --all` on a networked machine")
    from skytrace.archive.products import astropy_available
    from skytrace.ai.meta_client import MetaConfig
    if not MetaConfig.from_env().api_key:
        warn("no Meta API key configured: the copilot uses the local deterministic assistant")
    smoke = ROOT / "data" / "meta_smoke_test.json"
    if not smoke.exists():
        warn("Meta API smoke test has never been run (python scripts/meta_smoke_test.py)")

    if not a.no_tests:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/unit", "tests/integration",
                            "tests/robustness"],
                           cwd=ROOT, capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["no output"])[-1]
        check("unit + integration + robustness tests", r.returncode == 0, last)
        if a.e2e:
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "e2e", "tests/e2e"],
                               cwd=ROOT, capture_output=True, text=True)
            check("browser acceptance test", r.returncode == 0, (r.stdout.strip().splitlines() or ["no output"])[-1])

    ok = all(c["ok"] for c in checks)
    from skytrace.provenance import utc_now_iso
    rep = {"checked_at": utc_now_iso(), "ok": ok, "python": platform.python_version(), "versions": versions,
           "fits_reader": "astropy" if astropy_available() else "native", "checks": checks, "warnings": warnings,
           "archive_bundles": n_archive, "synthetic_bundles": sum(r["kind"] == "synthetic" for r in results)}
    out = ROOT / "data" / "verification_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2))
    print(f"\n{'VERIFIED' if ok else 'NOT VERIFIED'}: {sum(c['ok'] for c in checks)}/{len(checks)} checks passed, {len(warnings)} warning(s). Report: {out.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
