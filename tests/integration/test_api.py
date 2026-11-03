"""HTTP API integration tests against the real server process (OFFLINE=1, bundled synthetic data)."""

import json
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
    env = {**os.environ, "OFFLINE": "1", "SKYTRACE_RECORDS_DIR": str(tmp_path_factory.mktemp("rec")), "META_API_KEY": "",
           "SKYTRACE_SESSIONS_DIR": str(tmp_path_factory.mktemp("sessions")), "SKYTRACE_SYNTHLAB_DIR": str(tmp_path_factory.mktemp("synthlab"))}
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


def test_record_export_and_verified_import(base):
    s = post(base, "/api/targets/syn-hpm-1/analyze", {"params": {}}).json()
    r = get(base, f"/api/investigations/{s['investigation_id']}/record.json")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    text = r.text
    ok = requests.post(base + "/api/records/import", data=('{"name": "imp", "record": ' + text + "}").encode(),
                       headers={"Content-Type": "application/json"}, timeout=60, proxies=NOPROXY)
    assert ok.status_code == 200, ok.text
    d = ok.json()
    assert d["content_hash_verified"] is True and d["same_bundle"] is True
    listed = {x["record_id"]: x for x in get(base, "/api/records").json()["records"]}
    assert listed[d["record_id"]]["imported"] is True
    rep = post(base, f"/api/records/{d['record_id']}/replay").json()
    assert rep["reproduced"] is True
    import json as _json
    rec = _json.loads(text)
    rec["events"][2]["detail"] = "tampered"
    bad = post(base, "/api/records/import", {"record": rec})
    assert bad.status_code == 400 and "content hash" in bad.json()["error"]
    rec2 = _json.loads(text)
    rec2["parameters"]["bundle"] = "barnards-star"
    assert post(base, "/api/records/import", {"record": rec2}).status_code == 400
    assert post(base, "/api/records/import", {"record": {"x": 1}}).status_code == 400


