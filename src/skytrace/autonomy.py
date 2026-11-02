"""CYCLE-1: the research cycle of bounded autonomy — which registered actions answer which open item, under stated rules.

The cycle inspects the intelligence report, lists what is unanswered, and proposes registered actions (capabilities.ACTIONS)
only. Rules, in this order (each proposal names its rule, the open item it addresses and the action's permission class):

  A1 the integrity gate's 'Reproducible' requirement is not met          → reproduce_independent (REPROX-1)
  A2 a sensitivity-fingerprint dimension 'preprocessing' is not tested   → run_stability (STAB-1)
  A3 a major or critical challenge is open in the ledger                 → challenge_interpretation (ASL-1), then your judgement
  A4 a competing explanation has never been tested (unknown map U4)      → evaluate_hypotheses (HYPO-1)
  A5 the uncertainty budget lists unquantified effects                  → decompose_uncertainty (UNC-1)
  A6 always, as the first step                                           → check_quality (DQ-1)

Further proposals — counterfactual scenarios (WHATIF-1) and hypothetical observation plans (ORACLE-1) — are listed for you to
decide on; the cycle never executes them. Execution is governed by the autonomy level (capabilities.AUTONOMY_LEVELS): advisory
executes nothing, supervised executes each step you approve, restricted automation executes the predefined workflow after one
authorization. Nothing in the cycle alters source data, publishes anything or marks an interpretation as established.
"""

from __future__ import annotations

from . import capabilities

METHOD = "CYCLE-1"
RULES = {"A1": "the integrity gate's 'Reproducible' requirement is not met", "A2": "the fingerprint dimension 'preprocessing' is not tested",
         "A3": "a major or critical challenge is open", "A4": "a competing explanation has never been tested",
         "A5": "the uncertainty budget lists unquantified effects", "A6": "always: start from the data-quality checks"}
PERM = {a["id"]: a["permission"] for a in capabilities.ACTIONS}
TITLE = {a["id"]: a["title"] for a in capabilities.ACTIONS}


def propose(intel: dict, unknown: dict | None = None) -> dict:
    out = []

    def add(rule, action, why, addresses):
        out.append({"id": f"{rule}:{action}", "rule": rule, "rule_text": RULES[rule], "action": action, "title": TITLE[action], "permission": PERM[action],
                    "why": why, "addresses": addresses[:10]})
    add("A6", "check_quality", "every conclusion rests on the usable exposures", ["claim:data_quality"])
    g3 = next((r for r in intel["gate"]["requirements"] if r["id"] == "G3"), None)
    if g3 and g3["state"] != "met":
        add("A1", "reproduce_independent", g3["detail"], ["GATE-1:G3"])
    nt = [f"{q['question']}:F4" for q in intel["fingerprint"]["questions"] for d in q["dimensions"] if d["id"] == "F4" and d["state"] == "not tested"]
    if nt:
        add("A2", "run_stability", "conclusions not yet re-run under small parameter changes", nt)
    major = [i["id"] for c in intel["adversary"]["conclusions"] for q in c["questions"] for i in q["items"] if i["severity"] in ("major", "critical") and i["status"] == "open"]
    if major:
        add("A3", "challenge_interpretation", f"{len(major)} major or critical challenge(s) open", major)
    untested = [i["id"] for r in (unknown or {}).get("regions", []) if r["id"] == "unresolved" for i in r["items"] if i["basis"] == "HYPO-1 overall 'untested'"]
    if untested:
        add("A4", "evaluate_hypotheses", f"{len(untested)} explanation(s) never tested", untested)
    if intel["budget"]["counts"]["unquantified"]:
        add("A5", "decompose_uncertainty", f"{intel['budget']['counts']['unquantified']} effect(s) without a number", ["BUDGET-1:unquantified"])
    later = [{"kind": "counterfactual scenario", "what": q["question"], "spec": q.get("scenario")} for q in intel["whatif"]["questions"] if q.get("scenario")]
    later += [{"kind": "hypothetical observation plan", "what": f"{qq}: {p['ranking'][0]} ranks first" if p and p.get("ranking") else qq, "spec": None}
              for qq, p in intel["oracle"]["examples"].items() if p and p.get("available")]
    return {"method": METHOD, "rules": RULES, "proposals": out, "for_you_to_decide": later, "levels": capabilities.AUTONOMY_LEVELS,
            "restricted_workflow": capabilities.RESTRICTED_WORKFLOW, "workflow_permissions": {a: PERM[a] for a in capabilities.RESTRICTED_WORKFLOW},
            "note": "Proposals are registered actions chosen by stated rules. The cycle never alters data, publishes, or marks an interpretation as established."}
