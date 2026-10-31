"""Knowledge boundary (KBOUND-1) and claim stress testing (CLAIMX-1).

KBOUND-1 places every claim of an investigation in one of four regions by fixed rules (REGION_RULES), never by a score:
established by the recorded evidence · supported under specified assumptions · unresolved or inconclusive · outside the
current evidence. Each placement says why, which evidence and assumptions matter, which test could move it and which
limitations prevent a stronger statement.

CLAIMX-1 stress-tests one claim in ten modes. Each mode has a documented rule and one result: pass, warning, fail,
inconclusive, not tested or blocked. A failed mode marks a weakness of that claim; it does not invalidate the investigation.
"""

from __future__ import annotations

from . import counterfactual as cf, epistemic as epi
from .review import CAUSAL_WORDS

METHOD_BOUNDARY = "KBOUND-1"
METHOD_STRESS = "CLAIMX-1"
REGIONS = ["established", "supported under assumptions", "unresolved", "outside the evidence"]
REGION_LABEL = {"established": "Established by the recorded evidence", "supported under assumptions": "Supported under specified assumptions",
                "unresolved": "Unresolved or inconclusive", "outside the evidence": "Outside the current evidence"}
REGION_RULES = {
    "B1": "a claim that counts or reads recorded values without a fitted model (status 'derived' or 'measured') and has no review flag is established",
    "B2": "a claim decided through a model-dependent inference, with no open artefact explanation and no recorded contradiction, is supported under the assumptions it depends on",
    "B3": "a claim with an open artefact explanation, a recorded contradiction, or a limited / inconclusive category is unresolved",
    "B4": "a question DISC-1 marks not answerable, and any competing explanation that no test has reached, lies outside the current evidence",
}
LIMITED = {"calibration_limited", "registration_limited", "measurement_failed", "insufficient_data", "spectral_difference_only", "inconclusive", "instrumental"}
POSITIVE = {"variability_candidate", "motion_detected", "motion_inconsistent"}
ALTS = {"variability": ["V-CALIB", "V-ERRMODEL", "V-WAVELENGTH", "V-BLEND"], "motion": ["M-REGISTRATION", "M-CHROMATIC", "M-REFS"]}
MODES = [("compatibility", "Input compatibility"), ("measurement", "Measurement validity"), ("statistics", "Statistical assumptions"),
         ("method", "Method suitability"), ("provenance", "Provenance completeness"), ("sensitivity", "Uncertainty sensitivity"),
         ("alternatives", "Alternative explanations"), ("wording", "Claim wording"), ("reproducibility", "Reproducibility"),
         ("sufficiency", "Evidence sufficiency")]
RESULTS = ["pass", "warning", "fail", "inconclusive", "not tested", "blocked"]


def _outcomes(record):
    a = next((e for e in record["events"] if e["step"] == "assess"), None)
    return {o["question"]: o for o in ((a or {}).get("data") or {}).get("outcomes", [])}


def _hyp(disc):
    return {h["id"]: h for q in (disc.get("hypotheses") or {}).get("questions", []) for h in q.get("hypotheses", [])}


def _assumptions_of(graph, cid, limit=10):
    tr = epi.trace(graph, cid)
    lab = {n["id"]: n for n in graph["nodes"]}
    ids = [x["id"] for x in tr["nodes"] if lab[x["id"]]["kind"] in ("assumption", "model")]
    return [{"id": i, "label": lab[i]["label"]} for i in ids[:limit]], len(ids)


