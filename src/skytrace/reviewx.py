"""Evidence-driven review board (REVIEWX-1): eight automated review perspectives over one investigation.

Each perspective is a fixed selection of checks from the compiler (SCI-COMP), the claim stress tests (CLAIM-X), the
integrity firewall (INTEG-1, on the investigation report) and the method genome; every item links to the claim, method,
file or missing prerequisite it concerns. Items are findings of rules, not opinions, and automated review is not peer
review: human comments and documented responses are recorded per item in the session (`reviews`) and shown with it.
"""

from __future__ import annotations

METHOD = "REVIEWX-1"
PERSPECTIVES = [
    ("data", "Data integrity", ["T1", "T2", "T5", "V2", "V4", "D1", "D2"]),
    ("method", "Method suitability", ["A3", "A4", "M1", "M2", "M3", "M4", "M5"]),
    ("statistics", "Statistical reasoning", ["E1", "U2", "U3"]),
    ("uncertainty", "Uncertainty", ["U1", "U2", "U3", "U4"]),
    ("provenance", "Provenance", ["V1", "V2", "V3", "V4", "A1", "A2"]),
    ("reproducibility", "Reproducibility", ["V1"]),
    ("interpretation", "Interpretation", ["E2", "E3", "C1", "C2", "C3", "C4"]),
    ("reporting", "Reporting", []),
]
OUTCOME = {"pass": "no issue under this rule", "warning": "needs attention", "fail": "problem", "not applicable": "not applicable"}


def board(compiled: dict, stresses: dict, report_check: dict | None, genome: dict) -> dict:
    checks = compiled["checks"]
    out = []
    for pid, name, ids in PERSPECTIVES:
        items = []
        for c in checks:
            base = c["id"].split("-")[0]
            if base in ids:
                items.append({"id": f"{pid}:{c['id']}", "source": f"SCI-COMP {c['id']}", "rule": c["rule"], "outcome": c["outcome"],
                              "meaning": OUTCOME[c["outcome"]], "detail": c["detail"], "links": c.get("cites", [])[:8]})
        if pid == "statistics":
            for q, s in stresses.items():
                for m in s.get("modes", []):
                    if m["mode"] in ("statistics", "sensitivity"):
                        items.append({"id": f"{pid}:{q}:{m['mode']}", "source": f"CLAIM-X {m['mode']} ({q})", "rule": m["rule"],
                                      "outcome": {"pass": "pass", "warning": "warning", "fail": "fail"}.get(m["result"], "not applicable"),
                                      "meaning": m["result"], "detail": m["detail"], "links": [f"claim:{q}"] + m.get("cites", [])[:4]})
        if pid == "method":
            for m in genome["methods"]:
                if m["used_in_run"]:
                    h = m["health"]
                    missing = h["documentation_missing"]
                    items.append({"id": f"{pid}:dna:{m['id']}", "source": "METHOD-DNA-1", "rule": "a method used has documented assumptions, limits and defined known-answer tests",
                                  "outcome": "pass" if h["n_defined"] and not missing else "warning", "meaning": "documented" if not missing else "incomplete documentation",
                                  "detail": f"{h['n_defined']} known-answer test(s) defined" + (f"; missing: {', '.join(missing)}" if missing else ""),
                                  "links": [f"method:{m['id']}"]})
        if pid == "reproducibility":
            for q, s in stresses.items():
                m = next((x for x in s.get("modes", []) if x["mode"] == "reproducibility"), None)
                if m:
                    items.append({"id": f"{pid}:{q}", "source": f"CLAIM-X reproducibility ({q})", "rule": m["rule"],
                                  "outcome": {"pass": "pass", "fail": "fail"}.get(m["result"], "warning"), "meaning": m["result"], "detail": m["detail"],
                                  "links": [f"claim:{q}", "missing prerequisite: a recorded re-execution" if m["result"] == "not tested" else "$.content_hash"]})
        if pid == "reporting":
            if report_check:
                for c in report_check["checks"]:
                    items.append({"id": f"{pid}:{c['id']}", "source": f"INTEG-1 {c['id']} on the investigation report", "rule": c["rule"],
                                  "outcome": "pass" if c["ok"] else ("fail" if c["severity"] == "high" else "warning"), "meaning": c["name"],
                                  "detail": c["detail"], "links": ["report.md"] + [str(x) for x in c.get("items", [])[:4]]})
            else:
                items.append({"id": f"{pid}:none", "source": "INTEG-1", "rule": "the report is checked before export", "outcome": "not applicable",
                              "meaning": "not available", "detail": "no report text available here", "links": ["missing prerequisite: report"]})
        counts = {k: sum(i["outcome"] == k for i in items) for k in ("pass", "warning", "fail", "not applicable")}
        out.append({"id": pid, "name": name, "items": items, "counts": counts})
    return {"method": METHOD, "perspectives": out,
            "note": "Automated rule findings. They are not peer review by scientists; record your own review comments and responses on each item."}
