"""Copilot loop: question -> context -> tool selection -> validated tool execution -> model
interpretation -> evidence guard -> response.

Budgets: at most MAX_TOOL_CALLS tool calls, MAX_ROUNDS model calls and MAX_SECONDS
wall time. One repair round is allowed after a guard rejection; if the repaired
answer also fails, the model's text is withheld and replaced by the local
assistant's grounded answer, with the reasons shown. Rejected drafts are kept in
the audit record (never secrets: the API key is not part of any message).

Mode is always reported truthfully: "meta" only when a Meta model produced the
shown answer, "local" otherwise.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from ..view import InvestigationView
from . import guard, local
from .meta_client import MetaAPIError, MetaClient, MetaUnavailable
from .tools import ToolSession, call_tool, tool_specs

MAX_TOOL_CALLS = 8
MAX_ROUNDS = 10
MAX_SECONDS = 150

SYSTEM = """You are the research copilot inside SKYTRACE, an evidence-first tool for NASA SPHEREx images.
You help a user investigate ONE finished, deterministic investigation of one target.

How to work:
- Call the read-only tools to look up evidence before answering. Plan: summary first, then the specific tools the question needs.
- Use only numbers, dates and wavelengths that appear in tool outputs. Never compute or estimate new measurements.
- Keep three things apart: evidence (what was measured), interpretation (what it may mean, hedged), speculation (clearly marked).
- A 'z' value is the significance of a difference under the stated errors, not a probability.
- Candidates are not discoveries. You may discuss what would be needed to establish one.
- Flux comparisons are valid only for wavelength-matched pairs (rule WLMATCH-1). Say so when relevant.
- If the data are synthetic, say they are synthetic test data, not observations.
- If the evidence is insufficient, say what is missing and which data or step would supply it.
- If the question is ambiguous, ask one short follow-up question in follow_up_questions.
- Answer in the user's language (English or Bangla).

Reply with ONLY a JSON object:
{"answer": str,
 "claims": [{"text": str, "kind": "measurement"|"interpretation"|"speculation", "value": number|null, "unit": str,
             "evidence": ["<tool_call_id>", ...]}],
 "limitations": [str, ...],
 "follow_up_questions": [str, ...],
 "suggested_next_steps": [str, ...]}"""


@dataclass
class CopilotResult:
    mode: str                       # "meta" | "local"
    ok: bool
    answer: dict | None
    problems: list[str]
    tool_calls: list[dict]
    audit: list[dict]
    model: str | None = None
    withheld: list[dict] = field(default_factory=list)   # drafts blocked by the guard

    def to_dict(self) -> dict:
        return asdict(self)


def _context(s: ToolSession) -> str:
    v = s.view
    return json.dumps({"target": v.r["target"], "target_id": s.target_id, "synthetic": v.is_synthetic(),
                       "data_origins": v.data_origins(), "n_measurements": len(v.measurements),
                       "outcomes": [{"question": o["question"], "category": o["category"]} for o in v.outcomes()]})


def _local(question: str, s: ToolSession, problems: list[str], audit: list[dict], withheld=None, model=None) -> CopilotResult:
    a = local.answer(question, s)
    g = guard.check(json.dumps(a), s.outputs(), s.executed_names(), s.view.data_origins())
    audit.append({"kind": "guard", "on": "local", "ok": g.ok, "problems": g.problems})
    return CopilotResult("local", g.ok, a if g.ok else None, problems + [p["detail"] for p in g.problems],
                         [asdict(c) for c in s.calls], audit, model, withheld or [])


def ask(question: str, view: InvestigationView, target_id: str, history: list[dict] | None = None,
        client: MetaClient | None = None) -> CopilotResult:
    s = ToolSession(view, target_id)
    audit: list[dict] = []
    question = question.strip()[:2000]
    try:
        client = client or MetaClient()
    except MetaUnavailable as e:
        return _local(question, s, [f"Meta model not used: {e}. Answer written by the local deterministic assistant."], audit)

    messages = [{"role": "system", "content": SYSTEM},
                {"role": "system", "content": "Investigation context: " + _context(s)}]
    for h in (history or [])[-6:]:
        if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str):
            messages.append({"role": h["role"], "content": h["content"][:2000]})
    messages.append({"role": "user", "content": question})
    n_tool, start, repaired, withheld = 0, time.time(), False, []
    for _ in range(MAX_ROUNDS):
        if time.time() - start > MAX_SECONDS:
            return _local(question, s, ["Meta model exceeded the time budget; local answer shown."], audit, withheld, client.cfg.model)
        t0 = time.time()
        try:
            r = client.chat(messages, tools=tool_specs() if n_tool < MAX_TOOL_CALLS else None)
        except (MetaAPIError, MetaUnavailable) as e:
            audit.append({"kind": "model", "error": str(e)[:500]})
            return _local(question, s, [f"Meta model call failed ({str(e)[:200]}); local answer shown."], audit, withheld, client.cfg.model)
        msg = r["message"]
        audit.append({"kind": "model", "model": r.get("model"), "id": r.get("id"), "usage": r.get("usage"),
                      "seconds": round(time.time() - t0, 2), "finish_reason": r.get("finish_reason"),
                      "tool_calls": [c.get("function", {}).get("name") for c in (msg.get("tool_calls") or [])],
                      "content": (msg.get("content") or "")[:4000]})
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        if calls:
            for c in calls:
                cid, fn = c.get("id") or f"call_{n_tool}", c.get("function", {})
                if n_tool >= MAX_TOOL_CALLS:
                    out = {"error": "tool-call budget exhausted; answer with the evidence you have"}
                else:
                    n_tool += 1
                    out = call_tool(s, fn.get("name", ""), fn.get("arguments") or "{}", cid).output
                messages.append({"role": "tool", "tool_call_id": cid, "content": json.dumps(out, default=str)})
            continue
        content = (msg.get("content") or "").strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        g = guard.check(content, s.outputs(), s.executed_names(), view.data_origins())
        audit.append({"kind": "guard", "on": "meta", "ok": g.ok, "problems": g.problems})
        if g.ok:
            return CopilotResult("meta", True, g.answer, [], [asdict(c) for c in s.calls], audit, client.cfg.model, withheld)
        withheld.append({"draft": content[:4000], "problems": g.problems})
        if repaired:
            return _local(question, s, ["The model's answer was withheld by the evidence guard: "
                                        + "; ".join(p["detail"] for p in g.problems[:4])], audit, withheld, client.cfg.model)
        repaired = True
        messages.append({"role": "user", "content": "The evidence guard rejected that answer: "
                         + "; ".join(p["detail"] for p in g.problems[:8])
                         + ". Revise: use only values from tool outputs, cite tool_call ids, hedge interpretations, state "
                           "limitations, and reply with the JSON object only."})
    return _local(question, s, ["Meta model exceeded the round budget; local answer shown."], audit, withheld, client.cfg.model)
