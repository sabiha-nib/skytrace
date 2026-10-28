"""Bounded explain-the-evidence loop with an audit trail.

ask() runs at most MAX_TOOL_CALLS tool calls and MAX_ROUNDS model calls, then
passes the final answer through guard.check. One repair round is allowed if
the guard rejects; after that, the guard's verdict stands and the user sees
the problems instead of the unsupported text.

local_answer() is the deterministic fallback used when the Meta API is not
available. It is labelled as such and contains only values copied from the
record.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from . import guard, tools
from .meta_client import MetaAPIError, MetaClient, MetaUnavailable

MAX_TOOL_CALLS = 6
MAX_ROUNDS = 8
MAX_SECONDS = 120

SYSTEM = """You explain results from SKYTRACE, an astronomy evidence pipeline for NASA SPHEREx images.
Rules:
- Use only numbers that appear in tool outputs. Never compute, estimate or invent measurements.
- Distinguish a measured change from a physical interpretation. Candidates are not discoveries.
- A 'z' value is the significance of a difference under stated errors, not a probability.
- If the evidence is insufficient, say so.
- Call tools to read the investigation, then reply with ONLY a JSON object:
  {"answer": str, "claims": [{"text": str, "value": number|null, "unit": str, "evidence": "<tool_call_id>"}],
   "limitations": [str, ...]}
- Answer in the language the user writes in (English or Bangla)."""


@dataclass
class AuditEntry:
    kind: str           # "model", "tool", "guard"
    detail: dict
    t: float = field(default_factory=time.time)


@dataclass
class CopilotResult:
    mode: str                    # "meta" or "local"
    ok: bool
    answer: dict | None
    problems: list[str]
    audit: list[AuditEntry]
    model: str | None = None

    def to_dict(self) -> dict:
        return {**asdict(self), "audit": [asdict(a) for a in self.audit]}


def ask(question: str, investigation: dict, client: MetaClient | None = None) -> CopilotResult:
    audit: list[AuditEntry] = []
    try:
        client = client or MetaClient()
    except MetaUnavailable as e:
        res = local_answer(investigation)
        res.problems.insert(0, f"Meta API unavailable ({e}); showing deterministic summary")
        return res

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    outputs: dict[str, dict] = {}
    n_tool, start, repaired = 0, time.time(), False
    for _ in range(MAX_ROUNDS):
        if time.time() - start > MAX_SECONDS:
            return CopilotResult("meta", False, None, ["time budget exceeded"], audit, client.cfg.model)
        try:
            r = client.chat(messages, tools=tools.tool_specs() if n_tool < MAX_TOOL_CALLS else None)
        except (MetaAPIError, MetaUnavailable) as e:
            audit.append(AuditEntry("model", {"error": str(e)}))
            res = local_answer(investigation)
            res.problems.insert(0, f"Meta API call failed ({e}); showing deterministic summary")
            res.audit = audit + res.audit
            return res
        msg = r["message"]
        audit.append(AuditEntry("model", {"message": msg, "usage": r.get("usage"), "model": r.get("model")}))
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        if calls:
            for c in calls:
                cid, fn = c.get("id", f"call_{n_tool}"), c.get("function", {})
                if n_tool >= MAX_TOOL_CALLS:
                    out = {"error": "tool-call budget exhausted; answer now"}
                else:
                    n_tool += 1
                    try:
                        out = tools.call_tool(investigation, fn.get("name", ""), fn.get("arguments") or "{}")
                        outputs[cid] = out
                    except tools.ToolError as e:
                        out = {"error": str(e)}
                audit.append(AuditEntry("tool", {"id": cid, "name": fn.get("name"), "arguments": fn.get("arguments"), "output": out}))
                messages.append({"role": "tool", "tool_call_id": cid, "content": json.dumps(out, default=str)})
            continue
        g = guard.check(msg.get("content") or "", outputs)
        audit.append(AuditEntry("guard", {"ok": g.ok, "problems": g.problems}))
        if g.ok:
            return CopilotResult("meta", True, g.answer, [], audit, client.cfg.model)
        if repaired:
            return CopilotResult("meta", False, None, g.problems, audit, client.cfg.model)
        repaired = True
        messages.append({"role": "user", "content": "Your answer was rejected by the evidence check: "
                         + "; ".join(g.problems) + ". Revise using only numbers from tool outputs, "
                         "cite tool_call ids, include limitations, and reply with the JSON object only."})
    return CopilotResult("meta", False, None, ["round budget exceeded"], audit, client.cfg.model)


def local_answer(investigation: dict) -> CopilotResult:
    """Deterministic, model-free summary: lists what the record says, nothing more."""
    s = tools.call_tool(investigation, "get_investigation_summary", {})
    lines, claims = [], []
    for e in investigation["events"]:
        if e["step"] in ("astrometry", "variability", "pairs") or e["status"] in ("failed",):
            lines.append(f"[{e['step']} / {e['status']}] {e['detail']}")
    answer = ("Deterministic summary (no language model was used). "
              + (" ".join(lines) if lines else "No comparison results are recorded for this investigation."))
    return CopilotResult("local", True, {"answer": answer, "claims": claims,
                                         "limitations": ["Generated without a model: no interpretation is offered.",
                                                         f"Data origins: {', '.join(s['data_origins']) or 'none'}"]},
                         [], [AuditEntry("tool", {"name": "get_investigation_summary", "output": s})])
