"""Provenance guard (GUARD-1): blocks model output that is not supported by evidence.

The model must answer with JSON:
  {"answer": "...",
   "claims": [{"text": "...", "value": <number|null>, "unit": "...", "evidence": "<tool_call_id>"}],
   "limitations": ["..."]}

Checks, all of which must pass before the answer is shown:
  1. Valid structure; every claim cites a tool call that actually happened.
  2. Every claim value occurs in that tool call's output (rounding-aware).
  3. Every number written in the answer text occurs in some tool output shown
     to the model (rounding-aware). Identifiers such as D1-D6, QR3 are exempt.
  4. No discovery/certainty language unless the evidence itself contains it.
  5. At least one limitation is stated.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

BANNED = (r"\bconfirmed (?:discovery|detection)\b", r"\bwe (?:have )?discovered\b", r"\bnew (?:planet|object|discovery)\b",
          r"\bplanet x\b", r"\bdefinitely\b", r"\bproves?\b", r"\bcertainly\b")
_NUM = re.compile(r"(?<![A-Za-z_])[-+−]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?")
_EXEMPT = re.compile(r"\b(?:D[1-6]|QR\d|DR\d|J2000|ICRS|WLMATCH-\d|APPHOT-\d|CENTROID-G2D-\d|DIFFAST-\d|PAIRDIFF-\d|LINFIT-\d|FLAGPOL-\d)\b")


@dataclass
class GuardResult:
    ok: bool
    problems: list[str] = field(default_factory=list)
    answer: dict | None = None


def _numbers_in(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out.append(float(obj))
    elif isinstance(obj, str):
        out += [_to_float(m) for m in _NUM.findall(obj) if _to_float(m) is not None]
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += _numbers_in(v)
    return out


def _to_float(s: str) -> float | None:
    try:
        return float(s.replace("−", "-").replace(",", ""))
    except ValueError:
        return None


def _supported(token: str, pool: list[float]) -> bool:
    v = _to_float(token)
    if v is None:
        return True
    decimals = len(token.split(".")[1]) if "." in token else 0
    for p in pool:
        if abs(round(p, decimals) - v) < 1e-9 or (p != 0 and abs(v - p) / abs(p) < 5e-3):
            return True
        # allow sign-free magnitude statements ("shifted by 801 mas/yr")
        if abs(round(abs(p), decimals) - abs(v)) < 1e-9:
            return True
    return False


def check(raw: str, tool_outputs: dict[str, dict]) -> GuardResult:
    problems: list[str] = []
    try:
        ans = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return GuardResult(False, ["answer is not valid JSON"])
    if not isinstance(ans, dict) or not isinstance(ans.get("answer"), str) or not isinstance(ans.get("claims"), list):
        return GuardResult(False, ["answer must be an object with 'answer' (string) and 'claims' (list)"])

    pool = [n for out in tool_outputs.values() for n in _numbers_in(out)]
    for i, c in enumerate(ans["claims"]):
        if not isinstance(c, dict):
            problems.append(f"claim {i} is not an object")
            continue
        ev = c.get("evidence")
        if ev not in tool_outputs:
            problems.append(f"claim {i} cites {ev!r}, which is not a tool call made in this session")
            continue
        val = c.get("value")
        if val is not None:
            if not isinstance(val, (int, float)) or not _supported(repr(float(val)), _numbers_in(tool_outputs[ev])):
                problems.append(f"claim {i} value {val!r} not found in evidence {ev}")

    text = _EXEMPT.sub(" ", ans["answer"])
    for tok in _NUM.findall(text):
        if not _supported(tok, pool):
            problems.append(f"number {tok} in the answer does not appear in any evidence")

    evidence_text = json.dumps(tool_outputs).lower()
    for pat in BANNED:
        if re.search(pat, ans["answer"], re.IGNORECASE) and not re.search(pat, evidence_text):
            problems.append(f"unsupported certainty/discovery language: /{pat}/")

    lim = ans.get("limitations")
    if not isinstance(lim, list) or not any(isinstance(x, str) and x.strip() for x in lim):
        problems.append("no limitations stated")
    return GuardResult(not problems, problems, ans if not problems else None)
