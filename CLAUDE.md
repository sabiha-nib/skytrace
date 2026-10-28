# CLAUDE.md — SKYTRACE

Evidence-first investigation of repeated SPHEREx observations. Built for Meta (not a hackathon submission).

## Commands
- Tests: `pytest` (deterministic, no network) · `pytest -m live` (real services)
- Feasibility: `python scripts/feasibility.py [--wavelengths] [--target NAME]`
- Investigation: `python scripts/run_pipeline.py "<target>"` (add `OFFLINE=1` to replay from cache)
- Model check: `python scripts/meta_smoke_test.py` (needs `META_API_KEY`)

## Data
- SPHEREx QR3 by default (DOI 10.26131/IRSA662), QR2 fallback (10.26131/IRSA652). Never cite QR1.
- Use only interfaces documented by IRSA (SIA2 collections, TAP spherex.*, cutout query string). Do not invent endpoints.
- Every acquired byte gets a `Provenance`; origins are `live | cache | fixture | synthetic` and must be shown truthfully.

## Science boundaries
- All measurement code lives in `src/skytrace/science/`: no network, no model calls, deterministic, tested.
- Flux comparisons only between wavelength-matched pairs (`WLMATCH-1`). Record every rejection.
- Never fill missing values: return NaN/None with a status and log it.
- Significance (`z`) is not probability and not classification. Candidates are not discoveries.
- Synthetic data must use `provenance.synthetic()`; reports containing it are bannered.

## AI boundaries
- Meta Model API via `ai/meta_client.py` only, key from env, backend only. No contributor models by default.
- Model sees only `ai/tools.py` outputs; answers must pass `ai/guard.py`. No code-execution or file tools.

## Definition of done for a gate
Executed, with evidence recorded in `docs/` or `data/`. Plausible-looking code is not evidence.
