"""Measure what a user waits for, in both delivery modes, on this machine. Writes docs/performance.json.

    python scripts/measure_performance.py

Wall-clock timings (median of N runs) from Python around Playwright waits and HTTP requests; no in-page script is
evaluated (the app's content security policy forbids it). Numbers describe this machine only.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
NOPROXY = {"http": None, "https": None}
N = 3


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def up(url: str) -> None:
    for _ in range(200):
        try:
            if requests.get(url, timeout=1, proxies=NOPROXY).ok:
                return
        except requests.RequestException:
            time.sleep(0.1)
    raise RuntimeError(url)


def timed(fn) -> float:
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


def med(xs):
    return round(statistics.median(xs), 3)


def page_timings(base: str, mode: str) -> dict:
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        loads, ready, disc, arena, unc = [], [], [], [], []
        for _ in range(N):
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()
            t0 = time.perf_counter()
            pg.goto(base + "#/lab?target=syn-var-1", wait_until="load")
            loads.append(time.perf_counter() - t0)
            if mode == "server":
                pg.locator("#data-pill", has_text="Synthetic").wait_for()
                pg.click("#run-btn")
            pg.locator(".outcome").first.wait_for(timeout=180000)
            ready.append(time.perf_counter() - t0)
            disc.append(timed(lambda: (pg.click(".nav button[data-ws=discovery]"), pg.locator(".engine-head").wait_for(timeout=60000))))
            arena.append(timed(lambda: (pg.click(".nav button[data-ws=arena]"), pg.locator(".matrix").wait_for(timeout=60000))))
            pg.click(".nav button[data-ws=lab]")
            unc.append(timed(lambda: (pg.locator("#lab-body .tabs button", has_text="Uncertainty").click(),
                                      pg.locator("#lab-body h3", has_text="Motion uncertainty components").wait_for(timeout=60000))))
            ctx.close()
        b.close()
    out["page_load_s"] = med(loads)
    out["first_result_s"] = med(ready)
    out["first_result_includes"] = "running the full analysis on the server" if mode == "server" else "loading the precomputed default run"
    out["discovery_engine_first_render_s"] = med(disc)
    out["hypothesis_arena_render_s"] = med(arena)
    out["uncertainty_tab_render_s"] = med(unc)
    return out


def main() -> int:
    res = {"machine": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count()},
           "runs_per_measurement": N, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    port = free_port()
    env = {**os.environ, "OFFLINE": "1", "META_API_KEY": "", "MODEL_API_KEY": "", "NO_PROXY": "127.0.0.1,localhost",
           "SKYTRACE_RECORDS_DIR": str(ROOT / "dist" / ".perf-records")}
    proc = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--port", str(port)], env=env, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/"
    try:
        up(base + "api/status")
        api = {}
        for tid in ("syn-var-1", "syn-hpm-1"):
            an, di, pk, gr = [], [], [], []
            for _ in range(N):
                t = time.perf_counter()
                r = requests.post(base + f"api/targets/{tid}/analyze", json={"params": {}}, proxies=NOPROXY, timeout=600)
                an.append(time.perf_counter() - t)
                iid = r.json()["investigation_id"]
                di.append(timed(lambda: requests.get(base + f"api/investigations/{iid}/discovery", proxies=NOPROXY).raise_for_status()))
                gr.append(timed(lambda: requests.get(base + f"api/investigations/{iid}/graph", proxies=NOPROXY).raise_for_status()))
                pk.append(timed(lambda: requests.get(base + f"api/investigations/{iid}/package.zip", proxies=NOPROXY).raise_for_status()))
            size = len(requests.get(base + f"api/investigations/{iid}/package.zip", proxies=NOPROXY).content)
            st = timed(lambda: requests.post(base + f"api/targets/{tid}/stability", json={"params": {}}, proxies=NOPROXY, timeout=900).raise_for_status())
            api[tid] = {"analysis_s": med(an), "discovery_report_s": med(di), "evidence_graph_s": med(gr),
                        "package_zip_s": med(pk), "package_zip_bytes": size, "stability_check_s": round(st, 3)}
        res["server_api"] = api
        res["server_page"] = page_timings(base, "server")
    finally:
        proc.terminate()
        proc.wait(10)
    prev = ROOT / "dist" / "preview"
    files = [p for p in prev.rglob("*") if p.is_file()]
    res["static_preview"] = {"files": len(files), "bytes": sum(p.stat().st_size for p in files),
                             "largest_files": sorted(((p.stat().st_size, str(p.relative_to(prev))) for p in files), reverse=True)[:5]}
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", "-d", str(prev), "--bind", "127.0.0.1", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        up(f"http://127.0.0.1:{port}/index.html")
        res["static_page"] = page_timings(f"http://127.0.0.1:{port}/", "static")
    finally:
        proc.terminate()
        proc.wait(10)
    (ROOT / "docs" / "performance.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
