"""Offline, deterministic investigation of one target bundle.

Reads only files listed in a verified bundle manifest; never touches the
network. Every step is logged in an Investigation, including rejected and
failed observations. The same bundle + parameters always produce the same
content hash (see report.Investigation.to_dict).
"""

from __future__ import annotations

import math
from dataclasses import asdict

from . import bundle as bmod
from .archive.products import ProductError, inspect_product, load_product
from .provenance import Provenance
from .report import Investigation
from .science import assess
from .science.astrometry import AstrometryError, compare_to_catalogue, fit_linear_motion
from .science.coords import Astrometry, mjd_to_jyear, propagate
from .science.measure import measure_exposure, predicted_xi_eta_mas
from .science.variability import compare_fluxes
from .science.wavelength import SourceSample, compare_pair, match_pairs, reason_category

ANALYSIS_VERSION = "skytrace-analysis/1"
DEFAULTS = {
    "aperture_radius_px": 2.0,
    "fit_half_size_px": 4,
    "wavelength_tolerance_channels": 0.5,
    "detectors": [1, 2, 3, 4, 5, 6],
    "max_observations": 400,
    "reader": "auto",
    "epoch_clip_sigma": 4.0,
}


def _prov(entry: dict | None) -> list[Provenance]:
    if not entry or not entry.get("provenance"):
        return []
    p = dict(entry["provenance"])
    p.setdefault("content_sha256", entry.get("sha256", ""))
    return [Provenance.from_dict(p)]


def target_astrometry(b: bmod.Bundle) -> Astrometry:
    a = b.target["astrometry"]
    return Astrometry(ra=a["ra"], dec=a["dec"], ref_epoch=a["ref_epoch"], pmra=a.get("pmra") or 0.0,
                      pmdec=a.get("pmdec") or 0.0, parallax=a.get("parallax") or 0.0,
                      radial_velocity=a.get("radial_velocity") or 0.0, source=a.get("source", ""))


