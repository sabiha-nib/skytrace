"""Independent validation of the native FITS/WCS reader (Gate C).

Inputs were written by software other than Skytrace (astropy, cfitsio, wcslib-era tools,
other missions) and copied unmodified from astropy v7.0.1 (tests/data/external/, BSD-3).
Expected values are transcribed from astropy's own test-suite, which checks them against
wcslib. The -TAB ground truth is astropy's analytic SimModelTAB.fwd_eval (re-implemented
here from astropy/wcs/tests/helper.py), not Skytrace code.

Tolerances (explicit):
  celestial pixel->sky            1e-8 deg (as astropy's own assertion) = 36 microarcsec
  SIP-distorted footprints        rtol 1e-7 (astropy's assert_allclose default)
  SIP focal-plane offset          rtol 1e-3 (as astropy's test_sip)
  -TAB vs analytic model          atol 1e-7 (as astropy's test_2d_spatial_tab_vs_model)
  scaled float32 table columns    rtol 1e-6 (astropy computes in float32, Skytrace in float64)
"""

from pathlib import Path

import numpy as np
import pytest

from skytrace import fitsio
from skytrace.wcs import CelestialWCS, TabWCS, WCSError

EXT = Path(__file__).resolve().parents[1] / "data" / "external" / "astropy-v7.0.1"


def hdr(name, i=0):
    return fitsio.read(EXT / name)[i].header


# ------------------------------------------------------------------ FITS structure
def test_binary_table_values_match_astropy():
    # astropy/io/fits/tests/test_table.py::test_binary_table
    t = fitsio.read(EXT / "tb.fits")[1]
    assert t.header["TFORM1"] == "1J"
    assert t.data["c1"].tolist() == [1, 2]
    assert [s.rstrip() for s in t.data["c2"].tolist()] == ["abc", "xy"]
    np.testing.assert_allclose(t.data["c3"], [3.7000002861022949, 6.6999998092651367], rtol=1e-6)   # TSCAL/TZERO applied
    assert t.data["c4"].tolist() == [False, True]                                                    # FITS logical 'F','T'


def test_tdim_shape_matches_astropy():
    # test_table.py: hdulist[1].data["V_mag"].shape == (3, 1, 1)
    assert fitsio.read(EXT / "tdim.fits")[1].data["V_mag"].shape == (3, 1, 1)


def test_image_axis_order_matches_astropy():
    # test_image.py::test_section: section[3, 2, 5] == 357 and the row [3, 2, :]
    a = fitsio.read(EXT / "arange.fits")[0].data
    assert a.shape == (7, 10, 11) and a[3, 2, 5] == 357
    assert a[3, 2, :].tolist() == list(range(352, 363))


def test_bscale_bzero_applied():
    h = fitsio.read(EXT / "scale.fits")[0]
    raw_bytes = (EXT / "scale.fits").read_bytes()
    nhead = raw_bytes.index(b"END" + b" " * 77) // 2880 * 2880 + 2880
    raw = np.frombuffer(raw_bytes[nhead:nhead + 21 * 20 * 2], ">i2").reshape(21, 20)
    np.testing.assert_allclose(h.data, raw * h.header["BSCALE"] + h.header["BZERO"], rtol=0, atol=1e-9)


def test_unsigned_integer_convention_and_bit_columns():
    t = fitsio.read(EXT / "memtest.fits")[1]
    assert all(np.isfinite(v).all() for k, v in t.data.items() if v.dtype.kind in "fiu")
    ev = fitsio.read(EXT / "chandra_time.fits")[1]
    bits = [v for k, v in ev.data.items() if v.dtype == np.uint8 and v.ndim == 2 and v.shape[1] == 32]
    assert bits and set(np.unique(bits[0])) <= {0, 1}


def test_zero_width_columns_parse():
    hd = fitsio.read(EXT / "zerowidth.fits")
    assert hd[2].data["ORBPARM"].shape == (29, 0)


