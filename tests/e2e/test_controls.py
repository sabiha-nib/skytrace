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
           "SKYTRACE_SESSIONS_DIR": str(tmp_path_factory.mktemp("sessions")),
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
    app.locator(".graph-svg .node[data-id='hyp:V-INTRINSIC']").click()
    app.locator("#graph-detail dt", has_text="Recorded tests").wait_for()
    app.locator("#graph-detail button", has_text="Open in the Hypothesis Arena").wait_for()
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
    app.locator("#import-preview", has_text="recomputed in this browser: matches").wait_for(timeout=30000)
    app.click("#import-confirm")
    app.locator("#toast", has_text="Imported").wait_for(timeout=30000)
    app.locator("#toast", has_text="content hash verified").wait_for()
    app.locator("td", has_text="imported").first.wait_for()
    bad = tmp_path / "bad.json"
    rec["events"][0]["detail"] = "edited"
    bad.write_text(json.dumps(rec))
    app.set_input_files("#import-file", str(bad))
    app.locator("#import-preview", has_text="does not match").wait_for(timeout=30000)
    assert app.locator("#import-confirm").is_disabled()          # refused before anything is stored
    app.click("#import-cancel")
    app.locator("#import-preview .import-preview").wait_for(state="detached")
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


def test_j_levels(app):
    app.set_viewport_size({"width": 1440, "height": 900})
    for sel in ["#run-btn", ".level-switch", "#palette-btn"]:     # the top bar fits a 1440 px window
        bb = app.locator(sel).bounding_box()
        assert bb["x"] + bb["width"] <= 1440, sel
    app.click(".level-switch button[data-level=explore]")
    assert app.locator("body").get_attribute("data-level") == "explore"
    app.click(".nav button[data-ws=lab]")
    app.locator("#lab-body .tabs button", has_text="Outcomes").wait_for()
    assert app.locator("#lab-body .tabs button", has_text="Measurements").count() == 0   # explore: fewer views, same results
    app.click(".level-switch button[data-level=research]")
    app.locator("#lab-body .tabs button", has_text="Measurements").wait_for()
    app.click(".nav button[data-ws=discovery]")
    app.locator(".inventory th", has_text="SHA-256").wait_for()
    assert app.locator(".inventory th", has_text="SHA-256").is_visible()
    app.click(".level-switch button[data-level=investigate]")
    assert app.locator(".inventory th", has_text="SHA-256").is_hidden()
    assert app.locator(".level-switch button[data-level=investigate]").get_attribute("aria-pressed") == "true"


def test_k_palette_help_shortcuts(app):
    app.locator("body").click(position={"x": 5, "y": 400})
    app.keyboard.press("Control+k")
    app.locator("#palette").wait_for(state="visible")
    pw.expect(app.locator("#palette-input")).to_be_focused()
    app.keyboard.type("hypothesis arena")
    app.locator("#palette-list li[aria-selected=true]", has_text="Hypothesis Arena").wait_for()
    app.keyboard.press("Enter")
    app.locator("#palette").wait_for(state="hidden")
    app.locator(".nav button[data-ws=arena][aria-current=page]").wait_for()
    app.locator("#palette-btn").click()
    app.locator("#palette").wait_for(state="visible")
    app.keyboard.type("zzzz-no-such-command")
    app.locator("#palette-list li", has_text="No matches").wait_for()
    app.keyboard.press("Escape")
    app.locator("#palette").wait_for(state="hidden")
    pw.expect(app.locator("#palette-btn")).to_be_focused()       # focus returns to the opener
    app.locator("body").click(position={"x": 5, "y": 400})
    app.keyboard.press("?")
    app.locator("#help").wait_for(state="visible")
    app.locator("#help dt", has_text="Wavelength-matched pair").wait_for()
    app.keyboard.press("Escape")
    app.locator("#help").wait_for(state="hidden")
    app.keyboard.press("Alt+1")
    app.locator(".nav button[data-ws=command][aria-current=page]").wait_for()
    app.keyboard.press("Alt+7")                       # investigate level: command, explorer, time, quality, planner, discovery, lab
    app.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()


