"""Phase 8 epistemic layer on the synthetic fixtures: EPI-1 objects, statuses and lineage; METHOD-DNA-1 integrity;
SCICOMP-1 stages and outcomes (including injected unit, provenance and wording defects); SCIDEBUG-1 recomputation and
divergence localisation; KBOUND-1 rules; CLAIMX-1 modes; NEG-1; BLIND-1; UFLOW-1; LINEAGE-1; MODELS-1; FUTURE-1;
NEXTX-1 and QFORGE-1; INTEG-1 (including the investigation report); REVIEWX-1; REPROX-1 verdicts; SIMCHECK-1 refusals;
the evidence-vault chain; and Python/browser parity of every browser port."""

import copy
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from skytrace import (analysis, blindspot, bundle as bmod, claims, counterfactual as cf, decide, discovery, epistemic as epi, futurelab,
                      infogain, integrity, ledger, lineage, methodgenome as mg, modelarena, negspace, quality, report, reprox, reviewx, scicomp,
                      scidebug, session, simcheck, uflow)
from skytrace.review import CAUSAL_WORDS
from skytrace.view import InvestigationView, evidence_graph

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
_C = {}


def ctx(tid):
    if tid not in _C:
        b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
        inv = analysis.run(b, {})
        rec = json.loads(json.dumps(inv.to_dict(), default=str))
        v = InvestigationView(rec, b.discovery, b.manifest, b.inspection)
        disc = discovery.report(rec, b.discovery, b.manifest, {})
        L = ledger.build(rec, evidence_graph(v, tid), b.discovery)
        Q = quality.checks(rec, b.manifest, b.discovery, b.path)
        G = epi.build(rec, disc, L, b.manifest)
        comp = scicomp.compile_investigation(rec, G, disc, L, b.manifest, Q)
        _C[tid] = dict(b=b, inv=inv, rec=rec, disc=disc, L=L, Q=Q, G=G, comp=comp)
    return _C[tid]


def recompile(c, rec):
    G = epi.build(rec, c["disc"], c["L"], c["b"].manifest)
    return scicomp.compile_investigation(rec, G, c["disc"], c["L"], c["b"].manifest, c["Q"])


# ------------------------------------------------------------------ EPI-1
@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
def test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses(tid):
    c = ctx(tid)
    G = c["G"]
    ids = [n["id"] for n in G["nodes"]]
    assert len(ids) == len(set(ids))
    assert epi.build(c["rec"], c["disc"], c["L"], c["b"].manifest)["nodes"] == G["nodes"], "deterministic"
    for n in G["nodes"]:
        assert n["kind"] in epi.KINDS
        if n["kind"] in ("transformation", "method"):
            assert n["status"] is None, "procedures carry no epistemic status"
        else:
            assert n["status"] in epi.STATUSES and n["status_rule"] in epi.STATUS_RULES
    by = {n["id"]: n for n in G["nodes"]}
    assert all(n["status"] == "simulated" for n in G["nodes"] if n["kind"] in ("source", "observation")), "synthetic files are simulated (S1)"
    assert all(n["status"] == "measured" for n in G["nodes"] if n["kind"] == "measurement")
    assert all(n["status"] == "hypothesized" for n in G["nodes"] if n["kind"] == "hypothesis")
    assert by["fit:motion"]["status"] == "model-dependent"
    assert by["claim:data_quality"]["status"] == "derived"
    for e in G["edges"]:
        assert e["source"] in by and e["target"] in by


