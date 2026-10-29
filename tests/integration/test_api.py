"""HTTP API integration tests against the real server process (OFFLINE=1, bundled synthetic data)."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]
NOPROXY = {"http": None, "https": None}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    env = {**os.environ, "OFFLINE": "1", "SKYTRACE_RECORDS_DIR": str(tmp_path_factory.mktemp("rec")), "META_API_KEY": ""}
    p = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--port", str(port)], env=env, cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            requests.get(url + "/api/status", timeout=1, proxies=NOPROXY)
            break
        except requests.RequestException:
            time.sleep(0.25)
    yield url
    p.terminate()
    p.wait(10)


def get(base, path, **kw):
    return requests.get(base + path, timeout=60, proxies=NOPROXY, **kw)


def post(base, path, body=None):
    return requests.post(base + path, json=body if body is not None else {}, timeout=120, proxies=NOPROXY)


def test_status_and_security_headers(base):
    r = get(base, "/api/status")
    d = r.json()
    assert d["offline"] is True and d["meta"]["configured"] is False
    assert all(b["ok"] for b in d["bundles"])
    assert "script-src 'self'" in r.headers["content-security-policy"] and r.headers["x-content-type-options"] == "nosniff"
    assert get(base, "/").status_code == 200


def test_targets_mark_real_without_data(base):
    t = {x["target_id"]: x for x in get(base, "/api/targets").json()["targets"]}
    assert t["barnards-star"]["kind"] is None and "acquire_targets.py" in t["barnards-star"]["acquire_command"]
    assert t["syn-var-1"]["kind"] == "synthetic" and t["syn-var-1"]["real_target"] is False
    r = get(base, "/api/targets/barnards-star")
    assert r.status_code == 404 and "acquire" in r.json()["error"]


@pytest.mark.parametrize("path", ["/api/targets/..%2F..%2Fetc/observations/x/image", "/api/targets/syn-var-1/observations/..%2F..%2Fsecret/image",
                                  "/api/records/..%2Fx", "/api/investigations/../../etc"])
def test_rejects_traversal(base, path):
    assert get(base, path).status_code in (400, 404)


def test_analysis_param_validation(base):
    assert post(base, "/api/targets/syn-var-1/analyze", {"params": {"aperture_radius_px": 50}}).status_code == 400
    assert post(base, "/api/targets/syn-var-1/analyze", {"params": {"__import__": 1}}).status_code == 400
    assert post(base, "/api/targets/syn-var-1/analyze", {"params": {"detectors": [7]}}).status_code == 400
    r = requests.post(base + "/api/targets/syn-var-1/analyze", data="not json", timeout=30, proxies=NOPROXY)
    assert r.status_code == 400


def test_full_api_cycle(base):
    a = post(base, "/api/targets/syn-hpm-1/analyze").json()
    iid = a["investigation_id"]
    assert a["synthetic"] is True and a["graph_counts"]["claim"] == 3
    key = next(e["data"]["key"] for e in a["record"]["events"] if e["step"] == "measure" and e["status"] == "ok")
    img = get(base, f"/api/targets/syn-hpm-1/observations/{key}/image").json()
    assert img["synthetic"] is True and img["width"] == 58 and img["file"]["sha256"]
    plates = {e["data"]["key"] for e in a["record"]["events"] if e["step"] == "measure" and (e["data"].get("plate") or {}).get("coeffs_deg")}
    acc = next(p for p in next(e for e in a["record"]["events"] if e["step"] == "pairs")["data"]["accepted"]
               if p["a"] in plates and p["b"] in plates)
    pair = get(base, f"/api/targets/syn-hpm-1/pair-image?a={acc['a']}&b={acc['b']}&inv={iid}").json()
    assert pair["comparison"]["compatible_for_photometry"] is True and "plate solutions" in pair["registration"]
    md = get(base, f"/api/investigations/{iid}/report.md")
    assert md.status_code == 200 and "SYNTHETIC DATA" in md.text
    ans = post(base, f"/api/investigations/{iid}/ask", {"question": "How does the result compare with the Gaia reference?"}).json()
    assert ans["mode"] == "local" and ans["ok"] and any(c["name"] == "get_astrometric_validation" for c in ans["tool_calls"])
    assert post(base, f"/api/investigations/{iid}/ask", {"question": ""}).status_code == 400
    rec = post(base, "/api/records", {"investigation_id": iid, "name": "api test", "transcript": [{"role": "user", "content": "q"}]}).json()
    rid = rec["record_id"]
    assert any(r["record_id"] == rid for r in get(base, "/api/records").json()["records"])
    rp = post(base, f"/api/records/{rid}/replay").json()
    assert rp["reproduced"] is True and rp["same_bundle"] is True
    opened = get(base, f"/api/records/{rid}").json()
    assert opened["bundle_available"] and opened["copilot_transcript"][0]["content"] == "q"
    assert requests.delete(base + f"/api/records/{rid}", timeout=10, proxies=NOPROXY).status_code == 200
    assert get(base, f"/api/records/{rid}").status_code == 404


def test_phase3_params_and_stability(base):
    assert post(base, "/api/targets/syn-hpm-1/analyze", {"params": {"apply_parallax": "yes"}}).status_code == 400
    assert post(base, "/api/targets/syn-hpm-1/analyze", {"params": {"wavelength_margin_um": 0.5}}).status_code == 400
    assert post(base, "/api/targets/syn-hpm-1/analyze", {"params": {"epoch_gap_days": True}}).status_code == 400
    r = post(base, "/api/targets/syn-var-1/stability", {"params": {"aperture_radius_px": 2.0}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["method"] == "STAB-1" and d["synthetic"] is True and len(d["runs"]) == 5
    assert set(d["stable"]) == {"data_quality", "motion", "variability"}
    assert d["base"]["categories"]["variability"] == "variability_candidate"
