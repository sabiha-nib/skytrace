"""Native WCS evaluation (NumPy only) for SPHEREx Level-2 headers.

Celestial: TAN projection (Calabretta & Greisen 2002) with optional SIP
distortion (Shupe et al. 2005). Supports CD or PC+CDELT. Pixel coordinates at
this API are 0-based (FITS pixel = ours + 1), matching astropy's origin=0.

Spectral: the -TAB algorithm (Greisen et al. 2006, FITS WCS Paper III, sect. 6)
for an alternate WCS (key "W" in SPHEREx files) whose coordinate array lives in
a BINTABLE (the WCS-WAVE extension). This is what astropy/wcslib evaluate in
IRSA's tutorial `WCS(header, fobj=hdul, key="W")`; SIP is deliberately not
applied to it, as in that tutorial.

archive.products uses astropy when installed and this module otherwise; the
two are compared in tests whenever astropy is present.
"""

from __future__ import annotations

import math

import numpy as np

from .science.coords import gnomonic, inverse_gnomonic


class WCSError(ValueError):
    pass


def _sip(h: dict, prefix: str) -> tuple[int, dict[tuple[int, int], float]]:
    order = int(h.get(f"{prefix}_ORDER", 0))
    coeffs = {}
    for p in range(order + 1):
        for q in range(order + 1 - p):
            v = h.get(f"{prefix}_{p}_{q}")
            if v is not None:
                coeffs[(p, q)] = float(v)
    return order, coeffs


def _poly(coeffs: dict, u, v):
    out = np.zeros_like(np.asarray(u, float))
    for (p, q), c in coeffs.items():
        out = out + c * np.power(u, p) * np.power(v, q)
    return out


class CelestialWCS:
    def __init__(self, h: dict, key: str = ""):
        k = key.strip()
        c1, c2 = str(h.get(f"CTYPE1{k}", "")), str(h.get(f"CTYPE2{k}", ""))
        if not (c1.startswith("RA--") and c2.startswith("DEC-")):
            raise WCSError(f"unsupported celestial axes {c1!r}, {c2!r}")
        proj = c1[5:8]
        if proj != "TAN" or c2[5:8] != "TAN":
            raise WCSError(f"only TAN projection supported, got {c1!r}")
        self.has_sip = c1.endswith("-SIP")
        self.crpix = np.array([float(h[f"CRPIX1{k}"]), float(h[f"CRPIX2{k}"])])
        self.crval = (float(h[f"CRVAL1{k}"]), float(h[f"CRVAL2{k}"]))
        if f"CD1_1{k}" in h:
            self.cd = np.array([[float(h.get(f"CD1_1{k}", 0)), float(h.get(f"CD1_2{k}", 0))],
                                [float(h.get(f"CD2_1{k}", 0)), float(h.get(f"CD2_2{k}", 0))]])
        else:
            pc = np.array([[float(h.get(f"PC1_1{k}", 1)), float(h.get(f"PC1_2{k}", 0))],
                           [float(h.get(f"PC2_1{k}", 0)), float(h.get(f"PC2_2{k}", 1))]])
            cdelt = np.array([float(h.get(f"CDELT1{k}", 1)), float(h.get(f"CDELT2{k}", 1))])
            self.cd = cdelt[:, None] * pc
        self.cd_inv = np.linalg.inv(self.cd)
        if str(h.get(f"RADESYS{k}", "ICRS")).strip() not in ("ICRS", "FK5", ""):
            raise WCSError(f"unsupported RADESYS {h.get(f'RADESYS{k}')!r}")
        self.a = _sip(h, "A")[1] if self.has_sip else {}
        self.b = _sip(h, "B")[1] if self.has_sip else {}
        self.ap = _sip(h, "AP")[1] if self.has_sip else {}
        self.bp = _sip(h, "BP")[1] if self.has_sip else {}

    def pixel_to_world(self, x, y):
        """0-based pixel -> (ra, dec) degrees."""
        u = np.asarray(x, float) + 1 - self.crpix[0]
        v = np.asarray(y, float) + 1 - self.crpix[1]
        if self.has_sip:
            u, v = u + _poly(self.a, u, v), v + _poly(self.b, u, v)
        xi = self.cd[0, 0] * u + self.cd[0, 1] * v
        eta = self.cd[1, 0] * u + self.cd[1, 1] * v
        return inverse_gnomonic(xi, eta, *self.crval)

    def world_to_pixel(self, ra, dec):
        xi, eta = gnomonic(np.asarray(ra, float), np.asarray(dec, float), *self.crval)
        U = self.cd_inv[0, 0] * xi + self.cd_inv[0, 1] * eta
        V = self.cd_inv[1, 0] * xi + self.cd_inv[1, 1] * eta
        if self.has_sip:
            if self.ap or self.bp:
                u, v = U + _poly(self.ap, U, V), V + _poly(self.bp, U, V)
            else:
                u, v = U.copy(), V.copy()
            for _ in range(20):  # refine with Newton on the forward polynomial (exact inverse)
                fu, fv = u + _poly(self.a, u, v) - U, v + _poly(self.b, u, v) - V
                h = 1e-4
                du_u = 1 + (_poly(self.a, u + h, v) - _poly(self.a, u - h, v)) / (2 * h)
                du_v = (_poly(self.a, u, v + h) - _poly(self.a, u, v - h)) / (2 * h)
                dv_u = (_poly(self.b, u + h, v) - _poly(self.b, u - h, v)) / (2 * h)
                dv_v = 1 + (_poly(self.b, u, v + h) - _poly(self.b, u, v - h)) / (2 * h)
                det = du_u * dv_v - du_v * dv_u
                su, sv = (dv_v * fu - du_v * fv) / det, (du_u * fv - dv_u * fu) / det
                u, v = u - su, v - sv
                if np.all(np.abs(su) < 1e-9) and np.all(np.abs(sv) < 1e-9):
                    break
        else:
            u, v = U, V
        return u + self.crpix[0] - 1, v + self.crpix[1] - 1

    def pixel_scale_arcsec(self) -> tuple[float, float]:
        return (float(np.hypot(*self.cd[:, 0]) * 3600), float(np.hypot(*self.cd[:, 1]) * 3600))


