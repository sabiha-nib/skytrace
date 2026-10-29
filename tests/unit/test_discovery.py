"""CAPREG-1, DISC-1, HYPO-1, UNC-1, REGDIAG-1 and PKG-1 on the synthetic fixtures (labelled synthetic)."""

import copy
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path

import pytest

from skytrace import analysis, bundle as bmod, capabilities, discovery, hypotheses, package, uncertainty
from skytrace.ai import copilot, guard, tools
from skytrace.provenance import stable_hash
from skytrace.view import registration_diagnostics
from test_report_ai import _record, view

ROOT = Path(__file__).resolve().parents[2]


def rec(tid):
    return json.loads(_record(tid))


def report(tid, av=None):
    b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
    return discovery.report(rec(tid), b.discovery, b.manifest, av or {"server": True, "network": False})


# ------------------------------------------------------------------ capability registry
def test_registry_names_only_real_methods_and_tests():
    src = "\n".join(p.read_text() for p in (ROOT / "src").rglob("*.py") if p.name != "capabilities.py")
    for c in capabilities.CAPABILITIES:
        for m in c["methods"]:
            assert m in src, f"{c['id']}: method {m} does not appear anywhere in the code"
        for t in c["tests"]:
            assert (ROOT / t).exists(), f"{c['id']}: test file {t} does not exist"
        for p, spec in c["parameters"].items():
            assert tuple(spec["range"]) == analysis.PARAM_BOUNDS[p]
    recorded = {v for v in analysis.methods().values() for v in ([v] if isinstance(v, str) else v)}
    assert recorded <= capabilities.method_ids() | {"LINFIT-LOO-1"}


def test_registry_availability_is_reported_not_assumed():
    reg = capabilities.registry({"server": False, "network": False})
    by = {c["id"]: c for c in reg["capabilities"]}
    assert by["archive"]["available"] is False and "blocked" in by["archive"]["availability_note"]
    assert by["hypotheses"]["available"] is True and by["stability"]["available"] is False
    assert capabilities.registry({})["capabilities"][0]["available"] is None   # unknown stays unknown


# ------------------------------------------------------------------ discovery engine
@pytest.mark.parametrize("tid", ["syn-hpm-1", "syn-var-1"])
def test_inventory_traces_to_manifest_and_counts_unknowns(tid):
    r = report(tid)
    b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
    files = {f["path"]: f["sha256"] for f in b.manifest["files"]}
    obs = [i for i in r["inventory"]["items"] if "included" in i]
    assert len(obs) == len(b.discovery["observations"])
    for i in obs:
        assert i["sha256"] == (files.get(i["file"]) if i["file"] else None)
    nulls = sum(1 for i in r["inventory"]["items"] for k, v in i.items()
                if v is None and k not in ("limitations", "wavelength_um", "release", "file"))
    assert r["inventory"]["summary"]["unknown_fields"] == nulls
    assert r["inventory"]["summary"]["synthetic"] is True


def test_questions_map_to_registered_capabilities_and_refuse_the_rest():
    r = report("syn-var-1")
    ids = {c["id"] for c in capabilities.CAPABILITIES}
    by = {q["id"]: q for q in r["questions"]}
    for q in r["questions"]:
        assert set(q["capabilities"]) <= ids
        if q["status"] == "not answerable":
            assert q["plan"]["missing_inputs"] or q.get("why_not")
    assert by["Q-DISCOVERY"]["status"] == "not answerable" and "confirmation" in by["Q-DISCOVERY"]["why_not"]
    assert by["Q-VAR"]["current_answer"]["category"] == "variability_candidate"
    assert any("synthetic" in l for l in by["Q-VAR"]["plan"]["limitations"])


def test_next_steps_say_when_services_are_unavailable():
    steps = report("syn-var-1", {"server": False, "network": False})["next_steps"]
    acq = [s for s in steps if s["capability"] == "archive"]
    assert acq and all(s["requires_unavailable_service"] and not s["runs_locally"] for s in acq)
    for s in steps:
        assert {"why", "data_required", "can_establish", "cannot_establish"} <= set(s)
        assert not re.search(r"\b\d+\s*%|confidence (?:will|to) (?:rise|increase)", json.dumps(s))   # no promised gains


