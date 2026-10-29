"""Hypothesis tests on recorded evidence (HYPO-1).

For each question the assessment answered (brightness change, motion), a fixed set of competing explanations is
tested against values already in the investigation record. Each test states its rule and the values it used, and
returns one of:

  consistent            the recorded measurement agrees with what the hypothesis predicts
  contradicted          the recorded measurement disagrees beyond the stated threshold
  inconclusive          the measurement cannot separate the hypothesis from its alternatives
  not_tested            no implemented method tests this (the reason and what would be needed are given)
  evidence_unavailable  the method exists but the inputs it needs were not produced for this investigation
  incompatible          the data cannot be used with the method (e.g. no wavelength-matched pair)

No probabilities or scores are produced. A hypothesis's overall line follows one rule, shown with it: any
contradicted test → contradicted; otherwise any consistent test → consistent so far; otherwise, if every test is
not_tested / evidence_unavailable / incompatible → untested; otherwise inconclusive. Thresholds are the
assessment's own (ASSESS-2: 5σ detection, 3σ consistency).
"""

from __future__ import annotations

import math

from .science.assess import T, pair_significance

METHOD = "HYPO-1"
STATUSES = ("consistent", "contradicted", "inconclusive", "not_tested", "evidence_unavailable", "incompatible")
OVERALL_RULE = ("any contradicted test → contradicted; else any consistent test → consistent so far; else all untested "
                "→ untested; else inconclusive")


def _first(record, step):
    return next((e for e in record["events"] if e["step"] == step), None)


def _test(tid, description, rule, status, detail, values=None):
    assert status in STATUSES, status
    return {"id": tid, "description": description, "rule": rule, "status": status, "detail": detail, "values": values or {}}


def overall(tests: list[dict]) -> str:
    st = [t["status"] for t in tests]
    if "contradicted" in st:
        return "contradicted"
    if "consistent" in st:
        return "consistent so far"
    if all(s in ("not_tested", "evidence_unavailable", "incompatible") for s in st):
        return "untested"
    return "inconclusive"


def _hyp(hid, statement, tests):
    return {"id": hid, "statement": statement, "tests": tests, "overall": overall(tests), "overall_rule": OVERALL_RULE}


