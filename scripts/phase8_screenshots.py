"""Take the Phase 8 screenshots from the static preview (dist/preview) into docs/screenshots/phase8-*.png.

    python scripts/phase8_screenshots.py

Serves dist/preview locally, opens it in Chromium (Playwright), loads the synthetic target syn-var-1 and captures each
Phase 8 workspace at desktop width, plus the reasoning graph and the compiler at phone width. Every image shows synthetic test
data, labelled as such by the interface. Console errors are collected and reported; the script fails if there are any.
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
    errors = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/index.html#/lab?target=syn-var-1")
            pg.locator(".outcome").first.wait_for(timeout=60000)
            pg.click(".level-switch button[data-level=research]")
            pg.wait_for_timeout(600)

            def snap(name):
                pg.wait_for_timeout(500)
                pg.screenshot(path=str(OUT / f"phase8-{name}.png"))
                print("wrote", f"phase8-{name}.png")

            def shot(ws, ready, name, before=None):
                pg.click(f".nav button[data-ws={ws}]")
                if before:
                    before()
                loc = pg.locator(ready).first
                loc.wait_for(timeout=60000)
                loc.scroll_into_view_if_needed()
                snap(name)

            shot("reasoning", ".epi-node", "reasoning-graph")
            pg.click("[data-rtab-epi=lineage]")
            pg.locator(".lin-stage").nth(8).wait_for(timeout=30000)
            snap("lineage-x")
            pg.click("[data-rtab-epi=graph]")
            shot("compiler", "#compile-outcome", "scientific-compiler")
            pg.click("[data-ctab=genome]")
            pg.click("[data-method=PAIRDIFF-2]")
            pg.locator("#method-detail h3").wait_for()
            snap("method-genome")
            pg.click("[data-ctab=compile]")
            shot("claims", ".kb-item", "knowledge-boundary")
            pg.click("[data-cltab=stress]")
            pg.locator("#cx-table tbody tr").first.wait_for()
            snap("claim-stress-test")
            pg.click("[data-cltab=blindspot]")
            pg.locator("#blind-table tbody tr").first.wait_for()
            snap("blindspots")
            pg.click("[data-cltab=boundary]")
            shot("debugger", "#dbg-panel", "scientific-debugger")
            pg.click("[data-dtab=diff]")
            pg.locator("#diff-run").wait_for(timeout=30000)
            pg.select_option("#diff-b", index=1)
            pg.click("#diff-run")
            pg.locator("#diff-earliest").wait_for(timeout=30000)
            pg.locator("#diff-earliest").scroll_into_view_if_needed()
            snap("differential-debugging")
            pg.click("[data-dtab=repro]")
            pg.click("#rx-run")
            pg.locator("#rx-verdict").wait_for(timeout=60000)
            snap("reproduction")
            pg.click("[data-dtab=inspect]")
            shot("models", ".models-table", "model-arena")
            shot("uflow", "[data-unode]", "uncertainty-flow")
            shot("future", "#future-validation", "futurelab")
            shot("decide", "#nx-list .nx-item", "next-steps")
            pg.click("[data-qtab-epi=questions]")
            pg.locator("#qf-list .nx-item").first.wait_for()
            snap("question-forge")
            pg.click("[data-qtab-epi=next]")
            shot("negative", "#neg-table tbody tr", "negative-space")

            def check():
                pg.click("#integ-run")
            shot("integrity", "#integ-outcome", "integrity-firewall", check)
            shot("protocol", "#pr-question", "protocol")
            shot("argue", "#arg-claim-ref", "reasoning-lab")
            shot("knowledge", "#vault-table", "evidence-vault", lambda: pg.click("[data-ktab=vault]"))
            pg.click("[data-ktab=search]")
            shot("review", "[data-perspective]", "review-board", lambda: pg.click("[data-rtab=board]"))
            pg.click("[data-rtab=review]")
            pg.set_viewport_size({"width": 390, "height": 844})
            shot("reasoning", ".epi-node", "reasoning-graph-mobile")
            shot("compiler", "#compile-outcome", "scientific-compiler-mobile")
            b.close()
    finally:
        srv.terminate()
    if errors:
        print("console errors:", errors)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
