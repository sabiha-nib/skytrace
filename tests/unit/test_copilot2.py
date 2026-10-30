"""Copilot 2.0: the Phase 6 intents call only registered read-only tools, pass the evidence guard and execute nothing."""

import pytest

from skytrace import capabilities
from skytrace.ai import copilot, local, tools
from test_report_ai import view

QUESTIONS = {"draft": "Draft a notebook note for this investigation.",
             "plan": "How would I test whether the source changed in brightness?",
             "quality": "Are there any data quality problems?",
             "missing": "Which evidence is still missing?",
             "hypotheses": "Which explanations remain viable?"}
TOOL_FOR = {"plan": "plan_investigation", "quality": "get_data_quality", "missing": "get_evidence_ledger",
            "hypotheses": "get_hypothesis_tests"}


@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
@pytest.mark.parametrize("intent", list(QUESTIONS))
def test_phase6_intents_pass_the_guard(tid, intent, no_network):
    assert local._intent(QUESTIONS[intent]) == intent
    r = copilot.ask(QUESTIONS[intent], view(tid), tid)
    assert r.mode == "local" and r.ok, r.problems
    names = [c["name"] for c in r.tool_calls]
    assert set(names) <= set(tools.TOOLS)
    if intent in TOOL_FOR:
        assert TOOL_FOR[intent] in names
    assert r.answer["answer"].startswith("These are synthetic test data")


def test_plan_tool_executes_nothing_and_uses_registered_actions(no_network):
    v = view()
    s = tools.ToolSession(v, "syn-var-1")
    before = dict(v.r)
    c = tools.call_tool(s, "plan_investigation", {"question": "Is the apparent motion real?"})
    assert c.ok and c.output["method"] == "PLAN-1" and "nothing was executed" in c.output["note"]
    assert {st["action"] for st in c.output["steps"]} <= set(capabilities.ACTION_IDS)
    assert v.r == before


def test_quality_tool_has_no_score(no_network):
    s = tools.ToolSession(view(), "syn-var-1")
    o = tools.call_tool(s, "get_data_quality", {}).output
    assert not any("score" in k for k in o) and set(o["summary"]) <= {"valid", "invalid", "incompatible", "not_available", "not_checked"}
    # files are not re-hashed through the copilot: that check is reported as not checked, never as valid
    assert next(ch for ch in o["checks"] if ch["id"] == "DQ-FILES")["outcome"] == "not_checked"
