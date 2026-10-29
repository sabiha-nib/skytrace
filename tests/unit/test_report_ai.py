"""Report, tools, guard and copilot-loop tests. Investigations come from the SYNTHETIC fixture bundles."""

import json
from functools import lru_cache

import pytest

from skytrace import analysis, bundle as bmod
from skytrace.ai import copilot, guard, local, tools
from skytrace.ai.meta_client import MetaAPIError, MetaClient, MetaConfig, MetaUnavailable
from skytrace.provenance import synthetic
from skytrace.report import Investigation, render_markdown
from skytrace.view import InvestigationView, evidence_graph


@lru_cache(maxsize=None)
def _record(tid: str) -> str:
    return json.dumps(analysis.run(bmod.load(bmod.SYNTHETIC_ROOT / tid)).to_dict())


def view(tid="syn-var-1") -> InvestigationView:
    b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
    return InvestigationView(json.loads(_record(tid)), b.discovery, b.manifest, b.inspection)


# ------------------------------------------------------------------ report
def make_inv():
    inv = Investigation("Test Star", {"cutout_size_deg": 0.1})
    inv.log("astrometry", "ok", "measured pm", {"fit": {"pm_eta_mas_yr": 10351.7}, "nan": float("nan")}, [synthetic("unit test")])
    inv.log("pairs", "rejected", "0 wavelength-matched pairs accepted of 3 considered")
    return inv


def test_report_is_deterministic_and_marks_synthetic():
    a, b = make_inv(), make_inv()
    b.created_at = "1999-01-01T00:00:00+00:00"
    assert a.to_dict()["content_hash"] == b.to_dict()["content_hash"]
    assert a.to_dict()["events"][0]["data"]["nan"] is None
    md = render_markdown(a)
    assert "SYNTHETIC DATA" in md and "Rejected or failed (1)" in md


def test_full_analysis_is_reproducible():
    b = bmod.load(bmod.SYNTHETIC_ROOT / "syn-hpm-1")
    assert analysis.run(b).to_dict()["content_hash"] == json.loads(_record("syn-hpm-1"))["content_hash"]


# ------------------------------------------------------------------ tools
def test_tools_validate_and_record():
    s = tools.ToolSession(view(), "syn-var-1")
    ok = tools.call_tool(s, "list_target_observations", {"status": "measured_ok", "limit": 5})
    assert ok.ok and len(ok.output["rows"]) == 5 and ok.output["synthetic"] is True
    bad = [tools.call_tool(s, "get_source_measurements", {"key": "x" * 200}),
           tools.call_tool(s, "inspect_image_quality", {"key": "QR3:a:D1", "path": "/etc/passwd"}),
           tools.call_tool(s, "inspect_image_quality", {"key": "../../etc/passwd"}),
           tools.call_tool(s, "run_shell", {"cmd": "ls"}),
           tools.call_tool(s, "list_target_observations", {"limit": 10_000})]
    assert not any(c.ok for c in bad) and all("error" in c.output for c in bad)
    assert len(s.calls) == 6 and set(s.outputs()) == {ok.id}
    assert {t["function"]["name"] for t in tools.tool_specs()} == set(tools.TOOLS) and len(tools.TOOLS) == 11


def test_compare_refuses_flux_for_incompatible_pair():
    v = view()
    keys = list(v.measurements)
    s = tools.ToolSession(v, "syn-var-1")
    d1 = [k for k in keys if k.endswith(":D1")]
    out = tools.call_tool(s, "compare_observation_epochs", {"key_a": d1[0], "key_b": d1[2]}).output
    assert out["compatible_for_photometry"] is False and out["flux"] is None and "not valid" in out["flux_note"]
    acc = v.accepted_pairs()[0]
    out = tools.call_tool(s, "compare_observation_epochs", {"key_a": acc["a"], "key_b": acc["b"]}).output
    assert out["compatible_for_photometry"] is True and out["flux"]["z"] is not None