def test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims():
    G = ctx("syn-var-1")["G"]
    back = epi.trace(G, "claim:variability")
    kinds = back["by_kind"]
    for k in ("source", "observation", "measurement", "derived", "method", "assumption", "uncertainty", "transformation"):
        assert kinds.get(k), f"a claim must trace back to {k}"
    ids = {x["id"] for x in back["nodes"]}
    assert "method:PAIRDIFF-2" in ids and "asm:threshold:variability_z" in ids and "model:constant_refs" in ids
    assert not any(i.startswith(("epoch:", "fit:")) for i in ids), "the brightness claim does not depend on the motion fit"
    f = next(n["id"] for n in G["nodes"] if n["id"].startswith("file:SYNTHETIC"))
    fwd = {x["id"] for x in epi.trace(G, f, "forward")["nodes"]}
    assert "claim:data_quality" in fwd and "conclusion:investigation" in fwd
    m = next(n["id"] for n in G["nodes"] if n["id"].startswith("meas:"))
    mb = {x["id"] for x in epi.trace(G, m)["nodes"]}
    assert sum(1 for i in mb if i.startswith("meas:")) == 0, "one measurement does not depend on other measurements"
    assert epi.trace(G, "nope")["error"]


def test_asserted_words_ignore_negated_uses():
    assert epi.asserted_words("This is not proof that the source is static.", ["proof"]) == []
    assert epi.asserted_words("No evidence of a discovery here.", ["discovery"]) == []
    assert epi.asserted_words("This is not proof. It proves nothing new.", ["proof", "proves"]) == ["proves"]
    assert epi.asserted_words("The discovery confirms it.", ["discovery", "confirms"]) == ["confirms", "discovery"]
    assert epi.asserted_words("undiscovered", ["discovered"]) == []


# ------------------------------------------------------------------ METHOD-DNA-1
def test_method_genome_is_complete_and_its_tests_exist():
    g = mg.genome(ctx("syn-var-1")["rec"])
    assert not g["unregistered_in_run"], "every method the run used is in the genome"
    for m in g["methods"]:
        assert m["output_status"] in ("measured", "derived", "model-dependent")
        assert all(i["unit"] == mg.QTYPES[i["type"]] for i in m["inputs"] + m["outputs"])
        assert m["health"]["n_defined"] == len(m["known_answer_tests"]) > 0, f"{m['id']}: every named known-answer test exists"
        assert not m["health"]["documentation_missing"], m["id"]
        assert set(m["dependencies"]) <= set(mg.BY_ID), m["id"]
        assert (ROOT / m["module"]).exists()
    c = mg.compare("PAIRDIFF-1", "PAIRDIFF-2")
    assert c["compatible"] and "z" in c["shared_output_types"]
    assert not mg.compare("APPHOT-1", "REFSEL-2")["compatible"]
    dg = mg.dependency_graph()
    assert {"source": "WLMATCH-2", "target": "PAIRDIFF-1"} in dg["edges"]


# ------------------------------------------------------------------ SCICOMP-1
@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
def test_compiler_runs_every_stage_and_states_the_precedence_rule(tid):
    comp = ctx(tid)["comp"]
    assert [s["id"] for s in comp["stages"]] == [s for s, _ in scicomp.STAGES[:-1]]
    assert comp["outcome"] in scicomp.OUTCOMES
    assert comp["outcome"] == "requires scientific review", "open artefact explanations require review on both fixtures"
    assert all(c["outcome"] in ("pass", "warning", "fail", "not applicable") and c["rule"] for c in comp["checks"])
    assert not [c for c in comp["checks"] if c["outcome"] == "fail"], [c for c in comp["checks"] if c["outcome"] == "fail"]
    assert "does not mean any conclusion is true" in comp["meaning"]


