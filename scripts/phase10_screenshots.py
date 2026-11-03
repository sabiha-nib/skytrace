"""Take the Phase 10 six-language screenshots from the static preview into docs/screenshots/phase10/.

    python scripts/phase10_screenshots.py [--langs en,bn,...]

Serves dist/preview locally and opens it in Chromium (Playwright). For each of the six interface languages it chooses the language
with the selector in the navigation, reloads the page without any URL parameter (the choice must persist), loads the synthetic
target syn-var-1 and captures:

* desktop (1440×900): the investigation, Signal Intelligence, World Model, explanations (Multilingual Research) and Settings;
* tablet (834×1112): World Model (convergence) and the Open Science Gateway;
* phone (390×844): the investigation, the navigation menu, cross-language search and Settings.

On every captured view it records: horizontal page scroll, labels/buttons/headings wider than their box (the same rule as the
Translation Quality Observatory's clipped-text check; screen-reader-only labels are skipped and text truncated on purpose with an
ellipsis is listed separately), navigation labels still in English in another language, the web fonts actually loaded, and
console errors. Results go to docs/screenshots/phase10/checks.json. Every image shows
synthetic test data, labelled as such by the interface. Exit status 1 on a console error, a failed persistence check or a
horizontal page scroll; clipped labels are reported for inspection, not treated as failures.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots" / "phase10"
sys.path.insert(0, str(ROOT / "scripts"))
from phase6_screenshots import free_port  # noqa: E402

LANGS = ["en", "bn", "hi", "es", "fr", "de"]
SIZES = {"desktop": (1440, 900), "tablet": (834, 1112), "phone": (390, 844)}
VIEWS = {
    "desktop": ["lab", "signal", "world", "explain", "settings"],
    "tablet": ["convergence", "gateway"],
    "phone": ["lab", "menu", "search", "settings"],
}

CHECK_JS = """() => {
  const sel = "button, .nav-h, th, label, .pill, .tabs [role=tab], h1, h2, h3, h4, .kv dt, select";
  const clipped = [], ellipsis = [];
  for (const e of document.querySelectorAll(sel)) {
    if (!e.offsetParent) continue;
    const cs = getComputedStyle(e);
    if (cs.overflowX === "auto" || cs.overflowX === "scroll") continue;
    if (e.classList.contains("sr-only") || cs.clip !== "auto") continue;
    if (e.scrollWidth > e.clientWidth + 1 && cs.textOverflow === "ellipsis") { ellipsis.push(`${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}: ${e.textContent.trim().slice(0, 50)}`); continue; }
    if (e.scrollWidth > e.clientWidth + 1) clipped.push(`${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}: ${e.textContent.trim().slice(0, 50)}`);
  }
  const lang = document.documentElement.lang;
  const english = [];
  if (lang !== "en") for (const b of document.querySelectorAll(".nav button[data-ws]")) {
    if (b.dataset.wsEn && b.textContent.trim() === b.dataset.wsEn.trim()) english.push(b.dataset.wsEn);
  }
  return {
    lang,
    hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    clipped,
    ellipsis,
    nav_still_english: english,
    fonts_loaded: [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family.replaceAll('"', "")),
  };
}"""


def shrink(path: Path) -> None:
    """Store the screenshot with a 256-colour palette (about a third of the size; text stays sharp, no dithering)."""
    from PIL import Image
    with Image.open(path) as im:
        q = im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(path, optimize=True)


def open_nav(pg):
    if pg.locator(".nav button[data-ws=lab]").first.is_visible():
        return
    pg.locator("#nav-toggle, .nav-toggle, button[aria-controls=nav]").first.click()
    pg.wait_for_timeout(300)


def goto_ws(pg, ws):
    open_nav(pg)
    pg.locator(f".nav button[data-ws={ws}]").first.click()
    pg.locator(f"#ws-{ws}").wait_for(state="visible", timeout=60000)
    pg.wait_for_timeout(1200)
    pg.evaluate("document.querySelector('main')?.scrollTo(0, 0); window.scrollTo(0, 0)")


def show(pg, view):
    if view == "lab":
        goto_ws(pg, "lab")
        pg.locator(".outcome").first.wait_for(timeout=60000)
    elif view == "signal":
        goto_ws(pg, "signal")
        pg.locator("#sig-selection").first.wait_for(timeout=60000)
    elif view == "world":
        goto_ws(pg, "world")
        pg.locator("[data-world-tab=world]").first.click()
        pg.locator("#wq-count").wait_for(timeout=60000)
    elif view == "convergence":
        goto_ws(pg, "world")
        pg.locator("[data-world-tab=convergence]").first.click()
        pg.wait_for_timeout(800)
    elif view == "gateway":
        goto_ws(pg, "gateway")
        pg.locator("[data-gw-tab=reports]").first.click()
        pg.locator("#report-langs").wait_for(timeout=60000)
    elif view == "explain":
        goto_ws(pg, "languages")
        pg.locator("[data-lang-tab=explain]").first.click()
        pg.locator(".explain-layer").first.wait_for(timeout=60000)
    elif view == "search":
        goto_ws(pg, "languages")
        pg.locator("[data-lang-tab=search]").first.click()
        sample = pg.locator("#xs-samples button, [data-xs-sample]").first
        if sample.count():
            sample.click()
        else:
            pg.fill("#xs-input", "proper motion")
        pg.wait_for_timeout(800)
    elif view == "menu":
        goto_ws(pg, "lab")
        if not pg.locator(".nav button[data-ws=lab]").first.is_visible():
            pg.locator("#nav-toggle, .nav-toggle, button[aria-controls=nav]").first.click()
            pg.wait_for_timeout(400)
    elif view == "settings":
        goto_ws(pg, "lab")
        pg.locator("#settings-btn").click()
        pg.locator("#settings-body select, #settings-body input").first.wait_for(timeout=10000)
    pg.wait_for_timeout(500)


def close_overlays(pg):
    if pg.locator("#settings").is_visible():
        pg.locator("#settings-close").click()
    pg.keyboard.press("Escape")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(LANGS))
    args = ap.parse_args()
    langs = args.langs.split(",")
    from playwright.sync_api import sync_playwright
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(ROOT / "dist" / "preview"), "--bind", "127.0.0.1", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    OUT.mkdir(parents=True, exist_ok=True)
    results, errors, failures = {}, [], []
    base = f"http://127.0.0.1:{port}/index.html"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for lang in langs:
                ctx = b.new_context(viewport={"width": 1440, "height": 900})
                pg = ctx.new_page()
                pg.on("console", lambda m, l=lang: errors.append(f"[{l}] {m.text}") if m.type == "error" else None)
                pg.on("pageerror", lambda e, l=lang: errors.append(f"[{l}] {e}"))
                # choose the language with the selector, then reload without a URL parameter: the choice must persist
                pg.goto(f"{base}#/lab?target=syn-var-1")
                pg.locator(".outcome").first.wait_for(timeout=60000)
                pg.select_option("#lang-select", lang)
                pg.wait_for_timeout(800)
                pg.goto(f"{base}#/lab?target=syn-var-1")
                pg.reload()
                pg.locator(".outcome").first.wait_for(timeout=60000)
                pg.wait_for_timeout(1500)
                persisted = pg.evaluate("[document.documentElement.lang, document.querySelector('#lang-select').value, localStorage.getItem('skytrace.lang')]")
                if persisted[0] != lang or persisted[1] != lang:
                    failures.append(f"{lang}: language did not persist across reload: {persisted}")
                results.setdefault(lang, {})["persisted"] = persisted
                pg.locator(".level-switch button[data-level=research]").first.click()
                pg.wait_for_timeout(600)
                for size, (w, h) in SIZES.items():
                    pg.set_viewport_size({"width": w, "height": h})
                    pg.wait_for_timeout(500)
                    for view in VIEWS[size]:
                        close_overlays(pg)
                        try:
                            show(pg, view)
                        except Exception as e:  # noqa: BLE001 - recorded and reported, never hidden
                            failures.append(f"{lang} {size} {view}: {e.__class__.__name__}: {str(e)[:200]}")
                            continue
                        name = f"{lang}-{size}-{view}.png"
                        pg.screenshot(path=str(OUT / name))
                        shrink(OUT / name)
                        chk = pg.evaluate(CHECK_JS)
                        results[lang][f"{size}/{view}"] = chk
                        if chk["hscroll"]:
                            failures.append(f"{lang} {size} {view}: horizontal page scroll")
                        print(f"wrote {name}: clipped={len(chk['clipped'])} nav_en={chk['nav_still_english']} ellipsis={len(chk['ellipsis'])} fonts={sorted(set(chk['fonts_loaded']))}")
                    close_overlays(pg)
                ctx.close()
            b.close()
    finally:
        srv.terminate()
    (OUT / "checks.json").write_text(json.dumps({"results": results, "console_errors": errors, "failures": failures}, ensure_ascii=False, indent=1) + "\n")
    for f in failures:
        print("FAIL", f)
    for e in errors:
        print("console error", e)
    return 1 if (failures or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