def test_l_discovery_engine(app):
    app.click(".nav button[data-ws=discovery]")
    app.locator(".engine-head", has_text="DISC-1").wait_for(timeout=30000)
    app.locator(".syn-note", has_text="Synthetic test data").wait_for()
    app.locator(".qitem", has_text="not answerable").first.wait_for()
    app.locator(".qitem", has_text="Does the target move").click()
    app.locator(".qitem[aria-checked=true]", has_text="Does the target move").wait_for()
    app.locator(".plan", has_text="LINFIT").wait_for()
    app.locator(".plan button", has_text="Open the motion fit").click()
    app.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()
    app.locator("#lab-body .tabs button[aria-selected=true]", has_text="Motion").wait_for()
    app.click(".nav button[data-ws=discovery]")
    app.locator(".qitem[aria-checked=true]", has_text="Does the target move").wait_for()   # the question is kept
    n = app.locator(".inventory tbody tr").count()
    app.locator("button", has_text="Show all").click()
    app.wait_for_timeout(200)
    assert app.locator(".inventory tbody tr").count() > n
    app.locator(".next li", has_text="Acquire real SPHEREx observations").wait_for()
    app.locator(".next li", has_text="needs network access").first.wait_for()


def test_m_hypothesis_arena(app):
    app.click(".nav button[data-ws=arena]")
    app.locator(".matrix tbody tr").first.wait_for(timeout=30000)
    app.locator(".matrix th", has_text="V-INTRINSIC").wait_for()
    app.locator(".testbtn").first.click()
    app.locator("#arena-detail dt", has_text="Rule").wait_for()
    assert "%" not in app.locator(".matrix").text_content()      # no probabilities anywhere in the matrix
    app.locator("#arena-body .tabs button", has_text="Motion").click()
    app.locator(".matrix th", has_text="M-REGISTRATION").wait_for()
    app.fill("#hyp-text", "The motion is real and not a registration artefact")
    app.locator(".pick", has_text="M-REGISTRATION").locator("input").check()
    app.click("#hyp-add")
    li = app.locator(".userhyps > li", has_text="not a registration artefact")
    li.wait_for()
    li.locator(".st").first.wait_for()
    li.locator("button", has_text="Remove").click()
    app.locator("#undo-box").wait_for(state="visible")
    assert app.locator(".userhyps > li").count() == 0
    app.locator("#undo-box button", has_text="Undo").click()
    app.locator(".userhyps > li", has_text="not a registration artefact").wait_for()


def test_n_uncertainty_and_figure_export(app):
    app.click(".nav button[data-ws=lab]")
    app.locator("#lab-body .tabs button", has_text="Uncertainty").click()
    app.locator("#lab-body h3", has_text="Motion uncertainty components").wait_for(timeout=30000)
    app.locator("#lab-body h3", has_text="Sensitivity to analysis choices").wait_for()
    app.locator("#lab-body h3", has_text="Not quantified by any method here").wait_for()
    app.locator("#lab-body td", has_text="matches log").first.wait_for()
    with app.expect_download() as d:
        app.locator("#lab-body .fig-export").first.click()
    svg = Path(d.value.path()).read_text()
    assert d.value.suggested_filename.endswith(".svg")
    assert "SYNTHETIC TEST DATA" in svg and "<metadata>" in svg and "Investigation " in svg


def test_o_registration_diagnostics(app):
    app.click(".nav button[data-ws=time]")
    app.locator("#tm-regdiag", has_text="REGDIAG-1").wait_for(timeout=30000)
    txt = app.locator("#tm-regdiag").text_content()
    assert "rotation" in txt and "reference stars" in txt and "not a photometric calibration" in txt


