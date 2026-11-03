"""Every visible control, in both delivery modes (Playwright + Chromium, offline).

server: `python run.py` with OFFLINE=1 (the full application).
static: `dist/preview/` served by a plain file server with no backend (the previewable build). The test rebuilds
        the interface files (`build_static.py --web-only`) and, if no recorded data exist, the whole preview.

Each control must either do what it says or be disabled with an explanation. Network requests are recorded and
must stay on the local origin. Run: pytest -m e2e tests/e2e
"""

import json
import re
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
           "SKYTRACE_SESSIONS_DIR": str(tmp_path_factory.mktemp("sessions")), "SKYTRACE_SYNTHLAB_DIR": str(tmp_path_factory.mktemp("synthlab")),
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


def test_h2_copilot_sources_drafts_and_plan(app):
    """Copilot 2.0: each answer names its source; a draft goes to the notebook as an assistant draft; a plan question
    hands the exact question to the Planner."""
    n = app.locator(".msg.bot .answer").count()            # wait for this question's answer, not the previous one
    app.fill("#ask-input", "Which evidence is still missing?")
    app.keyboard.press("Enter")
    app.locator(".msg.bot .answer").nth(n).wait_for(timeout=60000)
    mode = app.locator(".msg.bot .mode", has_text="source: deterministic local logic").last
    mode.wait_for(timeout=60000)
    assert app.locator(".msg.user .mode", has_text="user-authored content").count() >= 1
    assert "contradiction" in app.locator(".msg.bot .answer").last.text_content()
    app.locator(".msg.bot button", has_text="Add to notebook as draft").last.click()
    app.locator("#toast", has_text="assistant draft").wait_for()
    q = "How would I check whether the dimming is real?"
    app.fill("#ask-input", q)
    app.keyboard.press("Enter")
    btn = app.locator(".msg.bot button", has_text="Plan this question in the Planner").last
    btn.wait_for(timeout=60000)
    if app.mode == "static":
        assert app.locator(".msg.bot .recorded-q").last.is_visible()
    btn.click()
    app.locator("#ws-planner").wait_for(state="visible")
    app.locator("#plan-question").wait_for()
    assert app.locator("#plan-question").input_value() == q
    app.locator("button[data-ws='notebook']").click()
    app.locator("#ws-notebook .nb-block", has_text="assistant draft").first.wait_for(timeout=10000)


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
    # every visible top-bar control lies inside the window, from phone to desktop widths (870–1180 px once pushed
    # the Run and Copilot buttons off-screen; seen in the hosted preview)
    for w in (1440, 1280, 1180, 1100, 1000, 900, 870, 820, 390):
        app.set_viewport_size({"width": w, "height": 900})
        for sel in ["#run-btn", ".level-switch", "#palette-btn", "#help-btn", "#copilot-toggle", "#model-pill", "#data-pill"]:
            loc = app.locator(sel)
            if loc.is_visible():
                bb = loc.bounding_box()
                assert bb["x"] + bb["width"] <= w + 0.5, (w, sel)
    app.set_viewport_size({"width": 1440, "height": 900})
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
    app.keyboard.press("Alt+8")                       # investigate level: command, explorer, time, atlas, graph, reasoning, quality, lab
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
        for ws in ["discovery", "arena", "records", "command", "planner", "quality", "radar", "notebook", "experiments",
                   "horizon", "counterfactual", "synthetic", "adversarial", "autopilot", "atlas", "knowledge", "review",
                   "reasoning", "compiler", "claims", "debugger", "models", "uflow", "future", "decide", "negative", "integrity", "protocol", "argue",
                   "intel"]:
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
    # planning the same question again stores a new revision; the earlier one is kept in the session
    app.fill("#plan-question", "Could this source have changed between the two recorded observation epochs?")
    app.click("#plan-go")
    app.locator("#plan-canvas .plan-head h3", has_text="revision 2").wait_for(timeout=30000)


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
    # cancellation stops before the next step and keeps completed items; retry runs only what did not complete.
    # (Server mode: there each analysis takes long enough to cancel; the static preview finishes a run too fast.)
    if app.mode == "server":
        app.click("#wf-run")
        app.click("#wf-run")                                 # confirm
        pw.expect(app.locator("#wf-cancel")).to_be_enabled(timeout=30000)
        app.click("#wf-cancel")
        pw.expect(app.locator("#wf-run")).to_be_enabled(timeout=180000)
        assert app.locator("#wf-log td.wf-cancelled").count() >= 1
        app.locator("#wf-log button", has_text="Retry failed or cancelled items").click()
        app.locator("#wf-log td.wf-completed").nth(3).wait_for(timeout=180000)
        pw.expect(app.locator("#wf-log td.wf-cancelled")).to_have_count(0, timeout=180000)


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
    n = app.locator("#sessions-body tbody tr").count()
    app.click("#session-branch")
    app.locator("#toast", has_text="original session is unchanged").wait_for(timeout=30000)
    app.locator("#sessions-body tbody tr").nth(n).wait_for()
    assert app.locator("#session-btn .session-name").text_content().startswith("Branch of")
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
    import xml.etree.ElementTree as ET
    assert ET.fromstring(svg).tag.endswith("svg")                 # the exported file parses as SVG
    app.locator("#kg h3", has_text="Knowledge graph").wait_for()


def _research_level(app):
    app.click(".level-switch button[data-level=research]")


