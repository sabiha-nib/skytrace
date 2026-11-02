"""DGENOME-1: the discovery genome — how a candidate result developed, field by field, each field traced to where it is recorded.

A genome is built for each of a run's two scientific questions (brightness change and motion), whatever the outcome: a
null result has a genome too. Thirteen fields, as the Phase 9 brief lists them:

  original_observation, data_source, measurement_characteristics, initial_anomaly, detection_method, candidate_explanations,
  rejected_explanations, supporting_evidence, contradictory_evidence, uncertainty_structure, validation_procedures,
  final_interpretation, remaining_unknowns

Each field is read from the record (through the EPI-1 graph and its backward trace from the claim), HYPO-1, LEDGER-1
contradictions, UFLOW-1, CLAIMX-1, KBOUND-1, QFORGE-1 and BLIND-1, and cites the graph objects or record paths it used.

compare() sets two genomes side by side under stated rules: shared observational characteristics (detector overlap, wavelength
overlap, baselines within a factor of 1.25, the same data-source kind), different interpretations (category and boundary region),
similar methodological weaknesses (stress modes that warn or fail in both), related evidence patterns (the same competing
explanations with the same HYPO-1 status; contradictions present in both), different uncertainty structures (propagated and
non-propagated categories), and potentially reusable methods (a method one genome used whose pipeline step the other record also
ran). Matching fields say the investigations share structure. They are not evidence that the sources are physically alike, and no
similarity score is computed.
"""

from __future__ import annotations

from . import epistemic as epi

METHOD = "DGENOME-1"
FIELDS = ["original_observation", "data_source", "measurement_characteristics", "initial_anomaly", "detection_method", "candidate_explanations",
          "rejected_explanations", "supporting_evidence", "contradictory_evidence", "uncertainty_structure", "validation_procedures",
          "final_interpretation", "remaining_unknowns"]
QUESTIONS = ("variability", "motion")
UNC_NODES = {"variability": ["u:variance", "u:flux", "u:pair", "u:scale", "u:zcal", "u:out:variability"],
             "motion": ["u:variance", "u:centroid", "u:position", "u:visit", "u:pm", "u:out:motion"]}
NOTPROP = {"variability": ("WLMATCH-2", "PAIRDIFF", "CALCHECK", "APPHOT"), "motion": ("EPHEM", "LINFIT", "DIFFAST", "CENTROID", "REFSEL")}
BASELINE_FACTOR = 1.25
NOTE = ("Fields that match say two investigations share structure: data, methods, weaknesses or uncertainty treatment. They are not "
        "evidence that the sources are physically alike, and no similarity score is computed.")


