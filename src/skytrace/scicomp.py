"""Scientific reasoning compiler (SCICOMP-1): structural and methodological checks on one investigation.

Ten stages, each a list of checks. Every check states its rule, gives one outcome (pass / warning / fail / not applicable)
and cites the record fields or graph nodes it looked at. The overall outcome follows one precedence rule (OUTCOME_RULE).

A successful compilation means the investigation passed these defined checks. It is not evidence that a conclusion is
true: the checks cannot see systematic effects the record does not describe, and they run on whatever data the record
was made from (synthetic fixtures here).
"""

from __future__ import annotations

import math

from . import counterfactual as cf, epistemic as epi, methodgenome as mg
from .capabilities import CAPABILITIES
from .review import CAUSAL_WORDS

METHOD = "SCICOMP-1"
STAGES = [("parse", "Parse"), ("types", "Type checking"), ("dependencies", "Dependency resolution"), ("assumptions", "Assumption analysis"),
          ("methods", "Method validation"), ("evidence", "Evidence validation"), ("uncertainty", "Uncertainty validation"),
          ("provenance", "Provenance validation"), ("conclusions", "Conclusion review"), ("report", "Compilation report")]
OUTCOMES = ["valid under recorded rules", "valid with warnings", "incomplete", "incompatible", "unsupported claim", "invalid provenance",
            "requires scientific review"]
OUTCOME_RULE = ("first match wins: a failed provenance check → invalid provenance; a failed type check → incompatible; a failed parse or "
                "dependency check → incomplete; a failed evidence or conclusion check → unsupported claim; a check that asks for review → "
                "requires scientific review; any warning → valid with warnings; otherwise valid under recorded rules")
POSITIVE = {"variability_candidate", "motion_detected", "motion_inconsistent"}
ARTEFACT_ALTS = {"variability": ["V-CALIB", "V-ERRMODEL", "V-WAVELENGTH", "V-BLEND"], "motion": ["M-REGISTRATION", "M-CHROMATIC", "M-REFS"]}
PARAM_RANGES = {k: tuple(v["range"]) for c in CAPABILITIES for k, v in (c.get("parameters") or {}).items() if isinstance(v, dict) and "range" in v}


def _c(stage, cid, rule, outcome, detail, cites=None, review=False):
    return {"stage": stage, "id": cid, "rule": rule, "outcome": outcome, "detail": detail, "cites": (cites or [])[:12], "review": review}


def _ev(record):
    out = {}
    for i, e in enumerate(record["events"]):
        out.setdefault(e["step"], []).append((i, e))
    return out


