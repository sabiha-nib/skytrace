import json

import pytest

from skytrace.archive import spherex
from skytrace.archive.net import FetchError, Fetcher, OfflineError
from skytrace.archive.tap import parse_csv, parse_votable, validate_csv, validate_votable
from skytrace.provenance import Provenance, ProvenanceError


class FakeResp:
    def __init__(self, status, body=b""):
        self.status_code, self._body = status, body

    def iter_content(self, chunk_size):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        pass


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, timeout, stream):
        self.calls.append(url)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def fetcher(tmp_path, responses=(), offline=False, **kw):
    return Fetcher(tmp_path, offline=offline, session=FakeSession(responses), sleep=lambda s: None, **kw)


def test_live_then_cache_labels(tmp_path):
    f = fetcher(tmp_path, [FakeResp(200, b"a,b\n1,2\n")])
    r = f.get("https://x.test/tap", {"Q": "1"}, source="IRSA", release="QR3")
    assert r.provenance.origin == "live" and r.provenance.release == "QR3"
    # second fetcher: live fails -> served from cache, labelled cache, original time kept
    f2 = fetcher(tmp_path, [ConnectionError("down")] * 3)
    r2 = f2.get("https://x.test/tap", {"Q": "1"}, source="IRSA", release="QR3")
    assert r2.provenance.origin == "cache" and r2.content == r.content
    assert r2.provenance.retrieved_at == r.provenance.retrieved_at
    assert "live failure" in r2.provenance.notes and len(f2._session.calls) == 3


def test_releases_are_cached_separately(tmp_path):
    fetcher(tmp_path, [FakeResp(200, b"qr3")]).get("https://x.test/a", source="IRSA", release="QR3")
    f = fetcher(tmp_path, [], offline=True)
    with pytest.raises(OfflineError):
        f.get("https://x.test/a", source="IRSA", release="QR2")
    assert f.get("https://x.test/a", source="IRSA", release="QR3").content == b"qr3"


def test_offline_never_touches_network(tmp_path, no_network, monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    f = Fetcher(tmp_path)  # real constructor, no fake session: any request would hit the socket guard
    assert f.offline
    with pytest.raises(OfflineError, match="no cached copy"):
        f.get("https://irsa.ipac.caltech.edu/SIA", {"POS": "x"}, source="IRSA")


def test_offline_serves_fixture_with_label(tmp_path, no_network):
    fx = tmp_path / "fx.csv"
    fx.write_bytes(b"a\n1\n")
    prov = Provenance("IRSA", "https://irsa.ipac.caltech.edu/x", "2026-10-01T00:00:00+00:00", "live")
    (tmp_path / "fx.csv.provenance.json").write_text(json.dumps(prov.to_dict()))
    r = Fetcher(tmp_path / "c", offline=True).get("https://irsa.ipac.caltech.edu/x", source="IRSA", fixture=fx)
    assert r.provenance.origin == "fixture" and r.provenance.retrieved_at == "2026-10-01T00:00:00+00:00"


def test_fixture_without_provenance_is_refused(tmp_path):
    fx = tmp_path / "fx.csv"
    fx.write_bytes(b"a\n1\n")
    with pytest.raises(OfflineError, match="provenance"):
        Fetcher(tmp_path / "c", offline=True).get("https://x.test/a", source="IRSA", fixture=fx)


def test_transient_errors_retried_permanent_not(tmp_path):
    f = fetcher(tmp_path, [FakeResp(503), FakeResp(200, b"ok")])
    assert f.get("https://x.test/a", source="IRSA").content == b"ok"
    f = fetcher(tmp_path, [FakeResp(404), FakeResp(200, b"never")])
    with pytest.raises(FetchError) as e:
        f.get("https://x.test/b", source="IRSA")
    assert "HTTP 404" in str(e.value) and len(f._session.calls) == 1


def test_validation_failure_is_not_cached(tmp_path):
    f = fetcher(tmp_path, [FakeResp(200, b"<html>error</html>")])
    with pytest.raises(FetchError, match="invalid response"):
        f.get("https://x.test/a", source="IRSA", validate=validate_csv)
    assert not list(tmp_path.rglob("*.bin"))


def test_size_bound(tmp_path):
    f = fetcher(tmp_path, [FakeResp(200, b"x" * 1000)], max_bytes=100)
    with pytest.raises(FetchError, match="exceeds"):
        f.get("https://x.test/a", source="IRSA")


def test_corrupted_cache_is_not_served(tmp_path):
    fetcher(tmp_path, [FakeResp(200, b"good")]).get("https://x.test/a", source="IRSA")
    next(tmp_path.rglob("*.bin")).write_bytes(b"tampered")
    with pytest.raises(OfflineError):
        fetcher(tmp_path, offline=True).get("https://x.test/a", source="IRSA")


def test_provenance_rules():
    with pytest.raises(ProvenanceError):
        Provenance("IRSA", "", "2026-01-01", "live")
    with pytest.raises(ProvenanceError):
        Provenance("IRSA", "u", "2026-01-01", "synthetic")
    with pytest.raises(ProvenanceError):
        Provenance("IRSA", "u", "2026-01-01", "made-up")


# ------------------------------------------------------------- SPHEREx metadata parsing
URL = ("https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2025W18_2B/l2b-v20-2025-164/2/"
       "level2_2025W18_2B_0001_1D2_spx_l2b-v20-2025-164.fits")  # constructed to match the documented naming


def test_filename_and_release_parsing():
    assert spherex.parse_filename(URL) == ("2025W18_2B_0001_1", 2)
    assert spherex.release_from_path(URL) == "QR3"
    assert spherex.release_from_path("https://x/other.fits") == "UNKNOWN"


def test_observations_from_sia_rows():
    rows = [{"access_url": URL, "t_min": 60800.0, "t_max": 60800.002, "em_min": 1.1e-6, "em_max": 1.62e-6,
             "energy_bandpassname": "SPHEREx-D2", "obs_id": None}]
    (o,) = spherex.observations_from_sia(rows, "QR3")
    assert o.detector == 2 and o.obs_id == "2025W18_2B_0001_1" and o.em_min_um == pytest.approx(1.1)
    assert o.t_mid_mjd == pytest.approx(60800.001)


def test_cutout_url_rules():
    u = spherex.cutout_url(URL, 133.795, -7.245, 0.1)
    assert u.endswith("?center=133.7950000,-7.2450000d&size=0.1")
    with pytest.raises(ValueError):
        spherex.cutout_url("https://evil.test/x.fits", 1, 1, 0.1)
    with pytest.raises(ValueError):
        spherex.cutout_url(URL, 1, 1, 5.0)


VOT = b"""<?xml version="1.0"?><VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>
<FIELD name="access_url" datatype="char" arraysize="*"/><FIELD name="t_min" datatype="double"/>
<DATA><TABLEDATA><TR><TD>https://irsa.ipac.caltech.edu/a.fits</TD><TD>60800.5</TD></TR></TABLEDATA></DATA>
</TABLE></RESOURCE></VOTABLE>"""


def test_votable_parse_and_error_detection():
    validate_votable(VOT)
    assert parse_votable(VOT) == [{"access_url": "https://irsa.ipac.caltech.edu/a.fits", "t_min": 60800.5}]
    with pytest.raises(ValueError, match="error"):
        validate_votable(VOT.replace(b'value="OK"', b'value="ERROR"'))


def test_csv_parse_types_and_nulls():
    rows = parse_csv(b"a,b,c\n1,2.5,\nx,,3\n")
    assert rows == [{"a": 1, "b": 2.5, "c": None}, {"a": "x", "b": None, "c": 3}]