def test_t1_discovery_horizon(app, tmp_path):
    _research_level(app)
    app.click(".nav button[data-ws=horizon]")
    app.locator(".horizon-card").first.wait_for(timeout=60000)
    assert app.locator(".spe-layer").count() == 6
    first = app.locator(".horizon-card").first
    for label in ("Prompted by", "Required data", "Available data", "Proposed method", "Limitations", "Expected output", "Why this rank"):
        first.locator("dt", has_text=label).wait_for()
    assert "finding" not in " ".join(app.locator(".horizon-card h4").all_text_contents()).lower()
    app.locator(".tagrow .tag", has_text="C4").click()
    assert app.locator(".horizon-card").count() == app.locator(".horizon-card[data-cat=C4]").count() > 0
    app.locator("[data-hview=map]").click()
    app.locator("svg.hz-map text.hz-node").first.wait_for()
    app.locator("[data-hview=cards]").click()
    with app.expect_download() as d:
        app.click("#horizon-export")
    data = json.loads(Path(d.value.path()).read_text())
    assert data["cards"] and all(c["prompted_by"] for c in data["cards"])
    q = app.locator(".horizon-card h4").first.text_content()
    app.locator(".horizon-card button", has_text="Plan this question").first.click()
    app.locator("#plan-question").wait_for()
    pw.expect(app.locator("#plan-question")).to_have_value(q)
    app.locator(".tagrow .tag", has_text="all categories").count()


def test_t2_counterfactual_lab(app):
    _research_level(app)
    app.click(".nav button[data-ws=counterfactual]")
    app.locator(".cf-preset", has_text="Stricter brightness threshold").click()
    res = app.locator(".cf-result")
    res.wait_for(timeout=60000)
    res.locator(".pill", has_text="assumed").wait_for()
    res.locator(".pill", has_text="baseline intact").wait_for()
    assert res.locator("tr.changed").count() >= 1
    assert "not an observation" in res.text_content()
    app.locator("#cf-lineage tbody tr").first.wait_for()
    with app.expect_download() as d:
        app.click("#cf-export")
    r = json.loads(Path(d.value.path()).read_text())
    assert r["baseline"]["intact"] and r["scenario"]["baseline_hash"] == r["baseline"]["content_hash"]
    if app.mode == "server":                  # a custom scenario (static: only the prepared ones are recorded)
        app.select_option("#cf-kind", "error_scale")
        app.fill("#cf-value", "3")
        app.click("#cf-run")
        app.locator(".cf-result .pill", has_text="simulated").wait_for(timeout=60000)
    else:
        app.select_option("#cf-kind", "error_scale")
        app.fill("#cf-value", "3")
        app.click("#cf-run")
        app.locator("#cf-result .withheld", has_text="not precomputed").wait_for(timeout=30000)


def test_t3_adversarial_lab(app):
    _research_level(app)
    app.click(".nav button[data-ws=adversarial]")
    item = app.locator(".asl-item[data-challenge=M-CALCHECK]")
    item.wait_for(timeout=60000)
    item.locator("dt", has_text="Rule").wait_for()
    item.locator("textarea").fill("Checked the reference-star scatter in the ledger.")
    item.locator("button", has_text="Acknowledge").click()
    app.locator(".asl-item[data-challenge=M-CALCHECK] .pill", has_text="acknowledged").wait_for(timeout=30000)
    app.locator("[data-atab=ranking]").click()
    app.locator("#info-table tbody tr").first.wait_for()
    app.locator("dd", has_text="no numerical information gain").wait_for()
    app.locator("[data-atab=causal]").click()
    app.fill("#causal-from", "a calibration change in pass 3")
    app.fill("#causal-to", "the D1 flux difference")
    app.click("#causal-add")
    app.locator("#causal-user li", has_text="user-proposed").wait_for(timeout=30000)
    app.locator(".causal-list li", has_text="model-derived").first.wait_for()


def test_t4_synthetic_observatory_and_design(app):
    _research_level(app)
    app.click(".nav button[data-ws=synthetic]")
    app.select_option("#syn-template", "slow-mover")
    app.click("#syn-run")
    if app.mode == "server":
        app.click("#syn-run")                 # confirm
    res = app.locator(".syn-result")
    res.wait_for(timeout=120000)
    assert res.locator("tbody tr").count() == 2 and "agrees" in res.text_content()
    res.locator(".pill", has_text="synthetic").wait_for()
    app.locator("[data-stab=design]").click()
    app.click("#design-run")
    if app.mode == "server":
        app.click("#design-run")
    app.locator("#design-result tbody tr").nth(1).wait_for(timeout=180000)
    with app.expect_download() as d:
        app.click("#design-brief")
    assert "Not a telescope schedule" in Path(d.value.path()).read_text()


def test_t5_research_autopilot(app):
    _research_level(app)
    app.click(".nav button[data-ws=autopilot]")
    app.fill("#ap-objective", "Challenge my interpretation of the brightness change.")
    app.click("#ap-propose")
    app.locator("#ap-steps tbody tr").nth(2).wait_for(timeout=30000)
    app.select_option("#ap-level", "plan")
    pw.expect(app.locator("#ap-run")).to_be_disabled()
    app.select_option("#ap-level", "local")
    app.click("#ap-run")
    app.locator("#toast", has_text="authorization").wait_for()
    app.check("#ap-auth")
    app.click("#ap-run")
    app.locator("#ap-steps tr.ap-completed").nth(1).wait_for(timeout=120000)
    app.locator("h3", has_text="Proposed next step").wait_for(timeout=60000)


def test_t6_cosmic_atlas(app):
    app.click(".nav button[data-ws=atlas]")
    app.locator("#atlas-table tbody tr").nth(4).wait_for(timeout=30000)
    assert "unknown (no parallax recorded)" in app.locator("#atlas-table").text_content()
    assert app.locator("#atlas-sep tbody tr").count() >= 1
    assert "no projected or physical separation" in app.locator("#atlas-body").text_content()
    app.locator("svg.atlas-field").wait_for()


