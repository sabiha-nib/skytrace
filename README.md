# Skytrace

Skytrace investigates NASA SPHEREx's repeated near-infrared images of the same piece of sky. Pick a target and it finds every SPHEREx image covering it. It measures the target in each image and compares epochs only where the comparison is physically meaningful. It then reports what changed, how it was measured and how certain it is. Every claim traces back to the archive file it came from. A research copilot (Meta Model API) explains the evidence through read-only tools, and an evidence guard blocks any answer the data do not support.

**The model explains. The algorithms measure. The data provide evidence. The user investigates.**

![Time Machine comparing two wavelength-matched observations](docs/screenshots/time-machine-matched.png)

## Preview

| Way to open it | Command / link | What runs |
|---|---|---|
| **Hosted preview** (claude.ai artifact, private to its owner until shared) | https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT | the static build below: the same interface, with every result precomputed by the Python pipeline from the synthetic targets |
| Static preview, locally | `python scripts/build_static.py && python -m http.server -d dist/preview 8700` → http://127.0.0.1:8700/ | the same files, no backend |
| **Full application** | `OFFLINE=1 python run.py` → http://127.0.0.1:8600 | the server: live analysis with any parameters, the copilot loop, server-side records and replay |

The static preview says on every screen that it is a preview of precomputed results. Things that need the server
(arbitrary parameters, questions about named observations, replay by re-execution) are disabled or refused with
an explanation; pair comparisons, image registration and record-hash checks run in the browser with code that is
tested for parity with the Python implementation.

## Status (v0.6.0, 2026-10-30)

Phase 6 turned the discovery environment into a research operating system: a persistent, validated and hashed research
session; one registry of executable actions used by an investigation planner, workflows, a Discovery Radar of research
opportunities and guided missions; multi-epoch sequences that never interpolate; an experiment studio with negative controls;
a data-quality observatory without scores; an evidence ledger; a research notebook; a figure studio and a knowledge graph;
connector previews; and a copilot that labels where each answer came from ([docs/PHASE6_AUDIT.md](docs/PHASE6_AUDIT.md),
[docs/RESEARCH_METHODS.md](docs/RESEARCH_METHODS.md), [Phase 6 catalogue](docs/PHASE6_CATALOGUE.md)).

Phase 5 turned the investigation tool into a discovery environment built around one loop — explore, observe, compare,
detect, test, explain, verify, preserve, share — with an engine that says what the data can and cannot establish, a
hypothesis arena, an uncertainty explorer, a vault and a report studio ([docs/PHASE5_AUDIT.md](docs/PHASE5_AUDIT.md),
[docs/DISCOVERY_METHODS.md](docs/DISCOVERY_METHODS.md), [feature catalogue](docs/FEATURE_CATALOGUE.md)). Every new
result is computed by versioned, deterministic methods from the recorded investigation; none is a probability, and the
bundled data are still synthetic. Phase 4 (previewable application): [docs/PHASE4_AUDIT.md](docs/PHASE4_AUDIT.md).
Phase 3 (validation): [docs/PHASE3_GATES.md](docs/PHASE3_GATES.md).

