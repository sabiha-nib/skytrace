"""Phase 6 engines on the synthetic fixtures: COMPAT-1/SEQ-1, DQ-1, LEDGER-1, RADAR-1, PLAN-1, EXP-1, MISSION-1, WF-1,
ACQ-2 — known answers, injected defects, and Python/browser parity for the planner, missions and workflows."""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from skytrace import (analysis, bundle as bmod, capabilities, compat, connectors, experiments, hypotheses, ledger, missions, planner,
                      quality, radar, session, workflows)
from skytrace.server.research import specs
from skytrace.view import InvestigationView, evidence_graph

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
_RUNS = {}


def run(tid):
    if tid not in _RUNS:
        bd = bmod.SYNTHETIC_ROOT / tid
        b = bmod.load(bd)
        rec = json.loads(json.dumps(analysis.run(b, {}).to_dict(), default=str))
        g = evidence_graph(InvestigationView(rec, b.discovery, b.manifest, b.inspection), tid)
        _RUNS[tid] = (bd, b, rec, g)
    return _RUNS[tid]


# ------------------------------------------------------------------ COMPAT-1 / SEQ-1
def test_matrix_is_the_logged_decisions():
    for tid in ("syn-var-1", "syn-hpm-1"):
        _, b, rec, _ = run(tid)
        r = compat.report(rec, b.discovery, b.manifest)
        pairs = next(e["data"] for e in rec["events"] if e["step"] == "pairs")
        assert r["matrix"]["counts"]["accepted"] == len(pairs["accepted"])
        for code, n in pairs["rejection_reasons"].items():
            assert r["matrix"]["counts"][code] == n
        keys = r["matrix"]["keys"]
        for d in pairs["accepted"]:
            assert r["matrix"]["cells"][keys.index(d["a"])][keys.index(d["b"])] == "accepted"


def test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits():
    _, b, rec, _ = run("syn-var-1")
    r = compat.report(rec, b.discovery, b.manifest)
    codes = compat.pair_codes(rec)
    assert r["sequences"]
    for s in r["sequences"]:
        m = s["members"]
        assert all(codes[(x, y)][0] == "accepted" for i, x in enumerate(m) for y in m[i + 1:])
        assert "nothing between them was observed or interpolated" in s["note"]
        if s["n_visits"] <= 2:
            assert s["note"].startswith(f"only {s['n_visits']} visits")
    # the injected third-pass dimming is a two-visit sequence on each detector (passes 1 and 3 sample the same wavelength)
    assert any(s["n_frames"] == 4 and s["n_visits"] == 2 for s in r["sequences"])


def test_duplicate_files_are_detected():
    _, b, rec, _ = run("syn-var-1")
    man = copy.deepcopy(b.manifest)
    disc = copy.deepcopy(b.discovery)
    inc = [o for o in disc["observations"] if o["included"]]
    inc[1]["file"] = inc[0]["file"]
    r = compat.report(rec, disc, man)
    assert r["duplicates"] and set(r["duplicates"][0]["keys"]) == {inc[0]["key"], inc[1]["key"]}


# ------------------------------------------------------------------ DQ-1
def test_quality_outcomes_and_injected_defects(tmp_path):
    bd, b, rec, _ = run("syn-var-1")
    q = quality.checks(rec, b.manifest, b.discovery, bd)
    by = {c["id"]: c for c in q["checks"]}
    assert by["DQ-FILES"]["outcome"] == "valid" and by["DQ-RECORD"]["outcome"] == "valid"
    assert set(q["summary"]) == set(quality.OUTCOMES) and "score" not in q
    assert quality.checks(rec, b.manifest, b.discovery, None)["checks"][0]["outcome"] == "not_checked"
    # a corrupted copy of the bundle: file integrity becomes invalid
    copy_dir = tmp_path / "b"
    shutil.copytree(bd, copy_dir)
    f = next((copy_dir / "images").iterdir())
    f.write_bytes(f.read_bytes()[:-10] + b"0123456789")
    assert quality.checks(rec, b.manifest, b.discovery, copy_dir)["checks"][0]["outcome"] == "invalid"
    # an impossible value and a tampered record
    bad = copy.deepcopy(rec)
    m = next(e for e in bad["events"] if e["step"] == "measure" and (e["data"].get("photometry") or {}).get("status") == "ok")
    m["data"]["photometry"]["flux_err_ujy"] = -1.0
    q2 = {c["id"]: c for c in quality.checks(bad, b.manifest, b.discovery, None)["checks"]}
    assert q2["DQ-VALUES"]["outcome"] == "invalid" and q2["DQ-RECORD"]["outcome"] == "invalid"
    # missing metadata
    disc = copy.deepcopy(b.discovery)
    next(o for o in disc["observations"] if o["included"])["t_mid_iso"] = ""
    assert {c["id"]: c for c in quality.checks(rec, b.manifest, disc, None)["checks"]}["DQ-META"]["outcome"] == "not_available"


