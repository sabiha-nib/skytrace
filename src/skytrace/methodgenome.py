"""Method genome (METHOD-DNA-1): every analysis method of the pipeline as a structured, versioned object.

One entry per method that produces a recorded value: identity, purpose, typed inputs and outputs (with units), assumptions,
parameters, a mathematical description, dependencies, applicable and unsupported data, limitations, validation data,
known-answer tests, version history and the module that implements it. The descriptions restate the implementations'
own docstrings (`science/*.py`); the tests named here are checked to exist (`tests/unit/test_epistemic.py`).

Health is reported as facts, never as a score: how many known-answer tests are defined (and verified to exist), whether
the method is covered by the pipeline-level determinism check, whether its dependencies are importable here, and which
documentation fields are filled. Test coverage is software evidence; it is not scientific validity.

Output status follows one stated rule (EPI-1): "measured" = obtained by fitting or summing pixels of one exposure;
"derived" = arithmetic on recorded values without a further model; "model-dependent" = needs a fitted model or a
modelling assumption beyond the measurement (plate solution, motion fit, reference calibration, error-scale correction).
"""

from __future__ import annotations

import ast
import importlib.util
from functools import lru_cache
from pathlib import Path

METHOD = "METHOD-DNA-1"
ROOT = Path(__file__).resolve().parents[2]

# unit vocabulary used by SCI-COMP type checking: quantity type -> unit
QTYPES = {
    "image": "MJy/sr", "variance": "(MJy/sr)^2", "flags": "bitmask", "flux": "µJy", "flux_err": "µJy",
    "position_px": "px", "position_mas": "mas", "wavelength": "µm", "bandwidth": "µm", "time_mjd": "MJD", "time_jyear": "Julian year",
    "z": "dimensionless (σ)", "ratio": "dimensionless", "pm": "mas/yr", "pm_err": "mas/yr", "catalogue": "Gaia-like records",
    "category": "enumerated outcome", "plate": "affine coefficients (deg/px)", "parallax": "mas", "scale": "dimensionless",
}


def _m(mid, family, purpose, inputs, outputs, assumptions, parameters, math, deps, applicable, unsupported, limitations,
       validation, tests, versions, module, status, propagation):
    return {"id": mid, "family": family, "purpose": purpose, "inputs": inputs, "outputs": outputs, "assumptions": assumptions,
            "parameters": parameters, "math": math, "dependencies": deps, "applicable": applicable, "unsupported": unsupported,
            "limitations": limitations, "validation_data": validation, "known_answer_tests": tests, "versions": versions,
            "module": module, "output_status": status, "uncertainty_propagation": propagation}


def io(name, qtype):
    return {"name": name, "type": qtype, "unit": QTYPES[qtype]}


