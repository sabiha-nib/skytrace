# SKYTRACE — The Living Universe

An evidence-first investigation tool for NASA SPHEREx's repeated all-sky near-infrared images (0.75–5 µm, six detectors, 6.2″ pixels). It finds every SPHEREx image covering a target, measures the target in each one, and compares epochs only where the comparison is physically meaningful — then explains the result without inventing anything.

**The model explains. The algorithms measure. The data provide evidence. The user investigates.**

## Status (Phase 1, 2026-10-29)

| | |
|---|---|
| Deterministic science core | Built; 66 unit tests pass (synthetic data, labelled) |
| Archive access (IRSA SPHEREx QR3/QR2, SIMBAD, Gaia DR3) | Built; **not yet run against live services** — the development workspace has no outbound network |
| FITS reading (astropy) | Built; **untested on a real file** |
| Meta Model API adapter + evidence guard | Built and tested with a scripted client; **no live call yet** |
| Interactive UI | Not started (Gate F, after the science core is proven on real data) |

No real measurement has been produced yet. See `docs/DATA_FEASIBILITY_REPORT.md`.

## Why wavelength matching matters

Each SPHEREx detector sits behind a linear variable filter: the wavelength a star is measured at depends on where it lands on the detector. Two images of the same star on different dates usually sample different wavelengths, so a raw "blink" comparison mostly shows the star's spectrum, not a change. SKYTRACE compares fluxes only between images from the same detector whose wavelengths at the star's pixel agree within half a channel (rule `WLMATCH-1`), and lists every rejected pair with its reason.

Motion is measured differently: each exposure gets its own plate solution from Gaia DR3 reference stars propagated to that epoch (`DIFFAST-1`), so pointing and header-WCS errors cancel, and the fitted proper motion is compared with the catalogue value.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[astro,dev]"
cp .env.example .env          # optional: add META_API_KEY
pytest                        # deterministic tests (no network)
pytest -m live                # checks the real IRSA / SIMBAD / Gaia interfaces
```

## Use

```bash
python scripts/feasibility.py --wavelengths       # which targets have usable SPHEREx data
python scripts/run_pipeline.py "Epsilon Indi B"   # full investigation -> data/runs/<target>/report.md
OFFLINE=1 python scripts/run_pipeline.py "Epsilon Indi B"   # replay from cache only, no sockets
python scripts/meta_smoke_test.py                 # verify Meta Model API access
```

Downloads are cached under `cache/<kind>/<release>/` with a provenance sidecar per file. A cached response keeps the time of its original retrieval and is labelled `cache`, never `live`. Fixtures need their own provenance file or they are refused.

## Data sources

| Source | Use | Reference |
|---|---|---|
| SPHEREx Spectral Images QR3 (default) / QR2 (fallback), IRSA | images, flags, variance, spectral WCS | doi:10.26131/IRSA662, doi:10.26131/IRSA652 |
| SIMBAD (CDS) | target identity | simbad.cds.unistra.fr |
| Gaia DR3 (ESA) | target and reference-star astrometry | doi:10.1051/0004-6361/202243940 |

## AI

The Meta Model API (`muse-spark-1.3`, OpenAI-compatible, `https://api.meta.ai/v1`) is used only to explain a finished investigation record. It can call two read-only tools; it cannot fetch data, run code or measure. Every answer must be JSON whose claims cite tool calls, every number must appear in the evidence, discovery language is blocked, and limitations are mandatory (`ai/guard.py`). Without a key, a deterministic, labelled summary is shown instead. Contributor-mode models (which may train on request content) are refused by default.

Development AI: Claude Code (Claude Opus 5.5) wrote this code from the project briefs; methods and acceptance rules are documented in `docs/`.

## Limitations

- Nothing has yet been validated on real SPHEREx data.
- Aperture fluxes have no aperture correction; compare only within wavelength-matched pairs.
- Gaussian centroiding approximates the SPHEREx PSF; the file's PSF extension is not yet used.
- Parallax displacement is not modelled (bounded by the target's parallax; logged per run).
- Flag bits are applied only when their numbers are known from the file header or IRSA documentation.

## Layout

See `docs/PHASE1_IMPLEMENTATION_PLAN.md`. Requirement status: `docs/REQUIREMENT_TRACEABILITY.md`.
