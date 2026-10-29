# Previewing Skytrace

Three ways to open the application. All three show the same interface; they differ in what runs behind it.

| Way | How | What runs | Use it for |
|---|---|---|---|
| Hosted preview | https://claude.ai/artifact/RoUxXMSEELpbxBHj8wgzpT (private to its owner until shared) | the static build, hosted; nothing runs on a server while you browse | looking at the product |
| Static preview, locally | `python scripts/build_static.py && python -m http.server -d dist/preview 8700` → http://127.0.0.1:8700/ | the same static build, from your disk | checking the preview build |
| Full application | `OFFLINE=1 python run.py` → http://127.0.0.1:8600 | the Starlette server and the Python pipeline | real work: any parameters, replay, the copilot loop |

## What the static preview contains

`scripts/build_static.py` starts the real server with `OFFLINE=1`, calls its API and records the responses into
`dist/preview/data/`: targets, observation images, for each synthetic target the default analysis and the five
stability perturbations (record, summary, evidence graph, report, discovery report, the reproducibility package — the server-built zip carried as base64 with its SHA-256, checked in the browser before it is offered — and the
local assistant's answer to each question type), the stability result, and the capability registry as the preview
sees it. `PREVIEW_MANIFEST.json` lists every file with its SHA-256 and the commit it was built from.

`index.html` is for local use; `artifact.html` is the same page as body content for hosts that wrap pages in their
own document. The `<meta name="skytrace-mode" content="static">` tag switches `web/js/api.js` to the static backend
(`web/js/static/backend.js`).

## What works where

| Feature | Full application | Static preview |
|---|---|---|
| Analysis with default parameters | runs the pipeline | loads the precomputed run |
| Other parameters | runs the pipeline | the five stability perturbations only; anything else is refused with an explanation |
| Stability check | runs STAB-1 | precomputed result for the default parameters |
| Discovery Engine, Hypothesis Arena, Uncertainty | computed by the server from the record | precomputed by the server at build time |
| Pair comparison, registration, registration diagnostics | server | computed in the browser by parity-tested ports |
| Copilot | Meta model if configured (blocked here), else the local assistant | the local assistant's recorded answers, routed exactly as the server routes questions; questions naming specific observations need the server |
| Saved investigations | `data/records/` on the server; replay re-executes | this browser's storage; "Check" compares the content hash with the precomputed runs (no re-execution) |
| Import | content hash verified, bundle must exist, replay possible | content hash verified in the browser; only records of the preview's own runs can be opened |
| Report Studio downloads | server endpoints | precomputed files; in the hosted viewer, saving goes through the viewer's download prompt |

Every screen of the static preview says it is a preview of precomputed results.

## Rebuilding

```bash
python scripts/build_static.py            # full rebuild (about two minutes: runs every analysis)
python scripts/build_static.py --web-only # re-copy the interface only, keep the recorded data
python -m pytest -m e2e tests/e2e         # exercises every control in both modes
```
