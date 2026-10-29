"""Start SKYTRACE with one command:  python run.py   (options: --host, --port; see python run.py --help)

Equivalent to `python -m skytrace serve` without needing `pip install -e .`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from skytrace.__main__ import main  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1].startswith("-"):
        sys.argv.insert(1, "serve")
    raise SystemExit(main())