def test_t7_knowledge_atlas_and_twins(app):
    _research_level(app)
    app.click(".nav button[data-ws=knowledge]")
    app.locator("#ka-search").wait_for(timeout=60000)
    app.fill("#ka-search", "calibration")
    app.locator("#ka-results li").first.wait_for()
    assert "no embedding model" in app.locator("#knowledge-body").text_content()
    app.locator("[data-ktab=twins]").click()
    app.locator("#twin-integrity", has_text="recompute").wait_for(timeout=30000)
    app.select_option("#twin-b", "1")
    app.locator("#knowledge-body h3", has_text="Not comparable").wait_for()


def test_t8_review_room_repro_story(app):
    app.click(".nav button[data-ws=review]")
    app.locator(".review-list li").first.wait_for(timeout=60000)
    assert "not people" in app.locator("#review-body").text_content()
    app.locator("[data-rtab=repro]").click()
    app.click("#repro-run")
    if app.mode == "server":
        app.click("#repro-run")
    app.locator("#review-body h3", has_text="Verdict: reproduced").wait_for(timeout=120000)
    app.locator("[data-rtab=story]").click()
    app.locator(".story-ch").nth(9).wait_for()
    with app.expect_download() as d:
        app.click("#story-export")
    md = Path(d.value.path()).read_text()
    assert "SYNTHETIC TEST DATA" in md and "## 10. The next research question" in md and "discovered" not in md.lower()


def test_y_accessible_names(app):
    """Every visible button, field and chart in every workspace has an accessible name (no axe-core offline: a direct check)."""
    app.set_viewport_size({"width": 1440, "height": 900})
    problems = []
    app.click(".level-switch button[data-level=research]")
    for ws in ["command", "planner", "quality", "radar", "notebook", "experiments", "discovery", "explorer", "time", "lab", "arena", "graph", "records",
               "horizon", "counterfactual", "synthetic", "adversarial", "autopilot", "atlas", "knowledge", "review",
               "reasoning", "compiler", "claims", "debugger", "models", "uflow", "future", "decide", "negative", "integrity", "protocol", "argue",
                   "intel"]:
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


# ------------------------------------------------------------------ Phase 8: the epistemic layer
def _dl_json(app, sel):
    with app.expect_download() as d:
        app.click(sel)
    return json.loads(Path(d.value.path()).read_text())


def test_e1_reasoning_graph_and_lineage(app):
    _research_level(app)
    app.click(".nav button[data-ws=reasoning]")
    app.locator(".epi-node").first.wait_for(timeout=60000)
    pw.expect(app.locator("#epi-node")).to_have_value("claim:variability")
    pw.expect(app.locator("#epi-summary")).to_contain_text("upstream")
    for k in ("source", "measurement", "method", "assumption"):
        pw.expect(app.locator("#epi-summary")).to_contain_text(k)
    app.locator("#epi-selected .pill.epi").first.wait_for()
    app.select_option("#epi-node", index=app.locator("#epi-node option").count() - 1)      # a source file
    app.click("[data-dir=forward]")
    pw.expect(app.locator("#epi-summary")).to_contain_text("downstream")
    pw.expect(app.locator("#epi-summary")).to_contain_text("claim")
    data = _dl_json(app, "#epi-export")
    assert data["method"] == "EPI-1" and data["direction"] == "forward" and data["nodes"]
    app.click("[data-dir=back]")
    app.click("[data-rtab-epi=lineage]")
    app.locator(".lin-stage").nth(8).wait_for(timeout=30000)
    assert app.locator(".lin-stage.missing").count() == 0
    lin = _dl_json(app, "#lin-export")
    assert lin["method"] == "LINEAGE-1" and lin["complete"]
    app.click("[data-rtab-epi=graph]")


def test_e2_scientific_compiler_and_method_genome(app):
    _research_level(app)
    app.click(".nav button[data-ws=compiler]")
    app.locator("#compile-outcome").wait_for(timeout=60000)
    pw.expect(app.locator("#compile-outcome h3")).to_have_text("requires scientific review")
    pw.expect(app.locator("#compile-outcome")).to_contain_text("does not mean any conclusion is true")
    app.click("[data-stage=types]")
    assert app.locator("#compile-checks .check").count() == app.locator("#compile-checks .check[data-check^=T]").count() > 0
    app.click("[data-out=fail]")
    app.locator(".empty", has_text="No check matches").wait_for()
    app.click("[data-out=all]")
    app.click("[data-stage=types]")
    rep = _dl_json(app, "#compile-export")
    assert rep["method"] == "SCICOMP-1" and len(rep["stages"]) == 9
    app.click("[data-ctab=genome]")
    assert app.locator("#genome-table tbody tr").count() >= 13
    app.click("[data-method=APPHOT-1]")
    pw.expect(app.locator("#method-detail h3")).to_have_text("APPHOT-1")
    pw.expect(app.locator("#method-detail")).to_contain_text("µJy")
    app.select_option("#cmp-a", "PAIRDIFF-1")
    app.select_option("#cmp-b", "PAIRDIFF-2")
    pw.expect(app.locator("#cmp-out")).to_contain_text("Compatible")
    app.click("[data-ctab=compile]")


