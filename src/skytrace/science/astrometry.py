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

import math
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
                min_refs: int = 6, clip_sigma: float = 4.0, max_iter: int = 10) -> PlateSolution:
    """Weighted affine fit with leave-one-out outlier rejection (PLATE-LOO-1).

    ref_sig_px: per-star centroid sigma in pixels (isotropic approximation).
    At each iteration the star with the largest normalised residual is refitted
    out of the solution; it is rejected if its residual against the solution
    that excludes it exceeds clip_sigma times its combined uncertainty (scaled
    by that solution's reduced chi-square when > 1). Leave-one-out testing
    prevents a single bad star from hiding itself by dragging the fit.
    min_refs = 6 gives at least 6 degrees of freedom for the 6 affine parameters.
    """
    ref_ra, ref_dec, x, y, s = map(lambda a: np.asarray(a, float), (ref_ra, ref_dec, ref_x, ref_y, ref_sig_px))
    xi, eta = gnomonic(ref_ra, ref_dec, *tangent)
    keep = np.isfinite(x) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    rejected: list[int] = []

    def fit(idx):
        A = np.column_stack([np.ones(idx.size), x[idx], y[idx]])
        scale = _provisional_scale(A, xi[idx], eta[idx])
        w = 1.0 / (s[idx] * scale)
        Aw = A * w[:, None]
        ca, *_ = np.linalg.lstsq(Aw, xi[idx] * w, rcond=None)
        cb, *_ = np.linalg.lstsq(Aw, eta[idx] * w, rcond=None)
        rx, ry = xi[idx] - A @ ca, eta[idx] - A @ cb
        chi = np.hypot(rx, ry) * w
        rchi2 = float(np.sum(chi ** 2) / max(1, 2 * idx.size - 6))
        N = np.linalg.inv(Aw.T @ Aw)
        return ca, cb, rx, ry, chi, rchi2, N, scale

    for _ in range(max_iter + 1):
        idx = np.nonzero(keep)[0]
        if idx.size < min_refs:
            raise AstrometryError(f"{idx.size} usable reference stars; need at least {min_refs}")
        ca, cb, rx, ry, chi, rchi2, N, scale = fit(idx)
        if idx.size > min_refs:
            worst = idx[int(np.argmax(chi))]
            rest = idx[idx != worst]
            ca2, cb2, _, _, _, rchi2_2, N2, scale2 = fit(rest)
            a = np.array([1.0, x[worst], y[worst]])
            pred_var = float(a @ N2 @ a)                 # deg^2: uncertainty of the leave-one-out prediction
            dx = xi[worst] - a @ ca2
            dy = eta[worst] - a @ cb2
            sig = s[worst] * scale2                      # deg: this star's centroid error
            z = float(np.hypot(dx, dy) / np.sqrt((sig ** 2 + pred_var) * max(1.0, rchi2_2)))
            if z > clip_sigma:
                keep[worst] = False
                rejected.append(int(worst))
                continue
        cov = np.zeros((6, 6))
        cov[:3, :3] = N * max(1.0, rchi2)
        cov[3:, 3:] = N * max(1.0, rchi2)
        rms = float(np.sqrt(np.mean(np.concatenate([rx, ry]) ** 2)) * DEG_TO_MAS)
        return PlateSolution(np.concatenate([ca, cb]), cov, int(idx.size), rms, tangent, tuple(rejected),
                             method="DIFFAST-1/PLATE-LOO-1")
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
    rejected: tuple[int, ...] = ()
    method: str = "LINFIT-1"


