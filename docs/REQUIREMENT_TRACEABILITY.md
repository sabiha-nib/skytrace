# Requirement traceability (v0.9.0, 2026-11-02)

`IMPLEMENTED` means the code exists and its deterministic tests pass. `VERIFIED` means it is also confirmed on real data or a live service. `BLOCKED` names the missing access. Hackathon submission requirements were retired when the project moved to Meta.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| R01 | Target search, coordinate parsing, URL state | `science/coords.py`, `web/js/state.js` | `test_coords.py`; e2e loads `#/explorer?target=…` | IMPLEMENTED | |
| R02 | Real SPHEREx acquisition (QR3, QR2 fallback), checksums, resume, inspection | `archive/acquire.py`, `scripts/acquire_targets.py` | `test_acquire.py` (mocked) | **BLOCKED** | no route to IRSA; run `scripts/acquire_targets.py --all` and `pytest -m live` |
| R02.1 | Bundle manifest from files that exist; verified checksums | `bundle.py`, `scripts/verify_data_bundle.py` | `test_acquire.py`, verify.py | IMPLEMENTED | synthetic bundles verify |
| R02.2 | Observation index | `scripts/build_observation_index.py` | run manually | IMPLEMENTED | |
| R03 | Time Machine: epochs, blink/fade/side-by-side, contrast, overlays, compatibility gating | `web/js/timemachine.js`, `/pair-image` | e2e `test_04` | IMPLEMENTED | |
| R04 | Wavelength-matching rule with reasons | `science/wavelength.py` | unit + e2e | IMPLEMENTED | on synthetic λ |
| R05 | Difference image only for matched pairs | `web/js/viewer.js` | e2e `test_04` | IMPLEMENTED | display only |
| R06 | FITS reading and WCS (astropy or native) | `fitsio.py`, `wcs.py`, `archive/products.py` | `test_fits_wcs.py`; `tests/live` cross-check | IMPLEMENTED, real-file check **BLOCKED** | |
| R07 | Spectrum from measurements | `analysis.py` (spectrum step), Lab › Spectrum | e2e `test_05` | IMPLEMENTED | aperture fluxes, mixed epochs, labelled |
| R08 | Detectors D1–D6 handled separately | throughout | unit | IMPLEMENTED | |
| R09 | Catalogue identity (SIMBAD) and Gaia DR3 astrometry/references | `archive/references.py`, `acquire.resolve` | mocked | **BLOCKED** live | |
| R10 | Five named targets | `config/targets.json` | e2e `test_01` (no-data state) | IMPLEMENTED, data **BLOCKED** | |
| R11 | Reproducible investigation records | `report.py`, records API | reproducibility tests, e2e replay | IMPLEMENTED | |
| R12 | Uncertainty propagation and missing data | science modules | pull tests, NaN→null | IMPLEMENTED | |
| R13 | Evidence graph from recorded facts only | `view.evidence_graph`, `web/js/graph.js` | `test_evidence_graph_only_has_recorded_nodes`, e2e `test_06` | IMPLEMENTED | |
| R14 | Failure modes: flags, blends, outlier references, missing wavelength, edge, wrong responses, tampering | science + archive | unit | IMPLEMENTED | |
| R15 | Method comparison / sensitivity | Lab › Re-run & compare; MOMENT-1 cross-check | e2e `test_05` | IMPLEMENTED | |
| R16 | Investigation history | event log; saved records with transcript | e2e `test_08` | IMPLEMENTED | |
| R17 | Meta Model API integration | `ai/meta_client.py`, `ai/copilot.py` | scripted client | **BLOCKED** live | no key, no route |
| R18 | Read-only tools (12 in 0.5, 16 in 0.6), guard, budgets, audit, local fallback | `ai/` | `test_tool_contracts.py`, `test_report_ai.py`, `test_copilot2.py` | IMPLEMENTED | |
| R19 | Offline mode with sockets blocked | `archive/net.py`, server design | `test_offline_workflow.py`, e2e `test_09` | IMPLEMENTED | |
| R20 | Live/cache/fixture/synthetic labels | `provenance.py`, UI pills/banners/watermark | unit, e2e `test_02` | IMPLEMENTED | |
| R21 | Interactive UI, responsive, keyboard, CSP | `web/` | e2e incl. mobile | IMPLEMENTED | |
| R22 | Security: secrets, path validation, no arbitrary execution | server, tools, verify.py | integration traversal tests, secret scan | IMPLEMENTED | |
| R23 | Tests and test report | `tests/`, `docs/TEST_REPORT.md` | — | IMPLEMENTED | |
| R24 | Documentation | `README.md`, `docs/` | — | IMPLEMENTED | |
| R25 | AI disclosure | `docs/AI_USE.md` | — | IMPLEMENTED | |
| R26 | Single start command, verification command, release archive | `run.py`, `scripts/verify.py`, `scripts/make_release.py` | run | IMPLEMENTED | Dockerfile not built |
| R27 | Environment diagnosis distinguishing DNS / proxy / TLS / HTTP / package failures | `scripts/diagnose_environment.py`, `archive/net.py` | `test_proxy_policy_denial_not_retried` | IMPLEMENTED | `ENVIRONMENT_REPORT.md` |
| R28 | Independent FITS/WCS validation with tolerances | `fitsio.py`, `wcs.py` | `test_fits_wcs_external.py` (22) | IMPLEMENTED, real-file check **BLOCKED** | `FITS_WCS_VALIDATION.md` |
| R29 | Calibration and uncertainty audit with classification | `science/ephemeris.py`, `refsel.py`, `variability.py`, `astrometry.py`, `wavelength.py` | `test_ephemeris.py`, `test_calibration_v2.py`, robustness | IMPLEMENTED | `CALIBRATION_AUDIT.md` |
| R30 | Defensible outcomes: sensitivity, non-detection ≠ static, failure ≠ no motion | `science/assess.py` (ASSESS-2) | `test_assess2.py` | IMPLEMENTED | `ASSESSMENT_ENGINE.md` |
| R31 | Structured reason codes; no free-text parsing for status | `measure.py`, `wavelength.py`, `analysis.py` | `test_pair_codes_structured`, PROVCHECK `status_codes` | IMPLEMENTED | |
| R32 | Provenance verification command | `provenance_check.py`, `scripts/verify_provenance.py` | `test_provenance_check.py`, verify.py | IMPLEMENTED | |
| R33 | Tool contracts (schemas, bounds, envelope, errors, evidence fields, cache) | `ai/tools.py` (TOOLS-2) | `test_tool_contracts.py` | IMPLEMENTED | `COPILOT_TOOLS.md` |
| R34 | Guard: identifiers and uncertainty in addition to claims, numbers, citations, limitations, synthetic status | `ai/guard.py` (GUARD-3) | `test_guard3_identifiers_and_uncertainty` | IMPLEMENTED | |
| R35 | Live Meta test | `scripts/meta_smoke_test.py` | — | **BLOCKED** | api.meta.ai refused; no key |
| R36 | Robustness and perturbation stability (synthetic, labelled) | `synthetic.py`, `stability.py`, `/api/targets/{id}/stability` | `tests/robustness` (12), e2e `test_05b` | IMPLEMENTED | `TEST_REPORT.md` |
| R37 | Previewable application without a server; honest gating of server-only features | `scripts/build_static.py`, `web/js/static/` | `tests/e2e/test_controls.py[static]` | IMPLEMENTED | hosted as a private claude.ai artifact; hosted copy not opened from the build environment (sign-in) |
| R38 | Browser computations equal the Python ones (pair comparison, record content hash) | `web/js/static/compare.js`, `hash.js` | `tests/unit/test_static_preview.py` (Node parity, mutation-checked) | IMPLEMENTED | |
| R39 | Every visible control works or is disabled with a reason; back/forward; keyboard; overlay dismissal | `web/js/*` | `tests/e2e/test_controls.py` (both modes) | IMPLEMENTED | |
| R40 | Record export and verified import | `/api/investigations/{id}/record.json`, `/api/records/import`, `records.js` | integration + e2e | IMPLEMENTED | |

