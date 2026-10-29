# Skytrace

Skytrace investigates NASA SPHEREx's repeated near-infrared images of the same piece of sky. Pick a target and it finds every SPHEREx image covering it. It measures the target in each image and compares epochs only where the comparison is physically meaningful. It then reports what changed, how it was measured and how certain it is. Every claim traces back to the archive file it came from. A research copilot (Meta Model API) explains the evidence through read-only tools, and an evidence guard blocks any answer the data do not support.

**The model explains. The algorithms measure. The data provide evidence. The user investigates.**

![Time Machine comparing two wavelength-matched observations](docs/screenshots/time-machine-matched.png)

## Status (v0.2.0, 2026-10-29)

| Part | State |
|---|---|
| Application (API + web interface) | Works end to end; browser acceptance test passes (10/10) offline |
| Scientific pipeline | Works end to end on SPHEREx-format files; validated on synthetic data with known truth |
| Real SPHEREx data | **Not yet acquired.** The build environment could not reach IRSA. The five challenge targets show an honest "no data yet" state with the command that fetches their data |
| Acquisition (`scripts/acquire_targets.py`) | Built and tested against a mocked archive; **not yet run against the real one** |
| FITS/WCS reading | Uses astropy when installed; otherwise a built-in NumPy reader. **The built-in reader has never been checked against astropy on a real file:** astropy could not be installed here, and the live test that does this comparison needs network access |
| Meta copilot | Tool loop, guard and fallback built and tested with a scripted client. **No live Meta API call has been made** (no network, no key). Without a key, a clearly labelled local assistant answers |
| Tests | 121 unit + API tests and 10 browser steps pass. The 4 live tests fail here for lack of network |

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

SPHEREx detectors sit behind linear variable filters, so a star's measured wavelength depends on where it lands. Two images from different dates usually sample different wavelengths. Comparing their brightness directly mostly shows the star's spectrum, not a change. Skytrace compares fluxes only between images from the same detector whose wavelengths at the target agree within half a channel (rule `WLMATCH-1`), and it records every rejected pair with its reason.

Motion is measured per exposure against Gaia DR3 reference stars moved to that exposure's date. The pipeline masks neighbours, isolates and quality-checks the reference stars, and solves an affine plate with leave-one-out outlier rejection. The target's fitted proper motion is then compared with the catalogue. Fixed, versioned rules (`ASSESS-1`) classify each question. The outcomes are: motion detected, motion inconsistent with the catalogue, limited by registration, variability candidate, spectral differences only, mostly unusable data, insufficient evidence, or no significant change. A candidate is never called a discovery. Details: [docs/SCIENTIFIC_METHODS.md](docs/SCIENTIFIC_METHODS.md).

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
fixtures/synthetic/          SYNTHETIC bundles (generated; scripts/make_synthetic_fixtures.py)
data/bundles/                real archive bundles (created by scripts/acquire_targets.py)
scripts/                     acquire, index, verify bundles, analyse, smoke-test Meta, verify, release
tests/                       unit/, integration/ (API), e2e/ (browser), live/ (real services)
docs/                        architecture, methods, provenance, limitations, reproducibility, AI use, test report
```

Documentation: [Architecture](docs/ARCHITECTURE.md) · [Scientific methods](docs/SCIENTIFIC_METHODS.md) · [Data provenance](docs/DATA_PROVENANCE.md) · [Limitations](docs/LIMITATIONS.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Model integration](docs/MODEL_INTEGRATION.md) · [AI use](docs/AI_USE.md) · [Test report](docs/TEST_REPORT.md) · [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md)

## Data credits

SPHEREx Quick Release Spectral Images, NASA/IPAC Infrared Science Archive: QR3 doi:10.26131/IRSA662, QR2 doi:10.26131/IRSA652. Gaia DR3 (ESA; Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1). SIMBAD (CDS, Strasbourg).
