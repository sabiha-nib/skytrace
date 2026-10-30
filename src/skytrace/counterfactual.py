"""Counterfactual Universe Lab (CF-1): what changes in an investigation's outcomes if one stated thing were different.

A scenario names its baseline (the parameters of the original run, and that run's content hash) and one explicit
change. The original record is never modified: every scenario produces a separate result, and the baseline is
recomputed and its content hash compared with the stated one, so a scenario can show that its baseline is the
investigation it claims to vary.

Kinds and how each is executed:

  parameter      analysis parameters within the server's bounds (analysis.PARAM_BOUNDS, booleans, detectors);
                 the pipeline is re-run.                                                     → derived (re-run)
  exclusion      observations removed from the input: by key, by detector, or by a time window; the pipeline is
                 re-run on a copy of the bundle's index in which those observations are marked excluded with the
                 reason "counterfactual exclusion". The bundle on disk is not touched.       → derived (re-run)
  threshold      ASSESS-2 thresholds changed; the recorded inputs are re-assessed (no re-run). → assumed
  error_scale    every photometric uncertainty multiplied by k ≥ 1 (z divided by k); recorded pairs re-assessed.
                 A simulated perturbation of the error model, not a measurement.              → simulated
  method         brightness decided with PAIRDIFF-1 only (reference calibration ignored); recorded pairs
                 re-assessed.                                                                  → hypothetical method

Re-assessment uses the same assessment functions as the pipeline; with no change it reproduces the recorded
outcomes exactly (tests/unit/test_frontier.py). Labels on every value: observed (from the data files), derived
(computed from observed values by recorded methods), simulated (a deliberate perturbation), assumed (a threshold or
setting chosen for the scenario), hypothetical (a scenario that did not happen). Nothing here describes an alternative
physical reality: a scenario only shows how the stated analysis would respond to the stated change.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math

from . import analysis, canon
from .science import assess

METHOD = "CF-1"
SCHEMA_ID = "skytrace.counterfactual/1"
KINDS = ("parameter", "exclusion", "threshold", "error_scale", "method")
LABEL = {"parameter": "derived (pipeline re-run with a changed setting)", "exclusion": "derived (pipeline re-run without some observations)",
         "threshold": "assumed (threshold chosen for the scenario)", "error_scale": "simulated (error model perturbed)",
         "method": "hypothetical (alternative method applied to the recorded values)"}
THRESHOLD_BOUNDS = {"variability_z": (2.0, 10.0), "motion_detect_sigma": (2.0, 10.0), "catalogue_consistency_sigma": (1.0, 5.0)}
ERROR_SCALE_BOUNDS = (1.0, 5.0)
MAX_EXCLUDED_KEYS = 40
LEGEND = {"observed": "read from the data files", "derived": "computed from observed values by a recorded method",
          "simulated": "a deliberate perturbation for the scenario", "assumed": "a setting chosen for the scenario",
          "hypothetical": "a scenario that did not happen; not an alternative physical reality"}


# ---------------------------------------------------------------------------- validation
def clean_params(params: dict) -> dict:
    out = {}
    for k, v in (params or {}).items():
        if k in analysis.PARAM_BOOLEANS:
            if not isinstance(v, bool):
                raise ValueError(f"{k} must be true or false")
            out[k] = v
        elif k == "detectors":
            if not (isinstance(v, list) and v and all(isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 6 for d in v)):
                raise ValueError("detectors must be a non-empty list of integers 1-6")
            out[k] = sorted(set(v))
        elif k in analysis.PARAM_BOUNDS:
            lo, hi = analysis.PARAM_BOUNDS[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
                raise ValueError(f"{k} must be between {lo} and {hi}")
            out[k] = int(v) if k == "fit_half_size_px" else float(v)
        else:
            raise ValueError(f"unknown parameter {k}")
    return out


def validate(spec) -> list[str]:
    if not isinstance(spec, dict):
        return ["scenario must be an object"]
    errs = []
    extra = set(spec) - {"kind", "change", "label", "baseline_params", "baseline_hash"}
    if extra:
        errs.append(f"unknown field(s): {', '.join(sorted(extra))}")
    kind, ch = spec.get("kind"), spec.get("change")
    if kind not in KINDS:
        return errs + [f"kind must be one of {', '.join(KINDS)}"]
    if not isinstance(ch, dict) or not ch:
        return errs + ["change must be a non-empty object"]
    if "label" in spec and not (isinstance(spec["label"], str) and len(spec["label"]) <= 200):
        errs.append("label must be text of at most 200 characters")
    if spec.get("baseline_hash") is not None and not (isinstance(spec["baseline_hash"], str) and len(spec["baseline_hash"]) == 64):
        errs.append("baseline_hash must be a SHA-256 hex string")
    try:
        clean_params(spec.get("baseline_params") or {})
    except ValueError as e:
        errs.append(f"baseline_params: {e}")
    if kind == "parameter":
        try:
            if not clean_params(ch):
                errs.append("no parameter changed")
        except ValueError as e:
            errs.append(str(e))
    elif kind == "exclusion":
        if set(ch) - {"keys", "detectors", "window_mjd"}:
            errs.append("exclusion takes keys, detectors or window_mjd")
        keys = ch.get("keys", [])
        if not (isinstance(keys, list) and len(keys) <= MAX_EXCLUDED_KEYS and all(isinstance(k, str) and 3 <= len(k) <= 96 for k in keys)):
            errs.append(f"keys must be a list of at most {MAX_EXCLUDED_KEYS} observation keys")
        dets = ch.get("detectors", [])
        if not (isinstance(dets, list) and all(isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 6 for d in dets)):
            errs.append("detectors must be integers 1-6")
        w = ch.get("window_mjd")
        if w is not None and not (isinstance(w, list) and len(w) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in w) and w[0] < w[1]):
            errs.append("window_mjd must be [start, end] with start < end")
        if not (keys or dets or w):
            errs.append("nothing to exclude")
    elif kind == "threshold":
        for k, v in ch.items():
            if k not in THRESHOLD_BOUNDS:
                errs.append(f"threshold {k} cannot be varied (allowed: {', '.join(THRESHOLD_BOUNDS)})")
            elif isinstance(v, bool) or not isinstance(v, (int, float)) or not THRESHOLD_BOUNDS[k][0] <= v <= THRESHOLD_BOUNDS[k][1]:
                errs.append(f"{k} must be between {THRESHOLD_BOUNDS[k][0]} and {THRESHOLD_BOUNDS[k][1]}")
    elif kind == "error_scale":
        k = ch.get("photometric_error_factor")
        if set(ch) != {"photometric_error_factor"} or isinstance(k, bool) or not isinstance(k, (int, float)) or not ERROR_SCALE_BOUNDS[0] < k <= ERROR_SCALE_BOUNDS[1]:
            errs.append(f"error_scale takes photometric_error_factor, greater than {ERROR_SCALE_BOUNDS[0]} and at most {ERROR_SCALE_BOUNDS[1]}")
    elif kind == "method":
        if ch != {"variability_method": "PAIRDIFF-1"}:
            errs.append("method takes {\"variability_method\": \"PAIRDIFF-1\"} (brightness without reference calibration)")
    return errs


# ---------------------------------------------------------------------------- re-assessment from a record
def _ev(record: dict) -> dict:
    out = {}
    for e in record["events"]:
        out.setdefault(e["step"], e)
    return out


def reassess(record: dict, thresholds: dict | None = None, flux_pairs: list[dict] | None = None) -> dict:
    """Outcomes recomputed from the recorded inputs (ASSESS-2 functions, optional threshold overrides)."""
    ev = _ev(record)
    rec = {o["question"]: o for o in ev["assess"]["data"]["outcomes"]}
    out = {"data_quality": rec.get("data_quality")}
    var = ev.get("variability", {}).get("data") or {}
    pairs = ev.get("pairs", {}).get("data") or {}
    if "variability" in ev and "pairs" in var:
        acc = pairs.get("accepted", [])
        n = (acc if isinstance(acc, int) else len(acc)) + sum((pairs.get("rejection_reasons") or {}).values())
        sp = (ev.get("spectral_context", {}).get("data") or {}).get("pairs", [])
        out["variability"] = assess.assess_variability(flux_pairs if flux_pairs is not None else var["pairs"], sp, n,
                                                       var.get("calibration_check"), thresholds=thresholds)
    else:
        out["variability"] = rec.get("variability")
    a = ev.get("astrometry")
    if a and a["status"] == "ok":
        m = a["data"]
        times = [e["t_mjd"] for e in m.get("epochs", [])]
        out["motion"] = assess.assess_motion(m, {"pmra": m["catalogue"]["pmra"], "pmdec": m["catalogue"]["pmdec"]}, len(m["series"]),
                                             [s["plate_rms_mas"] for s in m["series"]], [(y - x) / 365.25 for x, y in zip(times, times[1:])],
                                             None, thresholds=thresholds)
    else:
        out["motion"] = rec.get("motion")
    return json.loads(json.dumps(out, default=str))


def _scale_pairs(pairs: list[dict], k: float) -> list[dict]:
    out = copy.deepcopy(pairs)
    for p in out:
        for f in ("flux_err_a_ujy", "flux_err_b_ujy", "sigma_ujy", "delta_err_ujy"):
            if isinstance(p.get(f), (int, float)):
                p[f] = p[f] * k
        if isinstance(p.get("z"), (int, float)):
            p["z"] = p["z"] / k
        d = p.get("differential") or {}
        for f in ("z_cal", "z_cal_scaled"):
            if isinstance(d.get(f), (int, float)):
                d[f] = d[f] / k
    return out


def _raw_only(pairs: list[dict]) -> list[dict]:
    out = copy.deepcopy(pairs)
    for p in out:
        if isinstance(p.get("differential"), dict):
            p["differential"] = {**p["differential"], "calibrated": False}
    return out


# ---------------------------------------------------------------------------- comparison
def metrics(outcomes: dict, record: dict | None = None) -> dict:
    m = (outcomes.get("motion") or {}).get("evidence", {}) or {}
    v = (outcomes.get("variability") or {}).get("evidence", {}) or {}
    s = (outcomes.get("variability") or {}).get("sensitivity", {}) or {}
    out = {"category." + q: (o or {}).get("category") for q, o in sorted(outcomes.items())}
    out.update({"motion.pm_measured_mas_yr": m.get("pm_measured_mas_yr"), "motion.pm_sigma_mas_yr": m.get("pm_sigma_mas_yr"),
                "brightness.n_matched_pairs": v.get("n_matched_pairs"),
                "brightness.n_calibrated_above_threshold": v.get("n_calibrated_above_threshold"),
                "brightness.n_uncalibrated_above_threshold": v.get("n_uncalibrated_above_threshold"),
                "brightness.max_abs_z_calibrated": v.get("max_abs_z_calibrated"),
                "brightness.min_detectable_fractional_change_at_threshold": s.get("min_detectable_fractional_change_5sigma")})
    if record is not None:
        ev = _ev(record)
        d = (ev.get("discover") or {}).get("data", {})
        out["input.observations_included"] = (d.get("n_total") or 0) - (d.get("n_excluded") or 0) if d else None
        out["input.observations_excluded_by_scenario"] = sum(1 for e in record["events"] if e["step"] == "select"
                                                            and (e.get("data") or {}).get("code") == "counterfactual_exclusion")
    return out


def _same(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def compare(base: dict, cf: dict) -> list[dict]:
    rows = []
    for k in sorted(set(base) | set(cf)):
        rows.append({"metric": k, "baseline": base.get(k), "counterfactual": cf.get(k), "changed": not _same(base.get(k), cf.get(k))})
    return rows


def record_hash(record: dict) -> str:
    """The investigation record's content hash, recomputed (same rule as report.Investigation.to_dict)."""
    from .provenance import stable_hash
    return stable_hash({k: v for k, v in record.items() if k not in ("created_at", "software", "content_hash")})


