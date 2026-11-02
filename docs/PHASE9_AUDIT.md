# Phase 9 audit: the scientific intelligence layer (v0.9.0)

Phase 9 asked Skytrace to become a coherent scientific intelligence system in six layers (observation, discovery, reasoning,
experimental, knowledge and integrity), sharing data structures and provenance. It named ten breakthrough systems (A–J), fourteen
additional capabilities to implement selectively (K–X), a unified interface of twelve parts, a shared entity model, a catalogue
of 600 concepts, staged implementation, tests and fifteen acceptance criteria.

Every earlier rule still applied. Phase 9 added its own, among them: never replace a working system with a mockup; memory must
not turn an old hypothesis into a fact; visual similarity is not physical similarity; every counterfactual is hypothetical and
never overwrites an observation; no causality from correlation alone; no claim to schedule a telescope; the adversary challenges
reasoning and does not manufacture objections; no autonomous system silently alters data, invents results, publishes or
promotes an interpretation; successful execution is not scientific validity; a shared keyword is not a scientific relation; no
fabricated endorsements; no implied live collaboration; and a synthetic test is never evidence of a real discovery.

## 1. Repository audit (before any Phase 9 change)

| Item | State at commit `9c76db1` (v0.8.0 plus its test report) |
|---|---|
| Version | 0.8.0 (`src/skytrace/__init__.py`, `pyproject.toml`) |
| Working tree | clean |
| Unit, integration, robustness and parity tests | 323 passed, 2 skipped (astropy not installed) |
| Browser tests | 107 passed (TEST_REPORT v0.8.0) |
| Static preview | https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT, version 7 (0.8.0) |
| Release artifacts | 0.2.0–0.8.0 archives with `.sha256` and `RELEASE_MANIFEST-<ver>.json`; 0.8.0 `fcde43a0…`, preview `8f6e723e…` |
| External services | IRSA, SIMBAD, Gaia, the Meta API, PyPI and npm are refused by the proxy (403). No astropy, no Meta key |
| Data | Two synthetic fixtures (`syn-hpm-1`, `syn-var-1`). No real SPHEREx bundle |

There was no uncommitted user work. Everything Phase 9 added was written in this session after the baseline was recorded and
committed in two commits (`0515f18` engines and parity core; `b8b7c0b` interface, research cycle, API recordings and catalogue).

What already existed and was reused rather than rebuilt:
- the epistemic report (EPI-1 graph and statuses, KBOUND-1, CLAIMX-1, NEG-1, UFLOW-1, LINEAGE-1, QFORGE-1, INTEG-1, REPROX-1), which
  every Phase 9 engine reads instead of re-deriving
- HYPO-1 competing explanations, UNC-1 uncertainty decomposition, DISC-1 discovery report, ASL-1 adversarial rules
- CF-1 counterfactual re-assessment (the what-if engine's baseline isolation), MODELS-1 and FUTURE-1 (the oracle's validated model)
- STAB-1, EXP-1, the capability registry CAPREG-3 and the executor (the research cycle runs only registered actions)
- sessions (SESSION-1 with the VAULT-1 hash chain), the static preview's recorded backend

What did not exist: an entity envelope shared by every object; memory across investigations; discovery genomes and their
comparison; a map of what is unknown; a challenge ledger by question; a completion gate and research debt; a causal graph of the
measurement process; hypothetical observation plans under a validated model with evidence negotiation; relationships between
investigations; reproduction manifests and comparison classes; a what-if engine over the brief's six questions; a sensitivity
fingerprint; an instrumental reality check; an uncertainty budget with classes; bounded autonomy levels; time capsules, handoffs
and a knowledge export.

## 2. Feature-preservation matrix

| Area | Before | After | Evidence |
|---|---|---|---|
| Pipeline and assessment (Phases 1–4) | unchanged | unchanged; record hashes identical | unit tests, e2e `a`–`o` |
| Discovery environment (Phase 5) | unchanged | unchanged | e2e `l`, `m`, `n`, `o`, `p`, `q` |
| Research operating system (Phase 6) | unchanged | `reproduce_independent` added to the registry; every earlier action intact | `test_registry_*`, `test_executor_implements_every_registered_action`, e2e `s1`–`s10` |
| Frontier laboratory (Phase 7) | unchanged | unchanged | e2e `t1`–`t8` |
| Epistemic layer (Phase 8) | unchanged | unchanged; read by Phase 9 | e2e `e1`–`e9`, `test_epistemic.py` |
| Sessions | v0.8 fields | four optional fields added (challenges, completion, capsules, cycles); 0.5–0.8 sessions still validate | `test_research_session.py`, `test_session_accepts_v07_fields_and_keeps_06_sessions_valid` |
| Navigation | every earlier workspace | one more: *Scientific Intelligence* (research level), with twelve panels | e2e `r`, `y`, `i1`–`i6` |
| Tests | 323/2 unit, 107 e2e | 348/2 unit, 119 e2e; none removed or weakened | TEST_REPORT v0.9.0 |

