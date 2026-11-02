"""GATE-1: the discovery integrity gate, and DEBT-1: the research-debt detector.

Before an investigation is marked complete, the gate checks the record against eight stated requirements. Each is 'met',
'not met' or 'needs your action' (a requirement only the session can satisfy: a reproduction you ran, challenges you
examined). The gate is 'ready to mark complete' only when every requirement is met. Passing says that the conclusions are
stated within the evidence, reproducible here, with their uncertainties and limitations disclosed. It does not say they are
true, and a completed synthetic investigation is a completed software test.

  G1 conclusions supported      every claim has decided inputs (no KBOUND-1 item 'unsupported') and the compiler outcome is
                                not 'unsupported claim', 'incompatible', 'incomplete' or 'invalid provenance'
  G2 provenance intact          the record's content hash recomputes and SCI-COMP stage 8 (provenance) has no failure
  G3 reproducible               an independent reproduction (REPROX-1) gave 'exact' or 'numerically equivalent' (session or recorded)
  G4 uncertainties disclosed    every outcome states its sensitivity or uncertainty, and the non-propagated effects are listed
  G5 limitations documented     the investigation report passes INTEG-1 I8 and every outcome lists limitations
  G6 wording within evidence    no conclusion is worded beyond its KBOUND-1 region (ADV-1 Q8 has no open major challenge) and
                                the report passes INTEG-1 I12
  G7 challenges examined        every major or critical ADV-1 challenge is acknowledged or resolved in the session
  G8 synthetic labelled         a synthetic record is labelled synthetic in the report (INTEG-1 I1)

DEBT-1 lists research debt: shortcuts and gaps that do not stop completion but should be paid down, each with its source:
compiler warnings, testable assumptions never tested, stress modes not tested, methods with missing documentation or no defined
known-answer test, uncertainty effects never quantified, viable explanations with open tests, and questions without a method.
"""

from __future__ import annotations

from . import counterfactual as cf

METHOD = "GATE-1"
METHOD_DEBT = "DEBT-1"
REQUIREMENTS = [("G1", "Conclusions supported"), ("G2", "Provenance intact"), ("G3", "Reproducible"), ("G4", "Uncertainties disclosed"),
                ("G5", "Limitations documented"), ("G6", "Wording within the evidence"), ("G7", "Challenges examined"), ("G8", "Synthetic data labelled")]
STATES = ["met", "not met", "needs your action"]
FAILING_COMPILE = ("unsupported claim", "incompatible", "incomplete", "invalid provenance")
GOOD_REPRO = ("exact reproduction", "numerically equivalent reproduction")


def base(record: dict, rep: dict, led: dict, reproduction: dict | None = None) -> dict:
    """The gate from the record alone. `reproduction`: a recorded REPROX-1 result, when one exists. The browser overlays the
    session (reproductions you ran, challenge statuses) with the same rules (intelcore.overlayGate, parity-tested)."""
    outs = [o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])]
    checks = {c["id"]: c for c in rep["compile"]["checks"]}
    R = []

    def req(rid, state, detail, cites=None):
        R.append({"id": rid, "name": dict(REQUIREMENTS)[rid], "state": state, "detail": detail, "cites": (cites or [])[:10]})
    uns = [b["id"] for b in rep["boundary"]["items"] if b["kind"] == "claim" and b.get("status") == "unsupported"]
    co = rep["compile"]["outcome"]
    req("G1", "not met" if uns or co in FAILING_COMPILE else "met",
        (f"unsupported claims: {', '.join(uns)}; " if uns else "") + f"compiler outcome '{co}'", uns + ["SCICOMP-1"])
    hok = cf.record_hash(record) == record.get("content_hash")
    pf = [c["id"] for c in rep["compile"]["checks"] if c["stage"] == "provenance" and c["outcome"] == "fail"]
    req("G2", "met" if hok and not pf else "not met", ("record hash recomputes" if hok else "record hash does not recompute") +
        (f"; provenance checks failing: {', '.join(pf)}" if pf else ""), ["$.content_hash"] + pf)
    v = (reproduction or {}).get("verdict")
    req("G3", "met" if v in GOOD_REPRO else "not met" if v else "needs your action",
        f"recorded reproduction: {v}" if v else "no independent reproduction recorded for this run: run it in the Scientific Debugger", ["REPROX-1"])
    nosens = [o["question"] for o in outs if o["question"] != "data_quality" and not (o.get("sensitivity") or o.get("evidence"))]
    npg = rep["uflow"]["not_propagated"]
    req("G4", "met" if not nosens and npg is not None else "not met",
        (f"outcomes without a sensitivity statement: {', '.join(nosens)}; " if nosens else "every outcome states its sensitivity; ") +
        f"{len(npg)} non-propagated effect(s) listed", [f"claim:{q}" for q in nosens] + ["UFLOW-1"])
    rc = {c["id"]: c for c in rep["report_check"]["checks"]}
    nolim = [o["question"] for o in outs if not o.get("limitations")]
    i8 = rc.get("I8", {}).get("ok", False)
    req("G5", "met" if i8 and not nolim else "not met",
        ("the report mentions its limitations" if i8 else "the report never mentions its limitations") +
        (f"; outcomes without limitations: {', '.join(nolim)}" if nolim else ""), ["INTEG-1:I8"])
    q8 = [i for c in led["conclusions"] for q in c["questions"] if q["id"] == "Q8" for i in q["items"] if i["severity"] in ("major", "critical")]
    i12 = rc.get("I12", {}).get("ok", False)
    req("G6", "met" if i12 and not q8 else "needs your action" if i12 else "not met",
        ("the report asserts no overstated wording" if i12 else "the report asserts overstated wording") +
        (f"; {len(q8)} major Q8 challenge(s) to examine" if q8 else ""), [i["id"] for i in q8] + ["INTEG-1:I12"])
    major = [i for c in led["conclusions"] for q in c["questions"] for i in q["items"] if i["severity"] in ("major", "critical")]
    req("G7", "met" if not major else "needs your action", f"{len(major)} major or critical challenge(s) not yet examined" if major
        else "no major or critical challenge raised", [i["id"] for i in major])
    syn = record.get("parameters", {}).get("bundle_kind") == "synthetic"
    i1 = rc.get("I1", {}).get("ok", True)
    req("G8", "met" if (not syn or i1) else "not met", ("synthetic record, labelled in the report" if syn else "archive record") if i1 else
        "synthetic record not labelled in the report", ["INTEG-1:I1"])
    return _finish(record, R, syn)


