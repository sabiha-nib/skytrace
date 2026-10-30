"""Take the Phase 6 screenshots from the static preview (dist/preview) into docs/screenshots/phase6-*.png.

    python scripts/phase6_screenshots.py

Serves dist/preview locally, opens it in Chromium (Playwright), loads the synthetic target syn-var-1 and captures each
Phase 6 workspace at desktop width, plus the Command Center at phone width. Every image shows synthetic test data,
labelled as such by the interface.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main() -> int:
    from playwright.sync_api import sync_playwright
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(ROOT / "dist" / "preview"), "--bind", "127.0.0.1", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.goto(f"http://127.0.0.1:{port}/index.html#/command?target=syn-var-1")
            pg.locator("#command-body h3").first.wait_for(timeout=60000)
            pg.click(".level-switch button[data-level=research]")
            pg.wait_for_timeout(600)

            def shot(ws, ready, name, before=None):
                pg.click(f".nav button[data-ws={ws}]")
                if before:
                    before()
                pg.locator(ready).first.wait_for(timeout=60000)
                pg.wait_for_timeout(500)
                pg.screenshot(path=str(OUT / f"phase6-{name}.png"))
                print("wrote", f"phase6-{name}.png")

            shot("command", "#command-body h3", "command-center")

            def plan():
                pg.locator("#plan-question").wait_for()
                pg.fill("#plan-question", "Could this source have changed between the two recorded observation epochs?")
                pg.click("#plan-go")
            shot("planner", ".plan-step", "planner", plan)
            shot("quality", ".dq-row", "data-quality")
            pg.locator("[data-qtab=matrix]").click()
            pg.locator(".matrix-svg").wait_for()
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(OUT / "phase6-compatibility-matrix.png"))
            print("wrote phase6-compatibility-matrix.png")
            shot("graph", ".graph-svg .node", "evidence-ledger", lambda: None)
            pg.locator("[data-ltab=claims]").click()
            pg.locator("#claim-detail").wait_for()
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(OUT / "phase6-claim-inspector.png"))
            print("wrote phase6-claim-inspector.png")
            shot("radar", ".radar-item", "discovery-radar")
            shot("experiments", "[data-template]", "experiment-studio")
            shot("notebook", "#nb-search", "notebook")
            pg.set_viewport_size({"width": 390, "height": 844})
            shot("command", "#command-body h3", "command-center-mobile")
            b.close()
    finally:
        srv.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