| Part | State |
|---|---|
| Application (API + web interface) | Works end to end offline, in both the server and the static-preview mode; every control is exercised by browser tests (counts in [docs/TEST_REPORT.md](docs/TEST_REPORT.md)) |
| Research operating system (v0.6) | Research sessions (SESSION-1), capability registry with actions (CAPREG-2), Investigation Planner (PLAN-1), Command Center, sequences (SEQ-1), compatibility matrix (COMPAT-1), data quality (DQ-1), evidence ledger (LEDGER-1), Discovery Radar (RADAR-1), Experiment Studio (EXP-1), workflows (WF-1), missions (MISSION-1), notebook, figure studio (FIG-2), knowledge graph (KG-1), connector previews (ACQ-2), Copilot 2.0 |
| Discovery environment (v0.5) | Discovery Engine (DISC-1), Hypothesis Arena (HYPO-1), Uncertainty Explorer (UNC-1), registration diagnostics (REGDIAG-1), capability registry (CAPREG-1), reproducibility package (PKG-1), vault, report studio, command palette, glossary, three levels of detail |
| Scientific pipeline | Parallax, Gaia quality cuts, visit-averaged motion fit, reference-calibrated photometry and an error-model check added (`skytrace-analysis/2`). Validated on synthetic data with known truth, including 12 robustness scenarios |
| Real SPHEREx data | **Not yet acquired (blocked).** IRSA, SIMBAD and Gaia are refused by this environment's network policy (proxy 403). Nothing here is a real-data result. What to allowlist: [docs/ENVIRONMENT_REPORT.md](docs/ENVIRONMENT_REPORT.md) |
| FITS/WCS reading | Built-in reader validated against 14 independent astropy/wcslib test files with stated tolerances (six defects found and fixed). **Not yet compared with astropy on a real SPHEREx file** |
| Assessment | `ASSESS-2`: every outcome states its sensitivity; a non-detection is never reported as proof, a failed fit never as "no motion" |
| Provenance | `scripts/verify_provenance.py` checks a record against its files' SHA-256, origins, codes and re-run determinism |
| Meta copilot | Tool contract (`TOOLS-2`) and guard (`GUARD-3`) tested with a scripted client. **No live Meta API call has been made (blocked: no route, no key)** |
| Tests | Unit, integration, robustness, parity and browser suites pass; the live tests fail here for lack of network. Counts and gates: [docs/TEST_REPORT.md](docs/TEST_REPORT.md) |

The bundled data are **synthetic**: two generated targets, SYN-HPM-1 (a fast-moving star) and SYN-VAR-1 (a star that dims). They exist so the whole workflow can be exercised and tested. Every synthetic file carries `SYNTHETIC = T`, every image is watermarked, and the interface labels them on every screen. The data verifier refuses a synthetic file inside an archive bundle.

## Quick start

```bash
python -m pip install -e ".[astro,dev]"   # or: pip install numpy scipy requests pydantic starlette uvicorn astropy
python run.py                             # http://127.0.0.1:8600
```

`python run.py` works without installing the package. Add `OFFLINE=1` to forbid all network use. The bundled synthetic targets work fully offline.

Check everything: dependencies, configuration, secret scan, data checksums and tests.

```bash
python scripts/verify.py           # add --e2e to include the browser test
```

## Getting real SPHEREx data

On a machine with internet access:

```bash
python scripts/acquire_targets.py --all     # SIMBAD + Gaia DR3 + IRSA SPHEREx QR3 (QR2 fallback), resumable
python scripts/build_observation_index.py
python scripts/verify_data_bundle.py
python scripts/verify_provenance.py --all --rerun   # trace each analysis record back to the stored files
pytest -m live tests/live -s                # confirms the archive interfaces and compares the native reader with astropy
```

Each target becomes a bundle in `data/bundles/<target>/`: the original files byte for byte, a manifest with SHA-256 checksums and provenance, the archive search results with the reason for every excluded image, and the real FITS structure as read. Restart Skytrace and the targets appear with their observations. See [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md).

## What you can do in the app

New in 0.6 (workspaces grouped Observe · Investigate · Verify · Record):

- **Research sessions**: everything you do in one line of work — question, runs, hypotheses, notes, plans, experiments, missions, workflows — kept as one validated, hash-checked session. Open, rename, branch, export and import (a changed file is refused).
- **Command Center**: what is loaded, the session, the outcomes, data quality, open radar items and missions, from real values only.
- **Investigation Planner**: ask a question in plain words; get a plan of registered actions with statuses (suggested, ready, running, completed, blocked, failed, needs review). Expensive steps wait for confirmation; inspection steps wait for your written judgement.
- **Time Machine sequences**: play every compatible epoch of one detector, frame by frame, with frame differences; never interpolated; it says when only two visits exist.
- **Data Quality Observatory**: eleven checks with their rules (invalid / incompatible / not available / not checked / valid — no score), the full compatibility matrix with reasons, a metadata diff, time coverage and connector previews.
- **Evidence Ledger**: each claim's support counted by kind, contradictions found by four fixed rules, provenance, methods, completeness and the session's change history.
- **Experiment Studio**: parameter, sensitivity, method-comparison, reproducibility, negative-control and robustness experiments; and validated workflows over several targets with per-item records, cancel and retry.
- **Discovery Radar**: research opportunities, each with what, why, evidence, data needed, method, what it cannot establish, and whether it can run now.
- **Research Notebook**: structured blocks (13 types) that reference recorded values, your text clearly separated from assistant drafts, version history, undo, Markdown export and a deterministic session package.
- **Figure Studio and knowledge graph** (in the Vault): figures with titles, units and provenance exported as SVG; links between saved records and sessions from stored facts only.
- **Missions**: six guided research tasks whose completion is read from the session — no points or badges.
- **Copilot 2.0**: plans, data quality, the ledger and competing explanations as new read-only tools; every answer names its source; add an answer to the notebook as a labelled draft or hand a question to the Planner.