def test_compiler_detects_injected_defects():
    c = ctx("syn-var-1")
    rec = copy.deepcopy(c["rec"])
    next(e for e in rec["events"] if e["step"] == "inspect")["data"]["image_bunit"] = "DN/s"
    rec["content_hash"] = cf.record_hash(rec)
    assert recompile(c, rec)["outcome"] == "incompatible", "a unit APPHOT-1 cannot accept is a type error"
    rec = copy.deepcopy(c["rec"])
    next(e for e in rec["events"] if e["step"] == "variability")["data"]["pairs"][0]["z"] += 1
    out = recompile(c, rec)
    assert out["outcome"] == "invalid provenance" and any(x["id"] == "V1" and x["outcome"] == "fail" for x in out["checks"])
    rec = copy.deepcopy(c["rec"])
    a = next(e for e in rec["events"] if e["step"] == "assess")
    a["data"]["outcomes"][2]["statement"] = "We discovered a variable star."
    rec["content_hash"] = cf.record_hash(rec)
    out = recompile(c, rec)
    assert out["outcome"] == "unsupported claim" and any(x["id"].startswith("C1") and x["outcome"] == "fail" for x in out["checks"])
    rec = copy.deepcopy(c["rec"])
    pz = next(e for e in rec["events"] if e["step"] == "variability")["data"]["pairs"][0]
    pz["sigma_ujy"] *= 2
    rec["content_hash"] = cf.record_hash(rec)
    assert any(x["id"] == "U2" and x["outcome"] == "fail" for x in recompile(c, rec)["checks"]), "a σ that does not recompute is caught"


# ------------------------------------------------------------------ SCIDEBUG-1
def test_debugger_breakpoints_are_real_stages_and_recompute_exactly():
    c = ctx("syn-var-1")
    rec = c["rec"]
    bps = scidebug.breakpoints(rec)
    assert [b["id"] for b in bps] == [s for s, _, _ in scidebug.STAGES], "every listed breakpoint exists in the record"
    pid = next(n["id"] for n in c["G"]["nodes"] if n["id"].startswith("pair:"))
    assert scidebug.inspect(rec, pid)["verdict"] == "recomputes identically"
    assert scidebug.inspect(rec, "claim:variability")["verdict"] == "recomputes identically"
    assert scidebug.inspect(rec, "fit:motion")["verdict"] in ("recomputes identically", "recomputes within tolerance")
    assert scidebug.inspect(rec, "meas:" + pid[5:].split("|")[0])["verdict"] == "not recomputable from the record alone"
    bad = copy.deepcopy(rec)
    next(e for e in bad["events"] if e["step"] == "variability")["data"]["pairs"][0]["flux_a_ujy"] += 50
    assert scidebug.inspect(bad, pid)["verdict"] == "inconsistent recorded values"


def test_differential_debugging_finds_the_earliest_divergence():
    c = ctx("syn-var-1")
    other = json.loads(json.dumps(analysis.run(c["b"], {"aperture_radius_px": 2.5}).to_dict(), default=str))
    d = scidebug.diff(c["rec"], other)
    assert d["earliest_divergence"] == "measurement"
    assert [p["key"] for p in d["parameters"]] == ["aperture_radius_px"] and d["assumptions"]
    assert {s["id"]: s["kind"] for s in d["stages"]}["ingestion"] == "identical"
    same = scidebug.diff(c["rec"], c["rec"])
    assert same["earliest_divergence"] is None and same["identical_hash"]


# ------------------------------------------------------------------ KBOUND-1, CLAIMX-1
def test_knowledge_boundary_rules():
    for tid, expect in (("syn-var-1", {"claim:data_quality": "established", "claim:motion": "supported under assumptions", "claim:variability": "unresolved"}),
                        ("syn-hpm-1", {"claim:data_quality": "established", "claim:variability": "unresolved", "claim:motion": "unresolved"})):
        c = ctx(tid)
        b = claims.boundary(c["rec"], c["G"], c["disc"], c["L"], c["comp"])
        got = {i["id"]: i["region"] for i in b["items"] if i["kind"] == "claim"}
        assert got == expect, (tid, got)
        assert all(i["rule"] in claims.REGION_RULES and i["why"] for i in b["items"])
        assert {"Q-CAUSE", "Q-DISCOVERY"} <= {i["id"] for i in b["items"] if i["region"] == "outside the evidence"}
        assert "confidence" not in json.dumps(b["counts"])


