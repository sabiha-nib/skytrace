"""Evidence guard (GUARD-2): blocks model output that the evidence does not support.

Expected answer object:
  {"answer": str,
   "claims": [{"text": str, "kind": "measurement"|"interpretation"|"speculation",
               "value": number|null, "unit": str, "evidence": [tool_call_id, ...]}],
   "limitations": [str, ...],
   "follow_up_questions": [str, ...], "suggested_next_steps": [str, ...]}

Checks (each failure is reported with a code):
  structure      valid JSON object with the fields above
  citation       every claim cites tool calls that ran in this session; claim values occur in them
  number         every number in the answer occurs in the evidence (rounding-aware)
  date           ISO dates / MJDs in the answer occur in the evidence
  wavelength     values with µm/nm units match wavelength-like evidence fields
  tool           tools named in the answer were actually executed
  causal         causal statements are hedged or restate the evidence's own reasons
  attribution    catalogues/missions named in the answer appear in the evidence
  certainty      no unhedged discovery, proof or certainty claims (discussing them is allowed)
  probability    significances are not presented as probabilities
  limitations    at least one limitation is stated
  synthetic      synthetic data is called synthetic and never presented as real observations
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

_NUM = re.compile(r"(?<![A-Za-z_\-:])[-+−]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?")
_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2})?)?")
_MJD = re.compile(r"\bMJD\s*([0-9]{5}(?:\.[0-9]+)?)", re.I)
_WL = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*(µm|μm|um|microns?|nm)\b", re.I)
_EXEMPT = re.compile(r"\b(?:D[1-6]|QR\d|DR\d|J2000|ICRS|[A-Z]{3,}-\d(?:/[A-Z\-]+-\d)?|[A-Z]+-[A-Z]+-\d|3σ|5σ|\d+σ|"
                     r"SYN[A-Z0-9_\-]*|SYNTHETIC:[A-Za-z0-9_:]+|QR\d:[A-Za-z0-9_:]+)\b")
_HEDGE = re.compile(r"\b(may|might|could|possibly|possible|likely|unlikely|consistent with|suggests?|perhaps|"
                    r"one explanation|cannot (?:be )?rule[sd]? out|would need|would require|if\b|whether|candidate|"
                    r"hypothes[ie]s|not (?:yet )?(?:established|confirmed|known))", re.I)
_NEG = re.compile(r"\b(not|no|never|cannot|can't|isn't|aren't|wasn't|without|neither|nor|before|until|rather than)\b", re.I)
_CAUSAL = re.compile(r"\b(because(?: of)?|caused by|due to|result(?:s|ed)? (?:of|from)|owing to|explains?|leads? to|"
                     r"is why|therefore)\b", re.I)
_CERTAIN = [
    re.compile(r"\b(?:is|are|was|were|represents?|constitutes?|confirms?)\s+(?:an?\s+|the\s+)?(?:new\s+|genuine\s+|real\s+|"
               r"confirmed\s+|definite\s+)?(?:discovery|new (?:object|planet|companion|body|moving object))\b", re.I),
    re.compile(r"\bwe (?:have )?(?:discovered|found a new|detected a new)\b", re.I),
    re.compile(r"\bconfirmed (?:discovery|detection|planet|variable|motion|companion)\b", re.I),
    re.compile(r"\b(?:definitely|certainly|undoubtedly|unquestionably|beyond doubt|proves?|proven)\b", re.I),
    re.compile(r"\bplanet x\b[^.]*\b(?:found|detected|discovered|exists?)\b", re.I),
]
_PROB = re.compile(r"\b(\d+(?:\.\d+)?\s*%|probability|chance|odds)\b[^.]*\b(variable|varies|moving|real|genuine|discovery|"
                   r"change[sd]?)\b", re.I)
_REAL = re.compile(r"\b(real|actual|genuine|archival|live)\s+(SPHEREx\s+)?(observations?|data|images?|measurements?)\b", re.I)
_SOURCES = ["Gaia", "SIMBAD", "IRSA", "SPHEREx", "WISE", "NEOWISE", "2MASS", "JWST", "Spitzer", "Hubble", "HST", "Pan-STARRS",
            "SDSS", "Horizons", "ZTF", "TESS", "Kepler", "AAVSO", "QR2", "QR3"]
STOP = set("the a an and or of to in on for with by at from this that these those is are was were be been it its as into than "
           "then there their them which who what when where how not no can could may might would should data observation "
           "observations measurement measurements value values".split())


@dataclass
class GuardResult:
    ok: bool
    problems: list[dict] = field(default_factory=list)
    answer: dict | None = None


def _to_float(s: str) -> float | None:
    try:
        return float(s.replace("−", "-").replace(",", ""))
    except ValueError:
        return None


def _numbers(obj, keyfilter=None, _key="") -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        if math.isfinite(obj) and (keyfilter is None or keyfilter(_key)):
            out.append(float(obj))
    elif isinstance(obj, str):
        if keyfilter is None or keyfilter(_key):
            out += [v for v in (_to_float(m) for m in _NUM.findall(obj)) if v is not None]
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out += _numbers(v, keyfilter, str(k))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += _numbers(v, keyfilter, _key)
    return out


def _supported(token: str, pool: list[float], allow_derived: bool = True) -> bool:
    v = _to_float(token)
    if v is None:
        return True
    decimals = len(token.split(".")[1]) if "." in token else 0
    for p in pool:
        # exact after rounding to the stated precision (sign-insensitive: "3400 mas/yr south" for -3400)
        if abs(round(p, decimals) - v) < 1e-9 or abs(round(abs(p), decimals) - abs(v)) < 1e-9:
            return True
        # or within 0.5 % (rounding to significant figures, e.g. 4.67 for 4.6690)
        if p != 0 and abs(abs(v) - abs(p)) / abs(p) < 5e-3:
            return True
    # small integers used as counts ("two epochs", "3 pairs") must still be evidenced, except trivial ones
    return allow_derived and decimals == 0 and abs(v) in (0, 1)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def check(raw: str, tool_outputs: dict[str, dict], executed_tools: set[str] | None = None,
          data_origins: list[str] | None = None) -> GuardResult:
    probs: list[dict] = []
    add = lambda code, detail: probs.append({"code": code, "detail": detail})
    try:
        ans = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return GuardResult(False, [{"code": "structure", "detail": "answer is not valid JSON"}])
    if not isinstance(ans, dict) or not isinstance(ans.get("answer"), str) or not isinstance(ans.get("claims", []), list):
        return GuardResult(False, [{"code": "structure", "detail": "answer must be an object with 'answer' (string) and 'claims' (list)"}])
    text = ans["answer"]
    extra_text = " ".join(str(x) for x in (ans.get("follow_up_questions") or []) + (ans.get("suggested_next_steps") or [])
                          if isinstance(x, str))
    executed_tools = executed_tools or set()
    origins = data_origins or []
    ev_text = json.dumps(tool_outputs, default=str)
    ev_lower = ev_text.lower()
    pool = _numbers(tool_outputs)

    # citation
    for i, c in enumerate(ans.get("claims", [])):
        if not isinstance(c, dict):
            add("structure", f"claim {i} is not an object")
            continue
        ev = c.get("evidence")
        ev = [ev] if isinstance(ev, str) else (ev or [])
        bad = [e for e in ev if e not in tool_outputs]
        if not ev or bad:
            add("citation", f"claim {i} cites {bad or 'nothing'}, not a tool call made in this session")
            continue
        val = c.get("value")
        if val is not None:
            sub = _numbers({e: tool_outputs[e] for e in ev})
            if not isinstance(val, (int, float)) or not _supported(repr(float(val)), sub, allow_derived=False):
                add("citation", f"claim {i} value {val!r} does not occur in its cited evidence {ev}")
        if c.get("kind") == "speculation" and not _HEDGE.search(str(c.get("text", ""))):
            add("causal", f"claim {i} is marked speculation but is worded as fact")

    # dates
    iso_ev = set(m.group(1) for m in _ISO.finditer(ev_text))
    body = text
    for m in _ISO.finditer(text):
        if m.group(1) not in iso_ev:
            add("date", f"date {m.group(1)} does not occur in the evidence")
    for m in _MJD.finditer(text):
        if not _supported(m.group(1), pool, allow_derived=False):
            add("date", f"MJD {m.group(1)} does not occur in the evidence")
    body = _ISO.sub(" ", _MJD.sub(" ", body))

    # wavelengths
    wl_pool = _numbers(tool_outputs, keyfilter=lambda k: any(t in k.lower() for t in ("wavelength", "lambda", "em_", "bandwidth",
                                                                                         "tolerance", "range")))
    for m in _WL.finditer(body):
        v = _to_float(m.group(1))
        unit = m.group(2).lower()
        tok = m.group(1) if unit != "nm" else f"{v / 1000:.{max(0, len(m.group(1).split('.')[-1]) + 3 if '.' in m.group(1) else 3)}f}"
        if not _supported(tok, wl_pool, allow_derived=False):
            add("wavelength", f"wavelength {m.group(0)} does not match any wavelength in the evidence")
    body = _WL.sub(" ", body)

    # numbers
    for tok in _NUM.findall(_EXEMPT.sub(" ", body + " " + extra_text)):
        if not _supported(tok, pool):
            add("number", f"number {tok} does not appear in any evidence")

    # tools named but not executed
    from .tools import TOOLS
    for name in TOOLS:
        if name in text and name not in executed_tools:
            add("tool", f"answer refers to {name}, which was not executed")

    sentences = _sentences(text)
    # causal
    for s in sentences:
        m = _CAUSAL.search(s)
        if not m or _HEDGE.search(s):
            continue
        tail = s[m.end():]
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z_\-]{3,}", tail.lower()) if w not in STOP]
        hits = sum(1 for w in words if w in ev_lower)
        if words and hits / len(words) < 0.6:
            add("causal", f"unhedged causal statement not grounded in the evidence: \"{s[:160]}\"")

    # attribution
    for src in _SOURCES:
        if re.search(rf"\b{re.escape(src)}\b", text) and src.lower() not in ev_lower:
            add("attribution", f"answer cites {src}, which does not appear in the evidence")

    # certainty / discovery
    for s in sentences:
        if s.endswith("?") or _NEG.search(s) or _HEDGE.search(s):
            continue
        for pat in _CERTAIN:
            if pat.search(s):
                add("certainty", f"unsupported certainty or discovery claim: \"{s[:160]}\"")
                break

    # probability confusion
    for s in sentences:
        if _PROB.search(s) and not _NEG.search(s):
            add("probability", f"presents a significance or percentage as a probability: \"{s[:160]}\"")

    # limitations
    lim = ans.get("limitations")
    if not isinstance(lim, list) or not any(isinstance(x, str) and x.strip() for x in lim):
        add("limitations", "no limitations stated")

    # synthetic vs real
    if "synthetic" in origins:
        if not re.search(r"\b(synthetic|simulated|generated)\b", text, re.I):
            add("synthetic", "the evidence is synthetic but the answer does not say so")
        for s in sentences:
            if _REAL.search(s) and not _NEG.search(s):
                add("synthetic", f"describes synthetic data as real: \"{s[:160]}\"")
    elif origins and re.search(r"\b(synthetic|simulated)\b", text, re.I) and "synthetic" not in ev_lower:
        add("synthetic", "calls archive data synthetic")

    return GuardResult(not probs, probs, ans if not probs else None)
