"""Algorithm tests on SYNTHETIC images (labelled; not observations)."""

import math

import numpy as np
import pytest

from skytrace.science import centroid as cen
from skytrace.science import photometry as ph
from skytrace.science.astrometry import AstrometryError, compare_to_catalogue, fit_linear_motion, solve_plate
from skytrace.science.coords import Astrometry, gnomonic, mjd_to_jyear, propagate
from skytrace.science.measure import measure_exposure
from skytrace.science.wavelength import SourceSample, match_pairs
from synthetic import SyntheticProduct


def star_image(x0, y0, amp=50.0, sigma=0.9, shape=(21, 21), noise=0.05, sky=1.0, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(shape)
    model = sky + amp * np.exp(-0.5 * ((xx - x0) ** 2 + (yy - y0) ** 2) / sigma ** 2)
    var = np.full(shape, noise ** 2)
    return model + rng.normal(0, noise, shape), var


def test_centroid_recovers_subpixel_position():
    img, var = star_image(10.37, 9.81)
    c = cen.fit_centroid(img, var, 10, 10)
    assert c.converged
    assert abs(c.x - 10.37) < 5 * c.sigma_x and abs(c.y - 9.81) < 5 * c.sigma_y
    assert c.sigma_x < 0.01


def test_centroid_uncertainty_is_calibrated():
    """Pull distribution over noise realisations should have unit width (no over/under-confidence)."""
    pulls = []
    for seed in range(150):
        img, var = star_image(10.2, 10.6, amp=8.0, noise=0.3, seed=seed)
        c = cen.fit_centroid(img, var, 10, 10)
        if c.converged:
            pulls.append((c.x - 10.2) / c.sigma_x)
    pulls = np.array(pulls)
    assert len(pulls) > 140
    assert abs(pulls.mean()) < 0.25
    assert 0.8 < pulls.std() < 1.25


def test_centroid_ignores_masked_pixels():
    img, var = star_image(10.0, 10.0)
    bad = np.zeros(img.shape, bool)
    img[10, 12] = 1e6           # a hot pixel next to the star
    bad[10, 12] = True
    c = cen.fit_centroid(img, var, 10, 10, bad=bad)
    assert c.converged and abs(c.x - 10.0) < 0.05 and c.n_masked == 1


def test_centroid_reports_failure_instead_of_guessing():
    img, var = star_image(1.0, 10.0)
    assert not cen.fit_centroid(img, var, 1, 10).converged
    flat = np.ones((21, 21))
    assert not cen.fit_centroid(flat, np.full((21, 21), 0.01), 10, 10).converged


def test_moment_centroid_cross_check():
    img, _ = star_image(10.3, 9.7, noise=0.0)
    x, y = cen.first_moment(img, 10.3, 9.7, background=1.0, radius=4)
    assert x == pytest.approx(10.3, abs=0.02) and y == pytest.approx(9.7, abs=0.02)


def test_photometry_recovers_flux_and_errors():
    sigma, amp = 0.9, 40.0
    omega = ph.pixel_solid_angle_from_scale(6.2)
    # truth = the same aperture applied to the noiseless, sky-free model (isolates noise behaviour
    # from pixel-sampling of the analytic profile)
    noiseless, _ = star_image(15.2, 14.8, amp=amp, sigma=sigma, shape=(31, 31), noise=0.0, sky=0.0)
    true_in_ap = float(np.sum(ph.aperture_weights((31, 31), 15.2, 14.8, 3.0) * noiseless))
    pulls = []
    for seed in range(100):
        img, var = star_image(15.2, 14.8, amp=amp, sigma=sigma, shape=(31, 31), noise=0.2, seed=seed)
        p = ph.aperture_photometry(img, var, 15.2, 14.8, omega, r_ap=3.0, r_in=6, r_out=10)
        assert p.status == "ok"
        pulls.append((p.flux_ujy / (omega * 1e12) - true_in_ap) / (p.flux_err_ujy / (omega * 1e12)))
    pulls = np.array(pulls)
    assert abs(pulls.mean()) < 0.3 and 0.75 < pulls.std() < 1.3


def test_photometry_flagged_returns_nan():
    img, var = star_image(10, 10, shape=(31, 31))
    bad = np.zeros(img.shape, bool)
    bad[10, 10] = True
    p = ph.aperture_photometry(img, var, 10, 10, 1e-9, bad=bad)
    assert p.status == "flagged" and math.isnan(p.flux_ujy)


def test_photometry_no_sky_and_off_image():
    img, var = star_image(10, 10, shape=(21, 21))
    assert ph.aperture_photometry(img, var, 10, 10, 1e-9, r_in=30, r_out=40).status == "no-sky"
    assert ph.aperture_photometry(img, var, 0.5, 10, 1e-9).status == "off-image"


def test_plate_solution_recovers_transform_and_rejects_outlier():
    rng = np.random.default_rng(1)
    prod = SyntheticProduct(crval=(150.0, 20.0), rotation_deg=7.0)
    ra = 150.0 + rng.uniform(-0.04, 0.04, 12)
    dec = 20.0 + rng.uniform(-0.04, 0.04, 12)
    xy = np.array([prod.sky_to_pixel(r, d) for r, d in zip(ra, dec)])
    xy += rng.normal(0, 0.01, xy.shape)
    xy[3] += 3.0  # a mismatched star
    sol = solve_plate(ra, dec, xy[:, 0], xy[:, 1], np.full(12, 0.01), (150.0, 20.0))
    assert 3 in sol.rejected_refs and sol.n_refs == 11
    test_ra, test_dec = 150.01, 19.99
    tx, ty = prod.sky_to_pixel(test_ra, test_dec)
    ra2, dec2, C = sol.to_sky(tx, ty)
    assert abs(ra2 - test_ra) * 3600e3 < 200 and abs(dec2 - test_dec) * 3600e3 < 200  # < 0.2" (~0.03 px)
    with pytest.raises(AstrometryError):
        solve_plate(ra[:3], dec[:3], xy[:3, 0], xy[:3, 1], np.full(3, 0.01), (150.0, 20.0))


def test_motion_fit_and_catalogue_comparison():
    rng = np.random.default_rng(2)
    t = np.array([2025.4, 2025.9, 2026.4, 2026.9])
    pm = (-800.0, 10360.0)
    xi = pm[0] * (t - 2026) + rng.normal(0, 30, 4)
    eta = pm[1] * (t - 2026) + rng.normal(0, 30, 4)
    fit = fit_linear_motion(t, xi, eta, np.full(4, 30.0), np.full(4, 30.0))
    assert fit.n_epochs == 4 and fit.baseline_yr == pytest.approx(1.5)
    c = compare_to_catalogue(fit, *pm)
    assert c["consistent_within_3sigma"]
    bad = compare_to_catalogue(fit, pm[0], pm[1] + 1000)
    assert not bad["consistent_within_3sigma"] and bad["z_pmdec"] < -3


def _hpm_scenario(blend: bool):
    """SYNTHETIC: a fast-moving star among Gaia-like reference stars over four epochs."""
    star = Astrometry(200.0, 10.0, 2016.0, pmra=-800.0, pmdec=10360.0)
    rng = np.random.default_rng(3)
    path = [propagate(star, 2025.3 + 0.1 * k) for k in range(20)]
    refs = []
    for dx, dy in rng.uniform(-0.05, 0.05, (40, 2)):
        r = Astrometry(200.0 + dx, 10.0 + dy, 2016.0, pmra=float(rng.normal(0, 5)), pmdec=float(rng.normal(0, 5)))
        near = min(math.hypot((r.ra - a) * math.cos(math.radians(10)), r.dec - d) for a, d in path) * 3600 / 6.2
        if near > 6:  # keep the target's path clear (blending is tested separately)
            refs.append(r)
    if blend:  # put a reference star right on the target's path at the third epoch
        ra3, dec3 = propagate(star, float(mjd_to_jyear(61170.0)))
        refs.append(Astrometry(ra3 + 0.6 / 3600, dec3, 2016.0))
    tangent = propagate(star, 2026.0)
    ms = []
    for k, mjd in enumerate([60800.0, 60990.0, 61170.0, 61350.0]):
        ep = float(mjd_to_jyear(mjd))
        tra, tdec = propagate(star, ep)
        # pointing differs per epoch by up to ~1 pixel; the plate solution must absorb it
        prod = SyntheticProduct(shape=(70, 70), crval=(tra + rng.normal(0, 0.0015), tdec + rng.normal(0, 0.0015)),
                                crpix=(34.5, 34.5), rotation_deg=float(rng.normal(0, 0.3)),
                                wl0_um=1.30 + 0.06 * (k % 2), seed=k)
        prod.add_star(tra, tdec, 30.0)
        refs_ep = []
        for i, r in enumerate(refs):
            ra_r, dec_r = propagate(r, ep)
            prod.add_star(ra_r, dec_r, 20.0)
            refs_ep.append({"ra": ra_r, "dec": dec_r, "source_id": i})
        prod.finalize()
        ms.append(measure_exposure(prod, f"obs{k}", 2, mjd, (tra, tdec), tangent, refs_ep))
    return star, ms


def test_end_to_end_synthetic_high_pm_star():
    """The injected proper motion is recovered within its own error bars; matched pairs follow WLMATCH-1."""
    star, ms = _hpm_scenario(blend=False)
    assert all(m.quality == "ok" and m.target_xi_eta_mas is not None for m in ms), [m.notes for m in ms]
    t = [float(mjd_to_jyear(m.mjd)) for m in ms]
    fit = fit_linear_motion(t, [m.target_xi_eta_mas[0] for m in ms], [m.target_xi_eta_mas[1] for m in ms],
                            [math.sqrt(m.target_cov_mas2[0]) for m in ms], [math.sqrt(m.target_cov_mas2[1]) for m in ms])
    cmp = compare_to_catalogue(fit, star.pmra, star.pmdec)
    assert cmp["consistent_within_3sigma"], (fit, cmp)
    assert fit.sig_eta < 500  # the 10"/yr motion is detected at > 20 sigma in this synthetic setup
    samples = [SourceSample(m.obs_id, m.detector, m.mjd, m.wavelength_um, m.bandwidth_um, m.quality) for m in ms]
    acc = [(d.a, d.b) for d in match_pairs(samples) if d.accepted]
    assert sorted(acc) == [("obs0", "obs2"), ("obs1", "obs3")]


def test_blended_target_is_flagged_not_measured():
    _, ms = _hpm_scenario(blend=True)
    m = ms[2]
    assert m.quality.startswith("blended") and m.target_xi_eta_mas is None
    assert any("target blended" in n for n in m.notes)
    # the target moves only ~0.8 px between epochs, so every epoch lies within 3 px of the
    # injected star: all must be flagged and none may contribute a position
    assert all(x.quality.startswith("blended") and x.target_xi_eta_mas is None for x in ms)