From 0.5:

- **Discovery Engine**: the evidence inventory (every item with source, origin, epoch, checksum; unknown values left empty and counted), research questions marked answerable, answerable with limits, or not answerable (with why), a test plan for each, an evidence review, and rule-based next steps that say what each can and cannot establish.
- **Hypothesis Arena**: competing explanations for each outcome (intrinsic change, calibration change, error model, registration, parallax, …) tested against recorded values by stated rules. Statuses are consistent, contradicted, inconclusive, not tested, evidence unavailable or incompatible; no probabilities. Write your own hypotheses, attach recorded tests, undo a removal.
- **Wavelength ruler** (always visible): every observation placed by the wavelength measured at the target and by date. Wavelength-matched pairs, the only ones whose brightness may be compared, appear as vertical links.
- **Sky Explorer**: every image with date, detector, wavelength at the target, flags, fit results, plate solution and provenance (source, release, retrieval time, checksum). Overlays show the catalogue position, the measured centroid and the reference stars.
- **Time Machine**: blink, fade or side-by-side views, registered with per-exposure Gaia plate solutions. The difference mode works only for wavelength-matched pairs. A different-wavelength comparison carries a permanent warning that brightness differences there are not evidence of change.
- **Discovery Lab**: deterministic outcomes for data quality, motion and brightness, each with its criteria, evidence, limitations and alternative explanations. Also: motion plots against the catalogue, matched-pair significances, the spectrum, the full measurement table, re-running with different parameters (with a side-by-side sensitivity comparison) and a Markdown report.
- **Uncertainty** (Discovery Lab tab): what each recorded uncertainty is made of, bounds shown as bounds, parameter sensitivity kept separate, and the effects no method here quantifies. Any chart can be exported as an SVG that carries its target, investigation hash and method versions.
- **Evidence Graph**: sources → observations → measurements → comparisons → claims → competing explanations, methods and limitations, built only from recorded events. Selecting a claim traces exactly what supports it.
- **Investigations** (vault and report studio): save an investigation with its parameters, data checksum, results, research question, your hypotheses and the copilot conversation; search, tag, rename, duplicate, compare two, reopen, replay; import with a preview and a content-hash check before anything is stored. Export the report, record, evidence graph, discovery report or a deterministic reproducibility package with SHA256SUMS.
- **Everywhere**: the discovery-loop bar, a command palette (Ctrl/⌘+K or /), a glossary and shortcut reference (?), Alt+1…9 for the visible workspaces, back/forward history, and three levels of detail (Explore, Investigate, Research) that change what is shown, never what is computed.
- **Research copilot**: answers questions about the evidence using 16 read-only tools, laid out as Answer · Evidence · Method · Limitations · Next step. It can say what Skytrace can do here from the capability registry. The panel shows each tool call and its output, tags claims as evidence, interpretation or speculation, links observations, and lists any drafts the guard withheld.

## How the science works

SPHEREx detectors sit behind linear variable filters, so a star's measured wavelength depends on where it lands. Two images from different dates usually sample different wavelengths. Comparing their brightness directly mostly shows the star's spectrum, not a change. Skytrace compares fluxes only between images from the same detector whose wavelengths at the target agree within half a channel, allowing for the 1 nm accuracy of the wavelength solution, and from the same archive release (rule `WLMATCH-2`). It records every rejected pair with a reason code, and divides out exposure-level calibration changes using reference stars measured in the same two images (`PAIRDIFF-2`).