class TabWCS:
    """-TAB alternate WCS with all axes sharing one coordinate array (Paper III)."""

    def __init__(self, h: dict, tables: dict[str, dict], key: str = "W"):
        k = key
        self.naxis = int(h.get(f"WCSAXES{k}", h.get("NAXIS", 2)))
        self.axes = []
        arr_name = None
        for i in range(1, self.naxis + 1):
            ctype = str(h.get(f"CTYPE{i}{k}", ""))
            if not ctype.endswith("-TAB"):
                raise WCSError(f"axis {i}{k} is {ctype!r}, not -TAB")
            ext = str(h.get(f"PS{i}_0{k}", "")).strip().upper()
            col = str(h.get(f"PS{i}_1{k}", "")).strip()
            idx = str(h.get(f"PS{i}_2{k}", "")).strip()
            m = int(h.get(f"PV{i}_3{k}", i))
            if ext not in tables:
                raise WCSError(f"axis {i}{k} references missing table {ext!r}")
            arr_name = arr_name or (ext, col)
            if (ext, col) != arr_name:
                raise WCSError("axes reference different coordinate arrays (unsupported)")
            self.axes.append({"ctype": ctype, "cunit": str(h.get(f"CUNIT{i}{k}", "")).strip(),
                              "crpix": float(h.get(f"CRPIX{i}{k}", 0.0)), "crval": float(h.get(f"CRVAL{i}{k}", 0.0)),
                              "cdelt": float(h.get(f"CDELT{i}{k}", 1.0)), "m": m,
                              "index": np.asarray(tables[ext][idx], float).ravel() if idx else None})
            if idx and idx not in tables[ext]:
                raise WCSError(f"index vector {idx!r} not in {ext}")
        self.pc = np.eye(self.naxis)
        for i in range(self.naxis):
            for j in range(self.naxis):
                v = h.get(f"PC{i + 1}_{j + 1}{k}")
                if v is not None:
                    self.pc[i, j] = float(v)
        ext, col = arr_name
        coords = np.asarray(tables[ext][col], float)
        if coords.ndim == self.naxis + 2 and coords.shape[0] == 1:  # one table row
            coords = coords[0]
        # FITS order (M, K1, ..., KM) is reversed in NumPy: shape (KM, ..., K1, M)
        if coords.ndim != self.naxis + 1 or coords.shape[-1] != self.naxis:
            raise WCSError(f"coordinate array shape {coords.shape} incompatible with {self.naxis} axes")
        self.coords = coords

    @staticmethod
    def _upsilon(psi: float, index: np.ndarray | None) -> float:
        """Fractional 1-based position of psi in the index vector (Paper III eq. 87-88)."""
        if index is None:
            return psi
        n = index.size
        inc = index[-1] >= index[0]
        idx = index if inc else index[::-1]
        if psi < idx[0] or psi > idx[-1]:
            # linear extrapolation by half a cell is allowed by Paper III; beyond that, undefined
            if n < 2:
                return float("nan")
            lo, hi = idx[0] - 0.5 * (idx[1] - idx[0]), idx[-1] + 0.5 * (idx[-1] - idx[-2])
            if not (lo <= psi <= hi):
                return float("nan")
        j = int(np.clip(np.searchsorted(idx, psi) - 1, 0, n - 2))
        u = (j + 1) + (psi - idx[j]) / (idx[j + 1] - idx[j])
        return u if inc else (n + 1 - u)

    def pixel_to_world(self, x: float, y: float) -> tuple[float, ...]:
        p = np.array([x + 1.0, y + 1.0][: self.naxis])  # FITS 1-based pixel
        q = self.pc @ (p - np.array([a["crpix"] for a in self.axes]))
        ups = np.zeros(self.naxis)
        for i, a in enumerate(self.axes):
            psi = a["cdelt"] * q[i] + a["crval"]
            ups[a["m"] - 1] = self._upsilon(psi, a["index"])
        if not np.all(np.isfinite(ups)):
            return tuple(float("nan") for _ in range(self.naxis))
        # multilinear interpolation in the coordinate array at 1-based positions ups (FITS axis order)
        K = self.coords.shape[:-1][::-1]  # FITS order lengths K1..KM
        lo = [int(np.clip(math.floor(u) - 1, 0, k - 2)) if k > 1 else 0 for u, k in zip(ups, K)]
        fr = [(u - 1 - l) if k > 1 else 0.0 for u, l, k in zip(ups, lo, K)]
        out = np.zeros(self.naxis)
        for corner in range(2 ** self.naxis):
            w, ind = 1.0, []
            for d in range(self.naxis):
                bit = (corner >> d) & 1
                w *= fr[d] if bit else (1 - fr[d])
                ind.append(min(lo[d] + bit, K[d] - 1))
            if w:
                out += w * self.coords[tuple(reversed(ind))]
        # element m of the coordinate vector belongs to the world axis whose PVi_3 = m
        return tuple(float(out[a["m"] - 1]) for a in self.axes)
