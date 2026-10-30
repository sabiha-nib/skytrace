"""Synthetic Observatory (SYNOBS-1) and Observation Design Lab (OBSDES-1).

SYNOBS-1 generates a labelled SYNTHETIC bundle from an explicit, bounded scenario (motion, brightness per pass,
noise, background, brightness of the target, per-pass instrumental gain, reference-star position errors, PSF width,
observation days and detector positions), runs the unchanged analysis pipeline on it, and compares the pipeline's
output with the generator's ground truth. It exists to test methods, not to stand in for observations: bundles are
written under data/synthlab/ (never data/bundles/ or fixtures/), carry SYNTHETIC = T and origin "synthetic", and are
named SYN-LAB-<hash>. The same scenario (seed included) always produces the same bytes and the same result.

"Expected" outcomes are stated by an explicit rule: an injected effect is expected to be found only when it exceeds
the sensitivity the pipeline itself reports for that data set (5σ motion sensitivity; minimum detectable fractional
change at the threshold); below that, a non-detection is the expected answer. Agreement on synthetic scenarios tests
the software's behaviour on its own generator; it does not establish performance on real SPHEREx data.

OBSDES-1 compares hypothetical observation schedules for one truth by generating each with SYNOBS-1 and reporting
what each schedule recovers. The schedules are hypothetical: Skytrace does not schedule or command any telescope, and
the generator's noise and detector model are illustrative, not SPHEREx performance.
"""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

from . import analysis, bundle as bmod, canon, synthetic
from .schema import check

METHOD = "SYNOBS-1"
DESIGN_METHOD = "OBSDES-1"
SCHEMA_ID = "skytrace.synthetic_scenario/1"
GENERATOR = f"{synthetic.GEN} via {METHOD}"
ROOT = Path(os.environ.get("SKYTRACE_SYNTHLAB_DIR") or Path(__file__).resolve().parents[2] / "data" / "synthlab")
MAX_KEEP = 24
POSITIONS = {"A": 520.0, "B": 1420.0, "C": 1010.0}   # detector y position of the target: sets the wavelength sampled
FIELD = (150.0, 10.0)
FIXED_STAMP = "2026-01-01T00:00:00+00:00"   # provenance stamp of generated files: fixed for byte-reproducibility, not a clock reading

N = lambda lo, hi: {"t": "num", "min": lo, "max": hi}   # noqa: E731
_PASS = {"t": "obj", "f": {"day": [N(0, 1500), True], "position": [{"t": "str", "enum": list(POSITIONS)}, True],
                           "brightness": [N(0.2, 2.0), True], "gain": [N(0.8, 1.25), False]}}
SPEC = {"t": "obj", "f": {
    "schema": [{"t": "const", "v": SCHEMA_ID}, False],
    "label": [{"t": "str", "max": 200}, False],
    "seed": [{"t": "int", "min": 0, "max": 2 ** 31 - 1}, True],
    "pm_mas_yr": [{"t": "arr", "items": N(-6000, 6000), "max": 2}, True],
    "passes": [{"t": "arr", "max": 6, "items": _PASS}, True],
    "noise": [N(0.004, 0.05), False],
    "sky": [N(0.1, 1.0), False],
    "target_flux_scale": [N(0.05, 3.0), False],
    "reference_offset_arcsec": [N(0.0, 10.0), False],
    "psf_sigma_scale": [N(0.7, 1.5), False],
}}
DEFAULTS = {"noise": 0.012, "sky": 0.3, "target_flux_scale": 1.0, "reference_offset_arcsec": 4.0, "psf_sigma_scale": 1.0}