def test_p_vault_and_studio(app, tmp_path):
    app.click(".nav button[data-ws=records]")
    app.locator("#records-body p", has_text="1 hypothesis(es) of your own").wait_for()
    for name, tags in [(f"vault A {app.mode}", "alpha, shared"), (f"vault B {app.mode}", "beta, shared")]:
        app.fill("#save-name", name)
        app.fill("#save-tags", tags)
        app.click("#save-record")
        app.locator("#vault tr", has_text=name).wait_for()
    app.fill("#vault-search", "vault A")
    app.locator("#vault h3", has_text="(1 of").wait_for()
    app.fill("#vault-search", "")
    app.locator(".tagrow .tag", has_text="beta").click()
    app.locator("#vault tr", has_text=f"vault B {app.mode}").wait_for()
    assert app.locator("#vault tr", has_text=f"vault A {app.mode}").count() == 0
    app.locator(".tagrow .tag", has_text="all").click()
    row = app.locator("#vault tr", has_text=f"vault B {app.mode}")
    row.locator("button", has_text="Edit").click()
    app.locator(f"#vault input[aria-label='New name']").fill(f"vault B2 {app.mode}")
    app.locator("#vault .rename button", has_text="Save").click()
    app.locator("#vault tr", has_text=f"vault B2 {app.mode}").wait_for()
    app.locator("#vault tr", has_text=f"vault A {app.mode}").locator("button", has_text="Duplicate").click()
    app.locator("#vault tr", has_text=f"Copy of vault A {app.mode}").wait_for()
    app.locator("#vault tr", has_text=f"vault B2 {app.mode}").locator("input[type=checkbox]").check()
    app.locator("#vault tr", has_text=f"Copy of vault A {app.mode}").locator("input[type=checkbox]").check()
    app.click("#vault-compare")
    app.locator("#vault-compare-box", has_text="Identical content hash").wait_for(timeout=30000)
    app.locator("#vault-compare-box td", has_text="The motion is real").count()
    # studio exports
    for bid, ext in [("#dl-report", ".md"), ("#dl-graph", ".json"), ("#dl-discovery", ".json"), ("#dl-package", ".zip")]:
        with app.expect_download() as d:
            app.click(bid)
        assert d.value.suggested_filename.endswith(ext), bid
        if ext == ".zip":
            import zipfile
            z = zipfile.ZipFile(d.value.path())
            names = z.namelist()
            assert any(n.endswith("/SHA256SUMS") for n in names) and any(n.endswith("/record.json") for n in names)
            assert z.testzip() is None
        if bid == "#dl-discovery":
            disc = json.loads(Path(d.value.path()).read_text())
            assert disc["method"].startswith("DISC-1") and disc["synthetic"] is True
    # reopening restores the saved hypothesis; deleting keeps the two-step confirmation
    app.locator("#vault tr", has_text=f"vault A {app.mode}").first.locator("button", has_text="Open").click()
    app.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()
    app.click(".nav button[data-ws=arena]")
    app.locator(".userhyps > li", has_text="not a registration artefact").wait_for(timeout=30000)
    app.click(".nav button[data-ws=records]")
    for name in [f"Copy of vault A {app.mode}", f"vault B2 {app.mode}", f"vault A {app.mode}"]:
        r = app.locator("#vault tr", has_text=name).first
        r.locator("button", has_text="Delete").click()
        r.locator("button", has_text="Confirm delete").click()
        app.locator("#toast", has_text="Deleted").wait_for()
        app.wait_for_timeout(300)


def test_q_copilot_sections_and_capabilities(app):
    app.locator("#suggestions .chip", has_text="What can you do").click()
    msg = app.locator(".msg.bot").last
    msg.locator(".ans-sec h5", has_text="Answer").wait_for(timeout=60000)
    msg.locator(".ans-sec h5", has_text="Method").wait_for()
    msg.locator(".ans-sec h5", has_text="Limitations").wait_for()
    assert "capabilit" in msg.locator(".answer").text_content().lower()


def test_r_new_workspaces_narrow(app):
    app.click(".level-switch button[data-level=research]")
    for w, h, name in [(820, 1100, "tablet"), (390, 844, "mobile")]:
        app.set_viewport_size({"width": w, "height": h})
        for ws in ["discovery", "arena", "records", "command", "planner", "quality", "radar", "notebook", "experiments"]:
            app.locator(f".nav button[data-ws={ws}]").click()
            app.wait_for_timeout(400)
            assert app.locator("#main").bounding_box()["width"] <= w
            png = app.screenshot(full_page=True)            # its width is the document's scroll width (no eval under CSP)
            sw = int.from_bytes(png[16:20], "big")
            assert sw <= w + 1, (ws, name, sw)
        if app.mode == "static":
            SHOTS.mkdir(parents=True, exist_ok=True)
            app.click(".nav button[data-ws=discovery]")
            app.wait_for_timeout(400)
            app.screenshot(path=str(SHOTS / f"preview-{name}-discovery.png"))
    app.set_viewport_size({"width": 1440, "height": 900})


