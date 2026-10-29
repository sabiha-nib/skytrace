"""Capability registry (CAPREG-1): what SKYTRACE can actually do, in one place.

Every entry names the implemented method versions it relies on, its inputs and accepted parameter ranges, its
outputs, its limitations, the tests that exercise it, and where it runs. The copilot, the Discovery engine and the
interface read this registry instead of describing capabilities in prose. `tests/unit/test_discovery.py` checks
that every method ID listed here is one the code records, and that every listed test file exists.

`execution`: "local" (pure computation on stored files), "server" (needs the running Skytrace server, not the
static preview), or "network" (needs an external service; reported with its current availability).
"""

from __future__ import annotations

from . import analysis

REGISTRY_VERSION = "CAPREG-1"


def _params(*names):
    return {n: {"range": list(analysis.PARAM_BOUNDS[n]), "default": analysis.DEFAULTS[n]} for n in names}


CAPABILITIES: list[dict] = [
    {"id": "measure", "name": "Per-exposure measurement",
     "methods": ["CENTROID-G2D-1", "NBMASK-1", "TGT-1", "APPHOT-1", "FLAGPOL-1"],
     "inputs": ["verified bundle: SPHEREx-layout image (IMAGE, FLAGS, VARIANCE, WCS-WAVE)", "catalogue astrometry"],
     "parameters": _params("aperture_radius_px", "fit_half_size_px"),
     "outputs": ["centroid ± error (px)", "aperture flux ± error (µJy)", "wavelength and bandwidth at the target (µm)",
                 "quality_code / astro_code"],
     "limitations": ["Gaussian PSF model", "aperture fluxes are not aperture-corrected"],
     "tests": ["tests/unit/test_measurement.py"], "execution": "server"},
    {"id": "wavelength_match", "name": "Wavelength compatibility of two observations", "methods": ["WLMATCH-2"],
     "inputs": ["two measured observations"], "parameters": _params("wavelength_tolerance_channels", "wavelength_margin_um"),
     "outputs": ["accepted / rejected with a reason code"],
     "limitations": ["the wavelength solution is accurate to about 1 nm"],
     "tests": ["tests/unit/test_wavelength_flags.py", "tests/unit/test_calibration_v2.py", "tests/unit/test_static_preview.py"],
     "execution": "local"},
    {"id": "brightness", "name": "Brightness comparison of matched pairs", "methods": ["PAIRDIFF-1", "PAIRDIFF-2", "CALCHECK-1"],
     "inputs": ["wavelength-matched pairs with usable photometry", "≥ 3 matched reference stars for calibration"],
     "parameters": {}, "outputs": ["z (raw)", "z (reference-calibrated, error-scaled)", "calibration ratio ± σ"],
     "limitations": ["z is a significance under the stated errors, not a probability"],
     "tests": ["tests/unit/test_calibration_v2.py", "tests/robustness/test_robustness.py"], "execution": "server"},
    {"id": "motion", "name": "Proper-motion measurement against Gaia references",
     "methods": ["REFSEL-1", "REFSEL-2", "PLATE-LOO-1", "EPHEM-AA-LP-1", "LINFIT-EPOCH-1", "LINFIT-LOO-1"],
     "inputs": ["≥ 2 exposures with a usable target position and plate solution", "catalogue proper motion"],
     "parameters": _params("epoch_clip_sigma", "epoch_gap_days"),
     "outputs": ["proper motion ± σ (mas/yr)", "difference from catalogue (σ)"],
     "limitations": ["chromatic PSF and distortion absorbed only to first order"],
     "tests": ["tests/unit/test_measurement.py", "tests/unit/test_ephemeris.py", "tests/robustness/test_robustness.py"],
     "execution": "server"},
    {"id": "assessment", "name": "Outcome assessment", "methods": ["ASSESS-2"],
     "inputs": ["motion fit", "matched-pair comparisons", "measurement status codes"], "parameters": {},
     "outputs": ["one category per question with evidence, criteria, sensitivity, limitations"],
     "limitations": ["thresholds fixed in advance (5σ detection, 3σ consistency)"],
     "tests": ["tests/unit/test_assess2.py", "tests/unit/test_offline_workflow.py"], "execution": "server"},
    {"id": "stability", "name": "Perturbation stability check", "methods": ["STAB-1"],
     "inputs": ["a bundle and base parameters"], "parameters": {},
     "outputs": ["outcome categories under five fixed parameter changes"],
     "limitations": ["parameter sensitivity, not statistical uncertainty"],
     "tests": ["tests/robustness/test_robustness.py", "tests/integration/test_api.py"], "execution": "server"},
    {"id": "registration", "name": "Registration diagnostics for a pair", "methods": ["REGDIAG-1"],
     "inputs": ["plate solutions of both exposures"], "parameters": {},
     "outputs": ["pixel scale, orientation, residual RMS per plate; relative rotation, scale ratio and shift"],
     "limitations": ["geometric only; says nothing about photometric calibration"],
     "tests": ["tests/unit/test_static_preview.py", "tests/unit/test_discovery.py"], "execution": "local"},
    {"id": "hypotheses", "name": "Hypothesis tests on recorded evidence", "methods": ["HYPO-1"],
     "inputs": ["a finished investigation record"], "parameters": {},
     "outputs": ["per hypothesis and test: consistent / contradicted / inconclusive / not tested / evidence unavailable / incompatible"],
     "limitations": ["rules over recorded values; no probabilities", "several explanations are not testable with these data"],
     "tests": ["tests/unit/test_discovery.py"], "execution": "local"},
    {"id": "uncertainty", "name": "Uncertainty decomposition", "methods": ["UNC-1"],
     "inputs": ["a finished investigation record"], "parameters": {},
     "outputs": ["components of the motion σ and of each pair's z denominator, from logged values"],
     "limitations": ["only components the methods actually compute; parameter sensitivity is reported separately (STAB-1)"],
     "tests": ["tests/unit/test_discovery.py"], "execution": "local"},
    {"id": "discovery", "name": "Discovery engine (inventory, questions, test plans, next steps)", "methods": ["DISC-1"],
     "inputs": ["a finished investigation record", "the bundle's discovery index and manifest"], "parameters": {},
     "outputs": ["evidence inventory", "answerability of registered questions", "test plans", "ranked next steps"],
     "limitations": ["recommends only actions the registry contains; says when they need unavailable services"],
     "tests": ["tests/unit/test_discovery.py"], "execution": "local"},
    {"id": "provenance", "name": "Provenance verification", "methods": ["PROVCHECK-1"],
     "inputs": ["an investigation record and its bundle"], "parameters": {},
     "outputs": ["10 named checks incl. file hashes, origins, codes, re-run determinism"],
     "limitations": ["re-run needs the server"], "tests": ["tests/unit/test_provenance_check.py"], "execution": "server"},
    {"id": "package", "name": "Reproducibility package", "methods": ["PKG-1"],
     "inputs": ["a finished investigation record"], "parameters": {},
     "outputs": ["zip: record, report, discovery, hypotheses, uncertainty, graph, capabilities, bundle manifest, checksums"],
     "limitations": ["contains no image data; replay needs the bundle"], "tests": ["tests/integration/test_api.py"],
     "execution": "local"},
    {"id": "archive", "name": "SPHEREx / SIMBAD / Gaia acquisition", "methods": [],
     "inputs": ["target name"], "parameters": {},
     "outputs": ["verified archive bundle with provenance"],
     "limitations": ["needs network access to irsa.ipac.caltech.edu, simbad.cds.unistra.fr, gea.esac.esa.int"],
     "tests": ["tests/unit/test_acquire.py", "tests/live/test_live_archive.py"], "execution": "network"},
    {"id": "copilot_model", "name": "Meta model copilot", "methods": ["TOOLS-2", "GUARD-3"],
     "inputs": ["question", "investigation"], "parameters": {},
     "outputs": ["guard-checked answer citing tool outputs"],
     "limitations": ["needs api.meta.ai and a key on the server"], "tests": ["tests/unit/test_report_ai.py"],
     "execution": "network"},
    {"id": "copilot_local", "name": "Local deterministic assistant", "methods": ["TOOLS-2", "GUARD-3"],
     "inputs": ["question", "investigation"], "parameters": {},
     "outputs": ["template answer filled only from tool outputs"],
     "limitations": ["keyword routing; no interpretation beyond the recorded outcomes"],
     "tests": ["tests/unit/test_report_ai.py", "tests/unit/test_tool_contracts.py"], "execution": "server"},
]


def registry(availability: dict | None = None) -> dict:
    """The registry with current availability: {"network": bool, "server": bool} (None = unknown)."""
    av = availability or {}
    out = []
    for c in CAPABILITIES:
        ex = c["execution"]
        ok = True if ex == "local" else av.get(ex)
        out.append({**c, "available": ok,
                    "availability_note": {"local": "runs wherever the record is present",
                                          "server": "needs the running Skytrace server" + ("" if ok else " (not available here)"),
                                          "network": "needs external services" + (" (blocked here)" if ok is False else "")}[ex]})
    return {"version": REGISTRY_VERSION, "capabilities": out}


def method_ids() -> set[str]:
    return {m for c in CAPABILITIES for m in c["methods"]}