## Phase 5 (v0.5)

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P5.01 | Discovery loop and persistent investigation context | `web/js/main.js`, `state.context` | e2e `test_l_discovery_engine`, `test_p_vault_and_studio` | IMPLEMENTED | question and hypotheses survive navigation and reopen |
| P5.02 | Three levels (Explore / Investigate / Research) | CSS `body[data-level]`, `web/js/lab.js` | e2e `test_j_levels` | IMPLEMENTED | |
| P5.03 | Command palette, keyboard shortcuts, glossary, undo, back/forward | `web/js/palette.js`, `main.js`, `arena.js` | e2e `test_k_palette_help_shortcuts`, `test_m_hypothesis_arena`, `test_f_back_forward` | IMPLEMENTED | undo covers hypothesis removal only |
| P5.04 | Feature catalogue ≥ 250 concepts, 25 domains, 7 scores, tiers | `scripts/feature_catalogue.py` → `docs/FEATURE_CATALOGUE.md` | `test_feature_catalogue.py` | IMPLEMENTED | counts computed |
| P5.05 | Discovery engine stages A–G | `discovery.py`, `web/js/discovery.js` | `test_discovery.py`; e2e | IMPLEMENTED | on synthetic data |
| P5.06 | Hypothesis Arena, rule-driven, no probabilities | `hypotheses.py`, `arena.js`, `rules.js` | `test_discovery.py`, parity test, e2e | IMPLEMENTED | three explanations have no implemented test (shown as not tested) |
| P5.07 | Uncertainty Explorer; sensitivity separate | `uncertainty.py`, `uncertainty.js` | `test_discovery.py`, e2e `test_n` | IMPLEMENTED | |
| P5.08 | Evidence Graph improvements | `view.evidence_graph` (explanation nodes), `graph.js` | `test_discovery.py`, e2e `test_e` | IMPLEMENTED | |
| P5.09 | Advanced Time Machine: registration diagnostics | `view.registration_diagnostics`, `compare.js`, `timemachine.js` | known-answer + parity tests, e2e `test_o` | IMPLEMENTED | |
| P5.10 | Copilot capability registry and evidence-structured answers | `capabilities.py`, tool `list_capabilities`, `copilot.js` | `test_tool_contracts.py`, e2e `test_q` | IMPLEMENTED; Meta model **BLOCKED** | no key, no route |
| P5.11 | Report and figure studio | `records.js` (studio), `figures.js`, `package.py` | e2e `test_n`, `test_p`; package determinism | IMPLEMENTED | PDF export deferred |
| P5.12 | Vault: search, tags, clone, rename, compare, import preview, delete confirmation | `records.js`, `PATCH`/`clone` routes | `test_api.py`, e2e `test_g`, `test_p` | IMPLEMENTED | |
| P5.13 | Offline first-class | OFFLINE=1, static preview with precomputed Phase 5 outputs | `test_offline_workflow.py`, e2e static mode | IMPLEMENTED | |
| P5.14 | Live-data program | `scripts/diagnose_environment.py` | re-run 2026-10-29 | **BLOCKED** | IRSA, SIMBAD, Gaia, Meta, PyPI, npm: proxy 403 |
| P5.15 | Performance and accessibility audit | `scripts/measure_performance.py`, `test_accessibility.py`, e2e `test_y`, `test_r` | as listed | IMPLEMENTED | no assistive-technology session |
| P5.16 | Security: untrusted imports, no secrets in frontend, no telemetry | `state.sanitizeContext`, import preview, verify.py secret scan | e2e, verify.py | IMPLEMENTED | |
| P5.17 | New release without overwriting 0.4.0 | `scripts/make_release.py` (refuses to overwrite) | release run | see TEST_REPORT | |