def test_e3_claims_boundary_stress_blindspots(app):
    _research_level(app)
    app.click(".nav button[data-ws=claims]")
    app.locator(".kb-item").first.wait_for(timeout=60000)
    app.locator("[data-region=unresolved] [data-kb='claim:variability']").click()
    pw.expect(app.locator("#kb-detail")).to_contain_text("artefact explanations not ruled out")
    app.locator("[data-region='outside the evidence'] [data-kb=Q-CAUSE]").wait_for()
    assert "confidence" not in app.locator("#claims-body").inner_text().lower().replace("not confidence levels", "")
    app.click("[data-cltab=stress]")
    assert app.locator("#cx-table tbody tr").count() == 10
    pw.expect(app.locator("#cx-table tr[data-mode=reproducibility]")).to_contain_text("not tested")
    pw.expect(app.locator("#cx-table tr[data-mode=alternatives]")).to_contain_text("warning")
    app.click("[data-cltab=blindspot]")
    app.locator("#blind-table tbody tr").first.wait_for(timeout=30000)
    assert app.locator("#blind-table tbody tr").count() == 11
    assert "%" not in app.locator("#claims-body").inner_text()
    assert _dl_json(app, "#blind-export")["method"] == "BLIND-1"
    pw.expect(app.locator("#blind-table tr[data-blind=epochs]")).to_contain_text("not examined")
    app.click("[data-cltab=boundary]")


def test_e4_scientific_debugger(app):
    _research_level(app)
    app.click(".nav button[data-ws=debugger]")
    app.locator("#dbg-panel").wait_for(timeout=60000)
    pw.expect(app.locator("#dbg-verdict")).to_contain_text("recomputes")
    app.select_option("#dbg-result", index=app.locator("#dbg-result option").count() - 1)          # a flux comparison
    pw.expect(app.locator("#dbg-verdict")).to_have_text(re.compile(r"^recomputes (identically|within tolerance)$"))
    app.click("[data-bp=assessment]")
    pw.expect(app.locator("#dbg-verdict")).to_have_text("recomputes identically")
    app.click("[data-dtab=diff]")
    app.locator("#diff-run, #debugger-body .empty").first.wait_for(timeout=30000)
    if app.locator("#diff-run").count():                          # static: the recorded runs; server: runs attached to the session
        app.select_option("#diff-b", index=1)
        app.click("#diff-run")
        app.locator("#diff-earliest").wait_for(timeout=30000)
        assert app.locator("#diff-table tbody tr").count() >= 5
    else:
        assert app.mode == "server"
        app.locator(".empty", has_text="needs two runs").wait_for()
    app.click("[data-dtab=repro]")
    app.click("#rx-run")
    if app.mode == "server":
        app.click("#rx-run")                                      # confirm
    app.locator("#rx-verdict", has_text="exact reproduction").wait_for(timeout=120000)
    app.click(".nav button[data-ws=claims]")
    app.click("[data-cltab=stress]")
    pw.expect(app.locator("#cx-table tr[data-mode=reproducibility]")).to_contain_text("pass")
    app.click("[data-cltab=boundary]")
    app.click(".nav button[data-ws=debugger]")
    app.click("[data-dtab=inspect]")


def test_e5_models_uncertainty_future(app):
    _research_level(app)
    app.click(".nav button[data-ws=models]")
    app.locator(".models-table").nth(1).wait_for(timeout=60000)
    assert app.locator("#models-body", has_text="LINFIT-EPOCH-1 reproduced").count() == 1
    assert "probability" not in app.locator("#models-body").inner_text().lower()
    assert _dl_json(app, "#models-export")["method"] == "MODELS-1"
    app.click(".nav button[data-ws=uflow]")
    app.locator("[data-unode='u:flux']").click()
    pw.expect(app.locator("#uflow-detail h3")).to_contain_text("flux error")
    assert app.locator("#uflow-gaps tbody tr").count() >= 4
    app.click(".nav button[data-ws=future]")
    pw.expect(app.locator("#future-validation")).to_contain_text("reproduces")
    assert app.locator("[data-scenario=baseline] tbody tr").count() == 5
    app.fill("#fl-years", "2")
    app.click("#fl-calc")
    pw.expect(app.locator("#fl-out")).to_contain_text("Hypothetical")
    app.click("#fl-keep")
    app.locator("#toast", has_text="hypothetical").wait_for()


def test_e6_decisions_and_questions(app):
    _research_level(app)
    app.click(".nav button[data-ws=decide]")
    app.locator("#nx-list .nx-item").nth(2).wait_for(timeout=60000)
    app.locator("#nx-list .nx-item").nth(1).locator("dt", has_text="Why not higher").wait_for()
    pw.expect(app.locator("#decide-body")).to_contain_text("not an optimisation")
    app.locator("#nx-list .nx-item").first.locator("button", has_text="Record this decision").click()
    app.locator("#toast", has_text="Decision recorded").wait_for()
    app.click("[data-qtab-epi=questions]")
    app.locator("#qf-list .nx-item").first.wait_for()
    app.click("[data-qcat=hypothetical]")
    assert app.locator("#qf-list .nx-item").count() == app.locator("#qf-list .nx-item", has_text="hypothetical").count() > 0
    app.locator("#qf-list .nx-item").first.locator("button", has_text="Plan this question").click()
    app.locator("#plan-question").wait_for()
    app.click(".nav button[data-ws=decide]")
    app.click("[data-qcat=all]")
    app.click("[data-qtab-epi=next]")


def test_e7_negative_space_and_integrity(app):
    _research_level(app)
    app.click(".nav button[data-ws=negative]")
    app.locator("#neg-table tbody tr").first.wait_for(timeout=60000)
    total = app.locator("#neg-table tbody tr").count()
    app.fill("#neg-search", "WLMATCH")
    assert 0 < app.locator("#neg-table tbody tr").count() < total
    app.fill("#neg-search", "")
    app.fill("#neg-new-attempted", "compare D1 pairs by eye")
    app.fill("#neg-new-happened", "too few visits to judge")
    app.click("#neg-add")
    app.locator("#neg-table tbody tr", has_text="compare D1 pairs by eye").wait_for(timeout=30000)
    app.click(".nav button[data-ws=integrity]")
    app.click("#integ-run")
    app.locator("#integ-outcome", has_text="ready").wait_for(timeout=30000)
    app.select_option("#integ-source", "paste")
    app.fill("#integ-text", "We discovered a variable star with high probability (flux 12345.67 µJy).")
    app.click("#integ-run")
    app.locator("#integ-outcome", has_text="needs attention").wait_for()
    pw.expect(app.locator("#integ-table tr[data-icheck=I12]")).to_contain_text("discovered")
    assert _dl_json(app, "#integ-export")["method"] == "INTEG-1"
    app.select_option("#integ-source", "report")


