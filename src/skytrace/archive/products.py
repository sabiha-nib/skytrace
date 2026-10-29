"""Read and inspect SPHEREx Level-2 Spectral Image products (full MEFs or IRSA cutouts).

Documented structure (IRSA SPHEREx data-products page): extensions IMAGE
(MJy/sr, zodi not subtracted), FLAGS, VARIANCE ((MJy/sr)^2), ZODI, PSF
(121 zone PSFs, 10x oversampled), WCS-WAVE (coordinate array for the
spectral WCS with alternate key "W").

Reader choice: astropy when installed ("astropy"), otherwise the NumPy-only
implementation in skytrace.fitsio / skytrace.wcs ("native"). The reader used
is recorded in every inspection report. Structural mismatches raise
ProductError instead of being worked around.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import fitsio
from ..wcs import CelestialWCS, TabWCS, WCSError

REQUIRED_EXT = ("IMAGE", "FLAGS", "VARIANCE")
OPTIONAL_EXT = ("ZODI", "PSF", "WCS-WAVE")
TIME_KEYS = ("MJD-OBS", "MJD-BEG", "MJD-AVG", "MJD-END", "DATE-OBS", "DATE-BEG", "DATE-AVG",
             "DATE-END", "TSTART", "TSTOP", "TMID", "DATE")
_UNIT_TO_UM = {"um": 1.0, "micron": 1.0, "microns": 1.0, "µm": 1.0, "m": 1e6, "nm": 1e-3, "angstrom": 1e-4, "": 1.0}


class ProductError(ValueError):
    pass


def astropy_available() -> bool:
    try:
        import astropy  # noqa: F401
        return True
    except ImportError:
        return False


@dataclass
class Product:
    image: np.ndarray
    flags: np.ndarray
    variance: np.ndarray
    zodi: np.ndarray | None
    headers: dict[str, dict]
    reader: str
    _raw: object = field(repr=False, default=None)      # astropy HDUList or list[fitsio.HDU]
    _cel: object = field(repr=False, default=None)
    _spec: object = field(repr=False, default=None)

    # ------------------------------------------------------------ celestial
    def _celestial(self):
        if self._cel is None:
            if self.reader == "astropy":
                from astropy.wcs import WCS
                self._cel = WCS(self._raw["IMAGE"].header).celestial
            else:
                try:
                    self._cel = CelestialWCS(self.headers["IMAGE"])
                except (WCSError, KeyError) as e:
                    raise ProductError(f"celestial WCS unreadable: {e}") from e
        return self._cel

    def sky_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        """0-based (x, y), including SIP distortion when present."""
        w = self._celestial()
        if self.reader == "astropy":
            x, y = w.all_world2pix([[ra, dec]], 0)[0]
        else:
            x, y = w.world_to_pixel(ra, dec)
        return float(x), float(y)

    def pixel_to_sky(self, x: float, y: float) -> tuple[float, float]:
        w = self._celestial()
        if self.reader == "astropy":
            ra, dec = w.all_pix2world([[x, y]], 0)[0]
        else:
            ra, dec = w.pixel_to_world(x, y)
        return float(ra), float(dec)

    def pixel_scale_arcsec(self) -> tuple[float, float]:
        w = self._celestial()
        if self.reader == "astropy":
            from astropy.wcs.utils import proj_plane_pixel_scales
            sx, sy = proj_plane_pixel_scales(w) * 3600.0
            return float(sx), float(sy)
        return w.pixel_scale_arcsec()

    # ------------------------------------------------------------ spectral
    def wavelength_at(self, x: float, y: float) -> tuple[float, float]:
        """(central wavelength, bandwidth) in micrometres at 0-based pixel (x, y).

        Evaluates the alternate spectral WCS (key "W") backed by WCS-WAVE, as in
        IRSA's tutorial. IRSA describes this as ~1 nm accurate and intended for
        visualisation; the separate Spectral WCS product (CWAVE/CBAND) is the
        science-grade reference.
        """
        if "WCS-WAVE" not in self.headers:
            raise ProductError("product has no WCS-WAVE extension; wavelength unknown")
        if self.reader == "astropy":
            from astropy.wcs import WCS
            sw = WCS(header=self._raw["IMAGE"].header, fobj=self._raw, key="W")
            sw.sip = None
            wl, bw = sw.pixel_to_world(x, y)
            return float(wl.to_value("um")), float(bw.to_value("um"))
        if self._spec is None:
            tables = {h.name: h.data for h in self._raw if h.kind == "table"}
            try:
                self._spec = TabWCS(self.headers["IMAGE"], tables, "W")
            except WCSError as e:
                raise ProductError(f"spectral WCS unreadable: {e}") from e
        wl, bw = self._spec.pixel_to_world(x, y)
        f = [_UNIT_TO_UM.get(a["cunit"].lower(), None) for a in self._spec.axes]
        if None in f:
            raise ProductError(f"unknown spectral units {[a['cunit'] for a in self._spec.axes]}")
        return wl * f[0], bw * f[1]

    def is_synthetic(self) -> bool:
        return any(bool(h.get("SYNTHETIC")) for h in self.headers.values())


def load_product(source: bytes | str | Path, prefer: str = "auto") -> Product:
    use_astropy = prefer == "astropy" or (prefer == "auto" and astropy_available())
    if use_astropy:
        from astropy.io import fits
        hdul = fits.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source, memmap=False)
        names = [h.name.upper() for h in hdul]
        get = lambda n: hdul[n].data
        headers = {h.name.upper(): dict(h.header) for h in hdul}
        raw, reader = hdul, "astropy"
    else:
        try:
            hdus = fitsio.read(source)
        except fitsio.FITSError as e:
            raise ProductError(str(e)) from e
        names = [h.name for h in hdus]
        by = {h.name: h for h in hdus}
        get = lambda n: by[n].data
        headers = {h.name: dict(h.header) for h in hdus}
        raw, reader = hdus, "native"
    missing = [e for e in REQUIRED_EXT if e not in names]
    if missing:
        raise ProductError(f"missing required extensions {missing}; found {names}")
    image = np.asarray(get("IMAGE"), dtype=float)
    flags = np.asarray(get("FLAGS"))
    var = np.asarray(get("VARIANCE"), dtype=float)
    if not (image.shape == flags.shape == var.shape) or image.ndim != 2:
        raise ProductError(f"IMAGE/FLAGS/VARIANCE shapes differ or are not 2-D: {image.shape} {flags.shape} {var.shape}")
    zodi = np.asarray(get("ZODI"), dtype=float) if "ZODI" in names else None
    return Product(image, flags, var, zodi, headers, reader, raw)


def inspect_product(p: Product) -> dict:
    """Record what the file actually contains. Logged for every release/detector before measuring."""
    img_h = p.headers["IMAGE"]
    report = {
        "reader": p.reader,
        "extensions": list(p.headers),
        "missing_optional": [e for e in OPTIONAL_EXT if e not in p.headers],
        "image_shape": list(p.image.shape),
        "image_bunit": img_h.get("BUNIT"),
        "variance_bunit": p.headers["VARIANCE"].get("BUNIT"),
        "flags_dtype": str(p.flags.dtype),
        "image_nan_fraction": float(np.mean(~np.isfinite(p.image))),
        "ctype": [img_h.get("CTYPE1"), img_h.get("CTYPE2")],
        "spectral_ctype": [img_h.get("CTYPE1W"), img_h.get("CTYPE2W")],
        "time_keywords": {k: img_h.get(k) for k in TIME_KEYS if k in img_h},
        "flag_bit_keywords": {k: v for k, v in p.headers["FLAGS"].items() if str(k).upper().startswith(("MP_", "BIT", "FLAG"))},
        "detector_keywords": {k: img_h.get(k) for k in ("DETECTOR", "DETNAME", "BAND", "FILTER") if k in img_h},
        "synthetic": p.is_synthetic(),
    }
    try:
        report["pixel_scale_arcsec"] = list(p.pixel_scale_arcsec())
    except Exception as e:  # recorded, not hidden
        report["pixel_scale_error"] = str(e)
    try:
        cy, cx = (s / 2 for s in p.image.shape)
        report["wavelength_at_center_um"] = list(p.wavelength_at(cx, cy))
    except Exception as e:
        report["wavelength_error"] = str(e)
    warnings = []
    if report["image_bunit"] and str(report["image_bunit"]).replace(" ", "").lower() != "mjy/sr":
        warnings.append(f"IMAGE BUNIT is {report['image_bunit']!r}, expected MJy/sr")
    if p.reader == "native":
        warnings.append("read with the native FITS/WCS implementation (astropy not installed)")
    report["warnings"] = warnings
    return report