## Phase 6 (v0.6)

Section numbers refer to the Phase 6 brief. Tests named `s1`–`s10`, `h2` are in `tests/e2e/test_controls.py` and run in server and static mode.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P6.01 | Audit the 0.5 repository first; preserve what works | `docs/PHASE6_AUDIT.md` | baseline `verify.py --e2e` 18/18 | DONE | no 0.5 test removed |
| P6.02 | Persistent, integrity-checked research session; versioned schema; migration | `session.py`, `canon.py`, `schema.py`, `web/js/session*.js`, `server/research.py` | `test_research_session.py` (7, incl. parity), e2e `s2`, `s9` | IMPLEMENTED | old records migrate; never discarded |
| P6.03 | Unified capability registry with actions used by planner, copilot, workflows, missions | `capabilities.py` (CAPREG-2), `web/js/executor.js` | `test_registry_actions_and_capabilities_are_consistent` | IMPLEMENTED | |
| P6.04 | Adaptive Investigation Planner: deterministic, validated, statuses, confirmation, no simulation | `planner.py`, `planner.js`, `plannerui.js` | `test_planner_known_plans`, parity, e2e `s2` | IMPLEMENTED | rule-based; no model intent used (no key) |
| P6.05 | Observatory Command Center with real values only | `commandcenter.js` | e2e `s1` | IMPLEMENTED | |
| P6.06 | Multi-epoch discovery: never interpolate; say when only two epochs | `compat.py` (SEQ-1), `timemachine.js` | `test_sequences_are_cliques…`, e2e `s3` | IMPLEMENTED | |
| P6.07 | Experiment Studio (parameter, sensitivity, method comparison, reproducibility, negative control, robustness); validity note | `experiments.py`, `experimentsui.js` | `test_experiment_validation_and_negative_control`, API, e2e `s8` | IMPLEMENTED | custom parameters need the server |
| P6.08 | Compatibility matrix with explicit rules; metadata diff; duplicates | `compat.py`, `qualityui.js` | `test_matrix_is_the_logged_decisions`, `test_duplicate_files_are_detected`, e2e `s3` | IMPLEMENTED | |
| P6.09 | Evidence Ledger: claims, contradictions, provenance, methods, completeness, history; one item ≠ full support | `ledger.py`, `ledgerui.js` | `test_ledger_counts_support_and_flags_conflicts`, e2e `s6` | IMPLEMENTED | |
| P6.10 | Knowledge graph only from stored relationships; empty state | `kg.js`, `records.js` | e2e `test_p_vault_and_studio` | IMPLEMENTED | |
| P6.11 | Visualization Studio with titles, units, provenance, export; PDF only if valid | `figurestudio.js` | e2e `s10` (SVG parses) | IMPLEMENTED | no PDF offered |
| P6.12 | Research Notebook: blocks, provenance links, authorship, export to package | `notebook.js`, `zipstore.js` | `test_zipstore_output_is_valid_and_deterministic`, e2e `s7`, `h2` | IMPLEMENTED | |
| P6.13 | Data Quality Observatory: five outcomes, no universal score | `quality.py`, `qualityui.js` | `test_quality_outcomes_and_injected_defects`, e2e `s3` | IMPLEMENTED | |
| P6.14 | Connectors: testable boundary, never claim success | `connectors.py`, `archive/net.py` | `test_connector_previews_match_acquisition_and_send_nothing`, `test_retry_after_is_honoured_and_bounded`, e2e `s4` | IMPLEMENTED; live use **BLOCKED** | proxy 403 |
| P6.15 | Copilot 2.0: registry-only, validated plans, answer-source labels | `ai/tools.py`, `ai/local.py`, `copilot.js` | `test_copilot2.py`, `test_tool_contracts.py`, intent parity, e2e `h2` | IMPLEMENTED; Meta model **BLOCKED** | |
| P6.16 | Discovery Radar: opportunities with what / why / evidence / data / method / cannot / can-run-now | `radar.py`, `radarui.js` | `test_radar_items_are_explained_and_ranked_by_the_stated_rule`, e2e `s5` | IMPLEMENTED | |
| P6.17 | Missions without gamification | `missions.py`, `missions.js`, `commandcenter.js` | `test_missions_read_completion_from_the_session`, e2e `s1` | IMPLEMENTED | task order not enforced |
| P6.18 | Research automation: workflows, batch, per-item records, cancel, retry, export/import, bounds | `workflows.py`, `workflows.js`, `experimentsui.js` | `test_workflow_validation`, parity, e2e `s8` (cancel/retry in server mode) | IMPLEMENTED | |
| P6.19 | Catalogue ≥ 300 distinct concepts in the brief's 30 domains, statuses, no synonyms | `scripts/phase6_catalogue.py` → `docs/PHASE6_CATALOGUE.md` | `test_phase6_catalogue.py` | IMPLEMENTED | 309 distinct; 15 merged |
| P6.20 | Prioritisation (Foundation / High Impact / Signature / Frontier) with the §20 fields | same | same | IMPLEMENTED | |
| P6.21 | UI: levels alter visibility only; empty states and disabled actions explain; real loading; responsive | `main.js`, CSS | e2e `test_j_levels`, `test_r_new_workspaces_narrow`, `test_y_accessible_names`, `test_z_no_external_requests_no_errors` | IMPLEMENTED | |
| P6.22 | Versioned schemas, migration, never discard records | `session.py` (`skytrace.research_session/1`), `workflows.py` (`skytrace.workflow/1`) | `test_migration_from_v05_saved_record` | IMPLEMENTED | |
| P6.23 | Tests for every Phase 6 area; BLOCKED reported as blocked; none removed | `tests/` | see TEST_REPORT v0.6.0 | IMPLEMENTED | live tests BLOCKED |
| P6.24 | Release: metadata, docs, methods generated from code, new version only, commit, no push | `scripts/gen_research_methods.py`, `make_release.py` | release run | see TEST_REPORT | not pushed |
| P6.25 | Hosted preview, tested as rendered | `dist/preview/`, hosted artifact | see TEST_REPORT | see TEST_REPORT | |