# ------------------------------------------------------------------ LEDGER-1
def test_ledger_counts_support_and_flags_conflicts():
    _, b, rec, g = run("syn-var-1")
    L = ledger.build(rec, g, b.discovery)
    var = next(c for c in L["claims"] if c["question"] == "variability")
    assert var["category"] == "variability_candidate" and var["support"]["comparisons"] >= 2
    assert all(f["sha256"] for f in var["provenance"]["files"])
    assert "not a measure of how well" in var["support_note"]
    assert any(c["rule"] == "C1" for c in L["contradictions"])           # raw ≥ 5σ but calibrated < 5σ exists in this fixture
    _, b2, rec2, g2 = run("syn-hpm-1")
    L2 = ledger.build(rec2, g2, b2.discovery)
    v2 = next(c for c in L2["claims"] if c["question"] == "variability")
    assert v2["support"]["direct"] == 0 and "absence" in v2["flags"][0]
    # a single supporting item is flagged, never called sufficient
    g1 = copy.deepcopy(g)
    sup = [e for e in g1["edges"] if e["source"] == "claim:variability" and e["rel"] == "supported by"]
    g1["edges"] = [e for e in g1["edges"] if e not in sup[1:]]
    one = next(c for c in ledger.build(rec, g1, b.discovery)["claims"] if c["question"] == "variability")
    assert one["flags"] == ["rests on a single evidence item"]


# ------------------------------------------------------------------ RADAR-1
def test_radar_items_are_explained_and_ranked_by_the_stated_rule():
    bd, b, rec, g = run("syn-var-1")
    c, q, L = compat.report(rec, b.discovery, b.manifest), quality.checks(rec, b.manifest, b.discovery, bd), ledger.build(rec, g, b.discovery)
    R = radar.scan(rec, c, q, L, hypotheses.evaluate(rec), network=False)
    assert R["items"] and "not detections" in R["note"]
    for x in R["items"]:
        assert x["proposal"] and x["why"] and x["cannot_establish"] and "can_run_now" in x
        if x["action"]:
            assert x["action"] in capabilities.ACTION_IDS
    runnable = [x["can_run_now"] for x in R["items"]]
    assert runnable == sorted(runnable, reverse=True)
    assert any(x["signal"] == "R1" for x in R["items"])                 # significant pairs exist in the variable fixture
    assert all(not x["can_run_now"] for x in R["items"] if x["action"] == "acquire_data")
    for x in R["items"]:
        assert "discover" not in x["proposal"].lower()


# ------------------------------------------------------------------ PLAN-1
QUESTIONS = ["Could this source have changed between the two recorded observation epochs?", "Does the target move?",
             "Why did it dim?", "Is this a new planet?", "How far away is it?", "What can you do?", "Can this result be reproduced?",
             "Is the data usable? Which exposures were rejected?", "How robust is it to parameter choices?", "What are the uncertainties?",
             "Which explanations remain viable?", "Did SYN-VAR-1 get brighter on D3 on 2025-06-19?", "Show me the coverage gaps",
             "Compare SYNTHETIC:SYN11_23:D1 and SYNTHETIC:SYN31_23:D1", "Write a report", "Verify provenance", "banana", "",
             "Did the flux change and did it move?", "µ change ünïcode"]
FACTS = [{"has_target_data": True, "has_run": True, "run_hash": "a" * 64, "pair": None, "server": True, "static": False, "network": False, "targets": ["syn-var-1", "SYN-VAR-1"]},
         {"has_target_data": True, "has_run": False, "pair": ["SYNTHETIC:SYN11_23:D1", "SYNTHETIC:SYN12_23:D1"], "server": False, "static": True, "network": False, "targets": []},
         {"has_target_data": False, "has_run": False, "pair": None, "server": True, "static": False, "network": None, "targets": []}]


