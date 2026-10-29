"""Offline, deterministic investigation of one target bundle.

Reads only files listed in a verified bundle manifest; never touches the
network. Every step is logged in an Investigation, including rejected and
failed observations. The same bundle + parameters always produce the same
content hash (see report.Investigation.to_dict).

Version 2 (skytrace-analysis/2) adds, relative to version 1:
  * REFSEL-2 catalogue quality cut on reference stars (RUWE, duplicated_source, 5/6-p solution);
  * apparent positions with annual parallax (EPHEM-AA-LP-1) for target and references, and
    parallax-corrected target positions for the motion fit;
  * LINFIT-EPOCH-1 (visit-averaged positions) as the primary motion fit; per-exposure fit kept as a cross-check;
  * WLMATCH-2 (wavelength-accuracy margin, same-release photometry by default);
  * PAIRDIFF-2 reference-normalised photometry and CALCHECK-1 (scatter of constant reference stars);
  * structured status codes everywhere (no parsing of free-text reasons).
"""

from __future__ import annotations

import math
from dataclasses import asdict

from . import bundle as bmod
from .archive.products import ProductError, inspect_product, load_product
from .provenance import Provenance
from .report import Investigation
from .science import assess
from .science import ephemeris
from .science.astrometry import (EPOCH_METHOD, AstrometryError, compare_to_catalogue, epoch_average,
                                 fit_linear_motion, group_epochs)
from .science.coords import Astrometry, apparent_position, mjd_to_jyear, parallax_offset_at, propagate
from .science.measure import measure_exposure, predicted_xi_eta_mas
from .science.refsel import METHOD as REFSEL_METHOD, select_references
from .science.variability import METHOD as PAIRDIFF1, METHOD_DIFF as PAIRDIFF2, compare_fluxes, differential_pair, robust_scatter
from .science.wavelength import RULE_VERSION as WLMATCH, SourceSample, compare_pair, match_pairs

ANALYSIS_VERSION = "skytrace-analysis/2"
DEFAULTS = {
    "aperture_radius_px": 2.0,
    "fit_half_size_px": 4,
    "wavelength_tolerance_channels": 0.5,
    "wavelength_margin_um": 0.002,
    "photometry_same_release": True,
    "detectors": [1, 2, 3, 4, 5, 6],
    "max_observations": 400,
    "reader": "auto",
    "epoch_clip_sigma": 4.0,
    "epoch_gap_days": 3.0,
    "apply_parallax": True,
    "reference_quality_cut": True,
}
CALCHECK = "CALCHECK-1"
CALCHECK_MIN_REF_Z = 10
CALCHECK_MAX_SCATTER = 1.5   # reference-star z scatter above this -> error model underestimates


def methods() -> dict:
    return {"wavelength_match": WLMATCH, "reference_selection": REFSEL_METHOD, "ephemeris": ephemeris.METHOD,
            "variability": [PAIRDIFF1, PAIRDIFF2], "calibration_check": CALCHECK, "motion_primary": EPOCH_METHOD,
            "motion_crosscheck": "LINFIT-LOO-1", "assessment": assess.RULES}


def _prov(entry: dict | None) -> list[Provenance]:
    if not entry or not entry.get("provenance"):
        return []
    p = dict(entry["provenance"])
    if not p.get("content_sha256"):   # tie the record to the stored bytes (manifest SHA-256)
        p["content_sha256"] = entry.get("sha256", "")
    return [Provenance.from_dict(p)]


def target_astrometry(b: bmod.Bundle) -> Astrometry:
    a = b.target["astrometry"]
    return Astrometry(ra=a["ra"], dec=a["dec"], ref_epoch=a["ref_epoch"], pmra=a.get("pmra") or 0.0,
                      pmdec=a.get("pmdec") or 0.0, parallax=a.get("parallax") or 0.0,
                      radial_velocity=a.get("radial_velocity") or 0.0, source=a.get("source", ""))


def _ref_astrometry(r: dict, with_parallax: bool) -> Astrometry:
    return Astrometry(r["ra"], r["dec"], r.get("ref_epoch") or 2016.0, r.get("pmra") or 0.0, r.get("pmdec") or 0.0,
                      parallax=(r.get("parallax") or 0.0) if with_parallax else 0.0)


def _count(d: dict, k: str) -> None:
    d[k] = d.get(k, 0) + 1


