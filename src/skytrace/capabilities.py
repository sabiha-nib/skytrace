"""Capability registry (CAPREG-3, extends CAPREG-1/2; CAPREG-3 adds the Phase 7 capabilities and an action permission class): what SKYTRACE can actually do, in one place.

Every entry names the implemented method versions it relies on, its inputs and accepted parameter ranges, its
outputs, its limitations, the tests that exercise it, and where it runs. The copilot, the Discovery engine and the
interface read this registry instead of describing capabilities in prose. `tests/unit/test_discovery.py` checks
that every method ID listed here is one the code records, and that every listed test file exists.

`execution`: "local" (pure computation on stored files), "server" (needs the running Skytrace server, not the
static preview), or "network" (needs an external service; reported with its current availability).
"""

from __future__ import annotations

from . import analysis

REGISTRY_VERSION = "CAPREG-3"


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


# ------------------------------------------------------------------ CAPREG-2: Phase 6 capabilities
CAPABILITIES += [
    {"id": "session", "name": "Research session", "methods": ["SESSION-1", "SKY-CANON-1", "SCHEMA-1"],
     "inputs": ["user decisions and notes", "references to analysis runs"], "parameters": {},
     "outputs": ["integrity-checked session (content hash) with activity history"],
     "limitations": ["holds references to computed results, not copies", "single user: no access control"],
     "tests": ["tests/unit/test_research_session.py"], "execution": "local"},
    {"id": "sequences", "name": "Observation compatibility and multi-epoch sequences", "methods": ["COMPAT-1", "SEQ-1"],
     "inputs": ["a finished investigation record", "the bundle's discovery index and manifest"], "parameters": {},
     "outputs": ["compatibility matrix with WLMATCH-2 reason codes", "compatible sequences", "coverage gaps", "duplicate files",
                 "metadata completeness"],
     "limitations": ["compatibility is the recorded WLMATCH-2 decision; nothing is inferred from image appearance",
                     "a sequence lists only observed epochs; nothing is interpolated"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "quality", "name": "Data quality checks", "methods": ["DQ-1"],
     "inputs": ["a finished investigation record", "the bundle manifest", "the stored files (server)"], "parameters": {},
     "outputs": ["one outcome per check: valid under the tested rules / invalid / incompatible / not available / not checked"],
     "limitations": ["no overall quality score", "file hashes are recomputed only where the files are present (server)"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "ledger", "name": "Evidence ledger", "methods": ["LEDGER-1"],
     "inputs": ["a finished investigation record", "the evidence graph", "HYPO-1 results"], "parameters": {},
     "outputs": ["per claim: support counts by kind, provenance files, methods and parameters", "contradictions",
                 "completeness gaps"],
     "limitations": ["support is counted, not weighed; a single supporting item is flagged, never called sufficient"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "planner", "name": "Adaptive Investigation Planner", "methods": ["PLAN-1"],
     "inputs": ["a research question in words", "the current facts (target data, run, selected pair, server, network)"],
     "parameters": {}, "outputs": ["structured intent", "plan of registered actions with dependencies and statuses"],
     "limitations": ["keyword rules, not language understanding; unrecognised questions are said to be unrecognised",
                     "plans only registered actions"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "radar", "name": "Discovery Radar (research opportunities)", "methods": ["RADAR-1"],
     "inputs": ["record", "compatibility report", "quality checks", "ledger", "hypothesis tests"], "parameters": {},
     "outputs": ["recommendations with reason, supporting evidence, data needed, method, what it cannot establish, runnable now"],
     "limitations": ["recommends investigations, never detects astronomical events"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "experiments", "name": "Experiment Studio", "methods": ["EXP-1"],
     "inputs": ["experiment configuration (template, parameters, criteria)", "bundle"], "parameters": {},
     "outputs": ["per-run summaries and evaluation against the stated criteria"],
     "limitations": ["at most 8 runs per experiment", "a run that completes is not a valid experiment by itself"],
     "tests": ["tests/unit/test_research_os.py", "tests/integration/test_api.py"], "execution": "server"},
    {"id": "missions", "name": "Missions", "methods": ["MISSION-1"],
     "inputs": ["research session"], "parameters": {},
     "outputs": ["task status derived from the session's recorded activity"],
     "limitations": ["completion means the steps were done, not that a conclusion is valid"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "workflows", "name": "Research automation (workflows)", "methods": ["WF-1"],
     "inputs": ["workflow document"], "parameters": {},
     "outputs": ["validated workflow", "per-item execution records"],
     "limitations": ["at most 4 targets × 10 steps", "imported workflows run only after validation"],
     "tests": ["tests/unit/test_research_os.py"], "execution": "local"},
    {"id": "connectors", "name": "Archive connectors", "methods": ["ACQ-2"],
     "inputs": ["query parameters"], "parameters": {},
     "outputs": ["validated request preview", "service availability from the last diagnosis"],
     "limitations": ["a preview is not a search; sending needs network access (blocked here)"],
     "tests": ["tests/unit/test_research_os.py", "tests/unit/test_acquire.py"], "execution": "local"},
]

# ------------------------------------------------------------------ CAPREG-3: Phase 7 capabilities
CAPABILITIES += [
    {"id": "possibility", "name": "Scientific Possibility Engine and Discovery Horizon", "methods": ["SPE-1", "HORIZON-1"],
     "inputs": ["record", "discovery report", "research report", "information analysis", "challenges"], "parameters": {},
     "outputs": ["six inspectable layers", "research opportunity cards with feasibility and stated ranking", "opportunity map"],
     "limitations": ["identifies opportunities for investigation, never findings", "ranking is a stated order, not a value"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "local"},
    {"id": "adversarial", "name": "Adversarial Science Lab", "methods": ["ASL-1"],
     "inputs": ["record", "hypothesis tests", "quality checks", "ledger", "uncertainty", "stability (optional)"], "parameters": {},
     "outputs": ["challenges: issue, evidence, rule, severity class, why, verification, status"],
     "limitations": ["raises a challenge only when a stated rule fires; open does not mean wrong"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "local"},
    {"id": "information", "name": "Information analysis (qualitative)", "methods": ["INFO-1"],
     "inputs": ["hypothesis tests"], "parameters": {},
     "outputs": ["candidate tests ranked by feasibility and the viable explanations they bear on"],
     "limitations": ["no probability model exists, so no numerical information gain is computed"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "local"},
    {"id": "review", "name": "Review Room", "methods": ["REVIEW-1"],
     "inputs": ["record", "quality", "ledger", "hypotheses", "uncertainty", "reproducibility audit", "challenges", "session"], "parameters": {},
     "outputs": ["findings by role, each citing a record, rule or missing prerequisite"],
     "limitations": ["software rule sets, not human reviewers"], "tests": ["tests/unit/test_frontier.py"], "execution": "local"},
    {"id": "reproducibility", "name": "Reproducibility Challenge", "methods": ["REPRO-1", "PROVCHECK-1"],
     "inputs": ["record", "bundle", "session"], "parameters": {},
     "outputs": ["eleven checks and a verdict by a stated rule"],
     "limitations": ["re-execution (R9) needs the server", "exact hash equality; does not validate the method itself"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "server"},
    {"id": "twins", "name": "Astro-Twins", "methods": ["TWIN-1"],
     "inputs": ["record", "discovery index", "manifest", "target", "scenario", "session"], "parameters": {},
     "outputs": ["versioned, hashed records of an observation, target, analysis, scenario or investigation", "structural comparison"],
     "limitations": ["computational records, not physical models of objects"], "tests": ["tests/unit/test_frontier.py"], "execution": "local"},
    {"id": "counterfactual", "name": "Counterfactual Universe Lab", "methods": ["CF-1", "ASSESS-2"],
     "inputs": ["baseline run", "one stated change"], "parameters": {},
     "outputs": ["baseline and counterfactual outcomes side by side, changed metrics, the change that caused them"],
     "limitations": ["only bounded, stated changes", "a scenario is not an observation and never alters the original"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "server"},
    {"id": "synthetic_observatory", "name": "Synthetic Observatory and Observation Design Lab", "methods": ["SYNOBS-1", "OBSDES-1"],
     "inputs": ["bounded scenario (motion, brightness by pass, noise, background, gain, reference errors, schedule, seed)"], "parameters": {},
     "outputs": ["labelled SYNTHETIC bundle", "pipeline output against ground truth", "hypothetical schedule comparison"],
     "limitations": ["illustrative instrument model, not SPHEREx calibration", "agreement on generated data does not validate real-data performance",
                     "schedules are hypothetical; no telescope is scheduled"],
     "tests": ["tests/unit/test_frontier.py"], "execution": "server"},
]

# Fields every capability declares (CAPREG-2): description, preconditions (facts), dependencies (capabilities),
# validation status and the data types it applies to.
_V_KNOWN = "known-answer tests on synthetic fixtures"
_EXTRA = {
    "measure": ("Measures position and flux of the target in each exposure.", ["has_target_data"], [], _V_KNOWN),
    "wavelength_match": ("Decides whether two observations sample the same wavelength closely enough to compare brightness.",
                         ["has_run"], ["measure"], _V_KNOWN + "; browser port parity-tested on every fixture pair"),
    "brightness": ("Compares fluxes of wavelength-matched pairs, raw and reference-calibrated.", ["has_run"], ["measure", "wavelength_match"], _V_KNOWN),
    "motion": ("Fits proper motion from Gaia-referenced positions and compares it with the catalogue.", ["has_run"], ["measure"], _V_KNOWN),
    "assessment": ("Classifies each question with fixed thresholds and states the sensitivity.", ["has_run"], ["brightness", "motion"], _V_KNOWN),
    "stability": ("Re-runs the analysis under five fixed parameter changes.", ["has_target_data", "server_or_precomputed"], ["assessment"], _V_KNOWN),
    "registration": ("Describes the geometry relating two exposures' plate solutions.", ["has_pair"], ["measure"], _V_KNOWN + "; parity-tested"),
    "hypotheses": ("Tests competing explanations against recorded values by stated rules.", ["has_run"], ["assessment"], _V_KNOWN),
    "uncertainty": ("Shows what each recorded uncertainty is made of.", ["has_run"], ["assessment"], "recompute check against logged values"),
    "discovery": ("Inventory, answerable questions, test plans and next steps.", ["has_run"], ["hypotheses", "uncertainty"], "unit-tested"),
    "provenance": ("Checks a record against its files, origins, codes and re-run determinism.", ["has_run", "server"], [], "tamper tests"),
    "package": ("Deterministic zip with record, reports and checksums.", ["has_run"], ["discovery"], "determinism test"),
    "archive": ("Acquires SPHEREx, SIMBAD and Gaia data into a verified bundle.", ["network"], [], "not validated: blocked (no network)"),
    "copilot_model": ("Explains evidence with the Meta model through read-only tools.", ["network", "model_key"], [], "not validated: blocked (no key, no route)"),
    "copilot_local": ("Answers from tool outputs with fixed templates.", ["has_run"], [], "unit-tested; guard-checked"),
    "session": ("Keeps the question, runs, hypotheses, notes, plans, experiments and activity of one investigation.", [], [], "parity-tested (Python/browser)"),
    "sequences": ("Lists which observations can be compared and groups compatible epochs into sequences.", ["has_run"], ["wavelength_match"], _V_KNOWN),
    "quality": ("Runs named data-quality checks with explicit outcomes.", ["has_run"], ["measure"], "unit-tested with injected defects"),
    "ledger": ("Shows what supports each claim, what conflicts, and what is missing.", ["has_run"], ["hypotheses"], "unit-tested"),
    "planner": ("Turns a question into a plan of registered actions.", [], [], "parity-tested (Python/browser) on a question corpus"),
    "radar": ("Lists investigation opportunities with their reasons.", ["has_run"], ["sequences", "quality", "ledger"], "unit-tested"),
    "experiments": ("Runs bounded experiments and evaluates them against stated criteria.", ["has_target_data", "server_or_precomputed"], ["assessment"], _V_KNOWN),
    "missions": ("Guides a sequence of tasks whose completion is read from the session.", [], ["session"], "parity-tested (Python/browser)"),
    "workflows": ("Validates and runs declared multi-step, multi-target workflows.", [], ["planner"], "unit-tested"),
    "connectors": ("Describes and validates archive queries against documented interfaces.", [], [], "unit-tested; live use blocked"),
    "possibility": ("Lays an investigation out in six layers and lists research opportunities.", ["has_run"], ["discovery", "ledger", "adversarial", "information"], "unit-tested on both fixtures"),
    "adversarial": ("Challenges the investigation's own interpretation with documented rules.", ["has_run"], ["hypotheses", "quality", "ledger"], "unit-tested on both fixtures"),
    "information": ("Ranks open tests by how many viable explanations they bear on.", ["has_run"], ["hypotheses"], "unit-tested"),
    "review": ("Runs five software review roles over the investigation.", ["has_run"], ["quality", "ledger", "reproducibility"], "unit-tested"),
    "reproducibility": ("Audits whether the investigation can be reproduced, and re-executes it on the server.", ["has_run"], ["provenance"], "tamper and replay tests"),
    "twins": ("Builds hashed, comparable records of observations, targets, analyses, scenarios and investigations.", ["has_run"], [], "integrity and parity tests"),
    "counterfactual": ("Re-runs or re-assesses the analysis under one stated change and compares with the baseline.", ["has_target_data", "server_or_precomputed"], ["assessment"], "isolation and reproduction tests"),
    "synthetic_observatory": ("Generates labelled synthetic scenarios and compares the pipeline with their ground truth.", ["server_or_precomputed"], ["assessment"], "known-answer and determinism tests"),
}
_DATA_TYPES = {"archive": ["target name"], "session": ["research session"], "planner": ["research question"],
               "missions": ["research session"], "workflows": ["workflow document"], "connectors": ["archive query"],
               "synthetic_observatory": ["synthetic scenario"], "counterfactual": ["investigation record", "synthetic bundle", "archive bundle"]}
for _c in CAPABILITIES:
    _d, _pre, _deps, _val = _EXTRA[_c["id"]]
    _c.setdefault("description", _d)
    _c.setdefault("preconditions", _pre)
    _c.setdefault("dependencies", _deps)
    _c.setdefault("validation", _val)
    _c.setdefault("data_types", _DATA_TYPES.get(_c["id"], ["synthetic bundle", "archive bundle", "investigation record"]))

# ------------------------------------------------------------------ executable actions (planner, workflows, missions)
# Each action runs exactly one registered capability through one existing interface entry point. `confirm`: the user
# must confirm before it runs (it re-executes the pipeline, takes long, or needs a decision). `static`: how the static
# preview can serve it — "browser" (parity-tested port), "precomputed" (results recorded at build time; other inputs
# are refused), or "unavailable" (needs the full application).
FACTS = {
    "has_target_data": "the target has stored observations",
    "has_run": "an analysis run is loaded",
    "has_pair": "two observations are selected",
    "pair_compatible": "the selected pair is wavelength-matched (WLMATCH-2)",
    "has_question": "a research question is set",
    "server": "the Skytrace server is running (not the static preview)",
    "server_or_precomputed": "the server is running, or the preview has the result precomputed",
    "network": "external archives are reachable",
    "model_key": "a model API key is configured on the server",
}
ACTIONS: list[dict] = [
    {"id": "run_analysis", "capabilities": ["measure", "wavelength_match", "brightness", "motion", "assessment"],
     "title": "Run the analysis", "preconditions": ["has_target_data"], "produces": ["has_run"], "confirm": True,
     "cost": "a few seconds (re-executes the pipeline)", "static": "precomputed",
     "inputs": {"t": "obj", "f": {"params": [{"t": "map", "keys": "^[a-z_]{1,40}$", "max": 20, "values": {"t": "any", "of": [{"t": "num"}, {"t": "bool"}]}}, False]}, "extra": False}},
    {"id": "run_stability", "capabilities": ["stability"], "title": "Check stability under parameter changes",
     "preconditions": ["has_target_data", "server_or_precomputed"], "produces": [], "confirm": True, "cost": "about 15 s (six analyses)",
     "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "compare_pair", "capabilities": ["wavelength_match", "registration"], "title": "Compare two observations",
     "preconditions": ["has_run", "has_pair"], "produces": [], "confirm": False, "cost": "instant", "static": "browser",
     "inputs": {"t": "obj", "f": {"a": [{"t": "str", "min": 1, "max": 200}, True], "b": [{"t": "str", "min": 1, "max": 200}, True]}, "extra": False}},
    {"id": "inspect_pair", "capabilities": ["registration"], "title": "Inspect the pair by eye in the Time Machine",
     "preconditions": ["has_run", "has_pair"], "produces": [], "confirm": False, "cost": "your judgement", "static": "browser",
     "review": True, "inputs": {"t": "obj", "f": {"a": [{"t": "str", "min": 1, "max": 200}, True], "b": [{"t": "str", "min": 1, "max": 200}, True]}, "extra": False}},
    {"id": "build_sequences", "capabilities": ["sequences"], "title": "Group compatible epochs into sequences",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "evaluate_hypotheses", "capabilities": ["hypotheses"], "title": "Test competing explanations",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "decompose_uncertainty", "capabilities": ["uncertainty"], "title": "Decompose the uncertainties",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "check_quality", "capabilities": ["quality"], "title": "Run the data-quality checks",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "inspect_ledger", "capabilities": ["ledger"], "title": "Inspect the evidence ledger",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "scan_radar", "capabilities": ["radar"], "title": "List research opportunities",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "verify_provenance", "capabilities": ["provenance"], "title": "Verify provenance and re-run",
     "preconditions": ["has_run", "server"], "produces": [], "confirm": True, "cost": "a few seconds (re-executes the pipeline)",
     "static": "unavailable", "inputs": {"t": "obj", "f": {"rerun": [{"t": "bool"}, False]}, "extra": False}},
    {"id": "run_experiment", "capabilities": ["experiments"], "title": "Run an experiment",
     "preconditions": ["has_target_data", "server_or_precomputed"], "produces": [], "confirm": True, "cost": "up to 8 analyses",
     "static": "precomputed", "inputs": {"t": "obj", "f": {"template": [{"t": "str", "enum": ["parameter", "sensitivity", "reproducibility",
                                                                                                 "method_comparison", "negative_control", "robustness"]}, True],
                                                           "configs": [{"t": "json", "max_bytes": 4000, "depth": 4}, False]}, "extra": False}},
    {"id": "build_package", "capabilities": ["package"], "title": "Build the reproducibility package",
     "preconditions": ["has_run"], "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "acquire_data", "capabilities": ["archive"], "title": "Acquire archive observations",
     "preconditions": ["network"], "produces": ["has_target_data"], "confirm": True, "cost": "minutes; downloads files",
     "static": "unavailable", "inputs": {"t": "obj", "f": {"target": [{"t": "str", "min": 1, "max": 64}, True]}, "extra": False}},
]
ACTIONS += [
    {"id": "run_counterfactual", "capabilities": ["counterfactual"], "title": "Run a counterfactual scenario",
     "preconditions": ["has_target_data", "server_or_precomputed"], "produces": [], "confirm": True, "cost": "seconds (re-assessment) to ~10 s (re-run)",
     "static": "precomputed", "inputs": {"t": "obj", "f": {"scenario": [{"t": "json", "max_bytes": 4000, "depth": 4}, True]}, "extra": False}},
    {"id": "challenge_interpretation", "capabilities": ["adversarial"], "title": "Challenge the interpretation", "preconditions": ["has_run"],
     "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "rank_tests", "capabilities": ["information"], "title": "Rank the open tests", "preconditions": ["has_run"],
     "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "review_investigation", "capabilities": ["review"], "title": "Run the Review Room", "preconditions": ["has_run"],
     "produces": [], "confirm": False, "cost": "instant", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "reproduce", "capabilities": ["reproducibility"], "title": "Run the Reproducibility Challenge (re-execute)", "preconditions": ["has_run", "server"],
     "produces": [], "confirm": True, "cost": "a few seconds (re-executes the pipeline)", "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "reproduce_independent", "capabilities": ["reproducibility"], "title": "Run the independent reproduction (REPROX-1, five verdicts)",
     "preconditions": ["has_run", "server_or_precomputed"], "produces": [], "confirm": True, "cost": "a few seconds (re-executes the pipeline and compares every stage)",
     "static": "precomputed", "inputs": {"t": "obj", "f": {}, "extra": False}},
    {"id": "run_synthetic", "capabilities": ["synthetic_observatory"], "title": "Generate and analyse a synthetic scenario",
     "preconditions": ["server_or_precomputed"], "produces": [], "confirm": True, "cost": "about 5 s (writes a synthetic bundle, runs the analysis)",
     "static": "precomputed", "inputs": {"t": "obj", "f": {"scenario": [{"t": "json", "max_bytes": 4000, "depth": 4}, True]}, "extra": False}},
]
# Permission class of each action (Research Autopilot): inspect (reads recorded results), analysis (re-executes or
# generates locally), export (writes a file for the user), network (contacts external services). Autopilot levels:
# inspect only < plan only < execute approved local analysis < execute approved batch workflows < export results.
PERMISSION = {"run_analysis": "analysis", "run_stability": "analysis", "compare_pair": "inspect", "inspect_pair": "inspect",
              "build_sequences": "inspect", "evaluate_hypotheses": "inspect", "decompose_uncertainty": "inspect", "check_quality": "inspect",
              "inspect_ledger": "inspect", "scan_radar": "inspect", "verify_provenance": "analysis", "run_experiment": "analysis",
              "build_package": "export", "acquire_data": "network", "run_counterfactual": "analysis", "challenge_interpretation": "inspect",
              "rank_tests": "inspect", "review_investigation": "inspect", "reproduce": "analysis", "reproduce_independent": "analysis",
              "run_synthetic": "analysis"}
for _a in ACTIONS:
    _a["permission"] = PERMISSION[_a["id"]]
AUTOPILOT_LEVELS = [{"id": "inspect", "name": "Inspect only", "allows": ["inspect"], "plans": False},
                    {"id": "plan", "name": "Plan only", "allows": ["inspect"], "plans": True},
                    {"id": "local", "name": "Execute approved local analysis", "allows": ["inspect", "analysis"], "plans": True},
                    {"id": "batch", "name": "Execute approved batch workflows", "allows": ["inspect", "analysis"], "plans": True, "batch": True},
                    {"id": "export", "name": "Export results", "allows": ["inspect", "analysis", "export"], "plans": True, "batch": True}]
# Phase 9 bounded autonomy (the research cycle): three named levels, each mapped onto the CAPREG-3 level it corresponds to.
# Advisory proposes and executes nothing; supervised executes one approved step at a time; restricted automation executes the
# predefined, auditable workflow below after one authorization that lists every step. No level allows network or export.
AUTONOMY_LEVELS = [{"id": "advisory", "name": "Advisory", "allows": [], "capreg3": "plan", "executes": "nothing: proposes actions only"},
                   {"id": "supervised", "name": "Supervised", "allows": ["inspect", "analysis"], "capreg3": "local",
                    "executes": "each step you approve, one at a time"},
                   {"id": "restricted", "name": "Restricted automation", "allows": ["inspect", "analysis"], "capreg3": "local",
                    "executes": "the predefined workflow, after one authorization that lists every step"}]
RESTRICTED_WORKFLOW = ["check_quality", "evaluate_hypotheses", "decompose_uncertainty", "challenge_interpretation", "reproduce_independent"]
ACTION_IDS = {a["id"] for a in ACTIONS}


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
    return {"version": REGISTRY_VERSION, "capabilities": out, "actions": ACTIONS, "facts": FACTS, "autopilot_levels": AUTOPILOT_LEVELS,
            "autonomy_levels": AUTONOMY_LEVELS, "restricted_workflow": RESTRICTED_WORKFLOW}


def method_ids() -> set[str]:
    return {m for c in CAPABILITIES for m in c["methods"]}