@pytest.mark.parametrize("name,match", [("group.fits", "random-groups"), ("comp.fits", "variable-length")])
def test_unsupported_formats_are_refused_clearly(name, match):
    with pytest.raises(fitsio.FITSError, match=match) as e:
        fitsio.read(EXT / name)
    assert "astropy" in str(e.value)


@pytest.mark.parametrize("damage", ["truncate", "no_end", "bad_width"])
def test_malformed_files_fail_with_fits_error(damage):
    raw = (EXT / "tb.fits").read_bytes()
    if damage == "truncate":
        raw = raw[:4000]
    elif damage == "no_end":
        raw = raw[:2880].replace(b"END" + b" " * 77, b" " * 80) + b"\0" * 100
    else:
        raw = raw.replace(b"NAXIS1  =                   12", b"NAXIS1  =                   13")
    with pytest.raises(fitsio.FITSError):
        fitsio.read(raw)


# ------------------------------------------------------------------ celestial WCS
def test_sip2_linear_pix2world_matches_wcslib():
    # astropy/wcs/tests/test_wcs.py::test_pix2world (wcs_pix2world: no SIP), origin 0
    h = hdr("sip2.fits")
    w = CelestialWCS(h)
    np.testing.assert_allclose(w.cd, [[0.00024976, 0.00023018], [0.00023043, -0.00024997]], atol=1e-8)
    ra, dec = w.pixel_to_world(np.arange(3.0), np.arange(3.0), distort=False)
    ans = np.array([[202.39265216, 47.17756518], [202.39335826, 47.17754619], [202.39406436, 47.1775272]])
    np.testing.assert_allclose(np.column_stack([ra, dec]), ans, atol=1e-8, rtol=1e-10)


@pytest.mark.parametrize("distort,ref", [
    (True, [[202.39314493, 47.17753352], [202.71885939, 46.94630488], [202.94631893, 47.15855022], [202.72053428, 47.37893142]]),
    (False, [[202.39265216, 47.17756518], [202.7469062, 46.91483312], [203.11487481, 47.14359319], [202.76092671, 47.40745948]]),
])
def test_sip_footprint_matches_wcslib(distort, ref):
    # test_wcs.py::test_calc_footprint_1 (all_pix2world, SIP) and _2 (no distortion); axes (1000, 1051)
    w = CelestialWCS(hdr("sip.fits"))
    corners = np.array([[1, 1], [1, 1051], [1000, 1051], [1000, 1]], float) - 1   # 1-based pixel centres -> 0-based
    ra, dec = w.pixel_to_world(corners[:, 0], corners[:, 1], distort=distort)
    np.testing.assert_allclose(np.column_stack([ra, dec]), ref, rtol=1e-7)


def test_sip_inverse_roundtrip_on_real_header():
    w = CelestialWCS(hdr("sip.fits"))
    xs, ys = np.array([0.0, 500.3, 999.0]), np.array([0.0, 520.7, 1050.0])
    ra, dec = w.pixel_to_world(xs, ys)
    x2, y2 = w.world_to_pixel(ra, dec)
    np.testing.assert_allclose(x2, xs, atol=1e-6)
    np.testing.assert_allclose(y2, ys, atol=1e-6)


def test_irac_sip_focal_plane_matches_wcslib():
    """test_wcs.py::test_sip: sip_pix2foc(200, 200, origin=0) == (72, 72) within rtol 1e-3.

    astropy returns the focal-plane offset from CRPIX expressed with the caller's origin, i.e.
    (u + A(u, v)) - 1 for origin 0, where u = x(1-based) - CRPIX. This is a weak check (rtol 1e-3
    is +/-0.07 px); the footprint tests above check SIP to rtol 1e-7.
    """
    h = fitsio.parse_header((EXT / "irac_sip.hdr").read_bytes())
    w = CelestialWCS(h)
    from skytrace.wcs import _poly
    u, v = 200.0 + 1 - w.crpix[0], 200.0 + 1 - w.crpix[1]
    fu, fv = u + _poly(w.a, u, v), v + _poly(w.b, u, v)
    np.testing.assert_allclose([fu - 1, fv - 1], [72, 72], rtol=1e-3)