def test_evidence_graph_only_has_recorded_nodes():
    v = view()
    g = evidence_graph(v, "syn-var-1")
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    included = {o["key"] for o in v.observations() if o.get("included")}
    assert {n["label"] for n in g["nodes"] if n["kind"] == "observation"} == included
    assert g["counts"]["claim"] == 3 and g["counts"]["comparison"] == len(v.accepted_pairs())


# ------------------------------------------------------------------ guard
EV = {"c1": {"fit": {"pm_eta_mas_yr": 10351.7, "sig_eta": 42.0}, "t_mid_iso": "2025-06-03T00:00:00+00:00",
             "wavelength_um": 1.3125, "catalogue": {"source": "Gaia DR3"}, "synthetic": False}}
ORIG = ["live"]


def ans(text, claims=None, limitations=("Parallax not modelled.",)):
    return json.dumps({"answer": text, "claims": claims if claims is not None else
                       [{"text": "pm", "kind": "measurement", "value": 10351.7, "unit": "mas/yr", "evidence": ["c1"]}],
                       "limitations": list(limitations)})


def codes(text, **kw):
    return {p["code"] for p in guard.check(ans(text, **kw), EV, {"get_astrometric_validation"}, ORIG).problems}


def test_guard_accepts_grounded_answer():
    assert codes("The northward motion is 10352 ± 42 mas/yr, measured on 2025-06-03 at 1.31 µm, compared with Gaia DR3.") == set()


@pytest.mark.parametrize("text,code", [
    ("The star moved 12000 mas/yr.", "number"),
    ("It was observed on 2025-07-14.", "date"),
    ("The measurement at 2.4 µm shows it.", "wavelength"),
    ("I ran inspect_image_quality and it looked fine.", "tool"),
    ("The flux dropped because of a dust cloud passing in front.", "causal"),
    ("JWST data agree with this.", "attribution"),
    ("This is a new discovery.", "certainty"),
    ("This proves the star is variable.", "certainty"),
    ("There is a 99% probability that the star is variable.", "number"),
])
def test_guard_blocks(text, code):
    assert code in codes(text)


def test_guard_allows_discussing_discovery_and_hedged_causes():
    assert codes("Could this be a discovery? Not from this evidence: it is a candidate that would need independent confirmation.") == set()
    assert codes("The difference could be caused by a calibration drift; that has not been tested.") == set()


def test_guard_probability_and_limitations_and_citations():
    assert "probability" in codes("The probability that the star is variable is high.")
    assert "limitations" in codes("Measured 10352 mas/yr.", limitations=())
    assert "citation" in codes("ok", claims=[{"text": "x", "value": 5.0, "evidence": ["c1"]}])
    assert "citation" in codes("ok", claims=[{"text": "x", "value": 42.0, "evidence": ["c9"]}])
    assert "structure" in {p["code"] for p in guard.check("not json", EV).problems}


def test_guard_synthetic_rules():
    syn = ["synthetic"]
    g = guard.check(ans("Measured 10352 mas/yr."), EV, set(), syn)
    assert "synthetic" in {p["code"] for p in g.problems}
    g = guard.check(ans("These synthetic real observations show 10352 mas/yr."), EV, set(), syn)
    assert any("as real" in p["detail"] for p in g.problems)
    assert guard.check(ans("In these synthetic test data, not real observations, the motion is 10352 mas/yr."), EV, set(), syn).ok


# ------------------------------------------------------------------ copilot loop
class FakeClient:
    """Scripted stand-in for the Meta API (no network)."""

    def __init__(self, replies):
        self.replies, self.cfg, self.sent = list(replies), MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3"), []

    def chat(self, messages, tools=None, response_format=None, temperature=0.0):
        self.sent.append(messages[:])
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return {"message": r, "usage": {"total_tokens": 1}, "model": self.cfg.model, "id": "x", "finish_reason": "stop"}


def tool_call(cid, name, args):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def final(text, value, ev="c1"):
    return {"role": "assistant", "content": json.dumps({
        "answer": text, "claims": [{"text": "x", "kind": "measurement", "value": value, "unit": "", "evidence": [ev]}],
        "limitations": ["Synthetic test record."]})}