def test_phase5_discovery_package_capabilities_and_vault(base):
    import hashlib
    import io
    import zipfile
    s = post(base, "/api/targets/syn-var-1/analyze", {"params": {}}).json()
    iid = s["investigation_id"]
    caps = get(base, "/api/capabilities").json()
    assert caps["version"] == "CAPREG-3" and any(c["id"] == "archive" and c["available"] is False for c in caps["capabilities"])
    d = get(base, f"/api/investigations/{iid}/discovery").json()
    assert d["method"] == "DISC-1" and d["content_hash"] == s["record"]["content_hash"]
    assert {"inventory", "questions", "hypotheses", "uncertainty", "next_steps"} <= set(d)
    z = get(base, f"/api/investigations/{iid}/package.zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    names = {n.split("/", 1)[1]: n for n in zf.namelist()}
    for line in zf.read(names["SHA256SUMS"]).decode().splitlines():
        h, f = line.split("  ")
        assert hashlib.sha256(zf.read(names[f])).hexdigest() == h
    assert get(base, f"/api/investigations/{iid}/package.zip").content == z.content          # deterministic
    ctx = {"question": "Did it dim?", "hypotheses": [{"text": "intrinsic dimming", "tests": ["V-INTRINSIC/T-SIG"]}]}
    r = post(base, "/api/records", {"investigation_id": iid, "name": "vault", "tags": ["dimming", "dimming", " syn "],
                                    "context": ctx}).json()
    rid = r["record_id"]
    full = get(base, f"/api/records/{rid}").json()
    assert full["tags"] == ["dimming", "syn"] and full["context"] == ctx and full["outcomes"][2]["category"] == "variability_candidate"
    up = requests.patch(base + f"/api/records/{rid}", json={"name": "renamed", "tags": ["x"]}, timeout=30, proxies=NOPROXY).json()
    assert up["name"] == "renamed" and up["tags"] == ["x"] and up["modified_at"]
    assert requests.patch(base + f"/api/records/{rid}", json={"name": "  "}, timeout=30, proxies=NOPROXY).status_code == 400
    big = {"notes": "x" * 60_000}
    assert requests.patch(base + f"/api/records/{rid}", json={"context": big}, timeout=30, proxies=NOPROXY).status_code == 413
    c = post(base, f"/api/records/{rid}/clone").json()
    assert c["cloned_from"] == rid and c["name"] == "Copy of renamed"
    listed = {x["record_id"]: x for x in get(base, "/api/records").json()["records"]}
    assert listed[c["record_id"]]["content_hash"] == listed[rid]["content_hash"]


def test_phase6_research_planner_sessions_experiments_connectors(base):
    sp = get(base, "/api/specs").json()
    assert sp["session_schema_id"] == "skytrace.research_session/1" and "templates" in sp["planner"]
    iid = post(base, "/api/targets/syn-var-1/analyze", {"params": {}}).json()["investigation_id"]
    r = get(base, f"/api/investigations/{iid}/research").json()
    assert r["compat"]["method"] == "COMPAT-1" and r["quality"]["method"] == "DQ-1"
    assert r["ledger"]["method"] == "LEDGER-1" and r["radar"]["method"] == "RADAR-1"
    assert not any(k in r["quality"] for k in ("score", "overall_score", "grade")) and all(set(c) >= {"outcome", "rule", "items"} for c in r["quality"]["checks"])
    # planner: the server fixes where it runs; blocked steps say why
    p = post(base, "/api/plan", {"question": "Could this source have changed between the two recorded observation epochs?",
                                 "facts": {"has_target_data": True, "has_run": True, "run_hash": "x", "static": True}}).json()
    assert p["intent"]["kind"] == "change" and any(s["status"] == "blocked" and "two observations" in s["note"] for s in p["steps"])
    assert post(base, "/api/plan", {"question": " "}).status_code == 400
    # sessions: create, update, integrity, import refusal of a tampered copy, migration from a saved record
    s = post(base, "/api/sessions", {"name": "API test", "target_id": "syn-var-1"}).json()
    assert len(s["content_hash"]) == 64
    s["question"] = {"id": "Q-VAR", "text": "Did it change?"}
    s2 = requests.put(base + f"/api/sessions/{s['session_id']}", json={"session": s}, timeout=30, proxies=NOPROXY).json()
    assert s2["content_hash"] != s["content_hash"]
    got = get(base, f"/api/sessions/{s['session_id']}").json()
    assert got["_verification"]["hash_ok"] is True
    bad = dict(s2, name="tampered")
    assert post(base, "/api/sessions/import", {"session": bad}).status_code == 400
    assert post(base, "/api/sessions/import", {"session": {"schema": "skytrace.research_session/9"}}).status_code == 400
    imp = post(base, "/api/sessions/import", {"session": s2}).json()
    assert imp["hash_verified"] and imp["session_id"] != s2["session_id"]
    lst = get(base, "/api/sessions").json()
    assert {x["session_id"] for x in lst["sessions"]} >= {s["session_id"], imp["session_id"]}
    rec = post(base, "/api/records", {"investigation_id": iid, "name": "for migration", "context": {"question": "Q-MOT", "question_text": "moves?"}}).json()
    mig = post(base, f"/api/sessions/from-record/{rec['record_id']}").json()
    assert mig["question"]["id"] == "Q-MOT" and mig["history"][-1]["kind"] == "session.migrate"
    assert requests.delete(base + f"/api/sessions/{imp['session_id']}", timeout=30, proxies=NOPROXY).status_code == 200
    # experiments: validation before execution; a reproducibility run gives identical hashes
    assert post(base, "/api/experiments", {"target_id": "syn-var-1", "template": "parameter", "configs": [{"aperture_radius_px": 9}]}).status_code == 400
    ex = post(base, "/api/experiments", {"target_id": "syn-var-1", "template": "reproducibility"}).json()
    assert ex["evaluation"]["passed"] is True and ex["n_analyses"] == 2 and "not thereby a valid experiment" in ex["validity_note"]
    # provenance verification (PROVCHECK-1) without re-run
    pv = post(base, f"/api/investigations/{iid}/provenance", {"rerun": False}).json()
    assert pv["checks"] and all("id" in c for c in pv["checks"])
    # connectors: previews validate and never send
    c = get(base, "/api/connectors").json()
    assert {x["id"] for x in c["connectors"]} == {"spherex_sia", "spherex_tap", "simbad_resolve", "gaia_cone"}
    assert all(x["usable_now"] is False for x in c["connectors"])          # OFFLINE=1
    pr = post(base, "/api/connectors/spherex_sia/preview", {"params": {"ra": 10, "dec": 5, "release": "QR3", "radius_arcsec": 1}}).json()
    assert pr["ok"] and pr["sent"] is False and pr["request"]["url"] == "https://irsa.ipac.caltech.edu/SIA"
    assert post(base, "/api/connectors/spherex_sia/preview", {"params": {"ra": 400}}).json()["ok"] is False
    # workflows
    w = sp["workflow_templates"][0]
    assert post(base, "/api/workflows/validate", {"workflow": w}).json()["valid"]
    assert not post(base, "/api/workflows/validate", {"workflow": dict(w, steps=[{"id": "x", "action": "rm_rf", "depends": []}])}).json()["valid"]


def test_phase7_frontier_counterfactual_reproduce_synthetic(base):
    r = post(base, "/api/targets/syn-var-1/analyze", {"params": {}})
    iid = r.json()["investigation_id"]
    f = post(base, f"/api/investigations/{iid}/frontier", {}).json()
    assert {"spe", "asl", "info", "review", "repro", "twins"} <= set(f)
    assert [l["n"] for l in f["spe"]["layers"]] == [1, 2, 3, 4, 5, 6] and f["info"]["probability_model"] is None
    assert post(base, f"/api/investigations/{iid}/frontier", {"stability": "x"}).status_code == 400
    c = post(base, "/api/counterfactuals", {"target_id": "syn-var-1", "baseline_investigation_id": iid,
                                                  "scenario": {"kind": "threshold", "change": {"variability_z": 9}}}).json()
    assert c["baseline"]["intact"] and c["scenario"]["baseline_hash"] == f["content_hash"] and c["twin"]["kind"] == "scenario"
    assert post(base, "/api/counterfactuals", {"target_id": "syn-var-1", "scenario": {"kind": "parameter", "change": {"aperture_radius_px": 99}}}).status_code == 400
    assert post(base, "/api/counterfactuals", {"target_id": "../etc", "scenario": {"kind": "method", "change": {"variability_method": "PAIRDIFF-1"}}}).status_code in (400, 404)
    assert post(base, f"/api/investigations/{iid}/reproduce", {}).json()["verdict"] == "reproduced"
    assert post(base, "/api/synthetic", {"scenario": {"seed": 1}}).status_code == 400
    sp = get(base, "/api/specs").json()["frontier"]
    assert sp["counterfactual"]["presets"] and sp["autopilot"]["levels"] and sp["twin"]["semantics"]


def test_phase8_epistemic_reproduce_integrity(base):
    iid = post(base, "/api/targets/syn-var-1/analyze", {"params": {}}).json()["investigation_id"]
    d = get(base, f"/api/investigations/{iid}/epistemic").json()
    assert {"graph", "genome", "compile", "boundary", "stress", "negative", "blindspot", "uflow", "lineage", "breakpoints", "inspect", "models",
            "future", "next", "questions", "facts", "report_check", "review"} <= set(d)
    assert d["compile"]["outcome"] == "requires scientific review" and "does not mean" in d["compile"]["meaning"]
    assert get(base, f"/api/investigations/{iid}/epistemic").json() == d  # cached by content hash, same answer
    pair = next(n["id"] for n in d["graph"]["nodes"] if n["id"].startswith("pair:"))
    lin = get(base, f"/api/investigations/{iid}/lineage?result={pair}").json()
    assert lin["result"] == pair and lin["stages"]
    assert get(base, f"/api/investigations/{iid}/lineage?result=pair:nope").status_code == 404
    r = post(base, f"/api/investigations/{iid}/reproduce-x", {}).json()
    assert r["verdict"] == "exact reproduction"
    rep = get(base, f"/api/investigations/{iid}/report.md").text
    ok = post(base, "/api/integrity", {"investigation_id": iid, "text": rep}).json()
    assert ok["outcome"] == "ready"
    bad = post(base, "/api/integrity", {"investigation_id": iid, "text": "We discovered a new variable star with 99% probability."}).json()
    assert bad["outcome"] == "needs attention" and any(not c["ok"] and c["id"] == "I6" for c in bad["checks"])
    assert post(base, "/api/integrity", {"investigation_id": iid, "text": 5}).status_code == 400
    assert post(base, "/api/simulation-audit", {"scenario": {"seed": 1}}).status_code == 400
    assert post(base, "/api/simulation-audit", {"scenario": {}, "seeds": [1, 2, 3, 4]}).status_code == 400
    sp = get(base, "/api/specs").json()["epistemic"]
    assert len(sp["statuses"]) == 10 and len(sp["kinds"]) == 15 and len(sp["stress"]["modes"]) == 10


def test_phase9_intelligence_corpus_oracle_whatif_reproduction(base):
    iid = post(base, "/api/targets/syn-var-1/analyze", {"params": {}}).json()["investigation_id"]
    iid2 = post(base, "/api/targets/syn-hpm-1/analyze", {"params": {}}).json()["investigation_id"]
    d = get(base, f"/api/investigations/{iid}/intelligence").json()
    assert {"entities", "genomes", "adversary", "gate", "debt", "causal", "oracle", "negotiation", "instrumental", "fingerprint", "budget",
            "whatif", "reproduction", "unknown"} <= set(d)
    assert d["entities"]["errors"] == [] and d["gate"]["outcome"] == "not ready" and len(d["unknown"]["regions"]) == 8
    c = get(base, "/api/intelligence/corpus").json()
    assert c["n"] >= 2 and c["memory"]["items"] and all(x["status"] != "verified" for x in c["memory"]["items"] if x["kind"] == "explanation")
    o = post(base, "/api/oracle", {"investigation_id": iid2, "spec": {"question": "motion", "candidates": [{"added_years_after_last": [1.0]}]}}).json()
    assert o["available"] and o["information_gain"] is None and o["hypothetical"]
    assert post(base, "/api/oracle", {"investigation_id": iid2, "spec": {"question": "motion", "candidates": [{"added_years_after_last": [99]}]}}).status_code == 400
    v = post(base, "/api/whatif/visit", {"investigation_id": iid2, "dt_years": 1.0, "position": "static"}).json()
    assert v["hypothetical"] and v["after"]["snr"] < v["before"]["snr"]
    assert post(base, "/api/whatif/visit", {"investigation_id": iid2, "dt_years": 99}).status_code == 400
    m = get(base, f"/api/investigations/{iid}/reproduction-manifest").json()
    m2 = get(base, f"/api/investigations/{iid2}/reproduction-manifest").json()
    assert m == d["reproduction"]
    assert post(base, "/api/reproduction/compare", {"a": m, "b": m}).json()["status"] == "exact match"
    assert "different input data" in post(base, "/api/reproduction/compare", {"a": m, "b": m2}).json()["classes"]
    bad = dict(m, outcomes={})
    assert post(base, "/api/reproduction/compare", {"a": bad, "b": m}).status_code == 400
    assert get(base, f"/api/investigations/{iid}/intelligence").json()["content_hash"] == d["content_hash"]
    sp = get(base, "/api/specs").json()["intelligence"]
    assert len(sp["entity"]["types"]) >= 22 and len(sp["unknown"]["regions"]) == 8 and len(sp["gate"]["requirements"]) == 8


def test_phase10_universal_and_multilingual_report(base):
    iid = post(base, "/api/targets/syn-var-1/analyze", {"params": {}}).json()["investigation_id"]
    u = get(base, f"/api/investigations/{iid}/universal").json()
    assert {"signal", "convergence", "leads", "negative", "multimodal", "world", "opportunities", "compiler", "sources", "agents", "explain",
            "timeline", "director", "market"} <= set(u)
    assert all(s["state"] == "not connected" and s["updates"] == [] for s in u["sources"]["sources"])
    assert {i["novelty"]["scope"] for i in u["opportunities"]["items"]} <= {"new to this investigation", "new to this collection"}
    en = get(base, f"/api/investigations/{iid}/report.md").text
    for lang in ("bn", "hi", "es", "fr", "de"):
        r = get(base, f"/api/investigations/{iid}/report.md?lang={lang}")
        assert r.status_code == 200 and r.headers["content-language"] == lang and f".{lang}.md" in r.headers["content-disposition"]
        t = r.text
        assert t.startswith("<!-- language:") and "machine-translated by an AI model" in t
        body = t.split("\n", 2)[2]
        # the same numbers, in the same order, outside the translation notice
        from skytrace import i18n
        notice = [ln for ln in body.splitlines() if ln.startswith("> ") and "(" + lang + ")" in ln]
        assert len(notice) == 1
        assert sorted(i18n.numbers("\n".join(ln for ln in body.splitlines() if ln not in notice))) == sorted(i18n.numbers(en))
    assert get(base, f"/api/investigations/{iid}/report.md?lang=xx").headers["content-language"] == "en"