def run(b: bmod.Bundle, params: dict | None = None) -> Investigation:
    p = {**DEFAULTS, **(params or {})}
    inv = Investigation(b.target.get("name", b.target_id),
                        {**p, "analysis_version": ANALYSIS_VERSION, "bundle": b.target_id, "bundle_kind": b.kind,
                         "bundle_manifest_sha256": bmod.sha256_file(b.path / "manifest.json")})
    tprov = _prov(b.file_entry("target.json"))
    ast = target_astrometry(b)
    inv.log("target", "ok", f"{b.target.get('name')}: catalogue astrometry from {ast.source}",
            {"identity": b.target.get("identity", {}), "astrometry": asdict(ast)}, tprov)

    disc_prov = _prov(b.file_entry("discovery.json"))
    all_obs = b.all_observations()
    excluded = [o for o in all_obs if not o.get("included")]
    inv.log("discover", "ok", f"{len(all_obs)} archive images recorded; {len(all_obs) - len(excluded)} included by "
            f"selection criteria", {"criteria": b.discovery.get("selection", {}),
                                    "n_total": len(all_obs), "n_excluded": len(excluded)}, disc_prov)
    for o in excluded:
        inv.log("select", "rejected", f"{o['key']}: {o.get('exclusion_reason', 'excluded')}", {"key": o["key"]})

    obs = [o for o in b.observations() if o.get("detector") in p["detectors"]][: p["max_observations"]]
    refs = b.references.get("stars", [])
    inv.log("references", "ok" if refs else "rejected",
            f"{len(refs)} astrometric reference stars from {b.references.get('catalogue', 'unknown catalogue')}",
            {"n": len(refs), "catalogue": b.references.get("catalogue")}, _prov(b.file_entry("references.json")))
    tangent = propagate(ast, float(mjd_to_jyear(median_mjd(obs)))) if obs else (ast.ra, ast.dec)

    measurements, inspected = [], set()
    for o in obs:
        key = o["key"]
        fe = b.file_entry(o["file"])
        if o.get("t_mid_mjd") is None:
            inv.log("measure", "rejected", f"{key}: no observation time in archive metadata", {"key": key}, _prov(fe))
            continue
        try:
            prod = load_product(b.path / o["file"], prefer=p["reader"])
        except ProductError as e:
            inv.log("measure", "failed", f"{key}: unreadable product: {e}", {"key": key}, _prov(fe))
            continue
        if (o["release"], o["detector"]) not in inspected:
            inspected.add((o["release"], o["detector"]))
            inv.log("inspect", "info", f"product structure {o['release']} D{o['detector']} (reader: {prod.reader})",
                    {"key": key, **inspect_product(prod)}, _prov(fe))
        epoch = float(mjd_to_jyear(o["t_mid_mjd"]))
        tra, tdec = propagate(ast, epoch)
        refs_ep = []
        for r in refs:
            ra_r, dec_r = propagate(Astrometry(r["ra"], r["dec"], r.get("ref_epoch", 2016.0), r.get("pmra") or 0.0,
                                               r.get("pmdec") or 0.0), epoch)
            refs_ep.append({"ra": ra_r, "dec": dec_r, "source_id": r["source_id"]})
        try:
            m = measure_exposure(prod, key, o["detector"], o["t_mid_mjd"], (tra, tdec), tangent, refs_ep,
                                 p["aperture_radius_px"], p["fit_half_size_px"])
        except Exception as e:  # logged, never hidden
            inv.log("measure", "failed", f"{key}: {type(e).__name__}: {e}", {"key": key}, _prov(fe))
            continue
        measurements.append(m)
        d = asdict(m)
        d["key"], d["release"], d["t_mid_iso"], d["file"] = key, o["release"], o.get("t_mid_iso"), o["file"]
        wl = f"{m.wavelength_um:.4f} µm" if m.wavelength_um else "λ unknown"
        inv.log("measure", "ok" if m.quality == "ok" else "rejected", f"{key} ({wl}): {m.quality}", d, _prov(fe))

    if not measurements:
        inv.log("assess", "info", "no measurements; nothing to assess",
                {"outcomes": [assess.assess_quality(len(obs), len(obs), {"unreadable or missing": len(obs)})]})
        return inv

    # ---------------------------------------------------------------- wavelength-matched pairs
    samples = [SourceSample(m.obs_id, m.detector, m.mjd, m.wavelength_um if m.wavelength_um else float("nan"),
                            m.bandwidth_um if m.bandwidth_um else float("nan"), m.quality) for m in measurements]
    decisions = match_pairs(samples, p["wavelength_tolerance_channels"])
    acc = [d for d in decisions if d.accepted]
    reasons: dict[str, int] = {}
    for d in decisions:
        if not d.accepted:
            r = reason_category(d.reason)
            reasons[r] = reasons.get(r, 0) + 1
    inv.log("pairs", "ok" if acc else "rejected",
            f"{len(acc)} wavelength-matched pairs accepted of {len(decisions)} considered (rule WLMATCH-1)",
            {"accepted": [asdict(d) for d in acc], "rejection_reasons": reasons,
             "rejected_same_detector": [asdict(d) for d in decisions if not d.accepted and d.reason.startswith("wavelength mismatch")][:200]})
    phot = {m.obs_id: (m.photometry["flux_ujy"], m.photometry["flux_err_ujy"], m.photometry["status"])
            for m in measurements if m.photometry}
    fluxes, skipped = compare_fluxes(decisions, phot)
    flux_d = [asdict(f) for f in fluxes]
    inv.log("variability", "ok" if fluxes else "skipped",
            f"{len(fluxes)} matched-pair flux comparisons; max |z| = "
            f"{max((abs(f.z) for f in fluxes), default=float('nan')):.2f}", {"pairs": flux_d, "skipped": skipped})

    # spectral context: same detector, wavelength mismatch (shows spectrum, not variability)
    spectral = []
    for d in decisions:
        if not d.accepted and d.reason.startswith("wavelength mismatch") and d.a in phot and d.b in phot:
            fa, fb = phot[d.a], phot[d.b]
            if fa[2] == fb[2] == "ok":
                s = math.hypot(fa[1], fb[1])
                spectral.append({"a": d.a, "b": d.b, "delta_lambda_um": d.delta_lambda_um, "delta_t_days": d.delta_t_days,
                                 "z": (fb[0] - fa[0]) / s if s > 0 else None})
    inv.log("spectral_context", "info",
            f"{len(spectral)} same-detector pairs at different wavelengths (context only: differences reflect the spectrum)",
            {"pairs": spectral[:200]})

    # ---------------------------------------------------------------- spectrum
    spec = [{"key": m.obs_id, "detector": m.detector, "mjd": m.mjd, "wavelength_um": m.wavelength_um,
             "bandwidth_um": m.bandwidth_um, "flux_ujy": m.photometry["flux_ujy"], "flux_err_ujy": m.photometry["flux_err_ujy"],
             "status": m.photometry["status"]} for m in measurements if m.wavelength_um and m.photometry]
    inv.log("spectrum", "ok" if any(s["status"] == "ok" for s in spec) else "rejected",
            f"{sum(s['status'] == 'ok' for s in spec)} usable spectral points from {len(spec)} exposures "
            "(aperture fluxes; not aperture-corrected; mixed epochs)", {"points": spec})

    # ---------------------------------------------------------------- astrometry
    astro = [m for m in measurements if m.target_xi_eta_mas is not None]
    motion = None
    if len(astro) >= 2:
        t = [float(mjd_to_jyear(m.mjd)) for m in astro]
        xi = [m.target_xi_eta_mas[0] for m in astro]
        eta = [m.target_xi_eta_mas[1] for m in astro]
        sx = [math.sqrt(m.target_cov_mas2[0]) for m in astro]
        se = [math.sqrt(m.target_cov_mas2[1]) for m in astro]
        try:
            fit = fit_linear_motion(t, xi, eta, sx, se, clip_sigma=p["epoch_clip_sigma"])
            cmp = compare_to_catalogue(fit, ast.pmra, ast.pmdec)
            pred = [predicted_xi_eta_mas(*propagate(ast, ti), tangent) for ti in t]
            series = [{"key": m.obs_id, "t_jyear": ti, "xi_mas": x, "eta_mas": e, "sig_xi_mas": a, "sig_eta_mas": c,
                       "pred_xi_mas": pr[0], "pred_eta_mas": pr[1], "plate_rms_mas": m.plate["rms_mas"],
                       "n_refs": m.plate["n_refs"], "used_in_fit": i not in fit.rejected}
                      for i, (m, ti, x, e, a, c, pr) in enumerate(zip(astro, t, xi, eta, sx, se, pred))]
            motion = {"fit": asdict(fit), "comparison": cmp, "series": series,
                      "catalogue": {"pmra": ast.pmra, "pmdec": ast.pmdec, "source": ast.source},
                      "parallax_systematic_bound_mas": ast.parallax}
            inv.log("astrometry", "ok",
                    f"measured pm = ({fit.pm_xi_mas_yr:.0f} ± {fit.sig_xi:.0f}, {fit.pm_eta_mas_yr:.0f} ± {fit.sig_eta:.0f}) "
                    f"mas/yr from {fit.n_epochs} exposures ({len(fit.rejected)} rejected as outliers) over {fit.baseline_yr:.2f} yr; catalogue "
                    f"({ast.pmra:.0f}, {ast.pmdec:.0f}) mas/yr", motion)
        except AstrometryError as e:
            inv.log("astrometry", "failed", str(e))
    else:
        inv.log("astrometry", "skipped", f"{len(astro)} exposure(s) with a plate solution; need at least 2")

    # ---------------------------------------------------------------- assessment
    rej_reasons: dict[str, int] = {}
    for m in measurements:
        if m.quality != "ok":
            k = m.quality.split(":")[0]
            rej_reasons[k] = rej_reasons.get(k, 0) + 1
    n_failed = sum(1 for e in inv.events if e.step == "measure" and e.status in ("failed",))
    if n_failed:
        rej_reasons["unreadable or failed"] = n_failed
    times = sorted({round(m.mjd, 3) for m in astro})
    gaps = [(b_ - a_) / 365.25 for a_, b_ in zip(times, times[1:])]
    outcomes = [
        assess.assess_quality(len(measurements) + n_failed, sum(rej_reasons.values()), rej_reasons),
        assess.assess_motion(motion, {"pmra": ast.pmra, "pmdec": ast.pmdec}, len(astro),
                             [m.plate["rms_mas"] for m in astro], gaps),
        assess.assess_variability(flux_d, spectral, len(decisions)),
    ]
    inv.log("assess", "ok", "; ".join(f"{o['question']}: {o['category']}" for o in outcomes),
            {"outcomes": outcomes, "thresholds": assess.T, "rules": assess.RULES})
    return inv


def median_mjd(obs: list[dict]) -> float:
    t = sorted(o["t_mid_mjd"] for o in obs if o.get("t_mid_mjd") is not None)
    return t[len(t) // 2] if t else 60900.0


def pair_decision(m_a: dict, m_b: dict, tolerance: float = 0.5) -> dict:
    """Compatibility of two logged measurements (used by the API and copilot tools)."""
    sa = SourceSample(m_a["key"], m_a["detector"], m_a["mjd"], m_a.get("wavelength_um") or float("nan"),
                      m_a.get("bandwidth_um") or float("nan"), m_a["quality"])
    sb = SourceSample(m_b["key"], m_b["detector"], m_b["mjd"], m_b.get("wavelength_um") or float("nan"),
                      m_b.get("bandwidth_um") or float("nan"), m_b["quality"])
    return asdict(compare_pair(sa, sb, tolerance))


