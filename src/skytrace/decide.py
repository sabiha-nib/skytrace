"""Research decision support (NEXTX-1) and research question discovery (QFORGE-1).

NEXTX-1 turns the open items of an investigation into a transparent decision record. Candidates come from the knowledge
boundary (what keeps a claim unresolved), the open hypothesis tests (INFO-1), the claim stress tests (modes not tested)
and the compiler's review flags. They are ordered by one stated rule (ORDER_RULE). Each recommendation states the action,
the reasoning, the evidence used, the inputs it needs, its limitations and why the items below it were not placed higher.
No cost is used (none is recorded) and no ordering is claimed to be optimal.

QFORGE-1 lists research questions that arise from this investigation's evidence and gaps, each placed in one of
CATEGORIES with the evidence that prompted it, the motivation, the available and missing inputs, a possible method, the
expected output and its limitations. Every question cites the record item it came from.
"""

from __future__ import annotations

METHOD_NEXT = "NEXTX-1"
METHOD_Q = "QFORGE-1"
FEAS = ["can run now", "needs the server", "needs new data", "needs a new method"]
ORDER_RULE = ("1) items that bear on an unresolved claim before others; 2) feasibility (can run now → needs the server → needs new data → "
              "needs a new method); 3) more viable explanations addressed before fewer; 4) identifier, for a stable order")
CATEGORIES = ["directly answerable", "partially answerable", "testable with current inputs", "requires additional data", "requires a new method",
              "hypothetical", "outside current capabilities"]


def next_steps(boundary: dict, info: dict, stresses: dict, compiled: dict, server: bool = True) -> dict:
    unresolved = {i["id"] for i in boundary["items"] if i["region"] == "unresolved"}
    C = []
    for c in info.get("candidates", []):
        claim = f"claim:{c.get('question')}"
        C.append({"id": f"NX-T-{c['test']}", "action": f"Evaluate test {c['test']}: {c.get('description', '')}", "kind": "hypothesis test",
                  "claim": claim, "feasibility": c.get("feasibility"), "addresses": len(c.get("bears_on") or []),
                  "reasoning": f"bears on {', '.join(c.get('bears_on') or []) or 'no viable explanation'}; status {', '.join(c.get('statuses') or [])}",
                  "evidence": [f"HYPO-1 {b}" for b in (c.get("bears_on") or [])][:6], "inputs": c.get("route") or "", "limitations": c.get("limitation") or
                  "a test result changes a rule status; it does not establish a cause"})
    for q, s in stresses.items():
        for m in s.get("modes", []):
            if m["mode"] == "reproducibility" and m["result"] == "not tested":
                C.append({"id": f"NX-R-{q}", "action": "Re-execute the run and compare (Reproduce)", "kind": "reproduction", "claim": f"claim:{q}",
                          "feasibility": "can run now" if server else "needs the server", "addresses": 0,
                          "reasoning": "the claim's reproducibility mode is not tested", "evidence": ["CLAIMX-1 reproducibility"], "inputs": "the run's bundle and parameters",
                          "limitations": "an identical re-execution shows determinism here, not correctness"})
                break
    for chk in compiled["checks"]:
        if chk.get("review"):
            C.append({"id": f"NX-C-{chk['id']}", "action": f"Review: {chk['rule']}", "kind": "scientific review",
                      "claim": next((x for x in chk.get("cites", []) if x.startswith("claim:")), "claim:variability" if chk["id"] in ("E3",) or chk["id"].endswith("variability") else "claim:motion"),
                      "feasibility": "can run now", "addresses": len(chk.get("cites", [])), "reasoning": chk["detail"], "evidence": chk.get("cites", [])[:6],
                      "inputs": "your judgement, recorded as a note", "limitations": "review records a judgement; it does not change the recorded values"})
    seen, uniq = set(), []
    for c in C:
        if c["id"] not in seen:
            seen.add(c["id"])
            uniq.append(c)
    key = lambda c: (0 if c["claim"] in unresolved else 1, FEAS.index(c["feasibility"]) if c["feasibility"] in FEAS else len(FEAS), -c["addresses"], c["id"])  # noqa: E731
    uniq.sort(key=key)
    for i, c in enumerate(uniq):
        c["rank"] = i + 1
        c["ranking_reason"] = (("bears on the unresolved " + c["claim"]) if c["claim"] in unresolved else "does not bear on an unresolved claim") + f"; {c['feasibility']}; addresses {c['addresses']}"
        if i > 0:
            p = uniq[i - 1]
            kp, kc = key(p), key(c)
            crit = next(j for j in range(4) if kp[j] != kc[j]) if kp != kc else 3
            c["why_not_higher"] = ["the item above bears on an unresolved claim and this one does not",
                                   f"the item above is more feasible ({p['feasibility']} vs {c['feasibility']})",
                                   f"the item above addresses more viable explanations ({p['addresses']} vs {c['addresses']})",
                                   "same position on every criterion; ordered by identifier"][crit]
    return {"method": METHOD_NEXT, "order_rule": ORDER_RULE, "recommendations": uniq,
            "note": "A decision record, not an optimisation: no objective function is defined and no cost data exists. The order follows the stated rule only."}


