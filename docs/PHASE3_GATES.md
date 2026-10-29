# Phase 3 gate report (v0.3.0, 2026-10-29)

A gate passes only when its acceptance checks were executed and recorded. Blocked gates are reported
as blocked and work continued past them. Nothing here rests on real SPHEREx data: none could be obtained
in this environment.

| Gate | Subject | Status | Evidence |
|---|---|---|---|
| A | Baseline and environment diagnosis | **PASS** | v0.2.0 baseline verified (14/14) before changes; `scripts/diagnose_environment.py` separates DNS, proxy CONNECT, TLS, HTTP and package failures → `ENVIRONMENT_REPORT.md` |
| B | Real SPHEREx acquisition (QR3, QR2 fallback, 5 targets) | **BLOCKED** | IRSA, SIMBAD, Gaia refused by the egress proxy (403 at CONNECT); re-attempted in Phase 3, stops at the first request without retrying policy denials or substituting data. No identifiers, epochs or coverage are claimed |
| C | Independent FITS/WCS validation | **PASS** for tested capabilities; real-file comparison **BLOCKED** | 22 tests on 14 independent astropy/wcslib files with explicit tolerances; 6 reader defects found and fixed → `FITS_WCS_VALIDATION.md` |
| D | Calibration and uncertainty audit | **PASS** (synthetic validation) | 14 effects classified; parallax, release mixing, wavelength-accuracy margin, calibration change, error model, correlated errors and reference quality fixed with versioned methods → `CALIBRATION_AUDIT.md` |
| E | Defensible assessment and complete provenance | **PASS** | ASSESS-2 (non-detection ≠ static; failure ≠ no motion; sensitivity on every outcome), structured codes everywhere, STAB-1 stability check, PROVCHECK-1 verifier → `ASSESSMENT_ENGINE.md` |
| F | Copilot tool contracts, guard, live Meta test | Contracts and guard **PASS**; live Meta **BLOCKED** | TOOLS-2 envelope and error codes (14 tests), GUARD-3 adds identifier and uncertainty checks; api.meta.ai refused and no key → `COPILOT_TOOLS.md`. No scripted response is presented as a model response |
| G | Robustness (synthetic, labelled) | **PASS** | 12 scenarios with known truth incl. perturbation stability → `TEST_REPORT.md` |
| H | Documentation and release | **PASS** | docs updated, `verify.py --e2e` 17/17, release archive `dist/skytrace-0.3.0.zip` with SHA-256 manifest |

## What would change the blocked gates

Gate B, the real-file part of Gate C and the live part of Gate F all need network access to
`irsa.ipac.caltech.edu`, `simbad.cds.unistra.fr`, `gea.esac.esa.int`, `api.meta.ai` (plus `pypi.org` and
`files.pythonhosted.org` for astropy) and a Meta key in the environment. The commands to run are in
`ENVIRONMENT_REPORT.md`. The next milestone is unchanged: the first real SPHEREx product acquired, read by
both readers, measured, assessed, and traced by `verify_provenance.py` from archive bytes to outcome.