def test_s1_command_center_session_and_mission(app):
    app.set_viewport_size({"width": 1440, "height": 900})
    app.click(".level-switch button[data-level=research]")
    app.click(".nav button[data-ws=command]")
    app.locator("#command-body h3", has_text="Data quality").wait_for(timeout=30000)
    app.locator("#command-body h3", has_text="Observation coverage").wait_for()
    app.locator(".cc-coverage circle").first.wait_for(state="attached")
    app.fill("#cc-question", "Could this source have changed between the two recorded observation epochs?")
    app.click("#cc-question-set")
    app.locator("#session-box .session-name", has_text="SYN-VAR-1").wait_for(timeout=30000)
    app.locator(".cc-question", has_text="changed between").wait_for()
    app.locator("#command-body .activity li", has_text="Research question").wait_for()
    m = app.locator(".mission[data-mission=compare-pair]")
    m.locator("button", has_text="Start mission").click()
    m = app.locator(".mission[data-mission=compare-pair]")
    m.locator(".tasks li.done", has_text="Run (or load) the analysis").wait_for(timeout=30000)
    assert m.locator(".tasks li.done", has_text="wavelength-matched pair").count() == 0


def test_s2_planner_plans_runs_and_persists(app):
    app.click(".nav button[data-ws=time]")
    app.locator(".partner-list button.partner").first.wait_for(timeout=30000)
    app.locator(".partner-list button.partner").filter(has_not=app.locator(".why")).first.click()   # a wavelength-matched partner
    app.locator("#tm-banner", has_text="Wavelength-matched pair").wait_for(timeout=30000)
    app.click(".nav button[data-ws=command]")
    app.locator(".mission[data-mission=compare-pair] .tasks li.done", has_text="wavelength-matched pair").wait_for(timeout=30000)
    app.click(".nav button[data-ws=planner]")
    q = app.locator("#plan-question")
    pw.expect(q).to_have_value("Could this source have changed between the two recorded observation epochs?")
    app.click("#plan-go")
    app.locator(".plan-step[data-step=analysis] .step-st", has_text="completed").wait_for(timeout=30000)
    for sid in ("quality", "pair", "tests", "uncertainty"):
        app.locator(f".plan-step[data-step={sid}] .step-st", has_text="ready").wait_for()
    app.locator(".plan-step[data-step=stability] .step-st", has_text="suggested").wait_for()
    app.click("#plan-run")
    for sid in ("quality", "pair", "tests", "uncertainty"):
        app.locator(f".plan-step[data-step={sid}] .step-st", has_text="completed").wait_for(timeout=60000)
    app.locator(".plan-step[data-step=pair] .step-result", has_text="compatible").wait_for()
    app.locator(".plan-step[data-step=inspect] .step-st", has_text="ready").wait_for()
    app.locator(".plan-step[data-step=inspect] button", has_text="Run").click()
    app.locator(".nav button[data-ws=time][aria-current=page]").wait_for()
    app.click(".nav button[data-ws=planner]")
    st = app.locator(".plan-step[data-step=inspect]")
    st.locator(".step-st", has_text="needs review").wait_for()
    st.locator("textarea").fill("No artefact visible at the target position.")
    st.locator("button", has_text="Mark reviewed").click()
    app.locator(".plan-step[data-step=inspect] .step-st", has_text="completed").wait_for()
    app.locator(".plan-next", has_text="Next scientifically useful step").wait_for()
    # unanswerable and unrecognised questions are said to be so, with no steps
    q.fill("Why did it dim?")
    app.click("#plan-go")
    app.locator("#plan-canvas .status-rejected", has_text="Not answerable here").wait_for()
    assert app.locator(".plan-step").count() == 0
    # the plan survives a reload: it is in the session
    app.reload()
    if app.mode == "server":                                  # the server keeps no analysis across page loads; the session does
        app.locator("#run-btn").wait_for()
        app.click("#run-btn")
        app.locator("#run-btn", has_text="Re-run analysis").wait_for(timeout=120000)
    app.click(".nav button[data-ws=command]")
    app.locator("#command-body h3", has_text="Pending research tasks").wait_for(timeout=30000)
    app.click(".nav button[data-ws=planner]")
    app.locator(".plan-step[data-step=inspect] .step-st", has_text="completed").wait_for(timeout=30000)


