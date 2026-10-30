"""Scientific Possibility Engine (SPE-1) and Discovery Horizon (HORIZON-1).

SPE-1 lays an investigation out in six inspectable layers, each computed from recorded values by an existing,
versioned method — it adds no measurement and no probability:

  1 knowledge inventory        DISC-1 inventory: every evidence item, its origin and checksum, unknown fields counted
  2 question space             DISC-1 questions: answerable / answerable with limits / not answerable, and why
  3 investigation design       for each askable question: method, required and missing inputs, PLAN-1 actions
  4 computational experiments  what can be executed here: CF-1 scenario kinds, EXP-1 templates, SYNOBS-1 templates,
                               and what this session has already executed
  5 evidence evaluation        LEDGER-1 support and contradictions, HYPO-1 statuses, UNC-1 unquantified effects,
                               ASL-1 challenge counts
  6 research opportunities     Discovery Horizon cards (below)

HORIZON-1 turns the layers into research opportunities — work that remains possible with the evidence available — and
never into findings. Every card states: the research question, the evidence that prompted it, the data it requires
and the data available, the proposed method, its limitations, its feasibility, the expected output, and why it is
ranked where it is. Ranking (stated, not computed): feasibility (can run now > needs the server > needs new data >
needs a new method), then the category order below. Categories come only from rules over the recorded state:

  C1 unexamined significant pairs     RADAR-1 R1 items whose pair is not in the session's examined list
  C2 unsupported or conflicting       LEDGER-1 flags and contradictions (RADAR-1 R6)
  C3 incomplete candidate assessment  ASL-1 hypothesis challenges (H1) on a positive claim
  C4 unresolved hypotheses            INFO-1 candidate tests
  C5 unexplored parameter space       no STAB-1 result or no CF-1 scenario in the session
  C6 unexplored compatible epochs     SEQ-1 sequences of ≥ 3 frames not opened in the session
  C7 unvalidated assumptions          ASL-1 method challenges (M)
  C8 missing calibration metadata     DQ-CAL not valid
  C9 unused measurements              RADAR-1 R4
  C10 incomplete provenance           replay not run (REPRO-1 R9) or LEDGER-1 unexpected gaps
"""

from __future__ import annotations

from . import counterfactual, experiments, planner, synthobs

METHOD = "SPE-1"
HORIZON = "HORIZON-1"
CATS = {"C1": "Unexamined significant pairs", "C2": "Unsupported or conflicting evidence", "C3": "Incomplete candidate assessment",
        "C4": "Unresolved hypotheses", "C5": "Unexplored parameter space", "C6": "Unexplored compatible epochs",
        "C7": "Unvalidated analytical assumptions", "C8": "Missing calibration metadata", "C9": "Unused measurements",
        "C10": "Incomplete provenance"}
FEAS = ["can run now", "needs the server", "needs new data", "needs a new method"]


def _card(cid, cat, question, prompted, required, available, method, limits, feas, expected, refs=None):
    assert cat in CATS and feas in FEAS
    return {"id": cid, "category": cat, "category_name": CATS[cat], "question": question, "prompted_by": prompted,
            "required_data": required, "available_data": available, "method": method, "limitations": limits,
            "feasibility": feas, "expected_output": expected, "refs": refs or []}


