"""Adversarial Science Laboratory (ASL-1): rule-based challenges to an investigation's own interpretation.

Each challenge names the issue, the recorded evidence that raised it, the rule that raised it, a severity class, why
it matters, how to verify it, and its status. A challenge is raised only when a stated rule fires on recorded
values; the laboratory never claims a flaw that a rule did not establish, and "open" means "not yet examined", not
"wrong". Severity is a fixed class of the rule, not a probability or a score:

  critical   recorded evidence contradicts something the claim relies on, or the record/inputs fail an integrity check
  major      the claim's outcome changes under a documented alternative (parameter, method, re-assessment), rests on
             a single evidence item, or a LEDGER-1 contradiction rule fires
  moderate   a competing explanation is still viable for a positive claim, or a method assumption is not verified
  note       a blind spot: something not yet examined, or a known gap that does not by itself weaken the claim

Modes: hypothesis challenger (H), method challenger (M), evidence challenger (E), reproducibility challenger (R),
alternative explanation explorer (A), blind-spot inspector (B), sensitivity (S), data quality (Q).
Status: open · acknowledged (you attached a note to the challenge in the session) · resolved by rule (only where a
rule can close it, e.g. a replay reproduced the content hash).
"""

from __future__ import annotations

METHOD = "ASL-1"
SEVERITY = ["critical", "major", "moderate", "note"]
MODES = {"H": "hypothesis challenger", "M": "method challenger", "E": "evidence challenger", "R": "reproducibility challenger",
         "A": "alternative explanation explorer", "B": "blind-spot inspector", "S": "sensitivity challenger", "Q": "data-quality challenger"}
POSITIVE = {"variability_candidate", "motion_detected", "motion_inconsistent"}
CLAIM_OWN = {"variability": "V-INTRINSIC", "motion": "M-CATALOGUE"}
ARTEFACTS = {"variability": ["V-CALIB", "V-ERRMODEL", "V-WAVELENGTH", "V-BLEND"],
             "motion": ["M-REGISTRATION", "M-PARALLAX", "M-REFS", "M-CHROMATIC", "M-STATIC"]}
OPEN = ("not_tested", "evidence_unavailable", "inconclusive", "incompatible")


def _ev(record):
    out = {}
    for e in record["events"]:
        out.setdefault(e["step"], e)
    return out


def _c(cid, mode, question, issue, evidence, rule, severity, why, verify, **extra):
    assert severity in SEVERITY and mode in MODES
    return {"id": cid, "mode": mode, "mode_name": MODES[mode], "question": question, "issue": issue, "evidence": evidence,
            "rule": rule, "severity": severity, "why": why, "verification": verify, "status": "open", **extra}