## Phase 7 (v0.7)

Section numbers follow the Phase 7 brief. Tests named `t1`–`t8` are in `tests/e2e/test_controls.py` and run in server and static mode.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P7.01 | Audit the real repository first; record the baseline | `docs/PHASE7_AUDIT.md` | baseline at `fb03e93`: verify 18/18, 269/2, e2e 73 | DONE | version was 0.6.1, not 0.5.0 as the brief assumed |
| P7.02 | Scientific Possibility Engine, six layers, from recorded values | `possibility.py` (SPE-1), `horizonui.js` | `test_frontier.py::test_possibility_layers_and_horizon_cards`, e2e `t1` | IMPLEMENTED |  |
| P7.03 | Counterfactual Universe Lab: isolated, baseline identified, five value labels, comparison, lineage, export | `counterfactual.py` (CF-1), `counterfactualui.js`, `POST /api/counterfactuals` | `test_frontier.py::test_counterfactuals_are_isolated_and_labelled`, `::test_reassessment_without_change_reproduces_the_record`, `::test_counterfactual_validation_refuses`, API, e2e `t2` | IMPLEMENTED | original never modified (tested by hash and object equality) |
| P7.04 | ASTRO-TWIN: five twin kinds, versioning, comparison, provenance, integrity, export, restoration | `twin.py` (TWIN-1), `frontiercore.js`, `knowledgeui.js` | `test_frontier.py::test_twins_integrity_and_comparison`, parity, e2e `t7` | IMPLEMENTED (versioning and restoration DEFERRED) | twins are computational records, labelled so |
| P7.05 | Discovery Horizon: cards with all nine fields, opportunity map, no invented counts | `possibility.py` (HORIZON-1), `horizonui.js` | `test_frontier.py::test_possibility_layers_and_horizon_cards`, `::test_browser_overlays_match_python`, e2e `t1` | IMPLEMENTED | ranking is a stated convention |
| P7.06 | Adversarial Science Lab: modes; issue, evidence, rule, severity, why, verification, status; no unproven flaw | `adversarial.py` (ASL-1), `adversarialui.js` | `test_frontier.py::test_adversarial_rules_and_statuses`, e2e `t3` | IMPLEMENTED |  |
| P7.07 | Synthetic Observatory: generator version, parameters, seed, IDs, truth, assumptions, limitations, comparison, reproducible seeds, never replaces real data | `synthobs.py` (SYNOBS-1), `synthobsui.js`, `POST /api/synthetic` | `test_frontier.py::test_synthetic_scenarios_are_labelled_deterministic_and_known_answer`, `::test_synthetic_validation_and_design_refusals`, API, e2e `t4` | IMPLEMENTED | `data/synthlab/` only |
| P7.08 | Observation Design Lab: hypothetical only, no telescope scheduling | `synthobs.design` (OBSDES-1) | `test_frontier.py::test_observation_design_compares_schedules`, e2e `t4` | IMPLEMENTED |  |
| P7.09 | INFOGAIN: no numeric gain without probabilities; qualitative ranking | `infogain.py` (INFO-1) | `test_frontier.py::test_information_analysis_has_no_probabilities`, e2e `t3` | IMPLEMENTED | `probability_model` is null |
| P7.10 | Causality Workbench: four relationship labels; no causation from correlation | `adversarialui.js` (causal tab), `review.py` causal words | e2e `t3`, `test_frontier.py::test_review_findings_cite_sources` | IMPLEMENTED (empirically supported: none exist; temporal-order checks DEFERRED) |  |
| P7.11 | AUTOPILOT: permission levels, approval, recorded, cancel, capability validation, imported workflows never auto-run | `capabilities.py` (CAPREG-3), `autopilotui.js`, `executor.js` | `test_frontier.py::test_registry_permissions_cover_every_action`, `::test_executor_implements_every_registered_action`, e2e `t5` | IMPLEMENTED | no level grants network |
| P7.12 | COSMIC ATLAS: angular / projected / physical / unknown distance; nothing 3-D from 2-D | `atlasui.js`, `frontiercore.js` | `test_frontier.py::test_browser_twin_and_coordinates_match_python`, e2e `t6` | IMPLEMENTED | distance only from recorded parallax |
| P7.13 | KNOWLEDGE ATLAS: structured search; no fabricated semantic similarity | `knowledgeui.js` | e2e `t7` | IMPLEMENTED; semantic indexing **BLOCKED** | no embedding model reachable |
| P7.14 | REVIEW ROOM: software roles; findings cite records | `review.py` (REVIEW-1), `reviewui.js` | `test_frontier.py::test_review_findings_cite_sources`, e2e `t8` | IMPLEMENTED |  |
| P7.15 | DISCOVERY STORY: evidence-bound; inconclusive stays inconclusive | `reviewui.js` (story) | e2e `t8` | IMPLEMENTED |  |
| P7.16 | REPRODUCIBILITY CHALLENGE: import ≠ reproduction | `repro.py` (REPRO-1), `POST …/reproduce` | `test_frontier.py::test_reproducibility_verdicts_and_tamper`, API, e2e `t8` | IMPLEMENTED |  |
| P7.17 | Multi-agent research: design only unless a provider is verified; no simulated conversations | `docs/MULTI_AGENT_DESIGN.md` | — | **BLOCKED** (design documented) | Meta API 403, no key |
| P7.18 | Interaction and visualization: units, provenance, simulated values labelled | Phase 7 UI modules | e2e `t1`–`t8` (labels asserted) | IMPLEMENTED |  |
| P7.19 | Catalogue ≥ 400 distinct concepts in 40 domains, deduplicated, five statuses | `scripts/phase7_catalogue.py` → `docs/PHASE7_CATALOGUE.md` | `test_phase7_catalogue.py` | IMPLEMENTED | 406 distinct; 36 merged; 78 cite Phase 6 |
| P7.20 | Eight research-mode navigation | `web/index.html`, `main.js` | e2e `test_y_accessible_names`, `test_j_levels`, `test_r_new_workspaces_narrow` | IMPLEMENTED |  |
| P7.21 | Architecture: no unrelated rewrite; deterministic engines; session-dependent rules parity-tested | `server/frontier.py`, `frontiercore.js` | `test_frontier.py::test_browser_overlays_match_python` | IMPLEMENTED |  |
| P7.22 | Performance measured | `scripts/measure_performance.py` → `docs/performance.json` | see TEST_REPORT v0.7.0 | see TEST_REPORT |  |
| P7.23 | Security: validated inputs, permission boundaries, no keys in the browser, no automatic external access | `server/frontier.py`, `capabilities.py` | API tests, `test_frontier.py::test_registry_permissions_cover_every_action`, e2e `test_z_no_external_requests_no_errors` | IMPLEMENTED |  |
| P7.24 | Validation tests for every Phase 7 area; none removed | `tests/` | see TEST_REPORT v0.7.0 | IMPLEMENTED | live tests BLOCKED |
| P7.25 | Release: version, docs, methods generated from code, new version only, commit, no push; hosted preview opened where possible | `make_release.py`, `gen_frontier_methods.py` | see TEST_REPORT v0.7.0 | see TEST_REPORT | not pushed |