def test_planner_known_plans():
    p = planner.plan(QUESTIONS[0], FACTS[0])
    assert p["intent"]["kind"] == "change" and p["intent"]["pair_requested"]
    st = {s["id"]: s["status"] for s in p["steps"]}
    assert st["analysis"] == "completed" and st["pair"] == "blocked" and st["quality"] == "ready" and st["stability"] == "suggested"
    assert planner.plan("Why did it dim?", FACTS[0])["answerable"] is False
    assert planner.plan("banana", FACTS[0])["intent"]["kind"] == "unknown"
    s = planner.plan("Can this result be reproduced?", FACTS[1])
    assert {x["id"]: x["status"] for x in s["steps"]}["provenance"] == "blocked"           # server-only in the static preview
    n = planner.plan("Does the target move?", FACTS[2])
    assert all(x["status"] == "blocked" for x in n["steps"])
    assert all(x["action"] in capabilities.ACTION_IDS for q in QUESTIONS for f in FACTS for x in planner.plan(q, f)["steps"])
    assert planner.validate_intent({"kind": "rm"}) and not planner.validate_intent({"kind": "motion", "keys": ["SYNTHETIC:SYN11_23:D1"]})


# ------------------------------------------------------------------ MISSION-1
def mission_sessions():
    s = session.new("m", "syn-var-1", at="2026-10-30T10:00:00+00:00")
    s["missions"] = [{"template_id": m["id"], "started_at": "2026-10-30T10:00:00+00:00", "status": "active", "reviews": []} for m in missions.MISSIONS]
    s["missions"].append({"template_id": "unknown-mission", "started_at": "2026-10-30T10:00:00+00:00", "status": "active", "reviews": []})
    a = copy.deepcopy(s)
    a["runs"] = [{"investigation_id": "i", "content_hash": "a" * 64, "label": "x", "attached_at": "2026-10-30T10:00:00+00:00", "params": {}}]
    a["question"] = {"id": None, "text": "q"}
    for i, k in enumerate(["quality.view", "pair.view_matched", "ledger.claim", "report.export", "session.export", "experiment.reproducibility"]):
        a = session.log(a, k, k, at=f"2026-10-30T10:0{i + 1}:00+00:00")
    a = session.log(a, "quality.view", "before start", at="2026-10-29T09:00:00+00:00") if False else a
    a["notebook"] = [{"id": f"n{i}", "type": t, "author": "user", "created_at": "2026-10-30T10:00:00+00:00", "modified_at": "2026-10-30T10:00:00+00:00", "text": "x"}
                     for i, t in enumerate(["paragraph", "conclusion", "observation"])]
    a["hypotheses"] = [{"id": "U1", "statement": "s", "tests": ["V-INTRINSIC/T-SIG"], "kind": "interpretation", "created_at": "x"}]
    a["missions"][0]["reviews"] = [{"task_id": "review", "note": "checked", "at": "2026-10-30T11:00:00+00:00"}]
    late = copy.deepcopy(a)
    late["missions"][1]["started_at"] = "2026-10-30T23:00:00+00:00"            # events before the start do not count
    return [s, a, late]


def test_missions_read_completion_from_the_session():
    s, a, late = mission_sessions()
    ev0 = missions.evaluate(s)
    assert all(not t["done"] for m in ev0 if m["known"] for t in m["tasks"] if t["id"] != "question") and ev0[-1]["known"] is False
    ev = {m["template_id"]: m for m in missions.evaluate(a)}
    vi = {t["id"]: t["done"] for t in ev["verify-integrity"]["tasks"]}
    assert vi == {"run": True, "quality": True, "provenance": False, "review": True}
    assert {t["id"]: t["done"] for t in ev["compare-pair"]["tasks"]}["pair"] is True
    assert {t["id"]: t["done"] for t in {m["template_id"]: m for m in missions.evaluate(late)}["compare-pair"]["tasks"]}["pair"] is False


# ------------------------------------------------------------------ WF-1
def workflow_cases():
    w = copy.deepcopy(workflows.TEMPLATES[0])
    bad_action = dict(w, steps=[{"id": "x", "action": "rm_rf", "depends": []}])
    bad_dep = dict(w, steps=[{"id": "a", "action": "check_quality", "inputs": {}, "depends": ["b"]}, {"id": "b", "action": "run_analysis", "inputs": {}, "depends": []}])
    bad_input = dict(w, steps=[{"id": "a", "action": "run_experiment", "inputs": {"template": "anything"}, "depends": []}])
    too_big = dict(w, targets=["syn-var-1", "syn-hpm-1", "a", "b"], steps=[{"id": f"s{i}", "action": "check_quality", "inputs": {}, "depends": []} for i in range(7)])
    dup = dict(w, targets=["syn-var-1", "syn-var-1"])
    return [w, *workflows.TEMPLATES[1:], bad_action, bad_dep, bad_input, too_big, dup, {"schema": "x"}, "nope"]