def horizon(disc: dict, research: dict, info: dict, asl: dict, session: dict | None, server: bool, has_stability: bool) -> dict:
    s = session or {}
    examined = set(s.get("examined", []))
    seq_viewed = {h.get("ref") for h in s.get("history", []) if h.get("kind") == "sequence.view"}
    runnable = "can run now" if server else "needs the server"
    cards = []
    for ix, it in enumerate(research["radar"]["items"], 1):
        if it["signal"] == "R1":
            key = "|".join(it.get("refs", [])[:2])
            if key and key not in examined:
                cards.append(_card(f"H-R1-{ix:02d}", "C1", f"Is the difference in {key.replace('|', ' → ')} visible and free of artefacts?",
                                   [it["why"]] + it["evidence"][:2], ["the two images", "their registration"], ["both images (bundle)"],
                                   "inspect_pair (Time Machine)", [it["cannot_establish"]], "can run now",
                                   "your recorded judgement on the pair (needs-review step)", it.get("refs")))
        elif it["signal"] == "R6":
            cards.append(_card(f"H-R6-{ix:02d}", "C2", f"Which of the conflicting results should the claim rest on? ({it['proposal']})",
                               [it["why"]], it["data_needed"] if isinstance(it["data_needed"], list) else [it["data_needed"]],
                               ["the recorded values (present)"], "inspect_ledger · CF-1 method scenario", [it["cannot_establish"]],
                               "can run now", "the dependence of the claim on the conflicting choice", it.get("refs")))
        elif it["signal"] == "R4":
            cards.append(_card("H-R4", "C9", "Can the measurements without a wavelength-matched partner contribute?", [it["why"]],
                               ["a partner at the same detector position and release"], [it["proposal"]], "acquire_data → compare_pair",
                               [it["cannot_establish"]], "needs new data", "new matched pairs (after new observations)", it.get("refs")))
    for c in asl["challenges"]:
        if c["mode"] == "H" and c["id"].startswith("H-") and c["severity"] in ("major", "moderate") and c["status"] == "open":
            cards.append(_card(f"H-{c['id']}", "C3", f"Can {c['id'][2:]} be ruled out for the {c['question']} claim?", [c["issue"]] + c["evidence"][:3],
                               ["the open tests' inputs"], c["evidence"][:2], c["verification"], [c["why"]],
                               "needs new data" if "needs" not in c["verification"] else "needs a new method",
                               "a contradicted or consistent status for the competing explanation"))
        if c["mode"] == "M":
            cards.append(_card(f"H-{c['id']}", "C7", f"Does the result hold if this assumption fails? ({c['issue']})", c["evidence"][:3],
                               ["the recorded values"], c["evidence"][:2], c["verification"], [c["why"]], runnable,
                               "a CF-1 comparison showing whether outcomes change"))
    for t in info["candidates"][:6]:
        feas = {"can run now": runnable, "needs new data": "needs new data", "needs a new method": "needs a new method"}[t["feasibility"]]
        cards.append(_card(f"H-{t['test']}", "C4", f"What would {t['test']} ({t['description']}) say about {', '.join(t['bears_on'])}?",
                           [f"INFO-1 rank {t['rank']}: {t['why']}"], [t["route"]], [f"test status: {t['status']}"], t["rule"],
                           [info["interpretation_limits"]], feas, f"a decided status for {', '.join(t['bears_on'])}"))
    scen = s.get("scenarios") or []
    if not has_stability or not scen:
        cards.append(_card("H-PARAMS", "C5", "Do the outcomes depend on analysis choices or thresholds?",
                           (["no STAB-1 result for this run"] if not has_stability else []) + (["no CF-1 scenario in this session"] if not scen else []),
                           ["the bundle (re-run) or the record (re-assessment)"], ["the record and bundle"],
                           "run_stability · CF-1 parameter/threshold/error-scale scenarios", ["only the stated changes are examined"],
                           runnable if not has_stability else "can run now", "which outcomes change under which stated change"))
    for sq in research["compat"].get("sequences", []):
        if sq["n_frames"] >= 3 and sq["id"] not in seq_viewed:
            cards.append(_card(f"H-{sq['id']}", "C6", f"What does the compatible sequence {sq['id']} ({sq['n_frames']} frames, {sq['n_visits']} visits) show?",
                               [f"SEQ-1 {sq['id']}: every pair wavelength-matched"], ["the frames"], [f"{sq['n_frames']} recorded frames"],
                               "Time Machine → sequence playback", ["recorded frames only; never interpolated"], "can run now",
                               "your inspection of the sequence (logged in the session)", sq["members"][:4]))
    dq = {c["id"]: c for c in research["quality"]["checks"]}
    if dq.get("DQ-CAL", {}).get("outcome") != "valid":
        cards.append(_card("H-CAL", "C8", "Which pairs lack the calibration information PAIRDIFF-2 needs, and does it matter?",
                           [f"DQ-CAL: {dq.get('DQ-CAL', {}).get('outcome')}"], ["≥ 3 matched reference stars per pair"],
                           [str(dq.get("DQ-CAL", {}).get("counts"))], "inspect_ledger · CF-1 method scenario",
                           ["uncalibrated pairs cannot separate calibration changes from brightness changes"], runnable,
                           "the outcome with and without the uncalibrated pairs"))
    gaps = [g for g in research["ledger"]["completeness"].get("gaps", []) if not g.get("expected")]
    if gaps or any(c["id"] == "R-REPLAY" and c["status"] == "open" for c in asl["challenges"]):
        cards.append(_card("H-PROV", "C10", "Can this result be reproduced from its recorded inputs?",
                           (["replay not run"] if any(c["id"] == "R-REPLAY" and c["status"] == "open" for c in asl["challenges"]) else [])
                           + [f"{len(gaps)} unexpected provenance gap(s)"], ["the bundle and the server"], ["the record"],
                           "Reproducibility Challenge (REPRO-1)", ["exact hash equality; does not validate the method itself"],
                           runnable, "an audit verdict with every check"))
    order = list(CATS)
    cards.sort(key=lambda c: (FEAS.index(c["feasibility"]), order.index(c["category"]), c["id"]))
    for i, c in enumerate(cards, 1):
        c["rank"] = i
        c["priority_reason"] = f"{c['feasibility']}; category {c['category']} ({CATS[c['category']]}) is position {order.index(c['category']) + 1} of {len(order)} in the stated order"
    # opportunity map: only nodes and edges present in the cards
    nodes, edges = {}, []
    for c in cards:
        nodes[c["id"]] = {"id": c["id"], "kind": "question", "label": c["question"][:90]}
        m = "method:" + c["method"][:60]
        nodes.setdefault(m, {"id": m, "kind": "method", "label": c["method"][:60]})
        edges.append({"s": c["id"], "t": m, "rel": "tested by"})
        for p in c["prompted_by"][:2]:
            e = "evidence:" + str(p)[:60]
            nodes.setdefault(e, {"id": e, "kind": "evidence", "label": str(p)[:60]})
            edges.append({"s": e, "t": c["id"], "rel": "prompted"})
        for r in c["required_data"][:1]:
            rq = "requires:" + str(r)[:60]
            nodes.setdefault(rq, {"id": rq, "kind": "required evidence", "label": str(r)[:60]})
            edges.append({"s": c["id"], "t": rq, "rel": "needs"})
    return {"method": HORIZON, "cards": cards, "counts": {k: sum(c["category"] == k for c in cards) for k in CATS},
            "by_feasibility": {f: sum(c["feasibility"] == f for c in cards) for f in FEAS},
            "map": {"nodes": list(nodes.values()), "edges": edges}, "categories": CATS,
            "ranking_rule": "feasibility, then the stated category order C1–C10; not a value judgement or a probability",
            "note": "Research opportunities: work that remains possible with the recorded evidence. None is a finding."}