def test_e8_protocol_and_blind_analysis(app):
    _research_level(app)
    app.click(".nav button[data-ws=protocol]")
    app.fill("#pr-question", "Did SYN-VAR-1 change in brightness?")
    app.fill("#pr-primary_hypothesis", "The source dimmed between passes.")
    app.select_option("#pr-eval-variability", "variability_candidate")
    app.fill("#pr-param-aperture_radius_px", "2.0")
    app.click("#pr-save")
    app.locator("#pr-status", has_text="draft").wait_for(timeout=30000)
    app.click("#pr-lock")
    app.click("#pr-lock")
    app.locator("#pr-status", has_text="locked after results were visible").wait_for(timeout=30000)
    pw.expect(app.locator("#pr-question")).to_be_disabled()
    app.locator("#pr-compare-table tbody tr", has_text="as expected").wait_for()
    app.fill("#am-value", "3.0")
    app.fill("#am-reason", "larger aperture for the faint target")
    app.click("#am-add")
    app.locator("#protocol-body td", has_text="larger aperture").wait_for(timeout=30000)
    app.click("#blind-start")
    app.click("#blind-start")
    app.locator("#blind-state", has_text="blind active").wait_for(timeout=30000)
    for ws in ("lab", "command", "claims", "time"):
        app.click(f".nav button[data-ws={ws}]")
        app.locator(f"#ws-{ws} .blind-cover").wait_for()
        assert app.locator(".outcome:visible").count() == 0
    app.click(".nav button[data-ws=explorer]")
    assert app.locator("#ws-explorer .blind-cover").count() == 0
    pw.expect(app.locator("#ruler-caption")).to_contain_text("hidden by the blind")
    app.click(".nav button[data-ws=protocol]")
    app.click("#blind-end")
    app.locator("#toast", has_text="UNBLIND").wait_for()
    app.fill("#unblind-confirm", "UNBLIND")
    app.click("#blind-end")
    app.locator("#blind-state", has_text="unblinded").wait_for(timeout=30000)
    pw.expect(app.locator("#blind-card")).to_contain_text("matches")
    app.click(".nav button[data-ws=lab]")
    app.locator(".outcome").first.wait_for(timeout=30000)


def test_e9_reasoning_lab_and_phase8_tabs(app):
    _research_level(app)
    app.click(".nav button[data-ws=argue]")
    app.select_option("#arg-claim-ref", "claim:variability")
    app.click("#arg-new")
    app.locator("#arg-view").wait_for(timeout=30000)
    pw.expect(app.locator("#arg-valid")).to_contain_text("no supporting evidence")
    app.select_option("#arg-add-support", index=1)
    app.select_option("#arg-rule", index=1)
    app.select_option("#arg-add-asm", index=1)
    app.click("#arg-apply")
    pw.expect(app.locator("#arg-valid")).to_contain_text("every step has premises")
    pw.expect(app.locator("#arg-empirical")).to_contain_text("rests on")
    app.fill("#arg-dispute-text", "the threshold was chosen for another purpose")
    app.click("#arg-dispute")
    app.locator("#arg-view li", has_text="open").first.wait_for()
    app.click("#arg-branch")
    app.locator("#arg-list li").nth(1).wait_for()
    app.select_option("#arg-compare", index=1)
    app.locator("#arg-compare-out").wait_for()
    with app.expect_download() as d:
        app.click("#arg-export")
    assert "Well-formed" in Path(d.value.path()).read_text()
    app.click(".nav button[data-ws=knowledge]")
    app.click("[data-ktab=vault]")
    pw.expect(app.locator("#vault-broken")).to_have_text("none")
    app.fill("#vault-correction", "the D1 note referred to visit 2")
    app.click("#vault-correct")
    app.locator("#vault-table tr", has_text="Correction to").first.wait_for(timeout=30000)
    app.click("[data-ktab=search]")
    app.click(".nav button[data-ws=review]")
    app.click("[data-rtab=board]")
    assert app.locator("[data-perspective]").count() == 8
    item = app.locator("details[data-perspective][open] .rb-item").first
    item.locator("input").fill("checked: the scale is applied")
    item.locator("button", has_text="Add").click()
    app.locator(".rb-item", has_text="checked: the scale is applied").wait_for(timeout=30000)
    app.click("[data-rtab=review]")
    app.click(".nav button[data-ws=synthetic]")
    app.click("[data-stab=audit]")
    app.click("#sa-run")
    if app.mode == "server":
        app.click("#sa-run")
    app.locator("#sa-verdict", has_text="stable").wait_for(timeout=180000)
    app.click("[data-stab=scenarios]")


# ------------------------------------------------------------------ Phase 9: the scientific intelligence workspace
def _intel(app, panel):
    _research_level(app)
    app.click(".nav button[data-ws=intel]")
    app.locator("#intel-layers").wait_for(timeout=120000)
    app.click(f"[data-ipanel={panel}]")
    app.locator(f"#intel-panel[data-panel={panel}]").wait_for(timeout=60000)


