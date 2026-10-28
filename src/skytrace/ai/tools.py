"""Read-only, schema-validated tools the model may call.

All tools read from one investigation record (the output of pipeline.run).
None of them fetch data, compute new measurements, touch files, or run code.
Outputs are size-bounded and carry a stable `evidence_id` so the guard can
check that every claim points at something the model was actually shown.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_OUTPUT_CHARS = 12000


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_Args):
    pass


class StepArgs(_Args):
    step: str = Field(..., min_length=1, max_length=64, description="Step name prefix, e.g. 'astrometry', 'pairs', 'measure'")
    status: Literal["any", "ok", "rejected", "failed", "skipped", "info"] = "any"
    limit: int = Field(10, ge=1, le=50)


class ToolError(ValueError):
    pass


def _summary(inv: dict, _: NoArgs) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for e in inv["events"]:
        c = counts.setdefault(e["step"], {})
        c[e["status"]] = c.get(e["status"], 0) + 1
    origins = sorted({p["origin"] for e in inv["events"] for p in e["provenance"]})
    return {"target": inv["target"], "parameters": inv["parameters"], "step_status_counts": counts,
            "data_origins": origins, "content_hash": inv.get("content_hash")}


def _events(inv: dict, a: StepArgs) -> dict:
    sel = [dict(e, index=i) for i, e in enumerate(inv["events"])
           if e["step"].startswith(a.step) and (a.status == "any" or e["status"] == a.status)]
    for e in sel:  # provenance shortened to what an explanation needs
        e["provenance"] = [{k: p.get(k) for k in ("source", "origin", "release", "dataset_id", "source_url", "retrieved_at")}
                           for p in e["provenance"]]
    return {"n_matching": len(sel), "events": sel[: a.limit]}


TOOLS: dict[str, tuple[type[_Args], Callable[[dict, Any], dict], str]] = {
    "get_investigation_summary": (NoArgs, _summary,
                                  "Overview of the investigation: target, parameters, counts of steps by status, data origins."),
    "get_events": (StepArgs, _events,
                   "Logged steps whose name starts with `step` (e.g. 'resolve', 'discover', 'measure', 'pairs', "
                   "'variability', 'astrometry'), optionally filtered by status. Includes data and provenance."),
}


def tool_specs() -> list[dict]:
    """OpenAI-compatible tool definitions."""
    return [{"type": "function", "function": {"name": n, "description": d, "parameters": m.model_json_schema()}}
            for n, (m, _, d) in TOOLS.items()]


def call_tool(inv: dict, name: str, raw_args: str | dict) -> dict:
    if name not in TOOLS:
        raise ToolError(f"unknown tool {name!r}")
    model, fn, _ = TOOLS[name]
    try:
        args = model.model_validate_json(raw_args) if isinstance(raw_args, str) else model.model_validate(raw_args or {})
    except ValidationError as e:
        raise ToolError(f"invalid arguments for {name}: {e.errors(include_url=False)}") from e
    out = fn(inv, args)
    text = json.dumps(out, default=str)
    if len(text) > MAX_OUTPUT_CHARS:
        out = {"truncated": True, "note": f"output exceeded {MAX_OUTPUT_CHARS} chars; narrow the query",
               "partial": text[:MAX_OUTPUT_CHARS]}
    return out
