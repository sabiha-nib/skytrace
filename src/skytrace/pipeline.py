"""End-to-end investigation of one target: resolve -> discover -> retrieve -> measure -> compare -> report.

Every step is logged in an Investigation, including rejections and failures.
Nothing here is allowed to fill a gap with an assumed value: a missing input
ends that branch with a logged reason.
"""

from __future__ import annotations

import math
from dataclasses import asdict

from .archive import references as refs_mod
from .archive import spherex
from .archive.net import Fetcher, FetchError, OfflineError
from .archive.products import ProductError, inspect_product, load_product
from .report import Investigation
from .science.astrometry import AstrometryError, compare_to_catalogue, fit_linear_motion
from .science.coords import Astrometry, angular_separation_deg, mjd_to_jyear, parse_dec, parse_ra, propagate
from .science.measure import measure_exposure, predicted_xi_eta_mas
from .science.variability import compare_fluxes
from .science.wavelength import SourceSample, match_pairs

DEFAULTS = {
    "releases": ["QR3", "QR2"],
    "cutout_size_deg": 0.1,
    "aperture_radius_px": 2.0,
    "wavelength_tolerance_channels": 0.5,
    "reference_g_range": [10.0, 16.0],
    "max_observations": 200,
    "discovery_epoch_jyear": 2026.0,
}

ACQ_ERRORS = (FetchError, OfflineError, LookupError, ValueError)


def resolve_target(fetcher: Fetcher, cfg: dict, inv: Investigation) -> Astrometry | None:
    try:
        row, prov = refs_mod.resolve_simbad(fetcher, cfg["simbad_id"])
    except ACQ_ERRORS as e:
        inv.log("resolve:simbad", "failed", str(e))
        return None
    inv.log("resolve:simbad", "ok", f"{row['main_id']} (coords bibcode {row.get('coo_bibcode')})", row, [prov])
    simbad = Astrometry(ra=float(row["ra"]), dec=float(row["dec"]), ref_epoch=2000.0,
                        pmra=float(row.get("pmra") or 0), pmdec=float(row.get("pmdec") or 0),
                        parallax=float(row.get("plx_value") or 0), source="SIMBAD")

    if cfg.get("supplied_coords"):
        sc = cfg["supplied_coords"]
        sep = float(angular_separation_deg(parse_ra(sc["ra"]), parse_dec(sc["dec"]), simbad.ra, simbad.dec)) * 3600
        inv.log("resolve:supplied-coords", "info",
                f"supplied coordinates ({sc['source']}) are {sep:.2f} arcsec from SIMBAD J2000", {"sep_arcsec": sep})

    ra16, dec16 = propagate(simbad, 2016.0)
    try:
        rows, gprov = refs_mod.gaia_cone(fetcher, ra16, dec16, 5 / 3600, g_min=-5, g_max=25, limit=20)
    except ACQ_ERRORS as e:
        inv.log("resolve:gaia", "failed", f"{e}; using SIMBAD astrometry")
        return simbad
    best = None
    for r in rows:
        if r.get("pmra") is None:
            continue
        dpm = math.hypot(r["pmra"] - simbad.pmra, r["pmdec"] - simbad.pmdec)
        if dpm <= max(50.0, 0.05 * math.hypot(simbad.pmra, simbad.pmdec)) and (best is None or dpm < best[0]):
            best = (dpm, r)
    if best is None:
        inv.log("resolve:gaia", "rejected", f"no Gaia DR3 source within 5\" with proper motion matching SIMBAD; "
                f"{len(rows)} candidates examined; using SIMBAD astrometry", {"n_candidates": len(rows)}, [gprov])
        return simbad
    g = refs_mod.to_astrometry(best[1])
    inv.log("resolve:gaia", "ok", f"Gaia DR3 {best[1]['source_id']} (|Δpm| vs SIMBAD {best[0]:.1f} mas/yr)", best[1], [gprov])
    return g


