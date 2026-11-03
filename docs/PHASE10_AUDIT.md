# Phase 10 audit: the universal frontier (v0.10.0)

Phase 10 asked for two things of different weight. Part I — six interface languages (English, Bangla, Hindi, Spanish, French,
German) with a central architecture, terminology, multilingual reports, cross-language search, a translation quality observatory
and per-language visual checks — was mandatory and release-blocking. Parts II–V listed some twenty-five further systems (world
model, research singularity lab, signal intelligence, multimodal intelligence, convergence, paradox engine, negative space,
information gain oracle, model arena, digital twin, discovery radar, peer review simulator, knowledge compiler, director, agents,
marketplace, flight recorder, handoff, accessibility levels, explainability, atlas, timeline, open science gateway, a unified
environment and a command palette), to be built selectively — "do not implement features simply to increase the implemented
count". Part VII asked for an 800-idea catalogue; Part IX set gates A–E.

Every earlier rule still applied, and Phase 10 added its own, among them: keyword matching is never called semantic search;
translation must not change a conclusion; AI-made translations are distinguished from the computation; local absence is never
global novelty; repeated use of the same data is not independent confirmation; a contradiction is a lead, not a paradox; a
non-detection does not prove absence; no manufactured probabilities or information-gain values; no single leaderboard; a
simulation is not an observation; no simulated live monitoring; simulated review is not a real reviewer; passing compilation is
not proof; agents sharing a model are not independent; an unvalidated method is not "recommended"; no cryptographic claims
without enforcement; nothing published automatically; and a successful build is not a successful preview.

## 1. Repository audit (before any Phase 10 change)

| Item | State at commit `01fa057` (v0.9.0 plus its test report) |
|---|---|
| Version | 0.9.0 (`src/skytrace/__init__.py`, `pyproject.toml`) |
| Working tree | clean; no uncommitted user work |
| Unit, integration, robustness and parity tests | 348 passed, 2 skipped (astropy not installed) |
| Browser tests | 119 passed (TEST_REPORT v0.9.0) |
| Static preview | https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT, version 8 (0.9.0) |
| Release artifacts | 0.2.0–0.9.0 archives with `.sha256` and `RELEASE_MANIFEST-<ver>.json`; 0.9.0 `1388418f…`, preview `2db9f41f…` |
| External services | IRSA, SIMBAD, Gaia, the Meta API, PyPI and npm refused by the proxy. No astropy, no Meta key |
| Data | Two synthetic fixtures (`syn-hpm-1`, `syn-var-1`). No real SPHEREx bundle |
| Languages | English only; every interface string hard-coded in `web/index.html` and the ES modules; reports English only |

What already existed and was reused rather than rebuilt (Phase 10 adds sections to these workspaces instead of new copies):

| Phase 10 system | Already present | Phase 10 decision |
|---|---|---|
| §15 Information Gain Oracle | INFO-1 (v0.7), ORACLE-1/EVNEG-1 (v0.9): expected significance and Δχ²; information gain withheld without defensible priors | **Kept**; nothing added (a new number would need priors that do not exist) |
| §16 Model Arena | MODELS-1 (v0.8): several models, no single ranking | **Composed**: SIGNAL-1 model comparison reports BIC only when its assumptions hold |
| §17 Research Digital Twin | TWIN-1 (v0.7) instrument twin; Synthetic Observatory | **Kept**, not renamed: it is not validated as a physically accurate twin, and says so |
| §18 Discovery Radar | RADAR-1 (v0.6) | **Extended**: OPP-2 ten fields and novelty scope; EXTSRC-1 sources "not connected" |
| §19 Peer Review Simulator | REVIEW-1, REVIEWX-1 (v0.7–0.8) | **Extended**: AGENTS-1 debate record in Review & Story; never presented as a real reviewer |
| §20 Knowledge Compiler | SCICOMP-1 (v0.8) | **Extended**: KCOMP-1 five statuses |
| §14 Negative Space | NEG-1 (v0.8) | **Extended**: NEGX-1 nine distinctions |
| §13 Paradox Engine | ADV-1 challenge ledger, KBOUND-1 | **Built** LEAD-1 (contradictions as research leads); not called paradoxes |
| §21 Investigation Director | CYCLE-1 (v0.9), executor | **Built** DIRECT-1 on top: approval per step, audit log |
| §24 Flight Recorder | VAULT-1 session hash chain | **Built** FLIGHT-1 replay; tamper-evident only |
| §26 Accessibility levels | three levels (v0.5) | **Renamed** Explorer / Researcher / Advanced |
| §28 Research Atlas | Knowledge graph (v0.6), MDNET-1 (v0.9) | **Composed** into WORLD-1; no new atlas |
| §31 Command palette | palette (v0.6) | **Extended** with terminology and cross-language search |

## 2. Feature preservation