T = "tests/unit/"
METHODS = [
    _m("FLAGPOL-1", "measurement", "Decide which FLAGS bits reject or warn a pixel.",
       [io("FLAGS extension", "flags")], [io("rejected/warned pixel mask", "flags")],
       ["bit numbers come from the file's FLAGS header or IRSA documentation; unknown bits are reported, never guessed"],
       [], "pixel rejected if any REJECT bit is set; warned if any WARN bit; MP_SOURCE informational", [],
       ["SPHEREx Level-2 images with a FLAGS extension"], ["files whose flag bits are undefined in header and documentation (reported as unresolved)"],
       ["only MP_TRANSIENT (bit 0) and MP_SOURCE (bit 21) are documented in what was available"],
       ["synthetic fixtures (FLAGS headers define MP_* keywords)"],
       [T + "test_wavelength_flags.py::test_flags_documented_fallback_reports_unresolved", T + "test_wavelength_flags.py::test_flags_from_header_and_mask"],
       [{"id": "FLAGPOL-1", "change": "initial policy"}], "src/skytrace/science/flags.py", "measured", "none (a mask has no uncertainty)"),
    _m("CENTROID-G2D-1", "measurement", "Position of the target (and reference stars) in one exposure.",
       [io("IMAGE", "image"), io("VARIANCE", "variance"), io("pixel mask", "flags")], [io("centroid x, y", "position_px")],
       ["the point-spread function is approximated by an elliptical 2-D Gaussian plus constant background",
        "VARIANCE describes the per-pixel noise"],
       ["fit_half_size_px"], "weighted least squares of an elliptical Gaussian + constant; covariance from the Jacobian, scaled by χ²ν when χ²ν > 1",
       ["FLAGPOL-1"], ["isolated point sources in a SPHEREx image stamp"], ["extended or blended sources (reported as blended)"],
       ["SPHEREx PSF is undersampled in some bands: the Gaussian is an approximation"],
       ["synthetic injections with known positions"],
       [T + "test_measurement.py::test_centroid_recovers_subpixel_position", T + "test_measurement.py::test_centroid_uncertainty_is_calibrated",
        T + "test_measurement.py::test_centroid_ignores_masked_pixels", T + "test_measurement.py::test_centroid_reports_failure_instead_of_guessing"],
       [{"id": "CENTROID-G2D-1", "change": "initial method"}], "src/skytrace/science/centroid.py", "measured",
       "Jacobian covariance of the fit (σx, σy, cov), inflated by √χ²ν when χ²ν > 1"),
    _m("APPHOT-1", "measurement", "Flux density of the target in one exposure.",
       [io("IMAGE", "image"), io("VARIANCE", "variance"), io("pixel mask", "flags"), io("centroid", "position_px")],
       [io("aperture flux", "flux"), io("flux error", "flux_err")],
       ["a local sky annulus removes zodiacal light and smooth background", "VARIANCE describes the per-pixel noise",
        "no aperture correction: the result is an aperture flux"],
       ["aperture_radius_px"], "F = Σ w (I − sky) Ω_pix; Var = Σ w² VARIANCE + (Σ w)² Var(sky mean); MJy/sr → µJy via 1e12 Ω_pix",
       ["FLAGPOL-1", "CENTROID-G2D-1"], ["point sources in calibrated surface-brightness images (MJy/sr)"],
       ["images in other units", "apertures touching rejected pixels (returned as flagged, not measured)"],
       ["aperture fluxes from different detectors or wavelengths are not comparable without an aperture correction"],
       ["synthetic injections with known fluxes"],
       [T + "test_measurement.py::test_photometry_recovers_flux_and_errors", T + "test_measurement.py::test_photometry_flagged_returns_nan",
        T + "test_measurement.py::test_photometry_no_sky_and_off_image"],
       [{"id": "APPHOT-1", "change": "initial method"}], "src/skytrace/science/photometry.py", "measured",
       "variance summed over aperture weights plus the sky-mean variance term"),
    _m("WLMATCH-2", "comparison rule", "Decide which pairs of exposures sample the same wavelength (and may be compared in flux).",
       [io("wavelength at target", "wavelength"), io("bandwidth", "bandwidth"), io("detector and release", "category")],
       [io("accepted / rejected pair with reason code", "category")],
       ["the linear variable filter maps detector position to wavelength through the WCS-WAVE table"],
       ["wavelength_tolerance_channels", "wavelength_margin_um", "photometry_same_release"],
       "accept iff same detector, same release, both usable, and |Δλ| + margin ≤ tolerance × min(bandwidth)", [],
       ["SPHEREx exposures of one target"], ["pairs from different detectors or releases (rejected with a code)"],
       ["residual wavelength mismatch within the tolerance is not modelled; it is recorded per pair"],
       ["synthetic fixtures with known wavelength layout"],
       [T + "test_wavelength_flags.py::test_matched_pair_accepted", T + "test_wavelength_flags.py::test_wavelength_mismatch_rejected",
        T + "test_wavelength_flags.py::test_different_detector_rejected_even_if_close_in_wavelength", T + "test_calibration_v2.py::test_pair_codes_structured"],
       [{"id": "WLMATCH-1", "change": "same detector, |Δλ| ≤ tolerance × bandwidth, usable photometry"},
        {"id": "WLMATCH-2", "change": "adds the wavelength margin and the same-release condition"}],
       "src/skytrace/science/wavelength.py", "derived", "none: a pass/fail rule; the residual Δλ is recorded, not propagated"),
    _m("PAIRDIFF-1", "comparison", "Significance of a flux difference within one wavelength-matched pair.",
       [io("flux a, b", "flux"), io("errors a, b", "flux_err")], [io("Δ", "flux"), io("σ", "flux_err"), io("z", "z"), io("ratio", "ratio")],
       ["the stated per-measurement errors are Gaussian and independent"], [],
       "Δ = f_b − f_a; σ = √(σ_a² + σ_b²); z = Δ/σ; ratio = f_b/f_a", ["WLMATCH-2", "APPHOT-1"],
       ["accepted WLMATCH-2 pairs with usable photometry"], ["pairs WLMATCH-2 rejected"],
       ["z is not a probability; exposure-level calibration offsets are not removed"],
       ["synthetic fixtures (syn-var-1 injects a change)"], [T + "test_discovery.py::test_uncertainty_recomputes_logged_values_exactly"],
       [{"id": "PAIRDIFF-1", "change": "initial method"}], "src/skytrace/science/variability.py", "derived", "quadrature sum of the two flux errors"),
    _m("PAIRDIFF-2", "comparison", "Reference-calibrated significance: removes exposure-level calibration offsets using reference stars.",
       [io("target fluxes a, b", "flux"), io("reference-star fluxes a, b", "flux")], [io("calibrated ratio", "ratio"), io("z_cal", "z")],
       ["reference stars are constant between the two exposures", "each reference star is itself wavelength-matched under WLMATCH-2"],
       [], "m = median(f_b/f_a over ≥ 3 references with SNR ≥ 10); z_cal from the target ratio relative to m, with the references' ratio scatter",
       ["PAIRDIFF-1", "WLMATCH-2", "APPHOT-1"], ["pairs with ≥ 3 matched reference stars"], ["pairs with fewer references (left uncalibrated, counted)"],
       ["a variable reference star biases m; colour differences between target and references are not modelled"],
       ["synthetic gain-change scenarios"], [T + "test_calibration_v2.py::test_pairdiff2_removes_calibration_offset", T + "test_calibration_v2.py::test_pairdiff2_needs_three_matched_refs"],
       [{"id": "PAIRDIFF-2", "change": "added in skytrace-analysis/2"}], "src/skytrace/science/variability.py", "model-dependent",
       "target and reference ratio scatter combined; then divided by the CALCHECK-1 scale in ASSESS-2"),
    _m("CALCHECK-1", "error-model check", "Whether the stated photometric errors describe constant reference stars.",
       [io("normalised reference flux differences", "z")], [io("robust scatter (error scale)", "scale")],
       ["reference stars are constant"], [], "scale = 1.4826 × MAD of the reference stars' normalised differences", ["PAIRDIFF-2"],
       ["runs with calibrated pairs"], ["runs without matched reference stars (not available)"],
       ["one scale for the whole run; detector or brightness dependence is not modelled"],
       ["synthetic fixtures"], [T + "test_calibration_v2.py::test_robust_scatter"],
       [{"id": "CALCHECK-1", "change": "added in skytrace-analysis/2"}], "src/skytrace/science/variability.py", "model-dependent",
       "scales z by 1/max(1, scale) in ASSESS-2 (an error-model correction, not a propagated variance)"),
    _m("REFSEL-2", "selection", "Which catalogue stars are good astrometric references.",
       [io("catalogue records", "catalogue")], [io("kept / rejected references with codes", "category")],
       ["RUWE ≤ 1.4 marks a well-fitted single star (Lindegren et al. 2021)"], ["reference_quality_cut"],
       "reject RUWE > 1.4, duplicated_source, astrometric_params_solved < 31; missing fields accepted and counted", [],
       ["Gaia DR3-like catalogues"], ["catalogues without proper motions"], ["missing RUWE is accepted (counted), so some references are unchecked"],
       ["synthetic catalogues"], [T + "test_calibration_v2.py::test_refsel2_cuts_and_counts"],
       [{"id": "REFSEL-1", "change": "every star in G 10–17.5 with a proper motion"}, {"id": "REFSEL-2", "change": "adds RUWE, duplicate and solution-type cuts"}],
       "src/skytrace/science/refsel.py", "derived", "none"),
    _m("DIFFAST-1/PLATE-LOO-1", "astrometry", "Map the target's pixel position to the sky using reference stars in the same exposure.",
       [io("target centroid", "position_px"), io("reference centroids", "position_px"), io("catalogue positions at epoch", "catalogue")],
       [io("tangent-plane position ξ, η", "position_mas"), io("plate solution", "plate")],
       ["a 6-parameter affine map describes pixel → tangent plane over the cutout", "reference stars are correctly propagated to the epoch"],
       [], "weighted affine fit (x, y) → (ξ, η) with leave-one-out outlier rejection; target position and covariance propagated through the fit",
       ["CENTROID-G2D-1", "REFSEL-2", "EPHEM-AA-LP-1"], ["exposures with ≥ 3 usable reference stars"], ["exposures without references (no_references, plate_failed)"],
       ["residual non-affine distortion is reported as plate RMS, not modelled"], ["synthetic fixtures with known transforms"],
       [T + "test_measurement.py::test_plate_solution_recovers_transform_and_rejects_outlier"],
       [{"id": "DIFFAST-1/PLATE-LOO-1", "change": "initial method"}], "src/skytrace/science/astrometry.py", "model-dependent",
       "centroid covariance and plate-parameter covariance propagated linearly"),
    _m("EPHEM-AA-LP-1", "astrometry", "Observer position for the parallax correction.",
       [io("epoch", "time_jyear"), io("catalogue parallax", "parallax")], [io("parallax offset", "position_mas")],
       ["SPHEREx's barycentric position equals Earth's to < 1e-5 mas effect", "Astronomical Almanac low-precision solar coordinates (0.01° in longitude)"],
       ["apply_parallax"], "Earth position = − geocentric Sun; offset from the parallax factors", [],
       ["dates 1950–2050"], ["dates outside 1950–2050"], ["heliocentric vs barycentric difference ≤ 0.01 × parallax, recorded as a systematic bound"],
       ["published ephemeris values"], [T + "test_ephemeris.py::test_parallax_ellipse_amplitude_and_phase", T + "test_ephemeris.py::test_march_equinox_longitude"],
       [{"id": "EPHEM-AA-LP-1", "change": "initial method"}], "src/skytrace/science/ephemeris.py", "model-dependent",
       "none propagated; a systematic bound of 0.01 × parallax is recorded"),
    _m("LINFIT-EPOCH-1", "astrometry", "Visit-averaged positions and the proper-motion fit across visits.",
       [io("exposure positions ξ, η", "position_mas"), io("epochs", "time_jyear")], [io("proper motion", "pm"), io("proper-motion error", "pm_err")],
       ["motion is linear over the baseline", "exposures within one visit share systematics, so each visit's error is max(formal, empirical/√n)"],
       ["epoch_gap_days", "epoch_clip_sigma"], "group exposures by gaps > epoch_gap_days; weighted means per visit; weighted linear least squares of position vs time",
       ["DIFFAST-1/PLATE-LOO-1", "LINFIT-LOO-1"], ["≥ 2 visits"], ["a single visit (reported as single-visit)"],
       ["acceleration and orbital motion are not modelled"], ["synthetic fixtures (syn-hpm-1 injects high proper motion)"],
       [T + "test_calibration_v2.py::test_epoch_grouping_and_error_floor", T + "test_calibration_v2.py::test_epoch_fit_does_not_shrink_correlated_errors",
        T + "test_measurement.py::test_motion_fit_and_catalogue_comparison"],
       [{"id": "LINFIT-1", "change": "weighted linear fit over exposures"}, {"id": "LINFIT-EPOCH-1", "change": "fit over visit means with an empirical error floor"}],
       "src/skytrace/science/astrometry.py", "model-dependent", "weighted least-squares covariance, inflated by √χ²ν when χ²ν > 1"),
    _m("LINFIT-LOO-1", "astrometry", "Leave-one-out rejection of discrepant visits inside the motion fit.",
       [io("visit positions", "position_mas")], [io("kept / rejected visits", "category")], ["at most a few visits are outliers"],
       ["epoch_clip_sigma"], "drop the worst visit if it deviates from the fit without it by more than epoch_clip_sigma; repeat", ["LINFIT-EPOCH-1"],
       ["≥ 3 visits"], ["two visits (no rejection possible)"], ["with few visits a real deviation and an outlier cannot be told apart"],
       ["synthetic fixtures"], [T + "test_measurement.py::test_motion_fit_and_catalogue_comparison"],
       [{"id": "LINFIT-LOO-1", "change": "initial method"}], "src/skytrace/science/astrometry.py", "model-dependent", "inherits LINFIT-EPOCH-1"),
    _m("ASSESS-2", "decision rules", "Turn measurements into one of a fixed set of outcomes per question.",
       [io("pair significances", "z"), io("proper motion and error", "pm"), io("exposure counts", "category")], [io("outcome per question", "category")],
       ["thresholds fixed before any data were examined (ASSESS-1 design), not tuned per target"],
       [], "variability candidate iff some |z_used| ≥ 5 (calibrated z when available, divided by the CALCHECK scale); motion detected iff |pm|/σ ≥ 5 and consistent with the catalogue within 3σ; instrumental iff > 50 % of exposures unusable",
       ["PAIRDIFF-1", "PAIRDIFF-2", "CALCHECK-1", "LINFIT-EPOCH-1"], ["records of skytrace-analysis/2"], ["records of other analysis versions"],
       ["a non-detection is bounded by the stated sensitivity, never proof of absence"], ["synthetic fixtures with known outcomes"],
       [T + "test_assess2.py::test_motion_outcomes", T + "test_assess2.py::test_variability_outcomes", T + "test_assess2.py::test_every_outcome_documents_itself"],
       [{"id": "ASSESS-1", "change": "initial rules"}, {"id": "ASSESS-2", "change": "adds the calibrated z and calcheck_unreliable_scale"}],
       "src/skytrace/science/assess.py", "derived", "none: categorical; each outcome states its sensitivity"),
]
BY_ID = {m["id"]: m for m in METHODS}
DOC_FIELDS = ("purpose", "inputs", "outputs", "assumptions", "math", "applicable", "unsupported", "limitations", "validation_data",
              "known_answer_tests", "versions", "module", "uncertainty_propagation")
