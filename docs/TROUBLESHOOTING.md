# Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| "Cannot reach the Skytrace server." banner | the server is not running, or the page was opened from a different port | `python run.py` and open http://127.0.0.1:8600 |
| "The preview's data files could not be loaded." | the static preview was opened from the file system (`file://`), or `dist/preview/data` is missing | serve it: `python -m http.server -d dist/preview 8700`; rebuild with `python scripts/build_static.py` |
| A target shows "No stored observations" | no bundle for it yet (the five challenge targets need real data) | `python scripts/acquire_targets.py --all` on a machine with internet access; synthetic targets work offline |
| Acquisition fails with a proxy or DNS error | network policy blocks IRSA, SIMBAD or Gaia | `python scripts/diagnose_environment.py` names each blocked service; see `docs/ENVIRONMENT_REPORT.md` for what to allowlist |
| Copilot says "Local assistant · no language model" | no `META_API_KEY`/`MODEL_API_KEY` in the environment, `OFFLINE=1`, or the API is unreachable | set the key in `.env` (never in code or the browser) and run `python scripts/meta_smoke_test.py` |
| A copilot draft is "withheld by the evidence guard" | the model stated a number, identifier or certainty the tool outputs do not support | expected behaviour; the panel lists the reasons and shows the local assistant's grounded answer instead |
| Static preview: "This preview contains precomputed runs only" | the parameters you chose were not precomputed | use one of the listed parameter sets, or run the full application |
| Static preview: question about a named observation refused | the recorded answers cover question types, not individual observation pairs | use the Time Machine's comparison panel, or the full application |
| Import refused: "content hash does not match" | the file was edited or truncated after export | re-export it; a record can only be imported unchanged |
| Import refused: "data bundle … not available" | the record was made from a bundle this machine does not have | acquire or copy that bundle into `data/bundles/`, then import again |
| Replay reports "not reproduced" | the bundle or the software changed since the record was saved | the message says which; compare `software` in the two records |
| Saved investigations vanish in the static preview | browser storage was cleared, or the browser blocks storage (then records last only for the page) | export records you want to keep (Report Studio → Record) |
| A download does nothing in the hosted preview | the viewer asks for confirmation; a declined prompt saves nothing | accept the viewer's save prompt; locally, downloads are ordinary browser downloads |
| Hypothesis shows "evidence unavailable" | a saved hypothesis cites a test that the current analysis did not produce | re-run with the parameters the record was made with, or attach other tests |
| `pytest -m live` fails | no network route to the services (expected in restricted environments) | run it where IRSA, SIMBAD and Gaia are reachable |
| e2e tests skip | Playwright or Chromium missing | install Playwright with its Chromium; the tests use no other network |
| `make_release.py` refuses to run | uncommitted changes, or that version's zip already exists | commit; bump the version (earlier release artifacts are never overwritten), or pass `--force` deliberately |
