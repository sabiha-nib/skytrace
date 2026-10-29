"""End-to-end acceptance test in a real browser (Playwright + Chromium), with OFFLINE=1.

Starts the actual server on a free port, drives the main user journey, records
every network request the page makes, and saves screenshots to docs/screenshots/.
Run: pytest tests/e2e -m e2e   (needs Playwright with Chromium installed)
"""

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


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = free_port()
    env = {**os.environ, "OFFLINE": "1", "SKYTRACE_RECORDS_DIR": str(tmp_path_factory.mktemp("records")),
           "META_API_KEY": "", "MODEL_API_KEY": "", "NO_PROXY": "127.0.0.1,localhost"}
    proc = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--port", str(port)], env=env, cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if requests.get(base + "/api/status", timeout=1, proxies={"http": None, "https": None}).ok:
                break
        except requests.RequestException:
            time.sleep(0.25)
    else:
        proc.kill()
        raise RuntimeError(proc.stdout.read().decode())
    yield base
    proc.terminate()
    proc.wait(10)


@pytest.fixture(scope="module")
def page(server):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.errors, pg.requests = [], []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
        pg.on("request", lambda r: pg.requests.append(r.url))
        pg.base = server
        yield pg
        b.close()


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / f"{name}.png"))


def test_01_starts_and_lists_targets(page):
    page.goto(page.base + "/#/explorer?target=barnards-star")
    page.locator("#target-select option").first.wait_for(state="attached")
    opts = page.locator("#target-select option").all_text_contents()
    assert any("Barnard" in o and "no data yet" in o for o in opts)
    assert any("SYN-VAR-1 (synthetic)" in o for o in opts)
    page.get_by_text("No SPHEREx data stored for Barnard's Star yet").wait_for()
    assert page.get_by_text("python scripts/acquire_targets.py --target barnards-star").is_visible()
    assert page.locator("#offline-pill").is_visible()
    assert page.locator("#run-btn").is_disabled()
    shot(page, "real-target-no-data")


def test_02_synthetic_is_unmistakable(page):
    page.select_option("#target-select", "syn-var-1")
    page.locator("#data-pill", has_text="Synthetic test data").wait_for()
    assert page.get_by_text("Synthetic test data.").first.is_visible()
    page.locator("#obs-meta", has_text="synthetic").wait_for()


def test_03_run_analysis_and_ruler(page):
    page.click("#run-btn")
    page.locator("#run-btn", has_text="Re-run analysis").wait_for(timeout=90000)
    page.locator("#ruler-caption", has_text="wavelength-matched pairs").wait_for()
    assert page.locator("#ruler-svg .pair-link").count() > 0
    page.locator("#obs-meta", has_text="Aperture flux").wait_for()
    shot(page, "explorer")


def test_04_time_machine_compatibility(page):
    page.click(".nav button[data-ws=time]")
    page.locator("#tm-banner", has_text="Wavelength-matched pair").wait_for()
    assert page.locator(".segmented button", has_text="Difference").is_enabled()
    page.locator(".segmented button", has_text="Difference").click()
    page.locator("#tm-details", has_text="z =").wait_for()
    shot(page, "time-machine-matched")
    page.locator(".partner", has_text="Brightness comparison unavailable").first.click()
    page.locator("#tm-banner", has_text="Not comparable for brightness").wait_for()
    assert page.locator(".segmented button", has_text="Difference").is_disabled()
    shot(page, "time-machine-incompatible")


def test_05_lab_tabs_and_rerun(page):
    page.click(".nav button[data-ws=lab]")
    page.locator(".outcome", has_text="Variability candidate").wait_for()
    for tab in ["Motion", "Brightness", "Spectrum", "Measurements"]:
        page.locator(".tabs button", has_text=tab).click()
        page.locator("[role=tabpanel] svg.chart, [role=tabpanel] table").first.wait_for()
    page.locator(".tabs button", has_text="Re-run & compare").click()
    page.locator("label", has_text="Aperture radius").locator("input").fill("2.5")
    page.locator("button", has_text="Re-run analysis").last.click()
    page.locator(".diff-table td.changed").first.wait_for(timeout=90000)
    assert page.locator(".diff-table td.changed").count() >= 1
    shot(page, "lab-rerun")
    page.locator(".tabs button", has_text="Outcomes").click()
    shot(page, "lab-outcomes")


def test_06_evidence_graph_traces_claim(page):
    page.click(".nav button[data-ws=graph]")
    page.locator(".graph-svg .node[data-id='claim:variability']").click()
    page.locator("#graph-detail", has_text="Traced observations").wait_for()
    assert page.locator(".graph-svg .node.dim").count() > 0 and page.locator(".graph-svg .edge.hl").count() > 0
    shot(page, "evidence-graph")


def test_07_copilot_uses_tools_and_labels_mode(page):
    page.locator("#suggestions .chip").first.click()
    page.locator(".msg.bot .mode", has_text="Local assistant").first.wait_for(timeout=60000)
    page.locator(".msg.bot details summary", has_text="Tool activity").first.wait_for()
    txt = page.locator(".msg.bot .answer").last.text_content()
    assert "synthetic" in txt.lower()
    page.fill("#ask-input", "Why was an observation excluded?")
    page.click("#ask-btn")
    page.locator(".msg.bot").nth(1).locator(".answer").wait_for(timeout=60000)
    shot(page, "copilot")


def test_08_save_replay_reopen(page):
    page.click(".nav button[data-ws=records]")
    page.fill("input[aria-label='Investigation name']", "E2E variability check")
    page.click("button:has-text('Save investigation')")
    row = page.locator("tr", has_text="E2E variability check")
    row.wait_for()
    row.locator("button", has_text="Replay").click()
    row.get_by_text("reproduced: identical content hash").wait_for(timeout=90000)
    shot(page, "records")
    row.locator("button", has_text="Open").click()
    page.locator(".nav button[data-ws=lab][aria-current=page]").wait_for()
    page.get_by_text("Reopened “E2E variability check”").first.wait_for()


def test_09_no_external_requests_and_no_errors(page):
    external = [u for u in page.requests if not u.startswith(page.base) and not u.startswith("data:")]
    assert external == [], external
    assert page.errors == [], page.errors


def test_10_mobile_layout(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.click(".nav button[data-ws=explorer]")
    page.wait_for_timeout(500)
    # the page forbids eval (CSP), so check the main column's box instead of evaluating scripts
    box = page.locator("#main").bounding_box()
    assert box["width"] <= 390
    shot(page, "mobile")
    page.set_viewport_size({"width": 1440, "height": 900})
