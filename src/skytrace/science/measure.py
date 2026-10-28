"""Per-exposure measurement of a target and its reference stars.

Works on any object implementing the ProductLike protocol (archive.products.Product
for real files; a synthetic stand-in in tests). This keeps every measurement step
testable without network access or FITS files.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

import numpy as np

from . import centroid as cen
from . import flags as fl
from . import photometry as ph
from .astrometry import AstrometryError, PlateSolution, solve_plate
from .coords import gnomonic


class ProductLike(Protocol):
    image: np.ndarray
    flags: np.ndarray
    variance: np.ndarray
    headers: dict

    def sky_to_pixel(self, ra: float, dec: float) -> tuple[float, float]: ...
    def pixel_scale_arcsec(self) -> tuple[float, float]: ...
    def wavelength_at(self, x: float, y: float) -> tuple[float, float]: ...


@dataclass(frozen=True)
class ExposureMeasurement:
    obs_id: str
    detector: int
    mjd: float
    predicted_xy: tuple[float, float]
    wavelength_um: float | None
    bandwidth_um: float | None
    centroid: dict | None
    photometry: dict | None
    flag_summary: dict
    quality: str                    # "ok" or a reason
    plate: dict | None = None       # plate-solution summary
    target_xi_eta_mas: tuple[float, float] | None = None   # relative to the fixed tangent point
    target_cov_mas2: tuple[float, float, float] | None = None  # (var_xi, var_eta, cov)
    notes: tuple[str, ...] = ()


def measure_exposure(prod: ProductLike, obs_id: str, detector: int, mjd: float,
                     target_radec: tuple[float, float], tangent: tuple[float, float],
                     refs: list[dict] | None = None, aperture_px: float = 2.0,
                     fit_half_size: int = 4) -> ExposureMeasurement:
    """refs: reference stars already propagated to this epoch: dicts with 'ra', 'dec', 'source_id'."""
    notes: list[str] = []
    fmap = fl.resolve_bits(prod.headers.get("FLAGS"))
    if fmap.origin != "header":
        notes.append("flag bits from documentation only; undocumented flags not applied: " + ", ".join(fmap.unresolved))
    bad = fmap.mask(prod.flags, fl.REJECT)

    x0, y0 = prod.sky_to_pixel(*target_radec)
    ny, nx = prod.image.shape
    if not (0 <= x0 < nx and 0 <= y0 < ny):
        return ExposureMeasurement(obs_id, detector, mjd, (x0, y0), None, None, None, None, {},
                                   "target outside cutout", notes=tuple(notes))
    try:
        wl, bw = prod.wavelength_at(x0, y0)
    except Exception as e:
        wl, bw = None, None
        notes.append(f"wavelength unavailable: {e}")

    yy, xx = np.indices(prod.image.shape)
    core = np.hypot(xx - x0, yy - y0) <= aperture_px + 0.5
    fsum = fl.summarize(prod.flags, core, fmap)

    sx, sy = prod.pixel_scale_arcsec()
    phot = ph.aperture_photometry(prod.image, prod.variance, x0, y0,
                                  ph.pixel_solid_angle_from_scale(sx, sy), r_ap=aperture_px, bad=bad)
    c = cen.fit_centroid(prod.image, prod.variance, x0, y0, half_size=fit_half_size, bad=bad)

    quality = "ok"
    if wl is None:
        quality = "no wavelength"
    elif phot.status != "ok":
        quality = f"photometry {phot.status}: {phot.detail}"

    plate_d, xi_eta, cov3 = None, None, None
    if refs and c.converged:
        rx, ry, rs, rra, rdec = [], [], [], [], []
        for r in refs:
            px, py = prod.sky_to_pixel(r["ra"], r["dec"])
            if not (fit_half_size <= px < nx - fit_half_size and fit_half_size <= py < ny - fit_half_size):
                continue
            rc = cen.fit_centroid(prod.image, prod.variance, px, py, half_size=fit_half_size, bad=bad)
            if rc.converged and np.hypot(rc.x - px, rc.y - py) < 2.0:
                rx.append(rc.x); ry.append(rc.y); rs.append(max(rc.sigma_x, rc.sigma_y))
                rra.append(r["ra"]); rdec.append(r["dec"])
        try:
            sol: PlateSolution = solve_plate(rra, rdec, rx, ry, rs, tangent)
            cov_xy = np.array([[c.sigma_x ** 2, c.cov_xy], [c.cov_xy, c.sigma_y ** 2]])
            xi, eta, C = sol.apply(c.x, c.y, cov_xy)
            k = 3600e3
            xi_eta = (float(xi * k), float(eta * k))
            cov3 = (float(C[0, 0] * k * k), float(C[1, 1] * k * k), float(C[0, 1] * k * k))
            plate_d = {"n_refs": sol.n_refs, "rms_mas": sol.rms_mas, "rejected_refs": list(sol.rejected_refs),
                       "method": sol.method}
        except AstrometryError as e:
            notes.append(f"plate solution failed: {e}")

    return ExposureMeasurement(obs_id, detector, mjd, (float(x0), float(y0)), wl, bw, asdict(c),
                               {**asdict(phot), "snr": phot.snr, "ab_mag": phot.ab_mag},
                               asdict(fsum), quality, plate_d, xi_eta, cov3, tuple(notes))


def predicted_xi_eta_mas(ra: float, dec: float, tangent: tuple[float, float]) -> tuple[float, float]:
    xi, eta = gnomonic(ra, dec, *tangent)
    return float(xi * 3600e3), float(eta * 3600e3)
