"""Native FITS reader/writer and WCS tests (standard conformance; astropy cross-checks when available)."""

import math

import numpy as np
import pytest

from skytrace import fitsio
from skytrace.wcs import CelestialWCS, TabWCS, WCSError


def card(k, v):
    return f"{k:<8}= {v:>20}".ljust(80).encode()


def raw_fits(cards: list[bytes], data: bytes) -> bytes:
    h = b"".join(cards) + b"END".ljust(80)
    h += b" " * (-len(h) % 2880)
    return h + data + b"\0" * (-len(data) % 2880)


def test_reads_hand_built_file_per_standard():
    # 2x3 int16 image with BZERO=32768 (unsigned convention) and a quoted string with an embedded quote
    data = (np.array([[0, 1, 2], [3, 4, 65535]], dtype=np.uint32) - 32768).astype(">i2").tobytes()
    cards = [card("SIMPLE", "T"), card("BITPIX", 16), card("NAXIS", 2), card("NAXIS1", 3), card("NAXIS2", 2),
             card("BZERO", 32768), card("BSCALE", 1), "OBJECT  = 'O''Brien '           / a comment".ljust(80).encode(),
             card("EXPTIME", "1.5D2")]
    (h,) = fitsio.read(raw_fits(cards, data))
    assert h.data.dtype == np.uint16 and h.data.tolist() == [[0, 1, 2], [3, 4, 65535]]
    assert h.header["OBJECT"] == "O'Brien" and h.header["EXPTIME"] == 150.0
    assert h.header.comments["OBJECT"] == "a comment"


def test_roundtrip_images_and_table(tmp_path):
    img = np.arange(12, dtype=np.float32).reshape(3, 4)
    flags = np.array([[1, 2], [3, 1 << 21]], dtype=np.int32)
    vals = np.random.default_rng(0).random((1, 4, 5, 2))
    hdr = fitsio.Header({"BUNIT": "MJy/sr", "CRVAL1": 12.5, "FLAG": True, "N": 7})
    p = tmp_path / "t.fits"
    fitsio.write(p, [fitsio.HDU("PRIMARY", fitsio.Header()), fitsio.HDU("IMAGE", hdr, img), fitsio.HDU("FLAGS", fitsio.Header(), flags),
                     fitsio.HDU("WCS-WAVE", fitsio.Header(), {"X": np.arange(5.0)[None], "VALUES": vals}, "table", ["X", "VALUES"])])
    assert p.stat().st_size % 2880 == 0
    h = {x.name: x for x in fitsio.read(p)}
    assert np.array_equal(h["IMAGE"].data, img) and np.array_equal(h["FLAGS"].data, flags)
    assert h["IMAGE"].header["BUNIT"] == "MJy/sr" and h["IMAGE"].header["FLAG"] is True and h["IMAGE"].header["N"] == 7
    assert h["WCS-WAVE"].header["TDIM2"] == "(2,5,4)"
    assert np.allclose(h["WCS-WAVE"].data["VALUES"], vals) and h["WCS-WAVE"].data["VALUES"].shape == (1, 4, 5, 2)


def test_truncated_and_non_fits_rejected(tmp_path):
    p = tmp_path / "t.fits"
    fitsio.write(p, [fitsio.HDU("PRIMARY", fitsio.Header(), np.zeros((50, 50), np.float32))])
    with pytest.raises(fitsio.FITSError, match="truncated"):
        fitsio.read(p.read_bytes()[:4000])
    with pytest.raises(fitsio.FITSError):
        fitsio.read(b"<html>" + b" " * 3000)


def tan_header(**extra):
    s = 6.2 / 3600
    h = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRPIX1": 30.5, "CRPIX2": 30.5, "CRVAL1": 150.0, "CRVAL2": -20.0,
         "CD1_1": -s, "CD1_2": 0.0, "CD2_1": 0.0, "CD2_2": s, "RADESYS": "ICRS"}
    h.update(extra)
    return h


def test_tan_reference_pixel_and_scale():
    w = CelestialWCS(tan_header())
    ra, dec = w.pixel_to_world(29.5, 29.5)  # 0-based CRPIX
    assert ra == pytest.approx(150.0) and dec == pytest.approx(-20.0)
    ra2, dec2 = w.pixel_to_world(29.5, 29.5 + 100)
    assert (dec2 - dec) * 3600 == pytest.approx(620.0, rel=1e-4)  # 100 px north at 6.2"/px
    assert w.pixel_scale_arcsec() == pytest.approx((6.2, 6.2))


