"""Phase 8 capability catalogue: the 500 concepts of the Phase 8 brief (§26, 50 domains), deduplicated against each
other and against the Phase 7 catalogue, plus concepts this project added, each with description, user value, scientific
value, dependencies, status, priority, verification and limitations.

    python scripts/phase8_catalogue.py      # writes docs/phase8_catalogue.json and docs/PHASE8_CATALOGUE.md

Status   E existing (built in 0.7.0 or earlier; `p7` names the Phase 7 catalogue entry where one exists — never counted as new) ·
         N new in 0.8 · D deferred (not built; nothing claims it) · B blocked (needs a service this environment refuses) · X out of scope.
Group    F Foundation · H High Impact · S Signature · R Frontier (priority P1 · P2 · P2 · P3).
Merged   a concept naming the same capability as another is recorded with `duplicate_of` and not counted; concepts this project
         added (P8-X..) keep the distinct count at or above 500.
Each row: number | status | group | evidence (";"-separated; `py:x` = src/skytrace/x.py, `js:x` = web/js/x.js) | verification
         (`E:` tests/unit/test_epistemic.py, `C:` e2e test_controls, `F:` test_frontier, `A:` test_api, `R:` test_research_os,
         `S:` test_research_session, `D:` test_discovery, `O:` test_offline_workflow, `P:` test_static_preview, `N:` test_notebook_package,
         `X:` test_accessibility, `T:` test_tool_contracts, `Q:` test_provenance_check (file), `W:` test_wavelength_flags (file),
         `K:` test_acquire (file), or a path) | description | limitation (optional) | p7:<id> or dup:<number> (optional).
User value, scientific value and dependencies: the domain's statement (USER_VALUE, SCI_VALUE) and the modules the evidence names.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = {"E": "existing", "N": "new in 0.8", "D": "deferred", "B": "blocked", "X": "out of scope"}
GROUP = {"F": "Foundation", "H": "High Impact", "S": "Signature", "R": "Frontier"}
PRIORITY = {"F": "P1", "H": "P2", "S": "P2", "R": "P3"}
TESTS = {"E": "tests/unit/test_epistemic.py", "C": "tests/e2e/test_controls.py", "F": "tests/unit/test_frontier.py", "A": "tests/integration/test_api.py",
         "R": "tests/unit/test_research_os.py", "S": "tests/unit/test_research_session.py", "D": "tests/unit/test_discovery.py",
         "O": "tests/unit/test_offline_workflow.py", "P": "tests/unit/test_static_preview.py", "N": "tests/unit/test_notebook_package.py",
         "X": "tests/unit/test_accessibility.py", "T": "tests/unit/test_tool_contracts.py", "Q": "tests/unit/test_provenance_check.py",
         "W": "tests/unit/test_wavelength_flags.py", "K": "tests/unit/test_acquire.py"}

DOMAINS = ["Epistemic Computing", "Scientific Compilation", "Scientific Debugging", "Knowledge Boundaries", "Claim Stress Testing", "Negative Knowledge",
           "Blindspot Detection", "Method Intelligence", "Uncertainty Lineage", "Data Lineage", "Blind Analysis", "Reproduction", "Decision Intelligence",
           "Model Arena", "Evidence Conservation", "Scientific Argumentation", "Scientific Integrity", "Question Discovery", "Research Protocols",
           "Possibility Mapping", "Multi-Scale Exploration", "Simulation Validation", "Research Review", "Future Scenarios", "Scientific Copilot",
           "Investigation State", "Advanced Data Quality", "Statistical Reasoning", "Observation Intelligence", "Advanced Time Research", "Image Science",
           "Scientific Automation", "Research Knowledge", "Collaborative Review", "Scientific Reporting", "Scientific Accessibility", "External Data Integrity",
           "Security", "Platform Engineering", "Scientific Validation", "Advanced Hypothesis Research", "Counterfactual Research", "Digital Twins",
           "Scientific Information Analysis", "Scientific Reasoning Quality", "Research Decision History", "Scientific Learning", "Discovery Operations",
           "Research Interoperability", "The Epistemic Frontier"]
USER_VALUE = {
    0: "see how each conclusion is built and what it rests on", 1: "find structural problems in an investigation before trusting it", 2: "find out why a result came out as it did",
    3: "see what the evidence does and does not establish", 4: "challenge one claim systematically", 5: "keep failed and inconclusive work instead of losing it",
    6: "see which parts have not been looked at", 7: "understand and compare the methods behind the numbers", 8: "see where uncertainty comes from and what it omits",
    9: "follow a result back to its files", 10: "fix analysis choices before seeing outcomes", 11: "repeat an analysis and see how close it comes",
    12: "decide what to do next with stated reasons", 13: "compare models on the same data honestly", 14: "keep an untampered history of the investigation",
    15: "build and test an argument", 16: "check a text before sharing it", 17: "find questions worth asking", 18: "separate planned from post-hoc choices",
    19: "navigate from questions to the data and methods they need", 20: "move between pixels, measurements and conclusions", 21: "know what a simulation assumes",
    22: "review an investigation from several angles", 23: "plan future measurements", 24: "ask questions in plain language", 25: "save, branch and restore work",
    26: "trust the data's quality checks", 27: "check statistical reasoning", 28: "understand each observation in context", 29: "work across many epochs",
    30: "inspect images", 31: "automate repeatable work safely", 32: "find related work", 33: "review together", 34: "produce reports that can be checked",
    35: "use the product with any ability", 36: "trust what came from an archive", 37: "be safe with imported material", 38: "run the product reliably",
    39: "know the software is tested", 40: "work with competing hypotheses", 41: "ask what-if questions", 42: "keep hashed records of what Skytrace knows",
    43: "pick the most informative test", 44: "judge the quality of the reasoning", 45: "audit decisions later", 46: "learn the methods", 47: "organise ongoing work",
    48: "exchange data with other tools", 49: "inspect the architecture of scientific knowledge itself"}
SCI_VALUE = {i: v for i, v in enumerate([
    "every statement carries its origin and method, so inference can be told from observation", "methodological errors are caught by rules, not by impression",
    "discrepancies are traced to their earliest cause", "scientific restraint becomes visible", "a claim's weak points are named by rule",
    "negative results stay part of the record", "coverage of the defined checks is explicit", "methods carry their assumptions and validation",
    "uncertainty is never silently dropped", "transformations are auditable", "analysis choices are protected from outcome bias", "reproducibility is graded honestly",
    "research steps are justified", "model fit is separated from physical truth", "the evidence history is tamper-evident", "logical validity is separated from empirical truth",
    "overstatement and unsupported numbers are caught before publication", "questions are grounded in evidence", "pre-analysis plans are distinguishable from post-hoc ones",
    "research options are mapped to actual capabilities", "evidence is examined at every level", "synthetic benchmarks stay distinct from observational validation",
    "review findings cite their evidence", "future measurements are planned with validated formulas", "answers stay grounded in tools",
    "state is versioned and verifiable", "quality is assessed by explicit rules", "statistical assumptions are checked", "observations are compared only when compatible",
    "temporal analysis respects sampling", "image processing is traceable", "automation stays within validated capabilities", "knowledge links rest on stored facts",
    "review is accountable", "reports are traceable to records", "access does not depend on ability", "archive data are verified", "imports cannot run code or escape paths",
    "results do not depend on luck of the environment", "methods are validated against known answers", "competing explanations are tested by rules",
    "scenarios never overwrite the original", "twins are computational records, not physics", "test selection is reasoned without invented probabilities",
    "reasoning quality is inspected by rule", "decisions are reconstructible", "methods are learned with their limits", "work progress is honest",
    "records travel with their provenance", "conclusions are inspectable, testable, challengeable and reproducible"])}

NAMES = """Scientific object schemas|Epistemic status labels|Reasoning graphs|Claim lineage|Assumption lineage|Inference dependencies|Scientific object versioning|Epistemic validation|Claim comparison|Knowledge boundary inspection
Input type checking|Unit compatibility|Dependency resolution|Assumption checking|Method precondition checking|Evidence validation|Uncertainty validation|Provenance validation|Conclusion validation|Compilation reports
Result breakpoints|Transformation inspection|Intermediate output inspection|Run comparison|Divergence localization|Input difference inspection|Parameter difference inspection|Method difference inspection|Reproduction debugging|Debugging history
Evidence-supported claims|Assumption-dependent claims|Inconclusive claims|Unsupported claims|Missing-evidence mapping|Boundary transitions|Claim status history|Evidence sufficiency|Boundary explanations|Boundary exports
Input compatibility|Measurement validity|Statistical assumptions|Method suitability|Uncertainty review|Alternative explanation tests|Reproducibility checks|Claim wording review|Contradiction inspection|Stress-test reports
Failed analysis records|Inconclusive tests|Unavailable data|Unsupported methods|Missing measurements|Invalid comparisons|Failed reproductions|Abandoned hypotheses|Known limitations|Negative knowledge search
Unexamined observations|Unused measurements|Missing metadata|Untested assumptions|Unexplored hypotheses|Unexamined systematics|Missing provenance|Untested boundaries|Investigation coverage|Blindspot reports
Method schemas|Method assumptions|Method version history|Method dependency graphs|Method comparison|Method compatibility|Validation coverage|Known-answer tests|Method limitations|Method reproducibility
Input uncertainty|Transformation uncertainty|Calibration uncertainty|Model uncertainty|Parameter uncertainty|Output uncertainty|Propagation method records|Unit-aware propagation|Uncertainty dependencies|Uncertainty lineage exports
Source-file identity|Input fingerprints|Transformation history|Unit conversion records|Coordinate transformation records|Processing-stage comparison|Missing transformation detection|Dependency changes|Data product versioning|Lineage exports
Blind protocol creation|Hidden-field definitions|Information separation|Pre-analysis records|Controlled unblinding|Blind-state audit|Accidental disclosure checks|Protocol amendments|Blind analysis reports|Blind workflow validation
Environment fingerprints|Dependency snapshots|Input verification|Method restoration|Parameter restoration|Independent replay|Numerical comparison|Tolerance analysis|Difference localization|Reproduction reports
Next-test selection|Missing-evidence analysis|Investigation feasibility|Hypothesis discrimination|Test utility comparison|Decision records|Alternative action comparison|Decision assumptions|Decision history|Decision reports
Model registration|Model assumptions|Model comparison|Parameter inspection|Residual comparison|Goodness-of-fit diagnostics|Model sensitivity|Model validation|Model limitations|Model selection records
Append-only event records|Claim history|Hypothesis history|Analysis event history|Scenario history|Annotation history|Export history|Integrity verification|Historical evidence inspection|Evidence event export
Structured claims|Supporting arguments|Contradictory arguments|Assumption links|Inference rules|Argument branching|Argument comparison|Evidence tracing|Dispute tracking|Argument export
Unsupported-claim detection|Synthetic-data warnings|Unit validation|Provenance validation (export)|Citation validation|Unsupported-probability detection|Method-description validation|Limitation validation|Export readiness|Integrity reports
Evidence-generated questions|Research-gap questions|Testable questions|Partially answerable questions|Data-dependent questions|Method-dependent questions|Hypothetical questions|Question provenance|Question prioritization|Question history
Protocol creation|Hypothesis prerecording|Input selection records|Exclusion criteria|Parameter records|Evaluation criteria|Robustness plans|Protocol locking|Protocol amendments (protocols)|Protocol comparison
Research possibility graph|Evidence dependencies|Method dependencies|Missing prerequisite mapping|Question navigation|Investigation path planning|Path validity|Opportunity comparison|Map provenance|Possibility map export
Pixel inspection|Measurement inspection|Observation inspection|Investigation inspection|Knowledge inspection|Synchronized selections|Cross-level navigation|Evidence focus|Context preservation|Multi-scale exports
Generator identity|Seed records|Ground-truth records|Noise assumptions|Simplification records|Validity domains|Repeated-seed tests|Boundary tests|Recovery diagnostics|Simulation audits
Data review|Method review|Statistical review|Uncertainty review (review)|Provenance review|Reproducibility review|Interpretation review|Human review comments|Review responses|Review reports
Additional-observation planning|Measurement-precision scenarios|Cadence scenarios|Temporal-baseline scenarios|Missing-metadata scenarios|Future-test comparison|Hypothetical data requirements|Scenario assumptions|Future research planning|Scenario reports
Epistemic-aware question routing|Claim provenance responses|Assumption explanations|Evidence limitation explanations|Scientific compilation explanations|Debugging assistance|Research question generation|Method comparison assistance|Review assistance|Source-grounded report drafting
State snapshots|State branching|State restoration|State comparison|State validation|State migrations|State provenance|State integrity|State recovery|State export
Data-quality rule registry|Unit consistency|Metadata completeness|Calibration metadata|File integrity|Observation compatibility|Missing-value classification|Quality-rule history|Quality comparison|Quality reports
Assumption checks|Model diagnostics|Residual analysis|Sensitivity analysis|Boundary testing|Parameter identifiability where applicable|Numerical stability|Model comparison (statistics)|Diagnostic lineage|Statistical reports
Observation metadata graph|Observation dependencies|Epoch compatibility|Instrument compatibility|Channel compatibility|Coverage gaps|Observation pairing|Observation quality|Observation history|Observation exports
Multi-epoch comparison|Temporal coverage|Sampling analysis|Time-gap inspection|Temporal measurement trajectories|Sequence compatibility|Temporal uncertainty|Temporal residuals|Animation provenance|Temporal reports
Pixel profiles|Region statistics|Background diagnostics|Registration diagnostics|Transformation inspection (images)|Image masks|Residual maps|Image compatibility|Processing history|Image provenance
Workflow templates|Capability validation|Workflow permissions|Execution records|Cancellation|Retry controls|Failure localization|Workflow branching|Workflow reproducibility|Workflow export
Structured research search|Related investigation discovery|Method relationships|Target relationships|Evidence reuse|Knowledge collections|Knowledge history|Research path saving|Knowledge provenance|Knowledge exports
Review assignments|Reviewer identity|Evidence comments|Claim comments|Review resolution|Review history|Read-only sharing|Conflict detection|Review permissions|Review packages
Claim-linked reports|Method reports|Evidence reports|Uncertainty reports|Reproduction reports (reporting)|Integrity reports (reporting)|Figure provenance|Investigation narratives|Machine-readable packages|Report validation
Epistemic glossary|Contextual explanations|Keyboard reasoning navigation|Accessible graph exploration|Screen-reader summaries|High contrast|Reduced motion|Beginner scientific mode|Research mode|Accessible figure exports
Archive connector validation|Response schema validation|Download checksums|Data release metadata|Rate-limit handling|Acquisition provenance|Retry history|Cache integrity|External error diagnostics|Archive audit
Import validation|Workflow sandboxing|Path validation|API credential isolation|Permission boundaries|Untrusted response handling|Safe report generation|Audit logs|Dependency review|Security tests
Startup diagnostics|Dependency diagnostics|Memory management|Image performance|Graph performance|Large-session handling|Export performance|Offline diagnostics|Recovery workflows|Release integrity
Known-answer datasets|Golden fixtures|Cross-language parity|Numerical boundaries|Property-based testing|Scientific regression tests|Uncertainty validation (tests)|Provenance validation (tests)|Reproducibility validation|Method test coverage
Hypothesis dependencies|Competing hypothesis models|Contradictory predictions|Evidence requirements|Falsification records|Hypothesis revision|Hypothesis branching|Hypothesis comparison|Hypothesis history (research)|Hypothesis exports
Input perturbation|Parameter perturbation|Scenario comparison|Baseline preservation|Counterfactual provenance|Scenario reproducibility|Scenario sensitivity|Difference localization (counterfactual)|Scenario validation|Counterfactual reports
Observation twin|Target twin|Analysis twin|Scenario twin|Investigation twin|Twin versioning|Twin comparison|Twin dependencies|Twin restoration|Twin integrity
Test discrimination|Hypothesis separation|Information assumptions|Evidence-gap ranking|Candidate measurement comparison|Decision analysis|Sensitivity-driven planning|Information method validation|Research action comparison|Information reports
Inference inspection|Assumption completeness|Evidence sufficiency (reasoning)|Claim scope validation|Contradiction handling|Unsupported language detection|Alternative interpretation review|Reasoning history|Argument comparison (reasoning)|Reasoning quality reports
Decision records (history)|Decision alternatives|Decision assumptions (history)|Decision dependencies|Decision revisions|Decision rationale|Decision comparison|Decision provenance|Decision audit|Decision exports
Method walkthroughs|Reasoning tutorials|Interactive assumptions|Evidence interpretation lessons|Uncertainty demonstrations|Counterfactual exercises|Scientific debugging tutorials|Reproducibility exercises|Research mission templates|Learning progress records
Investigation queues|Research milestones|Evidence task lists|Review queues|Experiment queues|Blocked-task explanations|Execution history|Research scheduling|Progress snapshots|Operation reports
Versioned JSON schemas|FITS metadata exchange where supported|VOTable interoperability where supported|Standardized measurement exports|Provenance exchange|Investigation package import|Investigation package export|Schema compatibility|External reference validation|Interoperability reports
Scientific reasoning compilation|Scientific investigation debugging|Knowledge boundary exploration|Claim stress testing|Negative knowledge preservation|Blindspot detection|Method genome|Uncertainty lineage|Scientific integrity firewall|End-to-end epistemic reproducibility"""

E = "E:"
ROWS = f"""
1|N|F|py:epistemic|{E}test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses|Fifteen object kinds with stable identifiers built from the record (EPI-1).||
2|N|F|py:epistemic;js:epiui|{E}test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses|Ten epistemic statuses assigned by stated rules S1–S10 from origin and method, never from wording.||
3|N|S|py:epistemic;js:reasoningui|C:test_e1_reasoning_graph_and_lineage|Reasoning graph with data edges and procedural context.||
4|N|S|py:epistemic;js:epistemiccore|{E}test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims|Backward trace from a claim to files, measurements, methods and assumptions.||
5|N|H|py:epistemic|{E}test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims|Assumptions, models and thresholds reached by the trace.||
6|N|H|py:epistemic|{E}test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims|Inferences link their recorded inputs to claims; forward trace shows dependents.||
7|D|R|||Versioned scientific objects across runs.|Objects are rebuilt per run; no object version history.|
8|N|F|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Every object has a known kind and a status from the fixed list (SCI-COMP P3).||
9|D|H|||Comparing one claim across runs.|Run-to-run differences are shown by the debugger, not per claim.|
10|N|S|py:claims;js:claimsui|{E}test_knowledge_boundary_rules|Knowledge boundary with four regions and stated rules (KBOUND-1).||
11|N|F|py:scicomp|{E}test_compiler_detects_injected_defects|Comparisons only between same-detector, WLMATCH-accepted pairs; typed flux inputs.||
12|N|F|py:scicomp;py:methodgenome|{E}test_compiler_detects_injected_defects|Image and variance units checked against the method genome's declared inputs.||
13|N|F|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Every derived result resolves to recorded inputs.||
14|N|F|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Thresholds have provenance, parameters are recorded, testable assumptions were tested.||
15|N|F|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|PAIRDIFF-2, LINFIT and ASSESS-2 preconditions and parameter ranges.||
16|N|F|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Outcomes re-derived from recorded inputs; positive claims decided by inputs; contradictions flagged.||
17|N|F|py:scicomp|{E}test_compiler_detects_injected_defects|Errors present and positive; σ and z recompute; non-propagating steps declared.||
18|N|F|py:scicomp|{E}test_compiler_detects_injected_defects|Record hash, file hashes against the manifest, method versions.||
19|N|F|py:scicomp|{E}test_compiler_detects_injected_defects|Negation-aware wording check; open alternatives; absence claims bounded by sensitivity.||
20|N|S|py:scicomp;js:compilerui|C:test_e2_scientific_compiler_and_method_genome|Ten-stage report with one precedence rule and exportable JSON.||
21|N|S|py:scidebug;js:debuggerui|{E}test_debugger_breakpoints_are_real_stages_and_recompute_exactly|Breakpoints only at execution stages the record contains.||
22|N|H|py:scidebug|C:test_e4_scientific_debugger|Method, formula, parameters and inputs behind a result.||
23|N|H|py:scidebug|{E}test_debugger_breakpoints_are_real_stages_and_recompute_exactly|Recorded intermediate values; nothing reconstructed that was not recorded.||
24|N|S|py:scidebug;js:epistemiccore|{E}test_differential_debugging_finds_the_earliest_divergence|Stage-by-stage comparison of two runs, also in the static preview.||
25|N|S|py:scidebug|{E}test_differential_debugging_finds_the_earliest_divergence|Earliest differing stage in pipeline order.||
26|N|H|py:scidebug|{E}test_differential_debugging_finds_the_earliest_divergence|Bundle manifest compared.||
27|N|H|py:scidebug|{E}test_differential_debugging_finds_the_earliest_divergence|Parameter and assumption differences listed.||
28|N|H|py:scidebug|{E}test_differential_debugging_finds_the_earliest_divergence|Method-version differences listed.||
29|N|H|py:reprox;py:scidebug|{E}test_reproduction_verdicts|Reproduction localises the earliest divergence.||
30|N|H|js:debuggerui|C:test_e4_scientific_debugger|Comparisons and reproductions kept in the session.||
31|N|S|py:claims|{E}test_knowledge_boundary_rules|Established region (rule B1).||
32|N|S|py:claims|{E}test_knowledge_boundary_rules|Supported under assumptions (B2), with the assumptions listed.||
33|N|S|py:claims|{E}test_knowledge_boundary_rules|Unresolved region (B3) with the reasons.||
34|N|H|py:claims;py:epistemic|{E}test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses|Claims without decided inputs are 'unsupported'.||
35|N|H|py:claims|C:test_e3_claims_boundary_stress_blindspots|Open tests that could move each claim.||
36|D|R|||Region changes over time.|Regions are computed per run; transitions are not tracked.|
37|D|R|||History of a claim's status.|Not built.|
38|N|H|py:claims|{E}test_claim_stress_modes_and_results|Sufficiency rules (two detectors, three visits, stated bound).||
39|N|H|py:claims|C:test_e3_claims_boundary_stress_blindspots|Every placement says why, with evidence, assumptions and limitations.||
40|N|H|js:claimsui|C:test_e3_claims_boundary_stress_blindspots|Boundary map exported as JSON.||
41|N|S|py:claims|{E}test_claim_stress_modes_and_results|Input-compatibility mode from SCI-COMP checks.||
42|N|H|py:claims|{E}test_claim_stress_modes_and_results|Measurement validity from DQ-1.||
43|N|H|py:claims|{E}test_claim_stress_modes_and_results|CALCHECK scale and fit χ²ν.||
44|N|H|py:claims|{E}test_claim_stress_modes_and_results|Method preconditions for the claim's methods.||
45|N|H|py:claims;py:counterfactual|{E}test_claim_stress_modes_and_results|Category re-derived at 3σ and 8σ thresholds.||
46|N|H|py:claims|{E}test_claim_stress_modes_and_results|Artefact explanations not ruled out.||
47|N|H|py:claims;js:claimsui|C:test_e4_scientific_debugger|Reproducibility mode settled by a recorded reproduction.||
48|N|H|py:claims;py:epistemic|{E}test_asserted_words_ignore_negated_uses|Negation-aware check of discovery, proof and causal wording.||
49|E|H|py:ledger|R:test_ledger_counts_support_and_flags_conflicts|Contradictions by rules C1–C4.||p7:P7-038
50|N|S|js:claimsui|C:test_e3_claims_boundary_stress_blindspots|Ten-mode stress report, exportable.||
51|N|S|py:negspace;js:negativeui|{E}test_negative_knowledge_registry_records_what_failed|Refused measurements and failed session work recorded.||
52|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Tests not run, lacking evidence or inconclusive.||
53|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Excluded images and unreachable services.||
54|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Uncalibrated pairs and questions no method answers.||
55|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Missing measurements grouped by refusal code.||
56|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Rejected pairs by WLMATCH-2 code.||
57|N|H|js:debuggerui;js:negativeui|C:test_e4_scientific_debugger|Unsuccessful reproductions added to the session registry.||
58|N|H|js:negativeui|C:test_e7_negative_space_and_integrity|Abandoning one of your hypotheses records it.||
59|N|H|py:negspace|{E}test_negative_knowledge_registry_records_what_failed|Outcome limitations as entries.||
60|N|S|js:negativeui|C:test_e7_negative_space_and_integrity|Search and filter by category and distinction.||
61|N|H|py:blindspot;js:epistemiccore|{E}test_blindspot_coverage_is_over_defined_checks_only|Visits without an inspected pair.||
62|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|Usable measurements used by no comparison and no fit.||
63|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|Unknown inventory fields.||
64|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|Assumptions a method could test but did not.||
65|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|Explanations without an evaluated test.||
66|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|UNC-1 unquantified effects.||
67|N|H|py:blindspot|{E}test_blindspot_coverage_is_over_defined_checks_only|Measurements without hashed source files.||
68|N|H|py:blindspot;js:epistemiccore|{E}test_browser_epistemic_functions_match_python|Sensitivity runs and threshold scenarios in the session.||
69|N|S|py:blindspot;js:claimsui|C:test_e3_claims_boundary_stress_blindspots|Coverage over eleven defined checks, no percentage.||
70|N|H|js:claimsui|C:test_e3_claims_boundary_stress_blindspots|Blindspot report exported as JSON.||
71|N|F|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Thirteen methods with typed inputs and outputs.||
72|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Assumptions per method.||
73|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Version chain (e.g. WLMATCH-1 → WLMATCH-2).||
74|N|H|py:methodgenome;js:compilerui|{E}test_method_genome_is_complete_and_its_tests_exist|Which methods each method relies on.||
75|N|H|py:methodgenome;js:compilerui|C:test_e2_scientific_compiler_and_method_genome|Field-by-field comparison of two methods.||
76|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Compatible = same output quantity type.||
77|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Defined known-answer tests checked to exist.||
78|E|F|tests/unit/test_measurement.py|D:test_registration_known_answer|Known-answer tests of each method.||p7:P7-314
79|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Limitations and unsupported data per method.||
80|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Determinism coverage per method.||
81|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Per-pixel VARIANCE as input uncertainty.||
82|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Centroid, flux, position, visit and pair propagation.||
83|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Reference-ratio scatter and CALCHECK scale.||
84|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|√χ²ν inflation shown as model uncertainty.||
85|E|H|py:stability|A:test_phase3_params_and_stability|Parameter sensitivity by the stability check (never added to a σ).||p7:P7-223
86|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Stated sensitivities as output uncertainty.||
87|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Propagation method per transformation; omissions listed.||
88|N|H|py:uflow|C:test_e5_models_uncertainty_future|Units for every node.||
89|N|H|py:uflow;js:uflowui|C:test_e5_models_uncertainty_future|Edges between uncertainty nodes.||
90|N|H|js:uflowui|C:test_e5_models_uncertainty_future|Uncertainty lineage export.||
91|E|F|py:bundle|K:|Source files identified by SHA-256 in the manifest.||p7:P7-205
92|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|Fingerprints at each lineage stage.||
93|N|S|py:lineage;js:reasoningui|C:test_e1_reasoning_graph_and_lineage|Nine-stage lineage of a result.||
94|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|MJy/sr × Ω_pix → µJy recorded.||
95|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|Pixel → plate → tangent plane recorded.||
96|N|H|py:scidebug|{E}test_differential_debugging_finds_the_earliest_divergence|Processing stages compared between runs.||
97|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|Missing stages reported, never filled.||
98|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|Software recorded vs installed.||
99|N|H|py:lineage|C:test_e1_reasoning_graph_and_lineage|Analysis, method and software versions with the lineage.||
100|N|H|js:reasoningui|C:test_e1_reasoning_graph_and_lineage|Lineage report export.||
101|N|S|js:protocolui|C:test_e8_protocol_and_blind_analysis|Protocol written before the blind.||
102|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Hidden fields stated.||
103|N|S|js:main;js:protocolui|C:test_e8_protocol_and_blind_analysis|Workspaces that would show outcomes are covered; renderers not called.||
104|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Lock records whether results were visible.||
105|N|S|js:protocolui|C:test_e8_protocol_and_blind_analysis|Unblinding needs a locked protocol and typed confirmation.||
106|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Blind events in the hash-chained history.||
107|N|H|js:main;js:ruler;js:copilot|C:test_e8_protocol_and_blind_analysis|Copilot paused and ruler emphasis off while blind.||
108|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Append-only amendments with reasons.||
109|D|H|||Dedicated blind-analysis report.|Protocol export and history cover it partly.|
110|N|H|tests/e2e/test_controls.py|C:test_e8_protocol_and_blind_analysis|The blind workflow is exercised end to end in both modes.||
111|N|H|py:reprox|{E}test_reproduction_verdicts|Environment versions compared with the record.||
112|N|H|py:reprox|{E}test_reproduction_verdicts|Dependency versions recorded and compared (no lock file).|Not a full package snapshot.|
113|E|F|py:provenance_check|Q:|Inputs verified against the manifest.||p7:P7-131
114|N|H|py:reprox|{E}test_reproduction_verdicts|Method versions compared with the current code.||
115|N|H|py:reprox|{E}test_reproduction_verdicts|Recorded parameters restored.||
116|E|F|py:provenance_check|F:test_reproducibility_verdicts_and_tamper|Replay by re-execution.||p7:P7-135
117|N|H|py:reprox;py:scidebug|{E}test_reproduction_verdicts|Every stage compared numerically.||
118|N|H|py:reprox|{E}test_reproduction_verdicts|Relative tolerance 1e-9; numerically equivalent verdict.||
119|N|H|||Difference localization.||dup:25
120|N|S|js:debuggerui|C:test_e4_scientific_debugger|Five-verdict reproduction report.||
121|E|S|py:infogain|F:test_information_analysis_has_no_probabilities|Test ranking (INFO-1).||p7:P7-070
122|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Boundary items that keep claims unresolved.||
123|E|H|py:possibility|C:test_t1_discovery_horizon|Feasibility classes.||p7:P7-025
124|E|S|py:infogain|F:test_information_analysis_has_no_probabilities|Which test bears on which explanations.||p7:P7-061
125|E|H|||Test utility comparison.||dup:121
126|N|S|py:decide;js:decideui|{E}test_decisions_are_explained_and_questions_cite_their_source|Decision records with action, reasoning, evidence, inputs, limitations.||
127|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Why each item is not placed higher.||
128|D|R|||Explicit decision assumptions.|Only the ordering rule is stated.|
129|N|H|js:decideui|C:test_e6_decisions_and_questions|Recorded decisions in the session history.||
130|N|H|js:decideui|C:test_e6_decisions_and_questions|Decision record export.||
131|D|H|||Registering your own models.|Two fixed models only.|
132|N|H|py:modelarena|{E}test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|Gaussian independent errors stated.||
133|N|S|py:modelarena;js:modelsui|{E}test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|M0 static vs M1 linear on the same visits.||
134|N|H|py:modelarena|C:test_e5_models_uncertainty_future|Fitted parameters with σ.||
135|N|H|py:modelarena;js:modelsui|C:test_e5_models_uncertainty_future|Residuals per visit for both models.||
136|N|H|py:modelarena|{E}test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|χ², dof, χ²ν, Δχ², AIC.||
137|N|H|py:modelarena|C:test_e5_models_uncertainty_future|Leave-one-visit-out refits.||
138|N|H|py:modelarena|{E}test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|M1 reproduces the pipeline's fit.||
139|N|H|py:modelarena|C:test_e5_models_uncertainty_future|Better fit ≠ physical explanation; no brightness models.||
140|N|H|js:modelsui|C:test_e5_models_uncertainty_future|Model selection record export.||
141|N|S|py:session;js:sessioncore|{E}test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid|Hash-chained, append-only history.||
142|D|H|||Claim change history across runs.|Not built.|
143|E|H|py:session|S:test_version_histories_are_kept_bounded_and_hashed|Hypothesis versions.||
144|E|H|py:session|S:test_session_rules|Analysis events in the history.||p7:P7-309
145|E|H|js:counterfactualui|C:test_t2_counterfactual_lab|Scenario lineage in the session.||p7:P7-009
146|E|H|js:notebook|S:test_version_histories_are_kept_bounded_and_hashed|Annotation and notebook versions.||p7:P7-237
147|E|H|py:session|S:test_session_rules|Exports logged in the history.||p7:P7-309
148|N|S|py:session;js:sessioncore|{E}test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid|Chain verification; edits detected and refused on save.||
149|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Vault table with links and corrections.||
150|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Event history export.||
151|N|S|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Arguments start from a recorded or written claim.||
152|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Supporting evidence from the reasoning graph.||
153|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Contradicting evidence.||
154|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Assumptions linked to graph objects.||
155|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Fixed list of inference rules.||
156|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Branching.||
157|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Comparison of two arguments.||
158|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Evidence statuses shown per argument.||
159|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Challenges to individual steps with status.||
160|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Markdown argument map with validity and empirical standing.||
161|N|S|py:integrity;js:epistemiccore|{E}test_integrity_firewall_flags_problems_without_rewriting|Asserted outcomes checked against the record (I4).||
162|N|S|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Synthetic disclosure (I1).||
163|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Numbers without units (I5).||
164|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Record hash recomputes (I9).||
165|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|The run is cited (I3).||
166|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Probability language (I6).||
167|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Unregistered method identifiers (I11).||
168|N|H|py:integrity|{E}test_integrity_firewall_flags_problems_without_rewriting|Limitations acknowledged (I8).||
169|N|S|py:integrity;js:integrityui|C:test_e7_negative_space_and_integrity|Ready / with warnings / needs attention; never blocks or rewrites.||
170|N|H|js:integrityui|C:test_e7_negative_space_and_integrity|Readiness report export.||
171|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Questions from DISC-1 and HYPO-1.||
172|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Questions from unresolved boundary items.||
173|N|H|py:decide|C:test_e6_decisions_and_questions|Testable with current inputs.||
174|N|H|py:decide|C:test_e6_decisions_and_questions|Partially answerable.||
175|N|H|py:decide|C:test_e6_decisions_and_questions|Requires additional data.||
176|N|H|py:decide|C:test_e6_decisions_and_questions|Requires a new method.||
177|N|H|py:decide;py:futurelab|C:test_e6_decisions_and_questions|Hypothetical questions from FutureLab.||
178|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Every question cites what prompted it.||
179|D|H|||Ranking questions.|Listed by category only.|
180|D|H|||Question history.|Not built.|
181|N|S|||Protocol creation.||dup:101
182|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Primary and alternative hypotheses recorded before locking.||
183|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Selected inputs recorded.||
184|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Exclusion criteria.||
185|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Planned parameters.||
186|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Expected outcome per question.||
187|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Planned robustness tests.||
188|N|S|js:protocolui|C:test_e8_protocol_and_blind_analysis|Lock with content hash and time; not called preregistration.||
189|N|H|||Protocol amendments (protocols).||dup:108
190|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Planned vs actual parameters and outcomes.||
191|E|H|py:possibility|C:test_t1_discovery_horizon|Opportunity map.||p7:P7-028
192|E|H|py:possibility|C:test_t1_discovery_horizon|Evidence that prompted each opportunity.||p7:P7-022
193|N|H|||Method dependencies.||dup:74
194|E|H|py:possibility|F:test_possibility_layers_and_horizon_cards|Missing inputs per question.||p7:P7-024
195|E|H|js:horizonui;js:decideui|C:test_e6_decisions_and_questions|Question hand-off to the Planner.||p7:X29
196|E|H|py:planner|R:test_planner_known_plans|Plans of registered actions.||p7:P7-082
197|D|R|||Validity of a path through the map.|Connections are not inferences; not checked.|
198|D|R|||Opportunity comparison.|Not built.|
199|D|R|||Map provenance.|Not built.|
200|E|H|js:horizonui|C:test_t1_discovery_horizon|Opportunity export.||p7:P7-030
201|D|H|||Pixel values.|The preview carries images, not pixel arrays.|
202|E|H|js:explorer|C:test_b_explorer_controls|Measurement inspection.||p7:P7-353
203|E|H|js:explorer|C:test_b_explorer_controls|Observation metadata and provenance.||p7:P7-323
204|E|H|js:discovery|C:test_l_discovery_engine|Investigation-level inspection.||
205|E|H|js:kg|C:test_p_vault_and_studio|Links to other saved investigations.||
206|E|H|js:ruler|C:test_b_explorer_controls|Selection shared between ruler and views.||p7:P7-352
207|N|H|js:compilerui;js:claimsui|C:test_e2_scientific_compiler_and_method_genome|Cited objects open in the reasoning graph.||
208|N|H|js:reasoningui|C:test_e1_reasoning_graph_and_lineage|Focus on one object and its trace.||
209|E|F|js:state|C:test_s2_planner_plans_runs_and_persists|URL and session state kept.||p7:P7-291
210|D|H|||Multi-scale exports.|Not built.|
211|N|H|py:simcheck|C:test_e9_reasoning_lab_and_phase8_tabs|Generator and version in the audit.||
212|E|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Seeds recorded.||p7:P7-042
213|E|F|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Ground truth recorded.||p7:P7-043
214|N|H|py:simcheck|C:test_e9_reasoning_lab_and_phase8_tabs|Noise assumptions stated.||
215|N|H|py:simcheck|C:test_e9_reasoning_lab_and_phase8_tabs|Simplifications stated.||
216|N|H|py:simcheck|C:test_e9_reasoning_lab_and_phase8_tabs|Validity domain from the scenario bounds.||
217|N|S|py:simcheck|C:test_e9_reasoning_lab_and_phase8_tabs|Same scenario, three seeds: verdict stability.||
218|D|R|||Boundary tests near sensitivity.|Not built.|
219|E|H|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|Recovery against truth.||p7:P7-181
220|N|H|py:simcheck;js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Simulation audit view.||
221|N|H|py:reviewx|{E}test_review_board_links_every_item|Data-integrity perspective.||
222|N|H|py:reviewx|{E}test_review_board_links_every_item|Method perspective with genome health.||
223|N|H|py:reviewx|{E}test_review_board_links_every_item|Statistical perspective.||
224|N|H|py:reviewx|{E}test_review_board_links_every_item|Uncertainty perspective.||
225|N|H|py:reviewx|{E}test_review_board_links_every_item|Provenance perspective.||
226|E|H|py:review|F:test_review_findings_cite_sources|Reproducibility review.||p7:P7-114
227|E|H|py:review|F:test_review_findings_cite_sources|Interpretation review.||p7:P7-115
228|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Your comments on each item.||
229|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Responses and resolution on each item.||
230|E|H|js:reviewui|C:test_t8_review_room_repro_story|Review export.||p7:P7-120
231|N|H|py:futurelab|{E}test_futurelab_formula_is_validated_before_scenarios|One more visit at a chosen time.||
232|N|H|py:futurelab|{E}test_futurelab_formula_is_validated_before_scenarios|Flux error needed for a given change.||
233|N|H|py:futurelab|C:test_e5_models_uncertainty_future|Number of visits over the same baseline.||
234|N|H|py:futurelab|{E}test_futurelab_formula_is_validated_before_scenarios|Longer baselines.||
235|N|H|py:futurelab|C:test_e5_models_uncertainty_future|Which missing input unblocks what.||
236|D|H|||Comparing future tests.|Not built.|
237|N|H|||Hypothetical data requirements.||dup:235
238|N|H|py:futurelab|{E}test_futurelab_formula_is_validated_before_scenarios|Assumptions with every scenario; validated formula first.||
239|E|H|py:synthobs|F:test_observation_design_compares_schedules|Schedule comparison.||p7:X25
240|D|H|||Scenario report export.|Kept in the session history only.|
241|D|H|||Copilot routing by epistemic object.|Copilot tools do not read the epistemic report.|
242|D|H|||Copilot answers citing claim lineage.|Not built.|
243|D|H|||Copilot assumption explanations.|Not built.|
244|E|H|py:ai/local|T:|Limitations in every copilot answer.||
245|D|H|||Copilot explaining compilation.|Not built.|
246|D|H|||Copilot debugging assistance.|Not built.|
247|D|H|||Copilot question generation.|Question Forge is deterministic.|
248|D|H|||Copilot method comparison.|Not built.|
249|D|H|||Copilot review assistance.|Not built.|
250|E|H|js:copilot;js:notebook|C:test_h2_copilot_sources_drafts_and_plan|Labelled drafts from tool outputs.||p7:P7-265
251|E|F|py:session|S:test_session_rules|Sessions as state snapshots.||p7:P7-291
252|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Branching.||p7:P7-151
253|E|H|js:session|C:test_s2_planner_plans_runs_and_persists|Restoration.||p7:P7-291
254|D|H|||Comparing two sessions.|Not built.|
255|E|F|py:session|S:test_browser_matches_python|Validation.||p7:P7-303
256|E|F|py:session|S:test_migration_from_v05_saved_record|Migrations; v0.7 sessions valid in 0.8.||p7:X18
257|E|H|py:session|S:test_session_rules|History records provenance.||p7:P7-309
258|E|F|py:session|S:test_browser_matches_python|Content hash (plus the 0.8 chain).||p7:P7-308
259|E|F|js:session|C:test_s2_planner_plans_runs_and_persists|Recovery.||p7:P7-291
260|E|F|js:sessionsui|C:test_s9_sessions_dialog_export_import|Export.||p7:P7-159
261|E|H|py:quality|R:test_quality_outcomes_and_injected_defects|Eleven DQ rules.||
262|E|F|py:quality|R:test_quality_outcomes_and_injected_defects|Unit checks.||p7:P7-174
263|E|H|py:quality|R:test_quality_outcomes_and_injected_defects|Metadata checks.||p7:P7-175
264|E|H|py:quality|R:test_quality_outcomes_and_injected_defects|Calibration metadata.||
265|E|F|py:quality|R:test_quality_outcomes_and_injected_defects|File integrity.||p7:P7-299
266|E|F|py:compat|R:test_matrix_is_the_logged_decisions|Compatibility.||p7:P7-179
267|E|H|py:discovery|D:test_inventory_traces_to_manifest_and_counts_unknowns|Unknowns counted, never filled.||
268|D|H|||Quality-rule history.|Not built.|
269|D|H|||Quality comparison between runs.|Not built.|
270|E|H|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Quality report.||p7:P7-277
271|N|H|py:claims|{E}test_claim_stress_modes_and_results|Error-model and fit-quality checks.||
272|N|H|py:modelarena|{E}test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|Fit diagnostics per model.||
273|N|H|py:modelarena|C:test_e5_models_uncertainty_future|Residual analysis.||
274|E|H|py:stability|A:test_phase3_params_and_stability|Sensitivity analysis.||p7:P7-223
275|E|H|py:experiments|R:test_experiment_validation_and_negative_control|Robustness at bounds.||p7:P7-225
276|D|R|||Identifiability checks.|Not applicable to the two linear fits here; not built.|
277|D|R|||Numerical stability.|Not built.|
278|N|H|||Model comparison (statistics).||dup:133
279|D|R|||Diagnostic lineage.|Not built.|
280|N|H|js:claimsui;js:modelsui|C:test_e3_claims_boundary_stress_blindspots|Stress and model reports.||
281|N|H|py:epistemic|C:test_e1_reasoning_graph_and_lineage|Observations as graph objects with metadata.||
282|N|H|py:epistemic|{E}test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims|Forward trace from an observation.||
283|E|F|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits|Epoch compatibility.||p7:P7-173
284|X|R|||Instrument compatibility.|One instrument.|
285|E|F|py:science/wavelength|W:|Channel compatibility.||p7:P7-172
286|E|H|py:compat|C:test_s3_quality_matrix_metadata_sequences|Coverage gaps.||p7:P7-055
287|E|F|py:science/wavelength|W:|Pairing.||p7:P7-172
288|E|H|py:quality|R:test_quality_outcomes_and_injected_defects|Observation quality.||
289|D|H|||Observation history.|Not built.|
290|E|H|js:records|C:test_g_records_controls|Observation inventory export.||p7:P7-280
291|E|S|js:timemachine|C:test_s3_quality_matrix_metadata_sequences|Multi-epoch comparison.||p7:P7-191
292|E|H|py:compat|C:test_s3_quality_matrix_metadata_sequences|Temporal coverage.||p7:P7-055
293|E|R|py:synthobs|F:test_observation_design_compares_schedules|Sampling analysis.||p7:P7-194
294|E|H|py:radar|R:test_radar_items_are_explained_and_ranked_by_the_stated_rule|Time gaps.||p7:P7-192
295|E|H|js:figurestudio|C:test_s10_figure_studio|Positions against time.||p7:P7-196
296|E|F|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits|Sequence compatibility.||p7:P7-197
297|N|H|py:uflow|{E}test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions|Visit-mean σ in the uncertainty flow.||
298|E|H|js:figurestudio|C:test_s10_figure_studio|Temporal residuals.||p7:P7-196
299|D|H|||Animation provenance.|Not built.|
300|D|H|||Temporal report.|Not built.|
301|D|H|||Pixel profiles.|Not built.|
302|D|H|||Region statistics.|Not built.|
303|D|H|||Background diagnostics.|Not built.|
304|E|S|py:view|D:test_registration_on_fixture_pairs|Registration diagnostics.||p7:P7-217
305|N|H|py:lineage|{E}test_lineage_refers_only_to_recorded_stages|Image transformations in the lineage.||
306|E|H|js:viewer|C:test_b_explorer_controls|Masks.||p7:P7-215
307|D|H|||Residual maps.|Not built.|
308|E|F|py:science/wavelength|W:|Image compatibility.||p7:P7-172
309|E|F|py:analysis|Q:|Processing history.||p7:P7-220
310|E|F|py:provenance|Q:|Image provenance.||
311|E|H|py:workflows|R:test_workflow_validation|Workflow templates.||p7:P7-361
312|E|F|py:capabilities|F:test_registry_permissions_cover_every_action|Capability validation.||p7:P7-083
313|E|F|py:capabilities|F:test_registry_permissions_cover_every_action|Permissions.||p7:P7-305
314|E|H|js:autopilotui|C:test_t5_research_autopilot|Execution records.||p7:P7-090
315|E|H|js:autopilotui|C:test_t5_research_autopilot|Cancellation.||p7:P7-088
316|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Retry.||p7:P7-295
317|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Per-task errors.||p7:P7-367
318|D|H|||Workflow branching.|Not built.|
319|E|H|py:workflows|R:test_browser_planner_missions_workflows_match_python|Workflow reproducibility.||p7:P7-370
320|E|H|js:experimentsui|C:test_s8_experiments_and_workflows|Workflow export.||p7:P7-368
321|E|S|js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Structured search.||p7:P7-106
322|E|H|js:kg|C:test_p_vault_and_studio|Related investigations.||p7:P7-103
323|E|H|js:kg|C:test_p_vault_and_studio|Method relationships.||p7:P7-102
324|E|H|js:kg|C:test_p_vault_and_studio|Target relationships.||p7:P7-104
325|D|H|||Evidence reuse across investigations.|Not built.|
326|D|H|||Knowledge collections.|Not built.|
327|D|H|||Knowledge history.|Not built.|
328|D|H|||Research path saving.|Not built.|
329|E|H|js:knowledgeui|C:test_t7_knowledge_atlas_and_twins|Search hits name their source.||p7:X37
330|E|H|js:records|C:test_p_vault_and_studio|Knowledge export.||p7:P7-110
331|X|R|||Review assignments.|No accounts.|
332|X|R|||Reviewer identity.|No accounts; comments say 'you'.|
333|E|H|js:adversarialui|C:test_t3_adversarial_lab|Evidence comments.||p7:P7-263
334|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Comments on claim-linked review items.||
335|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Resolved marker per item.||
336|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Review comments kept in the session.||
337|E|H|scripts/build_static.py|P:|Read-only sharing.||p7:P7-261
338|D|H|||Conflict detection.|Last save wins.|
339|X|R|||Review permissions.|No accounts.|
340|E|H|js:notebook|N:test_zipstore_output_is_valid_and_deterministic|Review packages.||p7:P7-268
341|N|S|py:report|{E}test_integrity_firewall_flags_problems_without_rewriting|The investigation report now states outcomes, criteria, sensitivities and limitations.||
342|E|H|scripts/gen_research_methods.py|D:test_registry_names_only_real_methods_and_tests|Methods reports.||p7:P7-272
343|E|H|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Evidence (ledger) report.||p7:P7-260
344|N|H|js:uflowui|C:test_e5_models_uncertainty_future|Uncertainty report.||
345|N|H|js:debuggerui|C:test_e4_scientific_debugger|Reproduction report.||
346|N|H|||Integrity reports (reporting).||dup:170
347|E|F|js:figurestudio|C:test_s10_figure_studio|Figure provenance.||p7:P7-137
348|E|H|js:reviewui|C:test_t8_review_room_repro_story|Narratives.||p7:P7-121
349|E|F|js:records|C:test_g_records_controls|Machine-readable packages.||p7:P7-280
350|N|H|||Report validation.||dup:169
351|N|H|js:palette|C:test_k_palette_help_shortcuts|Phase 8 terms in the glossary.||
352|E|H|js:discovery|C:test_l_discovery_engine|Contextual explanations.||p7:P7-282
353|N|H|js:uflowui;js:reasoningui|C:test_y_accessible_names|Graph objects reachable as buttons; flow nodes by keyboard.||
354|N|H|js:reasoningui|C:test_e1_reasoning_graph_and_lineage|The reasoning graph as layered lists, not only a picture.||
355|N|H|js:reasoningui|C:test_e1_reasoning_graph_and_lineage|Text summary of every trace.||
356|E|F|web/css/app.css|X:test_primary_button_text_contrast|Text tokens meet WCAG AA contrast on every surface.|No separate high-contrast theme; the default theme is tested instead.|
357|E|F|web/css/app.css|X:test_reduced_motion_disables_animation|Reduced motion.||p7:P7-289
358|E|H|js:main|C:test_j_levels|Explore level.||p7:P7-290
359|E|H|js:main|C:test_j_levels|Research level.||p7:P7-290
360|E|F|js:figurestudio|C:test_s10_figure_studio|Accessible figure exports.||
361|E|F|py:connectors|R:test_connector_previews_match_acquisition_and_send_nothing|Connector validation.||p7:P7-202
362|E|F|py:fitsio|K:|Response validation.||p7:P7-208
363|E|F|py:bundle|K:|Download checksums.||p7:P7-205
364|E|F|py:archive/acquire|K:|Release metadata.||p7:P7-209
365|E|H|py:archive/net|R:test_retry_after_is_honoured_and_bounded|Rate limits.||p7:P7-207
366|E|F|py:provenance|Q:|Acquisition provenance.||p7:P7-204
367|E|H|py:archive/net|R:test_retry_after_is_honoured_and_bounded|Retry history.||p7:P7-207
368|E|F|py:server/frontier|A:test_phase7_frontier_counterfactual_reproduce_synthetic|Cache reused only after checksum verification.||p7:P7-292
369|E|F|scripts/diagnose_environment.py|K:|External error diagnostics.||p7:P7-206
370|E|F|py:archive/acquire|K:|Acquisition audit.||p7:P7-210
371|E|F|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Import validation.||p7:P7-301
372|E|F|py:workflows|R:test_workflow_validation|Workflows never auto-run.||p7:P7-307
373|E|F|py:server/app|A:test_rejects_traversal|Path validation.||p7:P7-302
374|E|F|py:ai/meta_client|tests/unit/test_report_ai.py|Credentials only in the environment.||p7:P7-304
375|E|F|py:capabilities|F:test_registry_permissions_cover_every_action|Permission boundaries.||p7:P7-305
376|E|F|py:fitsio|K:|Untrusted responses validated.||p7:P7-306
377|E|F|js:util|C:test_z_no_external_requests_no_errors|Reports rendered as text nodes under a strict CSP.||p7:P7-310
378|E|H|py:session|S:test_session_rules|Audit history (hash-chained in 0.8).||p7:P7-309
379|B|R|||Dependency review.|Blocked: PyPI and OSV refused (403).|
380|E|F|tests/integration/test_api.py|A:test_rejects_traversal|Security tests.||p7:P7-310
381|E|F|py:server/app|A:test_status_and_security_headers|Startup diagnostics.||p7:P7-294
382|E|F|scripts/diagnose_environment.py|K:|Dependency diagnostics.||p7:P7-293
383|D|H|||Memory management.|Not built.|
384|E|H|scripts/measure_performance.py|scripts/measure_performance.py|Image performance measured.||
385|N|H|scripts/measure_performance.py|scripts/measure_performance.py|Epistemic report and Phase 8 workspaces measured.||
386|D|R|||Large sessions.|Not tested beyond the fixtures.|
387|D|H|||Export performance.|Not measured.|
388|E|F|py:archive/net|O:test_full_workflow_without_network|Offline diagnostics.||p7:P7-298
389|E|F|js:session|C:test_s2_planner_plans_runs_and_persists|Recovery.||p7:P7-291
390|E|F|scripts/make_release.py|scripts/verify.py|Release integrity.||p7:P7-300
391|E|F|py:synthetic|O:test_expected_outcomes_on_synthetic_truth|Known-answer datasets.||p7:P7-311
392|E|F|py:synthetic|O:test_expected_outcomes_on_synthetic_truth|Golden fixtures.||p7:P7-311
393|E|F|tests/js|{E}test_browser_epistemic_functions_match_python|Cross-language parity, extended to Phase 8.||p7:P7-313
394|E|F|py:canon|S:test_js_number_rules|Numerical boundaries.||p7:P7-315
395|D|H|||Property-based testing.|No property-testing library installed.|
396|E|F|docs/TEST_REPORT.md|scripts/verify.py|Scientific regression gates.||p7:P7-320
397|E|F|py:uncertainty|D:test_uncertainty_recomputes_logged_values_exactly|Uncertainty validation.||p7:P7-317
398|E|F|py:provenance_check|Q:|Provenance validation.||p7:P7-131
399|N|H|py:reprox|{E}test_reproduction_verdicts|Reproduction verdicts tested, including tampered and blocked cases.||
400|N|H|py:methodgenome|{E}test_method_genome_is_complete_and_its_tests_exist|Known-answer tests per method verified to exist.||
401|D|R|||Hypothesis dependencies.|Not built.|
402|E|S|py:hypotheses|D:test_hypotheses_known_answers|Competing explanations.||p7:P7-375
403|D|R|||Contradictory predictions.|Not built.|
404|E|F|py:hypotheses|D:test_hypotheses_never_produce_probabilities_and_use_known_statuses|Evidence requirements per test.||p7:P7-078
405|N|H|||Falsification records.||dup:58
406|E|H|py:session|S:test_version_histories_are_kept_bounded_and_hashed|Hypothesis revision.||
407|E|H|js:sessionsui|C:test_s9_sessions_dialog_export_import|Hypotheses branch with the session.||p7:P7-151
408|E|S|js:arena|C:test_m_hypothesis_arena|Hypothesis comparison.||p7:P7-372
409|E|H|||Hypothesis history (research).||dup:143
410|E|H|js:records|C:test_g_records_controls|Hypothesis export.||p7:P7-274
411|E|S|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Input exclusion scenarios.||p7:P7-004
412|E|S|py:counterfactual|C:test_t2_counterfactual_lab|Parameter scenarios.||p7:P7-003
413|E|S|js:counterfactualui|C:test_t2_counterfactual_lab|Scenario comparison.||p7:P7-008
414|E|F|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled|Baseline preserved.||p7:P7-002
415|E|H|js:counterfactualui|C:test_t2_counterfactual_lab|Scenario lineage.||p7:P7-009
416|E|F|py:counterfactual|F:test_reassessment_without_change_reproduces_the_record|Exact re-assessment.||p7:X02
417|E|H|py:counterfactual|C:test_t2_counterfactual_lab|Threshold scenarios.||p7:P7-006
418|E|H|js:counterfactualui|C:test_t2_counterfactual_lab|Changed outputs highlighted.||p7:P7-008
419|E|F|py:counterfactual|F:test_counterfactual_validation_refuses|Validation refusals.||p7:X35
420|E|H|js:counterfactualui|C:test_t2_counterfactual_lab|Export.||p7:P7-010
421|E|H|py:twin|F:test_twins_integrity_and_comparison|Observation twin.||p7:P7-011
422|E|H|py:twin|F:test_twins_integrity_and_comparison|Target twin.||p7:P7-012
423|E|H|py:twin|C:test_t7_knowledge_atlas_and_twins|Analysis twin.||p7:P7-013
424|E|H|py:twin|A:test_phase7_frontier_counterfactual_reproduce_synthetic|Scenario twin.||p7:P7-014
425|E|H|js:frontiercore|F:test_browser_twin_and_coordinates_match_python|Investigation twin.||p7:P7-015
426|D|H|||Twin versioning.|Version 1 only.|
427|E|S|py:twin|F:test_browser_overlays_match_python|Twin comparison.||p7:P7-017
428|E|F|py:twin|F:test_twins_integrity_and_comparison|Twin derivation hashes.||p7:P7-018
429|D|R|||Twin restoration.|Not built.|
430|E|F|py:twin|F:test_twins_integrity_and_comparison|Twin integrity.||p7:P7-020
431|E|S|py:infogain|F:test_information_analysis_has_no_probabilities|Test discrimination.||p7:P7-061
432|E|S|py:infogain|F:test_information_analysis_has_no_probabilities|Hypothesis separation.||p7:P7-070
433|E|F|py:infogain|C:test_t3_adversarial_lab|Information assumptions stated.||p7:P7-063
434|E|S|py:possibility|F:test_browser_overlays_match_python|Evidence-gap ranking.||p7:P7-026
435|E|S|||Candidate measurement comparison.||dup:431
436|D|R|||Decision analysis with outcome probabilities.|No defensible probabilities exist.|
437|E|H|py:possibility|F:test_possibility_layers_and_horizon_cards|Sensitivity-driven planning.||p7:P7-064
438|E|F|py:infogain|F:test_information_analysis_has_no_probabilities|Information method validation.||p7:P7-069
439|N|H|||Research action comparison.||dup:127
440|D|H|||Information report export.|Not built.|
441|N|H|py:scidebug;js:debuggerui|C:test_e4_scientific_debugger|Inferences inspected with recomputation.||
442|N|H|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Parameters recorded and methods documented.||
443|N|H|||Evidence sufficiency (reasoning).||dup:38
444|N|H|py:scicomp|{E}test_compiler_runs_every_stage_and_states_the_precedence_rule|Absence claims bounded by stated sensitivity.||
445|N|H|py:scicomp;py:claims|{E}test_knowledge_boundary_rules|Contradictions place claims in the unresolved region.||
446|N|H|||Unsupported language detection.||dup:48
447|E|H|py:adversarial|F:test_adversarial_rules_and_statuses|Alternative interpretations.||p7:P7-035
448|D|H|||Reasoning history.|Not built.|
449|N|H|||Argument comparison (reasoning).||dup:157
450|N|H|||Reasoning quality reports.||dup:20
451|N|H|||Decision records (history).||dup:126
452|N|H|||Decision alternatives.||dup:127
453|D|R|||Decision assumptions (history).||dup:128
454|D|R|||Decision dependencies.|Not built.|
455|D|H|||Decision revisions.|Not built.|
456|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Ranking reason per recommendation.||
457|D|H|||Decision comparison.|Not built.|
458|N|H|py:decide|{E}test_decisions_are_explained_and_questions_cite_their_source|Evidence used per recommendation.||
459|N|H|||Decision audit.||dup:129
460|N|H|||Decision exports.||dup:130
461|D|H|||Method walkthroughs.|Not built.|
462|D|H|||Reasoning tutorials.|Not built.|
463|D|H|||Interactive assumptions.|Not built.|
464|D|H|||Evidence interpretation lessons.|Not built.|
465|D|H|||Uncertainty demonstrations.|Not built.|
466|D|H|||Counterfactual exercises.|Not built.|
467|D|H|||Debugging tutorials.|Not built.|
468|D|H|||Reproducibility exercises.|Not built.|
469|E|H|py:missions|R:test_missions_read_completion_from_the_session|Mission templates.||p7:P7-241
470|E|H|py:session|C:test_s1_command_center_session_and_mission|Mission progress records.||p7:P7-246
471|D|H|||Investigation queues.|Not built.|
472|D|H|||Research milestones.|Not built.|
473|E|H|py:missions|R:test_missions_read_completion_from_the_session|Evidence task lists.||p7:P7-245
474|D|H|||Review queues.|Not built.|
475|D|H|||Experiment queues.|Not built.|
476|E|F|py:planner|R:test_planner_known_plans|Blocked steps say why.||p7:P7-084
477|E|H|js:autopilotui|C:test_t5_research_autopilot|Execution history.||p7:P7-090
478|X|R|||Research scheduling.|Skytrace schedules nothing.|
479|D|H|||Progress snapshots.|Not built.|
480|D|H|||Operation reports.|Not built.|
481|E|F|py:schema|S:test_browser_matches_python|Versioned JSON schemas.||p7:P7-303
482|D|R|||FITS metadata exchange.|Not built.|
483|D|R|||VOTable export.|Not built.|
484|D|H|||Standardised measurement exports.|Record JSON only.|
485|D|R|||Provenance exchange (e.g. W3C PROV).|Not built.|
486|E|F|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Package import.||p7:P7-301
487|E|F|py:package|D:test_package_is_deterministic_and_self_verifying|Package export.||p7:P7-260
488|E|F|py:session|S:test_migration_from_v05_saved_record|Schema compatibility.||p7:X18
489|E|F|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors|Citation registry of real datasets.||
490|D|H|||Interoperability reports.|Not built.|
491|N|S|||Scientific reasoning compilation.||dup:20
492|N|S|||Scientific investigation debugging.||dup:21
493|N|S|||Knowledge boundary exploration.||dup:10
494|N|S|||Claim stress testing.||dup:50
495|N|S|||Negative knowledge preservation.||dup:51
496|N|S|||Blindspot detection.||dup:69
497|N|S|||Method genome.||dup:71
498|N|S|||Uncertainty lineage.||dup:87
499|N|S|||Scientific integrity firewall.||dup:169
500|N|S|py:epistemic;py:scicomp;py:reprox|C:test_e4_scientific_debugger|A claim traced to its files, compiled, stress-tested and re-executed with a graded verdict.||
"""

EXTRA = """
X01|N|F|py:epistemic|E:test_asserted_words_ignore_negated_uses|Negation-aware wording rule|"not proof", "no evidence of a discovery" are not assertions; same sentence, four words.
X02|N|F|py:epistemic|E:test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses|Procedures carry no epistemic status|Transformations and methods are not statements.
X03|N|F|py:epistemic|E:test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses|Synthetic sources are 'simulated' (S1)|Generated files never appear as directly recorded.
X04|N|H|py:report|E:test_integrity_firewall_flags_problems_without_rewriting|Report states units encoded in result keys|Sensitivities rendered with mas/yr, yr, (fraction).
X05|N|F|py:scicomp|E:test_review_board_links_every_item|Every compiler check cites what it examined|A sample of the objects checked when nothing failed.
X06|N|F|py:scidebug|E:test_debugger_breakpoints_are_real_stages_and_recompute_exactly|Recomputation agreement classes|Identical, within tolerance, different, not computable.
X07|N|H|py:scidebug|E:test_browser_epistemic_functions_match_python|Language-independent value briefs|Debugger output identical in Python and the browser.
X08|N|F|py:integrity|E:test_integrity_firewall_flags_problems_without_rewriting|Grounding at the precision written|A number matches if a recorded value rounds to it.
X09|N|H|py:integrity|E:test_integrity_firewall_flags_problems_without_rewriting|Fenced data blocks exempt from the unit check|Keys carry their units there.
X10|N|H|py:negspace|E:test_negative_knowledge_registry_records_what_failed|Unreachable services from the environment report|Hosts that answered are not listed.
X11|N|F|py:session|E:test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid|Chain anchor after trimming|The first retained entry is reported as unverifiable, not as broken.
X12|N|F|py:session|E:test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid|0.7 sessions stay valid|Links are filled on the next save.
X13|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Blind commitment hash|SHA-256 of the hidden values, compared at unblinding.
X14|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|'Locked after results were visible' label|A late lock is never presented as a pre-analysis plan.
X15|N|H|js:protocolui|C:test_e8_protocol_and_blind_analysis|Amendments flagged when results were visible|Post-hoc changes are marked.
X16|N|F|py:reprox|E:test_reproduction_verdicts|Record integrity required for exact reproduction|An edited record cannot reproduce exactly.
X17|N|H|py:reprox|E:test_reproduction_verdicts|Documented differences need a recorded cause|Software, parameters or inputs.
X18|N|H|py:futurelab|E:test_futurelab_formula_is_validated_before_scenarios|Validation gate before scenarios|No scenario unless the formula reproduces the fit.
X19|N|H|js:futureui|C:test_e5_models_uncertainty_future|Interactive scenario calculator|Same formula in the browser, labelled hypothetical.
X20|N|H|py:modelarena|E:test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit|No p-values in model comparison|Criteria without probabilities.
X21|N|H|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs|Validity separated from empirical standing|Two verdicts per argument.
X22|N|H|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs|Corrections that point at old entries|Nothing is rewritten.
X23|N|H|py:simcheck|E:test_simulation_audit_refuses_invalid_scenarios|Audit refuses invalid scenarios|Same bounds as the generator.
X24|N|H|js:claimsui|C:test_e4_scientific_debugger|Session reproduction settles the stress mode|Recorded verdict used, same rule.
X25|N|H|js:main|C:test_e8_protocol_and_blind_analysis|Blind cover over workspaces|The renderer is not called.
X26|N|H|js:copilot|C:test_e8_protocol_and_blind_analysis|Copilot paused while blind|Its answers would reveal outcomes.
X27|N|H|js:ruler|C:test_e8_protocol_and_blind_analysis|Ruler emphasis off while blind|Significant pairs are not bolded.
X28|N|H|web/index.html|C:test_y_accessible_names|Navigation in the eight Phase 8 modes|Observatory · Evidence · Analyze · Challenge · Experiment · Plan · Knowledge · Publish.
X29|N|H|js:compilerui|C:test_e2_scientific_compiler_and_method_genome|Compiler filters by stage and outcome|Checks listed with their rules.
X30|N|H|py:server/epistemic|A:test_phase8_epistemic_reproduce_integrity|One cached epistemic report per record|Built once, served to every Phase 8 workspace.
X31|N|H|scripts/build_static.py|C:test_e1_reasoning_graph_and_lineage|Static preview records epistemic reports|Every recorded run has its report.
X32|N|H|py:server/epistemic|A:test_phase8_epistemic_reproduce_integrity|Lineage of any comparison on demand|Server route; claims and fit recorded for the preview.
X33|N|H|py:methodgenome|E:test_method_genome_is_complete_and_its_tests_exist|Unit vocabulary for type checking|Quantity types with units.
X34|N|H|py:decide|C:test_e6_decisions_and_questions|Questions hand off to the Planner|Plan this question.
X35|N|H|js:negativeui|C:test_e7_negative_space_and_integrity|Your own negative-knowledge entries|Kept in the session.
X36|N|H|js:integrityui|C:test_e7_negative_space_and_integrity|Check the notebook or pasted text|Same rules as for the report.
X37|D|H|||Copilot access to Phase 8 results|The copilot's tools do not yet read the epistemic report.
X38|N|F|scripts/phase8_catalogue.py|tests/unit/test_phase8_catalogue.py|Catalogue deduplicated against Phase 7|Existing concepts cite their Phase 7 entry.
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
    k = v.split(":", 1)[0]
    if ":" in v and k in TESTS:
        name = v.split(":", 1)[1]
        return TESTS[k] + (f"::{name}" if name else "")
    return v


