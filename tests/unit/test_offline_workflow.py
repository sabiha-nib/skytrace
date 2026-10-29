"""The complete server-side workflow with every socket blocked (not just OFFLINE=1 set).

Covers bundle verification, analysis, evidence graph, all copilot questions (local mode),
record save/replay logic, and the HTTP handlers, using only bundled synthetic data.
"""

import json

import pytest

from skytrace import analysis, bundle as bmod
from skytrace.ai import copilot
from skytrace.view import InvestigationView, evidence_graph


@pytest.mark.parametrize("tid", ["syn-hpm-1", "syn-var-1"])
def test_full_workflow_without_network(tid, no_network, monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("META_API_KEY", "would-be-ignored")
    bdir = bmod.SYNTHETIC_ROOT / tid
    assert bmod.verify(bdir)["ok"]
    b = bmod.load(bdir)
    rec = analysis.run(b).to_dict()
    assert {e["step"] for e in rec["events"]} >= {"target", "discover", "measure", "pairs", "astrometry", "assess"}
    v = InvestigationView(rec, b.discovery, b.manifest, b.inspection)
    g = evidence_graph(v, tid)
    assert g["counts"]["claim"] == 3
    for q in ["What changed between these observations?", "Why was an observation excluded?", "What should I investigate next?"]:
        r = copilot.ask(q, v, tid)
        assert r.mode == "local" and r.ok and "OFFLINE=1" in r.problems[0]
    # same inputs -> same content hash (deterministic replay)
    assert analysis.run(b).to_dict()["content_hash"] == rec["content_hash"]


def test_expected_outcomes_on_synthetic_truth():
    """The synthetic bundles have known truth; the deterministic outcomes must match it."""
    out = {}
    for tid in ("syn-hpm-1", "syn-var-1"):
        rec = analysis.run(bmod.load(bmod.SYNTHETIC_ROOT / tid)).to_dict()
        out[tid] = {o["question"]: o for o in next(e for e in rec["events"] if e["step"] == "assess")["data"]["outcomes"]}
    hpm, var = out["syn-hpm-1"], out["syn-var-1"]
    assert hpm["motion"]["category"] == "motion_detected"                      # injected 4.67"/yr motion recovered
    assert abs(hpm["motion"]["evidence"]["z_pmra"]) < 3 and abs(hpm["motion"]["evidence"]["z_pmdec"]) < 3
    assert hpm["variability"]["category"] in ("no_significant_change", "spectral_difference_only")  # constant star
    assert var["variability"]["category"] == "variability_candidate"           # injected 38% dimming
    assert var["motion"]["category"] == "no_significant_change"                # negligible motion
    assert hpm["data_quality"]["evidence"]["n_rejected"] >= 1                  # injected missing-WCS-WAVE file
    assert var["data_quality"]["evidence"]["n_rejected"] >= 1                  # injected overflow flags
