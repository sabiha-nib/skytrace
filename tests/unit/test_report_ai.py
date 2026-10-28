import json

import pytest

from skytrace.ai import copilot, guard, tools
from skytrace.ai.meta_client import MetaClient, MetaConfig, MetaUnavailable
from skytrace.provenance import synthetic
from skytrace.report import Investigation, render_markdown


def make_inv():
    inv = Investigation("Test Star", {"cutout_size_deg": 0.1})
    inv.log("astrometry", "ok", "measured pm", {"fit": {"pm_eta_mas_yr": 10351.7, "sig_eta": 42.0}, "nan": float("nan")},
            [synthetic("unit test")])
    inv.log("pairs", "rejected", "0 wavelength-matched pairs accepted of 3 considered")
    return inv


def test_report_is_deterministic_and_marks_synthetic():
    a, b = make_inv(), make_inv()
    b.created_at = "1999-01-01T00:00:00+00:00"
    assert a.to_dict()["content_hash"] == b.to_dict()["content_hash"]
    d = a.to_dict()
    assert d["events"][0]["data"]["nan"] is None  # NaN becomes an explicit null, never 0
    md = render_markdown(a)
    assert "SYNTHETIC DATA" in md and "Rejected or failed (1)" in md


def test_tools_validate_arguments():
    inv = make_inv().to_dict()
    out = tools.call_tool(inv, "get_events", '{"step": "astrometry"}')
    assert out["n_matching"] == 1
    with pytest.raises(tools.ToolError):
        tools.call_tool(inv, "get_events", '{"step": "astrometry", "path": "/etc/passwd"}')
    with pytest.raises(tools.ToolError):
        tools.call_tool(inv, "run_python", "{}")
    assert {t["function"]["name"] for t in tools.tool_specs()} == set(tools.TOOLS)


EVIDENCE = {"c1": {"events": [{"data": {"fit": {"pm_eta_mas_yr": 10351.7, "sig_eta": 42.0}}}]}}


def answer(text, claims=None, limitations=("Parallax not modelled.",)):
    return json.dumps({"answer": text, "claims": claims if claims is not None else
                       [{"text": "pm", "value": 10351.7, "unit": "mas/yr", "evidence": "c1"}],
                       "limitations": list(limitations)})


def test_guard_accepts_supported_answer_with_rounding():
    g = guard.check(answer("Measured northward motion is 10352 ± 42 mas/yr in D2."), EVIDENCE)
    assert g.ok, g.problems


def test_guard_rejects_invented_numbers_and_claims():
    g = guard.check(answer("The star moved 12000 mas/yr."), EVIDENCE)
    assert not g.ok and any("12000" in p for p in g.problems)
    g = guard.check(answer("ok", claims=[{"text": "x", "value": 5.0, "unit": "", "evidence": "c1"}]), EVIDENCE)
    assert not g.ok
    g = guard.check(answer("ok", claims=[{"text": "x", "value": 42.0, "unit": "", "evidence": "c9"}]), EVIDENCE)
    assert not g.ok and "not a tool call" in g.problems[0]


def test_guard_rejects_discovery_language_and_missing_limitations():
    assert not guard.check(answer("This is a confirmed discovery."), EVIDENCE).ok
    assert not guard.check(answer("Motion measured.", limitations=()), EVIDENCE).ok
    assert not guard.check("not json", EVIDENCE).ok


class FakeClient:
    """Scripted stand-in for the Meta API (no network)."""
    def __init__(self, replies):
        self.replies, self.cfg, self.sent = list(replies), MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3"), []

    def chat(self, messages, tools=None, response_format=None, temperature=0.0):
        self.sent.append(messages[:])
        return {"message": self.replies.pop(0), "usage": {}, "model": self.cfg.model}


def tool_call(cid, name, args):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_copilot_tool_loop_then_guarded_answer():
    inv = make_inv().to_dict()
    good = {"role": "assistant", "content": json.dumps({
        "answer": "The fitted northward proper motion is 10351.7 mas/yr with sigma 42.0 mas/yr.",
        "claims": [{"text": "pm", "value": 10351.7, "unit": "mas/yr", "evidence": "c1"}],
        "limitations": ["Synthetic test record."]})}
    r = copilot.ask("What was measured?", inv, FakeClient([tool_call("c1", "get_events", {"step": "astrometry"}), good]))
    assert r.ok and r.mode == "meta" and [a.kind for a in r.audit] == ["model", "tool", "model", "guard"]


def test_copilot_blocks_after_failed_repair():
    inv = make_inv().to_dict()
    bad = {"role": "assistant", "content": answer("It moves 99999 mas/yr.", claims=[])}
    r = copilot.ask("?", inv, FakeClient([tool_call("c1", "get_events", {"step": "astrometry"}), bad, bad]))
    assert not r.ok and r.answer is None and any("99999" in p for p in r.problems)


def test_copilot_tool_budget_enforced():
    inv = make_inv().to_dict()
    calls = [tool_call(f"c{i}", "get_investigation_summary", {}) for i in range(copilot.MAX_TOOL_CALLS + 2)]
    r = copilot.ask("?", inv, FakeClient(calls))
    assert not r.ok
    assert sum(1 for a in r.audit if a.kind == "tool" and "error" not in a.detail["output"]) == copilot.MAX_TOOL_CALLS


def test_local_mode_when_no_key(monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    r = copilot.ask("?", make_inv().to_dict())
    assert r.mode == "local" and "Deterministic summary" in r.answer["answer"] and "unavailable" in r.problems[0]


def test_client_refuses_contributor_and_offline(monkeypatch):
    monkeypatch.setenv("OFFLINE", "0")
    with pytest.raises(MetaUnavailable, match="contributor"):
        MetaClient(MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3-contributor"))
    monkeypatch.setenv("OFFLINE", "1")
    with pytest.raises(MetaUnavailable, match="OFFLINE"):
        MetaClient(MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3"))
