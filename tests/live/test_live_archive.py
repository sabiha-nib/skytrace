"""Live checks against the real services. Excluded by default; run with `pytest -m live` on a networked machine.

They confirm that the documented interfaces behave as this code assumes, and that the
native FITS/WCS implementation agrees with astropy on a real SPHEREx product. An
archive outage fails these tests only, never the deterministic suite.
"""

import numpy as np
import pytest

from skytrace.archive import references, spherex
from skytrace.archive.net import Fetcher

pytestmark = pytest.mark.live
RA, DEC = 127.69444, -39.17760   # IRSA's documented example position (SPHEREx data-access page)


@pytest.fixture(scope="module")
def fetcher(tmp_path_factory):
    return Fetcher(tmp_path_factory.mktemp("cache"), offline=False)


@pytest.fixture(scope="module")
def qr3(fetcher):
    obs, prov = spherex.discover_sia(fetcher, RA, DEC, "QR3", 0.01)
    assert prov.origin == "live"
    assert obs, "no QR3 images at IRSA's documented example position"
    return obs


def test_sia_qr3_returns_spherex_images(qr3):
    assert all(o.detector in range(1, 7) for o in qr3)
    assert all(o.access_url.startswith(spherex.IRSA) for o in qr3)
    assert all(o.t_mid_mjd and 60000 < o.t_mid_mjd < 62000 for o in qr3)
    assert {spherex.release_from_path(o.access_url) for o in qr3} == {"QR3"}


def test_tap_schema_has_documented_columns(fetcher):
    cols = {r["column_name"] for r in spherex.list_columns(fetcher, "spherex.plane")}
    assert {"planeid", "time_bounds_lower", "energy_bandpassname", "poly"} <= cols


def test_simbad_and_gaia_resolve_barnard(fetcher):
    row, _ = references.resolve_simbad(fetcher, "Barnard's star")
    assert row["pmdec"] > 10000
    rows, _ = references.gaia_cone(fetcher, 269.4486, 4.7397, 5 / 3600, g_min=-5, g_max=25)
    assert any(r["pmdec"] and r["pmdec"] > 10000 for r in rows)


def test_cutout_structure_and_native_reader_matches_astropy(fetcher, qr3, tmp_path):
    from skytrace.archive.products import inspect_product, load_product
    res = spherex.fetch_cutout(fetcher, qr3[0], RA, DEC, 0.05)
    p = tmp_path / "cut.fits"
    p.write_bytes(res.content)
    native = load_product(p, prefer="native")
    rep = inspect_product(native)
    print(rep)
    assert {"IMAGE", "FLAGS", "VARIANCE"} <= set(rep["extensions"])
    assert str(rep["image_bunit"]).replace(" ", "").lower() == "mjy/sr"
    pytest.importorskip("astropy")
    ref = load_product(p, prefer="astropy")
    assert np.array_equal(np.nan_to_num(native.image), np.nan_to_num(ref.image))
    assert np.array_equal(native.flags, ref.flags)
    ny, nx = native.image.shape
    for x, y in [(0, 0), (nx / 2, ny / 2), (nx - 1, ny - 1), (3.3, ny - 5.7)]:
        a, b = native.pixel_to_sky(x, y), ref.pixel_to_sky(x, y)
        assert abs(a[0] - b[0]) * 3600 * np.cos(np.radians(b[1])) < 0.01 and abs(a[1] - b[1]) * 3600 < 0.01  # < 10 mas
        wn, wa = native.wavelength_at(x, y), ref.wavelength_at(x, y)
        assert abs(wn[0] - wa[0]) < 1e-6 and abs(wn[1] - wa[1]) < 1e-6   # µm
    ra, dec = ref.pixel_to_sky(nx / 3, ny / 4)
    xn, yn = native.sky_to_pixel(ra, dec)
    assert abs(xn - nx / 3) < 1e-3 and abs(yn - ny / 4) < 1e-3
