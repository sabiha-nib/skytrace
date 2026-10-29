# SKYTRACE — Phase 1 Implementation Plan

> Superseded by v0.2.0: see [ARCHITECTURE.md](ARCHITECTURE.md), [TEST_REPORT.md](TEST_REPORT.md) and [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md). `pipeline.py` and `run_pipeline.py` were replaced by `archive/acquire.py` (network) and `analysis.py` (offline).

Updated 2026-10-29. Supersedes the hackathon-specific parts of `PHASE0_RECON.md`: SKYTRACE is now built for Meta, not as a Space Apps submission, so demo-length limits, submission rules and pre-event-work rules no longer apply (risks K2, K3 retired; R26/R27 reframed).

## Gate A — workspace audit (done)

| Finding | Consequence |
|---|---|
| Repository created at `skytrace/` in the cloud workspace; Phase 0 docs moved into `docs/`. | Project root confirmed. |
| This workspace cannot reach IRSA, SIMBAD, the Gaia archive, the Meta API, PyPI or npm (proxy `403 Forbidden`; DNS failure for PyPI). | Gates B, C (real data) and E (live model) cannot be executed here. |
| astropy / photutils are not installed and cannot be installed (no package index; building from GitHub source was refused by the workspace's safety policy). | FITS/WCS reading is written against astropy but untested; all math is pure NumPy/SciPy and tested. |
| Outdated items in the brief: QR2 is not current (QR3, DOI 10.26131/IRSA662, since Sept 2026); old Llama API model IDs are stale (Meta Model API at `api.meta.ai/v1`). | QR3 default, QR2 fallback; adapter targets `muse-spark-1.3` pending a smoke test. |

## Architecture as built

```
config/targets.json            target identities (resolved live; hints are secondary context only)
src/skytrace/
  provenance.py                Provenance records (origin: live | cache | fixture | synthetic)
  archive/   (data layer)
    net.py                     bounded fetch: timeouts, retries, size cap, atomic cache, OFFLINE=1
    tap.py                     TAP sync (CSV) + VOTable parsing
    spherex.py                 SIA2/TAP discovery, cutout URLs, release separation
    references.py              SIMBAD identity, Gaia DR3 astrometry and reference stars
    products.py                astropy reader + inspect_product() schema report   [untested here]
  science/   (deterministic layer; no network, no model)
    coords.py                  parsing, separations, gnomonic, rigorous space motion, parallax term
    wavelength.py              WLMATCH-1 compatibility rule with accept/reject reasons
    flags.py                   FLAGPOL-1; bit numbers only from file header or IRSA docs
    centroid.py                CENTROID-G2D-1 (+ MOMENT-1 cross-check)
    photometry.py              APPHOT-1 with flag rejection and local sky
    astrometry.py              DIFFAST-1 per-exposure plate solution vs Gaia; LINFIT-1 motion fit
    variability.py             PAIRDIFF-1 on wavelength-matched pairs only
    measure.py                 per-exposure measurement on any ProductLike
  pipeline.py                  resolve -> discover -> retrieve -> measure -> compare, all logged
  report.py                    Investigation log, content hash, Markdown report
  ai/        (interpretation layer)
    meta_client.py             OpenAI-compatible adapter; refuses contributor models; OFFLINE aware
    tools.py                   2 read-only pydantic-validated tools over the investigation record
    guard.py                   GUARD-1 number/claim/language checks
    copilot.py                 ≤6 tool calls, ≤8 rounds, 120 s, 1 repair, audit trail, local fallback
scripts/ feasibility.py, run_pipeline.py, meta_smoke_test.py
tests/unit (deterministic, synthetic-labelled) · tests/live (pytest -m live)
```

Not introduced, deliberately: FastAPI and the frontend (Gate F), MCP, agent frameworks, vector DB.

## Gate acceptance criteria

| Gate | Passes when | Status |
|---|---|---|
| A | Root confirmed, plan written, outdated claims identified | **PASSED** |
| B | `scripts/feasibility.py --wavelengths` has run live; matrix lists real images per target with λ-at-target and flags; ≥1 target has ≥2 wavelength-matched epochs or ≥2 plate-solvable epochs | **BLOCKED** (no network) — script written and executed; it recorded the denial |
| C | `scripts/run_pipeline.py` produces a report from real data for ≥1 target, with rejected observations listed | **BLOCKED** on B; pipeline verified end-to-end on synthetic images |
| D | Methods' bias/uncertainty verified (synthetic pull tests) **and** a real-data comparison with Gaia DR3 | **PARTIAL** — synthetic part passes; real part blocked |
| E | Smoke test records a successful tool call and structured output with the configured model | **BLOCKED** (no network, no key); adapter + guard tested with a scripted client |
| F | Interactive product | **NOT STARTED** by design |

## Next actions (in order, on a machine with network)

1. `pip install -e ".[astro,dev]"` then `pytest` (expect all unit tests to pass, now including the astropy cross-check).
2. `pytest -m live` — confirms SIA/TAP/SIMBAD/cutout behaviour and prints the real product structure.
3. `python scripts/feasibility.py --wavelengths` → commit `data/feasibility/*`, update `DATA_FEASIBILITY_REPORT.md` with the real matrix.
4. Choose the Gate C target from the matrix (prediction: Epsilon Indi B for astrometry, RW Aur for variability — see the report).
5. `python scripts/run_pipeline.py "<target>"`; inspect every rejected step before trusting any accepted one.
6. Set `META_API_KEY`; `python scripts/meta_smoke_test.py`; record in `docs/MODEL_INTEGRATION.md`.

## Risks (current)

| Risk | Mitigation |
|---|---|
| Real FITS structure differs from docs (extension names, flag keywords, cutout WCS-WAVE offsets) | `inspect_product` runs first per release/detector and is logged; `ProductError` instead of guessing |
| Bright targets (Barnard, R Dra) flagged as overflow/nonlinear | Flagged photometry returns NaN; astrometry may still use wings — must be validated against Gaia before use |
| Gaussian centroid bias with undersampled, chromatic PSF | Bias measured on real reference stars (plate residual RMS); PSF-extension fit planned as Method Arena alternative |
| Blends inflate errors (seen in synthetic crowded fields: motion-fit reduced χ² ≈ 0.04) | Errors are conservative, not biased; report reduced χ²; add blend flagging from Gaia neighbours |
| Parallax not modelled (≤ 547 mas for Barnard, ≤ 271 mas for ε Ind B, ≤ 439 mas for WISE 0855) | Logged as systematic bound; add spacecraft ephemeris (JPL Horizons) if residuals demand it |
| Meta API access/pricing/region | Local deterministic mode is always available and labelled |