def test_i1_command_center_genome_and_fingerprint(app):
    _intel(app, "command")
    assert app.locator("#intel-layers .intel-layer").count() == 6 and app.locator("#intel-layers [data-ipanel]").count() == 12
    pw.expect(app.locator("#ic-gate")).to_have_text("not ready")
    assert app.locator("#ic-investigations tbody tr").count() >= 1
    app.locator(".intel-head details summary").click()
    for k in ("Real data", "Synthetic data", "Simulated output", "Hypothetical scenario", "Unverified interpretation", "Verified computation"):
        app.locator(".kind-legend .kind", has_text=k).first.wait_for()
    app.locator("[data-goto=gate] button").first.click()
    app.locator("#intel-panel[data-panel=gate]").wait_for()
    app.click("[data-ipanel=genome]")
    app.locator("#gn-fields").wait_for(timeout=30000)
    assert app.locator("#gn-fields dt").count() == 13
    pw.expect(app.locator("#gn-fingerprint tr[data-dim=F2]")).to_contain_text("changes")
    pw.expect(app.locator("#gn-fingerprint tr[data-dim=F4]")).to_contain_text("not tested")
    assert app.locator("#gn-budget tbody tr", has_text="unquantified").count() >= 4
    if app.locator("#gn-compare option").count() > 1:
        app.select_option("#gn-compare", index=1)
        app.locator("#gn-cmp table").wait_for(timeout=30000)
        pw.expect(app.locator("#gn-cmp")).to_contain_text("not evidence that the sources are physically alike")
    app.select_option("#intel-focus", "motion")
    pw.expect(app.locator("#gn-fields")).to_contain_text("LINFIT-EPOCH-1")
    app.select_option("#intel-focus", "variability")


def test_i2_unknown_universe_and_network(app):
    _intel(app, "unknown")
    assert app.locator("#uk-map [data-region]").count() == 8
    app.locator("#uk-map [data-region=unexplored]").focus()
    app.keyboard.press("Enter")                               # the bands are keyboard-operable buttons
    app.locator("#uk-items [data-ukitem]").first.wait_for()
    pw.expect(app.locator("#intel-panel")).to_contain_text("U6")
    app.locator("#uk-map [data-region=unresolved]").focus()
    app.keyboard.press("Enter")
    pw.expect(app.locator("#uk-items")).to_contain_text("HYPO-1 overall 'untested'")
    assert _dl_json(app, "#uk-export")["method"] == "UNKNOWN-1"
    app.click("[data-ipanel=network]")
    app.locator("#net-graph [data-node]").first.wait_for(timeout=30000)
    if app.locator("#net-edges li").count():                  # the static preview holds twelve runs; a fresh server may hold one
        app.select_option("#net-rule", "N1")
        pw.expect(app.locator("#net-edges")).to_contain_text("limitation:")
        app.select_option("#net-rule", "all")
    else:
        assert app.mode == "server"
        pw.expect(app.locator("#net-edges")).to_contain_text("No pair of investigations")


def test_i3_adversary_and_causality(app):
    _intel(app, "adversary")
    app.locator("details[data-advq][open] [data-chal]").first.wait_for(timeout=30000)
    first = app.locator("details[data-advq][open] [data-chal]").first
    cid = first.get_attribute("data-chal")
    first.locator(".adv-note").fill("seen: the reference ratio scatter")
    first.locator(".adv-ack").click()
    pw.expect(app.locator(f"[data-chal='{cid}']")).to_contain_text("acknowledged")
    nxt = app.locator("details[data-advq][open] [data-chal]", has=app.locator(".out-warn", has_text="open")).first
    nxt.locator(".adv-resolve").click()
    app.locator("#toast", has_text="Resolving needs a recorded item").wait_for()
    pw.expect(app.locator("#adv-inst tr[data-inst=I1]")).to_contain_text("ruled out by rule")
    app.click("[data-ipanel=causal]")
    app.locator("#cl-models tbody tr").first.wait_for(timeout=30000)
    assert app.locator("#cl-models tbody td.cl-crit[title^='C5']", has_text="✓").count() == 0, "experimental support is never reached"
    app.locator("#cl-models tr[data-model=V-CALIB]").click()
    pw.expect(app.locator("#cl-selected")).to_contain_text("Confounders (common causes in the graph): detector, epoch")
    app.select_option("#cl-from", "calibration")
    app.select_option("#cl-rel", "causes")
    app.select_option("#cl-to", "flux_difference")
    app.click("#cl-add")
    app.locator("#cl-warn li", has_text="user-proposed causal claim").wait_for(timeout=30000)


def test_i4_whatif_and_oracle(app):
    _intel(app, "whatif")
    pw.expect(app.locator("[data-whatif=W3]")).to_contain_text("no valid method")
    pw.expect(app.locator("[data-whatif=W1]")).to_contain_text("computed here")
    app.fill("#wi-dt", "2")
    app.click("#wi-run")
    app.locator("#wi-snr").wait_for()
    pw.expect(app.locator("#wi-out")).to_contain_text("Hypothetical")
    app.click("#wi-record")
    app.locator("#toast", has_text="hypothetical scenario").wait_for()
    app.click("[data-ipanel=oracle]")
    app.select_option("#or-q", "motion")
    app.click("#or-run")
    app.locator("#or-table tbody tr").nth(1).wait_for(timeout=30000)
    pw.expect(app.locator("#or-out")).to_contain_text("not computed: bits of information need prior probabilities")
    app.locator(".or-cand .or-years").first.fill("99")
    app.click("#or-run")
    app.locator("#or-out .withheld", has_text="added_years_after_last").wait_for()
    app.locator(".or-cand .or-years").first.fill("1")
    assert app.locator("#or-neg tbody tr").count() >= 1