def test_missing_inputs_make_questions_unanswerable():
    r = rec("syn-var-1")
    r2 = copy.deepcopy(r)
    r2["events"] = [e for e in r2["events"] if e["step"] not in ("pairs", "variability", "astrometry")]
    for e in r2["events"]:
        if e["step"] == "measure":
            e["data"]["astro_code"] = "below_snr"
    by = {q["id"]: q for q in discovery.questions(r2)}
    assert by["Q-VAR"]["status"] == "not answerable" and by["Q-MOT"]["status"] == "not answerable"


# ------------------------------------------------------------------ hypotheses
def test_hypotheses_known_answers():
    hv = {h["id"]: h for q in hypotheses.evaluate(rec("syn-var-1"))["questions"] for h in q["hypotheses"]}
    hh = {h["id"]: h for q in hypotheses.evaluate(rec("syn-hpm-1"))["questions"] for h in q["hypotheses"]}
    assert hv["V-INTRINSIC"]["overall"] == "consistent so far"          # injected 38 % dimming
    assert hv["V-WAVELENGTH"]["overall"] == "untested" and hv["V-BLEND"]["overall"] == "untested"
    assert hh["M-CATALOGUE"]["overall"] == "consistent so far"          # injected catalogue motion
    assert hh["M-STATIC"]["overall"] == "contradicted"
    assert hh["M-REGISTRATION"]["overall"] == "contradicted"
    assert hh["V-INTRINSIC"]["overall"] == "inconclusive"               # constant star: not "contradicted"
    assert "not proof" in hv["M-STATIC"]["tests"][0]["detail"] or "does not prove" in hv["M-STATIC"]["tests"][0]["detail"]


def test_hypotheses_never_produce_probabilities_and_use_known_statuses():
    for tid in ("syn-var-1", "syn-hpm-1"):
        res = hypotheses.evaluate(rec(tid))
        text = json.dumps(res).lower()
        assert "probability" not in text.replace("not a probability", "")
        for q in res["questions"]:
            for h in q["hypotheses"]:
                assert h["overall"] in ("contradicted", "consistent so far", "untested", "inconclusive")
                for t in h["tests"]:
                    assert t["status"] in hypotheses.STATUSES and t["rule"] and t["detail"]


def test_calibration_hypothesis_on_a_gain_change(tmp_path):
    """Synthetic 25 % gain change on a constant star: the calibration explanation is the consistent one."""
    from skytrace.synthetic import SPECS, build
    s = copy.deepcopy(SPECS[1]); s.update(target_id="syn-gain-h", variability=[1, 1, 1, 1], gain_by_pass=[1, 1, 1.25, 1])
    b = bmod.load(build(s, tmp_path / "g"))
    hv = {h["id"]: h for q in hypotheses.evaluate(analysis.run(b).to_dict())["questions"] for h in q["hypotheses"]}
    assert hv["V-CALIB"]["overall"] == "consistent so far"
    assert hv["V-INTRINSIC"]["overall"] != "consistent so far"


# ------------------------------------------------------------------ uncertainty
@pytest.mark.parametrize("tid", ["syn-hpm-1", "syn-var-1"])
def test_uncertainty_recomputes_logged_values_exactly(tid):
    r = rec(tid)
    u = uncertainty.decompose(r)
    a = next(e for e in r["events"] if e["step"] == "astrometry")["data"]
    first = u["motion"]["rows"][0]
    assert first["values"] == {"east": a["fit"]["sig_xi"], "north": a["fit"]["sig_eta"]}
    for p in uncertainty.variability(r, top=1000)["pairs"]:
        if p["calibrated"]:
            assert p["consistent_with_log"], p
            assert abs(sum(p["variance_share"].values()) - 1) < 1e-12
    bound = next(x for x in u["motion"]["rows"] if x["kind"] == "bound")
    assert "not a standard deviation" in bound["detail"]["note"]