TEMPLATES = [
    {"id": "fast-mover", "title": "Fast-moving star, constant brightness", "scenario": {
        "seed": 201, "pm_mas_yr": [2500.0, -1800.0],
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 1.0}, {"day": 547, "position": "C", "brightness": 1.0}]}},
    {"id": "slow-mover", "title": "Motion below the expected sensitivity", "scenario": {
        "seed": 102, "pm_mas_yr": [60.0, 40.0],
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 1.0}, {"day": 547, "position": "C", "brightness": 1.0}]}},
    {"id": "dimming", "title": "Star that dims by 25% in one pass", "scenario": {
        "seed": 103, "pm_mas_yr": [5.0, -10.0],
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 0.75}, {"day": 547, "position": "B", "brightness": 1.0}]}},
    {"id": "gain-offset", "title": "Instrumental gain change, constant star", "scenario": {
        "seed": 202, "pm_mas_yr": [5.0, -10.0],
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 1.0, "gain": 0.85}, {"day": 547, "position": "B", "brightness": 1.0}]}},
    {"id": "faint", "title": "Faint target (low signal-to-noise)", "scenario": {
        "seed": 201, "pm_mas_yr": [800.0, 0.0], "target_flux_scale": 0.08,
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 1.0}, {"day": 547, "position": "C", "brightness": 1.0}]}},
    {"id": "blend", "title": "Failure case: a reference star on the target's path", "scenario": {
        "seed": 101, "pm_mas_yr": [2500.0, -1800.0],
        "passes": [{"day": 0, "position": "A", "brightness": 1.0}, {"day": 182, "position": "B", "brightness": 1.0},
                   {"day": 365, "position": "A", "brightness": 1.0}, {"day": 547, "position": "C", "brightness": 1.0}]}},
]


def validate(sc) -> list[str]:
    errs = check(SPEC, sc)
    if errs:
        return errs
    if len(sc["pm_mas_yr"]) != 2:
        errs.append("$.pm_mas_yr: give [east, north] in mas/yr")
    if len(sc["passes"]) < 2:
        errs.append("$.passes: at least 2 passes are needed")
    if errs:
        return errs
    days = [p["day"] for p in sc["passes"]]
    if days != sorted(days) or len(set(days)) != len(days):
        errs.append("$.passes: days must be strictly increasing")
    if any(b - a < 5 for a, b in zip(days, days[1:])):
        errs.append("$.passes: passes must be at least 5 days apart (each pass has two visits 2.5 days apart)")
    return errs


def normalise(sc: dict) -> dict:
    out = {"schema": SCHEMA_ID, **{k: sc.get(k, v) for k, v in DEFAULTS.items()}, "seed": int(sc["seed"]),
           "pm_mas_yr": [float(x) for x in sc["pm_mas_yr"]],
           "passes": [{"day": float(p["day"]), "position": p["position"], "brightness": float(p["brightness"]),
                       "gain": float(p.get("gain", 1.0))} for p in sc["passes"]]}
    for k in DEFAULTS:
        out[k] = float(out[k])
    return out


def scenario_id(sc: dict) -> str:
    return "syn-lab-" + canon.digest(normalise(sc))[:12]


def _gen_spec(sc: dict, tid: str) -> dict:
    t0 = 60900.0
    off = sc["reference_offset_arcsec"]
    gains = [p["gain"] for p in sc["passes"]]
    spec = {"target_id": tid, "name": tid.upper(), "seed": sc["seed"], "ra": FIELD[0], "dec": FIELD[1],
            "pmra": sc["pm_mas_yr"][0], "pmdec": sc["pm_mas_yr"][1],
            "role": "synthetic scenario (Synthetic Observatory)",
            "description": "Generated by the Synthetic Observatory from an explicit scenario; not an observation.",
            "n_refs": 16, "sky": sc["sky"], "noise": sc["noise"], "variability": [p["brightness"] for p in sc["passes"]],
            "sed": lambda wl: 4000.0 * (wl / 1.5) ** -0.5,
            "passes": [(t0 + p["day"], POSITIONS[p["position"]]) for p in sc["passes"]],
            "target_flux_scale": sc["target_flux_scale"], "psf_sigma_scale": sc["psf_sigma_scale"],
            "bad_refs": [(off, 0.0, None)] if off > 0 else [],
            "generated_at": FIXED_STAMP}
    if any(g != 1.0 for g in gains):
        spec["gain_by_pass"] = gains
    return spec