def fit_linear_motion(t_yr, xi_mas, eta_mas, sig_xi_mas, sig_eta_mas, clip_sigma: float | None = None,
                      min_epochs: int = 2) -> MotionFit:
    """Weighted linear fit of position vs time (LINFIT-1).

    With clip_sigma set, epochs are rejected one at a time by leave-one-out testing
    (LINFIT-LOO-1): the worst epoch is compared with the fit that excludes it and is
    dropped if it deviates by more than clip_sigma combined sigma. Rejected indices are
    returned in MotionFit.rejected.
    """
    t, x, e, sx, se = map(lambda a: np.asarray(a, float), (t_yr, xi_mas, eta_mas, sig_xi_mas, sig_eta_mas))
    if t.size < min_epochs:
        raise AstrometryError(f"need at least {min_epochs} epochs")
    keep = np.ones(t.size, bool)
    rejected: list[int] = []

    def wfit(idx, v, s):
        tt = t[idx]
        t0 = float(np.average(tt, weights=1 / s[idx] ** 2))
        A = np.column_stack([np.ones_like(tt), tt - t0])
        W = 1 / s[idx]
        coef, *_ = np.linalg.lstsq(A * W[:, None], v[idx] * W, rcond=None)
        cov = np.linalg.inv((A * W[:, None]).T @ (A * W[:, None]))
        chi2 = float(np.sum(((v[idx] - A @ coef) * W) ** 2))
        return coef, cov, chi2, t0

    while True:
        idx = np.nonzero(keep)[0]
        if idx.size < min_epochs or np.ptp(t[idx]) <= 0:
            raise AstrometryError(f"fewer than {min_epochs} usable epochs at distinct times after rejection")
        cx, Cx, chx, t0 = wfit(idx, x, sx)
        ce, Ce, che, _ = wfit(idx, e, se)
        dof = max(1, 2 * idx.size - 4)
        rchi2 = (chx + che) / dof
        if clip_sigma is None or idx.size <= max(min_epochs, 3):
            break
        res = np.hypot((x[idx] - cx[0] - cx[1] * (t[idx] - t0)) / sx[idx], (e[idx] - ce[0] - ce[1] * (t[idx] - t0)) / se[idx])
        worst = idx[int(np.argmax(res))]
        rest = idx[idx != worst]
        cx2, Cx2, chx2, t02 = wfit(rest, x, sx)
        ce2, Ce2, che2, _ = wfit(rest, e, se)
        r2 = max(1.0, (chx2 + che2) / max(1, 2 * rest.size - 4))
        a = np.array([1.0, t[worst] - t02])
        zx = (x[worst] - a @ cx2) / np.sqrt((sx[worst] ** 2 + a @ Cx2 @ a) * r2)
        ze = (e[worst] - a @ ce2) / np.sqrt((se[worst] ** 2 + a @ Ce2 @ a) * r2)
        if np.hypot(zx, ze) > clip_sigma:
            keep[worst] = False
            rejected.append(int(worst))
            continue
        break
    inflate = np.sqrt(max(1.0, rchi2))
    return MotionFit(float(cx[1]), float(ce[1]), float(np.sqrt(Cx[1, 1]) * inflate),
                     float(np.sqrt(Ce[1, 1]) * inflate), t0, float(np.ptp(t[idx])), int(idx.size), float(rchi2),
                     tuple(rejected), "LINFIT-LOO-1" if clip_sigma is not None else "LINFIT-1")


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


# ---------------------------------------------------------------------------- LINFIT-EPOCH-1
EPOCH_METHOD = "LINFIT-EPOCH-1"


def group_epochs(t_mjd, gap_days: float) -> list[list[int]]:
    """Group exposure indices into visits: a new epoch starts after a gap > gap_days."""
    order = sorted(range(len(t_mjd)), key=lambda i: t_mjd[i])
    groups: list[list[int]] = []
    for i in order:
        if groups and t_mjd[i] - t_mjd[groups[-1][-1]] <= gap_days:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def epoch_average(t_mjd, xi, eta, sx, se, groups: list[list[int]]) -> list[dict]:
    """Weighted mean position per epoch.

    The error of each epoch mean is max(formal error of the mean, empirical scatter / sqrt(n))
    (empirical term only for n >= 3). Exposures in one visit share the same reference stars and
    similar detector positions, so their errors are partly correlated; taking the larger of the two
    keeps the epoch error from shrinking below what the data show. This is the LINFIT-EPOCH-1 input.
    """
    out = []
    for g in groups:
        t = np.array([t_mjd[i] for i in g]); x = np.array([xi[i] for i in g]); e = np.array([eta[i] for i in g])
        wx = 1 / np.array([sx[i] for i in g]) ** 2; we = 1 / np.array([se[i] for i in g]) ** 2
        mx, me = float(np.sum(wx * x) / np.sum(wx)), float(np.sum(we * e) / np.sum(we))
        fx, fe = float(np.sum(wx) ** -0.5), float(np.sum(we) ** -0.5)
        n = len(g)
        ex = float(np.std(x, ddof=1) / math.sqrt(n)) if n >= 3 else 0.0
        ee = float(np.std(e, ddof=1) / math.sqrt(n)) if n >= 3 else 0.0
        out.append({"t_mjd": float(np.mean(t)), "n_exposures": n, "xi_mas": mx, "eta_mas": me,
                    "sig_xi_mas": max(fx, ex), "sig_eta_mas": max(fe, ee),
                    "formal_sig_mas": [fx, fe], "empirical_sig_mas": [ex, ee], "members": list(g)})
    return out