# ------------------------------------------------------------------ registration diagnostics
def test_registration_known_answer():
    s = 6.2 / 3600
    th = math.radians(30)
    ma = {"plate": {"coeffs_deg": [0.0, s, 0.0, 0.0, 0.0, s], "n_refs": 10, "rms_mas": 100.0}, "predicted_xy": [29.0, 29.0]}
    # B: rotated by 30 deg, scale 1.01, shifted by (2, -1) px in B's frame at the target
    M = [[1.01 * s * math.cos(th), -1.01 * s * math.sin(th)], [1.01 * s * math.sin(th), 1.01 * s * math.cos(th)]]
    mb = {"plate": {"coeffs_deg": [0.0, M[0][0], M[0][1], 0.0, M[1][0], M[1][1]], "n_refs": 8, "rms_mas": 120.0}}
    r = registration_diagnostics(ma, mb)
    assert r["available"] and abs(r["a"]["scale_x_arcsec_px"] - 6.2) < 1e-9 and abs(r["b"]["x_axis_angle_deg"] - 30) < 1e-9
    assert abs(r["relative"]["rotation_deg"] + 30) < 1e-9 and abs(r["relative"]["scale_ratio"] - 1 / 1.01) < 1e-9
    assert registration_diagnostics({"plate": None}, mb)["available"] is False


def test_registration_on_fixture_pairs():
    v = view("syn-hpm-1")
    for p in v.accepted_pairs()[:10]:
        r = v.pair_comparison(p["a"], p["b"])["registration"]
        if r["available"]:
            assert abs(r["a"]["scale_x_arcsec_px"] - 6.2) < 0.15 and abs(r["relative"]["scale_ratio"] - 1) < 0.02


# ------------------------------------------------------------------ package
def test_package_is_deterministic_and_self_verifying():
    r = rec("syn-var-1")
    text = json.dumps(r, indent=1)
    args = (text, r, "# report", {"x": 1}, {"nodes": []}, capabilities.registry({}), {"files": []}, "0.5.0")
    z1, z2 = package.build(*args), package.build(*args)
    assert z1 == z2
    zf = zipfile.ZipFile(io.BytesIO(z1))
    names = {n.split("/", 1)[1]: n for n in zf.namelist()}
    assert {"README.md", "record.json", "SHA256SUMS", "discovery.json", "bundle_manifest.json"} <= set(names)
    for line in zf.read(names["SHA256SUMS"]).decode().splitlines():
        h, f = line.split("  ")
        assert hashlib.sha256(zf.read(names[f])).hexdigest() == h
    pr = json.loads(zf.read(names["record.json"]))
    assert stable_hash({k: v for k, v in pr.items() if k not in ("created_at", "software", "content_hash")}) == pr["content_hash"]
    assert "SYNTHETIC TEST DATA" in zf.read(names["README.md"]).decode()


# ------------------------------------------------------------------ copilot
def test_local_capabilities_answer_passes_guard():
    v = view("syn-var-1")
    res = copilot.ask("What can you do here?", v, "syn-var-1", availability={"server": True, "network": False})
    assert res.mode == "local" and res.ok, res.problems
    assert "list_capabilities" in [c["name"] for c in res.tool_calls]
    assert "SPHEREx / SIMBAD / Gaia acquisition" in res.answer["answer"] and "Not available here" in res.answer["answer"]


def test_evidence_graph_links_each_tested_explanation_to_its_claim():
    from skytrace.view import evidence_graph
    v = view()
    g = evidence_graph(v, "syn-var-1")
    h = hypotheses.evaluate(v.r)
    hyp_nodes = {n["id"]: n for n in g["nodes"] if n["kind"] == "hypothesis"}
    expected = {f"hyp:{x['id']}": (q["question"], x) for q in h["questions"] for x in q["hypotheses"]}
    assert set(hyp_nodes) == expected.keys() and g["counts"]["hypothesis"] == len(expected)
    for nid, (question, x) in expected.items():
        n = hyp_nodes[nid]
        assert n["status"] == x["overall"] and [t["status"] for t in n["tests"]] == [t["status"] for t in x["tests"]]
        assert {"source": f"claim:{question}", "target": nid, "rel": "alternative explanation"} in g["edges"]
        assert {"source": nid, "target": "method:" + h["method"], "rel": "tested by"} in g["edges"]
        assert "probab" not in json.dumps(n).lower()
