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
        for kw in ("CPDIS1", "CPDIS2", "D2IMDIS1", "D2IMDIS2", "CQDIS1", "DQ1"):
            if kw in h:
                raise WCSError(f"distortion keyword {kw} (lookup-table / Paper IV distortion) is not supported by the native reader; install astropy")
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

    def pixel_to_world(self, x, y, distort: bool = True):
        """0-based pixel -> (ra, dec) degrees. distort=False skips SIP (astropy's wcs_pix2world)."""
        u = np.asarray(x, float) + 1 - self.crpix[0]
        v = np.asarray(y, float) + 1 - self.crpix[1]
        if self.has_sip and distort:
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
    """-TAB axes (Greisen et al. 2006, FITS WCS Paper III, sect. 6), possibly mixed with non-TAB axes.

    Supported: one coordinate array shared by all -TAB axes (M coupled axes), optional
    monotonic index vectors, PC or CD matrices, linear extrapolation up to half a cell
    beyond the table (as wcslib does). Refused with WCSError rather than approximated:
    EXTVER/EXTLEVEL other than 1, more than one coordinate array, non-monotonic index
    vectors, a coordinate array whose shape does not match the number of -TAB axes.
    """

    def __init__(self, h: dict, tables: dict[str, dict], key: str = "W"):
        k = key
        naxis = int(h.get(f"WCSAXES{k}") or 0) or max([i for i in range(1, 10) if f"CTYPE{i}{k}" in h] or [0])
        if naxis == 0:
            raise WCSError(f"no WCS axes with key {k!r}")
        self.naxis = naxis
        self.tab_axes = [i for i in range(1, naxis + 1) if str(h.get(f"CTYPE{i}{k}", "")).endswith("-TAB")]
        if not self.tab_axes:
            raise WCSError(f"no -TAB axes with key {k!r}")
        cd = any(f"CD{i}_{j}{k}" in h for i in range(1, naxis + 1) for j in range(1, naxis + 1))
        self.crpix = np.array([float(h.get(f"CRPIX{i}{k}", 0.0)) for i in range(1, naxis + 1)])
        self.crval = np.array([float(h.get(f"CRVAL{i}{k}", 0.0)) for i in range(1, naxis + 1)])
        cdelt = np.array([1.0 if cd else float(h.get(f"CDELT{i}{k}", 1.0)) for i in range(1, naxis + 1)])
        M = np.zeros((naxis, naxis))
        for i in range(1, naxis + 1):
            for j in range(1, naxis + 1):
                if cd:
                    M[i - 1, j - 1] = float(h.get(f"CD{i}_{j}{k}", 0.0))
                else:
                    M[i - 1, j - 1] = float(h.get(f"PC{i}_{j}{k}", 1.0 if i == j else 0.0))
        self.matrix = M if cd else cdelt[:, None] * M
        self.axes = []
        arr_name = None
        for i in self.tab_axes:
            ext = str(h.get(f"PS{i}_0{k}", "")).strip().upper()
            col = str(h.get(f"PS{i}_1{k}", "")).strip()
            idx = str(h.get(f"PS{i}_2{k}", "")).strip()
            for pv, what in ((1, "EXTVER"), (2, "EXTLEVEL")):
                v = h.get(f"PV{i}_{pv}{k}")
                if v not in (None, 1, 1.0):
                    raise WCSError(f"-TAB {what} = {v} is not supported by the native reader; install astropy")
            if ext not in tables:
                raise WCSError(f"axis {i}{k} references missing table {ext!r}")
            if col not in tables[ext]:
                raise WCSError(f"coordinate array column {col!r} not in {ext}")
            if idx and idx not in tables[ext]:
                raise WCSError(f"index vector {idx!r} not in {ext}")
            arr_name = arr_name or (ext, col)
            if (ext, col) != arr_name:
                raise WCSError("-TAB axes reference different coordinate arrays: not supported by the native reader; install astropy")
            index = np.asarray(tables[ext][idx], float).ravel() if idx else None
            if index is not None and index.size > 1:
                d = np.diff(index)
                if not (np.all(d >= 0) or np.all(d <= 0)):
                    raise WCSError(f"index vector {idx!r} is not monotonic")
                if not np.all(np.isfinite(index)):
                    raise WCSError(f"index vector {idx!r} contains non-finite values")
            self.axes.append({"axis": i, "ctype": str(h.get(f"CTYPE{i}{k}")), "cunit": str(h.get(f"CUNIT{i}{k}", "")).strip(),
                              "m": int(h.get(f"PV{i}_3{k}", 1)), "index": index})
        ext, col = arr_name
        coords = np.asarray(tables[ext][col], float)
        nt = len(self.tab_axes)
        if coords.ndim == nt + 2 and coords.shape[0] == 1:   # one table row
            coords = coords[0]
        # FITS order (M, K1, ..., KM) is reversed in NumPy: shape (KM, ..., K1, M)
        if coords.ndim != nt + 1 or coords.shape[-1] != nt:
            raise WCSError(f"coordinate array shape {coords.shape} incompatible with {nt} -TAB axes")
        if sorted(a["m"] for a in self.axes) != list(range(1, nt + 1)):
            raise WCSError("PVi_3 values must enumerate the coordinate-array axes 1..M")
        self.coords = coords
        # kept for backwards compatibility with callers that read per-axis crpix
        for a in self.axes:
            a["crpix"], a["crval"] = self.crpix[a["axis"] - 1], self.crval[a["axis"] - 1]

    @staticmethod
    def _upsilon(psi: float, index: np.ndarray | None) -> float:
        """Fractional 1-based position of psi in the index vector (Paper III eq. 87-88)."""
        if index is None:
            return psi
        n = index.size
        if n == 1:
            return 1.0 if psi == index[0] else float("nan")
        inc = index[-1] >= index[0]
        idx = index if inc else index[::-1]
        lo, hi = idx[0] - 0.5 * (idx[1] - idx[0]), idx[-1] + 0.5 * (idx[-1] - idx[-2])
        if not (lo <= psi <= hi):   # beyond half a cell: undefined
            return float("nan")
        j = int(np.clip(np.searchsorted(idx, psi) - 1, 0, n - 2))
        while j > 0 and idx[j + 1] == idx[j]:     # degenerate (repeated) entries: use the segment to the left
            j -= 1
        if idx[j + 1] == idx[j]:
            j = min(j + 1, n - 2)
        u = (j + 1) + (psi - idx[j]) / (idx[j + 1] - idx[j])
        return u if inc else (n + 1 - u)

    def pixel_to_world(self, *pix: float) -> tuple[float, ...]:
        """0-based pixel coordinates for all naxis axes -> world values of the -TAB axes (in axis order)."""
        if len(pix) != self.naxis:
            raise WCSError(f"expected {self.naxis} pixel coordinates, got {len(pix)}")
        p = np.asarray(pix, float) + 1.0       # FITS 1-based
        x = self.matrix @ (p - self.crpix)
        nt = len(self.axes)
        ups = np.zeros(nt)
        for a in self.axes:
            psi = x[a["axis"] - 1] + self.crval[a["axis"] - 1]
            ups[a["m"] - 1] = self._upsilon(psi, a["index"])
        K = self.coords.shape[:-1][::-1]  # FITS order lengths K1..KM
        if not np.all(np.isfinite(ups)) or any(not (0.5 <= u <= k + 0.5) for u, k in zip(ups, K)):
            return tuple(float("nan") for _ in self.axes)
        lo = [int(np.clip(math.floor(u) - 1, 0, k - 2)) if k > 1 else 0 for u, k in zip(ups, K)]
        fr = [(u - 1 - l) if k > 1 else 0.0 for u, l, k in zip(ups, lo, K)]
        out = np.zeros(nt)
        for corner in range(2 ** nt):
            w, ind = 1.0, []
            for d in range(nt):
                bit = (corner >> d) & 1
                w *= fr[d] if bit else (1 - fr[d])
                ind.append(min(lo[d] + bit, K[d] - 1))
            if w:
                out += w * self.coords[tuple(reversed(ind))]
        # element m of the coordinate vector belongs to the world axis whose PVi_3 = m
        return tuple(float(out[a["m"] - 1]) for a in self.axes)
