"""Every visible control, in both delivery modes (Playwright + Chromium, offline).

server: `python run.py` with OFFLINE=1 (the full application).
static: `dist/preview/` served by a plain file server with no backend (the previewable build). The test rebuilds
        the interface files (`build_static.py --web-only`) and, if no recorded data exist, the whole preview.

Each control must either do what it says or be disabled with an explanation. Network requests are recorded and
must stay on the local origin. Run: pytest -m e2e tests/e2e
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

pw = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.e2e
ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "screenshots"
NOPROXY = {"http": None, "https": None}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def wait_up(url, proc):
    for _ in range(120):
        try:
            if requests.get(url, timeout=1, proxies=NOPROXY).ok:
                return
        except requests.RequestException:
            time.sleep(0.25)
    proc.kill()
    raise RuntimeError(f"{url} did not start")


@pytest.fixture(scope="module", params=["server", "static"])
def app(request, tmp_path_factory):
    port = free_port()
    env = {**os.environ, "OFFLINE": "1", "SKYTRACE_RECORDS_DIR": str(tmp_path_factory.mktemp("rec")),
           "META_API_KEY": "", "MODEL_API_KEY": "", "NO_PROXY": "127.0.0.1,localhost"}
    if request.param == "server":
        proc = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--port", str(port)], env=env, cwd=ROOT,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}/"
        wait_up(base + "api/status", proc)
    else:
        prev = ROOT / "dist" / "preview"
        mode = ["--web-only"] if (prev / "data" / "status.json").exists() else []
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_static.py"), *mode], cwd=ROOT, env=env,
                       check=True, capture_output=True, timeout=900)
        proc = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(prev), "--bind", "127.0.0.1", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}/"
        wait_up(base + "index.html", proc)
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        pg = ctx.new_page()
        pg.errors, pg.requests = [], []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
        pg.on("request", lambda r: pg.requests.append(r.url))
        pg.base, pg.mode = base, request.param
        yield pg
        b.close()
    proc.terminate()
    proc.wait(10)


def changed(locator, action):
    """True if the element's rendering changes after action()."""
    before = locator.screenshot()
    action()
    locator.page.wait_for_timeout(150)
    return locator.screenshot() != before


def test_a_load_and_run(app):
    app.goto(app.base + "#/explorer?target=syn-var-1")
    app.locator("#data-pill", has_text="Synthetic test data").wait_for()
    if app.mode == "static":
        app.locator("#preview-pill", has_text="Static preview").wait_for()
        app.locator("#preview-note summary").click()
        app.locator("#preview-note p", has_text="no server, archive or language model is contacted").wait_for()
        assert app.locator("#offline-pill").is_hidden()
    app.click("#run-btn")
    app.locator("#run-btn", has_text="Re-run analysis").wait_for(timeout=120000)
    app.locator("#obs-meta", has_text="Aperture flux").wait_for(timeout=30000)


def test_b_explorer_controls(app):
    view = app.locator("#explorer-body .viewer").first
    assert changed(view, lambda: app.select_option("select[aria-label='Display stretch']", "linear"))
    assert changed(view, lambda: app.locator("input[aria-label='White point percentile']").fill("95"))
    assert changed(view, lambda: app.locator("input[aria-label='Black point percentile']").fill("5"))
    assert changed(view, lambda: app.click("button[aria-label='Zoom in']"))
    assert changed(view, lambda: app.click("button[aria-label='Zoom out']"))
    app.click("button[aria-label='Zoom in']")
    assert changed(view, lambda: app.click("#explorer-body button:has-text('Reset view')"))
    for lbl in ["Catalogue position", "Measured centroid", "Reference stars", "Rejected pixels"]:
        assert changed(view, lambda: app.locator("#explorer-body label", has_text=lbl).first.click()), lbl
    count = app.locator("#obs-count")
    app.select_option("select[aria-label='Filter by detector']", "3")
    assert count.text_content().startswith("9 ") or count.text_content().startswith("8 ")
    app.select_option("select[aria-label='Filter by status']", "excluded")
    app.locator("#explorer-body tbody tr").first.click()
    app.locator("#toast", has_text="Excluded at selection").wait_for()
    app.select_option("select[aria-label='Filter by detector']", "all")
    app.select_option("select[aria-label='Filter by status']", "all")
    first = app.locator("#explorer-body tbody tr[aria-selected=true]").get_attribute("data-key")
    app.locator("#explorer-body .viewer").first.click()
    app.keyboard.press("ArrowRight")
    app.wait_for_timeout(300)
    assert app.locator("#explorer-body tbody tr[aria-selected=true]").get_attribute("data-key") != first
    app.keyboard.press("ArrowLeft")
    app.wait_for_timeout(300)
    assert app.locator("#explorer-body tbody tr[aria-selected=true]").get_attribute("data-key") == first


