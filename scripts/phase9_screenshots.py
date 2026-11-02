"""Take the Phase 9 screenshots from the static preview (dist/preview) into docs/screenshots/phase9-*.png.

    python scripts/phase9_screenshots.py

Serves dist/preview locally, opens it in Chromium (Playwright), loads the synthetic target syn-var-1 and captures each of the
twelve Scientific Intelligence panels at desktop width (a tall viewport, because the workspace scrolls inside its own panel),
plus the Unknown Universe and the Integrity Gate at phone width. Every image shows synthetic test data, labelled as such by the
interface. Console errors are collected and reported; the script fails if there are any.
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

PANELS = [("command", "#ic-cards", "command-center"), ("genome", "#gn-fields", "discovery-genome"), ("unknown", "#uk-map", "unknown-universe"),
          ("network", "#net-graph", "multi-discovery-network"), ("adversary", "#adv-counts", "scientific-adversary"), ("causal", "#cl-graph", "causality-lab"),
          ("whatif", "#wi-out, [data-whatif]", "what-if-lab"), ("oracle", "#or-cands", "observation-oracle"), ("cycle", "#cy-steps", "research-cycle"),
          ("memory", "#mem-results", "research-memory"), ("repro", "#rp-manifest", "reproduction-network"), ("gate", "#gt-table", "integrity-gate")]


def main() -> int:
    from playwright.sync_api import sync_playwright
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(ROOT / "dist" / "preview"), "--bind", "127.0.0.1", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width, height, panels, suffix in [(1440, 1700, PANELS, ""), (390, 1500, [x for x in PANELS if x[0] in ("unknown", "gate")], "-mobile")]:
                pg = b.new_page(viewport={"width": width, "height": height})
                pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(f"http://127.0.0.1:{port}/index.html#/lab?target=syn-var-1")
                pg.locator(".outcome").first.wait_for(timeout=60000)
                pg.locator(".level-switch button[data-level=research]").first.click()
                pg.wait_for_timeout(600)
                nav = pg.locator(".nav button[data-ws=intel]")
                if not nav.is_visible():                      # phone width: the navigation is behind the menu button
                    pg.locator("#nav-toggle, .nav-toggle, button[aria-controls=nav]").first.click()
                nav.click()
                pg.locator("#intel-layers").wait_for(timeout=60000)
                for pid, ready, name in panels:
                    pg.locator(f"[data-ipanel={pid}]").first.click()
                    pg.locator(f"#intel-panel[data-panel={pid}]").wait_for(timeout=60000)
                    pg.locator(ready).first.wait_for(timeout=60000)
                    pg.evaluate("document.querySelector('#ws-intel')?.scrollIntoView(); document.querySelector('main')?.scrollTo(0, 0)")
                    pg.wait_for_timeout(500)
                    pg.screenshot(path=str(OUT / f"phase9-{name}{suffix}.png"))
                    print("wrote", f"phase9-{name}{suffix}.png")
                    if width < 500:
                        sw = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                        if sw[0] > sw[1]:
                            errors.append(f"horizontal scroll at {width}px on {pid}: {sw}")
                pg.close()
            b.close()
    finally:
        srv.terminate()
    if errors:
        print("console errors:", *errors, sep="\n  ")
        return 1
    print("no console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