def challenges(record: dict, hyp: dict, quality: dict, ledger: dict, unc: dict | None = None, stability: dict | None = None,
               session: dict | None = None, replay: dict | None = None) -> dict:
    ev = _ev(record)
    outs = {o["question"]: o for o in ev["assess"]["data"]["outcomes"]}
    hq = {q["question"]: {h["id"]: h for h in q["hypotheses"]} for q in hyp["questions"]}
    out = []

    # H / A: competing explanations that remain viable for a positive claim
    for q, own in CLAIM_OWN.items():
        cat = (outs.get(q) or {}).get("category")
        hs = hq.get(q, {})
        for hid in ARTEFACTS[q]:
            h = hs.get(hid)
            if not h or h["overall"] == "contradicted" or (q == "motion" and hid == "M-STATIC"):
                continue
            open_tests = [t for t in h["tests"] if t["status"] in OPEN]
            if cat in POSITIVE:
                sev = "major" if h["overall"] == "consistent so far" else "moderate"
                out.append(_c(f"H-{hid}", "H", q, f"{hid} is not ruled out for the claim “{cat.replace('_', ' ')}”: {h['statement']}",
                              [f"HYPO-1 {hid}: {h['overall']}"] + [f"{t['id']}: {t['status']}" for t in h["tests"]],
                              "ASL H1: a competing explanation of a positive claim whose overall status is not ‘contradicted’", sev,
                              "A positive claim stays a candidate while a competing explanation fits the same values.",
                              "Run or obtain the open tests: " + ("; ".join(f"{t['id']} ({t['rule']})" for t in open_tests) or "none open — inspect the consistent test values")))
            if h["overall"] in ("consistent so far", "inconclusive", "untested"):
                out.append(_c(f"A-{hid}", "A", q, f"Alternative interpretation for your review: {h['statement']}",
                              [f"HYPO-1 {hid}: {h['overall']}"], "ASL A1: list every competing explanation whose status is not ‘contradicted’",
                              "note", "Labelled alternative for review; it is not a finding and not more likely than the claim.",
                              "Compare the explanation's tests in the Hypothesis Arena."))
        if cat and cat.startswith("no_") and cat.endswith("_at_sensitivity"):
            sens = (outs[q].get("sensitivity") or {}) or (outs[q].get("evidence") or {})
            out.append(_c(f"H-ABSENCE-{q}", "H", q, f"“{cat.replace('_', ' ')}” is limited by the data's sensitivity, not proof of absence",
                          [f"ASSESS-2 {q}: {cat}", f"sensitivity: {', '.join(f'{k} = {v}' for k, v in list(sens.items())[:2])}"],
                          "ASL H2: an absence outcome is bounded by its stated sensitivity", "note",
                          "An effect smaller than the sensitivity would give the same result.",
                          "State the sensitivity with the result; more epochs or a longer baseline would lower it."))
    # contradicted tests inside the claim's own hypothesis
    for q, own in CLAIM_OWN.items():
        h = hq.get(q, {}).get(own)
        cat = (outs.get(q) or {}).get("category")
        if h and cat in POSITIVE and h["overall"] == "contradicted":
            bad = [t for t in h["tests"] if t["status"] == "contradicted"]
            out.append(_c(f"H-OWN-{q}", "H", q, f"The explanation the claim relies on ({own}) has a contradicted test",
                          [f"{t['id']}: {t['detail']}" for t in bad], "ASL H3: a contradicted test on the claim's own explanation",
                          "critical", "The recorded values disagree with what the claim predicts.", "Inspect the contradicted test's values."))

    # M: method assumptions
    var = (ev.get("variability") or {}).get("data") or {}
    cal = var.get("calibration_check") or {}
    if (cal.get("error_scale") or 0) > 1.5:
        out.append(_c("M-CALCHECK", "M", "variability", f"Reference stars scatter {cal['error_scale']:.2f}× their stated errors",
                      [f"CALCHECK-1 error_scale = {cal['error_scale']:.3f}", f"n_ref_z = {cal.get('n_ref_z')}"],
                      "ASL M1: CALCHECK-1 scale > 1.5 means the per-pixel error model underestimates the scatter", "moderate",
                      "Significances are divided by the scale on average; individual pairs may still be mis-scaled.",
                      "Run the error-scale counterfactual (CF-1) and the robustness experiment."))
    dq = {c["id"]: c for c in quality.get("checks", [])}
    if dq.get("DQ-CAL", {}).get("outcome") in ("not_available", "invalid", "incompatible"):
        out.append(_c("M-PAIRDIFF2", "M", "variability", "Some compared pairs lack the ≥ 3 matched reference stars PAIRDIFF-2 needs",
                      [f"DQ-CAL: {dq['DQ-CAL']['outcome']}", f"counts: {dq['DQ-CAL'].get('counts')}"],
                      "ASL M2: PAIRDIFF-2 assumes ≥ 3 wavelength-matched references per pair", "moderate",
                      "Uncalibrated pairs cannot separate a calibration change from a brightness change.",
                      "Check which pairs are calibrated (Evidence Ledger → claims); compare methods (CF-1 method scenario)."))
    a = ev.get("astrometry") or {}
    if a.get("status") == "ok" and (a["data"].get("fit_kind") == "exposure"):
        out.append(_c("M-EPOCHFIT", "M", "motion", "The motion fit used single exposures, not visit averages",
                      ["astrometry fit_kind = exposure"], "ASL M3: LINFIT-EPOCH-1 needs ≥ 2 visits; the per-exposure fit ignores correlated errors within a visit",
                      "moderate", "Errors correlated within one visit are not captured.", "Obtain a second visit separated by more than epoch_gap_days."))
    if record.get("parameters", {}).get("apply_parallax") is False:
        out.append(_c("M-PARALLAX-OFF", "M", "motion", "Parallax was not modelled in this run",
                      ["parameters.apply_parallax = false"], "ASL M4: a run with apply_parallax = false", "moderate",
                      "Annual parallax can bias a motion measured over a short baseline.", "Re-run with parallax applied (CF-1 parameter scenario)."))

    # E: evidence
    for cl in ledger.get("claims", []):
        for j, f in enumerate(cl.get("flags", [])):
            absence = "absence" in f
            out.append(_c(f"E-{cl['id'].split(':')[-1]}-{j + 1}", "E", cl.get("question", ""), f"{cl['id']}: {f}",
                          [f"support: {cl['support'].get('direct')} direct item(s), {cl['support'].get('comparisons')} comparison(s)"],
                          "ASL E3: LEDGER-1 absence flag" if absence else "ASL E1: LEDGER-1 flag on a claim", "note" if absence else "major",
                          "An absence is a statement about sensitivity, not positive evidence." if absence else "A claim on one item fails if that item is wrong.",
                          "State the sensitivity with the claim." if absence else "Find an independent item (another detector or epoch) that bears on the claim."))
    for i, x in enumerate(ledger.get("contradictions", [])):
        out.append(_c(f"E-{x['rule']}-{i + 1:02d}", "E", "variability" if x["rule"] in ("C1", "C4") else "motion",
                      f"{x['kind']}: {x['detail']}", x.get("items", [])[:4], f"ASL E2: LEDGER-1 rule {x['rule']}", "major",
                      x.get("meaning", "The evidence disagrees with itself."), "Inspect both items in the Time Machine and the Evidence Ledger."))

    # Q: data quality
    for c in quality.get("checks", []):
        if c["outcome"] == "invalid" and c["id"] in ("DQ-RECORD", "DQ-FILES"):
            out.append(_c(f"Q-{c['id']}", "Q", "", f"{c['name']}: invalid", [c["rule"]], "ASL Q1: an integrity check failed", "critical",
                          "Results cannot be trusted if their inputs changed.", "Re-verify the bundle and re-run."))
        elif c["outcome"] in ("invalid", "incompatible"):
            out.append(_c(f"Q-{c['id']}", "Q", "", f"{c['name']}: {c['outcome']}", [c["rule"], f"counts: {c.get('counts')}"],
                          "ASL Q2: a DQ-1 check is invalid or incompatible", "moderate",
                          "Affected observations are excluded or limited; check they are not the ones the claim depends on.",
                          "Open Data Quality and the affected observations."))

    # S: sensitivity (stability run, if recorded)
    if stability:
        base = (stability.get("base") or {}).get("categories") or {}
        for r in stability.get("runs", []):
            diff = {q: (base.get(q), c) for q, c in (r.get("categories") or {}).items() if base.get(q) != c}
            for q, (b0, b1) in diff.items():
                out.append(_c(f"S-{q}-{r.get('label', '')[:24]}", "S", q, f"{q}: {b0} → {b1} under “{r.get('label')}”",
                              [f"STAB-1 run {r.get('label')}"], "ASL S1: an outcome category changes under a STAB-1 perturbation", "major",
                              "The conclusion depends on an analysis choice.", "Report the dependence; examine the choice with CF-1."))
    else:
        out.append(_c("B-STABILITY", "B", "", "Sensitivity to analysis choices has not been examined",
                      ["no STAB-1 result for this run"], "ASL B1: no stability result recorded", "note",
                      "An outcome that flips under small changes is fragile.", "Run the stability check (Lab → Re-run) or a CF-1 parameter scenario."))

    # B: blind spots
    examined = set((session or {}).get("examined", []))
    scale = cal.get("error_scale")
    from .science.assess import T, pair_significance
    sig = [p for p in var.get("pairs", []) if (pair_significance(p, scale)[0] or 0) >= T["variability_z"] or abs(p.get("z") or 0) >= T["variability_z"]]
    unexamined = [p for p in sig if f"{p['a']}|{p['b']}" not in examined and f"{p['b']}|{p['a']}" not in examined]
    if unexamined:
        out.append(_c("B-PAIRS", "B", "variability", f"{len(unexamined)} significant pair(s) not yet inspected by eye in this session",
                      [f"{p['a']} → {p['b']}" for p in unexamined[:5]], "ASL B2: significant pairs absent from the session's examined list",
                      "note", "Artefacts (cosmic rays, edges, neighbours) are often visible in the images.", "Open each pair in the Time Machine.",
                      pairs=[f"{p['a']}|{p['b']}" for p in sig]))
    for u in (unc or {}).get("unquantified", [])[:6]:
        name = u.get("effect") or u.get("name") or str(u)[:80]
        out.append(_c("B-UNQ-" + "".join(ch for ch in name.upper() if ch.isalnum())[:16], "B", "", f"Unquantified effect: {name}", [u.get("why") or u.get("detail") or "UNC-1 lists it as not quantified"],
                      "ASL B3: UNC-1 unquantified component", "note", "It is not included in any stated uncertainty.", u.get("would_need") or "A model of the effect."))
    sel = (ev.get("discover") or {}).get("data", {})
    if sel.get("n_excluded"):
        out.append(_c("B-SELECTION", "B", "", f"{sel['n_excluded']} of {sel.get('n_total')} archive images were excluded at selection",
                      [f"selection criteria: {sel.get('criteria', {}).get('criteria') if isinstance(sel.get('criteria'), dict) else sel.get('criteria')}"],
                      "ASL B4: observations excluded by selection (possible selection effect)", "note",
                      "If exclusions depend on the target's position or brightness, the remaining sample may be biased.",
                      "Check the exclusion reasons (Data Quality → checks; Sky Explorer → rejected)."))

    # R: reproducibility
    if replay is None:
        out.append(_c("R-REPLAY", "R", "", "The result has not been reproduced by re-execution here",
                      ["no replay recorded"], "ASL R1: no PROVCHECK-1 determinism check for this run", "note",
                      "A result that cannot be re-run cannot be checked.", "Run the Reproducibility Challenge (server)."))
    else:
        det = next((c for c in replay.get("checks", []) if c["id"] == "determinism"), None)
        c = _c("R-REPLAY", "R", "", "Replay of the analysis", [det["detail"] if det else "no determinism check"],
               "ASL R1: PROVCHECK-1 determinism", "critical" if det and not det["ok"] else "note",
               "A replay that differs means the result depends on something not recorded.", "Compare software versions and inputs.")
        if det and det["ok"]:
            c["status"] = "resolved by rule"
        out.append(c)

    notes = {}
    for a_ in (session or {}).get("annotations", []):
        t = a_.get("target") or {}
        if t.get("kind") == "challenge":
            notes.setdefault(t.get("id"), []).append(a_.get("text", ""))
    for c in out:
        if c["id"] in notes and c["status"] == "open":
            c["status"], c["notes"] = "acknowledged", notes[c["id"]]
    out.sort(key=lambda c: (SEVERITY.index(c["severity"]), c["mode"], c["id"]))
    counts = {s: sum(c["severity"] == s for c in out) for s in SEVERITY}
    return {"method": METHOD, "content_hash": record.get("content_hash"), "challenges": out, "counts": counts,
            "severity_rule": __doc__.split("Modes:")[0].split("probability or a score:")[1].strip(),
            "note": "Open challenges are things to examine, not established flaws. Severity classes are fixed per rule; they are not scores."}