def _finish(record, R, syn):
    ready = all(r["state"] == "met" for r in R)
    return {"method": METHOD, "record": record.get("content_hash") if record else None, "requirements": R, "states": STATES,
            "outcome": "ready to mark complete" if ready else "not ready", "synthetic": syn,
            "counts": {s: sum(r["state"] == s for r in R) for s in STATES},
            "meaning": ("Ready means the conclusions are stated within the evidence, reproducible here, and disclose their uncertainty and "
                        "limitations. It does not mean they are true." + (" On synthetic data, completion is a completed software test." if syn else ""))}


def overlay(gate: dict, led_overlaid: dict, session: dict | None) -> dict:
    """Session part: a reproduction you ran (debug entries) satisfies G3; challenge statuses satisfy G6/G7."""
    s = session or {}
    R = [dict(r) for r in gate["requirements"]]
    by = {r["id"]: r for r in R}
    if by["G3"]["state"] != "met":
        rx = [d for d in s.get("debug") or [] if isinstance(d, dict) and d.get("kind") == "reproduction" and (d.get("content_hash") or d.get("record")) == gate["record"]]
        good = [d for d in rx if d.get("verdict") in GOOD_REPRO]
        if good:
            by["G3"].update(state="met", detail=f"reproduction you ran: {good[-1]['verdict']}")
        elif rx:
            by["G3"].update(state="not met", detail=f"reproduction you ran: {rx[-1].get('verdict')}")
    items = {i["id"]: i for c in led_overlaid["conclusions"] for q in c["questions"] for i in q["items"]}
    for rid, pred in (("G7", lambda i: True), ("G6", lambda i: i["question_id"] == "Q8")):
        r = by[rid]
        if r["state"] == "needs your action":
            left = [c for c in r["cites"] if c in items and pred(items[c]) and items[c]["status"] == "open"]
            if not left:
                r.update(state="met", detail=r["detail"] + " — all examined in the session")
            else:
                r.update(detail=f"{len(left)} challenge(s) still open")
    return {**_finish({"content_hash": gate["record"]}, R, gate["synthetic"]), "record": gate["record"]}


def debt(record: dict, rep: dict, disc: dict) -> dict:
    items = []

    def add(kind, label, source, ref):
        items.append({"kind": kind, "label": str(label)[:300], "source": source, "ref": ref})
    for c in rep["compile"]["checks"]:
        if c["outcome"] == "warning":
            add("methodological shortcut", f"{c['id']}: {c['detail']}", "SCICOMP-1 warning", c["id"])
    for c in rep["blindspot"]["checks"]:
        if c["id"] == "assumptions" and c["state"] in ("not examined", "partially examined"):
            add("undocumented or untested assumption", c["detail"], "BLIND-1 assumptions", "BLIND-1:assumptions")
    for q, s in rep["stress"].items():
        for m in s["modes"]:
            if m["result"] == "not tested":
                add("missing validation", f"{q}: stress mode '{m['name']}' not tested ({m.get('detail')})", "CLAIMX-1 not tested", f"CLAIMX-1:{q}:{m['mode']}")
    for m in rep["genome"]["methods"]:
        if not m.get("used_in_run"):
            continue
        h = m["health"]
        if h["documentation_missing"]:
            add("incomplete documentation", f"{m['id']}: missing {', '.join(h['documentation_missing'])}", "METHOD-DNA-1 health", m["id"])
        if not h["n_defined"]:
            add("incomplete tests", f"{m['id']}: no known-answer test defined", "METHOD-DNA-1 health", m["id"])
    for k, row in enumerate((disc.get("uncertainty") or {}).get("unquantified", [])):
        add("unquantified uncertainty", row.get("name") if isinstance(row, dict) else row, "UNC-1 unquantified", f"UNC-1:{k}")
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q["hypotheses"]:
            ot = [t["id"] for t in h.get("tests", []) if t["status"] in ("untested", "evidence_unavailable", "not_tested")]
            if h.get("overall") in ("consistent so far", "inconclusive") and ot:
                add("open test", f"{h['id']} is viable with open tests {', '.join(ot)}", "HYPO-1", f"HYPO-1:{h['id']}")
    for qn in rep["questions"]["questions"]:
        if qn["category"] == "requires a new method":
            add("missing method", qn["question"], "QFORGE-1", qn["id"])
    kinds = sorted({i["kind"] for i in items})
    return {"method": METHOD_DEBT, "record": record.get("content_hash"), "items": items, "by_kind": {k: sum(i["kind"] == k for i in items) for k in kinds},
            "note": "Research debt does not block completion. Each item names the check that found it; the list covers those checks only."}