## Phase 8 (v0.8)

Section numbers follow the Phase 8 brief. Tests named `e1`–`e9` are in `tests/e2e/test_controls.py` and run in server and static
mode. `test_epistemic.py` is `tests/unit/test_epistemic.py`.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P8.01 | §1 Audit the actual project first; preserve existing functionality | `docs/PHASE8_AUDIT.md` (feature-preservation matrix) | baseline at `948cd1c`: 292/2, e2e 89; every earlier test still runs | DONE | pipeline code unchanged; record hashes identical |
| P8.02 | §2.1 Epistemic objects (15 kinds, stable IDs) | `epistemic.py` (EPI-1) | `test_epistemic.py::test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses`, e2e `e1` | IMPLEMENTED |  |
| P8.03 | §2.2 Ten epistemic statuses from source and method, never wording | `epistemic.py` STATUS_RULES S1–S10 | same; `test_epistemic.py::test_asserted_words_ignore_negated_uses` | IMPLEMENTED | procedures carry no status |
| P8.04 | §2.3 Reasoning graph with backward and forward tracing | `epistemic.trace`, `epistemiccore.trace`, `reasoningui.js` | `test_epistemic.py::test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims`, parity, e2e `e1` | IMPLEMENTED |  |
| P8.05 | §3 SCI-COMP: ten stages, outcomes, never "proof" | `scicomp.py` (SCICOMP-1), `compilerui.js` | `test_epistemic.py::test_compiler_runs_every_stage_and_states_the_precedence_rule`, `::test_compiler_detects_injected_defects`, e2e `e2` | IMPLEMENTED | both fixtures: "requires scientific review" |
| P8.06 | §4 SCI-DEBUG: breakpoints at real stages, recomputation, no invented intermediates, differential debugging | `scidebug.py` (SCIDEBUG-1), `debuggerui.js`, `epistemiccore.diff` | `test_epistemic.py::test_debugger_breakpoints_are_real_stages_and_recompute_exactly`, `::test_differential_debugging_finds_the_earliest_divergence`, parity, e2e `e4` | IMPLEMENTED |  |
| P8.07 | §5 K-BOUNDARY: four regions, no numeric confidence | `claims.boundary` (KBOUND-1), `claimsui.js` | `test_epistemic.py::test_knowledge_boundary_rules`, e2e `e3` | IMPLEMENTED |  |
| P8.08 | §6 CLAIM-X: ten modes with documented rules, six results | `claims.stress` (CLAIMX-1) | `test_epistemic.py::test_claim_stress_modes_and_results`, e2e `e3`, `e4` | IMPLEMENTED |  |
| P8.09 | §7 NEGATIVE SPACE: required fields, seven distinctions, searchable, never erased | `negspace.py` (NEG-1), `negativeui.js` | `test_epistemic.py::test_negative_knowledge_registry_records_what_failed`, e2e `e7` | IMPLEMENTED | session entries persist with the session |
| P8.10 | §8 BLINDSPOT: coverage of defined checks, no percentage | `blindspot.py` (BLIND-1), `overlayBlindspots` | `test_epistemic.py::test_blindspot_coverage_is_over_defined_checks_only`, parity, e2e `e3` | IMPLEMENTED |  |
| P8.11 | §9 METHOD DNA: schema, comparison, dependency graph, health; tests ≠ validity | `methodgenome.py` (METHOD-DNA-1) | `test_epistemic.py::test_method_genome_is_complete_and_its_tests_exist`, e2e `e2` | IMPLEMENTED | 13 methods |
| P8.12 | §10 UNCERTAINTY FLOW: represented categories only, omissions listed, no invented propagation | `uflow.py` (UFLOW-1), `uflowui.js` | `test_epistemic.py::test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions`, e2e `e5` | IMPLEMENTED |  |
| P8.13 | §11 LINEAGE-X | `lineage.py` (LINEAGE-1), `GET …/lineage` | `test_epistemic.py::test_lineage_refers_only_to_recorded_stages`, API, e2e `e1` | IMPLEMENTED | preview: claims and fit |
| P8.14 | §12 BLINDLAB: hidden fields, who/when, disclosure prevention, documented unblinding, audit trail | `protocolui.js`, `main.js` (BLINDLAB-1), `ruler.js`, `copilot.js` | e2e `e8` | IMPLEMENTED | interface-level blinding; documented in LIMITATIONS |
| P8.15 | §13 REPRODUCE-X: five verdicts, no false "exact" | `reprox.py` (REPROX-1), `POST …/reproduce-x` | `test_epistemic.py::test_reproduction_verdicts`, API, e2e `e4` | IMPLEMENTED | local environment only |
| P8.16 | §14 NEXT-X: transparent decision records, no optimality | `decide.next_steps` (NEXTX-1), `decideui.js` | `test_epistemic.py::test_decisions_are_explained_and_questions_cite_their_source`, e2e `e6` | IMPLEMENTED |  |
| P8.17 | §15 MODEL ARENA: appropriate criteria, no arbitrary scores | `modelarena.py` (MODELS-1) | `test_epistemic.py::test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit`, e2e `e5` | IMPLEMENTED | your own models DEFERRED |
| P8.18 | §16 EVIDENCE VAULT: append-only, no claim of cryptographic immutability | `session.py`, `sessioncore.js` (VAULT-1), `epitabs.js` | `test_epistemic.py::test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid`, e2e `e9` | IMPLEMENTED |  |
| P8.19 | §17 REASONING LAB: validity separate from empirical truth | `argueui.js` (ARG-1) | e2e `e9` | IMPLEMENTED |  |
| P8.20 | §18 INTEGRITY-X: export readiness, never rewrites, never blocks | `integrity.py` (INTEG-1), `integrityCheck`, `POST /api/integrity` | `test_epistemic.py::test_integrity_firewall_flags_problems_without_rewriting`, parity, API, e2e `e7` | IMPLEMENTED | found a real gap: the report stated no limitations (fixed) |
| P8.21 | §19 QUESTION FORGE | `decide.questions` (QFORGE-1) | `test_epistemic.py::test_decisions_are_explained_and_questions_cite_their_source`, e2e `e6` | IMPLEMENTED | ranking DEFERRED |
| P8.22 | §20 Scientific contract: protocol, lock, amendments; not preregistration | `protocolui.js` (PROTOCOL-1) | e2e `e8` | IMPLEMENTED | late locks labelled |
| P8.23 | §21 POSSIBILITY ATLAS | `possibility.py` (Phase 7), `decideui.js` hand-off | e2e `t1`, `e6` | IMPLEMENTED (existing); path validity, opportunity comparison and map provenance DEFERRED | connections are not inferences |
| P8.24 | §22 Multi-scale workbench | Sky Explorer, ruler, Discovery Engine, KG, reasoning graph focus | e2e `test_b`, `l`, `p`, `e1`, `e2` | PARTIAL: measurement, observation, investigation and knowledge levels exist; pixel level and multi-scale export DEFERRED |  |
| P8.25 | §23 SIM-CHECK | `simcheck.py` (SIMCHECK-1), `epitabs.js` | `test_epistemic.py::test_simulation_audit_refuses_invalid_scenarios`, API, e2e `e9` | IMPLEMENTED | near-threshold boundary tests DEFERRED |
| P8.26 | §24 REVIEW-X: not peer review; human annotations | `reviewx.py` (REVIEWX-1), `epitabs.js` | `test_epistemic.py::test_review_board_links_every_item`, e2e `e9` | IMPLEMENTED | no accounts (reviewer identity out of scope) |
| P8.27 | §25 FUTURELAB: hypothetical only | `futurelab.py` (FUTURE-1), `futureui.js` | `test_epistemic.py::test_futurelab_formula_is_validated_before_scenarios`, parity, e2e `e5` | IMPLEMENTED |  |
| P8.28 | §26 Catalogue ≥ 500 distinct concepts in 50 domains, deduplicated against every earlier phase | `scripts/phase8_catalogue.py` → `docs/PHASE8_CATALOGUE.md` | `test_phase8_catalogue.py` | IMPLEMENTED | 507 distinct; 31 merged; 160 cite Phase 7 |
| P8.29 | §27 Eight-mode navigation | `web/index.html`, `main.js` | e2e `test_y_accessible_names`, `test_r_new_workspaces_narrow`, `test_j_levels` | IMPLEMENTED |  |
| P8.30 | §28 Reusable components; no fake metrics, no inert controls | `epiui.js` (status and outcome pills, tabs, tables), `app.css` | e2e `test_y` (every visible control named), `e1`–`e9` | IMPLEMENTED |  |
| P8.31 | §29 Data and scientific integrity distinctions | EPI-1 statuses, synthetic notes, labels | `test_epistemic.py::test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses` | IMPLEMENTED | no model computes anything |
| P8.32 | §30 Engineering: existing stack, one source of truth, typed, versioned, no new dependencies | `server/epistemic.py` (one cached report), method IDs | parity tests | IMPLEMENTED | no dependency added |
| P8.33 | §31 Tests for every area; browser workflows; none removed or weakened | `tests/` | see TEST_REPORT v0.8.0 | IMPLEMENTED | live tests BLOCKED |
| P8.34 | §32 Documentation and release; methods generated from code; new version only; no push | `gen_epistemic_methods.py`, `make_release.py` | see TEST_REPORT v0.8.0 | see TEST_REPORT | not pushed |
| P8.35 | §33 Working preview with the five capability classes stated | `docs/PREVIEW.md` | e2e static mode | see TEST_REPORT v0.8.0 | publication is not proof of rendering |

