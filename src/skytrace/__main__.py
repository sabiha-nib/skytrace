"""Command-line entry point.

  python -m skytrace serve [--host 127.0.0.1] [--port 8600]
  python -m skytrace verify
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(prog="skytrace")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="start the application")
    s.add_argument("--host", default=os.environ.get("SKYTRACE_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("SKYTRACE_PORT", "8600")))
    sub.add_parser("verify", help="check dependencies, bundles, checksums, configuration and tests")
    a = ap.parse_args()
    if a.cmd == "serve":
        _load_dotenv()
        import uvicorn
        print(f"SKYTRACE on http://{a.host}:{a.port}  (OFFLINE={os.environ.get('OFFLINE', '0')})")
        uvicorn.run("skytrace.server.app:app", host=a.host, port=a.port, log_level="info")
        return 0
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "verify.py")])


def _load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE lines); existing environment variables win."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


if __name__ == "__main__":
    raise SystemExit(main())