def questions(disc: dict, boundary: dict, future: dict) -> dict:
    Q = []
    st_map = {"answerable": "directly answerable", "answerable with limits": "partially answerable"}
    for q in disc.get("questions", []):
        plan = q.get("plan") or {}
        miss = [m.get("input") if isinstance(m, dict) else str(m) for m in plan.get("missing_inputs", [])]
        cat = st_map.get(q["status"]) or ("requires additional data" if miss else "outside current capabilities")
        Q.append({"id": f"QF-{q['id']}", "category": cat, "question": q["text"], "prompted_by": f"DISC-1 {q['id']} ({q['status']})",
                  "motivation": q.get("why_not") or "part of the investigation's scope", "available": [r.get("input") for r in plan.get("required_inputs", []) if r.get("available")],
                  "missing": miss, "method": plan.get("method") or "—", "expected": ", ".join(plan.get("expected_outputs") or []) or "—",
                  "limitations": plan.get("assumptions") or []})
    for h in [h for q in (disc.get("hypotheses") or {}).get("questions", []) for h in q.get("hypotheses", [])]:
        for t in h.get("tests", []):
            if t["status"] in ("not_tested", "evidence_unavailable"):
                needs_method = t["status"] == "not_tested" and ("method" in (t.get("detail") or "").lower() or "not implemented" in (t.get("detail") or "").lower())
                cat = "requires a new method" if needs_method else ("requires additional data" if t["status"] == "evidence_unavailable" else "testable with current inputs")
                Q.append({"id": f"QF-{h['id']}-{t['id']}", "category": cat, "question": f"Does {t['description'].lower()}?",
                          "prompted_by": f"HYPO-1 {h['id']} test {t['id']} ({t['status'].replace('_', ' ')})", "motivation": f"would test the explanation: {h['statement']}",
                          "available": [], "missing": [t.get("detail", "")[:160]] if t["status"] == "evidence_unavailable" else [], "method": t["rule"],
                          "expected": "a rule status for the test (consistent / contradicted / inconclusive)", "limitations": ["a test status is not a probability"]})
    for i in boundary["items"]:
        if i["region"] == "unresolved":
            Q.append({"id": f"QF-B-{i['id']}", "category": "partially answerable", "question": f"What would move “{(i['statement'] or '')[:100]}” out of the unresolved region?",
                      "prompted_by": f"KBOUND-1 {i['id']} ({i['rule']})", "motivation": i["why"], "available": list(i.get("evidence", {}).keys())[:6],
                      "missing": [f"{t.get('test')}: {t.get('rule')}" for t in i.get("could_change_it", []) if t.get("test")][:4],
                      "method": "the open tests listed", "expected": "a change of region, or a stated reason it cannot change", "limitations": i.get("limitations", [])[:3]})
    for s in future.get("scenarios", []):
        if s["id"] in ("baseline", "precision"):
            Q.append({"id": f"QF-F-{s['id']}", "category": "hypothetical", "question": s["title"], "prompted_by": f"FUTURE-1 {s['id']}",
                      "motivation": "planning future measurements", "available": ["recorded errors and baseline"], "missing": ["the hypothetical measurements"],
                      "method": "validated sensitivity formula (FUTURE-1)", "expected": "a sensitivity under stated assumptions", "limitations": s.get("assumptions", [])})
    counts = {c: sum(q["category"] == c for q in Q) for c in CATEGORIES}
    return {"method": METHOD_Q, "categories": CATEGORIES, "questions": Q, "counts": counts,
            "note": "Every question cites the record item that prompted it; none is generic."}
