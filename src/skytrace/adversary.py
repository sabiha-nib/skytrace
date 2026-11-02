"""ADV-1: the scientific adversary — a challenge ledger for each conclusion, organised by the eight questions of the Phase 9 brief.

The adversary does not invent objections. Every entry is a challenge that a stated rule raised on recorded values: an ASL-1
rule, a CLAIMX-1 stress mode that warned or failed, a viable HYPO-1 explanation, or one of the two selection rules below.
When no rule raises anything under a question, the ledger says so ("no challenge raised by the defined rules"); that is not
a statement that the question has no answer.

Questions and where their challenges come from:
  Q1 contradicting evidence      ASL E1–E3, H3; CLAIMX 'provenance' or 'sufficiency' failures that cite contradictions
  Q2 unsupported assumptions     ASL M2–M4; CLAIMX 'method' and 'compatibility'; BLIND-1 testable assumptions not tested
  Q3 alternative explanations    ASL H1/A1 for explanations that are not instrumental; CLAIMX 'alternatives'; HYPO-1 explanations
                                 still viable or untested
  Q4 instrumental artefact       ASL H1/A1 for instrumental explanations (calibration, wavelength, blending, registration,
                                 reference frame, chromatic offsets), ASL Q1–Q2, CLAIMX 'measurement'
  Q5 sample bias                 ASL B2, B4; rule X1 below
  Q6 parameter sensitivity       ASL S1, B1; CLAIMX 'sensitivity'
  Q7 underestimated uncertainty  ASL M1, B3; HYPO-1 V-ERRMODEL when not contradicted; CLAIMX 'statistics'
  Q8 claim exceeds the data      ASL H2; CLAIMX 'wording'; rule X2 below
  other                          ASL R1 and CLAIMX 'reproducibility' (reproducibility is checked by the debugger)

Extra rules:
  X1 a conclusion rests on observations from fewer than half of the detectors the bundle covers (selection by detector)
  X2 a positive outcome category whose claim is not in KBOUND-1's 'established' region

Severity: ASL challenges keep their rule's fixed class; CLAIMX 'fail' → major, 'warning' → moderate; X1 moderate; X2 major;
an alternative or instrumental explanation that is viable or untested → moderate. Resolution status is open until you act in the session:
acknowledged (a note) or resolved (only with a reference to a recorded item: a test, a reproduction, an experiment).
"""

from __future__ import annotations

from . import adversarial as asl

METHOD = "ADV-1"
QUESTIONS = [("Q1", "What evidence contradicts this conclusion?"), ("Q2", "Which assumptions are unsupported?"),
             ("Q3", "Which alternative explanations remain?"), ("Q4", "Could an instrumental artefact explain the signal?"),
             ("Q5", "Is the sample biased?"), ("Q6", "Is the analysis sensitive to parameter choices?"),
             ("Q7", "Is the uncertainty underestimated?"), ("Q8", "Does the conclusion exceed what the data supports?"),
             ("other", "Other rule-raised challenges")]
STATUSES = ["open", "acknowledged", "resolved"]
INSTRUMENTAL = {"V-CALIB", "V-WAVELENGTH", "V-BLEND", "M-REGISTRATION", "M-REFS", "M-CHROMATIC"}
ASL_Q = {"E1": "Q1", "E2": "Q1", "E3": "Q1", "H3": "Q1", "M2": "Q2", "M3": "Q2", "M4": "Q2", "Q1": "Q4", "Q2": "Q4",
         "B2": "Q5", "B4": "Q5", "S1": "Q6", "B1": "Q6", "M1": "Q7", "B3": "Q7", "H2": "Q8", "R1": "other"}
CX_Q = {"compatibility": "Q2", "method": "Q2", "alternatives": "Q3", "measurement": "Q4", "sensitivity": "Q6", "statistics": "Q7",
        "wording": "Q8", "provenance": "Q1", "sufficiency": "Q1", "reproducibility": "other"}
