# Limitations

## Not yet verified

- **No real SPHEREx data has been processed.** The build environment could not reach IRSA, SIMBAD or the Gaia archive (proxy `403 Forbidden`), and access to a networked computer was not granted. Every scientific statement in this repository rests on synthetic tests.
- **The native FITS/WCS reader has not been compared with astropy on a real file.** It follows the FITS standard, and its `-TAB` implementation follows Greisen et al. 2006. But the synthetic files were written by this project's own writer, so reader and writer agree by construction. `tests/live` performs the decisive comparison. Install astropy to use astropy for reading in the meantime.
- **The real FLAGS bit layout and time keywords are unknown.** Only `MP_TRANSIENT` (bit 0) and `MP_SOURCE` (bit 21) are documented in what was available. Other flags are applied only when the file's header defines them; otherwise they are reported as unresolved.
- **No Meta Model API call has been made.** The request format follows the documentation, but tool-call and structured-output behaviour of `muse-spark-1.3` are untested. Pricing, rate limits and availability in your country are unknown.
- **The Dockerfile has not been built.**

## Scientific

- Wavelengths come from the `WCS-WAVE` lookup, which IRSA describes as ~1 nm accurate and intended for visualisation. Sub-nm matching decisions would need the Spectral WCS product (CWAVE/CBAND).
- Aperture fluxes are not aperture-corrected. Fluxes from different detectors are not on a common scale, so the spectrum's shape across detectors is approximate.
- Gaussian centroids approximate the SPHEREx PSF. The file's PSF extension (121 zone PSFs) is not used yet.
- Parallax displacement is not modelled (up to 547 mas for Barnard's Star, 271 mas for ε Indi B, 439 mas for WISE 0855, from secondary sources). This needs the spacecraft's position per exposure.
- Chromatic PSF and distortion differences between wavelengths are not modelled; positions from different detectors are combined.
- The error model excludes PSF variation across the detector and calibration drift, so systematics can produce |z| > 5 for a constant source. That is why the outcome is called a *candidate*.
- Reference-star selection has no Gaia quality cut (e.g. RUWE). On the synthetic data, a reference star with a 0.5 px catalogue error was still used in 8 of 24 plates (all long-wavelength).
- Unresolved companions (RW Aur B at 1.4″, ε Indi Ba/Bb at 0.6″) contribute to every flux and centroid at 6.2″ pixels.
- Bright targets (Barnard's Star, likely R Draconis) may be flagged as overflow or non-linear in most exposures; flagged photometry is not measured.
- WISE 0855 is expected to be undetectable below ~3 µm and possibly in single exposures at all. Stacking within a visit is not implemented.

## Product

- Single-user: no accounts, and saved investigations are visible to anyone who can reach the server.
- Investigations are cached in server memory. A restart forgets unsaved runs, but saved records reopen and replay.
- The evidence guard is heuristic. It checks numbers, dates, wavelengths, sources, tool use, causal and certainty wording, and synthetic labelling against tool outputs. It does not understand meaning, so a sentence that combines correct numbers misleadingly can still pass.
- The local assistant answers with fixed templates. It routes questions by keywords and cannot answer arbitrary questions.
