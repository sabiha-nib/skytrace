"""Aperture photometry on SPHEREx surface-brightness images.

Method APPHOT-1:
  * IMAGE is calibrated surface brightness in MJy/sr with zodiacal light NOT
    subtracted; a local sky annulus removes zodi and other smooth background.
  * Flux density = sum over aperture of (I - sky) * pixel solid angle.
  * Circular aperture with 10x10 sub-pixel sampling for partial pixels.
  * Sky = sigma-clipped median of unflagged annulus pixels.
  * Variance = sum(w^2 * VARIANCE) + (sum w)^2 * sky_variance_of_mean.
  * If any pixel rejected by the flag policy has non-zero aperture weight, the
    flux is returned as NaN with status "flagged" rather than silently
    measuring around the damage.

The result is an aperture flux, not a total flux: no aperture correction is
applied. Values from different detectors or wavelengths are not directly
comparable without one; within a wavelength-matched pair the same aperture
makes the correction cancel to first order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

METHOD = "APPHOT-1"
MJY_SR_TO_UJY_PER_SR = 1e12  # 1 MJy = 1e12 uJy


@dataclass(frozen=True)
class Photometry:
    flux_ujy: float
    flux_err_ujy: float
    sky_mjy_sr: float
    aperture_radius_px: float
    annulus_px: tuple[float, float]
    n_sky: int
    status: str            # "ok", "flagged", "no-sky", "off-image"
    detail: str = ""
    method: str = METHOD

    @property
    def snr(self) -> float:
        return self.flux_ujy / self.flux_err_ujy if self.flux_err_ujy > 0 else float("nan")

    @property
    def ab_mag(self) -> float:
        return -2.5 * math.log10(self.flux_ujy * 1e-6 / 3631.0) if self.flux_ujy > 0 else float("nan")


def aperture_weights(shape, x0: float, y0: float, r: float, oversample: int = 10) -> np.ndarray:
    ny, nx = shape
    offs = (np.arange(oversample) + 0.5) / oversample - 0.5
    sx, sy = np.meshgrid(offs, offs)
    yy, xx = np.indices(shape)
    w = np.zeros(shape)
    near = np.hypot(xx - x0, yy - y0) <= r + 1.0
    for j, i in zip(*np.nonzero(near)):
        w[j, i] = np.mean(np.hypot(i + sx - x0, j + sy - y0) <= r)
    return w


def _clipped_median(v: np.ndarray, nsig: float = 3.0, iters: int = 5) -> tuple[float, float, int]:
    v = v[np.isfinite(v)]
    for _ in range(iters):
        if v.size < 5:
            break
        med = np.median(v)
        mad = 1.4826 * np.median(np.abs(v - med))
        keep = np.abs(v - med) <= nsig * max(mad, 1e-30)
        if keep.all():
            break
        v = v[keep]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    std = float(np.std(v, ddof=1)) if v.size > 1 else float("nan")
    return float(np.median(v)), std, int(v.size)


def aperture_photometry(image, variance, x0, y0, pixel_solid_angle_sr: float,
                        r_ap: float = 2.0, r_in: float = 4.0, r_out: float = 7.0,
                        bad: np.ndarray | None = None, min_sky: int = 20) -> Photometry:
    ann = (r_in, r_out)
    ny, nx = image.shape
    if not (r_ap <= x0 < nx - r_ap and r_ap <= y0 < ny - r_ap):
        return Photometry(np.nan, np.nan, np.nan, r_ap, ann, 0, "off-image", "aperture leaves the cutout")
    bad = np.zeros(image.shape, bool) if bad is None else bad
    invalid = bad | ~np.isfinite(image) | ~np.isfinite(variance)
    w = aperture_weights(image.shape, x0, y0, r_ap)
    hit = invalid & (w > 0)
    yy, xx = np.indices(image.shape)
    rr = np.hypot(xx - x0, yy - y0)
    sky_px = (rr >= r_in) & (rr <= r_out) & ~invalid
    sky, sky_std, n_sky = _clipped_median(image[sky_px])
    if n_sky < min_sky:
        return Photometry(np.nan, np.nan, sky, r_ap, ann, n_sky, "no-sky", f"{n_sky} usable sky pixels < {min_sky}")
    if hit.any():
        return Photometry(np.nan, np.nan, sky, r_ap, ann, n_sky, "flagged",
                          f"{int(hit.sum())} rejected/invalid pixels inside the aperture")
    sw = w.sum()
    flux_mjysr_px = float(np.sum(w * (image - sky)))
    var = float(np.sum(w ** 2 * variance)) + sw ** 2 * (math.pi / 2) * sky_std ** 2 / n_sky
    k = pixel_solid_angle_sr * MJY_SR_TO_UJY_PER_SR
    return Photometry(flux_mjysr_px * k, math.sqrt(var) * k, sky, r_ap, ann, n_sky, "ok")


def pixel_solid_angle_from_scale(arcsec_per_px_x: float, arcsec_per_px_y: float | None = None) -> float:
    ay = arcsec_per_px_x if arcsec_per_px_y is None else arcsec_per_px_y
    return (arcsec_per_px_x / 206264.80624709636) * (ay / 206264.80624709636)
