"""Read and inspect SPHEREx Level-2 Spectral Image products (full MEFs or IRSA cutouts).

Documented structure (IRSA SPHEREx data-products page): extensions IMAGE
(MJy/sr, zodi not subtracted), FLAGS, VARIANCE ((MJy/sr)^2), ZODI, PSF
(121 zone PSFs, 10x oversampled), WCS-WAVE (lookup table for the
spectral WCS with alternate key "W").

This module requires astropy. It has NOT yet been run against a real file in
this repository's history (see docs/DATA_FEASIBILITY_REPORT.md); the first
live run must execute `inspect_product` and record its output before any
measurement is trusted. Expected-structure mismatches raise ProductError
instead of being worked around.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REQUIRED_EXT = ("IMAGE", "FLAGS", "VARIANCE")
OPTIONAL_EXT = ("ZODI", "PSF", "WCS-WAVE")
TIME_KEYS = ("MJD-OBS", "MJD-BEG", "MJD-AVG", "MJD-END", "DATE-OBS", "DATE-BEG", "DATE-AVG",
             "DATE-END", "TSTART", "TSTOP", "TMID", "DATE")


class ProductError(ValueError):
    pass


def _astropy():
    try:
        from astropy.io import fits
        from astropy.wcs import WCS
        from astropy.wcs.utils import proj_plane_pixel_scales
    except ImportError as e:  # pragma: no cover - environment dependent
        raise ProductError("astropy is required to read SPHEREx FITS products (pip install astropy)") from e
    return fits, WCS, proj_plane_pixel_scales


@dataclass
class Product:
    image: np.ndarray
    flags: np.ndarray
    variance: np.ndarray
    zodi: np.ndarray | None
    headers: dict[str, dict]
    _hdul: object = field(repr=False)

    def celestial_wcs(self):
        _, WCS, _ = _astropy()
        return WCS(self._hdul["IMAGE"].header).celestial

    def sky_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        """0-based (x, y) pixel position, including SIP distortion if present."""
        x, y = self.celestial_wcs().all_world2pix([[ra, dec]], 0)[0]
        return float(x), float(y)

    def pixel_scale_arcsec(self) -> tuple[float, float]:
        _, _, scales = _astropy()
        sx, sy = scales(self.celestial_wcs()) * 3600.0
        return float(sx), float(sy)

    def wavelength_at(self, x: float, y: float) -> tuple[float, float]:
        """(central wavelength, bandwidth) in micrometres at 0-based pixel (x, y).

        Uses the alternate spectral WCS (key "W") backed by the WCS-WAVE table,
        exactly as in IRSA's tutorial. IRSA describes this as ~1 nm accurate and
        intended for visualisation; the separate Spectral WCS product
        (CWAVE/CBAND) is the science-grade reference and should be compared
        against this on real data before relying on sub-nm differences.
        """
        _, WCS, _ = _astropy()
        if "WCS-WAVE" not in self.headers:
            raise ProductError("product has no WCS-WAVE extension; wavelength unknown")
        sw = WCS(header=self._hdul["IMAGE"].header, fobj=self._hdul, key="W")
        sw.sip = None
        wl, bw = sw.pixel_to_world(x, y)
        return float(wl.to_value("um")), float(bw.to_value("um"))


def load_product(source: bytes | str | Path) -> Product:
    fits, _, _ = _astropy()
    hdul = fits.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source, memmap=False)
    names = [h.name.upper() for h in hdul]
    missing = [e for e in REQUIRED_EXT if e not in names]
    if missing:
        raise ProductError(f"missing required extensions {missing}; found {names}")
    image = np.asarray(hdul["IMAGE"].data, dtype=float)
    flags = np.asarray(hdul["FLAGS"].data)
    var = np.asarray(hdul["VARIANCE"].data, dtype=float)
    if not (image.shape == flags.shape == var.shape):
        raise ProductError(f"IMAGE/FLAGS/VARIANCE shapes differ: {image.shape} {flags.shape} {var.shape}")
    zodi = np.asarray(hdul["ZODI"].data, dtype=float) if "ZODI" in names else None
    headers = {h.name.upper(): dict(h.header) for h in hdul}
    return Product(image, flags, var, zodi, headers, hdul)


def inspect_product(p: Product) -> dict:
    """Record what the file actually contains. Run on every new product type before measuring."""
    img_h = p.headers["IMAGE"]
    report = {
        "extensions": list(p.headers),
        "missing_optional": [e for e in OPTIONAL_EXT if e not in p.headers],
        "image_shape": list(p.image.shape),
        "image_bunit": img_h.get("BUNIT"),
        "variance_bunit": p.headers["VARIANCE"].get("BUNIT"),
        "flags_dtype": str(p.flags.dtype),
        "image_nan_fraction": float(np.mean(~np.isfinite(p.image))),
        "ctype": [img_h.get("CTYPE1"), img_h.get("CTYPE2")],
        "has_spectral_wcs_W": any(str(k).endswith("W") and str(k).startswith("CTYPE") for k in img_h),
        "time_keywords": {k: img_h.get(k) for k in TIME_KEYS if k in img_h},
        "flag_bit_keywords": {k: v for k, v in p.headers["FLAGS"].items() if str(k).upper().startswith("MP_")},
        "detector_keywords": {k: img_h.get(k) for k in ("DETECTOR", "DETNAME", "BAND", "FILTER") if k in img_h},
    }
    try:
        report["pixel_scale_arcsec"] = list(p.pixel_scale_arcsec())
    except Exception as e:  # recorded, not hidden
        report["pixel_scale_error"] = str(e)
    if report["image_bunit"] and str(report["image_bunit"]).replace(" ", "").lower() not in ("mjy/sr",):
        report["warning"] = f"IMAGE BUNIT is {report['image_bunit']!r}, expected MJy/sr"
    return report
