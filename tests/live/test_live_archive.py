"""Live smoke tests against real services. Excluded by default; run with `pytest -m live`.

They check that the documented interfaces behave as this code assumes. An
archive outage fails these tests only, never the deterministic suite.
"""

import pytest

from skytrace.archive import references, spherex
from skytrace.archive.net import Fetcher

pytestmark = pytest.mark.live


@pytest.fixture
def fetcher(tmp_path):
    return Fetcher(tmp_path, offline=False)


def test_sia_qr3_returns_spherex_images(fetcher):
    # IRSA's documented example position (SPHEREx intro / data-access pages)
    obs, prov = spherex.discover_sia(fetcher, 127.69444, -39.17760, "QR3", 0.01)
    assert prov.origin == "live"
    assert obs, "no QR3 images at IRSA's documented example position"
    assert all(o.detector in range(1, 7) for o in obs)
    assert all(o.access_url.startswith(spherex.IRSA) for o in obs)


def test_tap_schema_has_documented_columns(fetcher):
    cols = {r["column_name"] for r in spherex.list_columns(fetcher, "spherex.plane")}
    assert {"planeid", "time_bounds_lower", "energy_bandpassname", "poly"} <= cols


def test_simbad_resolves_barnard(fetcher):
    row, _ = references.resolve_simbad(fetcher, "Barnard's star")
    assert row["pmdec"] > 10000


def test_cutout_is_fits_with_documented_extensions(fetcher):
    pytest.importorskip("astropy")
    from skytrace.archive.products import inspect_product, load_product
    obs, _ = spherex.discover_sia(fetcher, 127.69444, -39.17760, "QR3", 0.01)
    res = spherex.fetch_cutout(fetcher, obs[0], 127.69444, -39.17760, 0.02)
    rep = inspect_product(load_product(res.content))
    assert {"IMAGE", "FLAGS", "VARIANCE"} <= set(rep["extensions"])
    print(rep)