def test_workflow_validation():
    res = [workflows.validate(w) for w in workflow_cases()]
    assert res[:3] == [[], [], []] and all(res[3:])


# ------------------------------------------------------------------ parity
@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_planner_missions_workflows_match_python(tmp_path):
    sp = json.loads(json.dumps(specs()))
    cases = [[q, f] for q in QUESTIONS for f in FACTS]
    job = {"spec": sp, "planner_cases": cases, "sessions": mission_sessions(), "workflows": workflow_cases()}
    f = tmp_path / "job.json"
    f.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/research_parity.mjs"), str(ROOT), str(f)], capture_output=True, text=True, timeout=60, check=True)
    js = json.loads(r.stdout)
    assert js["plans"] == [json.loads(json.dumps(planner.plan(q, fa))) for q, fa in cases]
    assert js["missions"] == [missions.evaluate(s) for s in job["sessions"]]
    assert js["workflows"] == [workflows.validate(w) for w in job["workflows"]]


# ------------------------------------------------------------------ EXP-1 / ACQ-2 / registry
def test_experiment_validation_and_negative_control():
    assert experiments.validate({"template": "parameter", "configs": [{"aperture_radius_px": 0.2}]})
    assert experiments.validate({"template": "nope"})
    assert not experiments.validate({"template": "parameter", "configs": [{"aperture_radius_px": 3.0, "apply_parallax": False}]})
    c = experiments.control_for("syn-var-1", "variability")
    assert c["target_id"] == "syn-hpm-1"
    load = lambda t: bmod.load(bmod.SYNTHETIC_ROOT / t)  # noqa: E731
    r = experiments.run(load, "syn-var-1", {"template": "negative_control", "question": "variability"})
    assert r["evaluation"]["passed"] is True and r["evaluation"]["control_category"] != "variability_candidate"
    mc = experiments.run(load, "syn-hpm-1", {"template": "method_comparison"})
    assert mc["evaluation"]["motion"]["agree_within_3sigma"] is True


def test_connector_previews_match_acquisition_and_send_nothing():
    pr = connectors.preview("gaia_cone", {"ra": 10.0, "dec": 5.0, "radius_deg": 0.05, "g_min": 10, "g_max": 16})
    assert pr["ok"] and not pr["sent"] and "gaiadr3.gaia_source" in pr["request"]["params"]["QUERY"]
    assert connectors.preview("gaia_cone", {"ra": 10.0, "dec": 5.0, "radius_deg": 0.05, "g_min": 16, "g_max": 10})["ok"] is False
    assert connectors.preview("nope", {})["ok"] is False
    reg = connectors.registry(ROOT / "data" / "environment_report.json", offline=True)
    assert all(not c["usable_now"] and c["usable_note"] == "OFFLINE=1" for c in reg["connectors"])


def test_retry_after_is_honoured_and_bounded(tmp_path):
    from skytrace.archive import net
    slept = []

    class Resp:
        def __init__(self, code, ra=None):
            self.status_code, self.headers = code, ({"Retry-After": ra} if ra else {})

        def iter_content(self, chunk_size):
            yield b"ok"

        def close(self):
            pass

    seq = [Resp(429, "7"), Resp(503, "600"), Resp(200)]

    class Sess:
        def get(self, url, timeout, stream):
            return seq.pop(0)

    f = net.Fetcher(tmp_path, offline=False, session=Sess(), sleep=slept.append, retries=3)
    assert f.get("https://example.invalid/x", source="t").content == b"ok"
    assert slept == [7.0, net.MAX_RETRY_AFTER_S]


def test_registry_actions_and_capabilities_are_consistent():
    reg = capabilities.registry({"server": True, "network": False})
    caps = {c["id"] for c in reg["capabilities"]}
    for c in reg["capabilities"]:
        assert {"description", "preconditions", "dependencies", "validation", "data_types"} <= set(c)
        assert set(c["dependencies"]) <= caps
        assert set(c["preconditions"]) <= set(capabilities.FACTS)
    for a in capabilities.ACTIONS:
        assert set(a["capabilities"]) <= caps and set(a["preconditions"]) <= set(capabilities.FACTS)
        assert a["static"] in ("browser", "precomputed", "unavailable")