CX_SEV = {"fail": "major", "warning": "moderate"}
DEFAULT_TEST = {"Q1": "Inspect the contradicting items in the Evidence Ledger and Time Machine; decide whether a recorded test explains them.",
                "Q2": "Run the method's precondition check or a sensitivity experiment that varies the assumption.",
                "Q3": "Run the open tests of the competing explanation (Hypothesis Arena) or plan the observation that separates them (Observation Oracle).",
                "Q4": "Check the instrumental explanation's open tests; compare detectors and wavelength-matched pairs; inspect registration diagnostics.",
                "Q5": "Re-run with the excluded observations reviewed, or test whether the outcome holds per detector.",
                "Q6": "Run the stability check and a threshold counterfactual; record whether the category changes.",
                "Q7": "Compare the error scale on reference stars (CALCHECK-1) and re-assess with scaled errors (Counterfactual Lab).",
                "Q8": "Reword the conclusion to the KBOUND-1 region it occupies; check the text with the Integrity Firewall.",
                "other": "Run the independent reproduction in the Scientific Debugger."}


def _asl_rule(c: dict) -> str:
    r = str(c.get("rule", ""))
    return r.split(":")[0].replace("ASL", "").strip() if r.startswith("ASL") else r


def ledger(record: dict, rep: dict, frontier: dict, disc: dict) -> dict:
    """rep: epistemic report; frontier: frontier report (ASL-1); disc: DISC-1 (hypotheses)."""
    outs = {o["question"]: o for e in record["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}
    hyp = {q["question"]: q for q in (disc.get("hypotheses") or {}).get("questions", [])}
    bnd = {b["id"]: b for b in rep["boundary"]["items"]}
    det_bundle = sorted({n.get("detector") for n in rep["graph"]["nodes"] if n["kind"] == "observation" and n.get("detector") is not None})
    conclusions = []
    for q in ("variability", "motion", "data_quality"):
        if q not in outs:
            continue
        cid = f"claim:{q}"
        items = []

        def add(question, objection, rationale, evidence, severity, rule, follow_up, source):
            items.append({"id": f"{q}:{source}:{len(items)}", "question_id": question, "objection": objection, "rationale": rationale,
                          "evidence": [str(e) for e in (evidence or [])][:8], "severity": severity, "rule": rule, "status": "open",
                          "follow_up": follow_up or DEFAULT_TEST[question], "source": source})
        for c in frontier.get("asl", {}).get("challenges", []):
            if c.get("question") not in (q, None):
                continue
            r = _asl_rule(c)
            cid0 = str(c.get("id", ""))
            hid = cid0.split("-", 1)[1] if cid0[:2] in ("H-", "A-") else None
            if r in ("H1", "A1"):
                if hid == "V-ERRMODEL":
                    qq = "Q7"
                elif hid in INSTRUMENTAL:
                    qq = "Q4"
                else:
                    qq = "Q3"
            else:
                qq = ASL_Q.get(r, "other")
            add(qq, c.get("issue"), c.get("why"), c.get("evidence"), c.get("severity", "note"), c.get("rule"), c.get("verification"), f"ASL:{c['id']}")
        for m in rep["stress"].get(q, {}).get("modes", []):
            if m["result"] in ("fail", "warning"):
                add(CX_Q.get(m["mode"], "other"), f"{m['name']}: {m.get('detail') or m['result']}", m.get("rule"), m.get("cites"),
                    CX_SEV[m["result"]], f"CLAIMX-1 {m['mode']} ({m['result']})", None, f"CLAIMX:{m['mode']}")
        for h in (hyp.get(q) or {}).get("hypotheses", []):
            if h["id"] in (asl.CLAIM_OWN.get(q),) or h.get("overall") in ("contradicted",):
                continue
            already = any(h["id"] in (it["objection"] or "") or h["id"] in " ".join(it["evidence"]) for it in items)
            if already or h.get("overall") not in ("consistent so far", "inconclusive", "untested"):
                continue
            qq = "Q7" if h["id"] == "V-ERRMODEL" else "Q4" if h["id"] in INSTRUMENTAL else "Q3"
            open_t = [t["id"] for t in h.get("tests", []) if t["status"] != "consistent"]
            verb = "has not been tested" if h["overall"] == "untested" else "remains viable"
            add(qq, f"{h['id']} {verb}: {h['statement']}", f"HYPO-1 overall '{h['overall']}'" + (f" ({h['overall_rule']})" if h.get("overall_rule") else ""),
                [f"HYPO-1:{h['id']}"] + open_t, "moderate", "HYPO-1 explanation not ruled out", None, f"HYPO:{h['id']}")
        used = sorted({n.get("detector") for nid in _upstream(rep, cid) for n in [_node(rep, nid)] if n and n["kind"] == "observation" and n.get("detector") is not None})
        if q != "data_quality" and det_bundle and used and len(used) * 2 < len(det_bundle):
            add("Q5", f"the conclusion rests on detectors {', '.join(f'D{d}' for d in used)} of the {len(det_bundle)} the bundle covers",
                "a result seen on few detectors can reflect a detector-specific effect or selection", [f"D{d}" for d in used], "moderate",
                "ADV X1: fewer than half of the bundle's detectors", None, "X1")
        o = outs[q]
        b = bnd.get(cid, {})
        if o.get("category") in asl.POSITIVE and b.get("region") != "established":
            add("Q8", f"the outcome '{o['category']}' is positive but its claim sits in '{b.get('region')}'",
                f"KBOUND-1 {b.get('rule')}: {b.get('why')}", [cid], "major", "ADV X2: positive outcome not established", None, "X2")
        by_q = []
        for qid, text in QUESTIONS:
            xs = [i for i in items if i["question_id"] == qid]
            by_q.append({"id": qid, "question": text, "items": xs, "raised": bool(xs),
                         "note": None if xs else "no challenge raised by the defined rules"})
        conclusions.append({"claim": cid, "question": q, "category": o.get("category"), "region": b.get("region"), "statement": o.get("statement"),
                            "questions": by_q, "n": len(items), "by_severity": {s: sum(i["severity"] == s for i in items) for s in asl.SEVERITY}})
    return {"method": METHOD, "record": record.get("content_hash"), "questions": QUESTIONS, "statuses": STATUSES, "conclusions": conclusions,
            "note": "Every entry was raised by a stated rule on recorded values. A question with no entry has no rule-raised challenge; it is not "
                    "thereby answered. 'Open' means not yet examined, not 'wrong'."}


def _node(rep, nid):
    for n in rep["graph"]["nodes"]:
        if n["id"] == nid:
            return n
    return None


def _upstream(rep, cid):
    from . import epistemic as epi
    return [x["id"] for x in epi.trace(rep["graph"], cid, "back")["nodes"]]


def overlay(led: dict, session: dict | None) -> dict:
    """Apply the session's resolution statuses: {challenge id: {status, note, ref, at}}. 'resolved' needs a reference."""
    marks = {}
    for m in (session or {}).get("challenges") or []:
        if isinstance(m, dict) and m.get("id") and m.get("status") in STATUSES:
            if m["status"] == "resolved" and not m.get("ref"):
                continue
            marks[m["id"]] = m
    out = {**led, "conclusions": []}
    for c in led["conclusions"]:
        qs = []
        for q in c["questions"]:
            items = [{**i, "status": marks[i["id"]]["status"], "note": marks[i["id"]].get("note"), "resolved_by": marks[i["id"]].get("ref")}
                     if i["id"] in marks else i for i in q["items"]]
            qs.append({**q, "items": items})
        allx = [i for q in qs for i in q["items"]]
        out["conclusions"].append({**c, "questions": qs, "by_status": {s: sum(i["status"] == s for i in allx) for s in STATUSES}})
    return out