def test_copilot_meta_mode_with_tools_and_guard():
    v = view()
    z = max(abs(p["z"]) for p in v.flux_pairs())
    rep = final(f"In these synthetic data the largest matched-pair significance is {z:.1f}; this is a candidate, not a discovery.",
                round(z, 1))
    r = copilot.ask("What changed?", v, "syn-var-1",
                    client=FakeClient([tool_call("c1", "generate_investigation_summary", {}),
                                       tool_call("c2", "get_evidence_graph", {}), rep]))
    # the summary output contains max_abs_z, so the claim is evidenced by c1
    assert r.mode == "meta" and r.ok, r.problems
    assert [c["name"] for c in r.tool_calls] == ["generate_investigation_summary", "get_evidence_graph"]


def test_copilot_withholds_unsupported_answer_and_falls_back():
    v = view()
    bad = final("In these synthetic data the star brightened by 777 percent.", None)
    r = copilot.ask("What changed?", v, "syn-var-1",
                    client=FakeClient([tool_call("c1", "generate_investigation_summary", {}), bad, bad]))
    assert r.mode == "local" and r.ok and len(r.withheld) == 2
    assert any("777" in p["detail"] for p in r.withheld[0]["problems"])
    assert "withheld" in r.problems[0] and "777" not in r.answer["answer"]


def test_copilot_budget_and_api_error():
    v = view()
    many = [tool_call(f"c{i}", "get_analysis_provenance", {}) for i in range(copilot.MAX_TOOL_CALLS + 3)]
    r = copilot.ask("?", v, "syn-var-1", client=FakeClient(many))
    executed = [c for c in r.tool_calls if c["name"] == "get_analysis_provenance"]
    assert len(executed) == copilot.MAX_TOOL_CALLS and r.mode == "local"
    r = copilot.ask("?", v, "syn-var-1", client=FakeClient([MetaAPIError(429, '{"error":{"type":"rate_limit","message":"slow down"}}')]))
    assert r.mode == "local" and "rate_limit" in r.problems[0]


def test_no_key_uses_labelled_local_mode(monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    r = copilot.ask("What changed?", view(), "syn-var-1")
    assert r.mode == "local" and r.ok and "local deterministic assistant" in r.problems[0]
    assert any("without a language model" in l for l in r.answer["limitations"])


QUESTIONS = ["What changed between these observations?", "Which observations support this conclusion?",
             "Could the apparent motion be caused by alignment errors?", "Are these two observations measured at compatible wavelengths?",
             "Why was an observation excluded?", "How does the result compare with the Gaia reference?",
             "What is the largest remaining uncertainty?", "What should I investigate next?"]


@pytest.mark.parametrize("tid", ["syn-var-1", "syn-hpm-1"])
@pytest.mark.parametrize("q", QUESTIONS)
def test_local_answers_pass_guard(tid, q):
    s = tools.ToolSession(view(tid), tid)
    a = local.answer(q, s)
    g = guard.check(json.dumps(a), s.outputs(), s.executed_names(), s.view.data_origins())
    assert g.ok, (a["answer"], g.problems)
    assert "synthetic" in a["answer"].lower()


def test_client_refuses_contributor_and_offline(monkeypatch):
    monkeypatch.setenv("OFFLINE", "0")
    with pytest.raises(MetaUnavailable, match="contributor"):
        MetaClient(MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3-contributor"))
    monkeypatch.setenv("OFFLINE", "1")
    with pytest.raises(MetaUnavailable, match="OFFLINE"):
        MetaClient(MetaConfig("https://api.meta.ai/v1", "k", "muse-spark-1.3"))


def test_api_error_envelope_parsed():
    e = MetaAPIError(400, '{"error": {"message": "bad model", "type": "invalid_request_error", "param": "model", "code": null}}')
    assert e.type == "invalid_request_error" and "bad model" in str(e)
