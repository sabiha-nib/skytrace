"""Adaptive Investigation Planner (PLAN-1): from a research question to a plan of registered actions.

Deterministic. A question is matched against fixed keyword rules (SPEC["rules"], first match wins) to give a structured
intent; the intent selects a plan template (SPEC["templates"]) whose steps are registered actions
(`capabilities.ACTIONS`); each step's status is decided from the current facts:

  completed  its output already exists (e.g. an analysis run is loaded) — a real result being reused, named in `note`
  ready      every precondition holds now or is produced by an earlier step
  suggested  optional, and could run
  blocked    a precondition cannot be met here (the reason says which, and what would unblock it)
Execution later moves steps to running / completed / failed / needs_review (needs_review: a step whose outcome is a
human judgement, such as inspecting a pair by eye).

Unanswerable questions (cause, discovery, distance) get no steps and the registered reason. Unrecognised questions
are reported as unrecognised, with example questions — nothing is guessed. A language model may later propose an
intent, but it must pass `validate_intent` and is planned by the same rules; it never decides an outcome.

`web/js/planner.js` runs the same algorithm on the same SPEC in the browser (parity-tested on a question corpus).
"""

from __future__ import annotations

import re

from .capabilities import ACTIONS, FACTS
from .discovery import UNANSWERABLE

METHOD = "PLAN-1"
KEY_RE = r"\b(?:QR[0-9]|SYNTHETIC):[A-Za-z0-9_]+:D[1-6]\b"
DET_RE = r"\bD([1-6])\b"
DATE_RE = r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b"
PAIR_RE = r"\b(two|pair|both|between|epochs?|visits?|versus|vs)\b"