# ------------------------------------------------------------------ -TAB
class SimModelTAB:
    """Port of astropy/wcs/tests/helper.py::SimModelTAB (BSD-3, Astropy Developers): header + table + analytic truth."""

    def __init__(self, nx=150, ny=200, crpix=(1, 1), crval=(1, 1), cdelt=(1, 1)):
        self.nx, self.ny, self.crpix, self.crval, self.cdelt = nx, ny, crpix, crval, cdelt

    def fwd_eval(self, xy):
        xb = 1 + self.nx // 3
        px = np.array([1, xb, xb, self.nx + 1])
        py = np.array([1, self.ny + 1])
        xi = self.crval[0] + self.cdelt[0] * (px - self.crpix[0])
        yi = self.crval[1] + self.cdelt[1] * (py - self.crpix[1])
        cx, cy = np.array([0.0, 0.26, 0.8, 1.0]), np.array([-0.5, 0.5])
        x, y = xy[:, 0], xy[:, 1]
        i = 2 * (x > xb).astype(int)
        psix = self.crval[0] + self.cdelt[0] * (x - self.crpix[0])
        psiy = self.crval[1] + self.cdelt[1] * (y - self.crpix[1])
        cfx = (psix - xi[i]) / (xi[i + 1] - xi[i])
        cfy = (psiy - yi[0]) / (yi[1] - yi[0])
        return np.column_stack([cx[i] + cfx * (cx[i + 1] - cx[i]), cy[0] + cfy * (cy[1] - cy[0])])

    def header_and_tables(self):
        x = np.array([[0.0, 0.26, 0.8, 1.0], [0.0, 0.26, 0.8, 1.0]])
        y = np.array([[-0.5] * 4, [0.5] * 4])
        c = np.dstack([x, y])                       # numpy shape (K2, K1, M) = (2, 4, 2)
        xb = 1 + self.nx // 3
        px, py = np.array([1, xb, xb, self.nx + 1]), np.array([1, self.ny + 1])
        xi = self.crval[0] + self.cdelt[0] * (px - self.crpix[0])
        yi = self.crval[1] + self.cdelt[1] * (py - self.crpix[1])
        h = {"NAXIS": 2, "CTYPE1": "RA---TAB", "CTYPE2": "DEC--TAB", "PS1_0": "WCS-TABLE", "PS2_0": "WCS-TABLE",
             "PS1_1": "wavelength", "PS2_1": "wavelength", "PV1_3": 1, "PV2_3": 2, "CUNIT1": "deg", "CUNIT2": "deg",
             "CDELT1": self.cdelt[0], "CDELT2": self.cdelt[1], "CRPIX1": self.crpix[0], "CRPIX2": self.crpix[1],
             "CRVAL1": self.crval[0], "CRVAL2": self.crval[1], "PS1_2": "xi", "PS2_2": "yi", "PC1_1": 1, "PC2_2": 1}
        return h, {"WCS-TABLE": {"wavelength": c[None], "xi": xi[None], "yi": yi[None]}}


@pytest.mark.parametrize("params", [{}, {"crpix": (3, 7), "crval": (10, -4), "cdelt": (0.5, 2.0)}])
def test_tab_matches_analytic_model(params, tmp_path):
    # astropy/wcs/tests/test_tab.py::test_2d_spatial_tab_vs_model (atol 1e-7), incl. the index-vector jump
    m = SimModelTAB(**params)
    h, tables = m.header_and_tables()
    rng = np.random.default_rng(1)
    xy = 0.51 + np.array([m.nx + 0.99, m.ny + 0.99]) * rng.random((100, 2))     # 1-based, as astropy's test
    w = TabWCS(h, tables, key="")
    got = np.array([w.pixel_to_world(x - 1, y - 1) for x, y in xy])
    ok = np.isfinite(got).all(axis=1)
    assert ok.mean() > 0.95
    np.testing.assert_allclose(got[ok], m.fwd_eval(xy)[ok], atol=1e-7)
    # same through a FITS file written by Skytrace and read back (checks TDIM orientation end to end)
    p = tmp_path / "tab.fits"
    hh = fitsio.Header(h)
    fitsio.write(p, [fitsio.HDU("PRIMARY", hh, np.zeros((m.ny, m.nx), np.float32)),
                     fitsio.HDU("WCS-TABLE", fitsio.Header(), tables["WCS-TABLE"], "table", ["wavelength", "xi", "yi"])])
    hd = fitsio.read(p)
    w2 = TabWCS(hd[0].header, {x.name: x.data for x in hd if x.kind == "table"}, key="")
    got2 = np.array([w2.pixel_to_world(x - 1, y - 1) for x, y in xy[:20]])
    np.testing.assert_allclose(got2, got[:20], atol=0, equal_nan=True)