# ---------------------------------------------------------------------------- brightness
def variability(record: dict) -> dict:
    v = _first(record, "variability")
    outs = {o["question"]: o for o in (_first(record, "assess") or {"data": {}})["data"].get("outcomes", [])}
    o = outs.get("variability", {})
    pairs = (v or {"data": {}})["data"].get("pairs", []) if v else []
    cal = ((v or {}).get("data") or {}).get("calibration_check") or {}
    scale = cal.get("error_scale")
    meas = {e["data"]["key"]: e["data"] for e in record["events"] if e["step"] == "measure" and "key" in e["data"]}
    sig, raw_sig, calibrated = [], [], []
    for p in pairs:
        z, cal_ok = pair_significance(p, scale)
        if cal_ok:
            calibrated.append(p)
            if z is not None and abs(z) >= T["variability_z"]:
                sig.append(p)
        if p.get("z") is not None and abs(p["z"]) >= T["variability_z"]:
            raw_sig.append(p)
    sens = (o.get("sensitivity") or {}).get("min_detectable_fractional_change_5sigma_best_pair")

    # V-INTRINSIC
    if not pairs:
        t1 = _test("T-SIG", "A reference-calibrated matched pair differs by ≥ 5σ", "|z_cal,scaled| ≥ 5 in at least one pair",
                   "incompatible", "no wavelength-matched pair of usable measurements exists")
    elif not calibrated:
        t1 = _test("T-SIG", "A reference-calibrated matched pair differs by ≥ 5σ", "|z_cal,scaled| ≥ 5 in at least one pair",
                   "evidence_unavailable", "no pair had ≥ 3 wavelength-matched reference stars, so no calibrated significance exists",
                   {"n_pairs": len(pairs)})
    elif sig:
        t1 = _test("T-SIG", "A reference-calibrated matched pair differs by ≥ 5σ", "|z_cal,scaled| ≥ 5 in at least one pair",
                   "consistent", f"{len(sig)} of {len(calibrated)} calibrated pairs differ by ≥ 5σ",
                   {"n_significant": len(sig), "n_calibrated": len(calibrated),
                    "max_abs_z": max(abs(pair_significance(p, scale)[0]) for p in sig)})
    else:
        t1 = _test("T-SIG", "A reference-calibrated matched pair differs by ≥ 5σ", "|z_cal,scaled| ≥ 5 in at least one pair",
                   "inconclusive", "no calibrated pair differs by ≥ 5σ; a change smaller than the sensitivity is not excluded",
                   {"n_calibrated": len(calibrated), "best_pair_sensitivity_fraction": sens})
    dets = sorted({meas.get(p["a"], {}).get("detector") for p in sig} - {None})
    if not sig:
        t2 = _test("T-REPEAT", "The change appears in more than one detector", "significant pairs on ≥ 2 detectors",
                   "not_tested", "there is no significant pair to check")
    else:
        t2 = _test("T-REPEAT", "The change appears in more than one detector", "significant pairs on ≥ 2 detectors",
                   "consistent" if len(dets) >= 2 else "inconclusive",
                   f"significant pairs on detector(s) {', '.join('D%d' % d for d in dets)}" +
                   ("" if len(dets) >= 2 else "; one detector cannot rule out a detector-specific effect"), {"detectors": dets})
    h_intr = _hyp("V-INTRINSIC", "The source's brightness changed between the epochs.", [t1, t2])

    # V-CALIB
    raw_cal = [p for p in raw_sig if (p.get("differential") or {}).get("calibrated")]
    if not raw_sig:
        t = _test("T-REFRATIO", "Dividing by the reference stars' flux ratio removes the difference",
                  "raw |z| ≥ 5 pairs fall below 5σ after PAIRDIFF-2", "not_tested", "no raw difference ≥ 5σ to explain")
    elif not raw_cal:
        t = _test("T-REFRATIO", "Dividing by the reference stars' flux ratio removes the difference",
                  "raw |z| ≥ 5 pairs fall below 5σ after PAIRDIFF-2", "evidence_unavailable",
                  "none of the raw-significant pairs had ≥ 3 matched reference stars", {"n_raw_significant": len(raw_sig)})
    else:
        remain = [p for p in raw_cal if abs(pair_significance(p, scale)[0] or 0) >= T["variability_z"]]
        explained = len(raw_cal) - len(remain)
        status = "contradicted" if remain and not explained else "consistent" if not remain else "inconclusive"
        t = _test("T-REFRATIO", "Dividing by the reference stars' flux ratio removes the difference",
                  "raw |z| ≥ 5 pairs fall below 5σ after PAIRDIFF-2", status,
                  f"{len(remain)} of {len(raw_cal)} raw-significant calibrated pairs stay ≥ 5σ after calibration; {explained} fall below",
                  {"n_remain": len(remain), "n_explained": explained,
                   "ratios": [round((p["differential"].get("ratio_median") or float("nan")), 6) for p in raw_cal][:20]})
    h_cal = _hyp("V-CALIB", "A calibration change between the exposures explains the difference.", [t])

    # V-ERRMODEL
    if cal.get("status") in (None, "insufficient"):
        t = _test("T-CALCHECK", "Constant reference stars show the stated errors are too small to explain it",
                  "CALCHECK scale > 3, or significance gone after scaling", "evidence_unavailable",
                  "fewer than 10 reference-star comparisons; the error model could not be checked")
    elif (scale or 0) > T["calcheck_unreliable_scale"]:
        t = _test("T-CALCHECK", "Constant reference stars show the stated errors are too small to explain it",
                  "CALCHECK scale > 3, or significance gone after scaling", "consistent",
                  f"reference stars scatter {scale:.2f}× their stated errors; the error model is not reliable", {"scale": scale})
    elif sig:
        t = _test("T-CALCHECK", "Constant reference stars show the stated errors are too small to explain it",
                  "CALCHECK scale > 3, or significance gone after scaling", "contradicted",
                  f"{len(sig)} pair(s) stay ≥ 5σ after errors are scaled by {scale:.2f}", {"scale": scale, "n_significant": len(sig)})
    else:
        t = _test("T-CALCHECK", "Constant reference stars show the stated errors are too small to explain it",
                  "CALCHECK scale > 3, or significance gone after scaling", "inconclusive",
                  "no pair is significant after scaling, so there is no difference for the error model to explain", {"scale": scale})
    h_err = _hyp("V-ERRMODEL", "Underestimated measurement errors explain the difference.", [t])

    dl = [{"pair": f"{p['a']} → {p['b']}", "delta_lambda_um": p.get("delta_lambda_um")} for p in sig][:10]
    h_wl = _hyp("V-WAVELENGTH", "A wavelength difference within the matching tolerance, acting on the spectrum, explains it.",
                [_test("T-SLOPE", "Expected flux change from the local spectral slope across |Δλ|", "needs a spectral-slope model",
                       "not_tested", "not implemented: needs a local spectral-slope estimate at the matched wavelength; "
                       "the |Δλ| of the significant pairs is listed for inspection", {"significant_pairs_delta_lambda": dl})])
    h_blend = _hyp("V-BLEND", "An unresolved neighbour contributes to the difference.",
                   [_test("T-NEIGHBOUR", "Flux of uncatalogued neighbours inside the aperture", "needs PSF-fitting photometry",
                          "not_tested", "catalogued neighbours are masked (NBMASK-1) and blended exposures rejected; "
                          "uncatalogued neighbours need PSF-fitting photometry, which is not implemented")])
    return {"question": "variability", "outcome": o.get("category"),
            "hypotheses": [h_intr, h_cal, h_err, h_wl, h_blend]}


