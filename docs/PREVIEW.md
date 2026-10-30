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
stability perturbations (record, summary, evidence graph, report, discovery report, research report (compatibility, data
quality, ledger, radar), the reproducibility package — the server-built zip carried as base64 with its SHA-256, checked in the browser before it is offered — and the
local assistant's answer to each question type with the question it was recorded for), the stability result, the standard
experiments per target, the specifications (planner table, missions, templates, schemas, citations), the connector registry and
the capability registry as the preview sees it, and for Phase 7: the frontier report for every run (`frontier.json`), the default run's reproducibility audit with replay (`reproduce.json`), nine prepared counterfactual scenarios (`counterfactuals.json`), the six Synthetic Observatory templates (`synthetic.json`) and one schedule comparison (`design.json`). `PREVIEW_MANIFEST.json` lists every file with its SHA-256 and the commit it was built from.

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
| Research sessions | `data/sessions/` on the server, validated and hash-checked | this browser's storage, same validation and hash in JS; export to keep |
| Planner | `POST /api/plan` | the browser planner over the same rule table; server-only steps marked unavailable |
| Data quality, compatibility, ledger, radar | computed by the server | recorded by the server at build time (`research.json`) |
| Experiments | any template, custom parameters within bounds | the standard set recorded at build time; custom parameters refused with a reason |
| Workflows | validated by the server, executed step by step | validated and executed in the browser over precomputed runs |
| Notebook, figures, knowledge graph, missions | browser | browser (same code) |
| Connectors | registry and request previews (nothing sent) | registry only; previews refused |
| Copilot 2.0 | 16 tools, labelled sources, drafts, plan hand-off | recorded answers per question type; the answer says which question was recorded when yours differs |
| Discovery Horizon, Adversarial Lab, Review Room | computed by the server; session rules applied in the browser | recorded per run at build time (`frontier.json`); session rules in the browser (same code) |
| Counterfactual Lab | any valid scenario within the bounds | the nine prepared scenarios on the default run; edited scenarios refused with a reason |
| Synthetic Observatory, Observation Design Lab | generates and analyses any valid scenario (written to `data/synthlab/`) | the six templates and one recorded schedule comparison; edited scenarios refused |
| Reproducibility challenge | audit and re-execution | audit for every run; the recorded re-execution of the default run |
| Autopilot, Cosmic Atlas, Knowledge Atlas, twins, story | browser over server data | browser (same code) over recorded data |

Every screen of the static preview says it is a preview of precomputed results.

## Rebuilding

```bash
python scripts/build_static.py            # full rebuild (about two minutes: runs every analysis)
python scripts/build_static.py --web-only # re-copy the interface only, keep the recorded data
python -m pytest -m e2e tests/e2e         # exercises every control in both modes
```
