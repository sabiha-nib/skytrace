"""Phase 7 engines on the synthetic fixtures: CF-1 isolation and exact re-assessment, SYNOBS-1 determinism and known
answers, OBSDES-1, ASL-1 rules, INFO-1, REPRO-1 verdicts and tamper detection, REVIEW-1, TWIN-1 integrity, SPE-1 /
HORIZON-1, the v0.7 session fields, and Python/browser parity of the session-dependent rules."""

import copy
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from skytrace import (adversarial, analysis, bundle as bmod, capabilities, counterfactual as cf, discovery, hypotheses, infogain, ledger,
                      possibility, quality, repro, review, session, synthobs, twin, uncertainty)
from skytrace.server.research import compat
from skytrace.view import InvestigationView, evidence_graph

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
_C = {}


def ctx(tid):
    if tid not in _C:
        b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
        rec = json.loads(json.dumps(analysis.run(b, {}).to_dict(), default=str))
        v = InvestigationView(rec, b.discovery, b.manifest, b.inspection)
        g = evidence_graph(v, tid)
        disc = discovery.report(rec, b.discovery, b.manifest, {})
        q = quality.checks(rec, b.manifest, b.discovery, b.path)
        L = ledger.build(rec, g, b.discovery)
        from skytrace import radar
        c = compat.report(rec, b.discovery, b.manifest)
        res = {"compat": c, "quality": q, "ledger": L, "radar": radar.scan(rec, c, q, L, disc["hypotheses"], network=False)}
        _C[tid] = (b, rec, disc, res)
    return _C[tid]


load = lambda t: bmod.load(bmod.SYNTHETIC_ROOT / t)  # noqa: E731


# ------------------------------------------------------------------ CF-1
@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
def test_reassessment_without_change_reproduces_the_record(tid):
    _, rec, _, _ = ctx(tid)
    recorded = {o["question"]: o for o in next(e for e in rec["events"] if e["step"] == "assess")["data"]["outcomes"]}
    assert cf.reassess(rec) == json.loads(json.dumps(recorded))


def test_counterfactuals_are_isolated_and_labelled(tmp_path):
    b, rec, _, _ = ctx("syn-var-1")
    before = {p.name: bmod.sha256_file(p) for p in sorted(b.path.rglob("*.json"))}
    frozen = copy.deepcopy(rec)
    r = cf.run(load, "syn-var-1", {"kind": "threshold", "change": {"variability_z": 10}}, baseline_record=rec)
    assert r["status"] == "completed" and r["baseline"]["intact"] and r["baseline"]["content_hash"] == rec["content_hash"]
    assert rec == frozen, "the baseline record object must not be modified"
    assert r["counterfactual"]["categories"]["variability"] != r["baseline"]["categories"]["variability"]
    assert r["value_label"].startswith("assumed") and "not an observation" in r["caveat"]
    x = cf.run(load, "syn-var-1", {"kind": "exclusion", "change": {"detectors": [1]}}, baseline_record=rec)
    assert x["rerun"] and x["counterfactual"]["content_hash"] != rec["content_hash"]
    assert next(row for row in x["comparison"] if row["metric"] == "input.observations_excluded_by_scenario")["counterfactual"] == 8
    assert before == {p.name: bmod.sha256_file(p) for p in sorted(b.path.rglob("*.json"))}, "the bundle on disk must not change"
    same = cf.run(load, "syn-var-1", {"kind": "threshold", "change": {"variability_z": 5.0}}, baseline_record=rec)
    assert not any(row["changed"] for row in same["comparison"])
    m = cf.run(load, "syn-var-1", {"kind": "method", "change": {"variability_method": "PAIRDIFF-1"}}, baseline_record=rec)
    assert m["value_label"].startswith("hypothetical") and m["counterfactual"]["categories"]["variability"] == "calibration_limited"