SPEC = {
    "method": METHOD,
    "rules": [
        ["cause", r"\b(why did|what causes?|what caused|physical (cause|reason|mechanism)|mechanism)\b"],
        ["discovery", r"\b(new (object|planet|discovery|companion)|is this a (new )?discovery|planet x|discovered)\b"],
        ["distance", r"\b(how far|distance to|how distant)\b"],
        ["capabilities", r"\b(what can (you|skytrace)|which (methods|tools|capabilities)|capabilities)\b"],
        ["report", r"\b(report|write.?up|summari[sz]e|package|export)\b"],
        ["reproducibility", r"\b(reproduc\w*|replay|repeat\w*|same result)\b"],
        ["provenance", r"\b(provenance|integrity|checksums?|tamper\w*|traced?)\b"],
        ["quality", r"\b(quality|usable|rejected|excluded|flags?|flagged|bad data)\b"],
        ["uncertainty", r"\b(uncertaint\w*|error budget|how certain|how precise|error bars?)\b"],
        ["sensitivity", r"\b(sensitiv\w*|robust\w*|parameters?|stable|stability|fragile)\b"],
        ["explanations", r"\b(explanations?|alternatives?|hypothes\w*|artefacts?|artifacts?|caused by|could it be)\b"],
        ["change", r"\b(chang\w*|differ\w*|vary|varies|variab\w*)\b"],
        ["brightness", r"\b(bright\w*|dim\w*|fad\w*|flux\w*|magnitude)\b"],
        ["motion", r"\b(mov\w*|motion|proper|position\w*|shift\w*|drift\w*)\b"],
        ["coverage", r"\b(coverage|gaps?|timeline|sequences?|how many (epochs|visits|observations)|when was)\b"],
    ],
    "aspects": {"brightness": r"\b(bright\w*|dim\w*|fad\w*|flux\w*|magnitude)\b", "motion": r"\b(mov\w*|motion|proper|position\w*|shift\w*|drift\w*)\b"},
    # steps: [step id, action, optional, depends (step ids), condition]; condition ∈ always / pair / brightness / motion
    "templates": {
        "change": [["analysis", "run_analysis", False, [], "always"], ["quality", "check_quality", False, ["analysis"], "always"],
                   ["pair", "compare_pair", False, ["analysis"], "pair"], ["inspect", "inspect_pair", False, ["pair"], "pair"],
                   ["tests", "evaluate_hypotheses", False, ["analysis"], "always"], ["uncertainty", "decompose_uncertainty", False, ["analysis"], "always"],
                   ["stability", "run_stability", True, ["analysis"], "always"], ["radar", "scan_radar", True, ["quality"], "always"]],
        "brightness": [["analysis", "run_analysis", False, [], "always"], ["quality", "check_quality", False, ["analysis"], "always"],
                       ["pair", "compare_pair", False, ["analysis"], "pair"], ["inspect", "inspect_pair", False, ["pair"], "pair"],
                       ["tests", "evaluate_hypotheses", False, ["analysis"], "always"], ["uncertainty", "decompose_uncertainty", False, ["analysis"], "always"],
                       ["stability", "run_stability", True, ["analysis"], "always"]],
        "motion": [["analysis", "run_analysis", False, [], "always"], ["quality", "check_quality", False, ["analysis"], "always"],
                   ["pair", "compare_pair", True, ["analysis"], "pair"], ["tests", "evaluate_hypotheses", False, ["analysis"], "always"],
                   ["uncertainty", "decompose_uncertainty", False, ["analysis"], "always"], ["stability", "run_stability", True, ["analysis"], "always"]],
        "quality": [["analysis", "run_analysis", False, [], "always"], ["quality", "check_quality", False, ["analysis"], "always"],
                    ["ledger", "inspect_ledger", True, ["analysis"], "always"]],
        "provenance": [["analysis", "run_analysis", False, [], "always"], ["provenance", "verify_provenance", False, ["analysis"], "always"],
                       ["quality", "check_quality", False, ["analysis"], "always"]],
        "reproducibility": [["analysis", "run_analysis", False, [], "always"], ["repeat", "run_experiment", False, ["analysis"], "always"],
                            ["provenance", "verify_provenance", True, ["analysis"], "always"], ["package", "build_package", False, ["analysis"], "always"]],
        "sensitivity": [["analysis", "run_analysis", False, [], "always"], ["stability", "run_stability", False, ["analysis"], "always"],
                        ["uncertainty", "decompose_uncertainty", True, ["analysis"], "always"]],
        "uncertainty": [["analysis", "run_analysis", False, [], "always"], ["uncertainty", "decompose_uncertainty", False, ["analysis"], "always"],
                        ["stability", "run_stability", True, ["analysis"], "always"]],
        "explanations": [["analysis", "run_analysis", False, [], "always"], ["tests", "evaluate_hypotheses", False, ["analysis"], "always"],
                         ["ledger", "inspect_ledger", False, ["analysis"], "always"], ["pair", "compare_pair", True, ["analysis"], "pair"]],
        "coverage": [["analysis", "run_analysis", False, [], "always"], ["sequences", "build_sequences", False, ["analysis"], "always"],
                     ["radar", "scan_radar", True, ["analysis"], "always"]],
        "report": [["analysis", "run_analysis", False, [], "always"], ["ledger", "inspect_ledger", False, ["analysis"], "always"],
                   ["package", "build_package", False, ["analysis"], "always"]],
    },
    "experiment_template": {"reproducibility": "reproducibility"},
    "examples": ["Could this source have changed between the two recorded observation epochs?", "Does the target move?",
                 "How much of the data is usable?", "Can this result be reproduced?", "Which explanations remain viable?",
                 "What are the uncertainties made of?", "Which analysis choices change the result?"],
    "unanswerable": {q["id"]: {"text": q["text"], "why": q["why"], "needed": q["needed"]} for q in UNANSWERABLE},
    "unanswerable_map": {"cause": "Q-CAUSE", "discovery": "Q-DISCOVERY", "distance": "Q-DIST"},
}
ACT = {a["id"]: a for a in ACTIONS}
SPEC["actions"] = {a["id"]: {k: a[k] for k in ("title", "preconditions", "produces", "confirm", "cost", "static", "capabilities")} | {"review": bool(a.get("review"))}
                   for a in ACTIONS}
SPEC["facts"] = FACTS
SPEC["patterns"] = {"key": KEY_RE, "detector": DET_RE, "date": DATE_RE, "pair": PAIR_RE}


def parse(question: str, targets: list[str] | None = None) -> dict:
    q = question or ""
    ql = q.lower()
    kind, rule = "unknown", None
    for k, pat in SPEC["rules"]:
        if re.search(pat, ql, re.ASCII):
            kind, rule = k, pat
            break
    aspects = [a for a, pat in SPEC["aspects"].items() if re.search(pat, ql, re.ASCII)]
    if kind in ("brightness", "motion") and len(aspects) == 2:
        kind = "change"
    keys = list(dict.fromkeys(re.findall(KEY_RE, q, re.ASCII)))
    dets = sorted({int(d) for d in re.findall(DET_RE, q, re.ASCII)})
    dates = list(dict.fromkeys(re.findall(DATE_RE, q, re.ASCII)))
    tgt = None
    for t in targets or []:
        if t and t.lower() in ql:
            tgt = t
            break
    return {"kind": kind, "rule": rule, "aspects": aspects, "pair_requested": bool(re.search(PAIR_RE, ql, re.ASCII)) or len(keys) >= 2,
            "keys": keys[:4], "detectors": dets, "dates": dates[:4], "target": tgt, "text": q[:500]}


