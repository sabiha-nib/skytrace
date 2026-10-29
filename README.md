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

## Status (v0.4.0, 2026-10-29)

Phase 4 made the application previewable without a server and audited every control
([docs/PHASE4_AUDIT.md](docs/PHASE4_AUDIT.md)). Phase 3 (validation) is summarised in
[docs/PHASE3_GATES.md](docs/PHASE3_GATES.md).

Phase 3 was a validation phase: independent checks of the file reader, a calibration and uncertainty audit,
a stricter assessment engine, provenance verification and robustness tests. Gate summary:
[docs/PHASE3_GATES.md](docs/PHASE3_GATES.md).

| Part | State |
|---|---|
| Application (API + web interface) | Works end to end offline; 31 browser tests pass (journey + every control, in both the server and the static-preview mode) |
| Scientific pipeline | Parallax, Gaia quality cuts, visit-averaged motion fit, reference-calibrated photometry and an error-model check added (`skytrace-analysis/2`). Validated on synthetic data with known truth, including 12 robustness scenarios |
| Real SPHEREx data | **Not yet acquired (blocked).** IRSA, SIMBAD and Gaia are refused by this environment's network policy (proxy 403). Nothing here is a real-data result. What to allowlist: [docs/ENVIRONMENT_REPORT.md](docs/ENVIRONMENT_REPORT.md) |
| FITS/WCS reading | Built-in reader validated against 14 independent astropy/wcslib test files with stated tolerances (six defects found and fixed). **Not yet compared with astropy on a real SPHEREx file** |
| Assessment | `ASSESS-2`: every outcome states its sensitivity; a non-detection is never reported as proof, a failed fit never as "no motion" |
| Provenance | `scripts/verify_provenance.py` checks a record against its files' SHA-256, origins, codes and re-run determinism |
| Meta copilot | Tool contract (`TOOLS-2`) and guard (`GUARD-3`) tested with a scripted client. **No live Meta API call has been made (blocked: no route, no key)** |
| Tests | 199 unit/integration/robustness tests and 31 browser tests pass; the 4 live tests fail here for lack of network |

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

- **Wavelength ruler** (always visible): every observation placed by the wavelength measured at the target and by date. Wavelength-matched pairs, the only ones whose brightness may be compared, appear as vertical links.
- **Sky Explorer**: every image with date, detector, wavelength at the target, flags, fit results, plate solution and provenance (source, release, retrieval time, checksum). Overlays show the catalogue position, the measured centroid and the reference stars.
- **Time Machine**: blink, fade or side-by-side views, registered with per-exposure Gaia plate solutions. The difference mode works only for wavelength-matched pairs. A different-wavelength comparison carries a permanent warning that brightness differences there are not evidence of change.
- **Discovery Lab**: deterministic outcomes for data quality, motion and brightness, each with its criteria, evidence, limitations and alternative explanations. Also: motion plots against the catalogue, matched-pair significances, the spectrum, the full measurement table, re-running with different parameters (with a side-by-side sensitivity comparison) and a Markdown report.
- **Evidence Graph**: sources → observations → measurements → comparisons → claims → methods and limitations, built only from recorded events. Selecting a claim traces exactly what supports it.
- **Investigations**: save an investigation (parameters, data checksum, results, copilot conversation), reopen it, and replay it to confirm the content hash matches.
- **Research copilot**: answers questions about the evidence using 11 read-only tools. The panel shows each tool call and its output, tags claims as evidence, interpretation or speculation, links observations, and lists any drafts the guard withheld.

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
src/skytrace/                Python package: archive/ (data layer), science/ (deterministic), ai/ (copilot), server/ (API)
web/                         interface (HTML, CSS, ES modules)
config/targets.json          the five challenge targets
fixtures/synthetic/          SYNTHETIC bundles (generated by src/skytrace/synthetic.py; scripts/make_synthetic_fixtures.py)
data/bundles/                real archive bundles (created by scripts/acquire_targets.py)
scripts/                     diagnose environment, acquire, index, verify bundles, analyse, verify provenance, smoke-test Meta, verify, release
tests/                       unit/, integration/ (API), robustness/ (synthetic variants), e2e/ (browser), live/ (real services)
docs/                        architecture, methods, provenance, limitations, reproducibility, AI use, test report
```

Documentation: [Architecture](docs/ARCHITECTURE.md) · [Scientific methods](docs/SCIENTIFIC_METHODS.md) · [Data provenance](docs/DATA_PROVENANCE.md) · [Limitations](docs/LIMITATIONS.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Model integration](docs/MODEL_INTEGRATION.md) · [AI use](docs/AI_USE.md) · [Test report](docs/TEST_REPORT.md) · [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) · Phase 3: [Gates](docs/PHASE3_GATES.md) · [Environment](docs/ENVIRONMENT_REPORT.md) · [FITS/WCS validation](docs/FITS_WCS_VALIDATION.md) · [Calibration audit](docs/CALIBRATION_AUDIT.md) · [Assessment engine](docs/ASSESSMENT_ENGINE.md) · [Copilot tools](docs/COPILOT_TOOLS.md)

## Data credits

SPHEREx Quick Release Spectral Images, NASA/IPAC Infrared Science Archive: QR3 doi:10.26131/IRSA662, QR2 doi:10.26131/IRSA652. Gaia DR3 (ESA; Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1). SIMBAD (CDS, Strasbourg).