def test_counterfactual_validation_refuses():
    bad = [{"kind": "x", "change": {}}, {"kind": "parameter", "change": {"aperture_radius_px": 99}},
           {"kind": "threshold", "change": {"instrumental_fraction": 0.1}}, {"kind": "error_scale", "change": {"photometric_error_factor": 0.5}},
           {"kind": "exclusion", "change": {}}, {"kind": "method", "change": {"variability_method": "magic"}},
           {"kind": "parameter", "change": {"aperture_radius_px": 3}, "evil": 1}]
    for s in bad:
        assert cf.validate(s), s
    r = cf.run(load, "syn-var-1", {"kind": "exclusion", "change": {"keys": ["SYNTHETIC:NOPE_1:D1"]}}, baseline_record=ctx("syn-var-1")[1])
    assert r["status"] == "refused" and "unknown observation" in r["errors"][0]
    r = cf.run(load, "syn-var-1", {"kind": "threshold", "change": {"variability_z": 6}, "baseline_hash": "0" * 64}, baseline_record=ctx("syn-var-1")[1])
    assert r["status"] == "refused" and "baseline" in r["errors"][0]


# ------------------------------------------------------------------ SYNOBS-1 / OBSDES-1
@pytest.fixture()
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(synthobs, "ROOT", tmp_path / "synthlab")
    return tmp_path / "synthlab"


def test_synthetic_scenarios_are_labelled_deterministic_and_known_answer(lab):
    t = {x["id"]: x["scenario"] for x in synthobs.TEMPLATES}
    r = synthobs.run(t["fast-mover"])
    assert r["status"] == "completed" and r["synthetic"] and r["scenario_id"].startswith("syn-lab-")
    d = lab / r["scenario_id"]
    m = json.loads((d / "manifest.json").read_text())
    assert m["kind"] == "synthetic" and all(f["provenance"]["origin"] == "synthetic" for f in m["files"])
    assert "data/bundles" not in str(d) and "fixtures" not in str(d)
    rows = {x["question"]: x for x in r["evaluation"]["rows"]}
    assert rows["motion"]["verdict"] == "agrees" and rows["motion"]["pipeline"] == "motion_detected"
    assert abs(rows["motion"]["error"]["east_sigma"]) < 5 and abs(rows["motion"]["error"]["north_sigma"]) < 5
    shutil.rmtree(d)
    again = synthobs.run(t["fast-mover"])
    assert again["record_content_hash"] == r["record_content_hash"] and again["bundle_manifest_sha256"] == r["bundle_manifest_sha256"]
    slow = synthobs.run(t["slow-mover"])
    assert next(x for x in slow["evaluation"]["rows"] if x["question"] == "motion")["verdict"] == "agrees"
    blend = synthobs.run(t["blend"])
    assert blend["evaluation"]["failure_behaviour"]["rejected_exposures_by_reason"].get("blended", 0) > 0


def test_synthetic_validation_and_design_refusals(lab):
    assert synthobs.validate({"seed": 1, "pm_mas_yr": [0, 0], "passes": [{"day": 0, "position": "A", "brightness": 1}]})
    assert synthobs.validate({"seed": 1, "pm_mas_yr": [0, 0], "passes": [{"day": 9, "position": "A", "brightness": 1}, {"day": 3, "position": "A", "brightness": 1}]})
    assert synthobs.validate({"seed": 1, "pm_mas_yr": [9e9, 0], "passes": []})
    assert synthobs.design({"seed": 1, "pm_mas_yr": [0, 0]}, [{"name": "only one", "passes": []}])["status"] == "refused"