PIPELINE_DETERMINISM_TEST = T + "test_provenance_check.py::test_clean_record_passes_including_determinism"


@lru_cache(maxsize=1)
def _defined_tests() -> frozenset:
    out = set()
    for f in (ROOT / "tests").rglob("test_*.py"):
        try:
            tree = ast.parse(f.read_text())
        except (OSError, SyntaxError):
            continue
        rel = f.relative_to(ROOT).as_posix()
        out |= {f"{rel}::{n.name}" for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")}
    return frozenset(out)


def _dep_available(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def health(m: dict, used: bool) -> dict:
    defined = _defined_tests()
    tests = [{"test": t, "defined": t in defined} for t in m["known_answer_tests"]]
    missing_docs = [f for f in DOC_FIELDS if not m.get(f)]
    deps = {"numpy": _dep_available("numpy"), "scipy": _dep_available("scipy")}
    return {"known_answer_tests": tests, "n_defined": sum(t["defined"] for t in tests),
            "reproducibility": ("covered by the pipeline determinism check (re-execution gives the identical record hash)" if used
                                else "not exercised by this run"),
            "determinism_test": PIPELINE_DETERMINISM_TEST if PIPELINE_DETERMINISM_TEST in defined else None,
            "dependencies_available": deps, "documentation_missing": missing_docs,
            "note": "defined tests are software evidence; whether they pass is recorded in docs/TEST_REPORT.md. Neither is scientific validity."}


def used_methods(record: dict) -> set:
    mids = set()
    for v in (record.get("parameters", {}).get("methods") or {}).values():
        mids |= set(v) if isinstance(v, list) else {v}
    for e in record.get("events", []):
        d = e.get("data") or {}
        if e["step"] == "measure":
            mids |= {(d.get("centroid") or {}).get("method"), (d.get("photometry") or {}).get("method"), (d.get("flag_summary") or {}).get("policy")}
            if d.get("plate"):
                mids.add("DIFFAST-1/PLATE-LOO-1")
    mids.discard(None)
    return mids


def genome(record: dict | None = None) -> dict:
    used = used_methods(record) if record else set()
    return {"method": METHOD, "qtypes": QTYPES, "status_rule": __doc__.split("Output status follows one stated rule (EPI-1): ")[1].strip(),
            "methods": [{**m, "used_in_run": m["id"] in used, "health": health(m, m["id"] in used)} for m in METHODS],
            "unregistered_in_run": sorted(x for x in used if x not in BY_ID)}


def compare(a: str, b: str) -> dict:
    """Field-by-field comparison of two methods. Compatible = they produce at least one output of the same quantity type."""
    ma, mb = BY_ID[a], BY_ID[b]
    ta, tb = {o["type"] for o in ma["outputs"]}, {o["type"] for o in mb["outputs"]}
    rows = []
    for f in ("purpose", "inputs", "outputs", "assumptions", "parameters", "limitations", "validation_data", "known_answer_tests", "output_status"):
        va, vb = ma.get(f), mb.get(f)
        if isinstance(va, list) and isinstance(vb, list):
            ka = [x["name"] + " [" + x["unit"] + "]" if isinstance(x, dict) else str(x) for x in va]
            kb = [x["name"] + " [" + x["unit"] + "]" if isinstance(x, dict) else str(x) for x in vb]
            rows.append({"field": f, "only_a": [x for x in ka if x not in kb], "only_b": [x for x in kb if x not in ka], "both": [x for x in ka if x in kb]})
        else:
            rows.append({"field": f, "a": va, "b": vb, "same": va == vb})
    return {"a": a, "b": b, "compatible": bool(ta & tb), "shared_output_types": sorted(ta & tb), "rows": rows,
            "note": "compatible means the two methods produce the same kind of quantity; it does not mean either is better."}


def dependency_graph() -> dict:
    nodes = [{"id": m["id"], "family": m["family"]} for m in METHODS]
    edges = [{"source": d, "target": m["id"]} for m in METHODS for d in m["dependencies"] if d in BY_ID]
    return {"nodes": nodes, "edges": edges}