def test_i5_research_cycle_permissions_and_gate(app):
    _intel(app, "cycle")
    app.select_option("#cy-level", "advisory")
    app.locator("#cy-steps li").first.wait_for(timeout=30000)
    assert app.locator("#cy-steps .cy-run").count() == 0, "advisory executes nothing"
    app.select_option("#cy-level", "supervised")
    app.locator("#cy-steps li[data-step=check_quality] .cy-run").click()
    app.locator("#cy-steps li[data-step=check_quality]", has_text="completed").wait_for(timeout=60000)
    pw.expect(app.locator("#cy-log")).to_contain_text("approved this step")
    app.select_option("#cy-level", "restricted")
    app.click("#cy-start")
    app.locator("#toast", has_text="Tick the authorization").wait_for()
    app.check("#cy-auth")
    app.click("#cy-start")
    app.locator("#cy-log tr", has_text="reproduce_independent").wait_for(timeout=180000)
    pw.expect(app.locator("#cy-log")).to_contain_text("authorized the predefined workflow")
    with app.expect_download() as d:
        app.click("#cy-report")
    assert "No conclusion in this report is established by the cycle" in Path(d.value.path()).read_text()
    app.select_option("#cy-level", "advisory")
    app.click("[data-ipanel=gate]")
    app.locator("#gt-table tr[data-req=G3]").wait_for(timeout=30000)
    pw.expect(app.locator("#gt-table tr[data-req=G3]")).to_contain_text("met")
    assert app.locator("#gt-table tbody tr").count() == 8
    pw.expect(app.locator("#gt-mark")).to_be_disabled()


def test_i6_memory_reproduction_and_preservation(app):
    _intel(app, "memory")
    app.fill("#mem-query", "why did the brightness calibration fail")
    app.click("#mem-search")
    pw.expect(app.locator("#mem-concepts")).to_contain_text("Calibration")
    assert app.locator("#mem-results li").count() > 0
    assert app.locator("#mem-results li", has=app.locator(".out-ok", has_text="verified")).filter(has_text="explanation").count() == 0
    app.select_option("#mem-action", "variability")
    app.locator("#mem-warnings li").first.wait_for()
    assert app.locator("#mem-evolution tbody tr").count() >= 1 and app.locator("#mem-hyp tbody tr").count() >= 5
    app.click("[data-ipanel=repro]")
    m = _dl_json(app, "#rp-manifest")
    assert m["schema"] == "skytrace.reproduction/1" and m["manifest_digest"]
    app.fill("#rp-paste", json.dumps(m))
    app.click("#rp-compare-paste")
    pw.expect(app.locator("#rp-status")).to_contain_text("exact match")
    m["outcomes"]["variability"]["category"] = "edited"
    app.fill("#rp-paste", json.dumps(m))
    app.click("#rp-compare-paste")
    app.locator("#rp-out .withheld", has_text="digest does not match").wait_for()
    if app.locator("#rp-other option").count() > 1:            # another run of this target is held (always in the static preview)
        app.select_option("#rp-other", index=1)
        app.click("#rp-compare-run")
        pw.expect(app.locator("#rp-status")).to_contain_text("methodological")
    else:
        assert app.mode == "server"
    app.click("[data-ipanel=gate]")
    c = _dl_json(app, "#gt-capsule")
    assert c["schema"] == "skytrace.capsule/1" and len(c["digest"]) == 64
    app.locator("#gt-capsules tbody tr").first.wait_for(timeout=30000)
    k = _dl_json(app, "#gt-export")
    assert k["schema"] == "skytrace.knowledge/1" and k["entities"] and all(e["status"] for e in k["entities"])
    with app.expect_download() as d:
        app.click("#gt-handoff")
    assert "## How to reproduce" in Path(d.value.path()).read_text()
    app.click("[data-ipanel=command]")


# ------------------------------------------------------------------ Phase 10: six languages and the signature systems
def test_l1_language_switch_persists_and_localises(app):
    n0 = len(app.errors)                  # errors from earlier tests (e.g. the deliberately refused import) are not this test's
    app.select_option("#lang-select", "bn")
    pw.expect(app.locator(".nav button[data-ws=command]")).not_to_have_text("Command Center")
    assert app.evaluate("document.documentElement.lang") == "bn"
    pw.expect(app.locator(".level-switch button[data-level=explore]")).to_have_text("অন্বেষক")
    app.reload()
    app.locator("#data-pill").wait_for()
    pw.expect(app.locator("html")).to_have_attribute("lang", "bn")
    assert app.evaluate("localStorage.getItem('skytrace.lang')") == "bn"
    app.click("#run-btn")                                    # a reload in server mode forgets the open run: restore it for later tests
    pw.expect(app.locator("#run-btn .spinner")).to_have_count(0, timeout=120000)
    pw.expect(app.locator("#run-btn")).to_be_enabled()
    app.click("#settings-btn")
    pw.expect(app.locator("#settings .set-lang.current")).to_have_attribute("data-lang", "bn")
    assert app.locator("#settings [data-set-level=research]").bounding_box()["height"] >= 20   # the level switch is not collapsed
    app.select_option("#set-digits", "latn")
    app.keyboard.press("Escape")
    app.select_option("#lang-select", "de")
    pw.expect(app.locator(".level-switch button[data-level=research]")).to_have_text("Fortgeschritten")
    app.click(".level-switch button[data-level=research]")
    app.click(".nav button[data-ws=languages]")
    app.locator("#xs-input").wait_for(timeout=30000)
    app.fill("#xs-input", "নিজস্ব গতি")
    app.locator("#xs-table tr[data-xs='term:proper-motion']").wait_for()
    pw.expect(app.locator("#xs-method")).to_contain_text("keine semantische Suche")
    app.select_option("#lang-select", "en")
    pw.expect(app.locator(".nav button[data-ws=command]")).to_have_text("Command Center")
    app.click("#settings-btn")
    app.select_option("#set-digits", "locale")
    app.keyboard.press("Escape")
    assert app.errors[n0:] == [], app.errors[n0:]