def test_sip_forward_inverse_consistent():
    h = tan_header(CTYPE1="RA---TAN-SIP", CTYPE2="DEC--TAN-SIP", A_ORDER=2, A_2_0=2e-4, A_1_1=-1e-4, B_ORDER=2, B_0_2=1.5e-4)
    w = CelestialWCS(h)
    xs, ys = np.array([0.0, 10.3, 55.0]), np.array([3.0, 40.7, 58.0])
    ra, dec = w.pixel_to_world(xs, ys)
    x2, y2 = w.world_to_pixel(ra, dec)
    assert np.allclose(x2, xs, atol=1e-7) and np.allclose(y2, ys, atol=1e-7)
    u = 55.0 + 1 - 30.5  # distortion is applied (differs from pure TAN)
    assert abs(CelestialWCS(tan_header()).pixel_to_world(55.0, 3.0)[0] - w.pixel_to_world(55.0, 3.0)[0]) > 0
    assert u > 0


def test_unsupported_projection_refused():
    with pytest.raises(WCSError):
        CelestialWCS(tan_header(CTYPE1="RA---SIN", CTYPE2="DEC--SIN"))


def tab_setup(x0=100.0, y0=200.0):
    X = np.linspace(1, 2040, 11)
    Y = np.linspace(1, 2040, 11)
    vals = np.zeros((11, 11, 2))
    for j, y in enumerate(Y):
        for i, x in enumerate(X):
            vals[j, i] = (1.1 + 0.0002 * y + 0.00001 * x, 0.03 + 0.000001 * y)
    h = {"WCSAXESW": 2, "CTYPE1W": "WAVE-TAB", "CTYPE2W": "WAVE-TAB", "CUNIT1W": "um", "CUNIT2W": "um",
         "CRPIX1W": 0.0, "CRPIX2W": 0.0, "CRVAL1W": x0, "CRVAL2W": y0, "CDELT1W": 1.0, "CDELT2W": 1.0,
         "PS1_0W": "WCS-WAVE", "PS1_1W": "VALUES", "PS1_2W": "X", "PV1_3W": 1,
         "PS2_0W": "WCS-WAVE", "PS2_1W": "VALUES", "PS2_2W": "Y", "PV2_3W": 2}
    return h, {"WCS-WAVE": {"X": X[None], "Y": Y[None], "VALUES": vals[None]}}


def test_tab_lookup_with_cutout_offset():
    h, t = tab_setup()
    w = TabWCS(h, t, "W")
    # 0-based cutout pixel (10, 20) -> FITS (11, 21) -> detector pixel (111, 221)
    wl, bw = w.pixel_to_world(10, 20)
    assert wl == pytest.approx(1.1 + 0.0002 * 221 + 0.00001 * 111, abs=1e-12)
    assert bw == pytest.approx(0.03 + 0.000001 * 221, abs=1e-12)


def test_tab_outside_table_is_nan():
    h, t = tab_setup(x0=5000.0)
    assert all(math.isnan(v) for v in TabWCS(h, t, "W").pixel_to_world(10, 20))


def test_tab_missing_table_refused():
    h, _ = tab_setup()
    with pytest.raises(WCSError):
        TabWCS(h, {}, "W")


def test_cross_check_with_astropy(tmp_path):
    pytest.importorskip("astropy")
    from astropy.io import fits
    from astropy.wcs import WCS
    h = tan_header(CTYPE1="RA---TAN-SIP", CTYPE2="DEC--TAN-SIP", A_ORDER=2, A_2_0=2e-5, B_ORDER=2, B_0_2=1e-5, NAXIS=2,
                   NAXIS1=60, NAXIS2=60)
    aw = WCS(fits.Header(h))
    ra, dec = aw.all_pix2world([[12.3, 45.6]], 0)[0]
    nra, ndec = CelestialWCS(h).pixel_to_world(12.3, 45.6)
    assert abs(ra - nra) * 3600e3 < 0.5 and abs(dec - ndec) * 3600e3 < 0.5
    # spectral -TAB: compare with wcslib on a file
    th, tables = tab_setup()
    p = tmp_path / "s.fits"
    fitsio.write(p, [fitsio.HDU("PRIMARY", fitsio.Header()),
                     fitsio.HDU("IMAGE", fitsio.Header({**h, **th}), np.zeros((60, 60), np.float32)),
                     fitsio.HDU("WCS-WAVE", fitsio.Header(), tables["WCS-WAVE"], "table", ["X", "Y", "VALUES"])])
    with fits.open(p) as hdul:
        sw = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
        sw.sip = None
        a = sw.pixel_to_world_values(10, 20)
    assert np.allclose(a, TabWCS(th, tables, "W").pixel_to_world(10, 20), atol=1e-9)
