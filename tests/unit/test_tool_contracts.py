"""TOOLS-2 contract: every tool returns the same envelope, bounded output, typed error codes, and no side effects."""

import json

import pytest

from skytrace import bundle as bmod
from skytrace.ai import tools
from test_report_ai import view

ENVELOPE = {"contract", "tool", "call_id", "ok", "result", "error", "evidence_id", "data_status", "data_origins", "record", "cache"}


def valid_args(v):
    keys = [m for m in v.measurements]
    acc = v.accepted_pairs()[0]
    return {
        "list_target_observations": {"status": "rejected", "limit": 5},
        "get_observation_metadata": {"key": keys[0]},
        "get_wavelength_compatibility": {"key_a": acc["a"], "key_b": acc["b"]},
        "inspect_image_quality": {"key": keys[0]},
        "get_source_measurements": {"key": keys[0]},
        "compare_observation_epochs": {"key_a": acc["a"], "key_b": acc["b"]},
        "get_astrometric_validation": {},
        "get_evidence_graph": {"focus": "claim:motion"},
        "get_analysis_provenance": {},
        "list_capabilities": {},
        "generate_investigation_summary": {},
        "validate_claim_provenance": {"claim": "In these synthetic data the motion outcome is recorded.", "evidence_ids": ["t1"]},
    }


def test_every_tool_has_valid_args_case():
    assert set(valid_args(view())) == set(tools.TOOLS)


@pytest.mark.parametrize("name", list(tools.TOOLS))
def test_envelope_and_bounds(name, no_network):
    v = view()
    s = tools.ToolSession(v, "syn-var-1")
    tools.call_tool(s, "generate_investigation_summary", {})          # t1, so validate_claim has evidence
    c = tools.call_tool(s, name, valid_args(v)[name])
    env = c.envelope
    assert set(env) == ENVELOPE and env["contract"] == "TOOLS-2" and env["tool"] == name
    assert c.ok, env["error"]
    assert env["evidence_id"] == c.id and env["data_status"] == "synthetic" and env["data_origins"] == ["synthetic"]
    assert env["record"]["content_hash"] == v.r["content_hash"]
    assert len(json.dumps(env["result"], default=str)) <= tools.MAX_OUTPUT_CHARS


def test_error_codes():
    v = view()
    s = tools.ToolSession(v, "syn-var-1")
    cases = [("no_such_tool", {}, "unknown_tool"),
             ("get_observation_metadata", {"key": "x"}, "invalid_arguments"),                 # too short
             ("get_observation_metadata", {"key": "QR3:nope:D1", "extra": 1}, "invalid_arguments"),  # unknown field
             ("list_target_observations", {"limit": 500}, "invalid_arguments"),
             ("inspect_image_quality", {"key": "QR3:2099W01_1A_0000_1:D1"}, "not_found"),
             ("get_evidence_graph", {"focus": "meas:nothing"}, "not_found")]
    for name, args, code in cases:
        c = tools.call_tool(s, name, args)
        assert not c.ok and c.envelope["error"]["code"] == code and c.envelope["result"] is None, (name, c.envelope)
        assert c.envelope["evidence_id"] is None
    assert s.outputs() == {}         # failed calls can never be cited


def test_tools_have_no_side_effects(tmp_path):
    root = bmod.SYNTHETIC_ROOT / "syn-var-1"
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    v = view()
    s = tools.ToolSession(v, "syn-var-1")
    for name, args in valid_args(v).items():
        tools.call_tool(s, name, args)
    after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert before == after
