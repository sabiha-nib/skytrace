"""Celestial coordinate parsing, geometry and space-motion propagation.

Pure NumPy so it can be tested without astropy. When astropy is installed,
tests cross-check these functions against astropy.coordinates.

Conventions: angles in degrees at the API boundary, ICRS frame, proper motion
in RA includes the cos(dec) factor (pmra = mu_alpha*), epochs in Julian years.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

MAS_PER_RAD = 180.0 / math.pi * 3600e3
KM_S_PER_AU_YR = 4.740470446  # km/s corresponding to 1 AU/yr
JD_J2000 = 2451545.0
MJD_J2000 = 51544.5


class CoordinateError(ValueError):
    pass


# ---------------------------------------------------------------- parsing
_MINUS = "−‒–—"
_SEXA = re.compile(
    r"^\s*([+-]?)\s*(\d+(?:\.\d*)?)\s*[hd°:\s]\s*(\d+(?:\.\d*)?)\s*[m'′:\s]\s*(\d+(?:\.\d*)?)\s*[s\"″]?\s*$",
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    for ch in _MINUS:
        s = s.replace(ch, "-")
    return s.replace("''", '"').strip()


def parse_ra(text: str | float) -> float:
    """RA -> degrees. Decimal input is degrees; sexagesimal input is hours unless marked with d/°."""
    if isinstance(text, (int, float)):
        val = float(text)
    else:
        s = _norm(text)
        try:
            val = float(s.rstrip("d°"))
        except ValueError:
            m = _SEXA.match(s)
            if not m or m.group(1):
                raise CoordinateError(f"cannot parse right ascension {text!r}")
            a, b, c = (float(m.group(i)) for i in (2, 3, 4))
            if b >= 60 or c >= 60:
                raise CoordinateError(f"minutes/seconds must be < 60 in {text!r}")
            in_degrees = bool(re.search(r"[d°]", s, re.IGNORECASE))
            val = (a + b / 60 + c / 3600) * (1.0 if in_degrees else 15.0)
    if not (0.0 <= val < 360.0):
        raise CoordinateError(f"right ascension {val} deg outside [0, 360)")
    return val


def parse_dec(text: str | float) -> float:
    """Dec -> degrees, from decimal degrees or sexagesimal d m s."""
    if isinstance(text, (int, float)):
        val = float(text)
    else:
        s = _norm(text)
        try:
            val = float(s.rstrip("d°"))
        except ValueError:
            m = _SEXA.match(s)
            if not m:
                raise CoordinateError(f"cannot parse declination {text!r}")
            sign = -1.0 if m.group(1) == "-" else 1.0
            a, b, c = (float(m.group(i)) for i in (2, 3, 4))
            if b >= 60 or c >= 60:
                raise CoordinateError(f"minutes/seconds must be < 60 in {text!r}")
            val = sign * (a + b / 60 + c / 3600)
    if not (-90.0 <= val <= 90.0):
        raise CoordinateError(f"declination {val} deg outside [-90, 90]")
    return val


# ---------------------------------------------------------------- geometry
def angular_separation_deg(ra1, dec1, ra2, dec2):
    """Vincenty great-circle separation (numerically stable at all angles)."""
    r1, d1, r2, d2 = map(np.radians, (ra1, dec1, ra2, dec2))
    dra = r2 - r1
    num = np.hypot(np.cos(d2) * np.sin(dra),
                   np.cos(d1) * np.sin(d2) - np.sin(d1) * np.cos(d2) * np.cos(dra))
    den = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(dra)
    return np.degrees(np.arctan2(num, den))


def gnomonic(ra, dec, ra0, dec0):
    """Project sky positions onto the tangent plane at (ra0, dec0). Returns (xi, eta) in degrees.

    xi increases to the east, eta to the north.
    """
    a, d, a0, d0 = map(np.radians, (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    if np.any(cosc <= 0):
        raise CoordinateError("point is 90 deg or more from the tangent point")
    xi = np.cos(d) * np.sin(a - a0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / cosc
    return np.degrees(xi), np.degrees(eta)


def inverse_gnomonic(xi, eta, ra0, dec0):
    x, y, a0, d0 = np.radians(xi), np.radians(eta), np.radians(ra0), np.radians(dec0)
    rho = np.hypot(x, y)
    c = np.arctan(rho)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec = np.where(rho == 0, d0, np.arcsin(np.cos(c) * np.sin(d0) + y * np.sin(c) * np.cos(d0) / np.where(rho == 0, 1, rho)))
    ra = a0 + np.arctan2(x * np.sin(c), rho * np.cos(d0) * np.cos(c) - y * np.sin(d0) * np.sin(c))
    return np.degrees(ra) % 360.0, np.degrees(dec)


# ---------------------------------------------------------------- time
def mjd_to_jyear(mjd):
    return 2000.0 + (np.asarray(mjd, dtype=float) - MJD_J2000) / 365.25


def jyear_to_mjd(jyear):
    return MJD_J2000 + (np.asarray(jyear, dtype=float) - 2000.0) * 365.25


# ---------------------------------------------------------------- space motion
@dataclass(frozen=True)
class Astrometry:
    """Catalogue astrometry at a reference epoch (e.g. Gaia DR3, ref_epoch 2016.0)."""
    ra: float            # deg
    dec: float           # deg
    ref_epoch: float     # Julian year
    pmra: float = 0.0    # mas/yr, includes cos(dec)
    pmdec: float = 0.0   # mas/yr
    parallax: float = 0.0          # mas
    radial_velocity: float = 0.0   # km/s; 0 means "unknown": perspective acceleration ignored
    source: str = ""


def propagate(ast: Astrometry, epoch: float) -> tuple[float, float]:
    """Rigorous linear space motion (ESA 1997, Hipparcos Vol. 1, Sect. 1.5.5).

    Returns barycentric ICRS (ra, dec) in degrees at the requested Julian-year
    epoch. Parallax displacement (Earth/spacecraft position) is NOT applied; see
    `parallax_offset_mas` for that term.
    """
    t = epoch - ast.ref_epoch
    a, d = math.radians(ast.ra), math.radians(ast.dec)
    r0 = np.array([math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)])
    p = np.array([-math.sin(a), math.cos(a), 0.0])
    q = np.array([-math.sin(d) * math.cos(a), -math.sin(d) * math.sin(a), math.cos(d)])
    mu0 = (p * ast.pmra + q * ast.pmdec) / MAS_PER_RAD                    # rad/yr
    mur = ast.radial_velocity * ast.parallax / KM_S_PER_AU_YR / MAS_PER_RAD  # rad/yr
    f = (1 + 2 * mur * t + (mu0 @ mu0 + mur ** 2) * t ** 2) ** -0.5
    r = (r0 * (1 + mur * t) + mu0 * t) * f
    ra = math.degrees(math.atan2(r[1], r[0])) % 360.0
    dec = math.degrees(math.asin(max(-1.0, min(1.0, r[2] / np.linalg.norm(r)))))
    return ra, dec


def parallax_offset_mas(ra: float, dec: float, parallax_mas: float, observer_xyz_au) -> tuple[float, float]:
    """Apparent offset (d_ra*cos(dec), d_dec) in mas caused by parallax.

    observer_xyz_au: barycentric ICRS position of the observer in AU (for SPHEREx
    in low-Earth orbit this is effectively Earth's position). Must come from an
    ephemeris; this module does not compute it.
    """
    a, d = math.radians(ra), math.radians(dec)
    x, y, z = observer_xyz_au
    dra = parallax_mas * (x * math.sin(a) - y * math.cos(a))
    ddec = parallax_mas * (x * math.cos(a) * math.sin(d) + y * math.sin(a) * math.sin(d) - z * math.cos(d))
    return dra, ddec


def apparent_position(ast: Astrometry, mjd: float) -> tuple[float, float]:
    """Catalogue astrometry -> position seen from Earth/SPHEREx at mjd: space motion + annual parallax.

    Aberration and light deflection are common to the whole 0.1 deg field and cancel in
    differential astrometry, so they are not applied.
    """
    from .ephemeris import observer_barycentric_au
    ra, dec = propagate(ast, float(mjd_to_jyear(mjd)))
    if not ast.parallax:
        return ra, dec
    dra, ddec = parallax_offset_mas(ra, dec, ast.parallax, observer_barycentric_au(mjd))
    return ra + dra / 3600e3 / math.cos(math.radians(dec)), dec + ddec / 3600e3


def parallax_offset_at(ast: Astrometry, mjd: float) -> tuple[float, float]:
    """Parallax displacement (d_ra*cos(dec), d_dec) in mas at mjd."""
    from .ephemeris import observer_barycentric_au
    ra, dec = propagate(ast, float(mjd_to_jyear(mjd)))
    return parallax_offset_mas(ra, dec, ast.parallax, observer_barycentric_au(mjd)) if ast.parallax else (0.0, 0.0)