def test_l2_signal_world_and_explanations(app):
    n0 = len(app.errors)                  # errors from earlier tests (e.g. the deliberately refused import) are not this test's
    _research_level(app)
    app.click(".nav button[data-ws=signal]")
    app.locator("#sig-selection tbody tr").first.wait_for(timeout=120000)
    assert app.locator("#sig-selection tbody tr").count() == 8
    pw.expect(app.locator("#sig-selection tr[data-sig-method=lomb_scargle]")).to_contain_text("does not apply")
    pw.expect(app.locator("#sig-bic-reading")).to_contain_text("not reported")
    app.click(".nav button[data-ws=world]")
    app.locator("#wq-count").wait_for(timeout=60000)
    app.select_option("#wq-from", "hypothesis")
    pw.expect(app.locator("#wq-count")).not_to_contain_text("0 of")
    app.click("[data-world-tab=convergence]")
    pw.expect(app.locator("#world-out")).to_contain_text("runs of the same data bundle never confirm one another")
    app.click("[data-world-tab=leads]")
    pw.expect(app.locator("#world-out")).to_contain_text("not a paradox")
    app.click("[data-world-tab=timeline]")
    pw.expect(app.locator("#world-out")).to_contain_text("not determined")
    app.click(".nav button[data-ws=languages]")
    app.click("[data-lang-tab=explain]")
    app.locator("[data-explain]").first.wait_for(timeout=60000)
    for q in app.locator("[data-explain]").all():
        assert q.locator(".explain-layer").count() == 8
    app.click("[data-lang-tab=terms]")
    assert app.locator("#term-table tbody tr").count() >= 48
    app.click("[data-lang-tab=quality]")
    pw.expect(app.locator("#tq-table")).to_contain_text("Reviewed by a native speaker")
    app.click("#overflow-check")
    app.locator("#overflow-result").wait_for()
    assert app.errors[n0:] == [], app.errors[n0:]


def test_l3_gateway_handoff_reports_and_recorder(app, tmp_path):
    n0 = len(app.errors)                  # errors from earlier tests (e.g. the deliberately refused import) are not this test's
    _research_level(app)
    app.click(".nav button[data-ws=gateway]")
    h = _dl_json(app, "#ho-export")
    assert h["schema"] == "skytrace.handoff/1" and h["language"]["content"] == "en" and len(h["digest"]) == 64
    p = tmp_path / "h.json"
    p.write_text(json.dumps(h))
    app.set_input_files("#ho-file", str(p))
    app.locator("#ho-valid").wait_for()
    h["established"][0]["category"] = "discovery"
    p.write_text(json.dumps(h))                              # the same file, edited: it must be checked again
    app.set_input_files("#ho-file", str(p))
    pw.expect(app.locator("#ho-invalid")).to_contain_text("digest")
    app.click("[data-gw-tab=reports]")
    with app.expect_download() as d:
        app.click("#report-langs [data-report-lang=bn]")
    t = Path(d.value.path()).read_text()
    assert t.startswith("<!-- language: বাংলা (bn)") and "machine-translated" in t
    pw.expect(app.locator(".nav button[data-ws=command]")).to_have_text("Command Center")    # the interface language is unchanged
    app.click("[data-gw-tab=recorder]")
    app.locator("#fr-slider").wait_for()
    pw.expect(app.locator("#gw-out")).to_contain_text("not cryptographic immutability")
    app.click("[data-gw-tab=bundle]")
    pw.expect(app.locator("#osg-checks")).to_contain_text("Software licence declared")
    with app.expect_download() as d:
        app.click("#osg-download")
    assert Path(d.value.path()).read_bytes()[:2] == b"PK"
    assert app.errors[n0:] == [], app.errors[n0:]


def test_l4_phase10_sections_in_existing_workspaces(app):
    n0 = len(app.errors)                  # errors from earlier tests (e.g. the deliberately refused import) are not this test's
    _research_level(app)
    app.click(".nav button[data-ws=negative]")
    app.locator("#negx tbody tr").first.wait_for(timeout=60000)
    assert app.locator("#negx-dist option").count() == 10
    app.click(".nav button[data-ws=compiler]")
    app.locator("#kcomp tr[data-kcomp]").first.wait_for(timeout=60000)
    app.click(".nav button[data-ws=radar]")
    app.locator("#ext-sources tbody tr").first.wait_for(timeout=60000)
    assert app.locator("#ext-sources tbody tr").count() == app.locator("#ext-sources tbody tr", has_text="not connected").count() == 6
    app.click(".nav button[data-ws=autopilot]")
    app.click("#dir-start")
    app.locator("#dir-log tbody tr").first.wait_for()
    first = app.locator("#dir-steps tr[data-dir-step]").first.get_attribute("data-dir-step")
    pw.expect(app.locator(f"[data-dir-execute={first}]")).to_be_disabled()
    app.click(f"[data-dir-approve={first}]")
    pw.expect(app.locator(f"[data-dir-execute={first}]")).to_be_enabled()
    app.click(".nav button[data-ws=experiments]")
    app.locator("#market-table tbody tr").first.wait_for(timeout=60000)
    assert app.locator("#market-table tr", has_text="not recommended").count() >= 1
    app.click(".nav button[data-ws=review]")
    app.click("button[data-rtab=agents]")
    pw.expect(app.locator("#agents")).to_contain_text("not independent confirmation")
    assert app.errors[n0:] == [], app.errors[n0:]