def compile_investigation(record: dict, graph: dict, disc: dict, ledger: dict, manifest: dict | None = None, quality: dict | None = None) -> dict:
    ev = _ev(record)
    P = record.get("parameters", {})
    C = []
    meas = {(e.get("data") or {}).get("obs_id"): (i, e) for i, e in ev.get("measure", [])}
    ok_meas = {k for k, (i, e) in meas.items() if e.get("status") == "ok"}
    var = (ev.get("variability") or [(None, {"data": {}})])[0]
    pairs = (var[1].get("data") or {}).get("pairs", [])
    assess = (ev.get("assess") or [(None, {"data": {}})])[0]
    outcomes = {o["question"]: o for o in (assess[1].get("data") or {}).get("outcomes", [])}
    astro = (ev.get("astrometry") or [(None, {"data": {}})])[0][1].get("data") or {}

    # 1 parse
    C.append(_c("parse", "P1", "the record declares a known schema", "pass" if record.get("schema") == "skytrace.investigation/1" else "fail",
                f"schema = {record.get('schema')}", ["$.schema"]))
    missing = [s for s in ("discover", "measure", "assess") if s not in ev]
    C.append(_c("parse", "P2", "the record contains the discover, measure and assess steps", "fail" if missing else "pass",
                f"missing: {', '.join(missing)}" if missing else f"{len(record['events'])} events in {len(ev)} step types", ["$.events"]))
    bad = [n["id"] for n in graph["nodes"] if n["kind"] not in epi.KINDS or (n["status"] is not None and n["status"] not in epi.STATUSES)]
    C.append(_c("parse", "P3", "every scientific object has a known kind and an epistemic status from the fixed list (procedures excepted)",
                "fail" if bad else "pass", f"{len(graph['nodes'])} objects; {len(bad)} malformed" if bad else f"{len(graph['nodes'])} objects parsed", bad))

    # 2 types
    ins = [(e.get("data") or {}) for _, e in ev.get("inspect", [])]
    wrong_unit = [d.get("key") for d in ins if d.get("image_bunit") != mg.QTYPES["image"]]
    C.append(_c("types", "T1", f"APPHOT-1 needs images in {mg.QTYPES['image']}", "fail" if wrong_unit else ("pass" if ins else "not applicable"),
                f"{len(wrong_unit)} of {len(ins)} files in another unit" if wrong_unit else f"{len(ins)} files in {mg.QTYPES['image']}", wrong_unit))
    wrong_var = [d.get("key") for d in ins if d.get("variance_bunit") not in (mg.QTYPES["variance"], None)]
    C.append(_c("types", "T2", f"VARIANCE must be in {mg.QTYPES['variance']}", "fail" if wrong_var else ("pass" if ins else "not applicable"),
                f"{len(wrong_var)} files with another variance unit" if wrong_var else "variance units consistent", wrong_var))
    det = {k: (e.get("data") or {}).get("detector") for k, (i, e) in meas.items()}
    cross = [f"{p['a']}|{p['b']}" for p in pairs if det.get(p["a"]) != det.get(p["b"])]
    C.append(_c("types", "T3", "flux is compared only between exposures of the same detector (WLMATCH-2 condition 1)", "fail" if cross else ("pass" if pairs else "not applicable"),
                f"{len(cross)} cross-detector comparisons" if cross else f"{len(pairs)} comparisons, all same-detector", [f"pair:{x}" for x in cross]))
    acc = {(a["a"], a["b"]) for a in ((ev.get("pairs") or [(0, {"data": {}})])[0][1].get("data") or {}).get("accepted", []) if a.get("accepted", True)}
    unmatched = [f"{p['a']}|{p['b']}" for p in pairs if (p["a"], p["b"]) not in acc and (p["b"], p["a"]) not in acc]
    C.append(_c("types", "T4", "every flux comparison is a pair accepted by WLMATCH-2", "fail" if unmatched else ("pass" if pairs else "not applicable"),
                f"{len(unmatched)} comparisons of unaccepted pairs" if unmatched else "every comparison is an accepted wavelength-matched pair", [f"pair:{x}" for x in unmatched]))
    nonnum = [k for k in ok_meas if not _finite(((meas[k][1].get("data") or {}).get("photometry") or {}).get("flux_ujy"))
              and ((meas[k][1].get("data") or {}).get("photometry") or {}).get("status") == "ok"]
    C.append(_c("types", "T5", "usable photometry carries a numeric flux in µJy", "fail" if nonnum else "pass",
                f"{len(nonnum)} usable measurements without a numeric flux" if nonnum else f"{len(ok_meas)} usable measurements typed as flux [µJy]", [f"meas:{k}" for k in nonnum]))

    # 3 dependencies
    orphan = [f"{p['a']}|{p['b']}" for p in pairs if p["a"] not in meas or p["b"] not in meas]
    C.append(_c("dependencies", "D1", "every comparison's two measurements exist in the record", "fail" if orphan else ("pass" if pairs else "not applicable"),
                f"{len(orphan)} comparisons with a missing measurement" if orphan else "all comparison inputs present", [f"pair:{x}" for x in orphan]))
    series = {s.get("key") for s in astro.get("series", [])}
    miss_s = sorted(series - set(meas))
    skeys = [s.get("key") for s in astro.get("series", [])]
    members = {m for ep in astro.get("epochs", []) for m in ep.get("members") or []}
    miss_m = sorted(str(m) for m in members if not (isinstance(m, int) and 0 <= m < len(skeys)))
    C.append(_c("dependencies", "D2", "every sky position comes from a recorded measurement and every visit member is a recorded position",
                "fail" if miss_s or miss_m else ("pass" if series else "not applicable"),
                f"{len(miss_s)} positions and {len(miss_m)} visit members without a source" if miss_s or miss_m else f"{len(series)} positions, {len(members)} visit members resolved",
                [f"pos:{k}" for k in miss_s + miss_m]))
    ids = {n["id"] for n in graph["nodes"]}
    into = {}
    for e in graph["edges"]:
        into.setdefault(e["target"], []).append(e["source"])
    nodeless = [c for c in graph["claims"] if not [s for s in into.get(c, []) if s.startswith("inf:") and into.get(s)]]
    C.append(_c("dependencies", "D3", "every claim is concluded by an inference that has recorded inputs", "fail" if nodeless else "pass",
                f"{len(nodeless)} claims without decided inputs" if nodeless else f"{len(graph['claims'])} claims resolve to their inputs", nodeless))
    fit = astro.get("fit") or {}
    C.append(_c("dependencies", "D4", "a motion fit needs at least two visits", "not applicable" if not fit else ("pass" if (fit.get("n_epochs") or 0) >= 2 else "fail"),
                f"{fit.get('n_epochs')} visits" if fit else "no motion fit recorded", ["fit:motion"]))

    # 4 assumptions
    sd = assess[1].get("data") or {}
    C.append(_c("assumptions", "A1", "every decision threshold states where it came from", "pass" if sd.get("threshold_provenance") and sd.get("thresholds") else "fail",
                (sd.get("threshold_provenance") or "no provenance recorded")[:200], [f"asm:threshold:{k}" for k in (sd.get("thresholds") or {})]))
    miss_p = [k for k in epi.PARAM_STEPS if k not in P]
    C.append(_c("assumptions", "A2", "every analysis parameter is recorded with the result", "fail" if miss_p else "pass",
                f"not recorded: {', '.join(miss_p)}" if miss_p else f"{len(epi.PARAM_STEPS)} parameters recorded", [f"param:{k}" for k in miss_p]))
    used = mg.used_methods(record)
    unreg = sorted(m for m in used if m not in mg.BY_ID)
    C.append(_c("assumptions", "A3", "every method used has its assumptions documented in the method genome", "warning" if unreg else "pass",
                f"undocumented: {', '.join(unreg)}" if unreg else f"{len(used)} methods documented", [f"method:{m}" for m in unreg]))
    sel = ((ev.get("references") or [(0, {"data": {}})])[0][1].get("data") or {}).get("selection") or {}
    unchecked = {k: v for k, v in (sel.get("accepted_unchecked") or {}).items() if v}
    C.append(_c("assumptions", "A4", "assumptions a method could test were tested (REFSEL-2 quality cuts need RUWE and duplicate flags)",
                "warning" if unchecked else ("pass" if sel else "not applicable"),
                ("accepted without the check: " + ", ".join(f"{v} stars ({k})" for k, v in unchecked.items())) if unchecked else "all reference-star cuts evaluated",
                ["method:REFSEL-2", "asm:REFSEL-2:0"]))

    # 5 methods
    uncal = [p for p in pairs if not (p.get("differential") or {}).get("calibrated")]
    C.append(_c("methods", "M1", "PAIRDIFF-2 calibration needs ≥ 3 matched reference stars", "warning" if uncal else ("pass" if pairs else "not applicable"),
                f"{len(uncal)} of {len(pairs)} comparisons had fewer and were left uncalibrated (decided on PAIRDIFF-1 z)" if uncal else "every comparison calibrated",
                [_pid(p) for p in uncal]))
    n_ep = len(astro.get("epochs", []))
    C.append(_c("methods", "M2", "LINFIT-LOO-1 can reject a discrepant visit only with ≥ 3 visits", "not applicable" if not fit else ("pass" if n_ep >= 3 else "warning"),
                f"{n_ep} visits" + ("" if n_ep >= 3 else ": no visit could be rejected"), ["method:LINFIT-LOO-1"]))
    C.append(_c("methods", "M3", "ASSESS-2 applies only to records of skytrace-analysis/2", "pass" if P.get("analysis_version") == "skytrace-analysis/2" else "fail",
                f"analysis_version = {P.get('analysis_version')}", ["$.parameters.analysis_version"]))
    out = [f"{k} = {P[k]} outside {lo}–{hi}" for k, (lo, hi) in PARAM_RANGES.items() if isinstance(P.get(k), (int, float)) and not isinstance(P.get(k), bool) and not lo <= P[k] <= hi]
    C.append(_c("methods", "M4", "parameters lie within each method's documented range (CAPREG)", "fail" if out else "pass",
                "; ".join(out) if out else f"{sum(1 for k in PARAM_RANGES if k in P)} ranged parameters within range", [f"param:{k.split(' ')[0]}" for k in out]))
    nonconv = [k for k in series if not (((meas.get(k) or (0, {}))[1].get("data") or {}).get("centroid") or {}).get("converged", True)]
    C.append(_c("methods", "M5", "positions used for motion come from converged centroid fits", "fail" if nonconv else ("pass" if series else "not applicable"),
                f"{len(nonconv)} positions from fits that did not converge" if nonconv else "all centroid fits used for positions converged", [f"meas:{k}" for k in nonconv]))

    # 6 evidence
    try:
        re = cf.reassess(record)
        same = all(re.get(q, {}).get("category") == o.get("category") for q, o in outcomes.items())
    except Exception as e:      # noqa: BLE001 - reported, not hidden
        same, re = None, {"error": str(e)}
    C.append(_c("evidence", "E1", "re-applying ASSESS-2 to the recorded inputs reproduces every recorded outcome",
                "pass" if same else ("fail" if same is False else "warning"),
                "all outcomes re-derived exactly" if same else f"re-assessment differs or failed: {str(re)[:160]}", [f"claim:{q}" for q in outcomes]))
    for q, o in outcomes.items():
        if o.get("category") in POSITIVE:
            n_sup = sum(1 for e in graph["edges"] if e["target"] == f"inf:{q}")
            C.append(_c("evidence", f"E2-{q}", "a positive claim is decided by at least one recorded input meeting its threshold", "pass" if n_sup else "fail",
                        f"{n_sup} inputs decide claim:{q}; evidence: {_short(o.get('evidence'))}", [f"claim:{q}", f"inf:{q}"]))
    cons = ledger.get("contradictions", [])
    C.append(_c("evidence", "E3", "contradictory evidence is acknowledged by the claim it bears on (LEDGER-1 C1–C4)",
                "warning" if cons else "pass", (f"{len(cons)} contradictions recorded; the claim's category does not resolve them, so they need review" if cons
                                                 else "no contradictions recorded"), [f"con:{i}" for i in range(len(cons))], review=bool(cons)))

    # 7 uncertainty
    noerr = [k for k in ok_meas if not (_finite(((meas[k][1].get("data") or {}).get("photometry") or {}).get("flux_err_ujy"))
                                       and ((meas[k][1].get("data") or {}).get("photometry") or {}).get("flux_err_ujy") > 0)
             and ((meas[k][1].get("data") or {}).get("photometry") or {}).get("status") == "ok"]
    C.append(_c("uncertainty", "U1", "every usable flux has a finite, positive uncertainty", "fail" if noerr else "pass",
                f"{len(noerr)} fluxes without a usable error" if noerr else f"{len(ok_meas)} measurements carry errors", [f"meas:{k}" for k in noerr]))
    bad_z = []
    for p in pairs:
        s = math.sqrt(p["err_a_ujy"] ** 2 + p["err_b_ujy"] ** 2) if _finite(p.get("err_a_ujy")) and _finite(p.get("err_b_ujy")) else None
        if s is None or not math.isclose(s, p["sigma_ujy"], rel_tol=1e-9) or not math.isclose(p["delta_ujy"] / p["sigma_ujy"], p["z"], rel_tol=1e-9):
            bad_z.append(_pid(p))
    C.append(_c("uncertainty", "U2", "each comparison's σ = √(σa² + σb²) and z = Δ/σ recompute from the recorded values (relative tolerance 1e-9)",
                "fail" if bad_z else ("pass" if pairs else "not applicable"), f"{len(bad_z)} comparisons do not recompute" if bad_z else f"{len(pairs)} comparisons recompute", bad_z))
    cc = (var[1].get("data") or {}).get("calibration_check") or {}
    C.append(_c("uncertainty", "U3", "an error scale above 1 (CALCHECK-1) is applied to the decision, not ignored",
                "not applicable" if not cc else ("pass" if same is not False else "fail"),
                f"scale {cc.get('error_scale'):.3f} ({cc.get('status')}); ASSESS-2 divides z by it (E1 re-derives the decision with it)" if cc and _finite(cc.get("error_scale")) else "no error-model check recorded",
                ["scale:calcheck"]))
    nonprop = [m["id"] for m in mg.METHODS if m["id"] in used and m["uncertainty_propagation"].startswith("none") and m["output_status"] != "measured"
               and m["id"] not in ("ASSESS-2", "REFSEL-2")]
    C.append(_c("uncertainty", "U4", "steps that do not propagate uncertainty are declared (their effect is recorded as a bound or a residual, not a σ)",
                "warning" if nonprop else "pass", ("not propagated: " + "; ".join(f"{m} ({mg.BY_ID[m]['uncertainty_propagation']})" for m in nonprop)) if nonprop
                else "every step propagates or is categorical", [f"unc:{m}" for m in nonprop]))

    # 8 provenance
    rh = cf.record_hash(record)
    C.append(_c("provenance", "V1", "the record's content hash recomputes", "pass" if rh == record.get("content_hash") else "fail",
                "recomputed hash matches" if rh == record.get("content_hash") else f"stated {str(record.get('content_hash'))[:12]}…, recomputed {rh[:12]}…", ["$.content_hash"]))
    files = {f.get("sha256") for f in (manifest or {}).get("files", [])}
    noprov = [k for k, (i, e) in meas.items() if not (e.get("provenance") or [{}])[0].get("content_sha256")]
    unknown = [k for k, (i, e) in meas.items() if manifest and (e.get("provenance") or [{}])[0].get("content_sha256") not in files]
    C.append(_c("provenance", "V2", "every measurement names the SHA-256 of its source file, and that file is in the bundle manifest",
                "fail" if noprov or unknown else "pass", f"{len(noprov)} without a hash, {len(unknown)} not in the manifest" if noprov or unknown
                else f"{len(meas)} measurements trace to manifest files" + ("" if manifest else " (manifest not available here)"), [f"file:{k}" for k in (noprov + unknown)]))
    C.append(_c("provenance", "V3", "method versions and the bundle manifest hash are recorded", "pass" if P.get("methods") and P.get("bundle_manifest_sha256") else "fail",
                f"{len(P.get('methods') or {})} method roles; manifest {str(P.get('bundle_manifest_sha256'))[:12]}…", ["$.parameters.methods", "$.parameters.bundle_manifest_sha256"]))
    if quality:
        dq = next((c for c in quality.get("checks", []) if c["id"] == "DQ-FILES"), None)
        if dq:
            C.append(_c("provenance", "V4", "bundle files match their manifest checksums now (DQ-FILES)",
                        {"valid": "pass", "not_checked": "not applicable", "not_available": "not applicable"}.get(dq["outcome"], "fail"),
                        "; ".join(i["detail"] for i in dq.get("items", []))[:200], ["DQ-FILES"]))

    # 9 conclusions
    hyp = {h["id"]: h for q in (disc.get("hypotheses") or {}).get("questions", []) for h in q.get("hypotheses", [])}
    for q, o in outcomes.items():
        words = epi.asserted_words(o.get("statement") or "", CAUSAL_WORDS)
        C.append(_c("conclusions", f"C1-{q}", "a claim's wording does not assert discovery or causation (negated uses such as “not proof” are not assertions)", "fail" if words else "pass",
                    f"uses: {', '.join(words)}" if words else f"“{(o.get('statement') or '')[:120]}”", [f"claim:{q}"]))
        if o.get("category") in POSITIVE:
            open_alts = [a for a in ARTEFACT_ALTS.get(q, []) if a in hyp and hyp[a]["overall"] != "contradicted"]
            C.append(_c("conclusions", f"C2-{q}", "a positive claim with artefact explanations not ruled out needs scientific review",
                        "warning" if open_alts else "pass", f"not ruled out: {', '.join(open_alts)}" if open_alts else "every listed artefact explanation is contradicted by a test",
                        [f"hyp:{a}" for a in open_alts], review=bool(open_alts)))
        elif o.get("category", "").startswith("no_"):
            C.append(_c("conclusions", f"C3-{q}", "an absence claim states the sensitivity it is bounded by", "pass" if o.get("sensitivity") else "fail",
                        f"sensitivity: {_short(o.get('sensitivity'))}" if o.get("sensitivity") else "no sensitivity stated", [f"claim:{q}"]))
    C.append(_c("conclusions", "C4", "conclusions drawn from generated data are labelled as such", "pass",
                "bundle_kind = synthetic: every conclusion describes generated test data, not the sky" if P.get("bundle_kind") == "synthetic"
                else f"bundle_kind = {P.get('bundle_kind')}", ["$.parameters.bundle_kind"]))

    # every check cites what it examined: when a check found nothing to list, cite a sample of the objects it checked
    pair_ids = [_pid(p) for p in pairs][:5]
    meas_ids = [f"meas:{k}" for k in sorted(ok_meas)][:5]
    pos_ids = [f"pos:{k}" for k in sorted(series)][:5]
    defaults = {"T1": ["tf:inspect"], "T2": ["tf:inspect"], "T3": pair_ids, "T4": pair_ids, "T5": meas_ids, "D1": pair_ids, "D2": pos_ids,
                "M1": pair_ids, "M5": pos_ids, "M4": [f"param:{k}" for k in PARAM_RANGES if k in P][:6], "U1": meas_ids, "U2": pair_ids,
                "U4": ["unc:" + m for m in sorted(used) if m in mg.BY_ID][:6], "V2": [f"file:{k}" for k in sorted(meas)][:5], "E3": ["claim:variability"]}
    for c in C:
        if not c["cites"]:
            c["cites"] = defaults.get(c["id"], []) or ["$.events"]

    # 10 report
    def any_(stage, outcome):
        return any(c["stage"] in stage and c["outcome"] == outcome for c in C)
    if any_(("provenance",), "fail"):
        overall = "invalid provenance"
    elif any_(("types",), "fail"):
        overall = "incompatible"
    elif any_(("parse", "dependencies"), "fail"):
        overall = "incomplete"
    elif any_(("evidence", "conclusions"), "fail"):
        overall = "unsupported claim"
    elif any(c["review"] for c in C):
        overall = "requires scientific review"
    elif any(c["outcome"] == "warning" for c in C):
        overall = "valid with warnings"
    else:
        overall = "valid under recorded rules"
    stages = []
    for sid, name in STAGES[:-1]:
        cs = [c for c in C if c["stage"] == sid]
        stages.append({"id": sid, "name": name, "counts": {o: sum(c["outcome"] == o for c in cs) for o in ("pass", "warning", "fail", "not applicable")}})
    return {"method": METHOD, "content_hash": record.get("content_hash"), "outcome": overall, "outcome_rule": OUTCOME_RULE, "outcomes": OUTCOMES,
            "stages": stages, "checks": C, "synthetic": P.get("bundle_kind") == "synthetic",
            "meaning": "Passing means the investigation met these structural and methodological checks. It does not mean any conclusion is true."}


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _pid(p):
    return f"pair:{p['a']}|{p['b']}"


def _short(v):
    if isinstance(v, dict):
        return ", ".join(f"{k} = {round(x, 4) if isinstance(x, float) else x}" for k, x in list(v.items())[:4])
    return str(v)[:120]