def test_s3_quality_matrix_metadata_sequences(app):
    app.click(".nav button[data-ws=quality]")
    app.locator(".dq-row[data-check=DQ-FILES]").click()
    app.locator(".dq-card", has_text="every file's SHA-256 equals the manifest").wait_for()
    assert "score" not in app.locator("#quality-body").text_content().lower().replace("no overall quality score", "").replace("there is no overall quality score", "")
    app.locator("[data-qtab=matrix]").click()
    app.locator(".matrix-svg .mcell[tabindex='0']").first.click()
    app.locator("#matrix-cell button", has_text="Compare their metadata").click()
    app.locator("[data-qtab=metadata][aria-selected=true]").wait_for()
    app.locator(".compare-records th", has_text="sha256").wait_for()
    app.locator("[data-qtab=coverage]").click()
    app.locator("#quality-body td", has_text="SEQ-D1-1").wait_for()
    app.locator("#quality-body tr", has_text="SEQ-D1-1").locator("button", has_text="Open").click()
    app.locator(".nav button[data-ws=time][aria-current=page]").wait_for()
    app.locator(".seq-note", has_text="nothing is interpolated").wait_for(timeout=30000)
    app.locator(".seq-frames li").nth(1).wait_for(timeout=30000)
    app.locator("#seq-info h3", has_text="Frame 1 of").wait_for()
    app.click("button[aria-label='Next frame']")
    app.locator("#seq-info h3", has_text="Frame 2 of").wait_for()
    app.click("#seq-diff")
    app.locator("#time-body .caption", has_text="frame 2 − frame 1").wait_for()
    with app.expect_download() as d:
        app.click("#seq-export")
    rec = json.loads(Path(d.value.path()).read_text())
    assert rec["method"] == "SEQ-1" and all(f["sha256"] for f in rec["frames"]) and rec["synthetic"] is True
    app.locator("button", has_text="Back to pair comparison").click()


def test_s4_connectors(app):
    app.click(".nav button[data-ws=quality]")
    app.locator("[data-qtab=connectors]").click()
    card = app.locator("[data-connector=spherex_sia]")
    card.wait_for(timeout=30000)
    btn = card.locator("button", has_text="Validate and preview")
    if app.mode == "static":
        assert btn.is_disabled()
    else:
        card.locator("input[name=ra]").fill("10.5")
        card.locator("input[name=dec]").fill("-5")
        card.locator("input[name=radius_arcsec]").fill("1")
        btn.click()
        card.locator(".conn-out", has_text="Not sent").wait_for()
        card.locator(".conn-out", has_text="irsa.ipac.caltech.edu/SIA").wait_for()
        card.locator("input[name=ra]").fill("400")
        btn.click()
        card.locator(".conn-out .status-rejected").wait_for()
    assert "not usable now" in card.text_content()


def test_s5_radar(app):
    app.click(".nav button[data-ws=radar]")
    app.locator(".radar-item").first.wait_for(timeout=30000)
    assert "not detections" in app.locator("#radar-body").text_content()
    app.locator(".radar-item[data-signal=R1]").first.wait_for()
    app.locator(".tagrow .tag", has_text="can run now").click()
    assert app.locator(".radar-item.blocked").count() == 0
    app.locator(".radar-item[data-signal=R1]").first.locator("button", has_text="Open the pair").click()
    app.locator(".nav button[data-ws=time][aria-current=page]").wait_for()


