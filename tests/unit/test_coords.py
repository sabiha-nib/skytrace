import math

import numpy as np
import pytest

from skytrace.science.coords import (Astrometry, CoordinateError, angular_separation_deg, gnomonic,
                                     inverse_gnomonic, jyear_to_mjd, mjd_to_jyear, parallax_offset_mas,
                                     parse_dec, parse_ra, propagate)


def test_wise0855_supplied_coordinates():
    # RA 08h55m10.831s, Dec -7°14'42.53" (as supplied in the brief)
    assert parse_ra("08h55m10.831s") == pytest.approx((8 + 55 / 60 + 10.831 / 3600) * 15, abs=1e-12)
    assert parse_dec("−7°14′42.53″") == pytest.approx(-(7 + 14 / 60 + 42.53 / 3600), abs=1e-12)


@pytest.mark.parametrize("text", ["08:55:10.831", "08 55 10.831", "8h55m10.831s"])
def test_ra_formats_agree(text):
    assert parse_ra(text) == pytest.approx(133.7951291666, abs=1e-9)


def test_decimal_and_degree_marked_ra():
    assert parse_ra("133.5") == 133.5
    assert parse_ra("133d30m00s") == pytest.approx(133.5)


def test_negative_zero_degree_declination():
    assert parse_dec("-00:30:00") == pytest.approx(-0.5)


@pytest.mark.parametrize("bad", ["360", "-1", "25h00m00s", "12h61m00s", "-01:00:00", "abc"])
def test_bad_ra(bad):
    with pytest.raises(CoordinateError):
        parse_ra(bad)


@pytest.mark.parametrize("bad", ["91", "-90.5", "+10:60:00", "north"])
def test_bad_dec(bad):
    with pytest.raises(CoordinateError):
        parse_dec(bad)


def test_separation_known_values():
    assert angular_separation_deg(0, 0, 90, 0) == pytest.approx(90)
    assert angular_separation_deg(10, 89.9, 190, 89.9) == pytest.approx(0.2, abs=1e-9)
    assert angular_separation_deg(0, 0, 180, 0) == pytest.approx(180)
    assert angular_separation_deg(5, 5, 5, 5 + 1 / 3600) * 3600 == pytest.approx(1.0, rel=1e-9)


def test_gnomonic_roundtrip():
    ra, dec = np.array([180.01, 179.98, 180.0]), np.array([0.02, -0.03, 0.0])
    xi, eta = gnomonic(ra, dec, 180.0, 0.0)
    r2, d2 = inverse_gnomonic(xi, eta, 180.0, 0.0)
    assert np.allclose(r2, ra, atol=1e-10) and np.allclose(d2, dec, atol=1e-10)
    assert xi[0] > 0 and eta[0] > 0  # east and north are positive


def test_epochs():
    assert mjd_to_jyear(51544.5) == pytest.approx(2000.0)
    assert jyear_to_mjd(mjd_to_jyear(60500.25)) == pytest.approx(60500.25)


def test_propagation_zero_motion_is_identity():
    a = Astrometry(123.4, -45.6, 2016.0)
    assert propagate(a, 2026.0) == pytest.approx((123.4, -45.6))


def test_propagation_matches_linear_approx_for_high_pm():
    # Barnard-like motion (values for testing; not a reference)
    a = Astrometry(269.45, 4.74, 2016.0, pmra=-801.5, pmdec=10362.4, parallax=547.0)
    ra, dec = propagate(a, 2026.0)
    ddec = (dec - a.dec) * 3600e3
    dra = (ra - a.ra) * math.cos(math.radians(a.dec)) * 3600e3
    assert ddec == pytest.approx(10 * 10362.4, rel=1e-4)
    assert dra == pytest.approx(10 * -801.5, rel=2e-3)


def test_propagated_offset_equals_total_motion():
    a = Astrometry(10.0, 60.0, 2016.0, pmra=4000, pmdec=-2500)
    ra, dec = propagate(a, 2026.0)
    assert angular_separation_deg(ra, dec, a.ra, a.dec) * 3600 == pytest.approx(math.hypot(4000, 2500) * 10 / 1000, rel=1e-3)


def test_parallax_offset_direction():
    # Star at RA=90, Dec=0; observer displaced +1 AU along x: apparent shift is in +RA
    dra, ddec = parallax_offset_mas(90.0, 0.0, 100.0, (1.0, 0.0, 0.0))
    assert dra == pytest.approx(100.0) and ddec == pytest.approx(0.0, abs=1e-9)


def test_cross_check_with_astropy():
    pytest.importorskip("astropy")
    from astropy import units as u
    from astropy.coordinates import Angle, SkyCoord
    from astropy.time import Time
    assert parse_ra("08h55m10.831s") == pytest.approx(Angle("08h55m10.831s").deg, abs=1e-12)
    c = SkyCoord(269.45 * u.deg, 4.74 * u.deg, pm_ra_cosdec=-801.5 * u.mas / u.yr, pm_dec=10362.4 * u.mas / u.yr,
                 distance=(547 * u.mas).to(u.pc, u.parallax()), radial_velocity=-110 * u.km / u.s,
                 obstime=Time(2016.0, format="jyear"))
    c2 = c.apply_space_motion(new_obstime=Time(2026.0, format="jyear"))
    ra, dec = propagate(Astrometry(269.45, 4.74, 2016.0, -801.5, 10362.4, 547, -110), 2026.0)
    assert angular_separation_deg(ra, dec, c2.ra.deg, c2.dec.deg) * 3600e3 < 1.0  # < 1 mas
