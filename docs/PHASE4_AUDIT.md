# Phase 4 audit — previewable application (2026-10-29)

## Baseline (verified in this run)

| Item | Finding |
|---|---|
| Repository | `/home/claude/skytrace`, git, clean at `dc5cc20` (v0.3.0) |
| Frontend | `web/`: vanilla ES modules (13 files, ~2,050 lines), one stylesheet, no build step, no framework, no package manager. Served by the Python server at `/static/*` |
| Backend | `src/skytrace/server/app.py` (Starlette + uvicorn): 18 routes (status, targets, images, registered pair images, analyse, stability, investigation, graph, report, ask, records CRUD + replay). Strict CSP, no external requests |
| Start command | `python run.py` (add `OFFLINE=1`) → `http://127.0.0.1:8600`. **Started successfully** on port 8611 with `OFFLINE=1`; `/api/status` answered |
| Browser check | Chromium (Playwright) opened every workspace at 1440×900, 820×1100 and 390×844 after running the analysis: no JavaScript errors, no console errors, no external requests, no horizontal page overflow. Screenshots inspected |
| Data | Only the two **synthetic** bundles (`fixtures/synthetic/syn-hpm-1`, `syn-var-1`). No real archive bundle exists; acquisition is still blocked (proxy 403 to IRSA/SIMBAD/Gaia, see `ENVIRONMENT_REPORT.md`). The five challenge targets show a no-data state |
| Meta | No key, `api.meta.ai` refused; copilot runs the labelled local deterministic assistant |
| Tests | 193 unit/integration/robustness passed, 2 skipped (astropy); 11 browser steps passed; `verify.py --e2e` 17/17 (Phase 3 final run) |

## Blocker for "the user can open and interact with it"

The app runs only inside this cloud container. The user cannot reach `127.0.0.1` here, and there is no
persistent public preview server. The environment does offer **published artifacts** (a hosted web page
with supporting files), but those are static: no Python server runs behind them.

## Plan

1. **Static preview build** (`scripts/build_static.py` → `dist/preview/`): the *same* frontend code, with
   `api.js` switched to a static adapter. Everything the server would compute for the synthetic bundles is
   precomputed by the real Python code at build time and shipped as data files: targets, observation
   images, investigation records for the default parameters **and** each STAB-1 perturbation, evidence
   graphs, Markdown reports, stability results, and local-assistant answers for every question intent.
2. Things that need the server are **disabled with an explanation**, never faked: arbitrary parameter
   re-runs (the preview offers the precomputed parameter sets), copilot questions naming specific
   observations, replay by re-execution. Saved records in the preview live in the viewer's browser only and
   say so; export/import of record files works.
3. Pair comparison and image registration in the preview are computed in the browser from the record
   (a JS port of `view.pair_comparison`, tested against the Python output for every pair).
4. Publish `dist/preview/` as an artifact; verify the identical files locally in Chromium with no backend.
5. Visual refresh (cyan/violet observatory palette, focus states, reduced motion), browser back/forward,
   and an audit of every control (e2e coverage for the controls not exercised before).

## Defects found in the audit (to fix)

| # | Defect |
|---|---|
| 1 | Evidence Graph lists only 5 method nodes; the Phase 3 methods (EPHEM, REFSEL-2, PAIRDIFF-2, CALCHECK-1, LINFIT-EPOCH-1) recorded in `parameters.methods` are missing — an incomplete provenance view |
| 2 | Evidence Graph: claim labels overlap the comparison column |
| 3 | Outcome evidence keys are shown raw (`pm measured mas yr`) |
| 4 | URL state uses `replaceState` only; browser back/forward does not move between workspaces |
| 5 | Controls not covered by any test: blink speed, fade, stretch/black/white sliders, zoom buttons, reset view, overlay toggles, report download, record delete, detector/status filters |
| 6 | Accent palette is amber; brief asks for restrained cyan/violet |

## Must not regress

Scientific modules and their versions (`science/`, `analysis.py` v2, ASSESS-2), provenance safeguards
(bundle verification, PROVCHECK-1, synthetic labelling, watermark), WLMATCH-2 gating of brightness
comparisons, GUARD-3 and TOOLS-2, offline mode with zero external requests, strict CSP, record
save/replay with content hashes, and every existing test (193 + 11 browser steps).
