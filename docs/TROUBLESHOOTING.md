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

| Sessions dialog lists "Unreadable session files (kept, not deleted)" | a file in `data/sessions/` is not valid JSON or fails validation | open it to inspect; Skytrace never deletes it; fix or remove it yourself |
| "Import refused: content hash …" for a session | the session file was edited after export | re-export it; edit sessions only through the interface |
| A plan step shows *blocked* | a precondition is unmet (no pair selected, server-only action in the preview, no network) | the step's note names the missing input; supply it and plan again |
| A plan step stays *needs review* | inspection steps wait for your written judgement | open the step, write what you saw, *Mark reviewed* |
| Experiment Studio: "Custom parameter sets need the local server" | the static preview recorded only the standard experiments | run the full application |
| Negative control "not available" | no other fixture has that effect absent by construction | expected with the two fixtures; it is not a failure of the method |
| Connector preview refused in the static preview | previews are built by the server's acquisition code | run the full application (no network is used by a preview) |
| Copilot answer says it was recorded for a different question | static preview: one recorded answer per question type | ask in the full application for an answer to your exact wording |
| Two tabs show different session contents | sessions are single-writer; the last save wins | use one tab per session, or branch the session |
| Counterfactual refused: "baseline … does not match" | the stated baseline run's content hash no longer recomputes (bundle or software changed) | re-run the baseline, then build the scenario again |
| Counterfactual refused with a bound | a threshold, error factor or exclusion is outside the stated bounds | the message names the bound; the Counterfactual Lab lists them |
| Static preview: "this scenario is not precomputed in the preview" | only the nine prepared scenarios on the default run are recorded | use a prepared scenario, or run the full application |
| Synthetic scenario refused | a field is outside its bound (2–6 passes, positions A/B/C, …) | the message names the field; start from a template |
| Synthetic verdict "not determinable" | the pipeline refused the exposures (for example blended) or had too few | expected for the failure-case template; *Failure behaviour* lists the refusals |
| `data/synthlab/` grows | each new scenario writes a bundle | only the 24 most recent are kept (older ones are pruned); deleting the folder is safe (scenarios regenerate) |
| Autopilot will not run | the authorization box is not ticked, or the level does not allow the plan's permission classes | tick the authorization; steps the level does not allow are named and skipped |
| Reproducibility verdict "replayable, not replayed here" | only the audit ran | press *Re-execute and audit* (full application) to replay |
| Atlas shows "distance unknown" | no parallax is recorded for the target | expected; no distance is inferred from sky position |
| Knowledge search finds nothing for a related word | search is exact, multi-word substring matching | search for the words the item actually uses |
| Compiler outcome "requires scientific review" | a check asks for review (an unresolved contradiction, a positive claim with open alternatives); this is the expected outcome on both fixtures | open the Review perspective or the cited checks; it is not a failure and passing would not be proof |
| Debugger: "This stage records its decisions but no separate result" | the stage logs events but no single value to recompute | trace its events in the reasoning graph or the Discovery Lab's step log |
| Differential debugging "needs two runs" (full application) | only runs attached to the session can be compared | run a stability perturbation or another parameter set while the session is open |
| Reproduction "failed reproduction" with no software change | the record's parameters or inputs no longer give the recorded outputs, or the record was edited (its hash does not recompute) | the earliest divergence names the stage; re-run the analysis to get a fresh record |
| Lineage-X: "the preview records the lineage of the claims and the motion fit" | the static preview records lineage for the claims and the motion fit only | use the full application for other results |
| Workspaces show "Hidden by the blind analysis" | a blind analysis is active | finish the work you planned, then unblind in Protocol & Blind Analysis (needs a locked protocol and typing UNBLIND) |
| Copilot says it is paused | a blind analysis is active; its answers would reveal outcomes | unblind first |
| Session save refused: "evidence-vault chain broken at entry N" | an earlier history entry was edited outside Skytrace | restore an unedited export; corrections must be appended, not edited in |
| Integrity firewall "needs attention" on my notebook | a high-severity check failed (for example a number not in the record, or "discovered") | each failing check lists the items; the firewall never changes your text |
| Scientific Intelligence shows "Run the analysis first" | the panels read a finished investigation | run the analysis (or open a saved record) |
| Integrity Gate "not ready" on a fixture | *Reproducible*, *Wording within the evidence* and *Challenges examined* need your action | run the *reproduce independently* step in the Research Cycle, check the report wording, and acknowledge or resolve the open challenges; *ready* still does not mean true |
| A challenge cannot be resolved | resolution needs a reference to a recorded item | add a reference (a graph id, session item or record path), or acknowledge it instead |
| Research Cycle runs nothing | the level is *Advisory*, or (restricted) the authorization box is not ticked | choose *Supervised* and approve a step, or tick the authorization; steps the level does not allow are skipped with a reason |
| Observation Oracle shows a reason instead of a plan table | no measurement model reproduces the recorded fit for that question, so no plan can be evaluated | expected; the reason is shown and nothing is estimated instead |
| What-if "no valid method" | the question has no method that can recompute it from the record | expected (for example W3, the background model); the reason is shown |
| Multi-Discovery Network or genome comparison is empty (full application) | the server holds only one investigation | run a stability perturbation or another parameter set, or save records |
| Memory warning about an earlier failure | the same action failed before on this target; the reason is quoted | read the reason before repeating; the warning never blocks |
| Protocol says "locked after results were visible" | the lock was made after the analysis ran | expected: a late lock is labelled so; lock before running to record a pre-analysis plan |