def layers(record: dict, disc: dict, research: dict, info: dict, asl: dict, session: dict | None, server: bool,
           has_stability: bool, facts: dict | None = None) -> dict:
    s = session or {}
    inv = disc["inventory"]
    qs = disc["questions"]
    f = facts or {"has_target_data": True, "has_run": True, "run_hash": record.get("content_hash"), "server": server, "static": not server,
                  "network": False, "targets": []}
    design = []
    for q in qs:
        if q["status"] == "not answerable":
            continue
        p = planner.plan(q["text"], f)
        design.append({"question": q["id"], "text": q["text"], "status": q["status"], "method": q["plan"]["method"],
                       "required_inputs": q["plan"]["required_inputs"], "missing_inputs": q["plan"]["missing_inputs"],
                       "plan_intent": p["intent"]["kind"], "actions": [{"action": st["action"], "status": st["status"]} for st in p["steps"]]})
    ledger = research["ledger"]
    hyp = disc["hypotheses"]
    hz = horizon(disc, research, info, asl, s, server, has_stability)
    return {"method": METHOD, "content_hash": record.get("content_hash"), "synthetic": disc.get("synthetic"),
            "layers": [
                {"n": 1, "name": "Knowledge inventory", "method": "DISC-1 stage A", "summary": inv["summary"]},
                {"n": 2, "name": "Scientific question space", "method": "DISC-1 stage B",
                 "summary": {st: sum(q["status"] == st for q in qs) for st in ("answerable", "answerable with limits", "not answerable")},
                 "items": [{"id": q["id"], "text": q["text"], "status": q["status"], "why_not": q.get("why_not"),
                            "current": (q.get("current_answer") or {}).get("category")} for q in qs]},
                {"n": 3, "name": "Investigation design", "method": "DISC-1 plans + PLAN-1", "items": design},
                {"n": 4, "name": "Computational experimentation", "method": "CF-1 · EXP-1 · SYNOBS-1",
                 "summary": {"counterfactual_kinds": list(counterfactual.KINDS), "experiment_templates": list(experiments.TEMPLATES),
                             "synthetic_templates": [t["id"] for t in synthobs.TEMPLATES],
                             "executed_in_session": {"experiments": len(s.get("experiments", [])), "scenarios": len(s.get("scenarios") or []),
                                                     "plans": len(s.get("plans", []))},
                             "where": "server: all; static preview: the recorded set"}},
                {"n": 5, "name": "Evidence evaluation", "method": "LEDGER-1 · HYPO-1 · UNC-1 · ASL-1",
                 "summary": {"claims": [{"id": c["id"], "category": c["category"], "direct": c["support"]["direct"], "flags": len(c["flags"])}
                                        for c in ledger["claims"]],
                             "contradictions": len(ledger["contradictions"]),
                             "hypotheses": {h["id"]: h["overall"] for q in hyp["questions"] for h in q["hypotheses"]},
                             "unquantified_effects": len(disc["uncertainty"].get("unquantified", [])), "challenges": asl["counts"]}},
                {"n": 6, "name": "Research opportunities", "method": HORIZON, "summary": {"cards": len(hz["cards"]), **hz["by_feasibility"]}}],
            "horizon": hz,
            "note": "Every layer is computed from recorded values by a named method. The engine identifies opportunities for "
                    "investigation; it does not produce findings."}