def truth(sc: dict) -> dict:
    b = [p["brightness"] * p["gain"] for p in sc["passes"]]
    by_pos = {}
    for p in sc["passes"]:
        by_pos.setdefault(p["position"], []).append(p["brightness"])
    intrinsic = max((max(v) / min(v) - 1.0 for v in by_pos.values() if len(v) >= 2), default=0.0)
    instrumental = [p["gain"] for p in sc["passes"] if p["gain"] != 1.0]
    return {"pm_mas_yr": sc["pm_mas_yr"], "pm_total_mas_yr": math.hypot(*sc["pm_mas_yr"]),
            "brightness_by_pass": [p["brightness"] for p in sc["passes"]], "recorded_flux_factor_by_pass": b,
            "max_fractional_change_at_repeated_position": intrinsic,
            "positions": [p["position"] for p in sc["passes"]], "instrumental_gain_by_pass": [p["gain"] for p in sc["passes"]],
            "has_instrumental_offset": bool(instrumental), "reference_offset_arcsec": sc["reference_offset_arcsec"],
            "note": "Truth is the generator input. Brightness changes are comparable only between passes at the same detector position "
                    "(the same wavelength); a change between different positions is spectral, not variability."}


def _outs(rec: dict) -> dict:
    ev = next(e for e in rec["events"] if e["step"] == "assess")
    return {o["question"]: o for o in ev["data"]["outcomes"]}


def evaluate(sc: dict, rec: dict) -> dict:
    tr, outs = truth(sc), _outs(rec)
    mo, vo = outs.get("motion", {}), outs.get("variability", {})
    me, ve, vs = mo.get("evidence", {}) or {}, vo.get("evidence", {}) or {}, vo.get("sensitivity", {}) or {}
    rows = []
    fit = next((e["data"].get("fit") for e in rec["events"] if e["step"] == "astrometry" and e["status"] == "ok"), None)
    sig = me.get("pm_sigma_mas_yr")
    sens_pm = 5.0 * sig if sig else None
    if mo.get("category") in ("measurement_failed", "insufficient_data", None) or sens_pm is None:
        exp_m, verdict_m = "not determinable: the pipeline produced no motion sensitivity", "not determinable"
    else:
        present = tr["pm_total_mas_yr"] >= sens_pm
        exp_m = ("motion detected (truth above the 5σ sensitivity)" if present else
                 "no motion at this sensitivity (truth below the 5σ sensitivity)")
        got = mo["category"] in ("motion_detected", "motion_inconsistent")
        verdict_m = "agrees" if got == present else "disagrees"
    err = None
    if fit:
        err = {"east_mas_yr": fit["pm_xi_mas_yr"] - tr["pm_mas_yr"][0], "north_mas_yr": fit["pm_eta_mas_yr"] - tr["pm_mas_yr"][1],
               "east_sigma": (fit["pm_xi_mas_yr"] - tr["pm_mas_yr"][0]) / fit["sig_xi"] if fit.get("sig_xi") else None,
               "north_sigma": (fit["pm_eta_mas_yr"] - tr["pm_mas_yr"][1]) / fit["sig_eta"] if fit.get("sig_eta") else None}
    rows.append({"question": "motion", "truth": f"{tr['pm_total_mas_yr']:.0f} mas/yr", "expected": exp_m, "pipeline": mo.get("category"),
                 "measured": me.get("pm_measured_mas_yr"), "sensitivity": sens_pm, "error": err, "verdict": verdict_m,
                 "rule": "expected = detected iff |pm_true| ≥ 5 × pm_sigma reported by the pipeline"})
    mdc = vs.get("min_detectable_fractional_change_5sigma_best_pair")
    change = tr["max_fractional_change_at_repeated_position"]
    if vo.get("category") in ("insufficient_evidence", None) or mdc is None:
        exp_v, verdict_v = "not determinable: no wavelength-matched pair with a sensitivity", "not determinable"
    else:
        present = change >= mdc
        exp_v = ("brightness change found (truth above the best-pair sensitivity)" if present else
                 "no significant change (truth below the best-pair sensitivity)")
        got = vo["category"] in ("variability_candidate",)
        verdict_v = "agrees" if got == present else "disagrees"
        if present and vo["category"] == "calibration_limited":
            verdict_v = "not confirmed (calibration-limited: the change is significant only without reference calibration)"
        if tr["has_instrumental_offset"] and vo["category"] == "calibration_limited" and not present:
            verdict_v = "agrees (instrumental offset identified as calibration-limited)"
    rows.append({"question": "variability", "truth": f"{change:.0%} change at a repeated position" + (" + instrumental gain change" if tr["has_instrumental_offset"] else ""),
                 "expected": exp_v, "pipeline": vo.get("category"), "measured": ve.get("max_abs_z_calibrated"),
                 "sensitivity": mdc, "error": None, "verdict": verdict_v,
                 "rule": "expected = candidate iff the true fractional change at a repeated position ≥ the best-pair minimum detectable change"})
    fails = {}
    for e in rec["events"]:
        if e["step"] == "measure" and e["status"] in ("rejected", "failed"):
            c = (e.get("data") or {}).get("quality_code") or "rejected"
            fails[c] = fails.get(c, 0) + 1
    return {"truth": tr, "rows": rows, "categories": {q: o["category"] for q, o in outs.items()},
            "failure_behaviour": {"rejected_exposures_by_reason": dict(sorted(fails.items())),
                                  "note": "Exposures the pipeline refused to measure, with its reason codes (e.g. 'blended': another star "
                                          "inside the target aperture). Refusing is the intended behaviour, not an error."},
            "limitation": "Agreement on a generated scenario tests the software against its own generator; it does not establish "
                          "performance on real SPHEREx data."}


