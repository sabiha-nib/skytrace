"""Phase 6 capability catalogue: the 300 concepts of the Phase 6 brief (§19, domains A–AD), plus concepts this project
added, each with a status, a priority group (§20), evidence in the repository and the test that verifies it.

    python scripts/phase6_catalogue.py      # writes docs/phase6_catalogue.json and docs/PHASE6_CATALOGUE.md

Every count in the Markdown is computed from the rows below. tests/unit/test_phase6_catalogue.py checks that the
catalogue is well formed, that every cited file exists, that every cited test function exists, that every concept
marked existing or new cites both evidence and a verification, and that synonyms are merged rather than counted.

Status   E existing (built in 0.5 or earlier) · N new in 0.6 · D deferred (not built; nothing claims it) ·
         B blocked (needs a service or data this environment refuses) · X out of scope (not applicable or not advisable).
Group    F Foundation · H High Impact · S Signature · R Frontier (research-intensive), per §20 of the brief.
Synonyms A brief concept that names the same capability as another is recorded with `duplicate_of` and not counted as a
         distinct concept; concepts this project added (IDs P6-X..) keep the distinct count at or above 300.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = {"E": "existing", "N": "new in 0.6", "D": "deferred", "B": "blocked", "X": "out of scope"}
GROUP = {"F": "Foundation", "H": "High Impact", "S": "Signature", "R": "Frontier"}
PRIORITY = {"F": "P1", "H": "P2", "S": "P2", "R": "P3"}
DEFAULT_LIMIT = {"D": "Not built in 0.6; no control or document claims it.", "E": "", "N": ""}

RS, ROS, NB, CP2 = "tests/unit/test_research_session.py", "tests/unit/test_research_os.py", "tests/unit/test_notebook_package.py", "tests/unit/test_copilot2.py"
E2E, APP, API, DISC = "tests/e2e/test_controls.py", "tests/e2e/test_app.py", "tests/integration/test_api.py", "tests/unit/test_discovery.py"
STAT, OFF, TOOLS, AI = "tests/unit/test_static_preview.py", "tests/unit/test_offline_workflow.py", "tests/unit/test_tool_contracts.py", "tests/unit/test_report_ai.py"
ACQ, ARCH, PROV, FITS = "tests/unit/test_acquire.py", "tests/unit/test_archive.py", "tests/unit/test_provenance_check.py", "tests/unit/test_fits_wcs.py"
WL, MEAS, ASSESS, CAL, A11Y = "tests/unit/test_wavelength_flags.py", "tests/unit/test_measurement.py", "tests/unit/test_assess2.py", "tests/unit/test_calibration_v2.py", "tests/unit/test_accessibility.py"
FC6 = "tests/unit/test_phase6_catalogue.py"
SK = "src/skytrace/"
JS = "web/js/"

DOMAINS = ["A Research Session", "B Planning Intelligence", "C Observation Intelligence", "D Temporal Research", "E Image Analysis",
           "F Registration", "G Candidate Intelligence", "H Statistical Research", "I Hypothesis Intelligence", "J Uncertainty",
           "K Evidence", "L Scientific Methods", "M Experiment Studio", "N Data Quality", "O Acquisition", "P Research Notebook",
           "Q Visualization", "R Reporting", "S Collaboration", "T Copilot", "U Discovery Radar", "V Knowledge Graph",
           "W Automation", "X Mission System", "Y Accessibility and Learning", "Z Platform Reliability", "AA Security",
           "AB Scientific Validation", "AC Advanced Exploration", "AD Research Frontier"]

# (number, concept as named in the brief, status, group, evidence paths ";"-separated, verification, explanation, user outcome,
#  limitation, dependencies, duplicate_of)
R = []


def row(n, name, st, grp, ev, ver, expl, outcome, limit="", deps="", dup=None):
    R.append((n, name, st, grp, ev, ver, expl, outcome, limit, deps, dup))


# ---------------------------------------------------------------- A Research Session
row(1, "Session snapshots", "D", "H", "", "—", "Named restore points inside a session.", "Return to an earlier state without exporting.",
    "Not built: the exported session JSON (A9) and a branch (A2) are the ways to keep a copy.", "A9")
row(2, "Session branching", "N", "H", JS + "sessionsui.js", E2E + "::test_s9_sessions_dialog_export_import",
    "Copies the active session under a new id through the verified import path and records ‘Branched from …’ in its history.",
    "Try an alternative line of work without altering the original.", "Branches are independent copies; changes are not merged back.", "A6, A10")
row(3, "Session comparison", "D", "H", "", "—", "Side-by-side differences between two sessions.", "See what changed between two lines of work.", deps="A2")
row(4, "Session restoration", "N", "F", JS + "session.js", E2E + "::test_s2_planner_plans_runs_and_persists",
    "The active session is reloaded from storage at start-up (server files or this browser) and re-verified.", "Resume work after a reload.",
    "Static preview: stored in this browser only.")
row(5, "Session templates", "D", "H", "", "—", "Pre-filled sessions for common investigations.", "Start faster.",
    "Not built; missions (X232) offer guided starting points instead.", "X232")
row(6, "Session validation", "N", "F", SK + "session.py;" + JS + "sessioncore.js", RS + "::test_session_rules",
    "SCHEMA-1 validation of every field plus cross rules (history order, active run among runs, step dependencies precede).",
    "Malformed sessions are refused with a reason.")
row(7, "Session activity", "N", "F", SK + "session.py", RS + "::test_session_rules",
    "Append-only history of events (sequence number, time, kind, summary, reference).", "See what was done and when.",
    "History is capped at 2,000 events; the oldest are dropped first.")
row(8, "Session ownership metadata", "D", "H", "", "—", "Owner and contributor identities on a session.", "Know who did what.",
    "Skytrace has no user accounts; only ‘you’ versus ‘assistant draft’ authorship is recorded (S188).", "S190")
row(9, "Session export", "N", "F", JS + "sessionsui.js", E2E + "::test_s9_sessions_dialog_export_import",
    "Exports the session as canonical JSON with its content hash; import re-verifies it.", "Keep or move a session.")
row(10, "Session integrity", "N", "F", SK + "session.py;" + SK + "canon.py", RS + "::test_session_new_validates_and_hashes",
    "SHA-256 over the SKY-CANON-1 text of the session (notebook included); tampered imports are refused.", "Trust that a session is unaltered.")

# ---------------------------------------------------------------- B Planning Intelligence
row(11, "Natural-language question structuring", "N", "S", SK + "planner.py;" + JS + "planner.js", ROS + "::test_planner_known_plans",
    "PLAN-1 parses a question into an intent (kind, aspects, observation keys) with fixed ASCII rules; first match wins.",
    "Ask in plain words and get a structured question.", "Rule-based; questions outside the rules are reported as unplannable.")
row(12, "Research intent validation", "N", "F", SK + "planner.py", ROS + "::test_planner_known_plans",
    "Intents are schema-validated; a model-proposed intent is used only if it validates.", "No unvalidated plan reaches execution.")
row(13, "Plan dependency graph", "N", "H", SK + "planner.py;" + JS + "plannerui.js", RS + "::test_session_rules",
    "Each step lists the steps it depends on; validation refuses dependencies that do not precede; execution waits for them.",
    "Steps run in a sound order.", "Shown as ‘after step …’, not drawn as a diagram.")
row(14, "Prerequisite checking", "N", "F", SK + "capabilities.py;" + SK + "planner.py", ROS + "::test_planner_known_plans",
    "Each registered action states preconditions; unmet ones mark the step blocked with the reason.", "Know why a step cannot run.")
row(15, "Missing-input analysis", "E", "F", SK + "discovery.py", DISC + "::test_missing_inputs_make_questions_unanswerable",
    "DISC-1 names the inputs a question needs and marks it unanswerable when they are missing.", "Learn what data a question requires.")
row(16, "Plan preview", "N", "H", JS + "plannerui.js", E2E + "::test_s2_planner_plans_runs_and_persists",
    "The plan is shown with statuses and notes before anything runs.", "Review before executing.")
row(17, "Plan revision history", "N", "H", JS + "plannerui.js;" + SK + "session.py", E2E + "::test_s2_planner_plans_runs_and_persists",
    "Re-planning a question stores a new revision (r1, r2 …) in the session; earlier revisions are kept.", "Compare how a plan evolved.")
row(18, "Plan execution confirmation", "N", "F", JS + "plannerui.js;" + SK + "capabilities.py", E2E + "::test_s2_planner_plans_runs_and_persists",
    "Actions marked ‘confirm’ (re-analyses, long runs) run only after an explicit confirmation.", "Nothing expensive runs by surprise.")
row(19, "Plan comparison", "D", "R", "", "—", "Differences between two plans for related questions.", "Choose between approaches.", deps="B17")
row(20, "Plan reproducibility", "N", "S", SK + "planner.py;" + JS + "planner.js", ROS + "::test_browser_planner_missions_workflows_match_python",
    "The same question and facts give the same plan in Python and the browser; stored steps keep their inputs so they can be re-run.",
    "A plan can be regenerated and re-executed.")

# ---------------------------------------------------------------- C Observation Intelligence
row(21, "Observation compatibility matrix", "N", "S", SK + "compat.py;" + JS + "qualityui.js", ROS + "::test_matrix_is_the_logged_decisions",
    "COMPAT-1 matrix of every observation pair with the logged WLMATCH-2 decision and reason code; nothing is re-decided.",
    "See at a glance which observations can be compared and why not.")
row(22, "Metadata difference inspector", "N", "H", JS + "qualityui.js", E2E + "::test_s3_quality_matrix_metadata_sequences",
    "Field-by-field metadata of two observations with differing fields highlighted.", "Spot why two observations differ.")
row(23, "Duplicate observation detection", "N", "F", SK + "compat.py", ROS + "::test_duplicate_files_are_detected",
    "Observations whose files have the same SHA-256 are reported as duplicates.", "Avoid counting one exposure twice.")
row(24, "Observation grouping", "E", "H", JS + "explorer.js", E2E + "::test_b_explorer_controls",
    "Observations are grouped by detector on the ruler and filterable by status in the explorer.", "Navigate many observations.")
row(25, "Observation quality summaries", "E", "H", JS + "explorer.js;" + SK + "ai/tools.py", TOOLS,
    "Per-observation status, quality note and exclusion reason.", "Know whether an observation was usable.")
row(26, "Coverage gaps", "N", "H", SK + "compat.py;" + JS + "qualityui.js", E2E + "::test_s3_quality_matrix_metadata_sequences",
    "Per detector, visits and intervals without observations (≥ 30 days) from the recorded mid-times; Quality → Coverage tab.", "See where the time coverage is thin.",
    "Gaps are stated in days from recorded times; their cause (scheduling, visibility) is not inferred.")
row(27, "Channel relationships", "E", "S", SK + "science/wavelength.py", WL,
    "WLMATCH-2: two observations are photometrically comparable only on the same detector with wavelengths at the target within half a channel.",
    "Compare like with like.")
row(28, "Epoch grouping", "N", "H", SK + "compat.py", ROS + "::test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits",
    "Exposures are grouped into visits by time; sequences say how many distinct visits they span.", "Reason in visits, not single exposures.")
row(29, "Instrument comparison", "X", "R", "", "—", "Comparison across instruments.", "—",
    "Out of scope: Skytrace handles one instrument (SPHEREx); its six detectors are compared under C21 and C27.")
row(30, "Observation provenance export", "E", "F", SK + "package.py", DISC + "::test_package_is_deterministic_and_self_verifying",
    "PKG-1 package carries the bundle manifest, per-file SHA-256 and archive identifiers.", "Hand on exactly which files were used.")

# ---------------------------------------------------------------- D Temporal Research
row(31, "Multi-epoch playback", "N", "S", JS + "timemachine.js", E2E + "::test_s3_quality_matrix_metadata_sequences",
    "Plays only compatible sequences (SEQ-1) frame by frame; never interpolates between epochs; states when only two exist.",
    "Watch a source across all comparable epochs.", "Frames are the recorded cutouts; no frame is synthesised.")
row(32, "Timeline annotations", "D", "H", "", "—", "Notes pinned to points on the timeline.", "Mark events in time.",
    "The session schema has annotations; no timeline control writes them yet.", "A6")
row(33, "Temporal coverage map", "E", "H", JS + "ruler.js", APP + "::test_03_run_analysis_and_ruler",
    "The observation ruler places every observation by time and detector.", "See when the target was observed.")
row(34, "Epoch selection presets", "D", "H", "", "—", "One-click choices such as first/last epoch.", "Faster comparisons.",
    "Not built; the Time Machine lists compatible partners instead.")
row(35, "Time-gap diagnostics", "N", "H", SK + "radar.py;" + SK + "compat.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Unobserved intervals become Discovery Radar items (R8) with the detector, visit and length in days.", "Know which intervals lack data.",
    deps="C26")
row(36, "Temporal comparison reports", "D", "H", "", "—", "A narrative report across all epochs of a sequence.", "Summarise change over time.",
    "Not built; the sequence record export (D39) and the investigation report cover the parts that exist.", "D39")
row(37, "Time-dependent measurements", "E", "S", JS + "figurestudio.js;" + SK + "analysis.py", OFF + "::test_expected_outcomes_on_synthetic_truth",
    "Aperture flux and position per exposure with uncertainties, against time.", "See how a measurement evolves.")
row(38, "Compatible sequence validation", "N", "F", SK + "compat.py", ROS + "::test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits",
    "A sequence is a set of observations in which every pair is accepted by WLMATCH-2 (a clique per detector).", "Playback never mixes incomparable data.")
row(39, "Playback export", "N", "H", JS + "timemachine.js", E2E + "::test_s3_quality_matrix_metadata_sequences",
    "Exports the sequence record (keys, times, method, run hash) as JSON.", "Keep the exact frames that were played.")
row(40, "Temporal investigation templates", "N", "H", SK + "planner.py", ROS + "::test_planner_known_plans",
    "Change and coverage plan templates.", "Start a temporal investigation.", dup="AC287")

# ---------------------------------------------------------------- E Image Analysis
row(41, "Image profile inspection", "D", "H", "", "—", "Pixel profiles along a line.", "Inspect a source's shape.")
row(42, "Pixel-value inspection", "D", "H", "", "—", "Read individual pixel values under the pointer.", "Check values directly.")
row(43, "Coordinate overlays", "E", "H", JS + "viewer.js;" + JS + "explorer.js", E2E + "::test_b_explorer_controls",
    "Target position, aperture and reference stars drawn over the cutout.", "See where measurements were taken.")
row(44, "Image histogram comparison", "D", "H", "", "—", "Pixel histograms of two images.", "Compare image statistics.")
row(45, "Region selection", "D", "H", "", "—", "Draw a region on an image.", "Measure a chosen area.")
row(46, "Region statistics", "D", "H", "", "—", "Statistics inside a drawn region.", "Quantify an area.", deps="E45")
row(47, "Image-quality diagnostics", "E", "F", SK + "science/flags.py;" + SK + "ai/tools.py", WL,
    "FLAGPOL-1 quality-flag checks inside the aperture, with reasons.", "Know which images are compromised.")
row(48, "Mask visualization", "E", "H", JS + "viewer.js", E2E + "::test_b_explorer_controls",
    "Rejected pixels (flag mask) can be shown over the image.", "See which pixels were excluded.")
row(49, "Image processing history", "E", "F", SK + "analysis.py", PROV,
    "Each processing step is logged in the record with its method ID and outcome.", "Trace what was done to the data.")
row(50, "Figure export settings", "N", "H", JS + "figurestudio.js;" + JS + "records.js", E2E + "::test_s10_figure_studio",
    "Figure title and axis labels can be set before SVG export; units and provenance stay attached.", "Export figures that fit a report.")

# ---------------------------------------------------------------- F Registration
row(51, "Registration method registry", "E", "F", SK + "capabilities.py", DISC + "::test_registry_names_only_real_methods_and_tests",
    "Registration and astrometry methods are registered capabilities with versions and limitations.", "Know which method aligned the data.")
row(52, "Reference-image selection", "X", "H", "", "—", "Choosing a reference image to register to.", "—",
    "Not applicable: each exposure is registered to Gaia reference stars (plate solution), not to another image.")
row(53, "Transformation visualization", "D", "H", "", "—", "Drawing each plate transformation.", "See the alignment geometrically.")
row(54, "Residual maps", "D", "H", "", "—", "Spatial maps of reference-star residuals.", "See where alignment is poor.",
    "Median plate residuals are reported per exposure (F56); spatial maps are not drawn.")
row(55, "Registration diagnostics history", "D", "H", "", "—", "Registration diagnostics tracked across runs.", "See whether alignment improved.")
row(56, "Registration quality comparisons", "E", "S", SK + "view.py", DISC + "::test_registration_on_fixture_pairs",
    "REGDIAG-1 compares the registration of two epochs (residuals, reference counts, overlap).", "Judge whether two epochs are aligned well enough.")
row(57, "Alignment failure explanations", "E", "H", SK + "science/astrometry.py;" + SK + "ai/local.py", DISC + "::test_registration_known_answer",
    "Failed or rejected plate solutions are logged with reasons; the copilot's alignment answer reports them.", "Understand why alignment failed.")
row(58, "Reproducible transformation settings", "E", "F", SK + "analysis.py", API + "::test_record_export_and_verified_import",
    "Registration parameters are part of the analysis parameters and the record's content hash; replay reproduces them.", "Repeat the same alignment.")
row(59, "Registration compatibility matrix", "D", "R", "", "—", "Matrix of which epochs register consistently.", "Choose well-aligned pairs.", deps="F56")
row(60, "Registration report export", "D", "H", "", "—", "A dedicated registration report.", "Share alignment evidence.",
    "REGDIAG-1 values appear in the discovery report and package, not as a separate report.")

# ---------------------------------------------------------------- G Candidate Intelligence
row(61, "Candidate workbench", "E", "S", JS + "discovery.js", E2E + "::test_l_discovery_engine",
    "The Discovery Engine shows each candidate outcome with its inventory, questions, tests and next steps.", "Examine a candidate in one place.")
row(62, "Candidate review queues", "D", "H", "", "—", "Queues of candidates awaiting review.", "Work through many candidates.",
    "Investigations are per target; there are few candidates per run.")
row(63, "Candidate status history", "D", "H", "", "—", "A candidate's status across runs.", "See how a candidate's standing changed.")
row(64, "Candidate grouping", "D", "R", "", "—", "Grouping similar candidates.", "Find patterns.")
row(65, "Candidate comparison", "D", "H", "", "—", "Two candidates side by side.", "Compare candidates.", "Saved records can be compared (AC285).")
row(66, "Candidate provenance", "E", "F", SK + "view.py;" + JS + "graph.js", DISC + "::test_evidence_graph_links_each_tested_explanation_to_its_claim",
    "The evidence graph links each claim to measurements, observations, methods and files.", "Trace a candidate to its data.")
row(67, "Candidate rejection reasons", "E", "F", SK + "science/wavelength.py;" + SK + "science/flags.py", WL,
    "Every rejected pair or observation carries a logged reason code.", "Know why something was not used.")
row(68, "Candidate uncertainty", "E", "S", SK + "uncertainty.py", DISC + "::test_uncertainty_recomputes_logged_values_exactly",
    "UNC-1 decomposes each outcome's uncertainty into recomputed components.", "Know how uncertain a candidate is.")
row(69, "Candidate evidence coverage", "N", "S", SK + "ledger.py", ROS + "::test_ledger_counts_support_and_flags_conflicts",
    "LEDGER-1 counts direct evidence, comparisons, observations and detectors behind each claim and flags single-item support.",
    "See how broadly a claim is supported.", "Counts are not weights; one strong item can matter more than many weak ones.")
row(70, "Candidate review exports", "D", "H", "", "—", "Export of review decisions.", "Share reviews.", deps="S183")

# ---------------------------------------------------------------- H Statistical Research
row(71, "Fit diagnostics", "E", "H", SK + "science/astrometry.py;" + JS + "lab.js", DISC + "::test_registration_known_answer",
    "Motion fits report residual scatter, rejected epochs and baseline.", "Judge fit quality.")
row(72, "Residual inspection", "E", "H", JS + "lab.js;" + JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "Position offsets per exposure against time (positions figure) and per-exposure plate residuals.", "Look for structure in residuals.")
row(73, "Parameter covariance inspection where available", "E", "R", SK + "science/astrometry.py;" + SK + "science/centroid.py", MEAS,
    "Fit covariances are computed and recorded where the method yields them.", "Know correlated uncertainties.",
    "Recorded in the record; not visualised.")
row(74, "Sensitivity matrices", "E", "S", SK + "stability.py", API + "::test_phase3_params_and_stability",
    "STAB-1 re-runs the analysis over a fixed parameter set and tabulates the outcome per setting.", "See which choices matter.")
row(75, "Distribution comparisons", "D", "R", "", "—", "Comparing measured distributions with expectations.", "Detect excess scatter.",
    "The z histogram figure shows the distribution but makes no formal comparison.")
row(76, "Robustness tests", "N", "S", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control",
    "EXP-1 robustness experiment re-runs within bounded parameter ranges and checks outcome categories.", "Learn whether a result survives reasonable changes.",
    "Passing means the categories held for the tried settings, not that the result is correct.")
row(77, "Numerical precision diagnostics", "D", "R", "", "—", "Detecting precision loss in computations.", "Trust numbers near limits.")
row(78, "Boundary-condition analysis", "D", "R", "", "—", "Behaviour at parameter-range edges.", "Know where methods break.",
    "Parameter bounds are enforced (AB273), but behaviour at the bounds is not analysed.")
row(79, "Missing-data sensitivity", "D", "R", "", "—", "Leave-one-out and missing-epoch experiments.", "Know whether one observation drives a result.")
row(80, "Known-answer validation", "E", "F", SK + "synthetic.py", OFF + "::test_expected_outcomes_on_synthetic_truth",
    "Synthetic fixtures with injected answers; tests assert the recovered outcomes.", "Trust that methods recover known truth.")

# ---------------------------------------------------------------- I Hypothesis Intelligence
row(81, "Hypothesis templates", "E", "S", SK + "hypotheses.py", DISC + "::test_hypotheses_known_answers",
    "HYPO-1 fixed competing explanations per question, each with rule-based tests.", "Consider alternatives systematically.")
row(82, "Hypothesis version history", "N", "H", SK + "session.py;" + JS + "session.js", RS + "::test_version_histories_are_kept_bounded_and_hashed",
    "Edits to your own hypotheses keep up to 20 earlier wordings in the session.", "See how a hypothesis was refined.")
row(83, "Evidence requirements", "E", "F", SK + "hypotheses.py", DISC + "::test_hypotheses_never_produce_probabilities_and_use_known_statuses",
    "Each test states its rule, including what an untestable test would need.", "Know what evidence would decide a test.")
row(84, "Contradiction tracking", "N", "S", SK + "ledger.py;" + SK + "hypotheses.py", ROS + "::test_ledger_counts_support_and_flags_conflicts",
    "Contradicted tests set an explanation to ‘contradicted’; LEDGER-1 rule C4 flags tests within one explanation that disagree.",
    "See which explanations conflict with the data.")
row(85, "Falsification history", "D", "R", "", "—", "When and why explanations were ruled out across runs.", "Track eliminated explanations.")
row(86, "Alternative explanation maps", "E", "S", JS + "arena.js", E2E + "::test_m_hypothesis_arena",
    "The Hypothesis Arena lays out competing explanations and their tests side by side.", "Compare explanations at a glance.")
row(87, "Hypothesis dependency graphs", "D", "R", "", "—", "Which explanations depend on others.", "Understand nested explanations.")
row(88, "Hypothesis comparison reports", "E", "H", SK + "discovery.py;" + JS + "records.js", DISC + "::test_hypotheses_known_answers",
    "The discovery report (JSON) lists every explanation with test statuses and rules.", "Share the comparison.")
row(89, "Inconclusive test tracking", "N", "H", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Explanations whose tests are untested or inconclusive become radar items (R2), or R3 when no implemented test exists.",
    "Know which tests remain open.")
row(90, "Hypothesis export", "E", "F", SK + "package.py", DISC + "::test_package_is_deterministic_and_self_verifying",
    "Hypothesis evaluations travel in the record export and the reproducibility package.", "Keep the evaluations with the data.")

# ---------------------------------------------------------------- J Uncertainty
row(91, "Uncertainty decomposition", "E", "S", SK + "uncertainty.py", DISC + "::test_uncertainty_recomputes_logged_values_exactly",
    "UNC-1 splits each outcome's uncertainty into named components recomputed from logged values.", "See what dominates the error.")
row(92, "Measurement uncertainty", "E", "F", SK + "science/photometry.py;" + SK + "science/centroid.py", MEAS,
    "Photometric and positional uncertainties from the data and the error model.", "Every value comes with an uncertainty.")
row(93, "Model uncertainty", "D", "R", "", "—", "Uncertainty from model choices quantified.", "Know how much modelling choices matter.",
    "Unmodelled systematics are listed as unquantified; sensitivity (H74) shows outcome changes, not an uncertainty.")
row(94, "Propagation methods", "E", "H", SK + "uncertainty.py", DISC + "::test_uncertainty_recomputes_logged_values_exactly",
    "Stated propagation formulas, recomputed exactly from the logged inputs.", "Verify how errors combine.")
row(95, "Sensitivity visualization", "N", "H", JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "Sensitivity figure: measured value per analysis setting from the recorded stability run.", "See sensitivity at a glance.",
    "Needs a recorded stability run.", "H74")
row(96, "Missing-data impact", "D", "R", "", "—", "Effect of missing observations.", "—", dup="H79")
row(97, "Method limitation summaries", "E", "F", SK + "capabilities.py", DISC + "::test_registry_names_only_real_methods_and_tests",
    "Every capability states its limitations.", "Know what a method cannot do.")
row(98, "Uncertainty provenance", "E", "F", SK + "uncertainty.py", DISC + "::test_uncertainty_recomputes_logged_values_exactly",
    "Each component names the record fields it came from.", "Trace an uncertainty to its source.")
row(99, "Uncertainty comparison", "D", "H", "", "—", "Comparing uncertainty budgets between runs.", "See whether a change reduced errors.")
row(100, "Uncertainty export", "E", "H", JS + "figures.js;" + SK + "package.py", E2E + "::test_n_uncertainty_and_figure_export",
    "Uncertainty components export as a figure and in the discovery report and package.", "Share the error budget.")

# ---------------------------------------------------------------- K Evidence
row(101, "Claim ledger", "N", "S", SK + "ledger.py;" + JS + "ledgerui.js", ROS + "::test_ledger_counts_support_and_flags_conflicts",
    "LEDGER-1 lists every claim with category, supporting items by kind and flags; one linked item is never called full support.",
    "See exactly what each claim rests on.")
row(102, "Evidence lineage", "E", "F", SK + "view.py;" + JS + "graph.js", APP + "::test_06_evidence_graph_traces_claim",
    "Evidence graph from claims to measurements, observations, methods and files.", "Follow a claim back to the files.")
row(103, "Contradiction inspection", "N", "S", SK + "ledger.py;" + JS + "ledgerui.js", E2E + "::test_s6_ledger_inspectors",
    "Fixed rules C1–C4 (raw vs calibrated, fits disagreeing > 3σ, motion vs catalogue, tests disagreeing) with details.",
    "Find and inspect conflicts in the evidence.", "Only the four stated rules are checked.")
row(104, "Orphaned evidence detection", "N", "H", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Usable measurements with no wavelength-matched partner (radar R4) and ledger relationship gaps (R9) are reported.",
    "Find evidence that no comparison uses.")
row(105, "Provenance completeness", "N", "F", SK + "ledger.py", ROS + "::test_ledger_counts_support_and_flags_conflicts",
    "Counts items missing provenance fields (e.g. observations without an archive URL); absence outcomes are not flagged as gaps.",
    "Know where provenance is incomplete.")
row(106, "Source-file integrity", "E", "F", SK + "bundle.py;" + SK + "quality.py", ARCH,
    "Every bundle file has a SHA-256 in the manifest, verified on load; DQ-FILES reports the result.", "Trust the files are unaltered.")
row(107, "Method dependency tracing", "N", "H", JS + "ledgerui.js;" + SK + "capabilities.py", E2E + "::test_s6_ledger_inspectors",
    "The method inspector lists, for each claim, the method versions and parameters it depends on.", "See which methods a claim relies on.")
row(108, "Evidence graph filtering", "E", "H", JS + "graph.js", E2E + "::test_e_graph_controls",
    "Filter the evidence graph by node kind and focus on a node's neighbourhood.", "Read large graphs.")
row(109, "Evidence graph comparison", "D", "R", "", "—", "Differences between two evidence graphs.", "See how evidence changed between runs.")
row(110, "Evidence graph export", "E", "H", JS + "records.js", E2E + "::test_g_records_controls",
    "The evidence graph downloads as JSON.", "Analyse the graph elsewhere.")

# ---------------------------------------------------------------- L Scientific Methods
row(111, "Method documentation registry", "E", "F", SK + "capabilities.py;scripts/gen_discovery_methods.py", DISC + "::test_registry_names_only_real_methods_and_tests",
    "Capability registry plus method documents generated from code.", "Look up any method.")
row(112, "Method assumptions", "N", "H", SK + "capabilities.py", ROS + "::test_registry_actions_and_capabilities_are_consistent",
    "CAPREG-2 adds preconditions and data types to every capability, alongside its limitations.", "Know when a method applies.")
row(113, "Method compatibility", "N", "H", SK + "capabilities.py;" + SK + "planner.py", ROS + "::test_registry_actions_and_capabilities_are_consistent",
    "Actions declare preconditions, outputs and where they can run (server, browser, recorded, unavailable).", "Know whether a method can run here.")
row(114, "Method version comparison", "D", "R", "", "—", "Results of two versions of one method compared.", "See the effect of a method change.")
row(115, "Method execution history", "E", "F", SK + "analysis.py", PROV,
    "Every step records the method ID and version used; session history logs executed actions.", "Know which method ran when.")
row(116, "Method validation coverage", "N", "F", SK + "capabilities.py", ROS + "::test_registry_actions_and_capabilities_are_consistent",
    "Each capability records its validation status and the tests that cover it.", "Know how well a method is tested.")
row(117, "Method limitation warnings", "E", "F", SK + "capabilities.py;" + JS + "discovery.js", E2E + "::test_q_copilot_sections_and_capabilities",
    "Limitations are shown wherever a method's result is shown.", "Read results with their caveats.")
row(118, "Known-answer examples", "E", "H", "scripts/gen_discovery_methods.py;docs/DISCOVERY_METHODS.md", DISC + "::test_hypotheses_known_answers",
    "Method documents include the outcomes on the synthetic fixtures, generated from code.", "See a method work on a known case.")
row(119, "Method reproducibility", "E", "F", SK + "provenance_check.py", PROV,
    "PROVCHECK-1 re-runs an analysis and compares content hashes.", "Confirm a result reproduces exactly.")
row(120, "Method retirement tracking", "D", "R", "", "—", "Structured record of superseded methods.", "Know which methods were replaced.",
    "Superseded versions are named in the release notes only.")

# ---------------------------------------------------------------- M Experiment Studio
row(121, "Experiment templates", "N", "S", SK + "experiments.py;" + JS + "experimentsui.js", ROS + "::test_experiment_validation_and_negative_control",
    "Parameter, sensitivity, method comparison, reproducibility, negative control and robustness templates.", "Set up a standard experiment quickly.")
row(122, "Controlled parameter experiments", "N", "S", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control",
    "Up to six user-chosen parameter sets within the server's bounds, each against the default baseline.", "Test one choice at a time.",
    "At most 8 runs per experiment.")
row(123, "Baseline comparison", "N", "H", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control",
    "Every experiment runs the default-parameter baseline and compares outcome categories with it.", "Always know the reference point.")
row(124, "Method comparison", "N", "S", SK + "experiments.py", API + "::test_phase6_research_planner_sessions_experiments_connectors",
    "Compares raw and reference-calibrated pair differences on the same run.", "See how much calibration changes a result.",
    "A difference is expected when calibration matters; it is reported, not judged.")
row(125, "Negative controls", "N", "S", SK + "experiments.py;" + SK + "synthetic.py", ROS + "::test_experiment_validation_and_negative_control",
    "Runs the same analysis on a synthetic fixture with no injected effect; refused when no control fixture exists.", "Check the method does not invent signals.",
    "A control must be a different fixture with the effect absent by construction; with two fixtures, syn-var-1 has no motion control and syn-hpm-1 no variability control (reported as not available).")
row(126, "Repeated-run experiments", "N", "F", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control",
    "Reproducibility experiment runs the baseline twice independently and compares content hashes.", "Confirm determinism.")
row(127, "Experiment dependencies", "D", "R", "", "—", "Experiments that build on other experiments.", "Chain experiments.")
row(128, "Experiment failure analysis", "N", "H", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control",
    "Runs that fail are recorded with the error and counted as not passed, never dropped.", "Know why an experiment did not complete.")
row(129, "Experiment result comparison", "D", "H", "", "—", "Two experiments' results side by side.", "Compare experiment outcomes.")
row(130, "Experiment report export", "N", "H", JS + "notebook.js;" + JS + "executor.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Experiments are stored in the session and appear in the notebook export and session package.", "Share experiment results with their configuration.",
    "No standalone experiment report file.")

# ---------------------------------------------------------------- N Data Quality
row(131, "Data-quality rule registry", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-1: eleven named checks, each with a stated rule; outcomes invalid / incompatible / not available / not checked / valid; no score.",
    "See every check and its rule.")
row(132, "Missing metadata", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-META checks required observation fields are present.", "Find incomplete observations.")
row(133, "Invalid units", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-UNITS checks image units (MJy/sr) and variance units against what the photometry assumes.", "Catch unit mistakes.")
row(134, "Inconsistent identifiers", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-META and DQ-RECORD check that observation keys, files and manifest entries agree.", "Catch mismatched identifiers.")
row(135, "File integrity", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-FILES.", "—", dup="K106")
row(136, "Quality-flag summaries", "N", "H", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-FLAGS summarises FLAGPOL-1 decisions over all observations.", "See flag problems at a glance.")
row(137, "Unsupported calibration detection", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-CAL reports pairs with fewer than three wavelength-matched reference stars or no calibration check.", "Know when calibration is unsupported.")
row(138, "Processing-history validation", "N", "F", SK + "quality.py", ROS + "::test_quality_outcomes_and_injected_defects",
    "DQ-STEPS checks that every logged processing step completed and lists failed, skipped or rejected steps with their reasons.", "Trust the processing record.")
row(139, "Data-quality comparison", "D", "H", "", "—", "Quality outcomes compared between runs or targets.", "See whether quality improved.",
    "Repeated issues across saved records are linked in the knowledge graph (V214).")
row(140, "Data-quality export", "N", "H", SK + "server/research.py;" + JS + "qualityui.js", API + "::test_phase6_research_planner_sessions_experiments_connectors",
    "The research report (quality checks with rules and counts) is served as JSON and recorded in the static preview.", "Keep the quality assessment.")

# ---------------------------------------------------------------- O Acquisition
row(141, "Archive connector registry", "N", "F", SK + "connectors.py", ROS + "::test_connector_previews_match_acquisition_and_send_nothing",
    "Four connectors (SPHEREx SIA, SPHEREx TAP, SIMBAD, Gaia cone) with parameter schemas and availability from the environment report.",
    "Know which archives can be queried here.", "All four are blocked in this environment; previews only.")
row(142, "Query templates", "N", "H", SK + "connectors.py", ROS + "::test_connector_previews_match_acquisition_and_send_nothing",
    "Each connector's parameters have a schema and defaults.", "Build valid queries.")
row(143, "Query validation", "N", "F", SK + "connectors.py", ROS + "::test_connector_previews_match_acquisition_and_send_nothing",
    "Parameters are validated; the preview is built by the real request builder and nothing is sent.", "See the exact request before any network use.")
row(144, "Download manifests", "E", "F", SK + "bundle.py;" + SK + "archive/acquire.py", ARCH,
    "Bundles carry a manifest with source URL, size and SHA-256 per file.", "Know exactly what was downloaded.")
row(145, "Transfer diagnostics", "E", "F", "scripts/diagnose_environment.py", ACQ,
    "Per-service reachability verdicts written to data/environment_report.json.", "Learn why acquisition cannot run.")
row(146, "Retry records", "E", "H", SK + "archive/net.py", ROS + "::test_retry_after_is_honoured_and_bounded",
    "Bounded retries with back-off; Retry-After honoured up to 60 s; attempts logged.", "Transient failures are handled visibly.")
row(147, "Cache inspection", "D", "H", "", "—", "Browsing the response cache.", "See what is cached.", "Cached responses are labelled ‘cache’ in records.")
row(148, "Dataset version metadata", "E", "F", SK + "archive/acquire.py", ACQ,
    "Release (QR3, QR2 fallback) and DOI recorded per observation.", "Know which data release was used.")
row(149, "Archive response validation", "E", "F", SK + "fitsio.py;" + SK + "wcs.py", FITS,
    "FITS structure and WCS are validated before use.", "Malformed responses are refused.")
row(150, "Acquisition provenance", "E", "F", SK + "archive/acquire.py;" + SK + "provenance.py", PROV,
    "Origin labels (archive, cache, synthetic) and request details on every record.", "Know where data came from.")

# ---------------------------------------------------------------- P Research Notebook
row(151, "Structured note blocks", "N", "S", JS + "notebook.js;" + SK + "session.py", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Thirteen block types (heading, paragraph, observation, measurement, evidence, hypothesis, experiment, figure, warning, parameters, citation, question, conclusion).",
    "Write structured research notes.")
row(152, "Evidence-linked annotations", "N", "S", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Reference blocks point to recorded items and show their current values; broken references are marked.", "Notes stay tied to evidence.")
row(153, "Figure insertion", "N", "H", JS + "notebookhelpers.js;" + JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "A Figure Studio figure can be inserted as a figure block.", "Put figures in notes.")
row(154, "Observation references", "N", "H", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Blocks referencing an observation key resolve to its recorded metadata.", "Cite observations precisely.")
row(155, "Hypothesis references", "N", "H", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Blocks referencing a HYPO-1 explanation or your own hypothesis show its current status.", "Cite explanations with their status.")
row(156, "Experiment references", "N", "H", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Blocks referencing a stored experiment show its result.", "Cite experiments.")
row(157, "Note version history", "N", "H", JS + "notebook.js", RS + "::test_version_histories_are_kept_bounded_and_hashed",
    "Each edit keeps the previous text (≤ 20 versions); undo restores deleted blocks.", "Recover earlier wording.")
row(158, "Notebook export", "N", "F", JS + "notebook.js;" + JS + "zipstore.js", NB + "::test_zipstore_output_is_valid_and_deterministic",
    "Markdown export labelled [you] / [recorded] / [draft], and a deterministic session package ZIP.", "Share notes with their provenance.")
row(159, "Notebook search", "N", "H", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports",
    "Filters blocks by text.", "Find notes quickly.")
row(160, "Notebook integrity", "N", "F", SK + "session.py", RS + "::test_session_new_validates_and_hashes",
    "The notebook is part of the session hash.", "—", dup="A10")

# ---------------------------------------------------------------- Q Visualization
row(161, "Plot presets", "N", "H", JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "FIG-2 figures: timeline, flux per sequence, z histogram, positions, quality, sensitivity.", "Make standard figures in one step.")
row(162, "Figure annotations", "D", "H", "", "—", "Text and arrows on figures.", "Point out features.")
row(163, "Axis configuration", "N", "H", JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "Axis labels and title can be edited; units stay in the caption.", "Adapt labels to the audience.", "Scales and ranges are fixed by the data.")
row(164, "Unit-aware plotting", "N", "F", JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "Every figure states its units and axis quantities.", "Never guess a unit.")
row(165, "Accessible encodings", "E", "H", JS + "figurestudio.js;" + JS + "charts.js", E2E + "::test_y_accessible_names",
    "Charts are labelled images with text summaries; detectors use distinct colours plus labels.", "Figures readable without colour vision or sight.")
row(166, "Chart provenance", "N", "F", JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "Each figure names its source data, method and run content hash.", "Trace a figure to the data.")
row(167, "Figure version history", "D", "H", "", "—", "Earlier versions of a figure.", "Revert figure edits.")
row(168, "Multi-panel figures", "D", "H", "", "—", "Several plots in one figure.", "Compose comparisons.")
row(169, "Figure comparison", "D", "H", "", "—", "Two figures side by side.", "Compare runs visually.")
row(170, "Export validation", "N", "F", JS + "records.js;" + JS + "figurestudio.js", E2E + "::test_s10_figure_studio",
    "SVG export is generated from the rendered figure; the test checks it parses as SVG and carries its metadata; no PDF export is offered.", "Exports open correctly.",
    "PDF is not offered because no validated PDF writer is available.")

# ---------------------------------------------------------------- R Reporting
row(171, "Investigation reports", "E", "F", SK + "report.py", AI,
    "Markdown report: findings, method versions, limitations, provenance.", "Share an investigation.")
row(172, "Evidence reports", "N", "H", SK + "server/research.py", API + "::test_phase6_research_planner_sessions_experiments_connectors",
    "The research report JSON carries the ledger (claims, contradictions, completeness).", "Share the evidence assessment.")
row(173, "Method reports", "E", "H", "scripts/gen_discovery_methods.py", DISC + "::test_registry_names_only_real_methods_and_tests",
    "Generated method documents.", "Read how methods work.")
row(174, "Data-quality reports", "N", "H", SK + "server/research.py", API, "—", "—", dup="N140")
row(175, "Reproducibility reports", "E", "F", SK + "package.py", DISC + "::test_package_is_deterministic_and_self_verifying",
    "PKG-1 package with reproduction instructions and SHA256SUMS.", "Let others reproduce the result.")
row(176, "Hypothesis reports", "E", "H", SK + "discovery.py", DISC, "—", "—", dup="I88")
row(177, "Experiment reports", "N", "H", JS + "notebook.js", E2E, "—", "—", dup="M130")
row(178, "Figure packages", "D", "H", "", "—", "A bundle of all figures with provenance.", "Hand over figures together.",
    "Figures export one at a time as SVG.")
row(179, "Machine-readable exports", "E", "F", JS + "records.js", E2E + "::test_g_records_controls",
    "Record, graph, discovery report and package as JSON/ZIP.", "Process results programmatically.")
row(180, "Publication-ready export templates", "D", "R", "", "—", "Journal-style templates.", "Draft papers faster.",
    "Not built; nothing is labelled publication-ready.")

# ---------------------------------------------------------------- S Collaboration
row(181, "Review assignments", "X", "R", "", "—", "Assigning reviews to people.", "—", "Out of scope: single-user local application without accounts.")
row(182, "Evidence-linked comments", "D", "H", "", "—", "Comments attached to evidence items.", "Discuss specific evidence.",
    "Notebook reference blocks (P152) cover single-user notes on evidence.")
row(183, "Review status", "N", "H", JS + "plannerui.js;" + SK + "missions.py", E2E + "::test_s2_planner_plans_runs_and_persists",
    "Inspection steps stay ‘needs review’ until you mark them reviewed with a note; mission review tasks likewise.", "Human checks are explicit.")
row(184, "Reviewer annotations", "D", "H", "", "—", "Annotations by a second reviewer.", "Independent review.", deps="S190")
row(185, "Review history", "N", "H", SK + "session.py", RS + "::test_session_rules",
    "Review actions are session history events with notes.", "See when reviews happened.")
row(186, "Read-only sharing", "E", "H", "scripts/build_static.py", STAT,
    "The static preview presents recorded results read-only; it can be hosted as a private page and shared.", "Show results without a server.",
    "Shares a fixed build; it does not sync with later work.")
row(187, "Exportable review packages", "N", "H", JS + "notebook.js", NB + "::test_zipstore_output_is_valid_and_deterministic",
    "Session package ZIP (session, notebook, README) for a reviewer, alongside the PKG-1 package.", "Hand a reviewer everything.")
row(188, "Author attribution", "N", "F", JS + "notebook.js;" + SK + "session.py", E2E + "::test_h2_copilot_sources_drafts_and_plan",
    "Every block is authored by ‘you’ or ‘assistant draft’; drafts stay labelled until accepted.", "Never confuse your text with the assistant's.")
row(189, "Change conflict handling", "D", "H", "", "—", "Detecting concurrent edits to one session.", "Avoid lost edits.",
    "One browser tab per session is assumed; the last save wins.")
row(190, "Collaboration permissions", "X", "R", "", "—", "Per-user permissions.", "—", "Out of scope without accounts.")

# ---------------------------------------------------------------- T Copilot
row(191, "Capability-aware question routing", "N", "S", SK + "ai/local.py;" + SK + "ai/tools.py", CP2 + "::test_phase6_intents_pass_the_guard",
    "Questions route only to the 16 registered read-only tools; the browser port is parity-tested.", "Answers use only real capabilities.")
row(192, "Research intent extraction", "N", "S", SK + "ai/tools.py;" + SK + "planner.py", CP2 + "::test_plan_tool_executes_nothing_and_uses_registered_actions",
    "plan_investigation turns a question into a PLAN-1 intent and steps.", "The copilot understands what you want to test.")
row(193, "Structured test plans", "N", "S", SK + "ai/local.py;" + JS + "copilot.js", E2E + "::test_h2_copilot_sources_drafts_and_plan",
    "Plan answers list registered steps; ‘Plan this question in the Planner’ hands over the exact question; nothing executes.",
    "Move from a question to a runnable plan.")
row(194, "Evidence-linked responses", "E", "F", SK + "ai/guard.py;" + JS + "copilot.js", E2E + "::test_h_copilot_controls",
    "Claims cite tool-call evidence ids; GUARD-3 checks every cited number against the tool outputs.", "Check every number.")
row(195, "Limitation explanations", "E", "F", SK + "ai/local.py", AI, "Every answer lists its limitations.", "Read answers with caveats.")
row(196, "Method explanations", "E", "H", SK + "ai/tools.py", TOOLS, "Tool outputs name the method versions; answers show the tools used.", "Know how an answer was computed.")
row(197, "Investigation summaries", "E", "H", SK + "ai/tools.py", TOOLS, "generate_investigation_summary.", "Get an overview.")
row(198, "Source-grounded note drafting", "N", "S", SK + "ai/local.py;" + JS + "copilot.js;" + JS + "notebook.js", E2E + "::test_h2_copilot_sources_drafts_and_plan",
    "‘Add to notebook as draft’ inserts the answer and its limitations as assistant-draft blocks naming the source.", "Turn answers into notes safely.")
row(199, "Tool execution history", "E", "H", JS + "copilot.js", E2E + "::test_h_copilot_controls", "Every tool call with arguments and output is shown.", "Audit the assistant.")
row(200, "Response provenance", "N", "F", JS + "copilot.js", E2E + "::test_h2_copilot_sources_drafts_and_plan",
    "Each answer names its source: deterministic local logic, verified external model, recorded at build time; questions are labelled user-authored.",
    "Know where every answer came from.")

# ---------------------------------------------------------------- U Discovery Radar
row(201, "Unexamined evidence", "N", "S", SK + "radar.py;" + JS + "radarui.js", E2E + "::test_s5_radar",
    "Significant pairs not yet viewed in this session are listed (R1) and marked once examined.", "Do not miss evidence.")
row(202, "Unresolved hypotheses", "N", "S", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Explanations with open tests (R2) or no implemented test (R3).", "Know what remains to test.")
row(203, "Missing inputs", "N", "H", SK + "radar.py;" + SK + "discovery.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Each item states the data it needs and whether it can run now.", "Know what data to get.")
row(204, "Unused measurements", "N", "H", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Usable measurements without a matched partner (R4).", "Find measurements no comparison uses.", dup=None)
row(205, "Incomplete provenance", "N", "H", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Ledger relationship gaps become items (R9).", "Fix provenance gaps.")
row(206, "Sensitivity-driven opportunities", "N", "H", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "When sensitivity has not been examined, an item proposes it (R5).", "Test robustness when it matters.")
row(207, "Suggested follow-up tests", "N", "S", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Each item names the method to run and what it cannot establish.", "Know the next test and its limits.")
row(208, "Investigation prioritization", "N", "S", SK + "radar.py", ROS + "::test_radar_items_are_explained_and_ranked_by_the_stated_rule",
    "Fixed, stated order (R1, R6, R2, R5, R7, R4, R3, R9, R8) with runnable items first.", "Work on the most actionable items.",
    "The order is a stated convention, not a computed value of the opportunity.")
row(209, "Recommendation explanations", "N", "S", SK + "radar.py;" + JS + "radarui.js", E2E + "::test_s5_radar",
    "Each item gives what, why, evidence, data needed, method, cannot establish and can-run-now.", "Understand every suggestion.")
row(210, "Opportunity tracking", "N", "H", JS + "radarui.js;" + JS + "session.js", E2E + "::test_s5_radar",
    "Items whose pair was examined in the session are marked; running an item logs it.", "See progress through the radar.")

# ---------------------------------------------------------------- V Knowledge Graph
row(211, "Cross-investigation links", "N", "S", JS + "kg.js", E2E + "::test_p_vault_and_studio",
    "KG-1 links saved records and sessions by stored data only (rules K1–K5); empty state when fewer than two exist.",
    "See how investigations relate.", "Relationships come only from stored lists; none is inferred.")
row(212, "Shared method relationships", "N", "H", JS + "kg.js", E2E + "::test_p_vault_and_studio",
    "K4 links records analysed with the same analysis version.", "Find results comparable by method.")
row(213, "Related target records", "N", "H", JS + "kg.js", E2E + "::test_p_vault_and_studio", "K1 links records and sessions naming the same target.", "Gather work on one target.")
row(214, "Repeated data-quality issues", "N", "H", JS + "kg.js", E2E + "::test_p_vault_and_studio",
    "K5 links records with the same non-clean data-quality category and lists issues seen at least twice.", "Spot recurring problems.")
row(215, "Method dependency graph", "N", "H", JS + "ledgerui.js", E2E, "—", "—", dup="K107")
row(216, "Investigation clusters", "D", "R", "", "—", "Clustering similar investigations.", "Find groups of related work.")
row(217, "Graph provenance", "N", "F", JS + "kg.js", E2E + "::test_p_vault_and_studio", "Every edge names the rule that created it.", "Know why two items are linked.")
row(218, "Relationship confidence where justified", "X", "R", "", "—", "Confidence values on relationships.", "—",
    "Not justified: every KG-1 relationship is a stored fact, so no confidence is assigned.")
row(219, "Graph filtering", "D", "H", "", "—", "Filtering the knowledge graph.", "Read large graphs.", "The graph is small (saved records); not built.")
row(220, "Knowledge graph export", "N", "H", JS + "records.js;" + JS + "kg.js", E2E + "::test_p_vault_and_studio", "Downloads the graph as JSON.", "Analyse relationships elsewhere.")

# ---------------------------------------------------------------- W Automation
row(221, "Workflow templates", "N", "H", SK + "workflows.py", ROS + "::test_workflow_validation", "Three workflow templates over registered actions.", "Automate common sequences.")
row(222, "Batch analysis", "N", "H", JS + "experimentsui.js;" + JS + "executor.js", E2E + "::test_s8_experiments_and_workflows",
    "Runs a workflow over up to four targets with per-item records.", "Process several targets the same way.")
row(223, "Workflow validation", "N", "F", SK + "workflows.py;" + JS + "workflows.js", ROS + "::test_workflow_validation",
    "Schema skytrace.workflow/1, registered actions only, declared inputs, bounds; Python and browser agree.", "Invalid workflows never run.")
row(224, "Execution logs", "N", "H", JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows",
    "Each item and step records status, timing and error.", "Audit a batch.")
row(225, "Retry handling", "N", "H", JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows", "Failed items can be retried individually.", "Recover from transient failures.")
row(226, "Cancellation", "N", "F", JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows",
    "A running batch stops before its next step when cancelled; completed items are kept; retry then runs only the rest.", "Stop work safely.", "A step already running finishes.")
row(227, "Batch failure summaries", "N", "H", JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows", "Counts of completed, failed and cancelled items.", "See what went wrong at a glance.")
row(228, "Workflow versioning", "N", "F", SK + "workflows.py", ROS + "::test_workflow_validation", "Workflows declare their schema version; unknown versions are refused.", "Old workflows are never misread.")
row(229, "Workflow reproducibility", "N", "H", SK + "workflows.py", ROS + "::test_browser_planner_missions_workflows_match_python",
    "A workflow is a complete declarative JSON of actions and inputs that validates identically in Python and the browser.", "Re-run the same workflow later.")
row(230, "Workflow export", "N", "H", JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows", "Export and import workflow JSON with validation.", "Share workflows.")

# ---------------------------------------------------------------- X Mission System
row(231, "Guided research missions", "N", "H", SK + "missions.py;" + JS + "missions.js", ROS + "::test_missions_read_completion_from_the_session",
    "Six missions (verify integrity, compare a pair, examine a candidate, reproduce, test a hypothesis, produce a report); no points or badges.",
    "Learn a research workflow by doing it.")
row(232, "Mission templates", "N", "H", SK + "missions.py", ROS + "::test_missions_read_completion_from_the_session", "Missions are declarative templates of tasks with criteria.", "Consistent guidance.")
row(233, "Mission prerequisites", "N", "H", SK + "missions.py", ROS + "::test_missions_read_completion_from_the_session", "A mission states the data it needs before it starts.", "Start only missions that can finish.")
row(234, "Task dependencies", "D", "H", "", "—", "Tasks that cannot complete before earlier tasks.", "Follow a sound order.",
    "Not enforced: tasks are listed in a recommended order, but each task's completion is read from the session independently.")
row(235, "Mission progress", "N", "H", JS + "commandcenter.js;" + JS + "missions.js", E2E + "::test_s1_command_center_session_and_mission",
    "Progress is read from the session's recorded events, never self-reported.", "See real progress.")
row(236, "Mission completion criteria", "N", "F", SK + "missions.py", ROS + "::test_missions_read_completion_from_the_session",
    "Criteria are events, questions, runs, notebook content, tested hypotheses or a written review.", "Know exactly what completes a task.")
row(237, "Mission review", "N", "H", SK + "missions.py", ROS + "::test_missions_read_completion_from_the_session", "Review tasks need a written note.", "Reflection is part of the work.")
row(238, "Mission history", "N", "H", SK + "session.py", E2E + "::test_s1_command_center_session_and_mission", "Mission start, tasks and completion are session events.", "See past missions.")
row(239, "Mission export", "N", "H", JS + "sessionsui.js", E2E + "::test_s9_sessions_dialog_export_import", "Missions travel with the session export.", "Keep mission records.")
row(240, "Mission reproducibility", "D", "R", "", "—", "Re-running a mission on other data automatically.", "Repeat a guided study.")

# ---------------------------------------------------------------- Y Accessibility and Learning
row(241, "Guided learning paths", "D", "H", "", "—", "Sequenced lessons.", "Learn the science step by step.", "Missions (X231) guide tasks but are not lessons.")
row(242, "Scientific glossary", "E", "H", JS + "main.js;web/index.html", E2E + "::test_k_palette_help_shortcuts", "Glossary dialog of terms.", "Look up terms.")
row(243, "Contextual scientific explanations", "E", "H", JS + "discovery.js;" + JS + "lab.js", E2E + "::test_l_discovery_engine", "Explanations next to results (what z means, why pairs are rejected).", "Understand results in place.")
row(244, "Accessible graph navigation", "E", "F", JS + "graph.js", E2E + "::test_e_graph_controls", "Graph nodes are named, focusable and activated with Enter.", "Navigate the graph by keyboard.")
row(245, "Keyboard-only investigation", "E", "F", JS + "main.js", E2E + "::test_k_palette_help_shortcuts", "Command palette, Alt+number workspaces, Escape closes dialogs.", "Work without a mouse.")
row(246, "Screen-reader chart summaries", "E", "F", JS + "figurestudio.js;" + JS + "charts.js", E2E + "::test_y_accessible_names", "Charts carry text labels and captions.", "Charts usable with a screen reader.")
row(247, "High-contrast mode", "D", "H", "", "—", "A dedicated high-contrast theme.", "Better legibility.", "Text tokens meet WCAG AA (verified); no separate high-contrast theme.")
row(248, "Reduced-motion mode", "E", "F", "web/css/app.css", A11Y + "::test_reduced_motion_disables_animation", "prefers-reduced-motion disables animations and playback transitions.", "No motion for those who need it.")
row(249, "Beginner-to-research transitions", "N", "H", JS + "main.js", E2E + "::test_j_levels",
    "Levels change what is visible, never calculations; opening a deeper workspace raises the level with a notice.", "Grow into the tool.")
row(250, "Scientific terminology assistance", "E", "H", JS + "util.js", E2E + "::test_y_accessible_names", "Plain-language labels for categories and questions.", "Read results without jargon.")

# ---------------------------------------------------------------- Z Platform Reliability
row(251, "Startup diagnostics", "E", "F", SK + "server/app.py", API + "::test_status_and_security_headers", "Status endpoint reports versions, data and model availability.", "Know the app's state at once.")
row(252, "Dependency diagnostics", "E", "F", "scripts/diagnose_environment.py", ACQ, "Reports optional packages (astropy) and services.", "Know what is missing.")
row(253, "Memory usage monitoring", "D", "H", "", "—", "Tracking memory use.", "Avoid slowdowns.")
row(254, "Rendering performance", "E", "H", "scripts/measure_performance.py;docs/performance.json", "scripts/measure_performance.py", "Measured load and workspace render times.", "Know how fast the interface is.")
row(255, "Cache integrity", "N", "F", SK + "server/research.py", API + "::test_phase6_research_planner_sessions_experiments_connectors",
    "Research reports are cached by record content hash, so a changed record never reuses a stale report.", "Never read stale results.")
row(256, "Offline diagnostics", "E", "F", SK + "server/app.py", OFF + "::test_full_workflow_without_network", "OFFLINE=1 forbids network; the workflow is tested without network.", "Work offline knowingly.")
row(257, "Export integrity", "E", "F", SK + "package.py", DISC + "::test_package_is_deterministic_and_self_verifying", "Exports carry content hashes and SHA256SUMS.", "Verify exports.")
row(258, "Import validation", "E", "F", SK + "server/app.py;" + SK + "server/research.py", API + "::test_record_export_and_verified_import", "Imported records and sessions are validated and hash-checked; never overwrite existing ids.", "Bad imports are refused.")
row(259, "Error recovery", "N", "H", SK + "server/research.py;" + JS + "sessionsui.js", API + "::test_phase6_research_planner_sessions_experiments_connectors",
    "Unreadable session files are listed and kept, never deleted; failed steps keep their error.", "Problems never destroy work.")
row(260, "Release verification", "E", "F", "scripts/make_release.py;scripts/verify.py", "scripts/verify.py", "Gates run and recorded; release manifest with SHA-256; never overwrites a version.", "Trust a release.")

# ---------------------------------------------------------------- AA Security
row(261, "Import sandboxing", "E", "F", SK + "server/research.py", API + "::test_phase6_research_planner_sessions_experiments_connectors", "Imports are parsed as data only, size-limited and schema-checked; nothing in them executes.", "Imports cannot run code.")
row(262, "Path validation", "E", "F", SK + "server/app.py", API + "::test_rejects_traversal", "Identifiers are pattern-checked; traversal is refused.", "No file access outside data.")
row(263, "Input schema validation", "N", "F", SK + "schema.py;" + JS + "schema.js", RS + "::test_browser_matches_python", "SCHEMA-1 in Python and JS plus pydantic models for tool arguments.", "Inputs are checked identically everywhere.")
row(264, "Secret isolation", "E", "F", SK + "ai/meta_client.py", AI, "Model keys only from the environment; never in records, logs or the browser.", "Keys never leak.")
row(265, "API permission boundaries", "E", "F", SK + "ai/tools.py;" + SK + "server/research.py", TOOLS, "Copilot tools are read-only; the server overrides client claims about its own facts.", "The assistant cannot change data.")
row(266, "External response validation", "E", "F", SK + "fitsio.py;" + SK + "archive/acquire.py", FITS, "External data is validated before use.", "Malformed responses are refused.")
row(267, "Safe export generation", "E", "F", SK + "package.py;" + JS + "zipstore.js", NB + "::test_zipstore_output_is_valid_and_deterministic", "Exports are data files with fixed names; no scripts.", "Exports are safe to open.")
row(268, "Record integrity", "E", "F", SK + "provenance.py", STAT + "::test_js_content_hash_matches_python", "Records carry a content hash verified in Python and the browser.", "Detect altered records.")
row(269, "Audit history", "E", "H", SK + "ai/copilot.py;" + SK + "session.py", AI, "Copilot audit log of model calls; session history of actions.", "Reconstruct what happened.")
row(270, "Dependency review", "B", "F", "", "—", "Automated vulnerability audit of dependencies.", "Know dependencies are safe.",
    "Blocked: audit tools need PyPI/OSV access, which the proxy refuses here; dependencies are few and listed in pyproject.toml.")

# ---------------------------------------------------------------- AB Scientific Validation
row(271, "Golden fixtures", "E", "F", SK + "synthetic.py;fixtures/synthetic", OFF + "::test_expected_outcomes_on_synthetic_truth", "Deterministic synthetic fixtures with injected effects.", "Stable test inputs.")
row(272, "Cross-language parity", "E", "F", "tests/js", RS + "::test_browser_matches_python", "Browser ports are tested against Python on shared corpora (hash, pairs, intents, sessions, planner, missions, workflows).", "The browser computes what the server computes.")
row(273, "Boundary testing", "E", "F", SK + "canon.py;" + SK + "analysis.py", RS + "::test_js_number_rules", "Number limits (±2^53), parameter bounds and size limits are tested at their edges.", "Edges behave as stated.")
row(274, "Property-based tests", "D", "H", "", "—", "Generated-input tests.", "Find unexpected failures.", "No property-testing library is installed (PyPI blocked).")
row(275, "Regression tests", "E", "F", "tests", "scripts/verify.py", "Unit, API and browser suites run on every gate.", "Changes do not break working features.")
row(276, "Known-answer tests", "E", "F", SK + "synthetic.py", OFF, "—", "—", dup="H80")
row(277, "Numerical stability checks", "D", "R", "", "—", "Checks for ill-conditioned computations.", "Trust results near limits.")
row(278, "Uncertainty validation", "E", "F", SK + "uncertainty.py", DISC + "::test_uncertainty_recomputes_logged_values_exactly", "Components recompute the logged uncertainties exactly.", "Error budgets add up.")
row(279, "Provenance tests", "E", "F", SK + "provenance_check.py", PROV, "PROVCHECK-1 tests hashes, origins and determinism.", "Provenance claims hold.")
row(280, "Scientific method coverage", "N", "F", SK + "capabilities.py", ROS + "::test_registry_actions_and_capabilities_are_consistent", "Every capability names its tests; the consistency test checks they exist.", "Know which methods are tested.")

# ---------------------------------------------------------------- AC Advanced Exploration
row(281, "Multi-target investigation", "N", "H", SK + "workflows.py;" + JS + "experimentsui.js", E2E + "::test_s8_experiments_and_workflows", "Workflows run the same actions on up to four targets.", "Investigate several targets consistently.")
row(282, "Cross-observation comparison", "N", "H", SK + "compat.py", ROS, "—", "—", dup="C21")
row(283, "Spatial field comparison", "D", "R", "", "—", "Comparing fields around targets.", "Study the environment.")
row(284, "Target metadata comparison", "D", "H", "", "—", "Targets' metadata side by side.", "Compare targets.")
row(285, "Multi-investigation analysis", "E", "H", JS + "records.js", E2E + "::test_p_vault_and_studio", "Compare two saved records in the Vault.", "See how results differ between runs.")
row(286, "Observation relationship mapping", "N", "H", SK + "compat.py", ROS, "—", "—", dup="C21")
row(287, "Research question templates", "N", "H", SK + "planner.py", ROS + "::test_planner_known_plans", "PLAN-1 templates (change, brightness, motion, quality, provenance, reproducibility, sensitivity, uncertainty, explanations, coverage, report) with example questions.", "Start from a well-formed question.")
row(288, "Discovery workflow templates", "N", "H", SK + "workflows.py", ROS, "—", "—", dup="W221")
row(289, "Cross-session evidence review", "D", "R", "", "—", "Reviewing evidence across sessions.", "Combine lines of work.")
row(290, "Multi-target reports", "D", "H", "", "—", "One report over several targets.", "Summarise a campaign.")

# ---------------------------------------------------------------- AD Research Frontier
row(291, "Adaptive test selection", "N", "R", SK + "planner.py", ROS + "::test_planner_known_plans", "The plan adapts to the facts: it reuses a loaded run, skips actions this mode cannot run and marks blocked steps.", "Plans fit what is possible now.", "Adaptation is rule-based, not learned.")
row(292, "Evidence-gap optimization", "D", "R", "", "—", "Choosing observations that best close evidence gaps.", "Spend effort where it matters most.")
row(293, "Reproducible research plans", "N", "R", SK + "planner.py", ROS, "—", "—", dup="B20")
row(294, "Research dependency analysis", "N", "R", SK + "planner.py", ROS, "—", "—", dup="B13")
row(295, "Investigation completeness diagnostics", "D", "R", "", "—", "One diagnostic of how complete an investigation is.", "Know when to stop.", "Ledger completeness (K105) covers provenance only.")
row(296, "Explainable recommendation ranking", "N", "R", SK + "radar.py", ROS, "—", "—", dup="U208")
row(297, "Evidence conflict prioritization", "D", "R", "", "—", "Ranking contradictions by impact.", "Resolve the important conflicts first.")
row(298, "Research readiness reports", "D", "R", "", "—", "A report of what is ready to run and what is missing.", "Plan the next session.")
row(299, "Automated reproducibility audits", "E", "R", SK + "provenance_check.py;scripts/verify_provenance.py", PROV, "PROVCHECK-1 runs automatically and reports per check.", "Reproducibility is audited, not assumed.")
row(300, "Next-investigation recommendations", "E", "R", SK + "discovery.py", DISC + "::test_next_steps_say_when_services_are_unavailable", "DISC-1 next steps, each saying whether it can run here.", "Know what to investigate next.")

# ---------------------------------------------------------------- concepts this project added (counted; not in the brief)
EXTRA = [
 ("X01", "Observatory Command Center", "N", "S", JS + "commandcenter.js", E2E + "::test_s1_command_center_session_and_mission", "Real values only: data state, session, outcomes, quality, radar and missions; empty states explain themselves.", "One honest overview."),
 ("X02", "Canonical JSON (SKY-CANON-1)", "N", "F", SK + "canon.py;" + JS + "canon.js", RS + "::test_canon_refusals_and_order", "One text form for hashing in Python and JS; refuses values that cannot round-trip.", "Hashes agree everywhere."),
 ("X03", "Shared schema interpreter (SCHEMA-1)", "N", "F", SK + "schema.py;" + JS + "schema.js", RS + "::test_browser_matches_python", "One declarative schema checked identically in both languages.", "Validation never diverges."),
 ("X04", "Migration of 0.5 saved records into sessions", "N", "F", SK + "session.py", RS + "::test_migration_from_v05_saved_record", "Old records become sessions; the originals are kept.", "No earlier work is lost."),
 ("X05", "Shared action executor", "N", "F", JS + "executor.js", E2E + "::test_s2_planner_plans_runs_and_persists", "Planner, workflows, radar and missions execute registered actions through one path.", "Every route behaves the same."),
 ("X06", "Interface levels change visibility only", "E", "H", JS + "main.js", E2E + "::test_j_levels", "Levels hide or show controls; calculations are identical at every level.", "Simpler views never change results."),
 ("X07", "Synthetic data always identifiable", "E", "F", SK + "synthetic.py;" + SK + "ai/local.py", APP + "::test_02_synthetic_is_unmistakable", "SYN-* names, origin ‘synthetic’, banners and answer prefixes.", "Never mistake test data for observations."),
 ("X08", "Connector request preview", "N", "H", SK + "connectors.py", ROS + "::test_connector_previews_match_acquisition_and_send_nothing", "The real request builder captures the request without sending it.", "See exactly what would be sent."),
 ("X09", "Bounded Retry-After back-off", "N", "F", SK + "archive/net.py", ROS + "::test_retry_after_is_honoured_and_bounded", "Server-requested waits honoured up to 60 s.", "Polite, bounded retries."),
 ("X10", "Static preview with explicit limits", "E", "H", "scripts/build_static.py;" + JS + "static/backend.js", STAT, "Recorded results served without a server; unavailable actions refuse with a reason.", "A usable preview that never imitates."),
 ("X11", "Deterministic session package ZIP", "N", "F", JS + "zipstore.js", NB + "::test_zipstore_output_is_valid_and_deterministic", "Stored ZIP with CRC-32 and fixed timestamps; same input, same bytes.", "Packages can be compared by hash."),
 ("X12", "Concurrent render guard", "N", "F", JS + "util.js", E2E + "::test_z_no_external_requests_no_errors", "Render tokens discard stale asynchronous renders.", "No duplicated panels."),
 ("X13", "Experiment validity note", "N", "F", SK + "experiments.py", ROS + "::test_experiment_validation_and_negative_control", "Every experiment states that execution does not make it scientifically valid.", "Results are read with care."),
 ("X14", "Needs-review plan steps", "N", "H", JS + "plannerui.js", E2E + "::test_s2_planner_plans_runs_and_persists", "Inspection steps are excluded from batch runs and wait for a human note.", "Human judgement is never automated away."),
 ("X15", "Workflow resource bounds", "N", "F", SK + "workflows.py", ROS + "::test_workflow_validation", "At most 4 targets, 10 steps and 24 executions.", "Automation cannot run away."),
 ("X16", "Sequence frame difference view", "N", "H", JS + "timemachine.js", E2E + "::test_s3_quality_matrix_metadata_sequences", "Difference of consecutive recorded frames in a sequence.", "See change between frames."),
 ("X17", "Evidence guard on assistant answers (GUARD-3)", "E", "F", SK + "ai/guard.py", AI, "Model answers whose numbers are not in tool outputs are withheld.", "No invented numbers."),
 ("X18", "BLOCKED reporting for live tests", "E", "F", "scripts/diagnose_environment.py;tests/live", ACQ, "Live tests report BLOCKED with the refused service, never pass.", "Blocked work is never shown as done."),
 ("X19", "Absence outcomes handled in the ledger", "N", "F", SK + "ledger.py", ROS + "::test_ledger_counts_support_and_flags_conflicts", "‘No motion at sensitivity’ claims are not flagged as lacking support.", "Absence is reported correctly."),
 ("X20", "Data citations registry", "N", "H", SK + "server/research.py", API + "::test_phase6_research_planner_sessions_experiments_connectors", "SPHEREx QR3/QR2 and Gaia DR3 DOIs and SIMBAD for citation blocks.", "Cite the data correctly."),
 ("X21", "Static recorded-question disclosure", "N", "F", JS + "copilot.js;scripts/build_static.py", E2E + "::test_h2_copilot_sources_drafts_and_plan", "In the preview, an answer recorded for a different wording says which question was recorded.", "Never mistake a recorded answer for a live one."),
 ("X22", "Session package README", "N", "H", JS + "notebook.js", E2E + "::test_s7_notebook_blocks_versions_undo_exports", "Explains each file and how to recompute the session hash.", "Recipients can verify the package."),
 ("X23", "Copilot data-quality and ledger tools", "N", "S", SK + "ai/tools.py", CP2 + "::test_quality_tool_has_no_score", "get_data_quality, get_evidence_ledger and get_hypothesis_tests as read-only tools.", "Ask about quality and evidence directly."),
 ("X24", "Planner unanswerable map", "N", "F", SK + "planner.py", ROS + "::test_planner_known_plans", "Questions no registered action can answer get a stated reason instead of a plan.", "Honest refusals."),
]


def build() -> dict:
    items = []
    letters = [d.split()[0] for d in DOMAINS]
    for n, name, st, grp, ev, ver, expl, outcome, limit, deps, dup in R:
        dom = DOMAINS[(n - 1) // 10]
        items.append({"id": f"{letters[(n - 1) // 10]}{n}", "number": n, "domain": dom, "concept": name, "status": STATUS[st], "status_code": st,
                      "group": GROUP[grp], "priority": "—" if st == "X" else PRIORITY[grp], "explanation": expl, "user_outcome": outcome,
                      "dependencies": deps, "evidence": [p for p in ev.split(";") if p], "verification": ver,
                      "limitations": limit or DEFAULT_LIMIT.get(st, ""), "duplicate_of": dup, "source": "brief"})
    for xid, name, st, grp, ev, ver, expl, outcome in EXTRA:
        items.append({"id": f"P6-{xid}", "number": None, "domain": "Added by this project", "concept": name, "status": STATUS[st], "status_code": st,
                      "group": GROUP[grp], "priority": PRIORITY[grp], "explanation": expl, "user_outcome": outcome, "dependencies": "",
                      "evidence": [p for p in ev.split(";") if p], "verification": ver, "limitations": "", "duplicate_of": None, "source": "project"})
    distinct = [x for x in items if not x["duplicate_of"]]
    counts = {"rows": len(items), "brief_concepts": len(R), "merged_synonyms": len(items) - len(distinct), "added": len(EXTRA),
              "distinct": len(distinct), "domains": len(DOMAINS),
              "by_status": {STATUS[k]: sum(x["status_code"] == k for x in distinct) for k in STATUS},
              "by_group": {g: sum(x["group"] == g for x in distinct) for g in GROUP.values()},
              "implemented": sum(x["status_code"] in "EN" for x in distinct)}
    return {"schema": "skytrace.phase6_catalogue/1", "statuses": STATUS, "groups": GROUP, "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    out = ["# Skytrace Phase 6 capability catalogue", "",
           "Generated by `python scripts/phase6_catalogue.py`; every count is computed from the rows in that script. Checked by "
           "`tests/unit/test_phase6_catalogue.py`: well formed, every cited file and test function exists, every concept marked existing or "
           "new cites evidence and a verification, and synonyms are merged rather than counted.", "",
           "The 300 concepts and 30 domains are those of the Phase 6 brief (§19), named as the brief names them. Where two brief concepts "
           "name the same capability, the second is recorded with *duplicate of* and not counted; concepts this project added are listed "
           "at the end and counted. The Phase 5 catalogue (`docs/FEATURE_CATALOGUE.md`) is kept unchanged.", "",
           f"**{c['distinct']} distinct concepts** ({c['brief_concepts']} from the brief − {c['merged_synonyms']} merged synonyms + {c['added']} added), "
           f"in {c['domains']} domains. Status: " + ", ".join(f"{v} {k}" for k, v in c["by_status"].items()) +
           ". Groups: " + ", ".join(f"{v} {k}" for k, v in c["by_group"].items()) + ".", "",
           "Status: **existing** built in 0.5 or earlier · **new in 0.6** built in this release · **deferred** not built, nothing claims it · "
           "**blocked** needs a service this environment refuses · **out of scope** not applicable or not advisable. Groups follow §20: "
           "Foundation (P1), High Impact and Signature (P2), Frontier (P3). A priority is a planning signal; the status says what is built.", "",
           "| Domain | Distinct | Existing | New in 0.6 | Deferred | Blocked | Out of scope | Merged |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    doms = DOMAINS + ["Added by this project"]
    for d in doms:
        xs = [x for x in cat["items"] if x["domain"] == d]
        ds = [x for x in xs if not x["duplicate_of"]]
        n = Counter(x["status_code"] for x in ds)
        out.append(f"| {d} | {len(ds)} | {n['E']} | {n['N']} | {n['D']} | {n['B']} | {n['X']} | {len(xs) - len(ds)} |")
    out.append("")
    for d in doms:
        out += [f"## {d}", "", "| ID | Concept | Status | Group | Explanation | User outcome | Limitations | Depends on | Evidence | Verified by |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for x in (x for x in cat["items"] if x["domain"] == d):
            if x["duplicate_of"]:
                out.append(f"| {x['id']} | {x['concept']} | duplicate of {x['duplicate_of']} | — | Same capability as {x['duplicate_of']}; not counted. | — | — | — | — | — |")
                continue
            ev = ", ".join(f"`{p}`" for p in x["evidence"]) or "—"
            ver = x["verification"] if x["verification"] == "—" else f"`{x['verification']}`"
            out.append(f"| {x['id']} | {x['concept']} | {x['status']} | {x['group']} ({x['priority']}) | {x['explanation']} | {x['user_outcome']} | "
                       f"{x['limitations'] or '—'} | {x['dependencies'] or '—'} | {ev} | {ver} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "phase6_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "PHASE6_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