## 3. Decisions: build, compose, defer

| System | Decision | Where |
|---|---|---|
| A Cosmic Memory | built (MEMORY-1): statuses M1–M6, concept recall, failure warnings, outdated detection, knowledge evolution; explanations never promoted | `memory.py`, `intelcore.recall/failureWarnings`, panel *Research Memory* |
| B Discovery Genome | built (DGENOME-1): 13 fields with citations, structural comparison without a score | `dgenome.py`, panel *Discovery Genome* |
| C What-If engine | built (WHATIF-1) on CF-1: six questions, refusals where no method exists, hypothetical visit for motion | `whatif.py`, `intelcore.hypotheticalVisit`, panel *What-if Lab* |
| D Causality Lab | built (CAUSAL-1): documented graph, confounders, temporal association, interventions as re-analyses, criteria C1–C5; C5 never met | `causal.py`, panel *Causality Lab* |
| E Unknown Universe | built (UNKNOWN-1): eight regions U1–U8, one region per item, each item with its basis | `unknownmap.py`, panel *Unknown Universe* |
| F Observation Oracle | built (ORACLE-1): plans under the validated model, expected significance and Δχ², information gain not computed | `oracle.py`, panel *Observation Oracle* |
| G Scientific Adversary | built (ADV-1): ledger by eight questions; every entry names its rule; resolution needs a reference | `adversary.py`, panel *Scientific Adversary* |
| H Research Autopilot | built (CYCLE-1) on CAPREG-3 and the executor: advisory, supervised, restricted automation, audit log in the session | `autonomy.py`, `capabilities.AUTONOMY_LEVELS`, panel *Research Cycle* |
| I Reproduction Network | built (REPRONET-1) with REPROX-1: manifests, validation, six comparison classes | `repronet.py`, panel *Reproduction Network* |
| J Multi-Discovery Network | built (MDNET-1): nine rules, each edge with basis and limitation | `mdnet.py`, panel *Multi-Discovery Network* |
| K Decision theory | **partial**: NEXTX-1 decisions, oracle rankings with stated rules and registered costs exist; no utility workbench (utilities would be opinions presented as numbers) | catalogue P9 "Decision-theory workbench" (B) |
| L Sensitivity fingerprint | built (FINGERPRINT-1) | `fingerprint.py` |
| M Instrumental reality check | built (INSTCHECK-1), nine checks | `instcheck.py` |
| N Time capsule | built (CAPSULE-1, browser): export with digest, recorded in the session; no import verifier | `intelui.js` |
| O Evidence negotiation | built (EVNEG-1) | `oracle.negotiation` |
| P Research debt | built (DEBT-1) | `gate.debt` |
| Q Discovery Observatory | built as the *Command Center* panel over the investigations the server holds | `intelui.js` |
| R Method marketplace | **composed**: the Phase 8 method genome (METHOD-DNA-1) is the local catalogue of methods with inputs, assumptions, limitations and tests; no external endorsements exist or are shown | `methodgenome.py`, Reasoning workspace |
| S Lineage explorer | **composed**: LINEAGE-1 and EPI-1 traces (Phase 8); genome fields and gate items open the reasoning graph | `lineage.py`, `reasoningui.js` |
| T Uncertainty budget | built (BUDGET-1) | `budget.py` |
| U Hypothesis evolution | **partial**: HYPO-1 status per remembered run and versioned user hypotheses; no per-event timeline of weakening and strengthening | panel *Research Memory* |
| V Collaboration protocol | built as a Markdown handoff; no live collaboration | `intelui.js` |
| W Knowledge export | **partial**: `skytrace.knowledge/1` export with entity schema and digest; no import validator for it | `intelui.js` |
| X Integrity gate | built (GATE-1) | `gate.py`, panel *Integrity Gate* |

Python and browser: the session-dependent rules run in the browser so that the static preview works; they are ports of the
Python functions and parity-tested (`test_browser_intelligence_functions_match_python`), as in Phases 6–8. Everything else is
computed once by Python and recorded for the preview.

## 4. What is blocked or unverified

- **Real data.** Every Phase 9 result shown is computed on the synthetic fixtures. No real SPHEREx data was retrieved (IRSA
  refused). Nothing in the intelligence layer is evidence about the sky.
- **Corpus size.** The corpus holds only the investigations a server or preview holds (two fixtures, several runs each). Memory
  recall and network relations are exercised, but on a corpus too small to show patterns.
- **Model features.** Semantic recall with embeddings, multi-agent research and live model answers stay blocked (no verified
  provider, proxy 403).
- **Hosted preview.** See TEST_REPORT v0.9.0 for whether the republished preview was opened in a browser.