def test_s6_ledger_inspectors(app):
    app.click(".nav button[data-ws=graph]")
    app.locator(".graph-svg .node").first.wait_for(timeout=30000)
    app.locator("[data-ltab=claims]").click()
    app.locator("#claim-detail", has_text="Directly linked support").wait_for(timeout=30000)
    assert "not a measure of how well" in app.locator("#claim-detail").text_content()
    app.locator("[data-ltab=contradictions]").click()
    app.locator("#ledger-host h3", has_text="Contradiction inspector").wait_for()
    app.locator("#ledger-host li", has_text="C1").first.wait_for()           # raw vs calibrated conflict in the variable fixture
    app.locator("[data-ltab=provenance]").click()
    app.locator("#ledger-host td.mono").first.wait_for()
    app.locator("[data-ltab=methods]").click()
    app.locator("#ledger-host dt", has_text="Methods linked").first.wait_for()
    app.locator("[data-ltab=completeness]").click()
    app.locator("#ledger-host h3", has_text="Evidence completeness").wait_for()
    app.locator("[data-ltab=history]").click()
    app.locator("#ledger-host li", has_text="question").first.wait_for()
    app.click(".nav button[data-ws=command]")
    app.locator("#command-body h3", has_text="Missions").first.wait_for(timeout=30000)


def test_s7_notebook_blocks_versions_undo_exports(app, tmp_path):
    app.click(".nav button[data-ws=notebook]")
    app.select_option("#nb-type", "paragraph")
    app.fill("#nb-text", "The third pass looks fainter on D1.")
    app.click("#nb-add")
    blk = app.locator(".nb-block.nb-paragraph").first
    blk.wait_for(timeout=30000)
    blk.locator("textarea").fill("The third pass looks fainter on D1 and D2.")
    blk.locator("button", has_text="Save").click()
    app.locator(".nb-block.nb-paragraph .nb-head", has_text="edited 1×").wait_for()
    for t in ("measurement", "evidence", "figure", "citation"):
        app.select_option("#nb-type", t)
        app.locator("#nb-ref").wait_for()
        app.click("#nb-add")
        app.locator(f".nb-block.nb-{t}").first.wait_for()
    app.locator(".nb-block.nb-measurement", has_text="µJy").wait_for()
    app.locator(".nb-block.nb-figure svg").wait_for()
    assert app.locator(".nb-block .status-rejected").count() == 0               # every reference resolves
    app.locator(".nb-block.nb-citation button", has_text="Delete").click()
    app.locator("#nb-undo button", has_text="Undo").click()
    app.locator(".nb-block.nb-citation").wait_for()
    with app.expect_download() as d:
        app.click("#nb-export-md")
    md = Path(d.value.path()).read_text()
    assert "[you]" in md and "[recorded]" in md and "SYNTHETIC" in md
    with app.expect_download() as d:
        app.click("#nb-export-pkg")
    import zipfile
    z = zipfile.ZipFile(d.value.path())
    names = z.namelist()
    assert z.testzip() is None and any(n.endswith("/SHA256SUMS") for n in names) and any(n.endswith("/session.json") for n in names)
    assert any(n.endswith("/investigation-package.zip") for n in names)
    import hashlib
    sess = json.loads(z.read(next(n for n in names if n.endswith("/session.json"))))
    from skytrace import canon
    assert canon.digest({k: v for k, v in sess.items() if k != "content_hash"}) == sess["content_hash"]


def test_s8_experiments_and_workflows(app):
    app.click(".nav button[data-ws=experiments]")
    app.locator("[data-template=reproducibility]").click()
    app.click("#exp-run")
    app.click("#exp-run")                                   # confirm
    app.locator("#exp-result", has_text="criterion met").wait_for(timeout=120000)
    if app.mode == "static":
        app.locator("#exp-result", has_text="Recorded when this preview was built").wait_for()
    app.locator("#exp-result", has_text="not thereby a valid experiment").wait_for()
    app.locator("[data-template=parameter]").click()
    if app.mode == "static":
        app.locator("#experiments-body", has_text="Custom parameter sets need the local server").wait_for()
    app.locator(".tabs button", has_text="Workflows").click()
    app.click("#wf-validate")
    app.locator("#wf-validation", has_text="Valid").wait_for(timeout=30000)
    app.fill("#wf-text", '{"schema": "skytrace.workflow/1", "name": "bad", "targets": ["syn-var-1"], "steps": [{"id": "x", "action": "rm_rf", "depends": []}]}')
    app.click("#wf-validate")
    app.locator("#wf-validation .status-rejected").first.wait_for()
    app.fill("#wf-text", json.dumps({"schema": "skytrace.workflow/1", "name": "e2e", "targets": ["syn-hpm-1", "syn-var-1"],
                                     "steps": [{"id": "analysis", "action": "run_analysis", "inputs": {}, "depends": []},
                                               {"id": "quality", "action": "check_quality", "inputs": {}, "depends": ["analysis"]}]}))
    app.click("#wf-run")
    app.click("#wf-run")                                     # confirm
    app.locator("#wf-log td.wf-completed").nth(3).wait_for(timeout=180000)
    assert app.locator("#wf-log td.wf-failed").count() == 0
    app.locator("#data-pill", has_text="Synthetic").wait_for()
    pw.expect(app.locator("#target-select")).to_have_value("syn-var-1")