def run(b: bmod.Bundle, params: dict | None = None) -> Investigation:
    p = {**DEFAULTS, **(params or {})}
    inv = Investigation(b.target.get("name", b.target_id),
                        {**p, "analysis_version": ANALYSIS_VERSION, "methods": methods(), "bundle": b.target_id,
                         "bundle_kind": b.kind, "bundle_manifest_sha256": bmod.sha256_file(b.path / "manifest.json")})
    tprov = _prov(b.file_entry("target.json"))
    ast = target_astrometry(b)
    tast = b.target["astrometry"]
    inv.log("target", "ok", f"{b.target.get('name')}: catalogue astrometry from {ast.source}",
            {"identity": b.target.get("identity", {}), "astrometry": asdict(ast)}, tprov)

    disc_prov = _prov(b.file_entry("discovery.json"))
    all_obs = b.all_observations()
    excluded = [o for o in all_obs if not o.get("included")]
    inv.log("discover", "ok", f"{len(all_obs)} archive images recorded; {len(all_obs) - len(excluded)} included by "
            f"selection criteria", {"criteria": b.discovery.get("selection", {}),
                                    "n_total": len(all_obs), "n_excluded": len(excluded)}, disc_prov)
    for o in excluded:
        inv.log("select", "rejected", f"{o['key']}: {o.get('exclusion_reason', 'excluded')}",
                {"key": o["key"], "code": o.get("exclusion_code", "selection_excluded")})

    obs = [o for o in b.observations() if o.get("detector") in p["detectors"]][: p["max_observations"]]
    stars = b.references.get("stars", [])
    if p["reference_quality_cut"]:
        good, sel = select_references(stars)
    else:
        good, sel = list(stars), {"method": "none", "n_input": len(stars), "n_kept": len(stars)}
    good_ids = {str(s["source_id"]) for s in good}
    inv.log("references", "ok" if good else "rejected",
            f"{len(good)} of {len(stars)} catalogue stars pass the reference quality cut ({sel['method']}) "
            f"from {b.references.get('catalogue', 'unknown catalogue')}",
            {"n": len(good), "n_catalogue": len(stars), "catalogue": b.references.get("catalogue"), "selection": sel},
            _prov(b.file_entry("references.json")))
    tangent = propagate(ast, float(mjd_to_jyear(median_mjd(obs)))) if obs else (ast.ra, ast.dec)
    plx_on = bool(p["apply_parallax"])

    measurements, meta, inspected = [], {}, set()
    for o in obs:
        key = o["key"]
        fe = b.file_entry(o["file"])
        if o.get("t_mid_mjd") is None:
            inv.log("measure", "rejected", f"{key}: no observation time in archive metadata",
                    {"key": key, "quality_code": "no_time", "astro_code": "no_time"}, _prov(fe))
            continue
        try:
            prod = load_product(b.path / o["file"], prefer=p["reader"])
        except ProductError as e:
            inv.log("measure", "failed", f"{key}: unreadable product: {e}",
                    {"key": key, "quality_code": "unreadable", "astro_code": "unreadable"}, _prov(fe))
            continue
        if (o["release"], o["detector"]) not in inspected:
            inspected.add((o["release"], o["detector"]))
            inv.log("inspect", "info", f"product structure {o['release']} D{o['detector']} (reader: {prod.reader})",
                    {"key": key, **inspect_product(prod)}, _prov(fe))
        mjd = o["t_mid_mjd"]
        tpos = apparent_position(ast, mjd) if plx_on else propagate(ast, float(mjd_to_jyear(mjd)))
        refs_ep = []
        for r in stars:
            rra, rdec = apparent_position(_ref_astrometry(r, plx_on), mjd)
            refs_ep.append({"ra": rra, "dec": rdec, "source_id": r["source_id"],
                            "use_as_reference": str(r["source_id"]) in good_ids})
        try:
            m = measure_exposure(prod, key, o["detector"], mjd, tpos, tangent, refs_ep,
                                 p["aperture_radius_px"], p["fit_half_size_px"])
        except Exception as e:  # logged, never hidden
            inv.log("measure", "failed", f"{key}: {type(e).__name__}: {e}",
                    {"key": key, "quality_code": "measurement_error", "astro_code": "measurement_error"}, _prov(fe))
            continue
        plx = parallax_offset_at(ast, mjd) if plx_on else (0.0, 0.0)
        measurements.append(m)
        meta[m.obs_id] = {"release": o["release"], "parallax_offset_mas": plx}
        d = asdict(m)
        d.update({"key": key, "release": o["release"], "t_mid_iso": o.get("t_mid_iso"), "file": o["file"],
                  "parallax_offset_mas": list(plx)})
        wl = f"{m.wavelength_um:.4f} µm" if m.wavelength_um else "λ unknown"
        usable = m.quality_code == "ok" or m.astro_code == "ok"
        inv.log("measure", "ok" if usable else "rejected",
                f"{key} ({wl}): photometry {m.quality_code}; astrometry {m.astro_code}", d, _prov(fe))

    if not measurements:
        n = len(obs)
        inv.log("assess", "info", "no measurements; nothing to assess",
                {"outcomes": [assess.assess_quality(n, n, {"unreadable_or_missing": n})]})
        return inv
    by_id = {m.obs_id: m for m in measurements}

    # ---------------------------------------------------------------- wavelength-matched pairs
    samples = [SourceSample(m.obs_id, m.detector, m.mjd, m.wavelength_um if m.wavelength_um else float("nan"),
                            m.bandwidth_um if m.bandwidth_um else float("nan"), m.quality_code,
                            meta[m.obs_id]["release"]) for m in measurements]
    decisions = match_pairs(samples, p["wavelength_tolerance_channels"], margin_um=p["wavelength_margin_um"],
                            same_release=p["photometry_same_release"])
    acc = [d for d in decisions if d.accepted]
    reasons: dict[str, int] = {}
    for d in decisions:
        if not d.accepted:
            _count(reasons, d.code)
    inv.log("pairs", "ok" if acc else "rejected",
            f"{len(acc)} wavelength-matched pairs accepted of {len(decisions)} considered (rule {WLMATCH})",
            {"accepted": [asdict(d) for d in acc], "rejection_reasons": reasons, "rule": WLMATCH,
             "margin_um": p["wavelength_margin_um"], "same_release": p["photometry_same_release"],
             "rejected_same_detector": [asdict(d) for d in decisions if d.code in ("wavelength_mismatch", "wavelength_ambiguous",
                                                                                     "different_releases")][:200]})

    # ---------------------------------------------------------------- photometry: PAIRDIFF-1 and PAIRDIFF-2
    phot = {m.obs_id: (m.photometry["flux_ujy"], m.photometry["flux_err_ujy"], m.photometry["status"])
            for m in measurements if m.photometry}
    fluxes, skipped = compare_fluxes(decisions, phot)
    flux_d, ref_z_all = [], []
    for f in fluxes:
        dp = differential_pair(f, by_id[f.a].ref_photometry, by_id[f.b].ref_photometry,
                               p["wavelength_tolerance_channels"], p["wavelength_margin_um"])
        ref_z_all.extend(dp.get("ref_z", []))
        flux_d.append({**asdict(f), "differential": dp})
    scatter = robust_scatter(ref_z_all)
    if len(ref_z_all) < CALCHECK_MIN_REF_Z or not math.isfinite(scatter):
        cal = {"method": CALCHECK, "status": "insufficient", "n_ref_z": len(ref_z_all), "robust_scatter": None,
               "error_scale": None,
               "note": f"fewer than {CALCHECK_MIN_REF_Z} reference-star comparisons; the error model cannot be checked"}
    else:
        cal = {"method": CALCHECK, "n_ref_z": len(ref_z_all), "robust_scatter": scatter,
               "error_scale": max(1.0, scatter),
               "status": "ok" if scatter <= CALCHECK_MAX_SCATTER else "underestimated",
               "note": "robust scatter (1.4826 MAD) of normalised flux differences of constant reference stars; "
                       "1 means the stated errors describe them"}
    for fd in flux_d:
        dp = fd["differential"]
        if dp.get("calibrated") and cal["error_scale"]:
            dp["z_cal_scaled"] = dp["z_cal"] / cal["error_scale"]
    n_cal = sum(1 for fd in flux_d if fd["differential"].get("calibrated"))
    inv.log("variability", "ok" if fluxes else "skipped",
            f"{len(fluxes)} matched-pair flux comparisons ({n_cal} reference-calibrated); max |z| = "
            f"{max((abs(f.z) for f in fluxes), default=float('nan')):.2f}",
            {"pairs": flux_d, "skipped": skipped, "calibration_check": cal, "methods": [PAIRDIFF1, PAIRDIFF2]})

    # spectral context: same detector, wavelength mismatch (shows spectrum, not variability)
    spectral = []
    for d in decisions:
        if d.code == "wavelength_mismatch" and d.a in phot and d.b in phot:
            fa, fb = phot[d.a], phot[d.b]
            if fa[2] == fb[2] == "ok":
                s = math.hypot(fa[1], fb[1])
                spectral.append({"a": d.a, "b": d.b, "delta_lambda_um": d.delta_lambda_um, "delta_t_days": d.delta_t_days,
                                 "z": (fb[0] - fa[0]) / s if s > 0 else None})
    inv.log("spectral_context", "info",
            f"{len(spectral)} same-detector pairs at different wavelengths (context only: differences reflect the spectrum)",
            {"pairs": spectral[:200]})

    # ---------------------------------------------------------------- spectrum
    spec = [{"key": m.obs_id, "detector": m.detector, "mjd": m.mjd, "release": meta[m.obs_id]["release"],
             "wavelength_um": m.wavelength_um, "bandwidth_um": m.bandwidth_um, "flux_ujy": m.photometry["flux_ujy"],
             "flux_err_ujy": m.photometry["flux_err_ujy"], "status": m.photometry["status"],
             "quality_code": m.quality_code, "usable": m.quality_code == "ok"}
            for m in measurements if m.wavelength_um and m.photometry]
    inv.log("spectrum", "ok" if any(s["usable"] for s in spec) else "rejected",
            f"{sum(s['usable'] for s in spec)} usable spectral points from {len(spec)} exposures "
            "(aperture fluxes; not aperture-corrected; mixed epochs)", {"points": spec})

    # ---------------------------------------------------------------- astrometry
    astro = [m for m in measurements if m.astro_code == "ok" and m.target_xi_eta_mas is not None]
    motion, epochs, fit_error = None, [], None
    pmra_err, pmdec_err = tast.get("pmra_error") or 0.0, tast.get("pmdec_error") or 0.0
    plx_info = {"applied": plx_on, "method": ephemeris.METHOD if plx_on else None, "parallax_mas": ast.parallax,
                "systematic_bound_mas": ast.parallax * ephemeris.SYSTEMATIC_FRACTION_OF_PARALLAX if plx_on else ast.parallax}
    if len(astro) >= 2:
        mjds = [m.mjd for m in astro]
        t = [float(mjd_to_jyear(x)) for x in mjds]
        xi = [m.target_xi_eta_mas[0] - meta[m.obs_id]["parallax_offset_mas"][0] for m in astro]
        eta = [m.target_xi_eta_mas[1] - meta[m.obs_id]["parallax_offset_mas"][1] for m in astro]
        sx = [math.sqrt(m.target_cov_mas2[0]) for m in astro]
        se = [math.sqrt(m.target_cov_mas2[1]) for m in astro]
        epochs = epoch_average(mjds, xi, eta, sx, se, group_epochs(mjds, p["epoch_gap_days"]))
        exp_fit = epoch_fit = None
        errors = {}
        try:
            exp_fit = fit_linear_motion(t, xi, eta, sx, se, clip_sigma=p["epoch_clip_sigma"])
        except AstrometryError as e:
            errors["exposure_fit"] = str(e)
        if len(epochs) >= 2:
            try:
                epoch_fit = fit_linear_motion([float(mjd_to_jyear(e["t_mjd"])) for e in epochs],
                                              [e["xi_mas"] for e in epochs], [e["eta_mas"] for e in epochs],
                                              [e["sig_xi_mas"] for e in epochs], [e["sig_eta_mas"] for e in epochs],
                                              clip_sigma=p["epoch_clip_sigma"])
            except AstrometryError as e:
                errors["epoch_fit"] = str(e)
        else:
            errors["epoch_fit"] = f"{len(epochs)} visit(s) separated by more than {p['epoch_gap_days']} d; need 2"
        primary, kind = (epoch_fit, "epoch") if epoch_fit else (exp_fit, "exposure")
        if primary is None:
            fit_error = "; ".join(f"{k}: {v}" for k, v in errors.items())
            inv.log("astrometry", "failed", "; ".join(f"{k}: {v}" for k, v in errors.items()),
                    {"code": "fit_failed", "errors": errors, "epochs": epochs})
        else:
            cmp = compare_to_catalogue(primary, ast.pmra, ast.pmdec, pmra_err, pmdec_err)
            pred = [predicted_xi_eta_mas(*propagate(ast, ti), tangent) for ti in t]
            ep_of = {i: k for k, e in enumerate(epochs) for i in e["members"]}
            rej_exp = set(exp_fit.rejected) if exp_fit else set()
            series = [{"key": m.obs_id, "t_jyear": ti, "xi_mas": x, "eta_mas": e, "sig_xi_mas": a, "sig_eta_mas": c,
                       "pred_xi_mas": pr[0], "pred_eta_mas": pr[1], "plate_rms_mas": m.plate["rms_mas"],
                       "n_refs": m.plate["n_refs"], "used_in_fit": i not in rej_exp, "epoch": ep_of.get(i),
                       "parallax_offset_mas": list(meta[m.obs_id]["parallax_offset_mas"])}
                      for i, (m, ti, x, e, a, c, pr) in enumerate(zip(astro, t, xi, eta, sx, se, pred))]
            motion = {"fit": asdict(primary), "fit_kind": kind, "comparison": cmp,
                      "exposure_fit": asdict(exp_fit) if exp_fit else None,
                      "epoch_fit": asdict(epoch_fit) if epoch_fit else None,
                      "comparison_exposure_fit": compare_to_catalogue(exp_fit, ast.pmra, ast.pmdec, pmra_err, pmdec_err) if exp_fit else None,
                      "epochs": epochs, "fit_errors": errors, "series": series,
                      "catalogue": {"pmra": ast.pmra, "pmdec": ast.pmdec, "pmra_error": pmra_err,
                                    "pmdec_error": pmdec_err, "source": ast.source},
                      "parallax": plx_info, "parallax_systematic_bound_mas": plx_info["systematic_bound_mas"]}
            note = "" if kind == "epoch" else " (single visit: per-exposure fit; correlated errors within a visit are not captured)"
            inv.log("astrometry", "ok",
                    f"measured pm = ({primary.pm_xi_mas_yr:.0f} ± {primary.sig_xi:.0f}, {primary.pm_eta_mas_yr:.0f} ± "
                    f"{primary.sig_eta:.0f}) mas/yr from {primary.n_epochs} {kind}s ({len(primary.rejected)} rejected as "
                    f"outliers) over {primary.baseline_yr:.2f} yr; catalogue ({ast.pmra:.0f}, {ast.pmdec:.0f}) mas/yr{note}",
                    motion)
    else:
        inv.log("astrometry", "skipped", f"{len(astro)} exposure(s) with a usable target position and plate solution; need at least 2",
                {"code": "too_few_exposures", "n": len(astro)})

    # ---------------------------------------------------------------- assessment
    rej_reasons: dict[str, int] = {}
    for m in measurements:
        if m.quality_code != "ok" and m.astro_code != "ok":
            _count(rej_reasons, m.quality_code if m.quality_code == m.astro_code else f"{m.quality_code}/{m.astro_code}")
    for e in inv.events:
        if e.step == "measure" and e.status in ("failed", "rejected") and e.data.get("quality_code") in (
                "unreadable", "measurement_error", "no_time"):
            _count(rej_reasons, e.data["quality_code"])
    n_total = len(measurements) + sum(v for k, v in rej_reasons.items() if k in ("unreadable", "measurement_error", "no_time"))
    times = [e["t_mjd"] for e in epochs] if epochs else sorted({round(m.mjd, 3) for m in astro})
    gaps = [(b_ - a_) / 365.25 for a_, b_ in zip(times, times[1:])]
    outcomes = [
        assess.assess_quality(n_total, sum(rej_reasons.values()), rej_reasons),
        assess.assess_motion(motion, {"pmra": ast.pmra, "pmdec": ast.pmdec}, len(astro),
                             [m.plate["rms_mas"] for m in astro], gaps, fit_error),
        assess.assess_variability(flux_d, spectral, len(decisions), cal),
    ]
    inv.log("assess", "ok", "; ".join(f"{o['question']}: {o['category']}" for o in outcomes),
            {"outcomes": outcomes, "thresholds": assess.T, "rules": assess.RULES,
             "threshold_provenance": assess.THRESHOLD_PROVENANCE})
    return inv


def median_mjd(obs: list[dict]) -> float:
    t = sorted(o["t_mid_mjd"] for o in obs if o.get("t_mid_mjd") is not None)
    return t[len(t) // 2] if t else 60900.0


def _sample(m: dict) -> SourceSample:
    q = m.get("quality_code") or ("ok" if m.get("quality") == "ok" else str(m.get("quality")))
    return SourceSample(m["key"], m["detector"], m["mjd"], m.get("wavelength_um") or float("nan"),
                        m.get("bandwidth_um") or float("nan"), q, m.get("release", ""))


def pair_decision(m_a: dict, m_b: dict, tolerance: float = 0.5, margin_um: float = DEFAULTS["wavelength_margin_um"],
                  same_release: bool = DEFAULTS["photometry_same_release"]) -> dict:
    """Compatibility of two logged measurements (used by the API and copilot tools)."""
    return asdict(compare_pair(_sample(m_a), _sample(m_b), tolerance, margin_um=margin_um, same_release=same_release))