def test_observation_design_compares_schedules(lab):
    truth = {"seed": 201, "pm_mas_yr": [2500.0, -1800.0]}
    s1 = {"name": "two passes, 6 months", "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "A", "brightness": 1.0}]}
    s2 = {"name": "four passes, 18 months", "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                                                         {"day": 365, "position": "A", "brightness": 1.0}, {"day": 547, "position": "C", "brightness": 1.0}]}
    r = synthobs.design(truth, [s1, s2])
    assert r["status"] == "completed" and len(r["schedules"]) == 2 and "Not a telescope schedule" in r["brief"]
    a, b = r["schedules"]
    if a["motion_sensitivity_mas_yr"] and b["motion_sensitivity_mas_yr"]:
        assert b["motion_sensitivity_mas_yr"] < a["motion_sensitivity_mas_yr"]   # longer baseline → better sensitivity


# ------------------------------------------------------------------ ASL-1 / INFO-1 / REPRO-1 / REVIEW-1
def test_adversarial_rules_and_statuses():
    b, rec, disc, res = ctx("syn-var-1")
    a = adversarial.challenges(rec, disc["hypotheses"], res["quality"], res["ledger"], disc["uncertainty"])
    ids = {c["id"] for c in a["challenges"]}
    assert {"H-V-CALIB", "M-CALCHECK", "B-PAIRS", "B-STABILITY", "R-REPLAY"} <= ids
    assert sum(1 for i in ids if i.startswith("E-C1-")) == len(res["ledger"]["contradictions"])
    assert all(c["severity"] in adversarial.SEVERITY and c["rule"].startswith("ASL ") for c in a["challenges"])
    sess = {"examined": [], "annotations": [{"id": "a1", "target": {"kind": "challenge", "id": "M-CALCHECK"}, "text": "checked", "created_at": "2026-10-30T00:00:00+00:00"}]}
    a2 = adversarial.challenges(rec, disc["hypotheses"], res["quality"], res["ledger"], disc["uncertainty"], session=sess)
    assert next(c for c in a2["challenges"] if c["id"] == "M-CALCHECK")["status"] == "acknowledged"
    pairs = next(c for c in a["challenges"] if c["id"] == "B-PAIRS")["pairs"]
    a3 = adversarial.challenges(rec, disc["hypotheses"], res["quality"], res["ledger"], disc["uncertainty"], session={"examined": pairs})
    assert "B-PAIRS" not in {c["id"] for c in a3["challenges"]}
    hb, hrec, hdisc, hres = ctx("syn-hpm-1")
    ha = adversarial.challenges(hrec, hdisc["hypotheses"], hres["quality"], hres["ledger"], hdisc["uncertainty"])
    assert not any(c["severity"] == "major" and "absence" in c["issue"] for c in ha["challenges"])


def test_information_analysis_has_no_probabilities():
    _, rec, disc, _ = ctx("syn-var-1")
    i = infogain.analyse(disc["hypotheses"])
    assert i["probability_model"] is None and "no expected information" in i["uncertainty_model"]
    text = json.dumps(i).lower()
    assert "probability\": 0" not in text and "bits" not in text
    ranks = [c["rank"] for c in i["candidates"]]
    assert ranks == list(range(1, len(ranks) + 1))
    feas = [infogain.FEAS_ORDER.index(c["feasibility"]) for c in i["candidates"]]
    assert feas == sorted(feas)


def test_reproducibility_verdicts_and_tamper(tmp_path):
    b, rec, _, _ = ctx("syn-var-1")
    assert repro.audit(rec, b.path, rerun=False)["verdict"] == "replayable, not replayed here"
    assert repro.audit(rec, b.path, rerun=True)["verdict"] == "reproduced"
    assert repro.audit(rec, None, rerun=False)["verdict"] == "incomplete"
    bad = copy.deepcopy(rec)
    bad["parameters"]["aperture_radius_px"] = 3.0
    r = repro.audit(bad, None, rerun=False)
    assert r["verdict"] == "not reproducible as recorded" and next(c for c in r["checks"] if c["id"] == "R8")["outcome"] == "fail"


def test_review_findings_cite_sources():
    b, rec, disc, res = ctx("syn-var-1")
    rp = repro.audit(rec, b.path, rerun=False)
    asl = adversarial.challenges(rec, disc["hypotheses"], res["quality"], res["ledger"], disc["uncertainty"])
    rv = review.review(rec, res["quality"], res["ledger"], disc["hypotheses"], disc["uncertainty"], rp, asl,
                       {"question": {"text": "Did it dim?"}, "notebook": [{"author": "user", "text": "This proves the star dimmed."}]}, "brightness")
    assert all(f["cites"] for f in rv["findings"])
    causal = next(f for f in rv["findings"] if f["check"].startswith("Notes avoid"))
    assert causal["outcome"] == "not met" and "proves" in causal["detail"]
    assert "not people" in rv["note"]


# ------------------------------------------------------------------ TWIN-1
def test_twins_integrity_and_comparison():
    b, rec, _, _ = ctx("syn-var-1")
    a = twin.analysis_twin(rec)
    assert twin.verify(a) and a["semantics"].startswith("A computational record")
    t2 = copy.deepcopy(a)
    t2["sections"]["parameters"]["aperture_radius_px"] = 3.0
    assert not twin.verify(t2)
    _, hrec, _, _ = ctx("syn-hpm-1")
    c = twin.compare(a, twin.analysis_twin(hrec))
    assert c["comparable"] and not c["identical"] and c["counts"]["outputs"] >= 1
    assert twin.compare(a, a)["identical"]
    assert not twin.compare(a, twin.target(b.target, rec))["comparable"]
    o = twin.observation(rec, b.discovery, b.manifest, b.observations()[0]["key"])
    assert twin.verify(o) and o["sections"]["inputs"]["sha256"]
    r = cf.run(load, "syn-var-1", {"kind": "threshold", "change": {"variability_z": 8}}, baseline_record=rec)
    st = twin.scenario_twin(r)
    assert twin.verify(st) and rec["content_hash"] in st["derived_from"] and st["kind"] == "scenario"


# ------------------------------------------------------------------ SPE-1 / HORIZON-1
def test_possibility_layers_and_horizon_cards():
    b, rec, disc, res = ctx("syn-var-1")
    asl = adversarial.challenges(rec, disc["hypotheses"], res["quality"], res["ledger"], disc["uncertainty"])
    info = infogain.analyse(disc["hypotheses"])
    spe = possibility.layers(rec, disc, res, info, asl, None, True, False)
    assert [l["n"] for l in spe["layers"]] == [1, 2, 3, 4, 5, 6]
    cards = spe["horizon"]["cards"]
    need = {"question", "prompted_by", "required_data", "available_data", "method", "limitations", "feasibility", "expected_output", "priority_reason"}
    assert cards and all(need <= set(c) and c["prompted_by"] for c in cards)
    assert {c["category"] for c in cards} <= set(possibility.CATS)
    assert "finding" not in json.dumps([c["question"] for c in cards]).lower()
    ids = {n["id"] for n in spe["horizon"]["map"]["nodes"]}
    assert all(e["s"] in ids and e["t"] in ids for e in spe["horizon"]["map"]["edges"])


def test_session_accepts_v07_fields_and_keeps_06_sessions_valid():
    s = session.new("v0.7")
    assert session.validate(s) == []
    s["scenarios"] = [{"kind": "threshold", "change": {"variability_z": 8}}]
    s["causal"] = [{"from": "calibration", "to": "flux difference", "label": "user-proposed"}]
    s["annotations"] = [{"id": "a1", "target": {"kind": "challenge", "id": "M-CALCHECK"}, "text": "looked", "created_at": s["created_at"]}]
    assert session.validate(session.finalize(s)) == []


def test_registry_permissions_cover_every_action():
    assert capabilities.REGISTRY_VERSION == "CAPREG-3"
    assert all(a["permission"] in ("inspect", "analysis", "export", "network") for a in capabilities.ACTIONS)
    assert next(a for a in capabilities.ACTIONS if a["id"] == "acquire_data")["permission"] == "network"
    assert all(lv["id"] != "network" and "network" not in lv["allows"] for lv in capabilities.AUTOPILOT_LEVELS)


# ------------------------------------------------------------------ browser parity of the session-dependent rules
def _vincenty(ra1, dec1, ra2, dec2):
    r = math.pi / 180
    l1, b1, l2, b2 = ra1 * r, dec1 * r, ra2 * r, dec2 * r
    dl = l2 - l1
    num = math.hypot(math.cos(b2) * math.sin(dl), math.cos(b1) * math.sin(b2) - math.sin(b1) * math.cos(b2) * math.cos(dl))
    den = math.sin(b1) * math.sin(b2) + math.cos(b1) * math.cos(b2) * math.cos(dl)
    return math.atan2(num, den) / r


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_overlays_match_python(tmp_path):
    b, rec, disc, res = ctx("syn-var-1")
    hyp, unc = disc["hypotheses"], disc["uncertainty"]
    asl0 = adversarial.challenges(rec, hyp, res["quality"], res["ledger"], unc)
    info = infogain.analyse(hyp)
    pairs = next(c for c in asl0["challenges"] if c["id"] == "B-PAIRS")["pairs"]
    seqs = [s_["id"] for s_ in res["compat"]["sequences"] if s_["n_frames"] >= 3]
    ann = [{"id": "a1", "target": {"kind": "challenge", "id": "M-CALCHECK"}, "text": "x", "created_at": "2026-10-30T00:00:00+00:00"}]
    sessions = [None, {"examined": pairs[:3], "history": [{"kind": "sequence.view", "ref": seqs[0]}], "scenarios": [], "annotations": ann},
                {"examined": pairs, "history": [{"kind": "sequence.view", "ref": s_} for s_ in seqs], "scenarios": [{"kind": "threshold"}],
                 "notebook": [{"author": "user", "text": "Due to calibration, probably."}], "question": {"text": "Did it change?"}}]
    h0 = possibility.horizon(disc, res, info, asl0, None, True, False)
    rp = repro.audit(rec, b.path, rerun=False)
    rv0 = review.review(rec, res["quality"], res["ledger"], hyp, unc, rp, asl0, None, None)
    a_tw, b_tw = twin.analysis_twin(rec), twin.analysis_twin(ctx("syn-hpm-1")[1])
    seps = [[210.25, -32.6, 77.0, 30.4], [0, 0, 180, 0], [10, 89.9, 190, 89.9], [1, 1, 1, 1], [359.9, -10, 0.1, -10]]
    hcases = [[h0, s_, st, True] for s_ in sessions for st in (False, True)]
    job = {"horizon_cases": hcases, "asl_cases": [[asl0, s_] for s_ in sessions],
           "review_cases": [[rv0, s_, "change" if s_ else None, list(review.CAUSAL_WORDS)] for s_ in sessions],
           "twin_cases": [[a_tw, b_tw, list(twin.SECTIONS)], [a_tw, a_tw, list(twin.SECTIONS)]], "sep_cases": seps}
    f = tmp_path / "job.json"
    f.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/frontier_parity.mjs"), str(ROOT), str(f)], capture_output=True, text=True, timeout=60, check=True)
    js = json.loads(r.stdout)
    py_h = [possibility.horizon(disc, res, info, asl0, s_, sv, st) for _, s_, st, sv in hcases]
    for a_, p_ in zip(js["horizon"], py_h):
        assert a_["cards"] == json.loads(json.dumps(p_["cards"])) and a_["map"] == json.loads(json.dumps(p_["map"]))
    for a_, s_ in zip(js["asl"], sessions):
        assert a_["challenges"] == json.loads(json.dumps(adversarial.challenges(rec, hyp, res["quality"], res["ledger"], unc, session=s_)["challenges"]))
    for a_, s_ in zip(js["review"], sessions):
        p_ = review.review(rec, res["quality"], res["ledger"], hyp, unc, rp, asl0, s_, "change" if s_ else None)
        assert a_["findings"] == json.loads(json.dumps(p_["findings"])) and a_["counts"] == p_["counts"]
    assert js["twins"][0]["differences"] == json.loads(json.dumps(twin.compare(a_tw, b_tw)["differences"]))
    assert js["twins"][1]["identical"] is True
    for got, (a1, d1, a2, d2) in zip(js["sep"], seps):
        assert math.isclose(got, _vincenty(a1, d1, a2, d2), rel_tol=1e-12, abs_tol=1e-12)


def _galactic(ra, dec):
    G = [[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132], [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
         [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]]
    r = math.pi / 180
    v = [math.cos(dec * r) * math.cos(ra * r), math.cos(dec * r) * math.sin(ra * r), math.sin(dec * r)]
    g = [sum(G[i][j] * v[j] for j in range(3)) for i in range(3)]
    lon = math.atan2(g[1], g[0]) / r
    return (lon + 360 if lon < 0 else lon), math.asin(max(-1, min(1, g[2]))) / r


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_twin_and_coordinates_match_python(tmp_path):
    s = session.new("twin parity", "syn-var-1")
    s["runs"] = [{"investigation_id": "abc", "content_hash": "a" * 64, "label": "default", "attached_at": s["created_at"], "params": {}}]
    s["hypotheses"] = [{"id": "h1", "statement": "It dimmed.", "tests": [], "kind": "interpretation", "created_at": s["created_at"]}]
    s["question"] = {"id": None, "text": "Did it dim?"}
    s = session.finalize(s)
    l, b_ = _galactic(266.40499, -28.93617)               # the Galactic centre (ICRS) → l ≈ 0, b ≈ 0
    assert min(l, 360 - l) < 0.01 and abs(b_) < 0.01
    job = {"session": s, "coords": [[266.40499, -28.93617], [0, 0], [10.68471, 41.26875], [77.0, 30.4]],
           "sexa": [["17h57m48.49847s", True], ["+04d41m36.1139s", False], ["-29d00m00s", False], ["12.5", True], ["nonsense", True]]}
    f = tmp_path / "job.json"
    f.write_text(json.dumps(job))
    code = (f"import {{ readFileSync }} from 'node:fs'; import {{ pathToFileURL }} from 'node:url';"
            f"const fc = await import(pathToFileURL({json.dumps(str(ROOT / 'web/js/frontiercore.js'))}).href);"
            f"const canon = await import(pathToFileURL({json.dumps(str(ROOT / 'web/js/canon.js'))}).href);"
            f"const job = JSON.parse(readFileSync({json.dumps(str(f))}, 'utf8'));"
            "const tw = await fc.investigationTwin(job.session, canon.digest);"
            "process.stdout.write(JSON.stringify({tw, gal: job.coords.map(([a, d]) => fc.icrsToGalactic(a, d)), sexa: job.sexa.map(([t, r]) => fc.parseSexagesimal(t, r))}));")
    r = subprocess.run([NODE, "--input-type=module", "-e", code], capture_output=True, text=True, timeout=60, check=True)
    js = json.loads(r.stdout)
    assert js["tw"] == json.loads(json.dumps(twin.investigation(s)))
    for (gl, gb), (ra, dec) in zip(js["gal"], job["coords"]):
        pl, pb = _galactic(ra, dec)
        assert math.isclose(gl, pl, abs_tol=1e-9) and math.isclose(gb, pb, abs_tol=1e-9)
    assert math.isclose(js["sexa"][0], (17 + 57 / 60 + 48.49847 / 3600) * 15, rel_tol=1e-12)
    assert math.isclose(js["sexa"][1], 4 + 41 / 60 + 36.1139 / 3600, rel_tol=1e-12)
    assert js["sexa"][2] == -29.0 and js["sexa"][3] == 12.5 and js["sexa"][4] is None


def test_executor_implements_every_registered_action():
    import re
    src = (ROOT / "web/js/executor.js").read_text()
    block = src.split("const ACTIONS = {")[1].split("\n};")[0]
    names = set(re.findall(r"^  async (\w+)\(", block, re.M))
    assert names == capabilities.ACTION_IDS
