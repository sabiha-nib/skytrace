# Architecture

```
            ┌──────────────── network (only here) ────────────────┐
            │ IRSA SIA2/TAP/cutouts   SIMBAD TAP   Gaia DR3 TAP     │
            └───────────────┬─────────────────────────────────────┘
                            │ archive/net.py: timeouts, retries, size cap, atomic cache, OFFLINE=1
scripts/acquire_targets.py ─┤ archive/acquire.py (selection SEL-1, resume, inspection)
                            ▼
                 data/bundles/<target>/      fixtures/synthetic/<target>/
                 manifest.json (sha256 + provenance per file), target.json, references.json,
                 discovery.json (every image found, included or excluded with reason), inspection.json, images/*.fits
                            │  bundle.verify(): checksums, completeness, kind markers
                            ▼
   analysis.run(bundle, params) ── science/ (deterministic, no network, no model)
        coords · wavelength (WLMATCH-1) · flags (FLAGPOL-1) · centroid (CENTROID-G2D-1, NBMASK-1, TGT-1)
        photometry (APPHOT-1) · astrometry (REFSEL-1, PLATE-LOO-1, LINFIT-LOO-1) · variability (PAIRDIFF-1) · assess (ASSESS-1)
                            ▼
   report.Investigation: every step logged (ok / rejected / failed / skipped / info) with provenance; content hash
                            ▼
   view.InvestigationView + evidence_graph  ◄── ai/tools.py (11 read-only tools) ◄── ai/copilot.py ──► Meta Model API
                            │                                ai/guard.py (GUARD-2)     ai/local.py (fallback)
                            ▼
   server/app.py (Starlette): JSON API + static web/        ──►  browser (web/js: no build, no CDN, strict CSP)
```

## Layers and their rules

| Layer | Code | May | May not |
|---|---|---|---|
| Data | `archive/`, `bundle.py`, `fitsio.py`, `wcs.py` | fetch (acquisition only), cache, verify, read FITS | modify downloaded files; substitute unrelated data; label cache as live |
| Science | `science/`, `analysis.py` | measure, compare, classify with fixed rules | use the network; call a model; fill missing values |
| Interpretation | `ai/` | read logged evidence through tools, explain, suggest | measure; fetch; run code; read files; reach arbitrary URLs |
| Application | `server/`, `web/` | serve verified bundles, run analyses, mediate the copilot | contact archives; expose the API key |

## Key decisions

- **Bundles as the only analysis input.** Acquisition (network) and analysis (offline) are separate programs. Offline operation is therefore structural, not a mode bolted on: the server never calls an archive.
- **Native FITS/WCS fallback.** astropy could not be installed in the build environment. `fitsio.py` and `wcs.py` implement the subset SPHEREx products use: image and binary-table HDUs, TAN-SIP, and the `-TAB` spectral WCS. astropy is used whenever installed. The two are compared on synthetic files when astropy is present, and on a real cutout by `tests/live`.
- **Starlette, not FastAPI.** FastAPI was not installable here (no package index); Starlette and uvicorn were. The API is small enough that FastAPI's extras are not needed.
- **No frontend build.** Plain ES modules and an SVG/canvas implementation keep the interface installable and runnable offline with zero JavaScript dependencies. A strict Content-Security-Policy (`script-src 'self'`, no eval, no inline scripts) is enforced.
- **In-memory investigations, file-based records.** Analysis results are cached in memory by content hash. Saved investigations are JSON files in `data/records/`. That is enough for a single-user instrument; a multi-user deployment would need accounts and a database.
- **Not introduced:** agent frameworks, MCP servers, vector databases, task queues. Nothing in the requirements needed them.

## Request flow for one copilot question

1. `POST /api/investigations/{id}/ask` → `copilot.ask` builds a `ToolSession` over the stored record.
2. With a Meta key and `OFFLINE` unset, the model receives the system rules, a compact context (target, kind, outcome categories) and 11 tool schemas. It calls tools; each call is validated by pydantic and recorded.
3. The final JSON answer goes through `guard.check` against the outputs of the tools actually called. On failure, one repair round runs. A second failure withholds the draft and returns the local assistant's grounded answer instead.
4. Without a key, offline, or on any API error, the local assistant answers through the same tools and the same guard. The response always states which mode produced it.