# ---------------------------------------------------------------------------- motion
def motion(record: dict) -> dict:
    a = _first(record, "astrometry")
    outs = {o["question"]: o for o in (_first(record, "assess") or {"data": {}})["data"].get("outcomes", [])}
    o = outs.get("motion", {})
    ev = o.get("evidence", {})
    have = bool(a and a["status"] == "ok")
    d = a["data"] if have else {}
    cmp = d.get("comparison", {})
    snr = ev.get("detection_snr")
    detected = snr is not None and snr >= T["motion_detect_sigma"]
    sens = (o.get("sensitivity") or {}).get("min_detectable_pm_mas_yr_5sigma")
    na = lambda tid, desc, rule: _test(tid, desc, rule, "evidence_unavailable",
                                       (a or {}).get("detail", "no motion fit was recorded") if a else "no motion fit was recorded")

    # M-CATALOGUE
    if not have:
        t = na("T-CATZ", "Measured motion agrees with the catalogue", "|measured − catalogue| ≤ 3σ per axis")
    elif not detected and ev.get("pm_catalogue_mas_yr") is not None and sens and ev["pm_catalogue_mas_yr"] < sens:
        t = _test("T-CATZ", "Measured motion agrees with the catalogue", "|measured − catalogue| ≤ 3σ per axis", "inconclusive",
                  f"the catalogue motion ({ev['pm_catalogue_mas_yr']:.0f} mas/yr) is below this data set's 5σ sensitivity ({sens:.0f} mas/yr)",
                  {"z_pmra": cmp.get("z_pmra"), "z_pmdec": cmp.get("z_pmdec")})
    else:
        t = _test("T-CATZ", "Measured motion agrees with the catalogue", "|measured − catalogue| ≤ 3σ per axis",
                  "consistent" if cmp.get("consistent_within_3sigma") else "contradicted",
                  f"differences {cmp.get('z_pmra', float('nan')):.2f}σ (RA) and {cmp.get('z_pmdec', float('nan')):.2f}σ (Dec)",
                  {"z_pmra": cmp.get("z_pmra"), "z_pmdec": cmp.get("z_pmdec")})
    h_cat = _hyp("M-CATALOGUE", "The measured motion is the catalogued proper motion.", [t])

    # M-STATIC
    if not have:
        t = na("T-DET", "No significant motion", "|pm|/σ < 5")
    else:
        t = _test("T-DET", "No significant motion", "|pm|/σ < 5", "contradicted" if detected else "inconclusive",
                  f"motion detected at {snr:.1f}σ" if detected else
                  f"no motion above {sens:.0f} mas/yr (5σ); this does not prove the source is static" if sens else "no detection",
                  {"detection_snr": snr})
    h_static = _hyp("M-STATIC", "The source does not move.", [t])

    # M-REGISTRATION
    if not have:
        t = na("T-REG", "Registration residual is comparable to the measured displacement", "3 × median plate RMS ≥ |pm| × baseline")
    elif not detected:
        t = _test("T-REG", "Registration residual is comparable to the measured displacement", "3 × median plate RMS ≥ |pm| × baseline",
                  "not_tested", "no significant motion to explain")
    else:
        shift = ev["pm_measured_mas_yr"] * ev["baseline_yr"]
        rms = ev.get("median_plate_rms_mas")
        t = _test("T-REG", "Registration residual is comparable to the measured displacement", "3 × median plate RMS ≥ |pm| × baseline",
                  "consistent" if rms is not None and 3 * rms >= shift else "contradicted",
                  f"total measured displacement {shift:.0f} mas vs median registration residual {rms:.0f} mas per exposure",
                  {"displacement_mas": shift, "median_plate_rms_mas": rms})
    h_reg = _hyp("M-REGISTRATION", "Registration errors produce the apparent motion.", [t])

    # M-PARALLAX
    plx = d.get("parallax") or {}
    if not have:
        t = na("T-PLX", "Unremoved parallax is large enough to bias the rate", "parallax rate bound ≥ σ(pm)")
    else:
        base = d["fit"].get("baseline_yr") or 0.0
        bound = plx.get("systematic_bound_mas") if plx.get("applied") else plx.get("parallax_mas")
        rate = (bound / base) if bound is not None and base > 0 else None
        sig = ev.get("pm_sigma_mas_yr")
        if rate is None or sig is None:
            t = _test("T-PLX", "Unremoved parallax is large enough to bias the rate", "parallax rate bound ≥ σ(pm)",
                      "evidence_unavailable", "parallax or baseline not recorded")
        else:
            t = _test("T-PLX", "Unremoved parallax is large enough to bias the rate", "parallax rate bound ≥ σ(pm)",
                      "consistent" if rate >= sig else "contradicted",
                      f"{'residual after EPHEM-AA-LP-1' if plx.get('applied') else 'parallax not removed'}: ≤ {rate:.2f} mas/yr vs σ {sig:.0f} mas/yr",
                      {"rate_bound_mas_yr": rate, "pm_sigma_mas_yr": sig, "applied": plx.get("applied")})
    h_plx = _hyp("M-PARALLAX", "Unmodelled parallax produces or biases the apparent motion.", [t])

    # M-REFS
    r = _first(record, "references")
    sel = ((r or {}).get("data") or {}).get("selection") or {}
    loo = sum(len((e["data"].get("plate") or {}).get("rejected_refs") or []) for e in record["events"] if e["step"] == "measure")
    unchecked = sum((sel.get("accepted_unchecked") or {}).values()) if sel.get("accepted_unchecked") else None
    t = _test("T-REFSEL", "Reference stars were quality-checked and outliers removed",
              "inspect REFSEL-2 counts and leave-one-out plate rejections", "inconclusive",
              f"REFSEL-2 rejected {sum((sel.get('rejected') or {}).values())} catalogue star(s); "
              f"{unchecked if unchecked is not None else 'unknown number of'} quality checks could not be made (missing catalogue columns); "
              f"{loo} plate-level rejections across exposures", {"selection": sel, "plate_rejections": loo})
    h_refs = _hyp("M-REFS", "Faulty reference stars bias the plate solutions.", [t])
    h_chrom = _hyp("M-CHROMATIC", "Detector-dependent (chromatic) offsets produce the apparent motion.",
                   [_test("T-PERDET", "Motion fitted separately per detector agrees", "needs per-detector fits", "not_tested",
                          "not implemented: per-detector motion fits would separate chromatic offsets")])
    return {"question": "motion", "outcome": o.get("category"),
            "hypotheses": [h_cat, h_static, h_reg, h_plx, h_refs, h_chrom]}


def evaluate(record: dict) -> dict:
    return {"method": METHOD, "statuses": list(STATUSES), "overall_rule": OVERALL_RULE,
            "questions": [variability(record), motion(record)],
            "note": "Explanations with no implemented test are listed as not tested rather than omitted."}


def test_index(result: dict) -> dict:
    """{test id: test} for attaching recorded tests to user-written hypotheses."""
    return {f"{h['id']}/{t['id']}": {**t, "hypothesis": h["id"]} for q in result["questions"] for h in q["hypotheses"] for t in h["tests"]}
