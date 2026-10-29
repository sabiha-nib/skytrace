"""Earth ephemeris and parallax, checked against independently published 2026 events.

References (fetched 2026-10-29):
  LINZ 'Astronomical phenomena, July 2025 - June 2026' (NZST = UTC+12): perihelion 2026 Jan 4 05:16 NZST,
    March equinox 2026 Mar 21 02:46 NZST.
  thesuntoday.org 'Aphelion 2026': 2026 July 6 17:30 UTC, 152,087,775 km; perihelion distance 91,403,637 miles.
"""

import math

import pytest

from skytrace.science.coords import Astrometry, apparent_position, parallax_offset_at, propagate
from skytrace.science.ephemeris import observer_barycentric_au, sun_geocentric

AU_KM = 149597870.7


def mjd(y, m, d, hh=0, mm=0):
    from datetime import datetime, timezone
    t = datetime(y, m, d, hh, mm, tzinfo=timezone.utc)
    return (t - datetime(1858, 11, 17, tzinfo=timezone.utc)).total_seconds() / 86400


def test_perihelion_and_aphelion_distances():
    r_peri = math.dist((0, 0, 0), sun_geocentric(mjd(2026, 1, 3, 17, 16))[:3])
    r_aph = math.dist((0, 0, 0), sun_geocentric(mjd(2026, 7, 6, 17, 30))[:3])
    assert r_peri == pytest.approx(91403637 * 1.609344 / AU_KM, abs=2e-4)
    assert r_aph == pytest.approx(152087775 / AU_KM, abs=2e-4)


def test_march_equinox_longitude():
    lam = sun_geocentric(mjd(2026, 3, 20, 14, 46))[3]
    assert min(lam, 360 - lam) < 0.02          # 0.01 deg stated accuracy + aberration/nutation conventions


def test_observer_is_opposite_the_sun_and_one_au():
    for d in (0, 91, 182, 273):
        o = observer_barycentric_au(mjd(2026, 1, 1) + d)
        assert 0.98 < math.hypot(*o) < 1.02


def test_parallax_ellipse_amplitude_and_phase():
    # star at the ecliptic pole: the parallax path is a circle of radius p
    pole = Astrometry(270.0, 66.560708, 2016.0, parallax=500.0)
    r = [math.hypot(*parallax_offset_at(pole, mjd(2026, 1, 1) + d)) for d in range(0, 365, 30)]
    assert min(r) > 480 and max(r) < 520
    # star on the ecliptic at RA 0: displacement mostly along RA, zero at conjunction (Sun at RA ~ 0, March equinox)
    ecl = Astrometry(0.0, 0.0, 2016.0, parallax=500.0)
    dra, _ = parallax_offset_at(ecl, mjd(2026, 3, 20, 14, 46))
    assert abs(dra) < 15
    # at quadrature (June solstice) the full displacement p*R lies along the ecliptic, which at RA 0
    # is inclined by the obliquity: |d| = p*R, split as cos/sin(23.44 deg) between RA and Dec
    dra_sep, ddec_sep = parallax_offset_at(ecl, mjd(2026, 6, 21))
    assert math.hypot(dra_sep, ddec_sep) == pytest.approx(500 * 1.016, rel=0.005)
    assert math.degrees(math.atan2(abs(ddec_sep), abs(dra_sep))) == pytest.approx(23.44, abs=0.1)


def test_apparent_position_adds_parallax_to_space_motion():
    a = Astrometry(269.45, 4.74, 2016.0, pmra=-801.5, pmdec=10362.4, parallax=547.0)
    t = mjd(2026, 6, 1)
    ra, dec = apparent_position(a, t)
    ra0, dec0 = propagate(a, 2016.0 + (t - 57388.5) / 365.25)
    d = math.hypot((ra - ra0) * math.cos(math.radians(dec)), dec - dec0) * 3600e3
    assert 0 < d <= 547.0 * 1.02