def _outcomes(record: dict) -> dict:
    return {o["question"]: o for o in _ev(record)["assess"]["data"]["outcomes"]}


def _explain(kind: str, change: dict, rows: list[dict]) -> list[str]:
    changed = [r for r in rows if r["changed"]]
    if not changed:
        return ["No compared output changed: under this change the analysis gives the same results as the baseline."]
    cause = {"parameter": "the changed analysis parameter(s) " + ", ".join(f"{k} = {v}" for k, v in change.items()),
             "exclusion": "the excluded observations (" + ", ".join(f"{k}: {v}" for k, v in change.items()) + ")",
             "threshold": "the changed threshold(s) " + ", ".join(f"{k} = {v}" for k, v in change.items()),
             "error_scale": f"the simulated error-model change (uncertainties × {change.get('photometric_error_factor')})",
             "method": "deciding brightness with PAIRDIFF-1 alone (no reference calibration)"}[kind]
    lines = [f"Every difference below follows from {cause}; nothing else differs between the two runs."]
    for r in changed:
        if r["metric"].startswith("category."):
            lines.append(f"{r['metric'][9:].replace('_', ' ')}: {r['baseline']} → {r['counterfactual']}.")
    return lines


def run(load, target_id: str, spec: dict, baseline_record: dict | None = None) -> dict:
    """Execute one scenario. `load(target_id)` returns the bundle; the baseline is recomputed unless given."""
    errs = validate(spec)
    if errs:
        return {"method": METHOD, "status": "refused", "errors": errs}
    kind, ch = spec["kind"], spec["change"]
    bparams = clean_params(spec.get("baseline_params") or {})
    b = load(target_id)
    base = baseline_record or json.loads(json.dumps(analysis.run(b, bparams).to_dict(), default=str))
    base_hash = base["content_hash"]
    if spec.get("baseline_hash") and spec["baseline_hash"] != base_hash:
        return {"method": METHOD, "status": "refused",
                "errors": [f"the stated baseline {spec['baseline_hash'][:12]}… is not the run these parameters give ({base_hash[:12]}…)"]}
    rerun, cf_record, notes = False, None, []
    if kind in ("parameter", "exclusion"):
        rerun = True
        if kind == "parameter":
            params = {**bparams, **clean_params(ch)}
            cf_b = b
        else:
            params = bparams
            disc = copy.deepcopy(b.discovery)
            keys, dets, w = set(ch.get("keys", [])), set(ch.get("detectors", [])), ch.get("window_mjd")
            unknown = sorted(keys - {o["key"] for o in disc.get("observations", [])})
            if unknown:
                return {"method": METHOD, "status": "refused", "errors": [f"unknown observation key(s): {', '.join(unknown[:5])}"]}
            n = 0
            for o in disc.get("observations", []):
                hit = o["key"] in keys or o.get("detector") in dets or (w and o.get("t_mid_mjd") is not None and w[0] <= o["t_mid_mjd"] <= w[1])
                if hit and o.get("included"):
                    o["included"], o["exclusion_reason"], o["exclusion_code"] = False, "counterfactual exclusion (scenario)", "counterfactual_exclusion"
                    n += 1
            if n == 0:
                return {"method": METHOD, "status": "refused", "errors": ["the exclusion matches no included observation"]}
            notes.append(f"{n} included observation(s) marked excluded in a copy of the bundle index; the bundle on disk is unchanged.")
            cf_b = dataclasses.replace(b, discovery=disc)
        cf_record = json.loads(json.dumps(analysis.run(cf_b, params).to_dict(), default=str))
        cf_out = _outcomes(cf_record)
    else:
        if kind == "threshold":
            cf_out = reassess(base, thresholds=ch)
        elif kind == "error_scale":
            var = (_ev(base).get("variability") or {}).get("data") or {}
            cf_out = reassess(base, flux_pairs=_scale_pairs(var.get("pairs", []), float(ch["photometric_error_factor"])))
            notes.append("Only photometric uncertainties are perturbed; motion is unchanged by construction.")
        else:
            var = (_ev(base).get("variability") or {}).get("data") or {}
            cf_out = reassess(base, flux_pairs=_raw_only(var.get("pairs", [])))
        notes.append("Re-assessed from the recorded inputs with the ASSESS-2 functions; the pipeline was not re-run.")
    # the baseline is never altered: recompute its hash from its content and compare
    intact = record_hash(base) == base_hash
    rows = compare(metrics(_outcomes(base), base), metrics(cf_out, cf_record if cf_record else base))
    if not rerun:   # inputs are the baseline's own; the input rows are identical by construction
        rows = [r for r in rows if not r["metric"].startswith("input.")]
    scen = {"schema": SCHEMA_ID, "target_id": target_id, "kind": kind, "change": ch, "label": spec.get("label") or "",
            "baseline_params": bparams, "baseline_hash": base_hash}
    out = {"method": METHOD, "status": "completed", "scenario": scen, "scenario_hash": canon.digest(scen),
           "value_label": LABEL[kind], "legend": LEGEND, "rerun": rerun,
           "baseline": {"content_hash": base_hash, "categories": {q: o["category"] for q, o in _outcomes(base).items()}, "intact": intact},
           "counterfactual": {"content_hash": cf_record["content_hash"] if cf_record else None,
                              "categories": {q: (o or {}).get("category") for q, o in cf_out.items()},
                              "statements": {q: (o or {}).get("statement") for q, o in cf_out.items()}},
           "comparison": rows, "explanation": _explain(kind, ch, rows), "notes": notes,
           "synthetic": base.get("parameters", {}).get("bundle_kind") == "synthetic",
           "caveat": "A counterfactual shows how the stated analysis responds to the stated change. It is not an observation and "
                     "does not describe an alternative physical reality; the original investigation is unchanged."}
    return out
