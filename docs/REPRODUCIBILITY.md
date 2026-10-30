# Reproducibility

## What makes a result reproducible

An investigation record (`report.Investigation.to_dict()`) contains:

- every parameter, including defaults: aperture radius, fit box, wavelength tolerance, epoch clip, detectors, reader
- the analysis version (`skytrace-analysis/1`) and the method ID used in every step
- the SHA-256 of the bundle manifest, which pins the SHA-256 of every input file
- every logged step with its data and the provenance of its inputs
- software versions (skytrace, Python, NumPy, SciPy, astropy)
- a **content hash** over target, parameters and events. Creation time and software versions are excluded, so the same inputs give the same hash.

`tests/unit/test_report_ai.py::test_full_analysis_is_reproducible` and `test_offline_workflow.py` check that two runs on the same bundle give the same content hash.

## Replay

In the app's **Investigations** workspace, *Replay* re-runs a saved investigation with its saved parameters on the bundle currently on disk, then compares:

| Comparison | Meaning |
|---|---|
| same manifest hash, same content hash | reproduced exactly |
| different manifest hash | the data changed since the record was saved |
| same manifest hash, different content hash | the software or environment changed (compare the recorded versions) |

API: `POST /api/records/{id}/replay`. The browser acceptance test saves an investigation, replays it and checks for "reproduced: identical content hash".

## From scratch on another machine

```bash
python -m pip install -e ".[astro,dev]"
python scripts/make_synthetic_fixtures.py     # optional: regenerates fixtures (FITS bytes are deterministic for the fixed seeds)
python scripts/acquire_targets.py --all       # real data (network); resumable, checksummed
python scripts/verify_data_bundle.py
python scripts/analyze_target.py <target_id>  # writes data/runs/<target_id>/investigation.json and report.md
python scripts/verify.py
```

## Caveats

- The FITS reader matters: astropy and the native reader should give identical pixels and agree on WCS to < 10 mas (checked by `tests/live`). The reader used is recorded in every inspection step.
- SciPy's least-squares results can differ in the last bits across versions and platforms. A content-hash mismatch with an identical manifest hash and different software versions is expected; compare the outcomes and numbers, not only the hash.
- Archive releases change. QR3 may be reprocessed, and IRSA corrected QR2 headers in April 2026. A re-acquired bundle is a new bundle with a new manifest hash; the old record still names the files it used.

## Verifying a record (v0.3)

```bash
python scripts/verify_provenance.py <target_id> --rerun     # or --all
```

PROVCHECK-1 checks that the record was made from the current manifest, that its content hash recomputes,
that every provenance hash matches a manifest file, that data origins match the bundle kind, that every
measured observation is in the discovery index, that all status codes are known, that method versions are
recorded, that outcomes agree with the step data, and (with `--rerun`) that re-running the analysis
reproduces the content hash. Results go to `data/runs/<target>/provenance_check.json`. The synthetic
fixtures themselves regenerate byte-identically: `python scripts/make_synthetic_fixtures.py --check`.

## Reproducibility package (v0.5)

*Investigations → Report Studio → Reproducibility package* (or `GET /api/investigations/{id}/package.zip`) gives one
deterministic zip: the record, report, discovery report, evidence graph, capability registry, bundle manifest, a README
and SHA256SUMS. To check it: `unzip skytrace-*-package.zip && cd skytrace-* && sha256sum -c SHA256SUMS`. The record's
content hash recomputes from `record.json` (the README shows how). To replay, place the bundle named in
`bundle_manifest.json` under `data/bundles/` (or use the bundled synthetic fixture) and import `record.json` into the
full application, then *Replay*.

## Research sessions and experiments (v0.6)

* **Session export** (Sessions dialog → *Export session (JSON)*) is the full session in canonical form; its `content_hash`
  recomputes as SHA-256 of the canonical text without that field (Python `skytrace.session.body_hash`, JS `sessioncore.bodyHash`;
  both are tested to agree). *Import session* refuses any file whose stated hash differs.
* **Session package** (Notebook → *Export session package (ZIP)*) is a deterministic stored ZIP: `session.json`, `notebook.md`
  (references resolved against the active run at export time) and a README explaining how to recompute the hash. Same session,
  same bytes (`tests/unit/test_notebook_package.py`).
* **Reproducibility experiment** (Experiment Studio) runs the baseline twice, independently, and compares content hashes;
  `python scripts/gen_research_methods.py` re-runs the standard experiments on both fixtures and writes their outcomes into
  `docs/RESEARCH_METHODS.md`.
* **Plans and workflows** are data: a stored plan keeps each step's action and inputs, and a workflow is a declarative JSON file
  (`skytrace.workflow/1`) that validates identically in Python and the browser, so either can be re-run later.

## Reproducibility challenge and synthetic scenarios (v0.7)

* **REPRO-1** (Review Room → Reproducibility) runs eleven checks: inputs identifiable, files available, checksums, method
  versions, parameters, dependencies, environment, record integrity, replay, figures and limitations. It gives one of four
  verdicts. *Reproduced* needs a re-execution here that gives the identical content hash. *Replayable, not replayed here* means
  nothing failed but no replay ran. *Not reproducible as recorded* means a replay or integrity check failed. *Incomplete* means
  inputs or metadata are missing. Importing a record only proves that it parses, and is never counted. A tampered record fails
  R8 (`tests/unit/test_frontier.py::test_reproducibility_verdicts_and_tamper`).
* **Synthetic scenarios** are reproducible to the byte. The same scenario and seed give identical files and the same record hash
  (`test_synthetic_scenarios_are_labelled_deterministic_and_known_answer`). An exported validation report carries the scenario,
  seed, generator version and record hash, so anyone can regenerate it with `POST /api/synthetic`.
* **Counterfactuals** are reproducible from their export: the baseline content hash, the scenario (kind and change) and the
  scenario hash. Re-assessment with no change reproduces the recorded outcomes exactly, so a difference is attributable to the
  stated change alone.
* `python scripts/gen_frontier_methods.py` re-runs the prepared counterfactuals, the synthetic templates, a schedule
  comparison and every frontier method on both fixtures, and writes the results into `docs/FRONTIER_METHODS.md`.
