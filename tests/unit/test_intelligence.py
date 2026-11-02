"""Phase 9 intelligence layer on the synthetic fixtures: SCI-ENTITY-1 provenance and versions, MEMORY-1 statuses, recall and
failure warnings, DGENOME-1 fields and comparison limits, UNKNOWN-1 regions, ADV-1 ledger, GATE-1 and DEBT-1, ORACLE-1 known
answers, CAUSAL-1 confounders and criteria, MDNET-1 relationships, REPRONET-1 manifests and comparison classes, WHATIF-1
isolation and refusals, FINGERPRINT-1, INSTCHECK-1, BUDGET-1, and Python/browser parity of intelcore.js. Synthetic results here
are software checks, never evidence about the sky."""

import copy
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from skytrace import (adversary, analysis, budget, bundle as bmod, causal, counterfactual as cf, dgenome, entities as E, fingerprint, gate, instcheck,
                      mdnet, memory, oracle, repronet, reprox, unknownmap, whatif)
from skytrace.server import intelligence as si

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
_C = {}


def run(tid, params=None):
    key = (tid, json.dumps(params or {}, sort_keys=True))
    if key not in _C:
        b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
        rec = json.loads(json.dumps(analysis.run(b, params or {}).to_dict(), default=str))
        e = {"record": rec, "target_id": tid}
        c = si._ctx(e)
        _C[key] = {"b": b, "rec": rec, "e": e, **c, "intel": si.intelligence_report(e)}
    return _C[key]


def corpus(*cs):
    return [{"iid": c["rec"]["content_hash"][:12], "record": c["rec"], "epistemic": c["rep"], "hypotheses": c["disc"]["hypotheses"], "origin": "test"} for c in cs]


