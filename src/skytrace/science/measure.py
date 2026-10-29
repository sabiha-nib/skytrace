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
    quality_code: str = "ok"        # photometric usability, one of QUALITY_CODES
    astro_code: str = "ok"          # astrometric usability, one of ASTRO_CODES
    ref_photometry: tuple = ()      # reference-star aperture fluxes in this exposure (for CALCHECK)


# Machine-readable status codes (never parse the free-text 'quality' field to decide anything).
QUALITY_CODES = {"ok", "target_outside", "no_wavelength", "photometry_flagged", "photometry_no_sky",
                 "photometry_off_image", "blended", "nonlinear_flag"}
ASTRO_CODES = {"ok", "target_outside", "centroid_failed", "below_snr", "blended", "no_references", "plate_failed"}


def measure_exposure(prod: ProductLike, obs_id: str, detector: int, mjd: float,
                     target_radec: tuple[float, float], tangent: tuple[float, float],
                     refs: list[dict] | None = None, aperture_px: float = 2.0,
                     fit_half_size: int = 4, isolation_px: float = 3.0, max_ref_rchi2: float = 3.0,
                     centroid_floor_px: float = 0.02, target_window_px: float = 1.5,
                     min_target_snr: float = 5.0, neighbour_mask_px: float = 2.5) -> ExposureMeasurement:
    """refs: catalogue stars already placed at this epoch: dicts with 'ra', 'dec', 'source_id' and optionally
    'use_as_reference' (False = masked as a neighbour but never used in the plate solution).

    Reference selection REFSEL-1: inside the cutout, no other catalogue source within
    isolation_px, PSF fit converged with reduced chi2 <= max_ref_rchi2, and within 2 px
    of the catalogue position. A systematic floor (centroid_floor_px) is added in
    quadrature to each reference centroid error, because the Gaussian PSF model is an
    approximation. The target centroid error is also floored the same way.

    Neighbour masking NBMASK-1: before any centroid fit, pixels within neighbour_mask_px of
    every other catalogue source near the star are excluded from the fit.

    Target astrometry TGT-1: the target centroid is confined to +/- target_window_px of
    its catalogue-predicted position (so deviations from the catalogue motion up to that
    size remain measurable) and the exposure is used for astrometry only if the target's
    aperture S/N >= min_target_snr.
    """
    notes: list[str] = []
    fmap = fl.resolve_bits(prod.headers.get("FLAGS"))
    if fmap.origin != "header":
        notes.append("flag bits from documentation only; undocumented flags not applied: " + ", ".join(fmap.unresolved))
    bad = fmap.mask(prod.flags, fl.REJECT)

    x0, y0 = prod.sky_to_pixel(*target_radec)
    ny, nx = prod.image.shape
    if not (0 <= x0 < nx and 0 <= y0 < ny):
        return ExposureMeasurement(obs_id, detector, mjd, (x0, y0), None, None, None, None, {},
                                   "target outside cutout", notes=tuple(notes),
                                   quality_code="target_outside", astro_code="target_outside")
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
    yy_all, xx_all = np.indices(prod.image.shape)
    cat_all = [prod.sky_to_pixel(r["ra"], r["dec"]) for r in (refs or [])]

    def neighbour_mask(px: float, py: float, exclude: int | None = None, include_target: bool = False) -> np.ndarray:
        """NBMASK-1: mask pixels within neighbour_mask_px of other catalogue sources near (px, py)."""
        m = bad.copy()
        srcs = [(qx, qy) for j, (qx, qy) in enumerate(cat_all) if j != exclude]
        if include_target:
            srcs.append((x0, y0))
        for qx, qy in srcs:
            if np.hypot(qx - px, qy - py) <= fit_half_size * 1.5 + neighbour_mask_px:
                m |= np.hypot(xx_all - qx, yy_all - qy) < neighbour_mask_px
        return m

    near = sorted((float(np.hypot(qx - x0, qy - y0)), (refs or [])[j].get("source_id"))
                  for j, (qx, qy) in enumerate(cat_all))
    blend = next(((d, sid) for d, sid in near if d < isolation_px), None)
    c = cen.fit_centroid(prod.image, prod.variance, x0, y0, half_size=fit_half_size, bad=neighbour_mask(x0, y0),
                         max_shift_px=target_window_px)
    target_detected = phot.status == "ok" and phot.snr >= min_target_snr
    if not c.converged:
        notes.append(f"target centroid not usable: {c.message}")
    elif not target_detected:
        notes.append(f"target below S/N {min_target_snr:g} in this exposure; not used for astrometry")
    if blend is not None:
        notes.append(f"target blended: catalogue source {blend[1]} is {blend[0]:.2f} px away (< {isolation_px:g} px); "
                     "not used for astrometry or photometry")
        target_detected = False

    quality, qcode = "ok", "ok"
    if wl is None:
        quality, qcode = "no wavelength", "no_wavelength"
    elif phot.status != "ok":
        quality, qcode = f"photometry {phot.status}: {phot.detail}", f"photometry_{phot.status.replace('-', '_')}"
    elif blend is not None:
        quality, qcode = f"blended: catalogue source within {blend[0]:.2f} px", "blended"
    elif "MP_NONLINEAR" in fsum.warn_names:
        quality, qcode = "photometry warn: non-linear pixels in the aperture (excluded from variability)", "nonlinear_flag"
    acode = ("blended" if blend is not None else "centroid_failed" if not c.converged else
             "below_snr" if not target_detected else "ok")

    plate_d, xi_eta, cov3 = None, None, None
    ref_phot: list[dict] = []
    if not refs and acode == "ok":
        acode = "no_references"
    if refs:  # the plate is solved whenever references exist; the target position needs a usable target
        rx, ry, rs, rra, rdec, rid = [], [], [], [], [], []
        ref_rejects: dict[str, int] = {}
        cat_xy = cat_all
        for i, r in enumerate(refs):
            px, py = cat_xy[i]
            if not (fit_half_size <= px < nx - fit_half_size and fit_half_size <= py < ny - fit_half_size):
                continue
            if r.get("use_as_reference") is False:  # catalogue quality cut (REFSEL-2): still masked as a neighbour
                continue
            # REFSEL-1 isolation: no other catalogue source (or the target) within isolation_px
            others = [np.hypot(px - qx, py - qy) for j, (qx, qy) in enumerate(cat_xy) if j != i]
            if np.hypot(px - x0, py - y0) < max(isolation_px, 2 * fit_half_size) or (others and min(others) < isolation_px):
                ref_rejects["not isolated"] = ref_rejects.get("not isolated", 0) + 1
                continue
            rc = cen.fit_centroid(prod.image, prod.variance, px, py, half_size=fit_half_size,
                                  bad=neighbour_mask(px, py, exclude=i, include_target=True), max_shift_px=2.0)
            if not rc.converged:
                ref_rejects["fit failed"] = ref_rejects.get("fit failed", 0) + 1
                continue
            if rc.reduced_chi2 > max_ref_rchi2:
                ref_rejects["poor PSF fit"] = ref_rejects.get("poor PSF fit", 0) + 1
                continue
            if np.hypot(rc.x - px, rc.y - py) >= 2.0:
                ref_rejects["far from catalogue position"] = ref_rejects.get("far from catalogue position", 0) + 1
                continue
            rx.append(rc.x); ry.append(rc.y)
            rs.append(float(np.hypot(max(rc.sigma_x, rc.sigma_y), centroid_floor_px)))
            rra.append(r["ra"]); rdec.append(r["dec"]); rid.append(r.get("source_id"))
            # CALCHECK input: aperture photometry of isolated reference stars (no catalogue source within the sky annulus)
            crowd = min([np.hypot(rc.x - qx, rc.y - qy) for j, (qx, qy) in enumerate(cat_xy) if j != i] + [np.hypot(rc.x - x0, rc.y - y0)])
            if crowd > 7.5:
                rp = ph.aperture_photometry(prod.image, prod.variance, rc.x, rc.y,
                                            ph.pixel_solid_angle_from_scale(sx, sy), r_ap=aperture_px, bad=bad)
                try:
                    rwl, rbw = prod.wavelength_at(rc.x, rc.y)
                except Exception:
                    rwl = rbw = None
                ref_phot.append({"source_id": r.get("source_id"), "flux_ujy": rp.flux_ujy, "flux_err_ujy": rp.flux_err_ujy,
                                 "status": rp.status, "wavelength_um": rwl, "bandwidth_um": rbw})
        try:
            sol: PlateSolution = solve_plate(rra, rdec, rx, ry, rs, tangent)
            if c.converged and target_detected:
                cov_xy = np.array([[c.sigma_x ** 2 + centroid_floor_px ** 2, c.cov_xy],
                                   [c.cov_xy, c.sigma_y ** 2 + centroid_floor_px ** 2]])
                xi, eta, C = sol.apply(c.x, c.y, cov_xy)
                k = 3600e3
                xi_eta = (float(xi * k), float(eta * k))
                cov3 = (float(C[0, 0] * k * k), float(C[1, 1] * k * k), float(C[0, 1] * k * k))
            rej = set(sol.rejected_refs)
            plate_d = {"n_refs": sol.n_refs, "n_candidates": len(rx), "rms_mas": sol.rms_mas,
                       "ref_rejections": ref_rejects, "selection": "REFSEL-1",
                       "rejected_refs": [rid[i] for i in sol.rejected_refs], "method": sol.method,
                       "coeffs_deg": [float(v) for v in sol.coeffs], "tangent": list(tangent),
                       "refs_xy": [{"source_id": rid[i], "x": rx[i], "y": ry[i], "used": i not in rej}
                                   for i in range(len(rx))]}
        except AstrometryError as e:
            notes.append(f"plate solution failed: {e}")
            if acode == "ok":
                acode = "plate_failed"
            plate_d = {"n_refs": 0, "n_candidates": len(rx), "failed": str(e), "ref_rejections": ref_rejects,
                       "refs_xy": [{"source_id": rid[i], "x": rx[i], "y": ry[i], "used": False} for i in range(len(rx))]}

    return ExposureMeasurement(obs_id, detector, mjd, (float(x0), float(y0)), wl, bw, asdict(c),
                               {**asdict(phot), "snr": phot.snr, "ab_mag": phot.ab_mag},
                               asdict(fsum), quality, plate_d, xi_eta, cov3, tuple(notes), qcode, acode, tuple(ref_phot))


def predicted_xi_eta_mas(ra: float, dec: float, tangent: tuple[float, float]) -> tuple[float, float]:
    xi, eta = gnomonic(ra, dec, *tangent)
    return float(xi * 3600e3), float(eta * 3600e3)
