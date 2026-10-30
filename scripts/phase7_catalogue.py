"""Phase 7 capability catalogue: the 400 concepts of the Phase 7 brief (§20, 40 domains), deduplicated against each
other and against the Phase 6 catalogue, plus concepts this project added, each with status, group, evidence and the
test that verifies it.

    python scripts/phase7_catalogue.py      # writes docs/phase7_catalogue.json and docs/PHASE7_CATALOGUE.md

Status   E existing (built in 0.6.1 or earlier; `p6` names the Phase 6 catalogue entry where one exists) · N new in 0.7 ·
         D deferred (not built; nothing claims it) · B blocked (needs a service this environment refuses) ·
         X out of scope.
Group    F Foundation · H High Impact · S Signature · R Frontier.
Merged   a concept naming the same capability as another (in this catalogue) is recorded with `duplicate_of` and not
         counted; distinct concepts this project added (P7-X..) keep the count at or above 400.
Each row: number | status | group | evidence (";"-separated; `py:x` = src/skytrace/x.py, `js:x` = web/js/x.js) |
         verification (`F:` test_frontier, `C:` e2e test_controls, `A:` test_api, `R:` test_research_os, `S:` test_research_session,
         `D:` test_discovery, `O:` test_offline_workflow, `P:` test_static_preview, `N:` test_notebook_package, `X:` test_accessibility,
         `T:` test_tool_contracts, `Q:` test_provenance_check (file), `W:` test_wavelength_flags (file), `Z:` test_fits_wcs (file),
         `K:` test_acquire (file), or a path) | explanation | limitation (optional) | p6 / duplicate_of (optional)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = {"E": "existing", "N": "new in 0.7", "D": "deferred", "B": "blocked", "X": "out of scope"}
GROUP = {"F": "Foundation", "H": "High Impact", "S": "Signature", "R": "Frontier"}
PRIORITY = {"F": "P1", "H": "P2", "S": "P2", "R": "P3"}
TESTS = {"F": "tests/unit/test_frontier.py", "C": "tests/e2e/test_controls.py", "A": "tests/integration/test_api.py",
         "R": "tests/unit/test_research_os.py", "S": "tests/unit/test_research_session.py", "D": "tests/unit/test_discovery.py",
         "O": "tests/unit/test_offline_workflow.py", "P": "tests/unit/test_static_preview.py", "N": "tests/unit/test_notebook_package.py",
         "X": "tests/unit/test_accessibility.py", "T": "tests/unit/test_tool_contracts.py", "Q": "tests/unit/test_provenance_check.py",
         "W": "tests/unit/test_wavelength_flags.py", "Z": "tests/unit/test_fits_wcs.py", "K": "tests/unit/test_acquire.py"}

DOMAINS = ["Counterfactual Research", "Astronomical Digital Twins", "Discovery Horizon", "Adversarial Science", "Synthetic Observatory",
           "Observation Design", "Information Analysis", "Causal Reasoning", "Research Autopilot", "Cosmic Atlas", "Knowledge Atlas",
           "Review Room", "Discovery Story", "Reproducibility", "Multi-Agent Research", "Investigation Branching", "Advanced Experimentation",
           "Observation Compatibility", "Signal Recovery", "Temporal Intelligence", "Data Acquisition", "Advanced Image Analysis",
           "Statistical Diagnostics", "Research Notebook", "Research Missions", "Evidence Intelligence", "Research Collaboration",
           "Scientific Reporting", "Learning and Accessibility", "Reliability", "Scientific Security", "Scientific Validation",
           "Multi-Target Investigation", "Scientific Opportunity Optimization", "Method Intelligence", "Visual Intelligence",
           "Research Automation", "Scientific Interpretation", "Advanced Research Planning", "The Scientific Frontier"]

NAMES = """Scenario branching|Baseline cloning|Parameter perturbation|Input exclusion|Measurement perturbation|Threshold variation|Method substitution|Scenario comparison|Scenario lineage|Counterfactual export
Observation twins|Target twins|Analysis twins|Scenario twins|Investigation twins|Twin versioning|Twin comparison|Twin provenance|Twin restoration|Twin integrity
Research opportunity discovery|Unexplored evidence detection|Unresolved question mapping|Missing-input mapping|Investigation readiness|Opportunity ranking|Opportunity explanation|Dependency visualization|Opportunity tracking|Opportunity export
Hypothesis challenge|Method challenge|Evidence challenge|Reproducibility challenge|Alternative explanation review|Confounder inspection|Assumption challenge|Contradiction discovery|Blind-spot analysis|Scientific challenge reports
Scenario generation|Reproducible random seeds|Ground-truth records|Signal injection|Noise injection|Background variation|Motion simulation|Missing-epoch simulation|Calibration perturbation|Synthetic validation reports
Research-driven observation requirements|Hypothetical cadence planning|Temporal sampling experiments|Coverage optimization|Observation-gap analysis|Synthetic observation schedules|Signal recovery experiments|Instrument requirement records|Observation strategy comparison|Planning brief export
Hypothesis discrimination|Candidate measurement comparison|Information-gain assumptions|Sensitivity-based planning|Evidence-gap prioritization|Decision-tree analysis|Expected measurement comparison|Information analysis reports|Test-selection explanations|Research-action ranking
Relationship diagrams|Confounder registry|Assumption-based causal models|Temporal-order checks|Alternative causal structures|Dependency inspection|Causal claim warnings|Evidence requirements|Model comparison|Causal reasoning reports
Research objective parsing|Workflow generation|Capability validation|Prerequisite checking|User approval|Execution orchestration|Task dependency management|Cancellation|Recovery|Execution audit
Target map|Sky-coordinate navigation|Observation-footprint maps|Spatial filtering|Coordinate transformations|Angular separation|Physical-distance metadata|Multi-target comparison|Spatial coverage|Atlas export
Research topic maps|Method relationships|Related investigations|Target relationships|Knowledge collections|Structured search|Semantic indexing when supported|Research path saving|Knowledge versioning|Knowledge export
Methods review|Evidence review|Data review|Reproducibility review|Interpretation review|Missing-assumption detection|Unsupported-claim detection|Limitation review|Review history|Review report
Investigation narrative|Evidence-linked chapters|Interactive research timelines|Figure sequences|Hypothesis histories|Method explanations|Results summaries|Limitations narratives|Presentation exports|Story reproducibility
Input verification|Environment records|Dependency fingerprints|Method fingerprints|Replay validation|Numerical tolerance checks|Figure provenance|Package verification|Reproducibility scoring with explicit rules|Audit exports
Agent capability registry|Role-specific permissions|Structured agent outputs|Evidence validation|Tool authorization|Agent execution logs|Agent result comparison|Conflicting-agent analysis|Human approval|Provider-independent orchestration
Branch creation|Branch comparison|Branch merging for user-authored metadata|Scenario isolation|Baseline preservation|Branch history|Branch provenance|Conflict detection|Branch export|Branch recovery
Experiment templates|Controlled experiments|Sensitivity experiments|Negative controls|Known-answer controls|Repeatability tests|Method comparisons|Experiment dependency graphs|Experiment diagnostics|Experiment packages
Instrument compatibility|Channel compatibility|Epoch compatibility|Unit compatibility|Metadata compatibility|Processing compatibility|Comparison restrictions|Compatibility explanations|Compatibility matrix|Compatibility export
Injection-recovery experiments|Detection threshold exploration|Recovery diagnostics|False-positive control tests|Signal-strength scenarios|Noise-level scenarios|Completeness measurements where justified|Recovery limitations|Ground-truth comparison|Recovery reports
Multi-epoch alignment|Time-gap inspection|Temporal coverage|Sampling cadence|Measurement sequences|Temporal residuals|Sequence compatibility|Frame provenance|Animation export|Temporal report
Archive query templates|Connector validation|Download manifests|Cache provenance|Dataset fingerprints|Transfer diagnostics|Retry history|Archive response inspection|Data-release metadata|Acquisition audit
Region selection|Pixel inspection|Region statistics|Profile analysis|Mask inspection|Background estimation diagnostics|Image registration review|Residual maps|Image comparison exports|Processing provenance
Model residuals|Fit diagnostics|Parameter sensitivity|Numerical stability|Boundary analysis|Distribution checks|Outlier inspection|Uncertainty propagation|Model limitation registry|Diagnostic exports
Structured research blocks|Observation references|Hypothesis references|Experiment references|Evidence links|Figure insertion|Annotation history|Notebook search|Notebook comparison|Notebook export
Mission templates|Research objectives|Prerequisite checks|Task dependencies|Completion criteria|Mission history|Mission review|Reproducible missions|Mission branching|Mission exports
Claim lineage|Evidence contradictions|Orphaned evidence|Evidence dependencies|Provenance gaps|Source verification|Claim status|Evidence comparison|Evidence audit|Evidence package
Read-only sharing|Review assignments|Evidence comments|Review annotations|Investigation authorship|Version conflicts|Review history (collaboration)|Exportable review packages|Collaboration permissions|Shared-session architecture
Research reports|Methods reports|Observation reports|Hypothesis reports|Experiment reports|Reproducibility reports|Data-quality reports|Scientific figure collections|Publication-oriented layouts|Machine-readable packages
Scientific tutorials|Interactive concept explanations|Guided investigations|Method walkthroughs|Contextual glossary|Keyboard-first workflows|Accessible graph navigation|Screen-reader summaries|Reduced-motion interface|Beginner-to-research pathways
Session recovery|Cache validation|Dependency inspection (environment)|Startup diagnostics|Execution recovery|Memory-aware rendering|Large-dataset handling|Offline diagnostics|Export integrity|Release verification
Import sandboxing|File-path validation|Schema validation|Secret isolation|Tool permission boundaries|External response validation|Workflow import safety|Record integrity|Audit history|Security regression tests
Golden datasets|Ground-truth fixtures|Cross-language parity|Known-answer tests|Numerical boundary tests|Property-based validation|Uncertainty tests|Method compatibility tests|Replay tests|Scientific regression reports
Multi-target sessions|Target comparison|Observation grouping|Cross-target metadata inspection|Multi-target evidence graphs|Shared method comparisons|Target-specific limitations|Batch investigation|Multi-target reporting|Cross-target reproducibility
Unexplored measurement detection|Research prerequisite mapping|Test-selection explanation|Evidence-gap ranking|Investigation feasibility|Opportunity dependencies|Research bottleneck detection|Alternative test paths|Opportunity history|Research optimization reports
Method discovery|Method documentation|Method compatibility|Method assumptions|Method version history|Method comparison|Method execution diagnostics|Method validation coverage|Method retirement warnings|Method reproducibility
Synchronized visualization panels|Cross-panel selection|Measurement overlays|Evidence-linked chart elements|Scenario comparison views|Interactive graph filtering|Coordinate inspection|Figure annotations|Export presets|Visualization provenance
Saved workflows|Parameter presets|Batch experiments|Execution queues|Cancellation (automation)|Failure recovery|Per-task diagnostics|Workflow versioning|Workflow import validation|Workflow reproducibility
Observation-versus-inference labels|Hypothesis comparison|Unsupported-claim warnings|Assumption registry|Alternative explanations|Evidence sufficiency checks|Limitation summaries|Contradiction review|Interpretation history|Scientific conclusion exports
Research question templates|Question dependency graphs|Test feasibility|Observation requirements|Missing-data planning|Research milestone tracking|Research plan comparison|Plan revision history|Plan reproducibility|Research plan export
Counterfactual scenario explorer|Astronomical investigation twins|Adaptive research planning|Adversarial hypothesis review|Synthetic observatory|Observation design experimentation|Information-guided testing|Research autopilot|Scientific knowledge atlas|Reproducible discovery orchestration"""

# number|status|group|evidence|verification|explanation|limitation|p6-or-dup
ROWS = """
1|N|S|py:counterfactual;js:counterfactualui|F:test_counterfactuals_are_isolated_and_labelled|One stated change against a named baseline; the original is never modified.||
2|N|F|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|The baseline is recomputed from its parameters and its content hash checked; a mismatched stated baseline is refused.||
3|N|S|py:counterfactual|C:test_t2_counterfactual_lab|Analysis parameters within the server's bounds, pipeline re-run.||
4|N|S|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Observations excluded by key, detector or time window in a copy of the bundle index; re-run.|The bundle on disk is untouched; exclusion is recorded as a selection rejection.|
5|N|S|py:counterfactual|C:test_t2_counterfactual_lab|Photometric uncertainties multiplied by k (simulated), recorded pairs re-assessed.|Photometry only; motion unchanged by construction.|
6|N|S|py:counterfactual;py:science/assess|F:test_reassessment_without_change_reproduces_the_record|ASSESS-2 thresholds overridden within bounds; recorded inputs re-assessed; unchanged thresholds reproduce the record exactly.||
7|N|S|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Brightness decided with PAIRDIFF-1 alone (hypothetical method).|Only this substitution is offered.|
8|N|S|js:counterfactualui|C:test_t2_counterfactual_lab|Side-by-side table of every compared output with changed rows marked and the change that caused them.||
9|N|H|js:counterfactualui|C:test_t2_counterfactual_lab|Every scenario kept in the session with its baseline hash and scenario hash.||
10|N|H|js:counterfactualui|C:test_t2_counterfactual_lab|The full comparison exports as JSON.||
11|N|H|py:twin|F:test_twins_integrity_and_comparison|Hashed record of one observation: file, checksum, metadata, measurements, processing steps.|Built by the module; not yet shown in the interface.|
12|N|H|py:twin|F:test_twins_integrity_and_comparison|Hashed record of a target and its outcomes.||
13|N|H|py:twin;js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Hashed record of an analysis: inputs, parameters, methods, measurements, outputs, assumptions.||
14|N|H|py:twin;py:server/frontier|A:test_phase7_frontier_counterfactual_reproduce_synthetic|Hashed record of a counterfactual scenario derived from its baseline.||
15|N|H|js:frontiercore|F:test_browser_twin_and_coordinates_match_python|Hashed record of a research session, built in the browser (parity with Python).||
16|D|H|||A history of successive twins of one thing.|Every twin is version 1; no twin history is kept.|
17|N|S|py:twin;js:frontiercore|F:test_browser_overlays_match_python|Deterministic structural diff per section; different kinds are refused.||
18|N|F|py:twin|F:test_twins_integrity_and_comparison|Each twin lists the hashes it was derived from.||
19|D|R|||Restoring an application state from a twin.|Not built.|
20|N|F|py:twin;js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Content hash recomputed in Python and the browser; tampering is detected.||
21|N|S|py:possibility;js:horizonui|F:test_possibility_layers_and_horizon_cards|Research opportunities from ten rules over the recorded state, never findings.||
22|N|S|py:possibility|F:test_browser_overlays_match_python|Unexamined significant pairs and unopened compatible sequences, filtered by the session.||
23|N|H|py:possibility|F:test_possibility_layers_and_horizon_cards|Question space layer: answerable, limited, not answerable, and why.||
24|N|H|py:possibility|F:test_possibility_layers_and_horizon_cards|Design layer: required and missing inputs per question with PLAN-1 actions.||
25|N|H|py:possibility|C:test_t1_discovery_horizon|Each opportunity has a feasibility class (can run now / needs the server / new data / a new method).||
26|N|S|py:possibility;js:frontiercore|F:test_browser_overlays_match_python|Stated order: feasibility, then category C1–C10.|A convention, not a value.|
27|N|H|py:possibility|C:test_t1_discovery_horizon|Every card states why it is ranked where it is.||
28|N|H|js:horizonui|C:test_t1_discovery_horizon|Map of evidence → question → method → required evidence built only from the cards.||
29|N|H|js:horizonui|C:test_t1_discovery_horizon|Opportunities noted in the session and marked as tracked.||
30|N|H|js:horizonui|C:test_t1_discovery_horizon|Opportunities export as JSON.||
31|N|S|py:adversarial|F:test_adversarial_rules_and_statuses|Competing explanations not ruled out for a positive claim, with the tests that could contradict it.||
32|N|S|py:adversarial|F:test_adversarial_rules_and_statuses|Method assumptions checked: error scale, calibration references, epoch fit, parallax.||
33|N|S|py:adversarial|F:test_adversarial_rules_and_statuses|Ledger flags and contradictions raised as challenges.||
34|N|H|py:adversarial;py:repro|F:test_reproducibility_verdicts_and_tamper|Replay status as a challenge, resolved only by a matching re-execution.||
35|N|H|py:adversarial|F:test_adversarial_rules_and_statuses|Explicitly labelled alternative interpretations for review.||
36|N|H|py:adversarial;js:adversarialui|C:test_t3_adversarial_lab|Selection exclusions and assumption-based alternatives shown as possible confounders.|No confounder is estimated.|
37|N|S|||Assumption challenge.||dup:32
38|E|F|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Contradictions by fixed rules C1–C4.||p6:K103
39|N|H|py:adversarial|F:test_adversarial_rules_and_statuses|Blind spots: unexamined pairs, no stability run, unquantified effects, selection.||
40|N|H|js:adversarialui|C:test_t3_adversarial_lab|Challenge report exported as JSON, with notes.||
41|N|S|py:synthobs;js:synthobsui|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Bounded scenarios generated as labelled SYNTHETIC bundles under data/synthlab.||
42|N|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Same scenario and seed → identical bytes and record hash (fixed generation stamp).||
43|N|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Generator inputs kept as ground truth with each result.||
44|N|H|py:synthobs|C:test_t4_synthetic_observatory_and_design|Brightness factors per pass inject a signal.||
45|N|H|py:synthobs|F:test_synthetic_validation_and_design_refusals|Noise level is a bounded parameter.||
46|N|H|py:synthobs|F:test_synthetic_validation_and_design_refusals|Background level is a bounded parameter.|Constant within a scenario.|
47|N|H|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Proper motion is a bounded parameter.||
48|N|H|py:synthobs|F:test_observation_design_compares_schedules|Passes can be omitted or spaced at will.||
49|N|H|py:synthobs|F:test_synthetic_validation_and_design_refusals|Per-pass gain and reference-star offsets perturb calibration and registration.||
50|N|H|js:synthobsui|C:test_t4_synthetic_observatory_and_design|Truth, expected (stated rule), output, error, verdict and failure behaviour, exportable.|Agreement on generated data does not validate real-data performance.|
51|N|R|py:synthobs|C:test_t4_synthetic_observatory_and_design|The planning brief states what the comparison can and cannot inform.|Derived from generated data only.|
52|N|R|py:synthobs|F:test_observation_design_compares_schedules|Hypothetical schedules defined as passes (day, detector position).|Not a telescope schedule.|
53|N|R|py:synthobs|F:test_observation_design_compares_schedules|Each schedule generated with the same truth and analysed by the pipeline.||
54|D|R|||Optimising a schedule for a goal.|Not built.|
55|E|H|py:compat|C:test_s3_quality_matrix_metadata_sequences|Coverage gaps per detector.||p6:D35
56|N|R|py:synthobs|F:test_observation_design_compares_schedules|Synthetic data generated on a hypothetical schedule.||
57|N|R|py:synthobs|F:test_observation_design_compares_schedules|Recovered motion sensitivity and verdicts per schedule.||
58|D|R|||Instrument requirements recorded per question.|Not built; instrument performance is not invented.|
59|N|R|||Observation strategy comparison.||dup:53
60|N|R|py:synthobs|C:test_t4_synthetic_observatory_and_design|Markdown brief labelled hypothetical and synthetic.||
61|N|S|py:infogain|F:test_information_analysis_has_no_probabilities|Which open test bears on which viable explanations.||
62|N|S|||Candidate measurement comparison.||dup:70
63|N|F|py:infogain;js:adversarialui|C:test_t3_adversarial_lab|Assumptions, absent probability model and interpretation limits shown.||
64|N|H|py:possibility|F:test_possibility_layers_and_horizon_cards|An opportunity proposes sensitivity checks when none was run (C5).||
65|N|H|||Evidence-gap prioritization.||dup:26
66|D|R|||Decision-tree analysis of test outcomes.|Needs outcome probabilities, which do not exist.|
67|X|R|||Expected measurement comparison.|Not advisable: without a probability model there is no defensible expected value.|
68|D|H|||An exportable information-analysis report.|The ranking is shown, not exported.|
69|N|H|py:infogain|F:test_information_analysis_has_no_probabilities|Each candidate states why it ranks where it does.||
70|N|S|py:infogain|F:test_information_analysis_has_no_probabilities|Candidates ranked by feasibility and the viable explanations they bear on; no numerical gain.||
71|N|H|js:adversarialui|C:test_t3_adversarial_lab|Relationships listed with their kind (model-derived, assumption-based, user-proposed).|Lists, not drawn diagrams.|
72|N|H|js:adversarialui|C:test_t3_adversarial_lab|Competing explanations act as the registry of possible confounders.||
73|N|H|js:adversarialui|C:test_t3_adversarial_lab|Each alternative causal structure labelled assumption-based with its test status.||
74|D|R|||Checking that a proposed cause precedes its effect.|Not built.|
75|N|H|||Alternative causal structures.||dup:73
76|N|H|js:adversarialui|C:test_t3_adversarial_lab|The pipeline's data-flow dependencies, labelled not causal.||
77|N|F|py:review;js:adversarialui|F:test_review_findings_cite_sources|Causal or discovery words in your notes are flagged.||
78|E|F|py:hypotheses|D:test_hypotheses_never_produce_probabilities_and_use_known_statuses|Each test states what evidence would decide it.||p6:I83
79|D|R|||Comparing causal models.|Not built.|
80|D|R|||Causal reasoning reports.|Not built.|
81|N|S|py:planner;js:autopilotui|C:test_t5_research_autopilot|Objectives matched by PLAN-1 rules (new challenge and counterfactual intents).||
82|N|S|py:planner|R:test_planner_known_plans|A workflow of registered actions from the matching template.||
83|N|F|py:capabilities;js:autopilotui|F:test_registry_permissions_cover_every_action|Only registered actions with a permission class can be scheduled.||
84|E|F|py:planner|R:test_planner_known_plans|Unmet preconditions block a step with its reason.||p6:B14
85|N|F|js:autopilotui|C:test_t5_research_autopilot|Nothing runs until you tick the authorization for the listed steps.||
86|N|S|js:autopilotui;js:executor|C:test_t5_research_autopilot|Authorized steps run one by one through the shared executor; failures stop the run.||
87|E|H|py:planner|S:test_session_rules|Steps declare dependencies that must precede them.||p6:B13
88|N|H|js:autopilotui|C:test_t5_research_autopilot|Cancel after the current step.||
89|D|H|||Resuming a failed autopilot run.|A failed run stops; start a new run.|
90|N|F|js:autopilotui|C:test_t5_research_autopilot|Each run kept in the session with level, steps, statuses and errors.||
91|N|H|js:atlasui|C:test_t6_cosmic_atlas|Equatorial sky map of the targets.||
92|N|H|js:atlasui|C:test_t6_cosmic_atlas|Selecting a target on the map switches to it.||
93|D|H|||Observation footprint maps.|Footprints are not served.|
94|D|H|||Spatial filtering of targets.|Not built.|
95|N|H|js:frontiercore|F:test_browser_twin_and_coordinates_match_python|ICRS to galactic coordinates (tested on the Galactic centre).||
96|N|H|js:frontiercore|F:test_browser_overlays_match_python|Great-circle angular separation (Vincenty).||
97|N|F|js:atlasui|C:test_t6_cosmic_atlas|Distance only from a recorded parallax, labelled inferred; otherwise unknown.||
98|N|H|js:atlasui|C:test_t6_cosmic_atlas|One table compares coordinates, frames, sources and distances of all targets.||
99|N|H|js:atlasui;py:server/app|C:test_t6_cosmic_atlas|Field view: target and reference stars in the tangent plane.||
100|N|H|js:atlasui|C:test_t6_cosmic_atlas|Atlas exports as JSON.||
101|D|R|||Research topic maps.|Not built.|
102|E|H|js:kg|C:test_p_vault_and_studio|Records linked by shared method set.||p6:V212
103|E|H|js:kg|C:test_p_vault_and_studio|Records and sessions linked by stored facts.||p6:V211
104|E|H|js:kg|C:test_p_vault_and_studio|Records naming the same target.||p6:V213
105|D|H|||Curated knowledge collections.|Not built.|
106|N|S|js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Exact multi-word search across records, sessions, notes, hypotheses, opportunities, challenges, methods and concepts.||
107|B|R|||Semantic indexing.|Blocked: no embedding or language model is reachable here; exact search is used instead.|
108|D|H|||Saving a research path.|Not built.|
109|D|H|||Versioned knowledge.|Not built.|
110|E|H|js:records|C:test_p_vault_and_studio|Knowledge graph export.||p6:V220
111|N|S|py:review;js:reviewui|C:test_t8_review_room_repro_story|Methods rule set.||
112|N|S|py:review|F:test_review_findings_cite_sources|Evidence rule set.||
113|N|S|py:review|F:test_review_findings_cite_sources|Data-quality rule set.||
114|N|S|py:review|F:test_review_findings_cite_sources|Reproducibility rule set (REPRO-1 verdict).||
115|N|S|py:review|F:test_review_findings_cite_sources|Interpretation rule set.||
116|N|H|py:review|F:test_review_findings_cite_sources|Thresholds without a documented origin are reported.|Only threshold provenance is checked.|
117|N|H|py:review|F:test_review_findings_cite_sources|Single-item claims and causal or discovery wording are reported.||
118|N|H|py:review|F:test_review_findings_cite_sources|Every outcome must state its limitations.||
119|D|H|||A history of reviews.|Exports are logged in the session history only.|
120|N|H|js:reviewui|C:test_t8_review_room_repro_story|Review exported as Markdown with citations.||
121|N|S|js:reviewui|C:test_t8_review_room_repro_story|Ten chapters written only from recorded outcomes and their statements.||
122|N|H|js:reviewui|C:test_t8_review_room_repro_story|Chapters cite counts, rules and identifiers from the record.|Text references, not links.|
123|N|H|js:reviewui|C:test_t8_review_room_repro_story|The session's recent history as a timeline.|A list, not interactive.|
124|D|H|||Figure sequences in the story.|Not built.|
125|D|H|||Hypothesis histories in the story.|Versions are kept in the session, not narrated.|
126|N|H|js:reviewui|C:test_t8_review_room_repro_story|Methods chapter from the recorded versions.||
127|N|H|js:reviewui|C:test_t8_review_room_repro_story|Results chapter: category and statement per question.||
128|N|H|js:reviewui|C:test_t8_review_room_repro_story|Limitations chapter with open critical and major challenges.||
129|D|H|||Slide or presentation export.|Markdown only.|
130|N|F|js:reviewui|C:test_t8_review_room_repro_story|The story names the run and session hashes it describes.||
131|E|F|py:provenance_check|Q:|Inputs verified against the manifest.||p6:K106
132|N|F|py:repro|F:test_reproducibility_verdicts_and_tamper|Software and platform versions checked (R6, R7).||
133|D|H|||Dependency lock fingerprints.|Not built.|
134|E|F|py:analysis|D:test_registry_names_only_real_methods_and_tests|Method versions recorded in every record.||p6:L115
135|E|F|py:provenance_check|F:test_reproducibility_verdicts_and_tamper|Re-execution compared by content hash.||p6:L119
136|N|F|py:repro|F:test_reproducibility_verdicts_and_tamper|Stated tolerance: exact hash equality.||
137|E|F|js:figurestudio|C:test_s10_figure_studio|Figures carry their run hash.||p6:Q166
138|E|F|py:package|D:test_package_is_deterministic_and_self_verifying|Package checksums verify.||
139|N|F|py:repro|F:test_reproducibility_verdicts_and_tamper|Four verdicts by one stated rule; no score; importing never counts.||
140|N|H|js:reviewui|C:test_t8_review_room_repro_story|Audit exported as JSON.||
141|B|R|||Agent capability registry.|Blocked: no verified model provider (Meta API refused, no key); the review roles are deterministic rule sets.|
142|B|R|||Role-specific agent permissions.|Blocked: no agents without a provider.|
143|B|R|||Structured agent outputs.|Blocked: no provider.|
144|E|F|py:ai/guard|T:|Model answers checked against tool outputs (GUARD-3).||
145|E|F|py:ai/tools|T:|Read-only tools only.||
146|E|H|py:ai/copilot|tests/unit/test_report_ai.py|Model calls audited.||
147|B|R|||Comparing agent results.|Blocked: no provider.|
148|B|R|||Analysing conflicting agents.|Blocked: no provider.|
149|N|F|||Human approval.||dup:85
150|E|H|py:ai/local|tests/unit/test_report_ai.py|The deterministic assistant answers when no provider is available.||
151|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Branch a session.||p6:A2
152|D|H|||Branch comparison.|Not built.|p6:A3
153|D|H|||Merging user-authored metadata between branches.|Not built.|
154|N|F|||Scenario isolation.||dup:2
155|N|F|||Baseline preservation.||dup:2
156|E|H|py:session|S:test_session_rules|Branches record where they came from in their history.||
157|E|H|||Branch provenance.||dup:156
158|D|H|||Conflict detection.|Last save wins.|p6:S189
159|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Branches export like any session.||
160|D|H|||Branch recovery.|Not built.|
161|E|S|py:experiments|R:test_experiment_validation_and_negative_control|Experiment templates.||p6:M121
162|E|S|py:experiments|R:test_experiment_validation_and_negative_control|Controlled parameter experiments.||p6:M122
163|E|S|py:stability|A:test_phase3_params_and_stability|Sensitivity experiments.||p6:H74
164|E|S|py:experiments|R:test_experiment_validation_and_negative_control|Negative controls on another fixture.||p6:M125
165|N|S|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Known-answer scenarios with stated expected outcomes.||
166|E|F|py:experiments|R:test_experiment_validation_and_negative_control|Repeatability.||p6:M126
167|E|S|py:experiments|A:test_phase6_research_planner_sessions_experiments_connectors|Method comparisons.||p6:M124
168|D|R|||Experiment dependency graphs.|Not built.|
169|E|H|py:experiments|R:test_experiment_validation_and_negative_control|Failed runs recorded with errors.||p6:M128
170|E|H|js:notebook|N:test_zipstore_output_is_valid_and_deterministic|Experiments travel in the session package.||p6:M130
171|X|R|||Instrument compatibility.|One instrument (SPHEREx).|p6:C29
172|E|F|py:science/wavelength|W:|WLMATCH-2.||
173|E|F|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits|Visits and compatible sequences.||
174|E|F|py:quality|R:test_quality_outcomes_and_injected_defects|Unit checks.||
175|E|H|js:qualityui|C:test_s3_quality_matrix_metadata_sequences|Metadata diff.||p6:C22
176|E|H|js:kg|C:test_p_vault_and_studio|Same analysis version.||
177|E|F|py:compat|R:test_matrix_is_the_logged_decisions|Reason codes restrict comparisons.||
178|E|F|py:compat|R:test_matrix_is_the_logged_decisions|Every code explained.||
179|E|S|py:compat|R:test_matrix_is_the_logged_decisions|Compatibility matrix.||p6:C21
180|E|H|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Research report JSON.||p6:N140
181|N|S|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Injected signals recovered or not, against truth.||
182|N|H|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Threshold scenarios on a recorded run.||
183|N|H|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Error in σ per motion component and a verdict.||
184|E|S|||False-positive control tests.||dup:164
185|N|H|py:synthobs|F:test_synthetic_validation_and_design_refusals|Target brightness scale and brightness factors.||
186|N|H|||Noise-level scenarios.||dup:45
187|D|R|||Completeness from many injections.|Not run: needs many generated scenarios per point.|
188|N|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Every result states that agreement does not validate real data.||
189|N|F|||Ground-truth comparison.||dup:43
190|N|H|||Recovery reports.||dup:50
191|E|S|js:timemachine|C:test_s3_quality_matrix_metadata_sequences|Registered multi-epoch playback.||p6:D31
192|E|H|py:radar|R:test_radar_items_are_explained_and_ranked_by_the_stated_rule|Time gaps as radar items.||p6:D35
193|E|H|js:ruler|tests/e2e/test_app.py|Observation ruler.||p6:D33
194|N|R|py:synthobs|F:test_observation_design_compares_schedules|Cadence varied in hypothetical schedules.||
195|E|S|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits|Measurement sequences.||
196|E|H|js:figurestudio|C:test_s10_figure_studio|Position offsets against time.||p6:H72
197|E|F|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits|Sequence compatibility.||p6:D38
198|E|H|js:timemachine|C:test_s3_quality_matrix_metadata_sequences|Sequence export lists frames and run.||p6:D39
199|D|H|||Animation export.|Not built.|
200|D|H|||Temporal report.|Not built.|p6:D36
201|E|H|py:connectors|R:test_connector_previews_match_acquisition_and_send_nothing|Query templates.|Live use blocked.|
202|E|F|py:connectors|R:test_connector_previews_match_acquisition_and_send_nothing|Connector validation.|Live use blocked.|
203|E|F|py:bundle|K:|Download manifests.||
204|E|F|py:provenance|Q:|Cache origin labels.||
205|E|F|py:bundle|K:|Dataset fingerprints (SHA-256).||
206|E|F|scripts/diagnose_environment.py|K:|Transfer diagnostics.||
207|E|H|py:archive/net|R:test_retry_after_is_honoured_and_bounded|Retry history.||
208|E|F|py:fitsio|Z:|Response validation.||
209|E|F|py:archive/acquire|K:|Release metadata.||
210|E|F|py:archive/acquire|K:|Acquisition report.|Live acquisition blocked.|
211|D|H|||Region selection.|Not built.|
212|D|H|||Pixel inspection.|Not built.|
213|D|H|||Region statistics.|Not built.|
214|D|H|||Profile analysis.|Not built.|
215|E|H|js:viewer|C:test_b_explorer_controls|Mask display.||p6:E48
216|D|H|||Background estimation diagnostics.|Not built.|
217|E|S|py:view|D:test_registration_on_fixture_pairs|REGDIAG-1.||
218|D|H|||Residual maps.|Not built.|p6:F54
219|D|H|||Image comparison exports.|Not built.|
220|E|F|py:analysis|Q:|Processing steps logged.||
221|E|H|js:figurestudio|C:test_s10_figure_studio|Model residuals.||
222|E|H|py:science/astrometry|D:test_registration_known_answer|Fit diagnostics.||
223|E|S|py:stability|A:test_phase3_params_and_stability|Parameter sensitivity.||
224|D|R|||Numerical stability diagnostics.|Not built.|
225|E|H|py:experiments|R:test_experiment_validation_and_negative_control|Robustness at parameter bounds.||p6:H76
226|D|R|||Distribution checks.|Not built.|
227|E|H|py:science/astrometry|D:test_registration_known_answer|Clipped outliers reported.||
228|E|F|py:uncertainty|D:test_uncertainty_recomputes_logged_values_exactly|UNC-1.||
229|E|F|py:capabilities|D:test_registry_names_only_real_methods_and_tests|Limitations per capability.||
230|D|H|||Diagnostic exports.|Not built.|
231|E|S|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Structured blocks.||p6:P151
232|E|H|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Observation references.||p6:P154
233|E|H|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Hypothesis references.||p6:P155
234|E|H|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Experiment references.||p6:P156
235|E|S|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Evidence-linked blocks.||p6:P152
236|E|H|js:notebookhelpers|C:test_s10_figure_studio|Figure insertion.||p6:P153
237|E|H|js:notebook|S:test_version_histories_are_kept_bounded_and_hashed|Version history.||p6:P157
238|E|H|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Search.||p6:P159
239|D|H|||Notebook comparison.|Not built.|
240|E|F|js:notebook|N:test_zipstore_output_is_valid_and_deterministic|Markdown and package export.||p6:P158
241|E|H|py:missions|R:test_missions_read_completion_from_the_session|Mission templates.||p6:X232
242|E|H|py:missions|R:test_missions_read_completion_from_the_session|Objectives.||
243|E|H|py:missions|R:test_missions_read_completion_from_the_session|Prerequisites stated.|Not enforced.|p6:X233
244|D|H|||Task dependencies.|Not enforced.|p6:X234
245|E|F|py:missions|R:test_missions_read_completion_from_the_session|Completion criteria.||p6:X236
246|E|H|py:session|C:test_s1_command_center_session_and_mission|Mission history.||p6:X238
247|E|H|py:missions|R:test_missions_read_completion_from_the_session|Review tasks.||p6:X237
248|D|R|||Reproducible missions.|Not built.|p6:X240
249|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Missions branch with the session.||
250|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Missions export with the session.||p6:X239
251|E|S|py:view|D:test_evidence_graph_links_each_tested_explanation_to_its_claim|Claim lineage.||p6:K102
252|E|S|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Evidence contradictions.||
253|E|H|py:radar|R:test_radar_items_are_explained_and_ranked_by_the_stated_rule|Unused measurements.||p6:K104
254|E|H|js:ledgerui|C:test_s6_ledger_inspectors|Methods each claim depends on.||p6:K107
255|E|F|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Provenance gaps.||p6:K105
256|E|F|py:bundle|K:|Source checksums.||
257|E|S|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Claim status and support.||
258|D|R|||Evidence comparison between runs.|Not built.|p6:K109
259|N|H|py:adversarial|F:test_adversarial_rules_and_statuses|Evidence challenger as an audit.||
260|E|F|py:package|D:test_package_is_deterministic_and_self_verifying|Evidence package.||
261|E|H|scripts/build_static.py|P:|Hosted read-only preview.||p6:S186
262|X|R|||Review assignments.|No accounts.|p6:S181
263|N|H|js:adversarialui;js:horizonui|C:test_t3_adversarial_lab|Notes attached to challenges and opportunities in the session.|Single user.|
264|N|H|||Review annotations.||dup:263
265|E|F|js:notebook|C:test_h2_copilot_sources_drafts_and_plan|Authorship labels.||p6:S188
266|D|H|||Version conflicts.|Last save wins.|
267|D|H|||Review history (collaboration).||dup:119
268|E|H|js:notebook|N:test_zipstore_output_is_valid_and_deterministic|Session package for reviewers.||p6:S187
269|X|R|||Collaboration permissions.|No accounts.|p6:S190
270|D|R|||Shared sessions.|Not built.|
271|E|F|py:report|tests/unit/test_report_ai.py|Investigation report.||
272|E|H|scripts/gen_research_methods.py|D:test_registry_names_only_real_methods_and_tests|Generated methods documents.||
273|D|H|||Per-observation reports.|The observation twin exists in Python only.|
274|E|H|py:discovery|D:test_hypotheses_known_answers|Hypothesis report.||
275|E|H|js:notebook|C:test_s7_notebook_blocks_versions_undo_exports|Experiments in the notebook export.||
276|N|F|py:repro;js:reviewui|C:test_t8_review_room_repro_story|Reproducibility audit report.||
277|E|H|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Data-quality report.||
278|D|H|||Figure collections.|One figure at a time.|p6:R178
279|D|R|||Publication-oriented layouts.|Not built.|
280|E|F|js:records|C:test_g_records_controls|Machine-readable exports.||
281|D|H|||Tutorials.|Not built.|
282|E|H|js:discovery|C:test_l_discovery_engine|Contextual explanations.||
283|E|H|py:missions|R:test_missions_read_completion_from_the_session|Missions as guided investigations.||
284|D|H|||Method walkthroughs.|Not built.|
285|E|H|js:palette|C:test_k_palette_help_shortcuts|Glossary with Phase 6–7 terms.||
286|E|F|js:main|C:test_k_palette_help_shortcuts|Keyboard paths.||
287|E|F|js:graph|C:test_e_graph_controls|Graph keyboard navigation.||
288|E|F|js:atlasui;js:horizonui|C:test_y_accessible_names|Labelled SVGs, including the new maps.||
289|E|F|web/css/app.css|X:test_reduced_motion_disables_animation|Reduced motion.||
290|E|H|js:main|C:test_j_levels|Levels.||
291|E|F|js:session|C:test_s2_planner_plans_runs_and_persists|Session restoration.||
292|N|F|py:server/frontier|A:test_phase7_frontier_counterfactual_reproduce_synthetic|Reports cached by record hash (and stability); synthetic results reused only after checksum verification.||
293|E|F|scripts/diagnose_environment.py|K:|Dependency inspection.||
294|E|F|py:server/app|A:test_status_and_security_headers|Startup status.||
295|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Retry of failed workflow items.||
296|D|H|||Memory-aware rendering.|Not built.|
297|D|R|||Large-dataset handling.|Only two fixtures exist here.|
298|E|F|py:archive/net|O:test_full_workflow_without_network|Offline mode.||
299|E|F|py:package|D:test_package_is_deterministic_and_self_verifying|Export integrity.||
300|E|F|scripts/make_release.py|scripts/verify.py|Release verification.||
301|E|F|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Imports parsed as data only.||
302|E|F|py:server/app|A:test_rejects_traversal|Path validation.||
303|E|F|py:schema|S:test_browser_matches_python|Schema validation, extended to scenario and synthetic specs.||
304|E|F|py:ai/meta_client|tests/unit/test_report_ai.py|Secrets only in the environment.||
305|N|F|py:capabilities|F:test_registry_permissions_cover_every_action|Permission classes per action; network never granted by the autopilot.||
306|E|F|py:fitsio|Z:|External responses validated.||
307|E|F|py:workflows|R:test_workflow_validation|Imported workflows validated, never auto-run.||
308|E|F|py:provenance|P:test_js_content_hash_matches_python|Record integrity.||
309|E|H|py:session|S:test_session_rules|Audit history.||
310|E|F|tests/integration/test_api.py|A:test_rejects_traversal|Security regression tests.||
311|E|F|py:synthetic|O:test_expected_outcomes_on_synthetic_truth|Golden fixtures with injected truth.||
312|E|F|||Ground-truth fixtures.||dup:311
313|E|F|tests/js|F:test_browser_overlays_match_python|Cross-language parity, extended to the Phase 7 overlays.||
314|E|F|py:synthetic|O:test_expected_outcomes_on_synthetic_truth|Known-answer tests.||
315|E|F|py:canon|S:test_js_number_rules|Numerical boundary tests.||
316|D|H|||Property-based validation.|No property-testing library installed.|
317|E|F|py:uncertainty|D:test_uncertainty_recomputes_logged_values_exactly|Uncertainty tests.||
318|E|F|py:science/wavelength|W:|Method compatibility tests.||
319|E|F|py:provenance_check|F:test_reproducibility_verdicts_and_tamper|Replay tests.||
320|E|F|docs/TEST_REPORT.md|scripts/verify.py|Regression gates recorded.||
321|D|H|||Multi-target sessions.|A session names one target.|
322|N|H|||Target comparison.||dup:98
323|E|H|js:explorer|C:test_b_explorer_controls|Observation grouping.||
324|D|H|||Cross-target metadata inspection.|Not built.|
325|D|R|||Multi-target evidence graphs.|Not built.|
326|E|H|js:kg|C:test_p_vault_and_studio|Shared method comparisons.||
327|E|F|py:science/assess|O:test_expected_outcomes_on_synthetic_truth|Limitations per target outcome.||
328|E|H|py:workflows|C:test_s8_experiments_and_workflows|Batch investigation.||
329|D|H|||Multi-target reporting.|Not built.|
330|D|R|||Cross-target reproducibility.|Not built.|
331|E|H|py:radar|R:test_radar_items_are_explained_and_ranked_by_the_stated_rule|Unexplored measurements.||p6:U204
332|N|H|||Research prerequisite mapping.||dup:24
333|N|H|||Test-selection explanation.||dup:69
334|N|H|||Evidence-gap ranking.||dup:26
335|N|H|||Investigation feasibility.||dup:25
336|N|H|||Opportunity dependencies.||dup:28
337|D|R|||Bottleneck detection.|Not built.|
338|D|R|||Alternative test paths.|Not built.|
339|N|H|||Opportunity history.||dup:29
340|D|R|||Optimisation reports.|Not built.|
341|E|H|py:capabilities|D:test_registry_names_only_real_methods_and_tests|Capability registry.||
342|E|F|scripts/gen_research_methods.py|D:test_registry_names_only_real_methods_and_tests|Method documentation.||
343|E|F|py:capabilities|R:test_registry_actions_and_capabilities_are_consistent|Preconditions.||p6:L113
344|E|F|py:capabilities|R:test_registry_actions_and_capabilities_are_consistent|Assumptions and limitations.||p6:L112
345|D|R|||Method version history.|Not built.|p6:L114
346|E|S|py:experiments;py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Method comparisons.||
347|E|H|py:analysis|Q:|Execution diagnostics in the record.||
348|E|F|py:capabilities|R:test_registry_actions_and_capabilities_are_consistent|Validation coverage.||p6:L116
349|D|R|||Method retirement warnings.|Not built.|p6:L120
350|E|F|py:provenance_check|F:test_reproducibility_verdicts_and_tamper|Method reproducibility.||
351|D|H|||Synchronised panels.|Not built.|
352|E|H|js:ruler|C:test_b_explorer_controls|Ruler selection drives the other views.||
353|E|H|js:viewer|C:test_b_explorer_controls|Measurement overlays.||
354|E|H|js:ruler|C:test_c_time_machine_controls|Chart elements open their observation.||
355|N|S|js:counterfactualui|C:test_t2_counterfactual_lab|Scenario comparison view.||
356|E|H|js:graph|C:test_e_graph_controls|Graph filtering.||
357|N|H|js:atlasui|C:test_t6_cosmic_atlas|Coordinates in two frames per target.||
358|D|H|||Figure annotations.|Not built.|p6:Q162
359|E|H|js:figurestudio|C:test_s10_figure_studio|Figure presets.||
360|E|F|js:figurestudio|C:test_s10_figure_studio|Visualization provenance.||
361|E|H|py:workflows|R:test_workflow_validation|Saved workflows.||
362|E|H|py:stability;py:counterfactual|C:test_t2_counterfactual_lab|Parameter and scenario presets.||
363|E|H|py:workflows|C:test_s8_experiments_and_workflows|Batch experiments.||
364|D|H|||Execution queues.|Steps run sequentially; no queue.|
365|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Cancellation.||
366|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Failure recovery.||
367|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Per-task records.||
368|E|F|py:workflows|R:test_workflow_validation|Versioned workflows.||
369|E|F|py:workflows|R:test_workflow_validation|Import validation.||
370|E|H|py:workflows|R:test_browser_planner_missions_workflows_match_python|Workflow reproducibility.||
371|N|S|py:counterfactual;js:counterfactualui|C:test_t2_counterfactual_lab|Observed / derived / simulated / assumed / hypothetical labels on scenario values.||
372|E|S|js:arena|C:test_m_hypothesis_arena|Hypothesis comparison.||
373|N|H|||Unsupported-claim warnings.||dup:117
374|D|H|||A single assumption registry.|Assumptions are stated per method, threshold and explanation.|
375|E|S|py:hypotheses|D:test_hypotheses_known_answers|Alternative explanations.||
376|E|F|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Single-item support flagged.||
377|E|F|py:science/assess|O:test_expected_outcomes_on_synthetic_truth|Limitation summaries.||
378|E|S|||Contradiction review.||dup:252
379|D|H|||Interpretation history.|Not built.|
380|D|H|||Conclusion exports.|The story is exported; a conclusion format is not.|
381|E|H|py:planner|R:test_planner_known_plans|Question templates.||p6:AC287
382|D|R|||Question dependency graphs.|Not built.|
383|N|H|||Test feasibility.||dup:70
384|N|R|||Observation requirements.||dup:51
385|N|H|py:counterfactual;py:synthobs|F:test_counterfactuals_are_isolated_and_labelled|Missing data examined by exclusion scenarios and omitted synthetic passes.||
386|D|H|||Milestone tracking.|Not built.|
387|D|H|||Plan comparison.|Not built.|p6:B19
388|E|H|js:plannerui|C:test_s2_planner_plans_runs_and_persists|Plan revisions.||p6:B17
389|E|F|py:planner|R:test_browser_planner_missions_workflows_match_python|Plan reproducibility.||p6:B20
390|D|H|||Plan export.|Not built.|
391|N|S|||Counterfactual scenario explorer.||dup:1
392|N|S|||Astronomical investigation twins.||dup:15
393|E|R|py:planner|R:test_planner_known_plans|Adaptive planning.||p6:AD291
394|N|S|||Adversarial hypothesis review.||dup:31
395|N|S|||Synthetic observatory.||dup:41
396|N|R|||Observation design experimentation.||dup:53
397|N|S|||Information-guided testing.||dup:61
398|N|S|||Research autopilot.||dup:86
399|N|S|||Scientific knowledge atlas.||dup:106
400|N|S|||Reproducible discovery orchestration.||dup:90
"""

EXTRA = """
X01|N|S|py:possibility|F:test_possibility_layers_and_horizon_cards|Six-layer investigation model (SPE-1)|Every layer computed by a named method from recorded values.
X02|N|F|py:counterfactual|F:test_reassessment_without_change_reproduces_the_record|Exact re-assessment from recorded inputs|With no change, re-assessment reproduces every recorded outcome.
X03|N|F|py:science/assess|F:test_reassessment_without_change_reproduces_the_record|Explicit threshold overrides in the assessment functions|Bounded overrides; the pipeline itself always uses the fixed thresholds.
X04|N|H|py:counterfactual|C:test_t2_counterfactual_lab|Prepared counterfactual scenarios|Nine labelled presets, recorded for the static preview.
X05|N|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Synthetic data isolated from observation bundles|Generated bundles live under data/synthlab, never data/bundles or fixtures.
X06|N|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Fixed generation stamp for byte-reproducible scenarios|Provenance and manifest times are fixed and documented as such.
X07|N|H|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Failure-behaviour reporting|Exposures the pipeline refused are counted by reason (e.g. blended).
X08|N|F|py:synthobs|C:test_t4_synthetic_observatory_and_design|Verdicts that name calibration limits|A change found only without calibration is reported as not confirmed.
X09|N|F|py:adversarial|F:test_adversarial_rules_and_statuses|Severity classes fixed per rule|Critical / major / moderate / note defined by rule, not scored.
X10|N|F|js:frontiercore|F:test_browser_overlays_match_python|Session-aware overlays with Python parity|Horizon, challenges and review refined in the browser by the same rules.
X11|N|H|js:autopilotui|C:test_t5_research_autopilot|Per-step verdict at the chosen permission level|Steps a level does not allow are named and skipped, never run.
X12|N|H|js:frontiercore|F:test_browser_twin_and_coordinates_match_python|Parsing of target coordinate hints|Sexagesimal hints parsed; unparseable ones are left empty.
X13|N|F|js:atlasui|C:test_t6_cosmic_atlas|Coordinate source labels|Each position says whether it is generator input, bundle, or an unverified secondary source.
X14|N|H|py:planner|R:test_planner_known_plans|Challenge and counterfactual planner intents|New PLAN-1 templates route objectives to the frontier actions.
X15|N|F|js:executor|F:test_executor_implements_every_registered_action|Executor coverage of every registered action|The browser executor implements exactly the registered actions.
X16|N|H|scripts/build_static.py|C:test_t2_counterfactual_lab|Static preview recording of Phase 7 results|Frontier reports, prepared scenarios, synthetic templates and one design are recorded at build time.
X17|N|F|js:static/backend|C:test_t2_counterfactual_lab|Canonical lookup keys for recorded scenarios|Edited scenarios are refused in the preview, never approximated.
X18|N|F|py:session|F:test_session_accepts_v07_fields_and_keeps_06_sessions_valid|Backward-compatible session extension|Optional v0.7 fields; 0.6 sessions stay valid.
X19|N|H|py:server/app|C:test_t6_cosmic_atlas|Reference-star positions served with the target|Enables the field view.
X20|N|F|py:twin|F:test_twins_integrity_and_comparison|Twin semantics statement|Every twin states it is a computational record, not a physical model.
X21|N|F|js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Twin integrity check in the browser|Content hashes recomputed when twins are shown.
X22|N|H|web/index.html|C:test_y_accessible_names|Navigation in eight research modes|Observatory · Discover · Investigate · Experiment · Understand · Orchestrate · Knowledge · Publish, gated by level.
X23|N|H|py:possibility|F:test_browser_overlays_match_python|Session-aware opportunity filtering|Examined pairs and opened sequences leave the horizon.
X24|N|F|js:reviewui|C:test_t8_review_room_repro_story|Story discipline|Inconclusive results stay inconclusive; positive outcomes stay candidates while alternatives stand.
X25|N|S|py:synthobs|F:test_observation_design_compares_schedules|Controlled schedule comparison|Same truth and seed for every schedule.
X26|N|H|py:infogain|F:test_information_analysis_has_no_probabilities|Resolution routes for open tests|What resolving each test would take (run, new data, new method).
X27|N|H|scripts/gen_research_methods.py|scripts/gen_research_methods.py|Phase 7 methods generated from code|Tables produced by running the methods.
X28|D|H|||Copilot access to Phase 7 results|The copilot's tools do not yet read frontier reports.
X29|N|H|js:horizonui|C:test_t1_discovery_horizon|Plan an opportunity's question|An opportunity's question hands over to the Planner.
X30|N|F|py:server/frontier|A:test_phase7_frontier_counterfactual_reproduce_synthetic|Validated Phase 7 API inputs|Scenarios, synthetic specs, stability bodies and identifiers are validated.
X31|N|H|js:counterfactualui|C:test_t2_counterfactual_lab|Baseline-intact indicator|The scenario shows whether its baseline's hash recomputed.
X32|N|H|js:adversarialui|C:test_t3_adversarial_lab|Challenge acknowledgement with notes|A note changes the status to acknowledged; the challenge stays visible.
X33|N|H|js:synthobsui|C:test_t4_synthetic_observatory_and_design|Synthetic scenario history in the session|Verdicts and record hashes kept per scenario.
X34|N|H|py:repro|F:test_reproducibility_verdicts_and_tamper|Tamper detection in the audit|A modified record fails R8.
X35|N|F|py:counterfactual|F:test_counterfactual_validation_refuses|Counterfactual input refusals|Unknown kinds, out-of-bound values and unknown keys are refused with reasons.
X36|N|H|js:reviewui|C:test_t8_review_room_repro_story|Story copied into the notebook as drafts|Labelled assistant drafts until accepted.
X37|N|H|js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Source attribution for every search result|Each hit names where it is stored.
X38|N|F|py:possibility|F:test_possibility_layers_and_horizon_cards|Opportunity map integrity|Every edge connects nodes present in the cards.
X39|N|H|js:autopilotui|C:test_t5_research_autopilot|Proposed next step after a run|The top remaining opportunity is offered.
X40|N|F|scripts/phase7_catalogue.py|tests/unit/test_phase7_catalogue.py|Catalogue deduplicated across phases|Phase 6 entries cited; synonyms merged.
X41|N|H|js:atlasui|C:test_t6_cosmic_atlas|Angular-only separation statement|The atlas says no physical separation is computed without distances.
X42|N|H|js:counterfactualui|C:test_t2_counterfactual_lab|Custom counterfactual builder|Kind-specific inputs with stated bounds.
"""


def _path(p):
    if p.startswith("py:"):
        return f"src/skytrace/{p[3:]}.py"
    if p.startswith("js:"):
        return f"web/js/{p[3:]}.js"
    return p


def _ver(v):
    if not v:
        return "—"
    if ":" in v and len(v.split(":")[0]) == 1 and v.split(":")[0] in TESTS:
        k, name = v.split(":", 1)
        return TESTS[k] + (f"::{name}" if name else "")
    return v


def build() -> dict:
    names = [n for line in NAMES.strip().split("\n") for n in line.split("|")]
    assert len(names) == 400, len(names)
    items = []
    for line in ROWS.strip().split("\n"):
        n, st, grp, ev, ver, expl, lim, ref = (line.split("|") + [""] * 8)[:8]
        n = int(n)
        dup = ref[4:] if ref.startswith("dup:") else None
        p6 = ref[3:] if ref.startswith("p6:") else None
        items.append({"id": f"P7-{n:03d}", "number": n, "domain": DOMAINS[(n - 1) // 10], "concept": names[n - 1], "status": STATUS[st], "status_code": st,
                      "group": GROUP[grp], "priority": "—" if st == "X" else PRIORITY[grp], "explanation": expl,
                      "evidence": [_path(p) for p in ev.split(";") if p], "verification": _ver(ver),
                      "limitations": lim or ("Not built in 0.7; no control or document claims it." if st == "D" else ""),
                      "phase6": p6, "duplicate_of": f"P7-{int(dup):03d}" if dup else None, "source": "brief"})
    for line in EXTRA.strip().split("\n"):
        xid, st, grp, ev, ver, name, expl = line.split("|")
        items.append({"id": f"P7-{xid}", "number": None, "domain": "Added by this project", "concept": name, "status": STATUS[st], "status_code": st,
                      "group": GROUP[grp], "priority": PRIORITY[grp], "explanation": expl, "evidence": [_path(p) for p in ev.split(";") if p],
                      "verification": _ver(ver), "limitations": "Not built in 0.7." if st == "D" else "", "phase6": None, "duplicate_of": None, "source": "project"})
    distinct = [x for x in items if not x["duplicate_of"]]
    counts = {"rows": len(items), "brief_concepts": 400, "merged_synonyms": len(items) - len(distinct), "added": len(EXTRA.strip().split("\n")),
              "distinct": len(distinct), "domains": len(DOMAINS), "carried_from_phase6": sum(1 for x in distinct if x["phase6"]),
              "by_status": {STATUS[k]: sum(x["status_code"] == k for x in distinct) for k in STATUS},
              "by_group": {g: sum(x["group"] == g for x in distinct) for g in GROUP.values()},
              "implemented": sum(x["status_code"] in "EN" for x in distinct)}
    return {"schema": "skytrace.phase7_catalogue/1", "statuses": STATUS, "groups": GROUP, "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    out = ["# Skytrace Phase 7 capability catalogue", "",
           "Generated by `python scripts/phase7_catalogue.py`; every count is computed. Checked by `tests/unit/test_phase7_catalogue.py` "
           "(400 brief concepts in 40 domains, ≥ 400 distinct, every cited file and test exists, deferred items cite nothing, synonyms "
           "point to counted concepts).", "",
           "The concepts and domains are those of the Phase 7 brief (§20). Duplicates inside this catalogue are merged (*duplicate of*); "
           "concepts already in the Phase 6 catalogue keep their status and cite the Phase 6 ID. Concepts this project added are listed "
           "at the end and counted. The 0.5 and 0.6 catalogues are kept unchanged.", "",
           f"**{c['distinct']} distinct concepts** ({c['brief_concepts']} from the brief − {c['merged_synonyms']} merged + {c['added']} added) in "
           f"{c['domains']} domains; {c['carried_from_phase6']} cite a Phase 6 entry. Status: " + ", ".join(f"{v} {k}" for k, v in c["by_status"].items()) +
           ". Groups: " + ", ".join(f"{v} {k}" for k, v in c["by_group"].items()) + ".", "",
           "| Domain | Distinct | Existing | New in 0.7 | Deferred | Blocked | Out of scope | Merged |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    doms = DOMAINS + ["Added by this project"]
    for d in doms:
        xs = [x for x in cat["items"] if x["domain"] == d]
        ds = [x for x in xs if not x["duplicate_of"]]
        n = Counter(x["status_code"] for x in ds)
        out.append(f"| {d} | {len(ds)} | {n['E']} | {n['N']} | {n['D']} | {n['B']} | {n['X']} | {len(xs) - len(ds)} |")
    out.append("")
    for d in doms:
        out += [f"## {d}", "", "| ID | Concept | Status | Group | Explanation | Limitations | Evidence | Verified by |", "|---|---|---|---|---|---|---|---|"]
        for x in (x for x in cat["items"] if x["domain"] == d):
            if x["duplicate_of"]:
                out.append(f"| {x['id']} | {x['concept']} | duplicate of {x['duplicate_of']} | — | Same capability as {x['duplicate_of']}; not counted. | — | — | — |")
                continue
            st = x["status"] + (f" (Phase 6 {x['phase6']})" if x["phase6"] else "")
            ev = ", ".join(f"`{p}`" for p in x["evidence"]) or "—"
            ver = x["verification"] if x["verification"] == "—" else f"`{x['verification']}`"
            out.append(f"| {x['id']} | {x['concept']} | {st} | {x['group']} ({x['priority']}) | {x['explanation']} | {x['limitations'] or '—'} | {ev} | {ver} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "phase7_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "PHASE7_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
