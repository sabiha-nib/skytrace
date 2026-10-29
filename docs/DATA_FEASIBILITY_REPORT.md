# SKYTRACE — Data Feasibility Report (Gate B)

> **Update (v0.2.0):** acquisition is now `scripts/acquire_targets.py`, which writes verified bundles (see [DATA_PROVENANCE.md](DATA_PROVENANCE.md)). A run on 2026-10-29 was again stopped by the proxy at the first SIMBAD request. `scripts/feasibility.py --wavelengths` still produces the matrix below once network access exists. The predictions in section 3 are unchanged and still untested.

Status 2026-10-29: **BLOCKED — no live archive result exists yet.** Nothing below is an observation. Section 1 is what was executed; section 2 is verified documentation; section 3 is a prediction to be tested, clearly labelled.

## 1. What was executed

`python scripts/feasibility.py` ran in the cloud workspace on 2026-10-29. Every target stopped at the first network call (SIMBAD TAP): the workspace proxy answered `403 Forbidden` for each of 3 attempts, and there was no cache or fixture to fall back on. The script recorded this verbatim in:

- `data/feasibility/feasibility_matrix.csv` — 5 rows, `retrieval_status = BLOCKED: target resolution failed …`
- `data/feasibility/feasibility_matrix.json` — the same rows plus each target's event log

IRSA, the Gaia archive and SIMBAD were also unreachable through the read-only web tool (robots or server errors), so no archive metadata at all has been retrieved. **No observation dates, detector coverage or flag states are known for any target.**

To complete Gate B on a networked machine:

```bash
pip install -e ".[astro,dev]"
pytest -m live                                   # interface checks, prints a real product's structure
python scripts/feasibility.py --wavelengths      # full matrix with λ-at-target and flags
```

Matrix columns (as required): `target, release, observation_id, observation_time, detector, product_type, wavelength_coverage, quality_status, retrieval_status, scientific_use, limitations, source_url`. With `--wavelengths`, `wavelength_coverage` adds the central wavelength and bandwidth **at the target's pixel**, and the per-target summary counts wavelength-matched pairs (rule WLMATCH-1).

## 2. Verified archive facts used by the code

| Fact | Source |
|---|---|
| QR3 current (DOI 10.26131/IRSA662), QR2 (10.26131/IRSA652) superseded, QR1 retired | IRSA QR overview |
| SIA2 `https://irsa.ipac.caltech.edu/SIA`, collections `spherex_qr3`, `spherex_qr3_deep`, `spherex_qr2`, `spherex_qr2_deep`; ~1-day ingestion lag | SPHEREx Archive data-access page |
| TAP tables `spherex.artifact` / `spherex.plane`, columns `uri`, `planeid`, `poly`, `energy_bandpassname`, `time_bounds_lower` | IRSA cutouts tutorial |
| Cutout: `?center=<ra>,<dec>d&size=<deg>` on an on-prem image URL | IRSA cutouts tutorial |
| One MEF per detector per pointing; `IMAGE` MJy/sr (zodi not subtracted), `FLAGS`, `VARIANCE`, `ZODI`, `PSF`, `WCS-WAVE`; 2040×2040 | SPHEREx data-products page |
| Pixel 6.2″; six detectors D1–D6 covering 0.75–5.0 µm | spherex.caltech.edu instrument page; data-products page |
| Wavelength per pixel via spectral WCS key `"W"` (WCS-WAVE table), ~1 nm, "for visualisation"; science-grade CWAVE/CBAND in a separate product | data-products page; intro tutorial |
| Flag bits documented: `MP_TRANSIENT`=0, `MP_SOURCE`=21; full table in Explanatory Supplement Table 10 | intro tutorial |
| 4 all-sky surveys of ~6 months each; 112.5 s frames; saturation flag for sources brighter than ~11 AB at 2 µm, < 2 usable samples brighter than ~6 AB; L2 registered to Gaia | Crill et al. 2024 (arXiv:2404.11017) |

Unverified and handled defensively in code: whether TAP `spherex.*` tables index QR3, QR2 or both (release is taken from the SIA collection or the file path, else `UNKNOWN`); header keywords for observation time (SIA `t_min`/`t_max` are used); whether cutouts preserve the `W` spectral WCS correctly (to be checked by `inspect_product` and by comparing a cutout with its full image).

## 3. Predictions to test (not results)

Reference values are from secondary sources (Wikipedia infoboxes citing Gaia DR3 / literature, fetched 2026-10-29) and will be replaced by live SIMBAD + Gaia DR3 values. Vega→AB offsets are standard approximations (J +0.91, K +1.85, W2 +3.34).

| Target | Expected signal | Shift per year at 6.2″/px | Brightness vs SPHEREx limits | Prediction |
|---|---|---|---|---|
| Barnard's Star | proper motion 10.39″/yr | 1.68 px/yr | J≈6.2 AB, K≈6.4 AB: far brighter than the ~11 AB saturation-flag level, near the ~6 AB "<2 samples" level | Photometry likely flagged in most bands. Astrometry possible only if unsaturated wings centroid reliably — must be proven against Gaia, not assumed. **Risky as the validation target.** |
| Epsilon Indi B | proper motion 4.68″/yr (Ba+Bb unresolved; separation 0.6″) | 0.76 px/yr | magnitudes not yet verified; T dwarfs at ~3.6 pc expected well above detection and below saturation | **Best candidate for astrometric validation**: sub-pixel shift but high S/N; ~400″ from ε Ind A, so A's wings should be checked |
| WISE 0855−0714 | proper motion 8.15″/yr | 1.31 px/yr | J≈25 (undetectable below ~3 µm); W2=13.89 Vega ≈ 17.2 AB at 4.6 µm vs ~18.4 AB full-survey per-channel depth quoted at 2 µm | Detectable, if at all, only in D5–D6 and possibly only after combining exposures within an epoch. Likely a documented non-detection in single exposures. |
| RW Aurigae | irregular variability; a major dimming event reported from Feb 2025 | 0.004 px/yr (static) | G=12.2; IR brightness not yet verified | **Good variability candidate** if ≥2 wavelength-matched pairs exist; companion at 1.45″ is unresolved and contributes to every flux |
| R Draconis | Mira-type variability | not verified | likely very bright in IR → saturation | Photometry may be fully flagged; would then be reported as unsuitable, not forced |

Feasibility rule: a target is "feasible" for variability only with ≥1 wavelength-matched pair of unflagged measurements, and for astrometry only with ≥2 epochs whose per-exposure plate solutions use ≥4 Gaia reference stars. A SIA hit alone does not qualify.