def boundary(record: dict, graph: dict, disc: dict, ledger: dict, compiled: dict) -> dict:
    outs, hyp = _outcomes(record), _hyp(disc)
    nodes = {n["id"]: n for n in graph["nodes"]}
    review = {c["id"]: c for c in compiled["checks"] if c.get("review")}
    cons = ledger.get("contradictions", [])
    items = []
    for q, o in outs.items():
        cid = f"claim:{q}"
        status = nodes.get(cid, {}).get("status")
        open_alts = [a for a in ALTS.get(q, []) if a in hyp and hyp[a]["overall"] != "contradicted"] if o["category"] in POSITIVE else []
        q_cons = [c for c in cons if q == "variability" and ("z" in (c.get("detail") or "") or c.get("rule") == "C1")]
        asm, n_asm = _assumptions_of(graph, cid)
        if o["category"] in LIMITED or open_alts or q_cons:
            region, rule = "unresolved", "B3"
            why = []
            if o["category"] in LIMITED:
                why.append(f"the category itself is limited ({o['category']})")
            if open_alts:
                why.append("artefact explanations not ruled out: " + ", ".join(open_alts))
            if q_cons:
                why.append(f"{len(q_cons)} recorded contradiction(s) (LEDGER-1)")
            why = "; ".join(why)
        elif status in ("derived", "measured"):
            region, rule, why = "established", "B1", f"the claim reads recorded values without a fitted model (status {status}) and no check asks for review"
        else:
            region, rule, why = "supported under assumptions", "B2", f"decided through a {status} inference; it holds if its {n_asm} upstream assumptions and models hold"
        tests = [{"hypothesis": h, "test": t["id"], "status": t["status"], "rule": t["rule"]} for h in (open_alts or ALTS.get(q, [])) if h in hyp
                 for t in hyp[h].get("tests", []) if t["status"] in ("not_tested", "evidence_unavailable", "inconclusive")][:6]
        items.append({"id": cid, "kind": "claim", "statement": o.get("statement"), "category": o.get("category"), "region": region, "rule": rule, "why": why,
                      "evidence": {k: v for k, v in (o.get("evidence") or {}).items() if not isinstance(v, (dict, list))},
                      "assumptions": asm, "n_assumptions": n_asm, "could_change_it": tests or [{"note": "no open test is recorded for this claim"}],
                      "limitations": o.get("limitations") or [], "status": status,
                      "review_flags": [c for c in review if c.endswith(q) or c == "E3" and q == "variability"]})
    for h in hyp.values():
        if h["overall"] in ("untested",) or all(t["status"] in ("not_tested", "evidence_unavailable") for t in h.get("tests", [])):
            items.append({"id": f"hyp:{h['id']}", "kind": "explanation", "statement": h["statement"], "category": h["overall"], "region": "outside the evidence",
                          "rule": "B4", "why": "no test of this explanation could be evaluated with the recorded data", "evidence": {},
                          "assumptions": [], "n_assumptions": 0,
                          "could_change_it": [{"hypothesis": h["id"], "test": t["id"], "status": t["status"], "rule": t["rule"]} for t in h.get("tests", [])][:4],
                          "limitations": [t.get("detail", "") for t in h.get("tests", [])][:3], "status": "hypothesized", "review_flags": []})
    for qq in disc.get("questions", []):
        if qq.get("status") == "not answerable":
            items.append({"id": qq["id"], "kind": "question", "statement": qq["text"], "category": "not answerable", "region": "outside the evidence", "rule": "B4",
                          "why": qq.get("why_not") or "DISC-1 marks it not answerable with the capabilities and data here", "evidence": {},
                          "assumptions": [], "n_assumptions": 0, "could_change_it": [{"note": m.get("input") if isinstance(m, dict) else str(m)} for m in (qq.get("plan") or {}).get("missing_inputs", [])][:4]
                          or [{"note": "a new capability; not available in this release"}], "limitations": [], "status": None, "review_flags": []})
    counts = {r: sum(i["region"] == r for i in items) for r in REGIONS}
    return {"method": METHOD_BOUNDARY, "regions": REGIONS, "region_labels": REGION_LABEL, "rules": REGION_RULES, "items": items, "counts": counts,
            "note": "Regions are categories with stated rules, not confidence levels. 'Established' means established by these records, which here are synthetic."}


