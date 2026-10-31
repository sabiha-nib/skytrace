"""Scientific integrity firewall (INTEG-1): export-readiness checks on a report, notebook export or any text.

Twelve checks (CHECKS), each with a stated rule and a severity (high / warning). The result is "ready", "ready with
warnings" or "needs attention". The firewall never blocks an export and never rewrites the text: it lists what to inspect.
Clearly labelled uncertainty is not a problem; unlabelled synthetic data, numbers the record does not contain, probability
language and overstated wording are. Mirrored in web/js/epistemiccore.js (`integrityCheck`, parity-tested) so the static
preview can check documents written in the browser.
"""

from __future__ import annotations

import bisect
import math
import re

from . import epistemic as epi, methodgenome as mg
from .capabilities import method_ids
from .review import CAUSAL_WORDS

METHOD = "INTEG-1"
CHECKS = [
    ("I1", "high", "synthetic data are labelled", "if the record comes from a synthetic bundle, the text says synthetic, generated or simulated"),
    ("I2", "warning", "numbers are supported", "every number in the text (other than small counts and years) matches a value in the record at the precision written"),
    ("I3", "warning", "the run is cited", "the text cites the run's content hash (at least 12 hex characters)"),
    ("I4", "high", "claims match the record", "an outcome phrase the text asserts (e.g. 'variability candidate') is the recorded category"),
    ("I5", "warning", "numbers carry units", "a number with decimals is followed by a unit or is a dimensionless quantity named before it (z, χ², ratio, scale)"),
    ("I6", "warning", "no unsupported probabilities", "the text does not assert probability language; z is a significance and statuses are rules"),
    ("I7", "warning", "simulation is not presented as observation", "a mention of counterfactual or scenario results is labelled hypothetical or 'not an observation'"),
    ("I8", "warning", "limitations are acknowledged", "the text mentions its limitations"),
    ("I9", "high", "provenance is valid", "the record's content hash recomputes"),
    ("I10", "warning", "compared inputs are compatible", "two observations joined by ↔, →, ' vs ' or ' and ' in one sentence form a WLMATCH-2 accepted pair"),
    ("I11", "warning", "methods are real", "every method identifier in the text is a registered method"),
    ("I12", "warning", "conclusions are not overstated", "the text does not assert discovery, proof, causation or certainty (negated uses are fine)"),
]
OVERSTATE = tuple(CAUSAL_WORDS) + ("confirmed", "definitely", "certainly", "undeniably")
PROB_WORDS = ("probability", "probable", "probably", "likely", "chance", "p-value", "confidence level")
PHRASES = [("variability candidate", "variability", "variability_candidate"), ("no significant brightness change", "variability", "no_variability_at_sensitivity"),
           ("motion detected", "motion", "motion_detected"), ("detected motion", "motion", "motion_detected"),
           ("no motion is detected", "motion", "no_motion_at_sensitivity"), ("motion inconsistent", "motion", "motion_inconsistent")]
UNITS = ("(fraction)", "µjy", "ujy", "mjy", "jy", "mas/yr", "mas", "µm", "um", "nm", "px", "pixel", "σ", "sigma", "%", "mjd", "yr", "year", "day", "d ", "deg", "°", "arcsec",
         "″", "s ", "mag", "visit", "exposure", "pair", "star", "file")
DIMLESS = ("z", "z_cal", "χ²", "χ²ν", "chi2", "ratio", "scale", "rms", "factor", "scatter", "σ")
NUM_RE = re.compile(r"(?<![A-Za-z0-9_\-.:])-?\d+(?:\.\d+)?(?:[eE]-?\d+)?(?![A-Za-z0-9_]|\.\d)")
SYN_RE = re.compile(r"(?<![a-z0-9:_\-])(synthetic|generated|simulated)(?![a-z0-9:_\-])")
METHOD_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*-\d+\b")


def _round_sig(v: float) -> float:
    return float(f"{v:.10g}")


