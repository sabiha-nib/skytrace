"""Take the Phase 7 screenshots from the static preview (dist/preview) into docs/screenshots/phase7-*.png.

    python scripts/phase7_screenshots.py

Serves dist/preview locally, opens it in Chromium (Playwright), loads the synthetic target syn-var-1 and captures each
Phase 7 workspace at desktop width, plus the Discovery Horizon at phone width. Every image shows synthetic test data or
generated scenarios, labelled as such by the interface.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
sys.path.insert(0, str(ROOT / "scripts"))
from phase6_screenshots import free_port  # noqa: E402


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
            pg.goto(f"http://127.0.0.1:{port}/index.html#/lab?target=syn-var-1")
            pg.locator(".outcome").first.wait_for(timeout=60000)
            pg.click(".level-switch button[data-level=research]")
            pg.wait_for_timeout(600)

            def snap(name):
                pg.wait_for_timeout(500)
                pg.screenshot(path=str(OUT / f"phase7-{name}.png"))
                print("wrote", f"phase7-{name}.png")

            def shot(ws, ready, name, before=None):
                pg.click(f".nav button[data-ws={ws}]")
                if before:
                    before()
                loc = pg.locator(ready).first
                loc.wait_for(timeout=60000)
                loc.scroll_into_view_if_needed()      # show the result itself, not the page header
                snap(name)

            shot("horizon", ".horizon-card", "discovery-horizon")
            pg.locator("[data-hview=map]").click()
            pg.locator("svg.hz-map").wait_for()
            snap("opportunity-map")
            pg.locator("[data-hview=cards]").click()
            shot("counterfactual", ".cf-result", "counterfactual-lab",
                 lambda: pg.locator(".cf-preset", has_text="Brightness without reference calibration").click())
            shot("adversarial", ".asl-item", "adversarial-lab")
            pg.locator("[data-atab=ranking]").click()
            pg.locator("#info-table tbody tr").first.wait_for()
            snap("test-ranking")
            pg.locator("[data-atab=causal]").click()
            pg.locator(".causal-list li").first.wait_for()
            snap("causality-workbench")
            shot("synthetic", ".syn-result", "synthetic-observatory", lambda: (pg.locator("#syn-run").wait_for(), pg.click("#syn-run")))
            pg.locator("[data-stab=design]").click()
            pg.click("#design-run")
            pg.locator("#design-result tbody tr").first.wait_for(timeout=60000)
            pg.locator("#design-result").scroll_into_view_if_needed()
            snap("observation-design")

            def propose():
                pg.locator("#ap-objective").fill("Challenge my interpretation of the brightness change.")
                pg.click("#ap-propose")
            shot("autopilot", "#ap-steps tbody tr", "autopilot", propose)
            shot("atlas", "#atlas-table tbody tr", "cosmic-atlas")
            shot("knowledge", "#ka-search", "knowledge-atlas")
            pg.locator("[data-ktab=twins]").click()
            pg.locator("#twin-integrity").wait_for(timeout=30000)
            snap("twins")
            shot("review", ".review-list li", "review-room")
            pg.locator("[data-rtab=repro]").click()
            pg.click("#repro-run")
            pg.locator("#review-body h3", has_text="Verdict").wait_for(timeout=60000)
            pg.locator("#review-body h3", has_text="Verdict").scroll_into_view_if_needed()
            snap("reproducibility")
            pg.locator("[data-rtab=story]").click()
            pg.locator(".story-ch").first.wait_for()
            snap("story")
            pg.set_viewport_size({"width": 390, "height": 844})
            shot("horizon", ".horizon-card", "discovery-horizon-mobile", lambda: None)
            b.close()
    finally:
        srv.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