def _prune():
    if not ROOT.exists():
        return
    dirs = sorted((p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("syn-lab-")), key=lambda p: p.stat().st_mtime)
    for p in dirs[:-MAX_KEEP]:
        shutil.rmtree(p, ignore_errors=True)


def run(sc: dict) -> dict:
    errs = validate(sc)
    if errs:
        return {"method": METHOD, "status": "refused", "errors": errs}
    n = normalise(sc)
    tid = scenario_id(n)
    out = ROOT / tid
    res_file = out / "scenario_result.json"
    if res_file.exists():
        cached = json.loads(res_file.read_text())
        if bmod.verify(out).get("ok"):
            cached["cache"] = "reused: identical scenario, bundle checksums verified"
            return cached
    ROOT.mkdir(parents=True, exist_ok=True)
    synthetic.build(_gen_spec(n, tid), out)
    m = json.loads((out / "manifest.json").read_text())       # fixed creation stamp: identical scenario → identical manifest
    m["created_at"] = FIXED_STAMP
    m["notes"] += f" Generated by the Synthetic Observatory ({METHOD}); timestamps are fixed for reproducibility."
    bmod.write_json(out / "manifest.json", m)
    b = bmod.load(out)
    rec = json.loads(json.dumps(analysis.run(b, {}).to_dict(), default=str))
    ev = evaluate(n, rec)
    res = {"method": METHOD, "status": "completed", "schema": SCHEMA_ID, "scenario": n, "scenario_id": tid, "label": sc.get("label", ""),
           "generator": GENERATOR, "synthetic": True, "bundle_manifest_sha256": bmod.sha256_file(out / "manifest.json"),
           "n_files": len(b.manifest["files"]), "record_content_hash": rec["content_hash"], "evaluation": ev,
           "assumptions": ["illustrative PSF, noise, linear-variable-filter gradient and flag layout (not SPHEREx calibration)",
                           "16 reference stars with catalogue-quality positions, one offset by reference_offset_arcsec",
                           "two visits per pass, 2.5 days apart, six detectors each"],
           "cache": "generated"}
    (out / "scenario_result.json").write_text(json.dumps(res, indent=1))
    _prune()
    return res