def validate_intent(intent: dict) -> list[str]:
    """Checks an intent proposed by anything other than `parse` (e.g. a language model) before it is planned."""
    errs = []
    if not isinstance(intent, dict):
        return ["intent must be an object"]
    if intent.get("kind") not in set(SPEC["templates"]) | set(SPEC["unanswerable_map"]) | {"capabilities", "unknown"}:
        errs.append(f"unknown intent kind {intent.get('kind')!r}")
    for k in intent.get("keys", []) or []:
        if not isinstance(k, str) or not re.fullmatch(KEY_RE.replace(r"\b", ""), k):
            errs.append(f"invalid observation key {k!r}")
    return errs


def _fact(facts: dict, name: str, action: dict) -> bool:
    if name == "server_or_precomputed":
        return bool(facts.get("server")) or action["static"] in ("precomputed", "browser")
    if name == "has_pair":
        return bool(facts.get("pair"))
    return bool(facts.get(name))


def plan(question: str, facts: dict) -> dict:
    intent = parse(question, facts.get("targets"))
    kind = intent["kind"]
    out = {"method": METHOD, "question": intent["text"], "intent": intent, "steps": [], "answerable": True, "explanation": "",
           "requires_confirmation": False}
    if kind in SPEC["unanswerable_map"]:
        u = SPEC["unanswerable"][SPEC["unanswerable_map"][kind]]
        out.update(answerable=False, explanation=f"Not answerable here: {u['why']}. Would need: {'; '.join(u['needed'])}.")
        return out
    if kind == "capabilities":
        out["explanation"] = "Ask the copilot or open the capability registry: this is a question about Skytrace, not about the data."
        return out
    if kind == "unknown":
        out.update(answerable=False, explanation="The question did not match any planning rule. Try one of: " + " · ".join(SPEC["examples"]))
        return out
    if not facts.get("has_target_data"):
        out["explanation"] = "The selected target has no stored observations, so no analysis can run."
    pair = intent["keys"][:2] if len(intent["keys"]) >= 2 else (facts.get("pair") or None)
    eff = dict(facts, pair=pair)
    produced: dict[str, str] = {}
    status_of: dict[str, str] = {}
    for sid, aid, optional, deps, cond in SPEC["templates"][kind]:
        if cond == "pair" and not intent["pair_requested"] and not optional:
            continue
        if cond == "pair" and optional and not (intent["pair_requested"] or pair):
            continue
        a = ACT[aid]
        step = {"id": sid, "action": aid, "capabilities": a["capabilities"], "title": a["title"], "depends": [d for d in deps if d in status_of],
                "confirm": a["confirm"], "cost": a["cost"], "optional": optional, "review": bool(a.get("review")), "inputs": {}, "note": ""}
        if aid in ("compare_pair", "inspect_pair") and pair:
            step["inputs"] = {"a": pair[0], "b": pair[1]}
        if aid == "run_experiment":
            step["inputs"] = {"template": SPEC["experiment_template"].get(kind, "sensitivity")}
        missing = []
        for f in a["preconditions"]:
            if _fact(eff, f, a) or f in produced:
                continue
            missing.append(f)
        if facts.get("static") and a["static"] == "unavailable":
            missing.append("server")
        if aid == "run_analysis" and facts.get("has_run"):
            step["status"] = "completed"
            step["note"] = f"reusing the loaded analysis run {str(facts.get('run_hash') or '')[:12]}"
        elif missing:
            step["status"] = "blocked"
            step["note"] = "needs: " + "; ".join(FACTS.get(m, m) for m in dict.fromkeys(missing))
            if "has_pair" in missing:
                step["note"] += " — select two observations in the Time Machine, or name them in the question"
        elif any(status_of.get(d) == "blocked" for d in step["depends"]):
            step["status"] = "blocked"
            step["note"] = "waits for a blocked step: " + ", ".join(d for d in step["depends"] if status_of.get(d) == "blocked")
        else:
            step["status"] = "suggested" if optional else "ready"
        for p_ in a["produces"]:
            if step["status"] in ("ready", "completed", "suggested"):
                produced[p_] = sid
        status_of[sid] = step["status"]
        out["steps"].append(step)
    out["requires_confirmation"] = any(s["confirm"] and s["status"] in ("ready", "suggested") for s in out["steps"])
    if not out["explanation"]:
        n_b = sum(s["status"] == "blocked" for s in out["steps"])
        out["explanation"] = (f"{len(out['steps'])} steps from the {kind} template" + (f"; {n_b} blocked" if n_b else "") +
                              ". Steps marked ‘confirm’ re-execute analyses or take time and run only after you confirm.")
    return out
