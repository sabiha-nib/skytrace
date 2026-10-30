"""Discovery Radar (RADAR-1): investigation opportunities, each with its reason — not a detector of astronomical events.

Signals (fixed rules over the record, COMPAT-1, DQ-1, LEDGER-1 and HYPO-1 outputs):
  R1 significant pairs to inspect      matched pairs at or above the detection threshold (calibrated where possible)
  R2 unresolved explanations           explanations whose implemented tests are inconclusive
  R3 untestable explanations           explanations whose every test needs a method that is not implemented
                                       (a test that is implemented but not applicable here is not an opportunity)
  R4 unused measurements               usable measurements that are in no accepted pair
  R5 sensitivity not yet examined      STAB-1 not run for this target (the interface clears it once run)
  R6 evidence conflicts                LEDGER-1 contradictions
  R7 data-quality gaps                 DQ-1 checks whose outcome is invalid or not available
  R8 unobserved intervals              coverage gaps between visits (needs new observations)
  R9 provenance gaps                   LEDGER-1 completeness gaps other than expected ones
Ranking is explicit: items that can run now come first; then by signal order above; ties keep the record's order.
Every item states what it proposes, why, the evidence behind it, the data it needs, the action that would carry it out,
what it cannot establish, and whether it can run here and now.
"""

from __future__ import annotations

from .science.assess import T, pair_significance

METHOD = "RADAR-1"
ORDER = ["R1", "R6", "R2", "R5", "R7", "R4", "R3", "R9", "R8"]


def _item(sig, what, why, evidence, data_needed, action, cannot, runnable, run_note, refs=None):
    return {"signal": sig, "proposal": what, "why": why, "evidence": evidence, "data_needed": data_needed, "action": action,
            "cannot_establish": cannot, "can_run_now": runnable, "run_note": run_note, "refs": refs or []}


def scan(record: dict, compat: dict, quality: dict, ledger: dict, hyp: dict, network: bool | None = False) -> dict:
    items = []
    var = next((e["data"] for e in record.get("events", []) if e.get("step") == "variability"), {}) or {}
    scale = (var.get("calibration_check") or {}).get("error_scale")
    thr = T["variability_z"]
    sig = []
    for p in var.get("pairs", []):
        z, cal = pair_significance(p, scale)
        if z is not None and abs(z) >= thr:
            sig.append((abs(z), cal, p))
    sig.sort(key=lambda x: -x[0])
    for z, cal, p in sig[:8]:
        items.append(_item("R1", f"Inspect {p['a']} → {p['b']} in the Time Machine",
                           f"{'reference-calibrated' if cal else 'raw (uncalibrated)'} |z| = {z:.1f} ≥ {thr:g}",
                           [f"pair:{p['a']}|{p['b']}"], "the two stored images (present)", "inspect_pair",
                           "whether the change is astrophysical: inspection can reveal artefacts, it cannot confirm a cause",
                           True, "opens the pair; you record what you see", refs=[p["a"], p["b"]]))
    for c in ledger.get("contradictions", [])[:6]:
        items.append(_item("R6", f"Resolve the conflict: {c['kind']}", c["detail"], c["items"], "the recorded values (present)",
                           "inspect_ledger", "which side is right, by itself: it shows where the evidence disagrees", True,
                           "opens the contradiction inspector"))
    for q in hyp.get("questions", []):
        for h in q["hypotheses"]:
            tests = h["tests"]
            impl = [t for t in tests if t["status"] not in ("not_tested",)]
            unimpl = [t for t in tests if t["status"] == "not_tested" and str(t.get("rule", "")).startswith("needs ")]
            if impl and all(t["status"] in ("inconclusive", "evidence_unavailable") for t in impl):
                items.append(_item("R2", f"Gather evidence on {h['id']}: {h['statement']}",
                                   "its implemented tests are inconclusive: " + "; ".join(f"{t['id']} {t['detail']}" for t in impl)[:300],
                                   [f"hyp:{h['id']}"] + [t["id"] for t in impl], "what each test's rule needs (see the test detail)",
                                   "evaluate_hypotheses", "the explanation's truth: only whether recorded values meet the rule", True,
                                   "opens the explanation in the Hypothesis Arena"))
            elif not impl and unimpl and len(unimpl) == len(tests):
                items.append(_item("R3", f"{h['id']} cannot be tested with the implemented methods",
                                   "; ".join(t["rule"] for t in tests), [f"hyp:{h['id']}"], "a method that is not implemented (see the rule)",
                                   None, "anything about this explanation with current methods", False, "needs a new method"))
    used = set()
    for d in (next((e["data"] for e in record.get("events", []) if e.get("step") == "pairs"), {}) or {}).get("accepted", []):
        used.update((d["a"], d["b"]))
    unused = [o["key"] for o in compat.get("observations", []) if o.get("quality") == "ok" and o["key"] not in used]
    if unused:
        items.append(_item("R4", f"{len(unused)} usable measurement(s) have no wavelength-matched partner",
                           "they contribute to the motion fit but to no brightness comparison", unused[:10],
                           "a revisit that samples the same wavelength on the same detector", "acquire_data",
                           "brightness change at those wavelengths", bool(network), "needs network access to the archives" if not network else "",
                           refs=unused[:10]))
    items.append(_item("R5", "Check how sensitive the outcomes are to analysis choices",
                       "STAB-1 has not been run in this view", ["STAB-1"], "the bundle (present)", "run_stability",
                       "statistical uncertainty (sensitivity is a different quantity)", True, "re-runs the analysis six times"))
    for c in quality.get("checks", []):
        if c["outcome"] in ("invalid", "not_available"):
            n = c["counts"].get(c["outcome"], 0)
            items.append(_item("R7", f"Review data-quality check {c['id']}: {c['name']}",
                               f"{n} item(s) {quality['labels'][c['outcome']]} under: {c['rule']}", [c["id"]],
                               "depends on the check (see its items)", "check_quality", "whether the affected results are wrong — only that a rule flagged them",
                               True, "opens the check"))
    for det, cov in sorted(compat.get("coverage", {}).get("per_detector", {}).items()):
        if cov["gaps"]:
            g = max(cov["gaps"], key=lambda x: x["days"])
            items.append(_item("R8", f"D{det}: no observations for {g['days']:.0f} days after visit {g['after_visit'] + 1}",
                               f"{len(cov['gaps'])} gap(s) ≥ {compat['coverage']['gap_threshold_days']:g} days between visits", [f"D{det}"],
                               "new observations in the gap", "acquire_data", "anything about the source during the gap",
                               bool(network), "needs network access to the archives" if not network else ""))
            break
    gaps = [g for g in ledger.get("completeness", {}).get("gaps", []) if not g.get("expected")]
    if gaps:
        items.append(_item("R9", f"{len(gaps)} relationship gap(s) in the evidence ledger", "; ".join(sorted({g['kind'] for g in gaps})),
                           [g["id"] for g in gaps[:10]], "the missing links", "inspect_ledger", "the claims' validity", True, "opens the completeness view"))
    items.sort(key=lambda x: (not x["can_run_now"], ORDER.index(x["signal"])))
    for i, x in enumerate(items, 1):
        x["rank"] = i
        x["rank_reason"] = ("can run now" if x["can_run_now"] else "cannot run here") + f"; signal {x['signal']} (order {ORDER.index(x['signal']) + 1} of {len(ORDER)})"
        x["id"] = f"{x['signal']}-{i}"
    return {"method": METHOD, "content_hash": record.get("content_hash"), "items": items, "order": ORDER,
            "note": "research opportunities: suggestions for what to examine next, not detections"}