def run(fetcher: Fetcher, cfg: dict, params: dict | None = None) -> Investigation:
    p = {**DEFAULTS, **(params or {})}
    inv = Investigation(cfg["name"], p)
    ast = resolve_target(fetcher, cfg, inv)
    if ast is None:
        return inv

    # ---- discovery (metadata only)
    ra_d, dec_d = propagate(ast, p["discovery_epoch_jyear"])
    pm_tot = math.hypot(ast.pmra, ast.pmdec) / 1000.0  # arcsec/yr
    radius = (pm_tot * 1.5 + 2.0) / 3600.0
    found: dict[tuple, spherex.Observation] = {}
    for rel in p["releases"]:
        try:
            obs, prov = spherex.discover_sia(fetcher, ra_d, dec_d, rel, radius)
        except ACQ_ERRORS as e:
            inv.log(f"discover:{rel}", "failed", str(e))
            continue
        new = 0
        for o in obs:
            key = (o.obs_id, o.detector)
            if key not in found:   # releases are listed in preference order
                found[key] = o
                new += 1
        inv.log(f"discover:{rel}", "ok", f"{len(obs)} images, {new} not already covered by a preferred release",
                {"n": len(obs), "detectors": sorted({o.detector for o in obs if o.detector})}, [prov])
    observations = sorted(found.values(), key=lambda o: (o.t_mid_mjd or 0, o.detector or 0))
    if not observations:
        inv.log("discover", "failed", "no SPHEREx images cover this target in the requested releases")
        return inv
    if len(observations) > p["max_observations"]:
        inv.log("discover", "info", f"limiting to first {p['max_observations']} of {len(observations)} images")
        observations = observations[: p["max_observations"]]

    # ---- reference stars (Gaia DR3) around the target
    tangent = propagate(ast, p["discovery_epoch_jyear"])
    try:
        ref_rows, rprov = refs_mod.gaia_cone(fetcher, *propagate(ast, 2016.0), p["cutout_size_deg"] * 0.6,
                                             *p["reference_g_range"])
        ref_rows = [r for r in ref_rows if r.get("pmra") is not None and
                    angular_separation_deg(r["ra"], r["dec"], *propagate(ast, 2016.0)) * 3600 > 20]
        inv.log("references:gaia", "ok", f"{len(ref_rows)} reference-star candidates", {"n": len(ref_rows)}, [rprov])
    except ACQ_ERRORS as e:
        ref_rows = []
        inv.log("references:gaia", "failed", f"{e}; astrometry will be skipped")

    # ---- per-exposure retrieval + measurement
    measurements, inspected = [], set()
    for o in observations:
        if o.t_mid_mjd is None or o.detector is None:
            inv.log("measure", "rejected", f"{o.obs_id}: missing time or detector in archive metadata", asdict(o) | {"raw": None})
            continue
        epoch = float(mjd_to_jyear(o.t_mid_mjd))
        tra, tdec = propagate(ast, epoch)
        try:
            res = spherex.fetch_cutout(fetcher, o, tra, tdec, p["cutout_size_deg"])
            prod = load_product(res.content)
        except (*ACQ_ERRORS, ProductError) as e:
            inv.log("retrieve", "failed", f"{o.obs_id} D{o.detector}: {e}")
            continue
        if (o.release, o.detector) not in inspected:
            inspected.add((o.release, o.detector))
            inv.log("inspect", "info", f"product structure {o.release} D{o.detector}", inspect_product(prod), [res.provenance])
        refs_epoch = []
        for r in ref_rows:
            ra_r, dec_r = propagate(refs_mod.to_astrometry(r), epoch)
            refs_epoch.append({"ra": ra_r, "dec": dec_r, "source_id": r["source_id"]})
        try:
            m = measure_exposure(prod, o.obs_id, o.detector, o.t_mid_mjd, (tra, tdec), tangent,
                                 refs_epoch, p["aperture_radius_px"])
        except Exception as e:  # a measurement failure is logged, never hidden
            inv.log("measure", "failed", f"{o.obs_id} D{o.detector}: {type(e).__name__}: {e}", provenance=[res.provenance])
            continue
        measurements.append(m)
        inv.log("measure", "ok" if m.quality == "ok" else "rejected",
                f"{o.obs_id} D{o.detector} t={o.t_mid_mjd:.4f} λ={m.wavelength_um} µm: {m.quality}",
                asdict(m), [res.provenance])

    if not measurements:
        inv.log("compare", "skipped", "no measurements")
        return inv

    # ---- wavelength-matched flux comparison
    samples = [SourceSample(m.obs_id + f"/D{m.detector}", m.detector, m.mjd, m.wavelength_um or float("nan"),
                            m.bandwidth_um or float("nan"), m.quality) for m in measurements]
    decisions = match_pairs(samples, p["wavelength_tolerance_channels"])
    acc = [d for d in decisions if d.accepted]
    inv.log("pairs", "ok" if acc else "rejected",
            f"{len(acc)} wavelength-matched pairs accepted of {len(decisions)} considered",
            {"accepted": [asdict(d) for d in acc],
             "rejection_reasons": _count(d.reason.split(":")[0] for d in decisions if not d.accepted)})
    phot = {m.obs_id + f"/D{m.detector}": (m.photometry["flux_ujy"], m.photometry["flux_err_ujy"], m.photometry["status"])
            for m in measurements if m.photometry}
    fluxes, skipped = compare_fluxes(decisions, phot)
    inv.log("variability", "ok" if fluxes else "skipped",
            f"{len(fluxes)} flux comparisons; max |z| = {max((abs(f.z) for f in fluxes), default=float('nan')):.2f}",
            {"pairs": [asdict(f) for f in fluxes], "skipped": skipped})

    # ---- astrometric motion vs catalogue
    astro = [m for m in measurements if m.target_xi_eta_mas is not None]
    if len(astro) < 2:
        inv.log("astrometry", "skipped", f"{len(astro)} exposures with a plate solution; need >= 2")
        return inv
    t = [float(mjd_to_jyear(m.mjd)) for m in astro]
    xi = [m.target_xi_eta_mas[0] for m in astro]
    eta = [m.target_xi_eta_mas[1] for m in astro]
    sx = [math.sqrt(m.target_cov_mas2[0]) for m in astro]
    se = [math.sqrt(m.target_cov_mas2[1]) for m in astro]
    try:
        fit = fit_linear_motion(t, xi, eta, sx, se)
    except AstrometryError as e:
        inv.log("astrometry", "failed", str(e))
        return inv
    cmp = compare_to_catalogue(fit, ast.pmra, ast.pmdec)
    pred = [predicted_xi_eta_mas(*propagate(ast, ti), tangent) for ti in t]
    resid = [(xi[i] - pred[i][0], eta[i] - pred[i][1]) for i in range(len(t))]
    expected_shift = math.hypot(ast.pmra, ast.pmdec) * fit.baseline_yr
    inv.log("astrometry", "ok",
            f"measured pm = ({fit.pm_xi_mas_yr:.0f} ± {fit.sig_xi:.0f}, {fit.pm_eta_mas_yr:.0f} ± {fit.sig_eta:.0f}) mas/yr "
            f"over {fit.baseline_yr:.2f} yr, {fit.n_epochs} exposures; catalogue ({ast.pmra:.0f}, {ast.pmdec:.0f}); "
            f"consistent within 3σ: {cmp['consistent_within_3sigma']}",
            {"fit": asdict(fit), "catalogue": asdict(ast), "comparison": cmp,
             "position_residuals_vs_catalogue_mas": resid,
             "expected_total_shift_mas": expected_shift,
             "parallax_systematic_bound_mas": ast.parallax,
             "limitations": ["Parallax displacement (up to the catalogue parallax) is not modelled; it requires "
                             "the spacecraft ephemeris per exposure.",
                             "Chromatic PSF/distortion differences between wavelengths are not modelled."]})
    return inv


def _count(items) -> dict:
    out: dict[str, int] = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out