def test_claim_stress_modes_and_results():
    c = ctx("syn-var-1")
    s = claims.stress(c["rec"], c["G"], c["disc"], c["L"], c["comp"], c["Q"], "variability")
    assert [m["mode"] for m in s["modes"]] == [m for m, _ in claims.MODES]
    assert all(m["result"] in claims.RESULTS and m["rule"] for m in s["modes"])
    r = {m["mode"]: m["result"] for m in s["modes"]}
    assert r["alternatives"] == "warning" and r["statistics"] == "warning" and r["wording"] == "pass"
    assert r["reproducibility"] == "not tested"
    s2 = claims.stress(c["rec"], c["G"], c["disc"], c["L"], c["comp"], c["Q"], "variability", repro={"verdict": "reproduced"})
    assert {m["mode"]: m["result"] for m in s2["modes"]}["reproducibility"] == "pass"
    h = ctx("syn-hpm-1")
    sv = claims.stress(h["rec"], h["G"], h["disc"], h["L"], h["comp"], h["Q"], "variability")
    assert {m["mode"]: m["result"] for m in sv["modes"]}["sensitivity"] == "warning", "spectral_difference_only changes at an 8σ threshold"


# ------------------------------------------------------------------ NEG-1, BLIND-1
def test_negative_knowledge_registry_records_what_failed():
    c = ctx("syn-var-1")
    n = negspace.registry(c["rec"], c["disc"], c["L"], env_report={"services": [{"service": "IRSA", "host": "irsa", "verdict": "proxy_refused"},
                                                                              {"service": "GitHub", "host": "github", "verdict": "http_400"}]})
    cats = {e["category"] for e in n["entries"]}
    assert {"unavailable data", "missing measurement", "invalid comparison", "unresolved contradiction", "inconclusive test", "known limitation"} <= cats
    assert all(e["distinction"] in negspace.DISTINCTIONS and e["category"] in negspace.CATEGORIES for e in n["entries"])
    assert all(k in e for e in n["entries"] for k in ("attempted", "why", "happened", "failure", "unknown", "repeatable", "unblock"))
    assert [e for e in n["entries"] if e["id"].startswith("N-ENV")] and not [e for e in n["entries"] if "github" in e["happened"]]


def test_blindspot_coverage_is_over_defined_checks_only():
    c = ctx("syn-var-1")
    b = blindspot.base(c["rec"], c["disc"], c["comp"], c["Q"], c["disc"]["uncertainty"])
    assert [r["id"] for r in b["checks"]] == [x[0] for x in blindspot.CHECKS]
    assert all(r["state"] in blindspot.STATES for r in b["checks"])
    assert "%" not in json.dumps(b["counts"])
    o = blindspot.overlay(b, {"examined": [b["checks"][0]["pairs"][0]], "notebook": [{"id": "n1", "author": "user", "text": "This proves it."}]}, CAUSAL_WORDS)
    st = {r["id"]: r["state"] for r in o["checks"]}
    assert st["epochs"] == "partially examined" and st["language"] == "partially examined" and st["boundaries"] == "not examined"


