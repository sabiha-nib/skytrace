"""Observer position for parallax (EPHEM-AA-LP-1).

SPHEREx is in a ~700 km Earth orbit, so its barycentric position is Earth's to within
~5e-6 AU; for a star at 2 pc that changes the parallax displacement by < 1e-5 mas.

Earth's position is taken as minus the geocentric Sun from the Astronomical Almanac's
low-precision solar coordinates (stated accuracy 0.01 deg in longitude, 1950-2050).
Error budget for the parallax displacement of a star with parallax p:
  * longitude error 0.01 deg    -> 1.7e-4 AU -> 1.7e-4 p   (0.09 mas for p = 547 mas)
  * heliocentric vs barycentric -> <= 0.01 AU (Sun's reflex motion, mainly Jupiter)
                                -> <= 0.01 p               (<= 5.5 mas for p = 547 mas)
Both are far below SPHEREx single-exposure astrometric errors (hundreds of mas), and the
0.01 p term is recorded with every result as a systematic bound.

Validated in tests against the 2026 perihelion/aphelion distances and March-equinox time.
"""

from __future__ import annotations

import math

import numpy as np

METHOD = "EPHEM-AA-LP-1"
SYSTEMATIC_FRACTION_OF_PARALLAX = 0.01


def sun_geocentric(mjd: float) -> tuple[float, float, float, float]:
    """Return (X, Y, Z) of the Sun in AU (ICRS-aligned equatorial, mean equinox of date) and its ecliptic longitude (deg)."""
    n = (mjd + 2400000.5) - 2451545.0
    L = math.radians((280.460 + 0.9856474 * n) % 360.0)
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    R = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    x = R * math.cos(lam)
    y = R * math.cos(eps) * math.sin(lam)
    z = R * math.sin(eps) * math.sin(lam)
    return x, y, z, math.degrees(lam) % 360.0


def observer_barycentric_au(mjd: float) -> np.ndarray:
    """Earth (= SPHEREx) position relative to the Sun, used as the barycentric observer position (AU)."""
    x, y, z, _ = sun_geocentric(mjd)
    return np.array([-x, -y, -z])
