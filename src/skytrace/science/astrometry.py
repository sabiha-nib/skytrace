"""Differential astrometry against Gaia reference stars.

Method DIFFAST-1, per exposure:
  1. Propagate Gaia DR3 reference stars to the exposure epoch (coords.propagate).
  2. Project them onto a tangent plane at a fixed tangent point.
  3. Fit a weighted 6-parameter affine map pixel (x, y) -> tangent plane (xi, eta)
     using reference-star centroids measured in the same exposure.
  4. Map the target's measured centroid through that solution, propagating both
     the centroid covariance and the plate-solution parameter covariance.

Because the solution is re-derived from field stars in every exposure, pointing
error and header-WCS error cancel; what remains is centroid noise, reference
catalogue error, and the residual (non-affine) distortion over the cutout,
which is reported as the post-fit residual RMS.

Then, across exposures:
  5. Fit position vs time with weighted linear least squares to obtain the
     apparent proper motion and its uncertainty, and compare it with the
     catalogue value (difference in units of the combined sigma).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coords import gnomonic, inverse_gnomonic

METHOD = "DIFFAST-1"
DEG_TO_MAS = 3600e3


@dataclass(frozen=True)
class PlateSolution:
    coeffs: np.ndarray        # [a0, a1, a2, b0, b1, b2] in degrees, xi = a0 + a1 x + a2 y
    cov: np.ndarray           # 6x6 covariance (deg^2)
    n_refs: int
    rms_mas: float            # post-fit residual RMS per axis
    tangent: tuple[float, float]
    rejected_refs: tuple[int, ...] = ()
    method: str = METHOD

    def apply(self, x: float, y: float, cov_xy: np.ndarray | None = None):
        """Return (xi, eta) in deg and their 2x2 covariance in deg^2."""
        a0, a1, a2, b0, b1, b2 = self.coeffs
        xi, eta = a0 + a1 * x + a2 * y, b0 + b1 * x + b2 * y
        Jp = np.zeros((2, 6))
        Jp[0, :3] = [1, x, y]
        Jp[1, 3:] = [1, x, y]
        C = Jp @ self.cov @ Jp.T
        if cov_xy is not None:
            Jx = np.array([[a1, a2], [b1, b2]])
            C = C + Jx @ cov_xy @ Jx.T
        return xi, eta, C

    def to_sky(self, x: float, y: float, cov_xy: np.ndarray | None = None):
        xi, eta, C = self.apply(x, y, cov_xy)
        ra, dec = inverse_gnomonic(xi, eta, *self.tangent)
        return float(ra), float(dec), C


class AstrometryError(RuntimeError):
    pass


def solve_plate(ref_ra, ref_dec, ref_x, ref_y, ref_sig_px, tangent: tuple[float, float],
                min_refs: int = 4, clip_sigma: float = 4.0, max_iter: int = 3) -> PlateSolution:
    """Weighted affine fit with iterative outlier rejection.

    ref_sig_px: per-star centroid sigma in pixels (isotropic approximation).
    """
    ref_ra, ref_dec, x, y, s = map(lambda a: np.asarray(a, float), (ref_ra, ref_dec, ref_x, ref_y, ref_sig_px))
    xi, eta = gnomonic(ref_ra, ref_dec, *tangent)
    keep = np.isfinite(x) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    rejected: list[int] = []
    for _ in range(max_iter + 1):
        idx = np.nonzero(keep)[0]
        if idx.size < min_refs:
            raise AstrometryError(f"{idx.size} usable reference stars; need at least {min_refs}")
        A = np.column_stack([np.ones(idx.size), x[idx], y[idx]])
        # weights: centroid sigma converted to degrees using a provisional scale
        scale = _provisional_scale(A, xi[idx], eta[idx])
        w = 1.0 / (s[idx] * scale)
        Aw = A * w[:, None]
        ca, *_ = np.linalg.lstsq(Aw, xi[idx] * w, rcond=None)
        cb, *_ = np.linalg.lstsq(Aw, eta[idx] * w, rcond=None)
        rx, ry = xi[idx] - A @ ca, eta[idx] - A @ cb
        chi = np.hypot(rx, ry) * w
        dof = max(1, 2 * idx.size - 6)
        rchi2 = float(np.sum(chi ** 2) / dof)
        worst = int(np.argmax(chi))
        robust = max(1.0, 1.4826 * float(np.median(chi)))  # robust: one outlier cannot inflate its own threshold
        if chi[worst] > clip_sigma * robust and idx.size > min_refs:
            keep[idx[worst]] = False
            rejected.append(int(idx[worst]))
            continue
        N = np.linalg.inv(Aw.T @ Aw) * max(1.0, rchi2)
        cov = np.zeros((6, 6))
        cov[:3, :3] = N
        cov[3:, 3:] = N
        rms = float(np.sqrt(np.mean(np.concatenate([rx, ry]) ** 2)) * DEG_TO_MAS)
        return PlateSolution(np.concatenate([ca, cb]), cov, int(idx.size), rms, tangent, tuple(rejected))
    raise AstrometryError("outlier rejection did not converge")


def _provisional_scale(A, xi, eta) -> float:
    ca, *_ = np.linalg.lstsq(A, xi, rcond=None)
    cb, *_ = np.linalg.lstsq(A, eta, rcond=None)
    return float(np.sqrt(abs(ca[1] * cb[2] - ca[2] * cb[1])))  # deg per pixel


@dataclass(frozen=True)
class MotionFit:
    pm_xi_mas_yr: float       # ~ pmra (cos dec included) near the tangent point
    pm_eta_mas_yr: float      # ~ pmdec
    sig_xi: float
    sig_eta: float
    t_ref: float              # Julian year of the zero point
    baseline_yr: float
    n_epochs: int
    reduced_chi2: float
    method: str = "LINFIT-1"


def fit_linear_motion(t_yr, xi_mas, eta_mas, sig_xi_mas, sig_eta_mas) -> MotionFit:
    t, x, e, sx, se = map(lambda a: np.asarray(a, float), (t_yr, xi_mas, eta_mas, sig_xi_mas, sig_eta_mas))
    if t.size < 2:
        raise AstrometryError("need at least two epochs")
    t0 = float(np.average(t, weights=1 / sx ** 2))

    def wfit(v, s):
        A = np.column_stack([np.ones_like(t), t - t0])
        W = 1 / s
        coef, *_ = np.linalg.lstsq(A * W[:, None], v * W, rcond=None)
        cov = np.linalg.inv((A * W[:, None]).T @ (A * W[:, None]))
        chi2 = float(np.sum(((v - A @ coef) * W) ** 2))
        return coef, cov, chi2

    cx, Cx, chx = wfit(x, sx)
    ce, Ce, che = wfit(e, se)
    dof = max(1, 2 * t.size - 4)
    rchi2 = (chx + che) / dof
    inflate = np.sqrt(max(1.0, rchi2))
    return MotionFit(float(cx[1]), float(ce[1]), float(np.sqrt(Cx[1, 1]) * inflate),
                     float(np.sqrt(Ce[1, 1]) * inflate), t0, float(t.max() - t.min()), int(t.size), float(rchi2))


def compare_to_catalogue(fit: MotionFit, pmra: float, pmdec: float,
                         pmra_err: float = 0.0, pmdec_err: float = 0.0) -> dict:
    """Difference measured - catalogue, and its significance per axis (not a probability)."""
    dx, de = fit.pm_xi_mas_yr - pmra, fit.pm_eta_mas_yr - pmdec
    sx, se = np.hypot(fit.sig_xi, pmra_err), np.hypot(fit.sig_eta, pmdec_err)
    return {
        "delta_pmra_mas_yr": float(dx), "delta_pmdec_mas_yr": float(de),
        "sigma_pmra_mas_yr": float(sx), "sigma_pmdec_mas_yr": float(se),
        "z_pmra": float(dx / sx) if sx > 0 else float("nan"),
        "z_pmdec": float(de / se) if se > 0 else float("nan"),
        "consistent_within_3sigma": bool(abs(dx) <= 3 * sx and abs(de) <= 3 * se),
        "note": "Significance of the difference from the catalogue value; not a probability "
                "that the measurement is correct. Tangent-plane axes approximate (pmra*, pmdec) "
                "near the tangent point.",
    }
