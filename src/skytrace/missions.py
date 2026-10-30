"""Missions (MISSION-1): guided sequences of tasks whose completion is read from the research session.

A mission states its objective, prerequisites, tasks, expected outputs, completion criteria and evidence requirements.
Task completion is never self-declared: each task has a criterion evaluated over the session — its activity history
(events after the mission started), its question, runs, notebook blocks and hypotheses — except review tasks, which
need a written review note. A completed mission means the steps were done; it says nothing about whether a conclusion is
right, and nothing is scored or rewarded.

Criterion forms (evaluated identically by `web/js/missions.js`, parity-tested):
  {"event": [kinds], "min": n}        at least n history events of these kinds since the mission started
  {"question": true}                  the session has a research question
  {"runs": n}                         at least n analysis runs attached
  {"notebook": [types], "min": n}     at least n notebook blocks of these types
  {"hypotheses_with_tests": n}        at least n user hypotheses citing a recorded test
  {"review": true}                    a review note for this task exists
"""

from __future__ import annotations

METHOD = "MISSION-1"

MISSIONS = [
    {"id": "verify-integrity", "level": "beginner", "title": "Verify the integrity of a dataset",
     "objective": "Establish that the files behind the investigation are intact and that the record traces to them.",
     "prerequisites": ["a target with stored observations"], "expected_outputs": ["data-quality checks reviewed", "provenance verification result"],
     "evidence": ["DQ-1 checks", "PROVCHECK-1 checks (full application)"],
     "tasks": [
         {"id": "run", "title": "Run (or load) the analysis", "criterion": {"runs": 1}},
         {"id": "quality", "title": "Open the Data Quality Observatory", "criterion": {"event": ["quality.view"], "min": 1}},
         {"id": "provenance", "title": "Verify provenance (re-run)", "criterion": {"event": ["provenance.run"], "min": 1},
          "note": "needs the full application; in the static preview this task stays open"},
         {"id": "review", "title": "Write what the checks showed", "criterion": {"review": True}}]},
    {"id": "compare-pair", "level": "beginner", "title": "Compare two compatible observations",
     "objective": "Compare two wavelength-matched exposures and record what changed, with its significance and limits.",
     "prerequisites": ["an analysis run"], "expected_outputs": ["a pair comparison", "a notebook observation"],
     "evidence": ["WLMATCH-2 decision", "PAIRDIFF-1/2 significance", "REGDIAG-1 diagnostics"],
     "tasks": [
         {"id": "run", "title": "Run (or load) the analysis", "criterion": {"runs": 1}},
         {"id": "pair", "title": "Open a wavelength-matched pair in the Time Machine", "criterion": {"event": ["pair.view_matched"], "min": 1}},
         {"id": "note", "title": "Record the comparison in the notebook", "criterion": {"notebook": ["observation", "measurement", "evidence"], "min": 1}},
         {"id": "review", "title": "Review: what does the comparison establish, and what not?", "criterion": {"review": True}}]},
    {"id": "examine-candidate", "level": "research", "title": "Examine a recorded candidate",
     "objective": "Take a variability or motion outcome through support, conflicts, competing explanations and sensitivity.",
     "prerequisites": ["an analysis run with an outcome to examine"], "expected_outputs": ["claim inspected", "explanations tested",
                                                                                         "sensitivity known", "a written conclusion"],
     "evidence": ["LEDGER-1 claim and contradictions", "HYPO-1 matrix", "STAB-1 or EXP-1 sensitivity"],
     "tasks": [
         {"id": "run", "title": "Run (or load) the analysis", "criterion": {"runs": 1}},
         {"id": "claim", "title": "Inspect the claim in the Evidence Ledger", "criterion": {"event": ["ledger.claim"], "min": 1}},
         {"id": "conflicts", "title": "Check the contradiction inspector", "criterion": {"event": ["ledger.contradictions"], "min": 1}},
         {"id": "explanations", "title": "Review competing explanations", "criterion": {"event": ["arena.view"], "min": 1}},
         {"id": "sensitivity", "title": "Check sensitivity to analysis choices", "criterion": {"event": ["stability.run", "experiment.sensitivity", "experiment.parameter", "experiment.robustness"], "min": 1}},
         {"id": "conclusion", "title": "Write a conclusion block", "criterion": {"notebook": ["conclusion"], "min": 1}},
         {"id": "review", "title": "Review the conclusion against its limitations", "criterion": {"review": True}}]},
    {"id": "reproduce", "level": "research", "title": "Reproduce an existing analysis",
     "objective": "Show that the analysis gives the identical result again and package it so others can check.",
     "prerequisites": ["an analysis run"], "expected_outputs": ["identical content hash on repetition", "reproducibility package"],
     "evidence": ["EXP-1 reproducibility or record replay", "PKG-1 checksums"],
     "tasks": [
         {"id": "run", "title": "Run (or load) the analysis", "criterion": {"runs": 1}},
         {"id": "repeat", "title": "Run a reproducibility experiment or replay a saved record", "criterion": {"event": ["experiment.reproducibility", "record.replay"], "min": 1}},
         {"id": "package", "title": "Export the reproducibility package", "criterion": {"event": ["package.export", "session.export"], "min": 1}},
         {"id": "review", "title": "Review: what was reproduced, and against what?", "criterion": {"review": True}}]},
    {"id": "test-hypothesis", "level": "research", "title": "Test a hypothesis against the evidence",
     "objective": "State a hypothesis, attach the recorded tests that bear on it, and write what they show.",
     "prerequisites": ["an analysis run"], "expected_outputs": ["a research question", "a hypothesis with attached tests", "a conclusion"],
     "evidence": ["HYPO-1 test results"],
     "tasks": [
         {"id": "question", "title": "Set a research question", "criterion": {"question": True}},
         {"id": "hypothesis", "title": "Write a hypothesis and attach at least one recorded test", "criterion": {"hypotheses_with_tests": 1}},
         {"id": "arena", "title": "Open the Hypothesis Arena", "criterion": {"event": ["arena.view"], "min": 1}},
         {"id": "conclusion", "title": "Write a conclusion block", "criterion": {"notebook": ["conclusion"], "min": 1}},
         {"id": "review", "title": "Review: which tests could still overturn it?", "criterion": {"review": True}}]},
    {"id": "produce-report", "level": "beginner", "title": "Produce a reproducible report",
     "objective": "Write up the investigation with its evidence links and export it with everything needed to check it.",
     "prerequisites": ["an analysis run"], "expected_outputs": ["notebook text", "report", "session package"],
     "evidence": ["notebook references resolved against the record", "PKG-1 inside the session package"],
     "tasks": [
         {"id": "question", "title": "Set a research question", "criterion": {"question": True}},
         {"id": "text", "title": "Write at least two notebook paragraphs or evidence links", "criterion": {"notebook": ["paragraph", "evidence", "measurement", "observation"], "min": 2}},
         {"id": "report", "title": "Export the report", "criterion": {"event": ["report.export"], "min": 1}},
         {"id": "package", "title": "Export the session package", "criterion": {"event": ["session.export"], "min": 1}},
         {"id": "review", "title": "Review the report for unsupported statements", "criterion": {"review": True}}]},
]


