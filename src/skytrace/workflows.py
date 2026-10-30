"""Research automation (WF-1): declared, bounded, validated workflows.

A workflow names its targets (batch items, at most 4) and its steps (at most 10), each step a registered action
(`capabilities.ACTIONS`) with its inputs and dependencies. Nothing runs until the document validates: known actions
only, inputs valid for that action, dependencies on earlier steps only, unique ids, at most 24 executions in total.
Imported workflows go through the same validation. Execution is done step by step by the interface's executor, which
records a result or an error per item and step, can be cancelled between steps, and can retry failed items.

`web/js/workflows.js` applies the same rules (parity-tested).
"""

from __future__ import annotations

from .capabilities import ACTIONS
from .schema import A, ID, ISO, O, S, check

METHOD = "WF-1"
SCHEMA_ID = "skytrace.workflow/1"
MAX_TARGETS, MAX_STEPS, MAX_EXECUTIONS = 4, 10, 24
ACT = {a["id"]: a for a in ACTIONS}

WORKFLOW_SCHEMA = O({
    "schema": ({"t": "const", "v": SCHEMA_ID}, True),
    "name": (S(120, 1), True),
    "description": (S(1000), False),
    "targets": (A(S(64, 1, r"^[A-Za-z0-9_.-]{1,64}$"), MAX_TARGETS), True),
    "steps": (A(O({"id": (ID, True), "action": (S(40, 1, enum=[a["id"] for a in ACTIONS]), True),
                   "inputs": ({"t": "json", "max_bytes": 4000, "depth": 4}, False), "depends": (A(ID, MAX_STEPS), True)}), MAX_STEPS), True),
    "created_at": (ISO, False),
})


def validate(w) -> list[str]:
    if not isinstance(w, dict):
        return ["$: a workflow must be an object"]
    errs = check(WORKFLOW_SCHEMA, w)
    if errs:
        return errs
    if not w["targets"]:
        errs.append("$.targets: at least one target")
    if len(set(w["targets"])) != len(w["targets"]):
        errs.append("$.targets: targets must be distinct")
    if not w["steps"]:
        errs.append("$.steps: at least one step")
    ids = [s["id"] for s in w["steps"]]
    if len(set(ids)) != len(ids):
        errs.append("$.steps: step ids must be distinct")
    for i, s in enumerate(w["steps"]):
        bad = [d for d in s["depends"] if d not in ids[:i]]
        if bad:
            errs.append(f"$.steps[{i}]: depends on steps that do not precede it: {', '.join(bad)}")
        inputs = s.get("inputs", {})
        errs += check(ACT[s["action"]]["inputs"], inputs, f"$.steps[{i}].inputs")
    if len(w["targets"]) * len(w["steps"]) > MAX_EXECUTIONS:
        errs.append(f"$: {len(w['targets'])} targets × {len(w['steps'])} steps exceeds {MAX_EXECUTIONS} executions")
    return errs


TEMPLATES = [
    {"schema": SCHEMA_ID, "name": "Quality and evidence review", "description": "Analysis, data-quality checks, hypothesis tests and the evidence ledger for every synthetic target.",
     "targets": ["syn-var-1", "syn-hpm-1"],
     "steps": [{"id": "analysis", "action": "run_analysis", "inputs": {}, "depends": []},
               {"id": "quality", "action": "check_quality", "inputs": {}, "depends": ["analysis"]},
               {"id": "tests", "action": "evaluate_hypotheses", "inputs": {}, "depends": ["analysis"]},
               {"id": "ledger", "action": "inspect_ledger", "inputs": {}, "depends": ["analysis"]}]},
    {"schema": SCHEMA_ID, "name": "Reproducibility audit", "description": "Repeat each analysis and package it.",
     "targets": ["syn-var-1", "syn-hpm-1"],
     "steps": [{"id": "analysis", "action": "run_analysis", "inputs": {}, "depends": []},
               {"id": "repeat", "action": "run_experiment", "inputs": {"template": "reproducibility"}, "depends": ["analysis"]},
               {"id": "package", "action": "build_package", "inputs": {}, "depends": ["analysis"]}]},
    {"schema": SCHEMA_ID, "name": "Sensitivity sweep", "description": "STAB-1 for every target.",
     "targets": ["syn-var-1", "syn-hpm-1"],
     "steps": [{"id": "analysis", "action": "run_analysis", "inputs": {}, "depends": []},
               {"id": "stability", "action": "run_stability", "inputs": {}, "depends": ["analysis"]}]},
]