def close(a, b, rel=1e-12):
    """Structural equality, with floats equal to a relative 1e-12: math.hypot and Math.hypot may round the last bit differently."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=rel, abs_tol=1e-300)
    return a == b


def rehash(rec):
    rec = copy.deepcopy(rec)
    rec["content_hash"] = cf.record_hash(rec)
    return rec


# ------------------------------------------------------------------ SCI-ENTITY-1
@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
def test_entities_have_ids_versions_provenance_and_statuses(tid):
    c = run(tid)
    ents = c["intel"]["entities"]["items"]
    assert c["intel"]["entities"]["errors"] == []
    assert {x["type"] for x in ents} >= {"investigation", "dataset", "observation", "measurement", "instrument", "method", "assumption", "claim",
                                         "uncertainty", "evidence", "calibration", "challenge", "conclusion"}
    for x in ents:
        assert x["type"] in E.TYPES and x["status"] in E.STATUSES and x["version"] >= 1 and x["provenance"]["hash"] == c["rec"]["content_hash"]
    inv = next(x for x in ents if x["type"] == "investigation")
    assert inv["status"] == "simulated" and inv["status_rule"] == "E1", "a synthetic investigation is simulated, never directly recorded"
    assert all(x["status"] == "not a statement" for x in ents if x["type"] in ("method", "transformation", "instrument"))
    again = E.investigation_entities(c["rec"], c["rep"]["graph"], c["frontier"])
    assert [x["id"] for x in again] == [x["id"] for x in ents], "stable identifiers"
    bad = copy.deepcopy(ents[:3])
    bad[0]["provenance"]["ref"] = "$.events[99999]"
    bad[1]["version"] = 0
    bad[2]["status"] = "certain"
    errs = E.validate(bad, E.resolver(c["rec"], c["rep"]["graph"], c["frontier"]))
    assert any("does not resolve" in e for e in errs) and any("version" in e for e in errs) and any("not an epistemic status" in e for e in errs)


def test_session_entities_follow_rules_and_count_versions():
    s = {"content_hash": "a" * 64, "created_at": "2026-11-01T00:00:00+00:00",
         "hypotheses": [{"id": "h1", "statement": "It dimmed.", "created_at": "2026-11-01T00:00:00+00:00", "versions": [{"at": "2026-11-01T00:00:00+00:00", "text": "x"}]}],
         "scenarios": [{"label": "threshold 8", "at": "2026-11-01T00:00:00+00:00"}], "causal": [{"from": "calibration", "rel": "causes", "to": "flux_difference"}],
         "history": [{"seq": 1, "at": "2026-11-01T00:00:00+00:00", "kind": "decision.record", "summary": "run stability"}]}
    ents = E.session_entities(s)
    by = {x["id"]: x for x in ents}
    assert by["hypothesis:user:h1"]["version"] == 2 and by["hypothesis:user:h1"]["status"] == "user-authored"
    assert by["counterfactual:0"]["status"] == "hypothetical" and by["research_decision:seq1"]["status"] == "user-authored"
    assert E.validate(ents) == []


# ------------------------------------------------------------------ MEMORY-1
def test_memory_statuses_never_promote_explanations_and_flag_tampering():
    a, b = run("syn-var-1"), run("syn-hpm-1")
    mem = memory.build(corpus(a, b))
    assert all(x["status"] == "provisional" and x["status_rule"] == "M6" for x in mem["items"] if x["kind"] == "explanation"), "never verified"
    assert all(x["status"] != "verified" for x in mem["items"] if x["kind"] in ("question", "assumption"))
    for x in mem["items"]:
        assert x["source"]["record"] in (a["rec"]["content_hash"], b["rec"]["content_hash"]) and x["status"] in memory.STATUSES
    tampered = copy.deepcopy(a["rec"])
    tampered["events"][0]["detail"] = "edited"
    m2 = memory.build([{**corpus(a)[0], "record": tampered}])
    assert {x["status"] for x in m2["items"]} == {"unverifiable"}


def test_memory_marks_superseded_conclusions_outdated():
    a = run("syn-var-1")
    later = copy.deepcopy(a["rec"])
    later["created_at"] = "2099-01-01T00:00:00+00:00"
    later["parameters"]["analysis_version"] = "skytrace-analysis/9"
    later = rehash(later)
    mem = memory.build(corpus(a) + [{**corpus(a)[0], "record": later, "iid": "later"}])
    old = [x for x in mem["items"] if x["record"] == a["rec"]["content_hash"] and x["kind"] == "conclusion"]
    assert old and all(x["status"] == "outdated" and x["superseded_by"] == later["content_hash"] for x in old)
    ev = [x for x in mem["evolution"] if x["question"] == "variability"][0]
    assert len(ev["steps"]) == 2 and ev["steps"][1]["differs_in"] == ["analysis_version"]


def test_recall_uses_the_concept_vocabulary_and_failure_warnings_quote_reasons():
    a, b = run("syn-var-1"), run("syn-hpm-1")
    mem = memory.build(corpus(a, b))
    r = memory.recall(mem, "Why did the brightness calibration look odd?")
    assert {c["id"] for c in r["concepts"]} == {"variability", "calibration", "cause"}
    assert r["results"] and all(set(x["matched"]) <= {"variability", "calibration", "cause"} for x in r["results"])
    assert memory.recall(mem, "zebra")["n"] == 0 and memory.recall(mem, "zebra")["note"]
    w = memory.warnings(mem, "syn-var-1", [{"id": "a1", "label": "compare pairs", "question": "variability", "concepts": []}])
    assert w and all(x["rule"] == "W1" and x["target"] == "syn-var-1" and x["what_failed"] for x in w)
    assert len({x["what_failed"] for x in w}) == len(w), "one warning per recorded failure"
    assert memory.warnings(mem, "syn-var-1", [{"id": "a2", "question": None, "concepts": ["archive"]}]) == [], "environment refusals are not repeatable failures"


# ------------------------------------------------------------------ DGENOME-1 and MDNET-1
def test_genomes_have_every_field_and_cite_real_objects():
    c = run("syn-var-1")
    ids = {n["id"] for n in c["rep"]["graph"]["nodes"]}
    for g in c["intel"]["genomes"]:
        assert g["available"] and list(g["fields"]) == dgenome.FIELDS
        for f, v in g["fields"].items():
            for cite in v.get("cites", []):
                assert cite in ids or cite.startswith(("$.", "hyp:", "CLAIMX-1", "SCICOMP-1", "QF-", "u:")) or cite.startswith("Q-"), (f, cite)
        assert g["fields"]["rejected_explanations"]["items"] == [h for h in g["fields"]["candidate_explanations"]["items"] if h["status"] == "contradicted"]


def test_genome_comparison_is_structural_and_unscored():
    a, b = run("syn-var-1"), run("syn-hpm-1")
    cmpd = dgenome.compare(a["intel"]["genomes"][0], b["intel"]["genomes"][0])
    assert "physically alike" in cmpd["note"] and not any("score" in k for k in cmpd)
    assert cmpd["interpretations"]["different"]
    same = dgenome.compare(a["intel"]["genomes"][0], a["intel"]["genomes"][0])
    assert all(s["match"] for s in same["shared_observational"]) and not same["interpretations"]["different"]


def test_network_edges_need_a_rule_and_state_basis_and_limitation():
    a, a2, b = run("syn-var-1"), run("syn-var-1", {"aperture_radius_px": 2.5}), run("syn-hpm-1")
    net = mdnet.build(corpus(a, a2, b))
    assert len(net["nodes"]) == 3
    for e in net["edges"]:
        assert e["relationships"] and e["rules"]
        for r in e["relationships"]:
            assert r["rule"] in mdnet.RULES and r["basis"] and r["limitation"] == mdnet.RULES[r["rule"]][1]
    sib = next(e for e in net["edges"] if {e["a"], e["b"]} == {a["rec"]["content_hash"][:16], a2["rec"]["content_hash"][:16]})
    n1 = next(r for r in sib["relationships"] if r["rule"] == "N1")
    assert n1["differs"] == ["aperture_radius_px"]
    cross = next(e for e in net["edges"] if b["rec"]["content_hash"][:16] in (e["a"], e["b"]) and a["rec"]["content_hash"][:16] in (e["a"], e["b"]))
    assert "N1" not in cross["rules"], "different targets are never 'the same target'"


# ------------------------------------------------------------------ UNKNOWN-1
def test_unknown_map_regions_have_rules_and_every_item_a_basis():
    a, a2 = run("syn-var-1"), run("syn-var-1", {"aperture_radius_px": 2.5})
    um = unknownmap.build(a["rec"], a["rep"], a["disc"], [a["rec"]["parameters"], a2["rec"]["parameters"]])
    assert [r["id"] for r in um["regions"]] == [r[0] for r in unknownmap.REGIONS]
    ids = [i["id"] for r in um["regions"] for i in r["items"]]
    assert len(ids) == len(set(ids)), "an item sits in one region only"
    for r in um["regions"]:
        assert r["rule"] == unknownmap.RULES[r["rule_id"]]
        for i in r["items"]:
            assert i["basis"] and i["region"] == r["id"]
    ap = [i for i in next(r for r in um["regions"] if r["id"] == "unexplored")["items"] if i["parameter"] == "aperture_radius_px"]
    lo, hi = unknownmap.scicomp.PARAM_RANGES["aperture_radius_px"]
    assert ap and all(i["sampled"] == [2.0, 2.5] for i in ap)
    assert {tuple(i["interval"]) for i in ap} <= {(lo, 2.0), (2.0, 2.5), (2.5, hi)}
    assert "not of astronomical knowledge" in um["note"]


# ------------------------------------------------------------------ ADV-1 and GATE-1
def test_adversary_raises_only_rule_backed_challenges():
    c = run("syn-var-1")
    led = c["intel"]["adversary"]
    var = next(x for x in led["conclusions"] if x["question"] == "variability")
    items = [i for q in var["questions"] for i in q["items"]]
    assert items and all(i["rule"] and i["source"] and i["follow_up"] and i["status"] == "open" for i in items)
    assert any(i["source"] == "X2" for i in items), "a positive outcome outside 'established' is challenged (Q8)"
    for q in var["questions"]:
        assert q["raised"] == bool(q["items"]) and (q["items"] or q["note"] == "no challenge raised by the defined rules")
    iid = items[0]["id"]
    o = adversary.overlay(led, {"challenges": [{"id": iid, "status": "resolved"}]})
    assert next(i for x in o["conclusions"] for q in x["questions"] for i in q["items"] if i["id"] == iid)["status"] == "open", "resolved needs a reference"
    o = adversary.overlay(led, {"challenges": [{"id": iid, "status": "resolved", "ref": "experiment:e1"}]})
    assert next(i for x in o["conclusions"] for q in x["questions"] for i in q["items"] if i["id"] == iid)["resolved_by"] == "experiment:e1"


def test_gate_requirements_and_session_overlay():
    c = run("syn-var-1")
    g = c["intel"]["gate"]
    assert [r["id"] for r in g["requirements"]] == [r[0] for r in gate.REQUIREMENTS] and g["outcome"] == "not ready"
    assert "does not mean they are true" in g["meaning"] and "software test" in g["meaning"]
    st = {r["id"]: r["state"] for r in g["requirements"]}
    assert st["G2"] == "met" and st["G3"] == "needs your action"
    tampered = copy.deepcopy(c["rec"])
    tampered["events"][3]["detail"] = "x"
    assert {r["id"]: r["state"] for r in gate.base(tampered, c["rep"], c["intel"]["adversary"])["requirements"]}["G2"] == "not met"
    led = c["intel"]["adversary"]
    marks = [{"id": i["id"], "status": "acknowledged", "note": "seen"} for x in led["conclusions"] for q in x["questions"] for i in q["items"]]
    sess = {"challenges": marks, "debug": [{"kind": "reproduction", "content_hash": c["rec"]["content_hash"], "verdict": "exact reproduction"}]}
    o = gate.overlay(g, adversary.overlay(led, sess), sess)
    assert {r["id"]: r["state"] for r in o["requirements"]} == {r: "met" for r, _ in gate.REQUIREMENTS} and o["outcome"] == "ready to mark complete"
    d = c["intel"]["debt"]
    assert d["items"] and all(i["source"] and i["ref"] for i in d["items"])


# ------------------------------------------------------------------ ORACLE-1 and CAUSAL-1
def test_oracle_known_answers_and_refusals():
    ctx = {"visits": [{"t_yr": 0.0, "sigma_mas": 10.0}, {"t_yr": 1.0, "sigma_mas": 10.0}], "validated": True, "recorded_pm_mas_yr": 30.0,
           "median_flux_ujy": 1000.0, "median_fractional_error": 0.02, "error_scale": 1.0}
    r = oracle.evaluate_ctx(ctx, {"question": "motion", "candidates": [{"added_years_after_last": [1.0]}]})
    rec, c1 = r["rows"]
    assert math.isclose(rec["sigma_mu_mas_yr"], 10 * math.sqrt(2)) and math.isclose(rec["expected_significance"], 30 / (10 * math.sqrt(2)))
    assert math.isclose(c1["sigma_mu_mas_yr"], 10 / math.sqrt(2)), "three equally spaced visits over two years: σ/√2"
    assert r["information_gain"] is None and "prior" in r["information_gain_note"] and r["ranking"] == ["c1"]
    v = oracle.evaluate_ctx(ctx, {"question": "variability", "h1_value": 0.1, "candidates": [{"fractional_error": 0.01}]})
    assert math.isclose(v["rows"][1]["expected_significance"], 0.1 / (math.sqrt(2) * 0.01)) and v["rows"][1]["discriminates"]
    assert oracle.validate_spec({"question": "motion", "candidates": [{"added_years_after_last": [30]}]})
    assert oracle.validate_spec({"question": "x", "candidates": []})
    real = run("syn-hpm-1")["intel"]["oracle"]
    assert real["validation"]["valid"] and real["examples"]["motion"]["available"]


def test_causal_confounders_and_criteria_never_claim_causation():
    assert causal.confounders("calibration", "flux_difference") == ["detector", "epoch"]
    assert causal.confounders("parallax", "position_change") == ["epoch"]
    lab = run("syn-var-1")["intel"]["causal"]
    for m in lab["models"]:
        assert m["criteria"]["C5"] is False
        assert m["label"] in ("contradicted by HYPO-1", "null model", "association only", "causal hypothesis (not established)")
    w = causal.warnings({"causal": [{"from": "calibration", "rel": "causes", "to": "flux_difference"}, {"from": "x", "rel": "correlates with", "to": "y"}]}, lab["models"])
    assert len(w) == 1 and "user-proposed" in w[0]["warning"] and "(C5) is not possible" in w[0]["warning"]


# ------------------------------------------------------------------ REPRONET-1
def test_reproduction_manifests_validate_and_comparison_classes():
    a, a2, b = run("syn-var-1"), run("syn-var-1", {"aperture_radius_px": 2.5}), run("syn-hpm-1")
    ma, ma2, mb = a["intel"]["reproduction"], a2["intel"]["reproduction"], b["intel"]["reproduction"]
    for m in (ma, ma2, mb):
        assert repronet.validate(m) == [] and m["dataset"]["files"] and m["stages"] and m["environment"] and m["limitations"]
    assert repronet.compare(ma, copy.deepcopy(ma))["status"] == "exact match"
    assert repronet.compare(ma, ma2)["classes"] == ["methodological"]
    assert "different input data" in repronet.compare(ma, mb)["classes"]
    t = copy.deepcopy(ma)
    t["outcomes"]["variability"]["category"] = "edited"
    assert any("digest" in e for e in repronet.validate(t))
    env2 = copy.deepcopy(ma)
    env2["environment"]["scipy"] = None
    env2["stages"][0]["digest"] = "0" * 64
    assert repronet.compare(ma, env2)["classes"][0] == "missing dependency"
    num = copy.deepcopy(ma)
    num["stages"][-1]["digest"] = "1" * 64
    assert repronet.compare(ma, num)["status"] == "numerical"
    assert "not show the result is scientifically valid" in repronet.compare(ma, ma)["note"]


# ------------------------------------------------------------------ WHATIF-1, FINGERPRINT-1, INSTCHECK-1, BUDGET-1
@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
def test_whatif_is_isolated_validated_and_refuses_without_a_method(tid):
    c = run(tid)
    before = copy.deepcopy(c["rec"])
    w = whatif.engine(c["rec"], c["disc"], c["intel"]["instrumental"], c["intel"]["causal"], c["intel"]["negotiation"])
    assert c["rec"] == before and cf.record_hash(c["rec"]) == c["rec"]["content_hash"], "the baseline is never modified"
    by = {q["id"]: q for q in w["questions"]}
    assert [q["id"] for q in w["questions"]] == [q[0] for q in whatif.QUESTIONS] and by["W3"]["kind"] == "no valid method"
    assert w["motion_context"]["validated"], "the refit reproduces the recorded motion fit before any what-if"
    v = by["W6"]["motion"]
    assert v["hypothetical"] and v["after"]["snr"] < v["before"]["snr"], "a visit at the static position weakens the motion"
    tr = whatif.hypothetical_visit(w["motion_context"], 1.0, "track")
    assert tr["after"]["sigma_mas_yr"] < tr["before"]["sigma_mas_yr"], "a visit on the track tightens the fit"
    assert not whatif.hypothetical_visit(w["motion_context"], 50.0)["available"]
    assert whatif.changes({"m": {"category": "a"}, "v": {"category": "b"}}, {"m": {"category": "a"}, "v": {"category": "c"}}) == \
        {"changed": [{"question": "v", "baseline": "b", "scenario": "c"}], "stable": [{"question": "m", "baseline": "a", "scenario": "a"}]}


def test_fingerprint_recomputes_and_never_scores():
    c = run("syn-var-1")
    fp = c["intel"]["fingerprint"]
    var = next(q for q in fp["questions"] if q["question"] == "variability")
    dims = {d["id"]: d for d in var["dimensions"]}
    assert dims["F2"]["state"] == "changes", "this candidate depends on the reference calibration"
    assert dims["F4"]["state"] == "not tested"
    assert all(d["state"] in fingerprint.STATES for q in fp["questions"] for d in q["dimensions"]) and not any("score" in k for k in fp)
    assert cf.reassess(c["rec"]) == {o["question"]: o for e in c["rec"]["events"] if e["step"] == "assess" for o in e["data"]["outcomes"]}, \
        "re-assessment without change reproduces the record, so every difference comes from the stated change"
    stab = {"runs": [{"label": "aperture +0.5 px", "changed": {"variability": ["a", "b"]}, "categories": {"variability": "b"}}]}
    var2 = next(q for q in fingerprint.fingerprint(c["rec"], stab)["questions"] if q["question"] == "variability")
    assert next(d for d in var2["dimensions"] if d["id"] == "F4")["state"] == "changes"


def test_instrumental_check_and_budget():
    c = run("syn-var-1")
    ic = c["intel"]["instrumental"]
    assert {r["state"] for r in ic["checks"]} <= set(instcheck.STATES) and "does not make a signal astrophysical" in ic["note"]
    assert next(r for r in ic["checks"] if r["id"] == "I8")["state"] == "not testable here"
    assert next(r for r in ic["checks"] if r["id"] == "I3")["state"] == "ruled out by rule", "V-ERRMODEL is contradicted by CALCHECK-1"
    bg = c["intel"]["budget"]
    shares = [r["variance_share"] for r in bg["questions"]["variability"]["rows"] if r["variance_share"] is not None]
    assert math.isclose(sum(shares), 1.0, rel_tol=1e-9)
    assert bg["counts"]["unquantified"] == len(bg["unquantified"]) > 0 and all(r["class"] in budget.CLASSES for r in bg["unquantified"])


# ------------------------------------------------------------------ browser parity
@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_intelligence_functions_match_python(tmp_path):
    a, b = run("syn-var-1"), run("syn-hpm-1")
    mem = memory.build(corpus(a, b))
    queries = ["Why did the brightness calibration look odd?", "proper motion and parallax", "zebra", "too few visits; blending"]
    actions = [{"id": "a1", "label": "x", "question": "variability", "concepts": []}, {"id": "a2", "question": None, "concepts": ["blending", "wavelength"]},
               {"id": "a3", "question": "motion", "concepts": ["registration"]}]
    led = a["intel"]["adversary"]
    ids = [i["id"] for x in led["conclusions"] for q in x["questions"] for i in q["items"]]
    sessions = [{}, {"challenges": [{"id": ids[0], "status": "acknowledged", "note": "n"}, {"id": ids[1], "status": "resolved"}, {"id": ids[2], "status": "resolved", "ref": "e:1"}]},
                {"challenges": [{"id": i, "status": "acknowledged"} for i in ids],
                 "debug": [{"kind": "reproduction", "content_hash": a["rec"]["content_hash"], "verdict": "failed reproduction"}]},
                {"debug": [{"kind": "reproduction", "content_hash": a["rec"]["content_hash"], "verdict": "exact reproduction"}]}]
    octx = {**b["intel"]["oracle"]["context"]}
    vctx = {**a["intel"]["oracle"]["context"]}
    specs = [[octx, {"question": "motion", "candidates": [{"added_years_after_last": [1.0]}, {"added_years_after_last": [0.5, 1.5], "error_factor": 0.5, "label": "two"}]}],
             [octx, {"question": "motion", "h1_value": 40.0, "candidates": [{"added_years_after_last": [2.0]}]}],
             [vctx, {"question": "variability", "candidates": [{"fractional_error": 0.01}, {"fractional_error": 0.002}]}],
             [vctx, {"question": "variability", "h1_value": 0.2, "candidates": [{"fractional_error": 0.05}]}]]
    bad_specs = [{"question": "motion", "candidates": [{"added_years_after_last": [30]}]}, {"question": "x"}, {"question": "variability", "candidates": [{"fractional_error": 2}]}, None]
    mc = [a["intel"]["whatif"]["motion_context"], b["intel"]["whatif"]["motion_context"]]
    visits = [[0, 1.0, "static", 1.0], [1, 2.5, "track", 0.5], [1, 1.0, "static", 3.0], [0, 40.0, "static", 1.0]]
    ma, mb = a["intel"]["reproduction"], b["intel"]["reproduction"]
    ma2 = run("syn-var-1", {"aperture_radius_px": 2.5})["intel"]["reproduction"]
    env2 = copy.deepcopy(ma)
    env2["environment"]["scipy"] = None
    env2["stages"][0]["digest"] = "0" * 64
    tam = copy.deepcopy(ma)
    tam["outcomes"]["variability"]["category"] = "x"
    repro_cases = [[ma, ma], [ma, ma2], [ma, mb], [ma, env2]]
    sess_e = {"content_hash": "b" * 64, "created_at": "2026-11-01T00:00:00+00:00",
              "hypotheses": [{"id": "h1", "statement": "It dimmed.", "created_at": "2026-11-01T00:00:00+00:00", "versions": [{"at": "2026-11-01T00:00:00+00:00", "text": "x"}], "tests": []}],
              "experiments": [{"id": "e1", "template": "sensitivity", "status": "completed", "created_at": "2026-11-01T00:00:00+00:00"}],
              "scenarios": [{"label": "t8", "at": "2026-11-01T00:00:00+00:00", "scenario_hash": "c" * 64}, None], "causal": [{"from": "a", "rel": "causes", "to": "b"}],
              "negative": [{"attempted": "x"}], "debug": [{"kind": "reproduction", "verdict": "exact reproduction", "at": "2026-11-01T00:00:00+00:00"}, {"kind": "diff"}],
              "history": [{"seq": 1, "at": "2026-11-01T00:00:00+00:00", "kind": "decision.record", "summary": "s"}, {"seq": 2, "at": "2026-11-01T00:00:00+00:00", "kind": "x.y", "summary": "t"}]}
    lab = a["intel"]["causal"]
    csess = [{"causal": [{"from": "calibration", "rel": "causes", "to": "flux_difference"}, {"from": "noise_model", "rel": "drives", "to": "x"},
                         {"from": "zzz", "rel": "due to", "to": "y"}, {"from": "a", "rel": "near", "to": "b"}, "junk"]}, {}]
    job = {"mem": mem, "queries": queries, "actions": actions, "target": "syn-var-1", "led": led, "gate": a["intel"]["gate"], "sessions": sessions,
           "specs": specs, "bad_specs": bad_specs, "mc": mc, "visits": visits, "repro_cases": repro_cases, "repro_validate": [ma, tam, {"schema": "x"}],
           "sess_e": sess_e, "models": lab["models"], "csess": csess, "causal_words": list(causal.CAUSAL_WORDS),
           "pyg": [0.05, 101.95108, 1.5606769092797264, 1e-7, 123456789.0, 2.0, 0.0001234, -3.14159]}
    p = tmp_path / "job.json"
    p.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/intel_parity.mjs"), str(ROOT), str(p)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    assert js["concepts"] == [memory.query_concepts(q) for q in queries]
    assert js["recall"] == [memory.recall(mem, q) for q in queries]
    assert js["warnings"] == memory.warnings(mem, "syn-var-1", actions)
    J = lambda x: json.loads(json.dumps(x))  # noqa: E731  (the browser receives JSON: tuples become lists)
    py_led = [adversary.overlay(led, s) for s in sessions]
    assert js["ledger"] == J(py_led)
    assert js["gate"] == J([gate.overlay(a["intel"]["gate"], ol, s) for ol, s in zip(py_led, sessions)])
    assert close(js["oracle"], J([oracle.evaluate_ctx(c, s) for c, s in specs]))
    assert js["bad_specs"] == [oracle.validate_spec(s) for s in bad_specs]
    assert close(js["visits"], J([whatif.hypothetical_visit(mc[i], dt, pos, k) for i, dt, pos, k in visits]))
    assert js["repro"] == [repronet.compare(x, y) for x, y in repro_cases]
    assert js["repro_validate"] == [repronet.validate(m) for m in [ma, tam, {"schema": "x"}]]
    assert js["sess_e"] == E.session_entities(sess_e)
    assert js["causal"] == [causal.warnings(s, lab["models"]) for s in csess]
    assert js["pyg"] == [format(x, "g") for x in job["pyg"]] + [format(x, ".4g") for x in job["pyg"]] + [format(x, ".3g") for x in job["pyg"]]


def test_research_cycle_proposes_registered_actions_by_rule_and_levels_bound_execution():
    from skytrace import autonomy, capabilities
    c, a2 = run("syn-var-1"), run("syn-var-1", {"aperture_radius_px": 2.5})
    u = unknownmap.build(c["rec"], c["rep"], c["disc"], [c["rec"]["parameters"], a2["rec"]["parameters"]])
    cy = autonomy.propose(c["intel"], u)
    ids = {a["id"] for a in capabilities.ACTIONS}
    assert [p["rule"] for p in cy["proposals"]][0] == "A6"
    for p in cy["proposals"]:
        assert p["action"] in ids and p["permission"] == capabilities.PERMISSION[p["action"]] and p["rule"] in autonomy.RULES and p["addresses"]
    assert {p["rule"] for p in cy["proposals"]} >= {"A1", "A2", "A3", "A4", "A5"}
    levels = {l["id"]: l for l in capabilities.AUTONOMY_LEVELS}
    assert levels["advisory"]["allows"] == [] and all("network" not in l["allows"] and "export" not in l["allows"] for l in levels.values())
    assert all(a in ids and capabilities.PERMISSION[a] in levels["restricted"]["allows"] for a in capabilities.RESTRICTED_WORKFLOW)
    assert all(x["kind"] in ("counterfactual scenario", "hypothetical observation plan") for x in cy["for_you_to_decide"])
    done = copy.deepcopy(c["intel"])
    done["gate"]["requirements"] = [{**r, "state": "met"} if r["id"] == "G3" else r for r in done["gate"]["requirements"]]
    assert "A1" not in {p["rule"] for p in autonomy.propose(done, u)["proposals"]}