def test_tab_on_astropy_written_file_with_mixed_axes():
    """tab-time-last-axis.fits: RA/Dec TAN + TIME-TAB as axis 3 (written by astropy).

    By Paper III with CRPIX3 = CRVAL3 = CDELT3 = 1 and no index vector, psi = p (1-based) and the
    time at 0-based pixel z is coordinates[z], which the file stores as 0..127: time(z) = z.
    """
    hd = fitsio.read(EXT / "tab-time-last-axis.fits")
    w = TabWCS(hd[0].header, {x.name: x.data for x in hd if x.kind == "table"}, key="")
    assert [a["ctype"] for a in w.axes] == ["TIME-TAB"]
    for z in (0, 1, 63.25, 126.5, 127):
        assert w.pixel_to_world(5.0, 7.0, z)[0] == pytest.approx(z, abs=1e-12)
    assert np.isnan(w.pixel_to_world(5.0, 7.0, 128.6)[0])          # beyond half a cell: undefined
    cel = CelestialWCS(hd[0].header)
    ra, dec = cel.pixel_to_world(31.5, 15.5)                         # CRPIX (32.5, 16.5) in 0-based
    assert ra == pytest.approx(5.6305039831305) and dec == pytest.approx(-72.050216354325)


def test_tab_refuses_unsupported_conventions():
    m = SimModelTAB()
    h, t = m.header_and_tables()
    with pytest.raises(WCSError, match="EXTVER"):
        TabWCS({**h, "PV1_1": 2}, t, key="")
    bad = {"WCS-TABLE": {**t["WCS-TABLE"], "xi": np.array([[1.0, 60.0, 10.0, 151.0]])}}
    with pytest.raises(WCSError, match="monotonic"):
        TabWCS(h, bad, key="")
    with pytest.raises(WCSError, match="missing table"):
        TabWCS(h, {}, key="")
    with pytest.raises(WCSError, match="lookup-table"):
        CelestialWCS({**hdr("sip.fits"), "CPDIS1": "Lookup"})


def test_tab_invalid_lookup_entries_propagate_nan():
    m = SimModelTAB()
    h, t = m.header_and_tables()
    c = t["WCS-TABLE"]["wavelength"].copy()
    c[0, 0, 1, 0] = np.nan                                           # one table cell invalid
    w = TabWCS(h, {"WCS-TABLE": {**t["WCS-TABLE"], "wavelength": c}}, key="")
    assert np.isnan(w.pixel_to_world(20.0, 5.0)[0])                  # uses that cell
    assert np.isfinite(w.pixel_to_world(120.0, 5.0)[0])              # does not


def test_blank_and_tnull_become_nan(tmp_path):
    """FITS Standard 4.0 sect. 5.2.2 (BLANK) and 7.3.2 (TNULL): undefined integers must not read as numbers."""
    img = np.array([[1, -32768, 3]], dtype=np.int16)
    p = tmp_path / "b.fits"
    fitsio.write(p, [fitsio.HDU("PRIMARY", fitsio.Header({"BLANK": -32768}), img),
                     fitsio.HDU("T", fitsio.Header({"TNULL1": -1}), {"c": np.array([5, -1, 7], np.int32)}, "table", ["c"])])
    hd = fitsio.read(p)
    assert np.isnan(hd[0].data[0, 1]) and hd[0].data[0, 2] == 3
    assert np.isnan(hd[1].data["c"][1]) and hd[1].data["c"][2] == 7
