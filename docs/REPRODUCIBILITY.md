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