def _med(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def genome(record: dict, rep: dict, hypotheses: dict, q: str) -> dict:
    """rep: the epistemic report of the record; hypotheses: HYPO-1 (DISC-1's 'hypotheses')."""
    G = rep["graph"]
    by = {n["id"]: n for n in G["nodes"]}
    cid = f"claim:{q}"
    if cid not in by:
        return {"method": METHOD, "question": q, "available": False, "why": "this run has no claim for the question"}
    up = {x["id"] for x in epi.trace(G, cid, "back")["nodes"]}
    obs = sorted((by[i] for i in up if by[i]["kind"] == "observation" and not by[i].get("excluded")), key=lambda n: (n.get("mjd") or 0, n["id"]))
    meas = [by[i] for i in up if by[i]["kind"] == "measurement"]
    p = record.get("parameters", {})
    synthetic = p.get("bundle_kind") == "synthetic"
    lam = [m.get("wavelength_um") for m in meas if m.get("wavelength_um") is not None]
    if not lam:                                   # wavelengths sit on the measure events
        ev = record["events"]
        lam = [ev[m["event"]]["data"].get("wavelength_um") for m in meas if isinstance(m.get("event"), int)]
        lam = [x for x in lam if isinstance(x, (int, float))]
    mjd = [o["mjd"] for o in obs if isinstance(o.get("mjd"), (int, float))]
    flux = [m.get("flux_ujy") for m in meas]
    frac = [m["flux_err_ujy"] / m["flux_ujy"] for m in meas if m.get("flux_ujy") and m.get("flux_err_ujy")]
    epochs = [i for i in up if i.startswith("epoch:")]
    hq = next((x for x in hypotheses.get("questions", []) if x["question"] == q), {"hypotheses": [], "outcome": None})
    cand = [{"id": h["id"], "statement": h["statement"], "status": h.get("overall")} for h in hq["hypotheses"]]
    claim = by[cid]
    bnd = next((b for b in rep["boundary"]["items"] if b["id"] == cid), {})
    stress = rep["stress"].get(q, {"modes": []})
    con = [e["source"] for e in G["edges"] if e["target"] == cid and e["rel"] == "contradicts"]
    unc = [n for n in rep["uflow"]["nodes"] if n["id"] in UNC_NODES[q]]
    notp = [x for x in rep["uflow"]["not_propagated"] if any(x["step"].startswith(s) for s in NOTPROP[q])]
    qf = [x for x in rep["questions"]["questions"] if x["category"] != "directly answerable" and q.split("_")[0] in (x["question"] + x["id"]).lower()]
    blind = [c for c in rep["blindspot"]["checks"] if c["state"] in ("not examined", "partially examined")]
    methods = sorted(i[7:] for i in up if i.startswith("method:"))
    thresholds = sorted(by[i]["label"] for i in up if i.startswith("asm:threshold:"))
    f = {
        "original_observation": {"value": (f"{obs[0]['id'][4:]} (D{obs[0].get('detector')}, MJD {obs[0].get('mjd')})" if obs else None),
                                 "n_observations": len(obs), "cites": [obs[0]["id"]] if obs else []},
        "data_source": {"value": f"{'synthetic bundle' if synthetic else 'SPHEREx archive bundle'} {p.get('bundle')}", "kind": "synthetic" if synthetic else "archive",
                        "manifest_sha256": p.get("bundle_manifest_sha256"), "cites": ["$.parameters.bundle_manifest_sha256"]},
        "measurement_characteristics": {"detectors": sorted({o.get("detector") for o in obs if o.get("detector") is not None}),
                                        "wavelength_um": [round(min(lam), 4), round(max(lam), 4)] if lam else None, "n_measurements": len(meas),
                                        "n_visits": len(epochs) or None, "baseline_days": round(max(mjd) - min(mjd), 2) if len(mjd) > 1 else None,
                                        "median_flux_ujy": _med(flux), "median_fractional_error": _med(frac), "cites": sorted(i for i in up if i.startswith("meas:"))[:5]},
        "initial_anomaly": {"value": claim["label"], "category": claim.get("category"), "cites": [cid]},
        "detection_method": {"methods": methods, "thresholds": thresholds, "cites": [f"method:{m}" for m in methods]},
        "candidate_explanations": {"items": cand, "cites": [f"hyp:{h['id']}" for h in cand]},
        "rejected_explanations": {"items": [h for h in cand if h["status"] == "contradicted"],
                                  "note": "rejected by a stated HYPO-1 rule on recorded values, not disproved"},
        "supporting_evidence": {"inferences": sorted(i for i in up if i.startswith("inf:")), "n_comparisons": sum(i.startswith("pair:") for i in up),
                                "fit": "fit:motion" in up, "cites": sorted(i for i in up if i.startswith(("inf:", "fit:")))},
        "contradictory_evidence": {"items": [{"id": c, "label": by[c]["label"], "rule": by[c].get("ledger_rule")} for c in con], "cites": con},
        "uncertainty_structure": {"propagated": [{"id": n["id"], "quantity": n["quantity"], "unit": n["unit"], "propagation": n["propagation"]} for n in unc],
                                  "not_propagated": notp, "cites": [n["id"] for n in unc]},
        "validation_procedures": {"stress": [{"mode": m["mode"], "result": m["result"]} for m in stress["modes"]],
                                  "compiler_outcome": rep["compile"]["outcome"], "reproduction": "not in the record (run the independent reproduction)",
                                  "cites": [f"CLAIMX-1:{q}", "SCICOMP-1"]},
        "final_interpretation": {"value": claim["label"], "category": claim.get("category"), "region": bnd.get("region"), "region_rule": bnd.get("rule"),
                                 "status": claim.get("status"), "cites": [cid]},
        "remaining_unknowns": {"could_change_it": bnd.get("could_change_it") or [], "open_questions": [x["question"] for x in qf][:8],
                               "blindspots": [c["name"] for c in blind], "cites": [x["id"] for x in qf][:8]},
    }
    return {"method": METHOD, "question": q, "available": True, "record": record.get("content_hash"), "target": record.get("target"), "fields": f,
            "field_order": FIELDS, "synthetic": synthetic}


def genomes(record: dict, rep: dict, hypotheses: dict) -> list[dict]:
    return [genome(record, rep, hypotheses, q) for q in QUESTIONS]


def _overlap(a, b):
    if not a or not b:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return [round(lo, 4), round(hi, 4)] if lo <= hi else None


def compare(ga: dict, gb: dict, steps_b: set | None = None, steps_a: set | None = None) -> dict:
    """steps_a / steps_b: the pipeline steps each record ran (for reusable methods)."""
    if not (ga.get("available") and gb.get("available")):
        return {"method": METHOD, "available": False, "why": "both genomes must exist"}
    A, B = ga["fields"], gb["fields"]
    ma, mb = A["measurement_characteristics"], B["measurement_characteristics"]
    shared = []
    dets = sorted(set(ma["detectors"]) & set(mb["detectors"]))
    shared.append({"field": "detectors", "a": ma["detectors"], "b": mb["detectors"], "shared": dets, "rule": "detectors used by both", "match": bool(dets)})
    wo = _overlap(ma["wavelength_um"], mb["wavelength_um"])
    shared.append({"field": "wavelength coverage (µm)", "a": ma["wavelength_um"], "b": mb["wavelength_um"], "shared": wo, "rule": "intervals overlap", "match": wo is not None})
    ba, bb = ma["baseline_days"], mb["baseline_days"]
    close = bool(ba and bb and max(ba, bb) / min(ba, bb) <= BASELINE_FACTOR)
    shared.append({"field": "baseline (days)", "a": ba, "b": bb, "rule": f"within a factor of {BASELINE_FACTOR}", "match": close})
    shared.append({"field": "data source", "a": A["data_source"]["kind"], "b": B["data_source"]["kind"], "rule": "same kind (archive or synthetic)",
                   "match": A["data_source"]["kind"] == B["data_source"]["kind"]})
    ia, ib = A["final_interpretation"], B["final_interpretation"]
    weak_a = {s["mode"] for s in A["validation_procedures"]["stress"] if s["result"] in ("warning", "fail")}
    weak_b = {s["mode"] for s in B["validation_procedures"]["stress"] if s["result"] in ("warning", "fail")}
    ca = {h["id"]: h["status"] for h in A["candidate_explanations"]["items"]}
    cb = {h["id"]: h["status"] for h in B["candidate_explanations"]["items"]}
    same_expl = sorted(k for k in set(ca) & set(cb) if ca[k] == cb[k])
    pa = {n["id"] for n in A["uncertainty_structure"]["propagated"]}
    pb = {n["id"] for n in B["uncertainty_structure"]["propagated"]}
    na = {x["step"] + ": " + x["what"] for x in A["uncertainty_structure"]["not_propagated"]}
    nb = {x["step"] + ": " + x["what"] for x in B["uncertainty_structure"]["not_propagated"]}
    reuse = []
    for m in A["detection_method"]["methods"]:
        if m not in B["detection_method"]["methods"]:
            step = next((s for s, ms in epi.STEP_METHODS.items() if m in ms), None)
            reuse.append({"method": m, "from": "a", "inputs_recorded_in_other": bool(step and steps_b and step in steps_b), "step": step})
    for m in B["detection_method"]["methods"]:
        if m not in A["detection_method"]["methods"]:
            step = next((s for s, ms in epi.STEP_METHODS.items() if m in ms), None)
            reuse.append({"method": m, "from": "b", "inputs_recorded_in_other": bool(step and steps_a and step in steps_a), "step": step})
    return {"method": METHOD, "available": True, "a": {"record": ga["record"], "target": ga["target"], "question": ga["question"]},
            "b": {"record": gb["record"], "target": gb["target"], "question": gb["question"]},
            "shared_observational": shared,
            "interpretations": {"a": {"category": ia["category"], "region": ia["region"]}, "b": {"category": ib["category"], "region": ib["region"]},
                                "different": (ia["category"], ia["region"]) != (ib["category"], ib["region"])},
            "similar_weaknesses": {"both": sorted(weak_a & weak_b), "only_a": sorted(weak_a - weak_b), "only_b": sorted(weak_b - weak_a),
                                   "rule": "CLAIMX-1 modes that warn or fail"},
            "evidence_patterns": {"same_explanations_same_status": same_expl, "contradictions": {"a": len(A["contradictory_evidence"]["items"]), "b": len(B["contradictory_evidence"]["items"])},
                                  "rule": "the same HYPO-1 explanation with the same overall status; LEDGER-1 contradictions present"},
            "uncertainty_structures": {"propagated_both": sorted(pa & pb), "propagated_only_a": sorted(pa - pb), "propagated_only_b": sorted(pb - pa),
                                       "not_propagated_both": sorted(na & nb), "not_propagated_only_a": sorted(na - nb), "not_propagated_only_b": sorted(nb - na)},
            "reusable_methods": {"items": reuse, "rule": "a method one genome used that the other did not, and whether the other record ran the pipeline step that produces its inputs"},
            "note": NOTE}