def test_s9_sessions_dialog_export_import(app, tmp_path):
    app.locator("#session-btn").click()
    app.locator("#sessions").wait_for(state="visible")
    with app.expect_download() as d:
        app.click("#session-export")
    exported = tmp_path / "s.json"
    d.value.save_as(exported)
    s = json.loads(exported.read_text())
    assert s["schema"] == "skytrace.research_session/1" and s["notebook"] and s["plans"]
    app.set_input_files("#session-import-file", str(exported))
    app.locator("#toast", has_text="content hash verified").wait_for(timeout=30000)
    bad = dict(s, name="tampered")
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    app.set_input_files("#session-import-file", str(tmp_path / "bad.json"))
    app.locator("#toast", has_text="Import refused").wait_for(timeout=30000)
    assert app.locator("#sessions-body tbody tr").count() >= 2
    app.locator("#sessions-body td.status-ok").first.wait_for()
    app.keyboard.press("Escape")
    app.locator("#sessions").wait_for(state="hidden")


def test_s10_figure_studio(app):
    app.click(".nav button[data-ws=records]")
    app.locator("#figure-studio select#fig-select").wait_for(timeout=30000)
    app.select_option("#fig-select", "zhist")
    app.locator("#fig-chart figcaption", has_text="pairs").wait_for()
    app.fill("#fig-title-in", "Pair significances (e2e)")
    app.locator("#figure-studio button", has_text="Apply").click()
    app.locator("#fig-chart h4", has_text="Pair significances (e2e)").wait_for()
    with app.expect_download() as d:
        app.click("#fig-export-svg")
    svg = Path(d.value.path()).read_text()
    assert "<metadata>" in svg and "SYNTHETIC TEST DATA" in svg and "zhist" in svg
    app.locator("#kg h3", has_text="Knowledge graph").wait_for()


def test_y_accessible_names(app):
    """Every visible button, field and chart in every workspace has an accessible name (no axe-core offline: a direct check)."""
    app.set_viewport_size({"width": 1440, "height": 900})
    problems = []
    app.click(".level-switch button[data-level=research]")
    for ws in ["command", "planner", "quality", "radar", "notebook", "experiments", "discovery", "explorer", "time", "lab", "arena", "graph", "records"]:
        app.locator(f".nav button[data-ws={ws}]").click()
        app.wait_for_timeout(700)
        scope = app.locator(f"#ws-{ws}, .topbar, .copilot, .session-box")
        for b in scope.locator("button:visible").all():
            name = (b.get_attribute("aria-label") or b.inner_text() or b.get_attribute("title") or "").strip()
            if not name:
                problems.append((ws, "button", b.inner_html()[:80]))
        for f in scope.locator("input:visible, select:visible, textarea:visible").all():
            fid = f.get_attribute("id")
            named = (f.get_attribute("aria-label") or f.locator("xpath=ancestor::label").count()
                     or (fid and app.locator(f"label[for='{fid}']").count()))
            if not named:
                problems.append((ws, "field", f.get_attribute("type"), fid))
        for svg in scope.locator("svg[role=img]:visible").all():
            if not (svg.get_attribute("aria-label") or "").strip():
                problems.append((ws, "svg", svg.get_attribute("class")))
    for d in app.locator("[role=dialog]").all():
        assert d.get_attribute("aria-modal") == "true" and d.get_attribute("aria-labelledby")
    assert problems == [], problems


def test_z_no_external_requests_no_errors(app):
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