## Phase 9 (v0.9)

Section numbers follow the Phase 9 brief. Tests named `i1`–`i6` are in `tests/e2e/test_controls.py` and run in server and static
mode. `test_intelligence.py` is `tests/unit/test_intelligence.py`.

| ID | Requirement | Location | Test | Status | Evidence / blocker |
|---|---|---|---|---|---|
| P9.01 | §0 Inspect the repository; preserve working functionality; no mockups | `docs/PHASE9_AUDIT.md` §1–2 | baseline at `9c76db1`: 323/2, e2e 107; all earlier tests still run | DONE | record hashes identical; no earlier test removed or weakened |
| P9.02 | §1 Six intelligence layers sharing data and provenance | `server/intelligence.py`, `intelui.js` LAYERS | e2e `i1`–`i6` | IMPLEMENTED | every engine reads the same epistemic report and entity envelope |
| P9.03 | §2A Cosmic Memory; never promotes a hypothesis | `memory.py`, `intelcore.recall`, `failureWarnings` | `test_intelligence.py::test_memory_statuses_never_promote_explanations_and_flag_tampering`, `::test_memory_marks_superseded_conclusions_outdated`, `::test_recall_uses_the_concept_vocabulary_and_failure_warnings_quote_reasons`, e2e `i6` | IMPLEMENTED | corpus is small (two synthetic targets) |
| P9.04 | §2B Discovery Genome (13 fields); visual similarity is not proof | `dgenome.py` | `test_intelligence.py::test_genomes_have_every_field_and_cite_real_objects`, `::test_genome_comparison_is_structural_and_unscored`, e2e `i1` | IMPLEMENTED |  |
| P9.05 | §2C What-If engine (8 steps); hypothetical; never overwrites | `whatif.py`, `counterfactual.py`, `intelcore.hypotheticalVisit` | `test_intelligence.py::test_whatif_is_isolated_validated_and_refuses_without_a_method`, e2e `i4` | IMPLEMENTED | W3 has no valid method; W4/W5 routed |
| P9.06 | §2D Causality Lab; never causality from correlation | `causal.py`, `intelcore.causalWarnings` | `test_intelligence.py::test_causal_confounders_and_criteria_never_claim_causation`, parity, e2e `i3` | IMPLEMENTED | C5 never met |
| P9.07 | §2E Unknown Universe (8 regions, traceable) | `unknownmap.py` | `test_intelligence.py::test_unknown_map_regions_have_rules_and_every_item_a_basis`, e2e `i2` | IMPLEMENTED |  |
| P9.08 | §2F Observation Oracle; no telescope scheduling | `oracle.py`, `intelcore.oracleEvaluate` | `test_intelligence.py::test_oracle_known_answers_and_refusals`, parity, e2e `i4` | IMPLEMENTED | information gain not computed (no defensible priors) |
| P9.09 | §2G Scientific Adversary; no manufactured objections | `adversary.py`, `intelcore.overlayLedger` | `test_intelligence.py::test_adversary_raises_only_rule_backed_challenges`, e2e `i3` | IMPLEMENTED |  |
| P9.10 | §2H Research Autopilot: three levels, audit trail | `autonomy.py`, `capabilities.AUTONOMY_LEVELS`, `intelui2.cyclePanel` | `test_intelligence.py::test_research_cycle_proposes_registered_actions_by_rule_and_levels_bound_execution`, e2e `i5` | IMPLEMENTED | no stop control or budgets (deferred) |
| P9.11 | §2I Reproduction Network; execution is not validity | `repronet.py`, `intelcore.reproCompare` | `test_intelligence.py::test_reproduction_manifests_validate_and_comparison_classes`, API test, e2e `i6` | IMPLEMENTED | cross-machine reproduction not run |
| P9.12 | §2J Multi-Discovery Network; no keyword similarity | `mdnet.py` | `test_intelligence.py::test_network_edges_need_a_rule_and_state_basis_and_limitation`, e2e `i2` | IMPLEMENTED |  |
| P9.13 | §3 K–X selectively implemented | `docs/PHASE9_AUDIT.md` §3 | L, M, O, P, T, X unit tests; N, Q, V, W e2e `i1`, `i5`, `i6` | PARTIAL | K and U partial; R and S composed from Phase 8; N and W export without importers |
| P9.14 | §4 Unified workspace of twelve parts; data kinds distinguished | `intelui.js`, `intelui2.js`, `intelbits.KINDS` | e2e `i1`–`i6`, `r`, `y` | IMPLEMENTED | no live multi-user collaboration |
| P9.15 | §5 Shared entities with id, version, provenance, time, status, validation | `entities.py`, `intelcore.sessionEntities` | `test_intelligence.py::test_entities_have_ids_versions_provenance_and_statuses`, `::test_session_entities_follow_rules_and_count_versions` | IMPLEMENTED | zero unresolved references on both fixtures |
| P9.16 | §6 Catalogue of 600 capabilities in ≥50 domains, categories A–D | `scripts/phase9_catalogue.py`, `docs/PHASE9_CATALOGUE.md` | `test_phase9_catalogue.py` (A cites existing evidence and tests) | DONE | a roadmap, not a build list |
| P9.17 | §7 Staged implementation | commits `0515f18`, `b8b7c0b` and the release commit | — | DONE |  |
| P9.18 | §8 Tests for every listed area; parity; responsive; accessibility | `tests/` | `test_intelligence.py::test_browser_intelligence_functions_match_python`, e2e `r`, `y` | IMPLEMENTED | see TEST_REPORT v0.9.0 |
| P9.19 | §9.13 A real local preview launched and inspected | `dist/preview/` | static-mode e2e; screenshots | see TEST_REPORT v0.9.0 |  |
| P9.20 | Real astronomical data | — | — | **BLOCKED** | IRSA, SIMBAD and Gaia refused (proxy 403) |
