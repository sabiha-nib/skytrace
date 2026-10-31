"""Negative knowledge registry (NEG-1): what was attempted and could not be established.

Entries are derived from the record (exclusions, failed measurements, rejected comparisons, uncalibrated pairs, tests that
were not run, inconclusive or lacked evidence, unresolved contradictions, known limitations), from DISC-1 (questions that
cannot be answered here) and from the environment report (services this machine cannot reach). The browser adds the
session's own entries (failed reproductions, refused or failed runs, abandoned hypotheses, entries you write) — nothing in
the history is erased.

Every entry records what was attempted, why, what happened, the inputs, whether the failure was technical or scientific,
what remains unknown, whether it can be repeated and what would unblock it, and one distinction from DISTINCTIONS.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

METHOD = "NEG-1"
CATEGORIES = ["failed analysis", "inconclusive test", "unavailable data", "unsupported method", "unresolved contradiction", "unsuccessful reproduction",
              "missing measurement", "invalid comparison", "abandoned hypothesis", "known limitation"]
DISTINCTIONS = ["no data", "data unavailable", "data not inspected", "test not run", "test failed", "test inconclusive", "evidence insufficient"]
ENV_REPORT = Path(__file__).resolve().parents[2] / "data" / "environment_report.json"


def _e(eid, category, distinction, attempted, why, happened, inputs, failure, unknown, repeatable, unblock, source):
    return {"id": eid, "category": category, "distinction": distinction, "attempted": attempted, "why": why, "happened": happened,
            "inputs": inputs[:12], "n_inputs": len(inputs), "failure": failure, "unknown": unknown, "repeatable": repeatable, "unblock": unblock,
            "source": source, "origin": "record" if source.startswith("$") else source.split(":")[0]}


def registry(record: dict, disc: dict, ledger: dict, env_report: dict | None = None) -> dict:
    E = []
    ev = {}
    for i, e in enumerate(record["events"]):
        ev.setdefault(e["step"], []).append((i, e))
    sel = ev.get("select", [])
    by_code = {}
    for i, e in sel:
        by_code.setdefault(e.get("detail", "").split(": ", 1)[-1], []).append((e.get("data") or {}).get("key"))
    for j, (reason, keys) in enumerate(by_code.items()):
        E.append(_e(f"N-SEL-{j}", "unavailable data", "no data", f"measure the target in {len(keys)} image(s)", "every image covering the target is a candidate observation",
                    f"excluded before measurement: {reason}", keys, "technical", "the target's flux and position at those epochs",
                    "no — the exclusion follows from the image geometry", "an image in which the target is not near the edge", f"$.events[{sel[0][0]}]"))
    failed = Counter()
    keys_by = {}
    for i, e in ev.get("measure", []):
        d = e.get("data") or {}
        if e.get("status") != "ok" or d.get("quality") != "ok":
            reason = str(d.get("quality") or e.get("status")).split(":")[0]   # grouped by the recorded quality code
            failed[reason] += 1
            keys_by.setdefault(reason, []).append(d.get("obs_id"))
    for j, (reason, n) in enumerate(failed.items()):
        E.append(_e(f"N-MEAS-{j}", "missing measurement", "test failed", f"measure {n} exposure(s)", "per-exposure measurement feeds every comparison and the motion fit",
                    f"measurement refused: {reason}", keys_by[reason], "technical", "the target's values in those exposures",
                    "yes — re-running gives the same refusal (deterministic)", "unflagged pixels around the target, or a method that models the damage", "$.events[measure]"))
    pr = (ev.get("pairs") or [(None, {"data": {}})])[0]
    reasons = (pr[1].get("data") or {}).get("rejection_reasons") or {}
    for j, (code, n) in enumerate(sorted(reasons.items())):
        E.append(_e(f"N-PAIR-{j}", "invalid comparison", "test not run", f"compare flux in {n} pair(s) of exposures", "brightness change can only be measured between comparable exposures",
                    f"rejected by WLMATCH-2: {code}", [], "scientific", "whether the flux changed between those exposures",
                    "yes (deterministic)", "exposures of the same detector and release at the same wavelength", f"$.events[{pr[0]}].data.rejection_reasons"))
    var = (ev.get("variability") or [(None, {"data": {}})])[0]
    uncal = [p for p in (var[1].get("data") or {}).get("pairs", []) if not (p.get("differential") or {}).get("calibrated")]
    if uncal:
        E.append(_e("N-UNCAL", "unsupported method", "evidence insufficient", f"reference-calibrate {len(uncal)} comparison(s) (PAIRDIFF-2)",
                    "calibration removes exposure-level offsets that could mimic a change", "fewer than 3 matched reference stars: left uncalibrated",
                    [f"{p['a']}|{p['b']}" for p in uncal], "scientific", "whether those differences survive calibration", "yes (deterministic)",
                    "more reference stars in the cutout (a larger cutout or deeper catalogue)", f"$.events[{var[0]}].data.pairs"))
    for i, (sk) in enumerate((var[1].get("data") or {}).get("skipped", [])[:1]):
        sk_all = (var[1].get("data") or {}).get("skipped", [])
        E.append(_e("N-SKIP", "missing measurement", "data not inspected", f"compare {len(sk_all)} accepted pair(s)", "accepted pairs are compared unless an input is unusable",
                    "skipped: " + "; ".join(sorted({str(s.get('reason', s))[:60] for s in sk_all}))[:200], [str(s.get("a", ""))[:60] for s in sk_all], "technical",
                    "the comparison values", "yes (deterministic)", "usable photometry in both exposures", f"$.events[{var[0]}].data.skipped"))
    status_map = {"not_tested": ("test not run", "inconclusive test"), "evidence_unavailable": ("evidence insufficient", "inconclusive test"),
                  "inconclusive": ("test inconclusive", "inconclusive test")}
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q.get("hypotheses", []):
            for t in h.get("tests", []):
                if t["status"] in status_map:
                    dist, cat = status_map[t["status"]]
                    E.append(_e(f"N-T-{h['id']}-{t['id']}", cat, dist, f"{t['id']}: {t['description']}", f"tests {h['id']} — {h['statement']}",
                                f"{t['status'].replace('_', ' ')}: {t.get('detail', '')}"[:240], [], "scientific" if t["status"] == "inconclusive" else "technical",
                                f"whether {h['id']} holds", "yes (deterministic on the same record)",
                                {"not_tested": "the input or method the test needs (see the Discovery Engine plan)", "evidence_unavailable": "the missing evidence named in the detail",
                                 "inconclusive": "more data or a more sensitive comparison"}[t["status"]], f"HYPO-1:{h['id']}:{t['id']}"))
    for qq in disc.get("questions", []):
        if qq.get("status") == "not answerable":
            E.append(_e(f"N-Q-{qq['id']}", "unsupported method", "no data", qq["text"], "the question is part of the investigation's scope",
                        f"not answerable: {qq.get('why_not') or 'no registered capability answers it'}"[:240], [], "scientific", qq["text"], "no",
                        "a new capability or new data (see DISC-1)", f"DISC-1:{qq['id']}"))
    for j, c in enumerate(ledger.get("contradictions", [])):
        E.append(_e(f"N-C-{j}", "unresolved contradiction", "test inconclusive", f"reconcile {c.get('kind')} for {' / '.join(c.get('items') or [])}",
                    "contradictory evidence must be resolved before a claim rests on it", c.get("detail", ""), c.get("items") or [], "scientific", c.get("meaning", ""),
                    "yes", "a test that decides between the two results (see Claim stress test)", f"LEDGER-1:{c.get('rule')}"))
    a = (ev.get("assess") or [(None, {"data": {}})])[0]
    for o in (a[1].get("data") or {}).get("outcomes", []):
        for k, lim in enumerate(o.get("limitations") or []):
            E.append(_e(f"N-L-{o['question']}-{k}", "known limitation", "evidence insufficient", f"answer the {o['question']} question", "stated with the outcome",
                        lim, [], "scientific", "what the method cannot see", "n/a", "a method or data that removes the limitation", f"$.events[{a[0]}].data.outcomes"))
    env = env_report
    if env is None and ENV_REPORT.exists():
        try:
            env = json.loads(ENV_REPORT.read_text())
        except (OSError, ValueError):
            env = None
    for j, s in enumerate((env or {}).get("services", (env or {}).get("checks", [])) or []):
        st = s.get("verdict") or s.get("status") or s.get("outcome") or ""
        if st and st not in ("ok", "reachable") and not st.startswith("http_"):     # http_* = the host answered
            E.append(_e(f"N-ENV-{j}", "unavailable data", "data unavailable", f"reach {s.get('name') or s.get('service')}", "real archive data and live services",
                        f"{st} ({s.get('host', '')})"[:200], [], "technical", "real SPHEREx observations of the targets", "yes, from a machine with access",
                        "allowlist the service (docs/ENVIRONMENT_REPORT.md)", f"environment:{s.get('name') or s.get('service')}"))
    counts = {c: sum(e["category"] == c for e in E) for c in CATEGORIES}
    return {"method": METHOD, "categories": CATEGORIES, "distinctions": DISTINCTIONS, "entries": E, "counts": counts,
            "note": "Nothing here is a finding. Each entry is something that was attempted (or would be needed) and did not produce knowledge."}