No workspace, route, method, test or release artifact was removed. Record hashes of both fixtures are unchanged, English
Markdown reports are byte-identical to 0.9.0 (checked once by rendering both fixtures with `report.py` from `01fa057` and from
this release; `test_report_in_six_languages_keeps_every_number_and_engine_statement` checks that `lang="en"` and the default
agree and that every language keeps every number), and every earlier test runs unchanged and passes (see TEST_REPORT v0.10.0). Two earlier user-facing behaviours were
changed on purpose:
- the level names Explorer / Investigator / Researcher became Explorer / Researcher / Advanced (the brief's names); the
  underlying identifiers (`explore`, `investigate`, `research`) and every saved preference are unchanged;
- the Settings dialog is new; the language selector also sits in the navigation bar;
- the top bar wraps onto a second line when its controls do not fit (they include the language picker now, and translated
  labels vary in length); below 1500 px the visible "Target" caption and the ⌘K hint are dropped first. The keyboard shortcuts
  Alt+1–9 keep their 0.9 targets at the Researcher level: the new World Model sits at the Advanced level for that reason.

## 3. Decisions for Parts II–V

| § | System | Decision | Where | Why / limit |
|---|---|---|---|---|
| 8 | Cosmic World Model | **Built** WORLD-1 | World Model workspace | structural graph of the investigation with a basis per edge and an exact query; not a model of the universe |
| 9 | Research Singularity Lab | **Composed** OPP-2 into the Discovery Radar | Radar | novelty limited to "new to this collection"; "underexplored in indexed sources" not evaluated (no literature index) |
| 10 | Signal Intelligence | **Built** SIGNAL-1 | Signal Intelligence workspace | ten methods with applicability rules and known-answer tests; no false-alarm probabilities |
| 11 | Multimodal | **Built** MODAL-1 | World Model → Measurements | only the modalities the record holds (photometry, astrometry, spectrum points, images) |
| 12 | Convergence | **Built** CONV-1 | World Model → Convergence | exposure-independent lines only; runs of the same bundle never confirm one another |
| 13 | Paradox Engine | **Built as** LEAD-1 | World Model → Research leads | a contradiction is a lead |
| 14 | Negative Space | **Extended** NEGX-1 | Negative Space | nine distinctions with "does not mean" |
| 15 | Information Gain | **Kept** (Phase 7/9) | Frontier / Intelligence | no defensible priors, so no information-gain value |
| 16 | Model Arena | **Kept + composed** | Epistemic / Signal | no leaderboard |
| 17 | Digital Twin | **Kept** TWIN-1 | Frontier | not described as physically accurate |
| 18 | Discovery Radar | **Extended** EXTSRC-1 | Radar | every source "not connected"; no monitoring, no updates shown |
| 19 | Peer Review Simulator | **Extended** AGENTS-1 | Review & Story | rule sets, not people |
| 20 | Knowledge Compiler | **Extended** KCOMP-1 | Scientific Compiler | passing is not proof |
| 21 | Director | **Built** DIRECT-1 | Research Autopilot | approval before each step; never acquires data or publishes |
| 22 | Agent collaboration | **Built** AGENTS-1 (rule sets) | Review & Story | shared model and data; no model calls |
| 23 | Experiment Marketplace | **Built** EXPMKT-1 | Experiments | "recommended" only with a known-answer test |
| 24 | Flight Recorder | **Built** FLIGHT-1 | Open Science Gateway | tamper-evident, not cryptographic |
| 25 | Handoff Protocol | **Built** HANDOFF-1 | Open Science Gateway | versioned schema, validation, digest; Python/JS parity |
| 26 | Accessibility mode | **Renamed** levels | header, Settings | the same investigation at three depths |
| 27 | Explainability | **Built** EXPLAIN-1 | Multilingual Research → Explanations | eight layers, six languages |
| 28 | Research Atlas | **Composed** | World Model, Knowledge Graph | no separate atlas |
| 29 | Discovery Timeline | **Built** TIMES-1 | World Model → Timeline | four kinds of time; event time "not determined" |
| 30 | Open Science Gateway | **Built** OSG-1 | Open Science Gateway | nothing uploaded; no licence declared, and it says so |
| 31 | Unified environment, palette | **Extended** | navigation, palette | four new workspaces in the existing groups (Analyze, Evidence, Knowledge, Publish) |
| 33 | Six-language responsive validation | **Done** | `scripts/phase10_screenshots.py`, TEST_REPORT | 6 languages × 3 sizes, screenshots inspected |

**Not built**: live monitoring of external sources (no network; would be fabricated), semantic search (no embedding model),
multi-user collaboration, a literature novelty check, information-gain values, native-speaker review of translations,
right-to-left scripts.

## 4. Part VII catalogue

`scripts/phase10_catalogue.py` → [PHASE10_CATALOGUE.md](PHASE10_CATALOGUE.md) and `docs/phase10_catalogue.json`: 800 ideas in 65
domains, each with ten fields. 600 Phase 9 concepts are carried over and re-mapped (one overstated name corrected: "Semantic
search across investigations" is now "Exact and concept-recall search … (no semantic search: no embedding model)"), and 200 new
ideas added. Classes: A 372 implemented and tested (every A cites an existing file and an existing test function, checked by
`test_phase10_catalogue.py`), B 163 implementable now, C 177 need data or infrastructure, D 88 speculative or out of scope.

## 5. Commits

Phase 10 was written in this session after the baseline above, and committed as one commit on `master` (local; nothing
pushed). See TEST_REPORT v0.10.0 for the commit id, the gates and the release.