def facts(record: dict, hash_ok: bool) -> dict:
    nums, keys = set(), set()

    def walk(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            if math.isfinite(x):
                nums.add(_round_sig(float(x)))
            return
        if isinstance(x, str):
            for m in NUM_RE.findall(x):
                try:
                    nums.add(_round_sig(float(m)))
                except ValueError:
                    pass
            return
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    nums |= {float(i) for i in range(len(record.get("events", [])) + 1)}      # event positions are recorded structure
    walk(record.get("events"))
    walk(record.get("parameters"))
    cats, accepted = {}, []
    for e in record["events"]:
        d = e.get("data") or {}
        if e["step"] == "assess":
            cats = {o["question"]: o["category"] for o in d.get("outcomes", [])}
        if e["step"] == "pairs":
            accepted = sorted(f"{a['a']}|{a['b']}" for a in d.get("accepted", []) if a.get("accepted", True))
        if e["step"] == "measure" and d.get("obs_id"):
            keys.add(d["obs_id"])
    return {"method": METHOD, "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic", "numbers": sorted(nums),
            "categories": cats, "accepted_pairs": accepted, "obs_keys": sorted(keys), "content_hash": record.get("content_hash"), "hash_ok": hash_ok,
            "methods": sorted(set(method_ids()) | set(mg.BY_ID) | {"WLMATCH-1", "ASSESS-1", "LINFIT-1", "REFSEL-1", "MOMENT-1", "SKY-CANON-1", "SCHEMA-1"})}


def _grounded(tok: str, nums: list, pct: bool) -> bool:
    try:
        x = float(tok)
    except ValueError:
        return True
    dec = len(tok.split(".")[1].split("e")[0].split("E")[0]) if "." in tok else 0
    sig = len(tok.lstrip("-").split("e")[0].split("E")[0].replace(".", "").lstrip("0"))
    if sig > 10:                                   # the record's numbers are kept to 10 significant digits
        x, half = _round_sig(x), abs(x) * 5e-10
    else:
        half = 0.5 * 10 ** (-dec) if "e" not in tok.lower() else abs(x) * 1e-6
    for target in ([x, x / 100] if pct else [x]):
        h = half / 100 if (pct and target != x) else half
        lo, hi = target - h - 1e-12 * abs(target), target + h + 1e-12 * abs(target)
        i = bisect.bisect_left(nums, lo)
        if i < len(nums) and nums[i] <= hi:
            return True
        i = bisect.bisect_left(nums, -hi)                     # the text may give a magnitude where the record has a sign
        if i < len(nums) and nums[i] <= -lo:
            return True
    return False


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def check(text: str, f: dict) -> dict:
    low = text.lower()
    R = []

    def add(cid, ok, detail, items=None):
        sev = next(c[1] for c in CHECKS if c[0] == cid)
        name, rule = next((c[2], c[3]) for c in CHECKS if c[0] == cid)
        R.append({"id": cid, "name": name, "rule": rule, "severity": sev, "ok": ok, "detail": detail, "items": (items or [])[:15]})

    if f.get("synthetic"):
        ok = bool(SYN_RE.search(low))
        add("I1", ok, "the text discloses synthetic data" if ok else "the record is synthetic but the text never says so")
    else:
        add("I1", True, "the record is not synthetic")
    nums = f.get("numbers") or []
    bad = []
    for m in NUM_RE.finditer(text):
        tok = m.group(0)
        try:
            x = float(tok)
        except ValueError:
            continue
        if "." not in tok and "e" not in tok.lower() and (abs(x) <= 10 or 1900 <= abs(x) <= 2100):
            continue
        pct = text[m.end():m.end() + 1] == "%"
        if not _grounded(tok, nums, pct):
            bad.append(tok)
    add("I2", not bad, f"{len(bad)} number(s) not found in the record" if bad else "every number checked is in the record", sorted(set(bad), key=bad.index))
    h = (f.get("content_hash") or "")
    cited = bool(h) and any(h[:k] in low for k in (64, 16, 12))
    add("I3", cited, "the run's content hash is cited" if cited else f"cite the run (content hash {h[:12]}…) so the text can be traced")
    wrong = []
    for phrase, q, cat in PHRASES:
        if epi.asserted_words(low, [phrase]) and (f.get("categories") or {}).get(q) not in (None, cat):
            wrong.append(f"“{phrase}” but the recorded {q} outcome is {f['categories'][q]}")
    add("I4", not wrong, "; ".join(wrong) if wrong else "no asserted outcome contradicts the record", wrong)
    nounit = []
    prose = re.sub(r"```.*?```", lambda m: " " * len(m.group(0)), text, flags=re.S)    # fenced data blocks carry units in their keys
    for m in NUM_RE.finditer(prose):
        tok = m.group(0)
        if "." not in tok:
            continue
        after = prose[m.end():m.end() + 14].lower().lstrip(" ±")
        before = prose[max(0, m.start() - 12):m.start()].lower().replace("|", " ").replace("/", " ")
        if any(after.startswith(u.strip()) for u in UNITS) or any(re.search(r"(^|[^a-z_])" + re.escape(d) + r"\s*[=:≈≥≤<>]?\s*[-−]?$", before.rstrip()) for d in DIMLESS):
            continue
        if re.match(r"^\s*(±|\+/-)", prose[m.end():m.end() + 4]) or prose[m.end():m.end() + 2].strip().startswith(("×", ")")):
            continue
        nounit.append(tok)
    add("I5", not nounit, f"{len(nounit)} decimal number(s) without a unit" if nounit else "decimal numbers carry units or are named dimensionless quantities", nounit)
    pw = epi.asserted_words(low, PROB_WORDS)
    add("I6", not pw, f"asserts: {', '.join(pw)}" if pw else "no probability language asserted", pw)
    sim = any(w in low for w in ("counterfactual", "scenario"))
    lab = any(w in low for w in ("hypothetical", "not an observation"))
    add("I7", not sim or lab, "scenario results are labelled" if lab or not sim else "counterfactual or scenario results are mentioned without 'hypothetical' or 'not an observation'")
    add("I8", "limitation" in low, "limitations are mentioned" if "limitation" in low else "the text never mentions its limitations")
    add("I9", bool(f.get("hash_ok")), "the record's hash recomputes" if f.get("hash_ok") else "the record's hash does not recompute")
    acc, keys = set(f.get("accepted_pairs") or []), f.get("obs_keys") or []
    badp = []
    for s in _sentences(text):
        found = sorted({k for k in keys if k in s}, key=s.index)
        if len(found) >= 2 and re.search(r"↔|→|\svs\.?\s|\sand\s", s):
            for i in range(len(found) - 1):
                a, b = found[i], found[i + 1]
                if f"{a}|{b}" not in acc and f"{b}|{a}" not in acc:
                    badp.append(f"{a} / {b}")
    add("I10", not badp, f"{len(badp)} compared pair(s) not accepted by WLMATCH-2" if badp else "every compared pair named is an accepted pair", badp)
    known = set(f.get("methods") or [])
    unk = sorted({m for m in METHOD_RE.findall(text) if m not in known and not any(m == k.split("/")[0] for k in known)})
    unk = [m for m in unk if not re.match(r"^(SYN|SYNTHETIC|D|Q|T|H|NX|QF|N)-", m)]
    add("I11", not unk, f"unregistered method identifier(s): {', '.join(unk)}" if unk else "every method identifier is registered", unk)
    ow = epi.asserted_words(low, OVERSTATE)
    add("I12", not ow, f"asserts: {', '.join(ow)}" if ow else "no overstated wording asserted", ow)
    high = [r for r in R if not r["ok"] and r["severity"] == "high"]
    warn = [r for r in R if not r["ok"] and r["severity"] == "warning"]
    outcome = "needs attention" if high else ("ready with warnings" if warn else "ready")
    return {"method": METHOD, "outcome": outcome, "checks": R, "n_high": len(high), "n_warning": len(warn),
            "note": "Advice only: the export is never blocked and the text is never changed."}
