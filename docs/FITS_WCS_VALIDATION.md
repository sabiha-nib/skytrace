# FITS and WCS validation (Gate C)

**Result: passed for every capability tested; comparison on real SPHEREx files blocked** (no archive
access, astropy not installable here — see `docs/ENVIRONMENT_REPORT.md`).

Skytrace reads SPHEREx products with astropy when it is installed (`reader: auto` prefers it) and
otherwise with a small native reader (`src/skytrace/fitsio.py`, `src/skytrace/wcs.py`). Phase 3 required
the native reader to be validated independently, not against files it wrote itself. The validation uses
14 files copied unmodified from the astropy v7.0.1 repository (written by astropy, cfitsio, wcslib or other
missions' software) with expected values transcribed from astropy's own tests. Files, licence and SHA-256:
`tests/data/external/astropy-v7.0.1/README.md`. Tests: `tests/unit/test_fits_wcs_external.py` (22),
`tests/unit/test_fits_wcs.py` (10).

## What is checked, with tolerances

| Capability | Independent reference | Tolerance | Result |
|---|---|---|---|
| Binary table values (E, J, A, L columns) | `tb.fits`, astropy test values | rtol 1e-6 | pass |
| TDIM array shape | `tdim.fits` → (3, 1, 1) | exact | pass |
| Image axis order (NAXIS1 fastest) | `arange.fits`, element [3,2,5] = 357 | exact | pass |
| BSCALE / BZERO | `scale.fits` | exact after scaling | pass |
| Unsigned-integer convention (TZERO 32768 etc.), X bit columns | `memtest.fits`, `btable.fits` | exact | pass |
| Zero-width columns (`0D`) | `zerowidth.fits` | parses | pass |
| BLANK / TNULL → NaN | constructed per standard | exact | pass |
| Random groups, tile-compressed images | `group.fits`, `comp.fits` | must be **refused** with a clear error | pass |
| Truncated / damaged files | 5 damage modes of real files | must raise `FITSError` | pass |
| TAN linear pixel→world | `sip2.fits`, wcslib values | atol 1e-8 deg | pass |
| TAN-SIP footprint (with and without SIP) | `sip.fits`, wcslib corners | rtol 1e-7 | pass |
| SIP inverse round trip | `sip.fits` header | < 1e-3 px | pass |
| SIP focal-plane coordinates | `irac_sip.hdr` (Spitzer) | rtol 1e-3 | pass (weak check; origin convention verified) |
| -TAB lookup (Greisen et al. 2006) | astropy `SimModelTAB` analytic model ported | atol 1e-7 | pass, 2 parameter sets + write/read |
| -TAB with mixed celestial + tabular axes | `tab-time-last-axis.fits` | CRPIX→CRVAL exact; time(z)=z | pass |
| -TAB out-of-range | half-cell rule 0.5 ≤ Υ ≤ K+0.5 | NaN beyond | pass |
| -TAB unsupported conventions | EXTVER ≠ 1, non-monotonic index, missing table, CPDIS distortion | must be refused | pass |
| Invalid -TAB entries | NaN in coordinate array | NaN propagates | pass |
| Units | `CUNITiW = um`, `BUNIT = MJy/sr` read and carried to photometry | exact | pass (synthetic + unit tests) |

## Defects the independent files found (all fixed)

Testing only against self-written files had hidden these:

1. Logical (`L`) columns were all read as True — now decoded from `b"T"`.
2. Zero-width columns raised a raw `ValueError` — repeat 0 is now supported.
3. Random-groups files were silently mis-read — now refused.
4. `TZERO = 32768` overflowed — the unsigned convention is now mapped to uint16/32/64.
5. Bit (`X`) columns were unsupported — now unpacked.
6. BLANK / TNULL values were returned as numbers — now NaN.

## What remains unverified

* The native reader has not read a real SPHEREx Level-2 file. Their headers (SIP order, `-TAB` table
  layout, FLAGS bit definitions, `l2b-v24` vs `l2b-v27` differences) are known only from IRSA documentation.
  The first real file must be read with both readers and compared (`tests/unit/test_fits_wcs.py::test_cross_check_with_astropy`
  runs automatically when astropy is installed; it is skipped here).
* Distortion lookup tables (CPDIS/D2IM) are refused rather than implemented; if real SPHEREx files carry
  them, astropy is required.
