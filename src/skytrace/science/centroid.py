"""Point-source centroiding with uncertainties.

Method CENTROID-G2D-1: weighted least-squares fit of an elliptical 2-D Gaussian
plus constant background to a small stamp, using the VARIANCE extension as
weights and excluding pixels rejected by the flag policy. Uncertainties come
from the Jacobian covariance scaled by the reduced chi-square when it exceeds
1 (so an imperfect PSF model inflates, never shrinks, the errors).

SPHEREx pixels are 6.2" and the PSF is undersampled in some bands, so a
Gaussian is an approximation. Bias is quantified with synthetic injections in
the test suite; a PSF-model fit using the file's PSF extension is the planned
alternative method for comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

METHOD = "CENTROID-G2D-1"


@dataclass(frozen=True)
class Centroid:
    x: float
    y: float
    sigma_x: float
    sigma_y: float
    cov_xy: float
    amplitude: float
    background: float
    fwhm_x: float
    fwhm_y: float
    reduced_chi2: float
    n_used: int
    n_masked: int
    converged: bool
    method: str = METHOD
    message: str = ""


def _model(p, xx, yy):
    amp, x0, y0, sx, sy, bg = p
    return amp * np.exp(-0.5 * (((xx - x0) / sx) ** 2 + ((yy - y0) / sy) ** 2)) + bg


def fit_centroid(image: np.ndarray, variance: np.ndarray, x0: float, y0: float,
                 half_size: int = 4, bad: np.ndarray | None = None,
                 min_good_pixels: int = 12, max_shift_px: float | None = None) -> Centroid:
    """Fit near (x0, y0) (0-based pixel coordinates, x = column).

    max_shift_px confines the fitted position to a box of that half-width around
    (x0, y0); a solution on that boundary is reported as not converged (the fit
    was being pulled toward something else, e.g. a brighter neighbour).
    """
    ny, nx = image.shape
    xc, yc = int(round(x0)), int(round(y0))
    x_lo, x_hi = max(0, xc - half_size), min(nx, xc + half_size + 1)
    y_lo, y_hi = max(0, yc - half_size), min(ny, yc + half_size + 1)
    stamp = image[y_lo:y_hi, x_lo:x_hi].astype(float)
    var = variance[y_lo:y_hi, x_lo:x_hi].astype(float)
    good = np.isfinite(stamp) & np.isfinite(var) & (var > 0)
    if bad is not None:
        good &= ~bad[y_lo:y_hi, x_lo:x_hi]
    n_masked = int(good.size - good.sum())
    yy, xx = np.mgrid[y_lo:y_hi, x_lo:x_hi]
    fail = lambda msg: Centroid(np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
                                np.nan, np.nan, np.nan, int(good.sum()), n_masked, False, message=msg)
    if good.sum() < min_good_pixels:
        return fail(f"only {int(good.sum())} usable pixels (need {min_good_pixels})")
    if (x_hi - x_lo, y_hi - y_lo) != (2 * half_size + 1, 2 * half_size + 1):
        return fail("fit stamp truncated by the cutout edge (PSF wings missing would bias the centroid)")

    d, w = stamp[good], 1.0 / np.sqrt(var[good])
    X, Y = xx[good], yy[good]
    bg0 = float(np.median(d))
    amp0 = float(np.max(d) - bg0)
    if amp0 <= 0:
        return fail("no positive peak above the local median")
    p0 = [amp0, float(x0), float(y0), 1.0, 1.0, bg0]
    lo = [0, x_lo - 0.5, y_lo - 0.5, 0.3, 0.3, -np.inf]
    hi = [np.inf, x_hi - 0.5, y_hi - 0.5, 3.0 * half_size, 3.0 * half_size, np.inf]
    if max_shift_px is not None:
        lo[1], hi[1] = max(lo[1], x0 - max_shift_px), min(hi[1], x0 + max_shift_px)
        lo[2], hi[2] = max(lo[2], y0 - max_shift_px), min(hi[2], y0 + max_shift_px)
    res = least_squares(lambda p: (_model(p, X, Y) - d) * w, p0, bounds=(lo, hi), x_scale="jac")
    dof = max(1, d.size - 6)
    rchi2 = float(np.sum(res.fun ** 2) / dof)
    try:
        cov = np.linalg.inv(res.jac.T @ res.jac) * max(1.0, rchi2)
    except np.linalg.LinAlgError:
        return fail("singular covariance")
    amp, xf, yf, sx, sy, bg = res.x
    at_bound = bool(np.any(np.abs(res.x[1:3] - np.array([lo[1], lo[2]])) < 1e-3) or
                    np.any(np.abs(res.x[1:3] - np.array([hi[1], hi[2]])) < 1e-3))
    ok = bool(res.success) and not at_bound and np.all(np.isfinite(np.diag(cov)))
    return Centroid(float(xf), float(yf), float(np.sqrt(cov[1, 1])), float(np.sqrt(cov[2, 2])),
                    float(cov[1, 2]), float(amp), float(bg), float(2.3548 * sx), float(2.3548 * sy),
                    rchi2, int(d.size), n_masked, ok,
                    message="" if ok else ("fit hit stamp boundary" if at_bound else res.message))


def first_moment(image: np.ndarray, x0: float, y0: float, radius: float = 2.5,
                 background: float = 0.0, bad: np.ndarray | None = None) -> tuple[float, float]:
    """Simple intensity-weighted centroid; used as a cross-check (method MOMENT-1)."""
    yy, xx = np.indices(image.shape)
    r = np.hypot(xx - x0, yy - y0) <= radius
    if bad is not None:
        r &= ~bad
    w = np.clip(image - background, 0, None) * r
    w = np.where(np.isfinite(w), w, 0.0)
    s = w.sum()
    if s <= 0:
        return float("nan"), float("nan")
    return float((w * xx).sum() / s), float((w * yy).sum() / s)