def task_done(task: dict, mission_state: dict, s: dict) -> bool:
    c = task["criterion"]
    since = mission_state.get("started_at") or ""
    if "event" in c:
        return sum(1 for h in s.get("history", []) if h["kind"] in c["event"] and h["at"] >= since) >= c.get("min", 1)
    if "question" in c:
        return bool((s.get("question") or {}).get("text", "").strip())
    if "runs" in c:
        return len(s.get("runs", [])) >= c["runs"]
    if "notebook" in c:
        return sum(1 for b in s.get("notebook", []) if b["type"] in c["notebook"]) >= c.get("min", 1)
    if "hypotheses_with_tests" in c:
        return sum(1 for h in s.get("hypotheses", []) if h.get("tests")) >= c["hypotheses_with_tests"]
    if "review" in c:
        return any(r["task_id"] == task["id"] and r["note"].strip() for r in mission_state.get("reviews", []))
    return False


def evaluate(s: dict) -> list[dict]:
    """Status of every mission in the session: per task done/open, and whether all are done."""
    by = {m["id"]: m for m in MISSIONS}
    out = []
    for ms in s.get("missions", []):
        m = by.get(ms["template_id"])
        if m is None:
            out.append({"template_id": ms["template_id"], "known": False, "tasks": [], "complete": False})
            continue
        tasks = [{"id": t["id"], "title": t["title"], "done": task_done(t, ms, s)} for t in m["tasks"]]
        out.append({"template_id": m["id"], "known": True, "tasks": tasks, "complete": all(t["done"] for t in tasks),
                    "n_done": sum(t["done"] for t in tasks), "n_tasks": len(tasks)})
    return out