def test_c_time_machine_controls(app):
    app.click("#obs-meta button:has-text('Compare in Time Machine')")
    app.locator(".nav button[data-ws=time][aria-current=page]").wait_for()
    app.locator("#tm-banner", has_text="Wavelength-matched pair").wait_for(timeout=30000)
    app.locator("#tm-details", has_text="Registration").wait_for()
    reg = app.locator("#tm-details dd").nth(2).text_content()
    assert "plate solutions" in reg
    app.locator("button[aria-pressed]", has_text="Pause").click()
    app.locator("button[aria-pressed=false]", has_text="Play").wait_for()
    app.locator("input[aria-label='Blink interval']").fill("400")
    app.locator(".segmented button", has_text="Fade").click()
    view = app.locator("#time-body .viewer").first
    assert changed(view, lambda: app.locator("input[aria-label='Fade between A and B']").fill("0.9"))
    app.locator(".segmented button", has_text="Side by side").click()
    assert app.locator("#time-body .viewer").count() == 2
    app.locator(".segmented button", has_text="Difference").click()
    app.locator("#time-body .caption", has_text="B − A").wait_for()
    app.locator("#time-body label", has_text="Same display scale").click()
    app.locator(".segmented button", has_text="Blink").click()
    app.locator(".partner", has_text="Brightness comparison unavailable").first.click()
    app.locator("#tm-banner", has_text="Not comparable for brightness").wait_for()
    assert app.locator(".segmented button", has_text="Difference").is_disabled()
    ask = app.locator("#tm-details button", has_text="Ask the copilot about this pair")
    if app.mode == "static":
        assert ask.is_disabled()
        app.locator("#tm-details", has_text="Not available in the static preview").wait_for()
    else:
        assert ask.is_enabled()


def test_d_lab_controls(app):
    app.click(".nav button[data-ws=lab]")
    app.locator(".outcome .sensitivity").first.wait_for()
    app.locator(".outcome dt", has_text="Measured proper motion (mas/yr)").first.wait_for()
    with app.expect_download() as d:
        app.click("button:has-text('Download report (Markdown)')")
    path = d.value.path()
    text = Path(path).read_text()
    assert d.value.suggested_filename.endswith(".md") and "SYNTHETIC" in text.upper()
    app.locator(".outcome summary", has_text="Criteria").first.click()
    app.locator(".outcome li", has_text="5").first.wait_for()
    app.locator(".tabs button", has_text="Re-run & compare").click()
    if app.mode == "static":
        app.locator("#preset-select option", has_text="aperture 2.5 px").wait_for(state="attached")
        app.select_option("#preset-select", label="aperture 2.5 px")
        app.click("#preset-run")
    else:
        app.locator("label", has_text="Aperture radius").locator("input").fill("2.5")
        app.locator("button", has_text="Re-run analysis").last.click()
    app.locator(".diff-table td.changed").first.wait_for(timeout=120000)
    app.locator("#stability-run").click()
    app.locator("#stability-out", has_text="Motion: stable").wait_for(timeout=240000)
    if app.mode == "static":   # a parameter set that was not precomputed is refused, not imitated
        app.click("#run-btn")
        app.locator("#run-btn", has_text="Re-run analysis").wait_for(timeout=60000)


def test_e_graph_controls(app):
    app.click(".nav button[data-ws=graph]")
    app.locator(".graph-svg .node[data-id='claim:variability']").click()
    app.locator("#graph-detail", has_text="Traced observations").wait_for()
    obs = app.locator(".graph-svg .node[data-id^='obs:']").first
    obs.focus()
    app.keyboard.press("Enter")
    app.locator("#graph-detail dt", has_text="SHA-256 (manifest)").wait_for()
    app.locator(".graph-svg .node[data-id^='method:PAIRDIFF-2']").wait_for(state="attached")
    app.locator(".graph-svg .node[data-id^='method:EPHEM-AA-LP-1']").wait_for(state="attached")
    app.locator("#graph-detail button", has_text="Open in Sky Explorer").click()
    app.locator(".nav button[data-ws=explorer][aria-current=page]").wait_for()


def test_f_back_forward(app):
    app.click(".nav button[data-ws=lab]")
    app.click(".nav button[data-ws=records]")
    app.go_back()
    app.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()
    app.go_forward()
    app.locator(".nav button[data-ws=records][aria-current=page]").wait_for()