def _deps(evidence):
    return sorted({p.split("/")[-1].replace(".py", "").replace(".js", "") for p in evidence if p.startswith(("src/", "web/js/"))})


def build() -> dict:
    names = [n for line in NAMES.strip().split("\n") for n in line.split("|")]
    assert len(names) == 500, len(names)
    items = []
    for line in ROWS.strip().split("\n"):
        n, st, grp, ev, ver, desc, lim, ref = (line.split("|") + [""] * 8)[:8]
        n = int(n)
        d = (n - 1) // 10
        dup = ref[4:] if ref.startswith("dup:") else None
        p7 = ref[3:] if ref.startswith("p7:") else None
        if p7 and not p7.startswith("P7-"):
            p7 = "P7-" + p7
        evidence = [_path(p) for p in ev.split(";") if p]
        items.append({"id": f"P8-{n:03d}", "number": n, "domain": DOMAINS[d], "name": names[n - 1], "description": desc,
                      "user_value": f"to {USER_VALUE[d]}", "scientific_value": SCI_VALUE[d], "dependencies": _deps(evidence),
                      "status": STATUS[st], "status_code": st, "group": GROUP[grp], "priority": "—" if st == "X" else PRIORITY[grp],
                      "evidence": evidence, "verification": _ver(ver),
                      "limitations": lim or ("Not built in 0.8; nothing claims it." if st == "D" else ""), "phase7": p7,
                      "duplicate_of": f"P8-{int(dup):03d}" if dup else None, "source": "brief"})
    for line in EXTRA.strip().split("\n"):
        xid, st, grp, ev, ver, name, desc = line.split("|")
        evidence = [_path(p) for p in ev.split(";") if p]
        items.append({"id": f"P8-{xid}", "number": None, "domain": "Added by this project", "name": name, "description": desc,
                      "user_value": "a more reliable epistemic layer", "scientific_value": "keeps statements, checks and exports honest", "dependencies": _deps(evidence),
                      "status": STATUS[st], "status_code": st, "group": GROUP[grp], "priority": PRIORITY[grp], "evidence": evidence, "verification": _ver(ver),
                      "limitations": "Not built in 0.8." if st == "D" else "", "phase7": None, "duplicate_of": None, "source": "project"})
    distinct = [x for x in items if not x["duplicate_of"]]
    counts = {"rows": len(items), "brief_concepts": 500, "merged_synonyms": len(items) - len(distinct), "added": len(EXTRA.strip().split("\n")),
              "distinct": len(distinct), "domains": len(DOMAINS), "carried_from_phase7": sum(1 for x in distinct if x["phase7"]),
              "by_status": {STATUS[k]: sum(x["status_code"] == k for x in distinct) for k in STATUS},
              "by_group": {g: sum(x["group"] == g for x in distinct) for g in GROUP.values()},
              "implemented": sum(x["status_code"] in "EN" for x in distinct)}
    return {"schema": "skytrace.phase8_catalogue/1", "statuses": STATUS, "groups": GROUP, "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    out = ["# Skytrace Phase 8 capability catalogue", "",
           "Generated by `python scripts/phase8_catalogue.py`; every count is computed. Checked by `tests/unit/test_phase8_catalogue.py` "
           "(500 brief concepts in 50 domains, ≥ 500 distinct, every cited file, test function and Phase 7 entry exists, deferred items cite nothing, "
           "synonyms point to counted concepts).", "",
           "Concepts and domains are those of the Phase 8 brief (§26). Existing concepts keep the status **existing** and cite their Phase 7 entry; "
           "they are not counted as new. Proposed, implemented, blocked and deferred capabilities are listed separately by status.", "",
           f"**{c['distinct']} distinct concepts** ({c['brief_concepts']} from the brief − {c['merged_synonyms']} merged + {c['added']} added) in "
           f"{c['domains']} domains; {c['carried_from_phase7']} cite a Phase 7 entry. Status: " + ", ".join(f"{v} {k}" for k, v in c["by_status"].items()) +
           ". Groups: " + ", ".join(f"{v} {k}" for k, v in c["by_group"].items()) + ".", "",
           "| Domain | Distinct | Existing | New in 0.8 | Deferred | Blocked | Out of scope | Merged |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    doms = DOMAINS + ["Added by this project"]
    for d in doms:
        xs = [x for x in cat["items"] if x["domain"] == d]
        ds = [x for x in xs if not x["duplicate_of"]]
        n = Counter(x["status_code"] for x in ds)
        out.append(f"| {d} | {len(ds)} | {n['E']} | {n['N']} | {n['D']} | {n['B']} | {n['X']} | {len(xs) - len(ds)} |")
    out.append("")
    for d in doms:
        xs = [x for x in cat["items"] if x["domain"] == d]
        if xs and xs[0]["source"] == "brief":
            i = DOMAINS.index(d)
            out += [f"## {d}", "", f"*User value:* to {USER_VALUE[i]}. *Scientific value:* {SCI_VALUE[i]}.", ""]
        else:
            out += [f"## {d}", ""]
        out += ["| ID | Concept | Status | Priority | Description | Dependencies | Limitations | Verified by |", "|---|---|---|---|---|---|---|---|"]
        for x in xs:
            if x["duplicate_of"]:
                out.append(f"| {x['id']} | {x['name']} | duplicate of {x['duplicate_of']} | — | Same capability as {x['duplicate_of']}; not counted. | — | — | — |")
                continue
            st = x["status"] + (f" (Phase 7 {x['phase7']})" if x["phase7"] else "")
            ver = x["verification"] if x["verification"] == "—" else f"`{x['verification']}`"
            out.append(f"| {x['id']} | {x['name']} | {st} | {x['group']} ({x['priority']}) | {x['description']} | {', '.join(x['dependencies']) or '—'} | "
                       f"{x['limitations'] or '—'} | {ver} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "phase8_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "PHASE8_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