# ---------------------------------------------------------------------------- Observation Design Lab
DESIGN_MAX = 3


def design(truth_sc: dict, schedules: list[dict]) -> dict:
    """Compare hypothetical schedules (lists of passes) for one truth (pm, brightness by position)."""
    if not isinstance(schedules, list) or not 2 <= len(schedules) <= DESIGN_MAX:
        return {"method": DESIGN_METHOD, "status": "refused", "errors": [f"give 2 to {DESIGN_MAX} schedules"]}
    rows, errs = [], []
    for i, s in enumerate(schedules):
        if not isinstance(s, dict) or not isinstance(s.get("passes"), list) or not isinstance(s.get("name"), str):
            errs.append(f"schedule {i + 1}: needs a name and passes")
            continue
        sc = {**truth_sc, "passes": s["passes"]}
        e = validate(sc)
        if e:
            errs += [f"schedule {i + 1}: {x}" for x in e]
    if errs:
        return {"method": DESIGN_METHOD, "status": "refused", "errors": errs}
    for s in schedules:
        r = run({**truth_sc, "passes": s["passes"]})
        ev = r["evaluation"]
        m = next(x for x in ev["rows"] if x["question"] == "motion")
        v = next(x for x in ev["rows"] if x["question"] == "variability")
        days = [p["day"] for p in s["passes"]]
        rows.append({"name": s["name"][:80], "scenario_id": r["scenario_id"], "n_passes": len(days), "span_days": days[-1] - days[0],
                     "positions": "".join(p["position"] for p in s["passes"]),
                     "motion_sensitivity_mas_yr": m["sensitivity"], "motion_category": m["pipeline"], "motion_verdict": m["verdict"],
                     "brightness_sensitivity": v["sensitivity"], "brightness_category": v["pipeline"], "brightness_verdict": v["verdict"]})
    brief = brief_md(truth_sc, rows)
    return {"method": DESIGN_METHOD, "status": "completed", "truth": truth(normalise({**truth_sc, "passes": schedules[0]["passes"]})),
            "schedules": rows, "brief": brief,
            "basis": "Each schedule was generated by SYNOBS-1 with the same truth and seed and analysed by the unchanged pipeline.",
            "caveat": "Hypothetical schedules on generated data. Skytrace does not schedule or command a telescope; SPHEREx's survey "
                      "cadence is set by the mission. Sensitivities come from an illustrative noise model."}


def brief_md(truth_sc: dict, rows: list[dict]) -> str:
    L = ["# Observation planning brief (hypothetical)", "",
         "> Generated by Skytrace OBSDES-1 from SYNTHETIC scenarios. Not a telescope schedule; not SPHEREx performance.", "",
         f"Truth used for every schedule: proper motion {truth_sc['pm_mas_yr']} mas/yr, seed {truth_sc['seed']}.", "",
         "| Schedule | Passes | Span (d) | Positions | Motion 5σ sensitivity (mas/yr) | Motion result | Brightness sensitivity | Brightness result |",
         "|---|---:|---:|---|---:|---|---:|---|"]
    for r in rows:
        ms = f"{r['motion_sensitivity_mas_yr']:.0f}" if r["motion_sensitivity_mas_yr"] else "—"
        bs = f"{r['brightness_sensitivity']:.1%}" if r["brightness_sensitivity"] else "—"
        L.append(f"| {r['name']} | {r['n_passes']} | {r['span_days']:.0f} | {r['positions']} | {ms} | {r['motion_category']} ({r['motion_verdict']}) | "
                 f"{bs} | {r['brightness_category']} ({r['brightness_verdict']}) |")
    L += ["", "Requirements this comparison can inform: the time span needed for a motion sensitivity, and the need for repeated "
          "detector positions (the same wavelength) to compare brightness. It cannot inform instrument availability or real noise."]
    return "\n".join(L) + "\n"
