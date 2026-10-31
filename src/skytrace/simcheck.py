"""Simulation audit (SIMCHECK-1): what a Synthetic Observatory scenario assumes, and whether its verdicts hold up.

The audit records the generator, version, seed, parameters, ground truth, noise and physical assumptions,
simplifications, validity domain and expected limitations (restated from `synthetic.py` and `synthobs.py`), and runs:
  * a repeated-seed test: the same scenario with different seeds (independent noise) — do the verdicts stay the same?
  * a failure-case inspection: which exposures the pipeline refused and why.
A synthetic benchmark tests the software against its own generator. It is not an observational validation dataset.
"""

from __future__ import annotations

from . import synthetic, synthobs

METHOD = "SIMCHECK-1"
MAX_SEEDS = 3
NOISE = ["Gaussian pixel noise with variance noise² + 0.004 × (signal above sky)", "hot pixels flagged in FLAGS", "noise is independent between pixels and exposures"]
PHYSICS = ["stars are point sources rendered with a Gaussian PSF whose width grows with detector number (illustrative, not SPHEREx calibration)",
           "linear proper motion, no parallax unless set", "brightness factor per pass multiplies the target only; gain multiplies every star",
           "wavelength at the target set by its detector position through a linear variable filter model"]
SIMPLIFICATIONS = ["constant sky within a scenario", "no zodiacal-light structure, cosmic rays or persistence", "no aperture losses beyond the Gaussian PSF",
                   "a synthetic reference catalogue whose stars are exactly where the catalogue says (except the configured offset)"]


def audit(scenario: dict, seeds: list | None = None) -> dict:
    errs = synthobs.validate(scenario)
    if errs:
        return {"method": METHOD, "status": "refused", "errors": errs}
    base = synthobs.normalise(scenario)
    seeds = [s for s in (seeds or [base["seed"], base["seed"] + 1000, base["seed"] + 2000]) if isinstance(s, int)][:MAX_SEEDS]
    runs = []
    for s in seeds:
        r = synthobs.run({**base, "seed": s})
        if r.get("status") == "refused":
            return {"method": METHOD, "status": "refused", "errors": r.get("errors")}
        runs.append({"seed": s, "scenario_id": r["scenario_id"], "verdicts": {x["question"]: x["verdict"] for x in r["evaluation"]["rows"]},
                     "categories": r["evaluation"]["categories"], "refused_exposures": r["evaluation"]["failure_behaviour"]["rejected_exposures_by_reason"],
                     "record_content_hash": r["record_content_hash"]})
    qs = sorted({q for r in runs for q in r["verdicts"]})
    stable = {q: len({r["verdicts"].get(q) for r in runs}) == 1 for q in qs}
    return {"method": METHOD, "status": "completed", "generator": synthobs.GENERATOR, "generator_version": synthetic.GEN, "scenario": base,
            "ground_truth": synthobs.truth(base), "noise_assumptions": NOISE, "physical_assumptions": PHYSICS, "simplifications": SIMPLIFICATIONS,
            "validity_domain": {k: (v.get("min"), v.get("max")) for k, v in ((k, s[0]) for k, s in synthobs.SPEC["f"].items()) if isinstance(v, dict) and "min" in v},
            "expected_limitations": ["agreement shows the pipeline recovers what this generator injects, under these assumptions",
                                     "it says nothing about PSF mismatch, real calibration drift or real flag behaviour"],
            "repeated_seed_test": {"seeds": seeds, "runs": runs, "stable": stable, "rule": "a verdict is stable when every seed gives the same verdict"},
            "failure_cases": [{"seed": r["seed"], "refused": r["refused_exposures"]} for r in runs if r["refused_exposures"]],
            "benchmark_kind": "synthetic benchmark (not an observational validation dataset)"}
