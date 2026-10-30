"""Review Room (REVIEW-1): structured software review of an investigation by five rule sets ("roles").

The roles are checklists run by software — methods, evidence, reproducibility, data quality, interpretation — not
people, and nothing here claims that a scientist reviewed the work. Every finding cites the record, the rule or the
missing prerequisite it rests on. Outcomes: met · not met · not checked (needs something this context lacks).
"""

from __future__ import annotations

METHOD = "REVIEW-1"
ROLES = {"methods": "Methods reviewer", "evidence": "Evidence reviewer", "reproducibility": "Reproducibility reviewer",
         "data": "Data-quality reviewer", "interpretation": "Interpretation reviewer"}
CAUSAL_WORDS = ("caused", "causes", "because of", "due to", "proves", "proof", "confirms", "discovered", "discovery")


def _f(role, check, outcome, cites, detail):
    assert role in ROLES and outcome in ("met", "not met", "not checked")
    return {"role": role, "role_name": ROLES[role], "check": check, "outcome": outcome, "cites": cites, "detail": detail}


def review(record: dict, quality: dict, ledger: dict, hyp: dict, unc: dict, repro: dict, challenges: dict,
           session: dict | None = None, plan_intent: str | None = None) -> dict:
    ev = {}
    for e in record["events"]:
        ev.setdefault(e["step"], e)
    outs = ev["assess"]["data"]["outcomes"]
    s = session or {}
    q = (s.get("question") or {}).get("text") or ""
    F = []
    F.append(_f("methods", "The research question is stated", "met" if q else "not met", ["session.question"],
                f"“{q[:160]}”" if q else "No research question in the session (Command Center → Research question)."))
    if q:
        ok = plan_intent not in (None, "unknown")
        F.append(_f("methods", "The question maps to registered methods", "met" if ok else "not met", ["PLAN-1 intent"],
                    f"intent: {plan_intent}" if ok else "PLAN-1 could not map the question to registered actions."))
    p = record.get("parameters", {})
    F.append(_f("methods", "Methods and versions are recorded", "met" if p.get("methods") and p.get("analysis_version") else "not met",
                ["record.parameters.methods", "record.parameters.analysis_version"], f"{p.get('analysis_version')}; {', '.join(sorted((p.get('methods') or {}).keys()))}"))
    th = ev["assess"]["data"].get("threshold_provenance")
    F.append(_f("methods", "Decision thresholds and their origin are documented", "met" if th else "not met", ["assess.threshold_provenance"], th or "missing"))

    dq = quality.get("checks", [])
    bad = [c for c in dq if c["outcome"] in ("invalid", "incompatible")]
    F.append(_f("data", "Data-quality checks were run", "met" if dq else "not met", ["DQ-1"], f"{len(dq)} checks"))
    F.append(_f("data", "No integrity check failed", "met" if not any(c["id"] in ("DQ-FILES", "DQ-RECORD") and c["outcome"] == "invalid" for c in dq) else "not met",
                ["DQ-FILES", "DQ-RECORD"], "; ".join(f"{c['id']}: {c['outcome']}" for c in dq if c["id"] in ("DQ-FILES", "DQ-RECORD"))))
    F.append(_f("data", "Data-quality problems are disclosed", "met", ["DQ-1"],
                (f"{len(bad)} check(s) invalid or incompatible: " + ", ".join(c["id"] for c in bad)) if bad else "no invalid or incompatible checks"))
    synth = p.get("bundle_kind") == "synthetic"
    F.append(_f("data", "Data origin is stated", "met", ["record.parameters.bundle_kind"], "synthetic test data (labelled)" if synth else "archive data"))

    flags = [f for c in ledger.get("claims", []) for f in c.get("flags", []) if "absence" not in f]
    F.append(_f("evidence", "No claim rests on a single evidence item", "met" if not flags else "not met", ["LEDGER-1 flags"], "; ".join(flags) or "none flagged"))
    nc = len(ledger.get("contradictions", []))
    F.append(_f("evidence", "Contradictions are examined", "met" if nc == 0 else "not met", ["LEDGER-1 C1–C4"],
                f"{nc} contradiction(s) found by fixed rules" + ("" if nc == 0 else ": examine them in the Evidence Ledger")))
    gaps = [g for g in ledger.get("completeness", {}).get("gaps", []) if not g.get("expected")]
    F.append(_f("evidence", "Provenance is complete", "met" if not gaps else "not met", ["LEDGER-1 completeness"], f"{len(gaps)} unexpected gap(s)"))

    F.append(_f("reproducibility", "The audit's verdict", "met" if repro.get("verdict") == "reproduced" else
                "not checked" if repro.get("verdict") in ("replayable, not replayed here", "incomplete") else "not met",
                ["REPRO-1"], repro.get("verdict", "not run")))

    unq = (unc or {}).get("unquantified", [])
    F.append(_f("interpretation", "Uncertainty is addressed", "met" if (unc or {}).get("motion") or (unc or {}).get("variability") else "not met",
                ["UNC-1"], f"decomposed; {len(unq)} effect(s) named as unquantified"))
    lim = all(o.get("limitations") for o in outs)
    F.append(_f("interpretation", "Limitations are disclosed with every outcome", "met" if lim else "not met", ["ASSESS-2 outcomes"], f"{len(outs)} outcomes"))
    viable = [h["id"] for qq in hyp["questions"] for h in qq["hypotheses"] if h["overall"] in ("consistent so far",) and not h["id"] in ("V-INTRINSIC", "M-CATALOGUE")]
    F.append(_f("interpretation", "Competing explanations are addressed", "met" if not viable else "not met", ["HYPO-1"],
                ("still consistent: " + ", ".join(viable)) if viable else "no competing explanation is ‘consistent so far’"))
    crit = (challenges or {}).get("counts", {}).get("critical", 0)
    F.append(_f("interpretation", "No critical adversarial challenge is open", "met" if crit == 0 else "not met", ["ASL-1"], f"{crit} critical"))
    texts = [b.get("text", "") for b in s.get("notebook", []) if b.get("author") == "user"]
    hits = sorted({w for t in texts for w in CAUSAL_WORDS if w in t.lower()})
    F.append(_f("interpretation", "Notes avoid unsupported causal or discovery language", "met" if not hits else "not met",
                ["notebook (your text)", "REVIEW-1 word list"], ("found: " + ", ".join(hits)) if hits else
                ("no notebook text yet" if not texts else "none of the listed words found")))
    counts = {r: {k: sum(1 for f in F if f["role"] == r and f["outcome"] == k) for k in ("met", "not met", "not checked")} for r in ROLES}
    return {"method": METHOD, "content_hash": record.get("content_hash"), "findings": F, "counts": counts,
            "note": "Structured software review: rule sets, not people. ‘Met’ means the stated rule is satisfied, not that the science is right."}