# ------------------------------------------------------------------ UFLOW-1, LINEAGE-1
def test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions():
    c = ctx("syn-var-1")
    u = uflow.flow(c["rec"], c["disc"]["uncertainty"])
    assert {n["category"] for n in u["nodes"]} <= set(uflow.CATEGORIES)
    ids = {n["id"] for n in u["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in u["edges"])
    assert any(g["step"] == "WLMATCH-2" for g in u["not_propagated"])
    pm = next(n for n in u["nodes"] if n["id"] == "u:pm")
    fit = next(e for e in c["rec"]["events"] if e["step"] == "astrometry")["data"]["fit"]
    assert pm["result"]["sig_xi"] == fit["sig_xi"], "values are recorded values, not re-estimates"


def test_lineage_refers_only_to_recorded_stages():
    c = ctx("syn-var-1")
    for rid in ("claim:variability", "fit:motion", next(n["id"] for n in c["G"]["nodes"] if n["id"].startswith("pair:"))):
        lin = lineage.lineage(c["rec"], c["b"].manifest, c["G"], rid, {"skytrace": "9.9"})
        assert [s["stage"] for s in lin["stages"]] == lineage.STAGES
        assert lin["complete"], (rid, lin["missing"])
        assert lin["dependency_changes"][0]["package"] == "skytrace"
    pair = lineage.lineage(c["rec"], c["b"].manifest, c["G"], next(n["id"] for n in c["G"]["nodes"] if n["id"].startswith("pair:")))
    assert len(pair["stages"][0]["fingerprints"]) == 2, "a comparison traces to exactly its two files"
    assert lineage.lineage(c["rec"], None, c["G"], "claim:motion")["missing"] == ["imported"], "without the manifest the import stage is missing, not invented"


# ------------------------------------------------------------------ MODELS-1, FUTURE-1
def test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit():
    for tid, moving in (("syn-hpm-1", True), ("syn-var-1", False)):
        m = modelarena.arena(ctx(tid)["rec"])
        for ax in m["axes"].values():
            assert ax["validation"]["agrees"]
            assert (ax["delta_aic"] > 2) == moving, (tid, ax["delta_aic"])
            assert ax["models"][0]["k"] == 1 and ax["models"][1]["k"] == 2
    assert "probability" not in json.dumps(modelarena.arena(ctx("syn-hpm-1")["rec"])).replace("not necessarily", "")


def test_futurelab_formula_is_validated_before_scenarios():
    c = ctx("syn-var-1")
    v = futurelab.validate(c["rec"])
    assert v["valid"]
    f = futurelab.scenarios(c["rec"], c["disc"])
    base = next(s for s in f["scenarios"] if s["id"] == "baseline")["rows"]
    assert not base[0]["hypothetical"] and all(r["hypothetical"] for r in base[1:])
    assert all(base[i + 1]["sigma_pm"] < base[i]["sigma_pm"] for i in range(len(base) - 1)), "a longer baseline improves sensitivity"
    assert math.isclose(futurelab.pair_precision(0.1, 1000, 2.0), 0.1 * 1000 / (5 * math.sqrt(2) * 2))


# ------------------------------------------------------------------ NEXTX-1, QFORGE-1
def test_decisions_are_explained_and_questions_cite_their_source():
    c = ctx("syn-var-1")
    b = claims.boundary(c["rec"], c["G"], c["disc"], c["L"], c["comp"])
    st = {q: claims.stress(c["rec"], c["G"], c["disc"], c["L"], c["comp"], c["Q"], q) for q in ("variability", "motion", "data_quality")}
    n = decide.next_steps(b, infogain.analyse(c["disc"]["hypotheses"], True), st, c["comp"])
    recs = n["recommendations"]
    assert recs and [r["rank"] for r in recs] == list(range(1, len(recs) + 1))
    assert all(r.get("why_not_higher") for r in recs[1:]) and all(r["reasoning"] and r["limitations"] for r in recs)
    assert "optimal" not in n["order_rule"] and "not an optimisation" in n["note"]
    qf = decide.questions(c["disc"], b, futurelab.scenarios(c["rec"], c["disc"]))
    assert all(q["category"] in decide.CATEGORIES and q["prompted_by"] for q in qf["questions"])


# ------------------------------------------------------------------ INTEG-1, REVIEWX-1
def test_integrity_firewall_flags_problems_without_rewriting():
    c = ctx("syn-var-1")
    f = integrity.facts(c["rec"], True)
    t = "We discovered a variable star with high probability: flux 12345.67 µJy (method FOO-3)."
    r = integrity.check(t, f)
    bad = {x["id"] for x in r["checks"] if not x["ok"]}
    assert {"I1", "I2", "I3", "I6", "I8", "I11", "I12"} <= bad and r["outcome"] == "needs attention"
    good = (f"Synthetic test data (run {c['rec']['content_hash'][:12]}). The variability candidate rests on reference-calibrated pairs; "
            "limitations: aperture fluxes are not aperture-corrected.")
    assert integrity.check(good, f)["outcome"] == "ready"
    md = report.render_markdown(c["inv"])
    assert "## Outcomes and limitations" in md
    assert integrity.check(md, f)["outcome"] == "ready", [x for x in integrity.check(md, f)["checks"] if not x["ok"]]


def test_review_board_links_every_item():
    c = ctx("syn-var-1")
    st = {q: claims.stress(c["rec"], c["G"], c["disc"], c["L"], c["comp"], c["Q"], q) for q in ("variability", "motion", "data_quality")}
    rb = reviewx.board(c["comp"], st, integrity.check(report.render_markdown(c["inv"]), integrity.facts(c["rec"], True)), mg.genome(c["rec"]))
    assert [p["id"] for p in rb["perspectives"]] == [p[0] for p in reviewx.PERSPECTIVES]
    assert all(i["links"] for p in rb["perspectives"] for i in p["items"])
    assert "not peer review" in rb["note"]


# ------------------------------------------------------------------ REPROX-1, SIMCHECK-1
def test_reproduction_verdicts(tmp_path):
    c = ctx("syn-var-1")
    assert reprox.reproduce(c["rec"], c["b"].path)["verdict"] == "exact reproduction"
    assert reprox.reproduce(c["rec"], tmp_path / "missing")["verdict"] == "blocked reproduction"
    t = copy.deepcopy(c["rec"])
    next(e for e in t["events"] if e["step"] == "variability")["data"]["pairs"][0]["z"] += 1
    r = reprox.reproduce(t, c["b"].path)
    assert r["verdict"] == "failed reproduction" and r["comparison"]["diff"]["earliest_divergence"] == "statistics"
    t2 = copy.deepcopy(c["rec"])
    t2["parameters"]["aperture_radius_px"] = 2.5          # the record states parameters its values were not made with
    t2["content_hash"] = cf.record_hash(t2)
    assert reprox.reproduce(t2, c["b"].path)["verdict"] == "failed reproduction", "nothing recorded explains the difference"
    t3 = copy.deepcopy(t2)
    t3["software"]["numpy"] = "1.26.0"                      # ...but if the record was made with other software, that is the documented reason
    assert reprox.reproduce(t3, c["b"].path)["verdict"] == "reproduction with documented differences"


def test_simulation_audit_refuses_invalid_scenarios():
    assert simcheck.audit({"seed": 1})["status"] == "refused"


# ------------------------------------------------------------------ VAULT-1
def test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid():
    s = session.new("vault")
    s = session.finalize(session.log(session.log(s, "a.b", "one"), "a.b", "two"))
    assert all("h" in e for e in s["history"]) and session.validate(s) == []
    v = session.verify_chain(s["history"])
    assert v["verified"] == 3 and not v["broken"]
    t = copy.deepcopy(s)
    t["history"][1]["summary"] = "edited"
    assert any("chain broken" in e for e in session.validate(t))
    old = copy.deepcopy(s)
    for e in old["history"]:
        del e["h"]
    assert session.validate(old) == [], "0.7 sessions without links stay valid"
    trimmed = copy.deepcopy(s)
    trimmed["history"] = trimmed["history"][1:]
    vt = session.verify_chain(trimmed["history"])
    assert vt["anchor"] == 2 and not vt["broken"]


# ------------------------------------------------------------------ parity
@pytest.mark.skipif(not NODE, reason="node not installed")
def test_browser_epistemic_functions_match_python(tmp_path):
    c, h = ctx("syn-var-1"), ctx("syn-hpm-1")
    clean = lambda r: json.loads(json.dumps(r).replace("NaN", "null"))  # noqa: E731  (the browser receives NaN as null)
    other = clean(json.loads(json.dumps(analysis.run(c["b"], {"aperture_radius_px": 2.5}).to_dict(), default=str)))
    rv, rh = clean(c["rec"]), clean(h["rec"])
    G = c["G"]
    pid = next(n["id"] for n in G["nodes"] if n["id"].startswith("pair:"))
    trace_cases = [[G, "claim:variability", "back"], [G, "claim:motion", "back"], [G, pid, "forward"], [G, "file:catalogue", "forward"], [G, "x", "back"]]
    word_cases = [["This is not proof. It proves nothing.", ["proof", "proves"]], ["No discovery; but a discovery later!", ["discovery"]],
                  ["Caused by χ² drift; not caused by noise", ["caused"]], ["undiscovered", ["discovered"]]]
    diff_cases = [[rv, other], [rv, rv], [rv, rh]]
    base = blindspot.base(c["rec"], c["disc"], c["comp"], c["Q"], c["disc"]["uncertainty"])
    sess = [{"examined": [base["checks"][0]["pairs"][0]], "notebook": [{"id": "n1", "author": "user", "text": "This proves it."}],
             "scenarios": [{"scenario": {"kind": "threshold"}}]}, {}, {"notebook": [{"id": "n", "author": "user", "text": "not proof"}],
                                                                    "experiments": [{"template": "robustness", "status": "completed"}]}]
    blind_cases = [[base, s, list(CAUSAL_WORDS)] for s in sess]
    sigma_cases = [[[2025.4, 2025.9, 2026.4, 2026.9], [100.0, 120.0, 90.0, 110.0]], [[1.0], [1.0]], [[0.0, 1.0, 2.0], [5.0, 5.0, 5.0]]]
    precision_cases = [[0.1, 1000.0, 2.0], [0.05, 5161.98, 0.5]]
    f = integrity.facts(c["rec"], True)
    texts = ["We discovered a variable star with high probability: flux 12345.67 µJy (method FOO-3).",
             f"Synthetic data, run {c['rec']['content_hash'][:12]}. A variability candidate; limitations noted. z = 8.172, scale 1.5607.",
             "SYNTHETIC:SYN11_23:D1 vs SYNTHETIC:SYN11_23:D2 differ by 44.12 µJy. No motion is detected; motion detected later. A counterfactual scenario.",
             report.render_markdown(c["inv"]), "Max |z_cal| = 8.172; |pm|/σ ≥ 5.0 and 0.460513 (fraction); 25% of 48; 2.5.3 version 1.4976043805611425 yr"]
    spec = {"checks": integrity.CHECKS, "phrases": integrity.PHRASES, "units": list(integrity.UNITS), "dimless": list(integrity.DIMLESS),
            "prob_words": list(integrity.PROB_WORDS), "overstate": list(integrity.OVERSTATE)}
    s0 = session.new("p")
    hist = session.log(session.log(s0, "a.b", "one", "ref:1"), "c.d", "two µ ²")["history"]
    filled = session.chain_fill(hist)
    edited = copy.deepcopy(filled)
    edited[1]["summary"] = "x"
    chain_cases = [hist, filled, edited, filled[1:]]
    job = {"trace_cases": trace_cases, "word_cases": word_cases, "diff_cases": diff_cases, "blind_cases": blind_cases, "sigma_cases": sigma_cases,
           "precision_cases": precision_cases, "integrity_cases": [[t, f] for t in texts], "integrity_spec": spec, "chain_cases": chain_cases}
    p = tmp_path / "job.json"
    p.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/epistemic_parity.mjs"), str(ROOT), str(p)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    assert js["trace"] == [epi.trace(g, i, d) for g, i, d in trace_cases]
    assert js["words"] == [epi.asserted_words(t, w) for t, w in word_cases]
    py_diff = [scidebug.diff(a, b) for a, b in diff_cases]
    assert json.loads(json.dumps(js["diff"])) == json.loads(json.dumps(py_diff))
    assert js["blind"] == [json.loads(json.dumps(blindspot.overlay(b, s, w))) for b, s, w in blind_cases]
    assert js["sigma"] == [futurelab.sigma_pm(t, s) for t, s in sigma_cases]
    assert js["precision"] == [futurelab.pair_precision(*x) for x in precision_cases]
    assert js["integrity"] == [integrity.check(t, f) for t in texts]
    assert [x["filled"] for x in js["chains"]] == [[e["h"] for e in session.chain_fill(hh)] for hh in chain_cases]
    assert [x["verify"] for x in js["chains"]] == [session.verify_chain(hh) for hh in chain_cases]