def stress(record: dict, graph: dict, disc: dict, ledger: dict, compiled: dict, quality: dict | None, question: str, repro: dict | None = None) -> dict:
    o = _outcomes(record).get(question)
    if not o:
        return {"method": METHOD_STRESS, "claim": f"claim:{question}", "error": "no such claim"}
    checks = {c["id"]: c for c in compiled["checks"]}
    hyp = _hyp(disc)
    R = []

    def add(mode, result, rule, detail, cites=None):
        R.append({"mode": mode, "name": dict(MODES)[mode], "result": result, "rule": rule, "detail": detail, "cites": cites or []})

    def from_checks(ids):
        cs = [checks[i] for i in ids if i in checks]
        if not cs:
            return "not tested", "no applicable check"
        if any(c["outcome"] == "fail" for c in cs):
            return "fail", "; ".join(c["detail"] for c in cs if c["outcome"] == "fail")
        if any(c["outcome"] == "warning" for c in cs):
            return "warning", "; ".join(c["detail"] for c in cs if c["outcome"] == "warning")
        if all(c["outcome"] == "not applicable" for c in cs):
            return "not tested", "not applicable to this record"
        return "pass", "; ".join(c["detail"] for c in cs)[:300]

    def fc(mode, ids, rule):
        r, d = from_checks(ids)
        add(mode, r, rule, d, ids)

    comp_ids = {"variability": ["T3", "T4", "D1"], "motion": ["D2", "D4"], "data_quality": ["T1", "T2", "T5"]}.get(question, [])
    fc("compatibility", comp_ids, "SCI-COMP type and dependency checks for this claim's inputs pass: " + ", ".join(comp_ids))
    dq = {c["id"]: c for c in (quality or {}).get("checks", [])}
    rel = {"variability": ["DQ-VALUES", "DQ-FLAGS", "DQ-PAIRS"], "motion": ["DQ-VALUES", "DQ-ASTRO"], "data_quality": ["DQ-VALUES", "DQ-FLAGS", "DQ-META"]}.get(question, [])
    got = [dq[i] for i in rel if i in dq]
    bad = [c for c in got if c["outcome"] in ("invalid", "incompatible")]
    add("measurement", "warning" if bad else ("pass" if got else "not tested"),
        "DQ-1 checks on the measurements this claim uses are valid (an invalid or incompatible check is a warning: it concerns some items, not necessarily the ones deciding the claim)",
        "; ".join(f"{c['id']} {c['outcome']}" for c in got) or "no data-quality report available", [c["id"] for c in got])
    if question == "variability":
        cc = next(((e.get("data") or {}).get("calibration_check") for e in record["events"] if e["step"] == "variability"), None) or {}
        st = cc.get("status")
        add("statistics", "warning" if st == "underestimated" else ("pass" if st else "not tested"),
            "CALCHECK-1: the stated photometric errors describe constant reference stars (scale ≈ 1); a larger scale is applied, but the error model was wrong by that factor",
            f"error scale {cc.get('error_scale'):.3f} ({st})" if st else "no error-model check recorded", ["scale:calcheck"])
    elif question == "motion":
        fit = next(((e.get("data") or {}).get("fit") for e in record["events"] if e["step"] == "astrometry"), None) or {}
        rc = fit.get("reduced_chi2")
        add("statistics", "not tested" if rc is None else ("pass" if rc <= 1.5 else "warning"),
            "the linear motion fit is consistent with its errors (χ²ν ≤ 1.5); larger values mean the errors or the model are inadequate (errors are inflated by √χ²ν)",
            f"χ²ν = {rc:.3f} over {fit.get('n_epochs')} visits" if rc is not None else "no fit", ["fit:motion"])
    else:
        add("statistics", "not tested", "the data-quality claim is a count; no statistical model is involved", "not applicable")
    fc("method", {"variability": ["M1", "M3"], "motion": ["M2", "M3", "M5"], "data_quality": ["M3"]}.get(question, []),
       "method preconditions and scope checks (SCI-COMP stage 5) pass for this claim's methods")
    fc("provenance", ["V1", "V2", "V3", "V4"], "record hash, file hashes, method versions and current file integrity check out")
    if question in ("variability", "motion"):
        base = o["category"]
        scen = ([{"variability_z": 3.0}, {"variability_z": 8.0}] if question == "variability" else [{"motion_detect_sigma": 3.0}, {"motion_detect_sigma": 8.0}])
        changes = []
        for th in scen:
            re = cf.reassess(record, thresholds=th).get(question, {})
            if re.get("category") != base:
                changes.append(f"{', '.join(f'{k} = {v}' for k, v in th.items())} → {re.get('category')}")
        add("sensitivity", "warning" if changes else "pass",
            "re-assessing the recorded inputs at a looser and a stricter threshold (3σ and 8σ; CF-1) leaves the category unchanged",
            ("category changes: " + "; ".join(changes)) if changes else f"category {base} at 3σ, 5σ and 8σ", [f"claim:{question}"])
    else:
        add("sensitivity", "not tested", "the data-quality claim has no significance threshold", "not applicable")
    alts = [a for a in ALTS.get(question, []) if a in hyp]
    if o["category"] in POSITIVE and alts:
        open_alts = [a for a in alts if hyp[a]["overall"] != "contradicted"]
        add("alternatives", "warning" if open_alts else "pass", "every artefact explanation HYPO-1 lists for a positive claim is contradicted by a test",
            ("not ruled out: " + ", ".join(f"{a} ({hyp[a]['overall']})" for a in open_alts)) if open_alts else "all contradicted", [f"hyp:{a}" for a in open_alts])
    else:
        add("alternatives", "not tested", "competing explanations are evaluated for positive claims", f"category {o['category']} is not a positive claim")
    words = epi.asserted_words(o.get("statement") or "", CAUSAL_WORDS)
    add("wording", "fail" if words else "pass", "the statement does not assert discovery, proof or causation (negated uses are not assertions)",
        f"asserts: {', '.join(words)}" if words else f"“{o.get('statement')}”", [f"claim:{question}"])
    if repro and repro.get("verdict") == "reproduced":
        add("reproducibility", "pass", "a re-execution gave the identical record hash (REPRO-1)", "reproduced", ["$.content_hash"])
    elif repro and repro.get("verdict") == "not reproducible as recorded":
        add("reproducibility", "fail", "a re-execution gave the identical record hash (REPRO-1)", "re-execution differed", ["$.content_hash"])
    else:
        add("reproducibility", "not tested", "a re-execution gave the identical record hash (REPRO-1)", "no re-execution of this run has been recorded; run Reproduce")
    if o["category"] in POSITIVE:
        if question == "variability":
            reps = next((t for t in hyp.get("V-INTRINSIC", {}).get("tests", []) if t["id"] == "T-REPEAT"), None)
            dets = (reps or {}).get("values", {}).get("detectors") or []
            add("sufficiency", "pass" if len(dets) >= 2 else "warning",
                "a positive brightness claim is sufficient when significant pairs occur on at least two detectors (independent wavelength channels)",
                f"significant pairs on {len(dets)} detector(s)", ["hyp:V-INTRINSIC"])
        else:
            fit = next(((e.get("data") or {}).get("fit") for e in record["events"] if e["step"] == "astrometry"), None) or {}
            add("sufficiency", "pass" if (fit.get("n_epochs") or 0) >= 3 else "warning",
                "a motion claim is sufficient when it rests on at least three visits (two visits cannot reveal a bad one)", f"{fit.get('n_epochs')} visits", ["fit:motion"])
    elif o["category"].startswith("no_"):
        add("sufficiency", "pass" if o.get("sensitivity") else "fail", "an absence claim is sufficient only as a bound: it must state its sensitivity",
            f"sensitivity stated: {', '.join(o.get('sensitivity') or {})}" if o.get("sensitivity") else "no sensitivity", [f"claim:{question}"])
    else:
        add("sufficiency", "inconclusive", "a limited or partial category is not a claim of change or absence", f"category {o['category']}")
    counts = {r: sum(x["result"] == r for x in R) for r in RESULTS}
    return {"method": METHOD_STRESS, "claim": f"claim:{question}", "statement": o.get("statement"), "category": o.get("category"), "modes": R, "counts": counts,
            "note": "A failed or warning mode shows where this claim is weak. It does not invalidate the investigation, and passing every mode does not make the claim true."}