Motion is measured per exposure against Gaia DR3 reference stars (RUWE ≤ 1.4) placed at their apparent positions on that exposure's date, including parallax; exposures from one visit are averaged before the motion fit. The pipeline masks neighbours, isolates and quality-checks the reference stars, and solves an affine plate with leave-one-out outlier rejection. The target's fitted proper motion is then compared with the catalogue. Fixed, versioned rules (`ASSESS-2`) classify each question and state the smallest change the data could have detected. Non-detections are reported "at this sensitivity", never as proof; failed measurements and calibration-limited comparisons have their own outcomes. A candidate is never called a discovery. Details: [docs/ASSESSMENT_ENGINE.md](docs/ASSESSMENT_ENGINE.md). Details: [docs/SCIENTIFIC_METHODS.md](docs/SCIENTIFIC_METHODS.md).

## Meta Model API

Copy `.env.example` to `.env`, set `META_API_KEY` (or `MODEL_API_KEY`) and run `python scripts/meta_smoke_test.py`. The adapter calls `POST https://api.meta.ai/v1/chat/completions` with model `muse-spark-1.3`. Requests are bounded: at most 8 tool calls, 10 rounds and 150 s per question, with retries that honour `Retry-After`. Contributor-mode models, which may train on request content, are refused by default. The API key stays on the server and never reaches the browser, logs or saved records. Details: [docs/MODEL_INTEGRATION.md](docs/MODEL_INTEGRATION.md).

## Deployment

Skytrace is one Python process serving the API and the static interface. The interface needs no build step and loads nothing from the internet.

```bash
SKYTRACE_HOST=0.0.0.0 SKYTRACE_PORT=8600 python run.py
```

A `Dockerfile` is included. It has **not been built here**, because the build environment cannot pull base images. For a shared deployment, put Skytrace behind a reverse proxy with TLS. It has no user accounts, and saved investigations are visible to everyone who can reach it.

## Repository

```
run.py                       start the app (no install needed)
src/skytrace/                Python package: archive/ (data layer), science/ (deterministic), ai/ (copilot), server/ (API),
                             research OS readers (session, planner, compat, quality, ledger, radar, experiments, missions, workflows, connectors)
web/                         interface (HTML, CSS, ES modules)
config/targets.json          the five challenge targets
fixtures/synthetic/          SYNTHETIC bundles (generated by src/skytrace/synthetic.py; scripts/make_synthetic_fixtures.py)
data/bundles/                real archive bundles (created by scripts/acquire_targets.py)
data/sessions/               research sessions saved by the server (git-ignored)
scripts/                     diagnose environment, acquire, index, verify bundles, analyse, verify provenance, smoke-test Meta, verify, release
tests/                       unit/, integration/ (API), robustness/ (synthetic variants), e2e/ (browser), live/ (real services)
docs/                        architecture, methods, provenance, limitations, reproducibility, AI use, test report
```

Documentation: [Architecture](docs/ARCHITECTURE.md) · [Scientific methods](docs/SCIENTIFIC_METHODS.md) · [Discovery methods](docs/DISCOVERY_METHODS.md) · [Research methods](docs/RESEARCH_METHODS.md) · [Feature catalogue (0.5)](docs/FEATURE_CATALOGUE.md) · [Phase 6 catalogue](docs/PHASE6_CATALOGUE.md) · Phase 6: [Audit](docs/PHASE6_AUDIT.md) · [Preview](docs/PREVIEW.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Release notes](docs/RELEASE_NOTES.md) · Phase 5: [Audit](docs/PHASE5_AUDIT.md) · [Data provenance](docs/DATA_PROVENANCE.md) · [Limitations](docs/LIMITATIONS.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Model integration](docs/MODEL_INTEGRATION.md) · [AI use](docs/AI_USE.md) · [Test report](docs/TEST_REPORT.md) · [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) · Phase 3: [Gates](docs/PHASE3_GATES.md) · [Environment](docs/ENVIRONMENT_REPORT.md) · [FITS/WCS validation](docs/FITS_WCS_VALIDATION.md) · [Calibration audit](docs/CALIBRATION_AUDIT.md) · [Assessment engine](docs/ASSESSMENT_ENGINE.md) · [Copilot tools](docs/COPILOT_TOOLS.md)

## Data credits

SPHEREx Quick Release Spectral Images, NASA/IPAC Infrared Science Archive: QR3 doi:10.26131/IRSA662, QR2 doi:10.26131/IRSA652. Gaia DR3 (ESA; Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1). SIMBAD (CDS, Strasbourg).