def test_g_records_controls(app, tmp_path):
    app.click(".nav button[data-ws=records]")
    app.fill("input[aria-label='Investigation name']", f"controls {app.mode}")
    app.click("button:has-text('Save investigation')")
    row = app.locator("tr", has_text=f"controls {app.mode}")
    row.wait_for()
    if app.mode == "static":
        app.locator("#storage-note", has_text="this browser only").wait_for()
    with app.expect_download() as d:
        app.click("#export-record")
    exported = tmp_path / "rec.json"
    d.value.save_as(exported)
    rec = json.loads(exported.read_text())
    assert rec["content_hash"] and rec["parameters"]["bundle"] == "syn-var-1"
    app.set_input_files("#import-file", str(exported))
    app.locator("#toast", has_text="Imported").wait_for(timeout=30000)
    app.locator("#toast", has_text="content hash verified").wait_for()
    app.locator("td", has_text="imported").first.wait_for()
    bad = tmp_path / "bad.json"
    rec["events"][0]["detail"] = "edited"
    bad.write_text(json.dumps(rec))
    app.set_input_files("#import-file", str(bad))
    app.locator("#toast", has_text="Import refused").wait_for(timeout=30000)
    check = row.locator("button", has_text="Check" if app.mode == "static" else "Replay")
    check.click()
    row.get_by_text("identical content hash" if app.mode == "server" else "matches the precomputed result").wait_for(timeout=120000)
    row.locator("button", has_text="Open").click()
    app.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()
    app.click(".nav button[data-ws=records]")
    row = app.locator("tr", has_text=f"controls {app.mode}").first
    row.locator("button", has_text="Delete").click()
    row.locator("button", has_text="Confirm delete").click()
    app.locator("#toast", has_text="Deleted").wait_for()


def test_h_copilot_controls(app):
    app.locator("#suggestions .chip").first.click()
    app.locator(".msg.bot .mode", has_text="Local assistant").first.wait_for(timeout=60000)
    ans = app.locator(".msg.bot .answer").last.text_content()
    assert "synthetic" in ans.lower()
    app.locator(".msg.bot details summary", has_text="Tool activity").last.click()
    app.locator(".msg.bot .ev-chip").last.click()
    app.locator(".msg.bot .chips .chip").last.click()
    app.locator(".msg.bot .answer").nth(1).wait_for(timeout=60000)
    app.fill("#ask-input", "Compare SYNTHETIC:SYN11_23:D1 and SYNTHETIC:SYN21_23:D1")
    app.keyboard.press("Enter")
    if app.mode == "static":
        app.locator(".msg.bot .withheld", has_text="questions that name specific observations").wait_for()
    else:
        app.locator(".msg.bot .answer").nth(2).wait_for(timeout=60000)


def test_i_narrow_copilot_overlay_and_escape(app):
    app.set_viewport_size({"width": 820, "height": 1000})
    toggle = app.locator("#copilot-toggle")
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    app.locator("#copilot").wait_for(state="visible")
    app.keyboard.press("Escape")
    app.locator("#copilot").wait_for(state="hidden")
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.click()
    app.click("#copilot-close")
    app.locator("#copilot").wait_for(state="hidden")
    for w, h, name in [(820, 1100, "tablet"), (390, 844, "mobile")]:
        app.set_viewport_size({"width": w, "height": h})
        for ws in ["explorer", "time", "lab", "graph", "records"]:
            app.locator(f".nav button[data-ws={ws}]").click()
            app.wait_for_timeout(300)
            assert app.locator("#main").bounding_box()["width"] <= w
        if app.mode == "static":
            SHOTS.mkdir(parents=True, exist_ok=True)
            app.click(".nav button[data-ws=lab]")
            app.screenshot(path=str(SHOTS / f"preview-{name}-lab.png"), full_page=False)
    app.set_viewport_size({"width": 1440, "height": 900})


def test_j_no_external_requests_no_errors(app):
    if app.mode == "static":
        SHOTS.mkdir(parents=True, exist_ok=True)
        app.click(".nav button[data-ws=time]")
        app.wait_for_timeout(800)
        app.screenshot(path=str(SHOTS / "preview-desktop-time.png"))
    external = [u for u in app.requests if not u.startswith(app.base.rstrip("/")) and not u.startswith(("data:", "blob:"))]
    assert external == [], external
    if app.mode == "static":
        assert not any("/api/" in u for u in app.requests), "the static preview must not call a server API"
    # the only expected console error is the browser's log line for the deliberately refused import (HTTP 400)
    errors = [e for e in app.errors if not (app.mode == "server" and "status of 400" in e)]
    assert errors == [], errors
    assert sum("status of 400" in e for e in app.errors) <= 1
