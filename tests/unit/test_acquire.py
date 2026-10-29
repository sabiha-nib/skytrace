"""Acquisition plumbing against a MOCKED archive (no network).

The fake services return SIMBAD/Gaia CSV, an SIA VOTable and FITS cutouts built
in the test. This checks discovery -> selection -> download -> checksum ->
inspection -> manifest -> verification, resumption, and failure reporting.
It does not show that the real services behave this way; tests/live does that.
"""

import json
import math
from urllib.parse import parse_qs, urlparse

import numpy as np
import pytest

from skytrace import bundle as bmod
from skytrace import fitsio
from skytrace.archive.acquire import acquire
from skytrace.archive.net import Fetcher

RA, DEC = 120.0, 15.0
SIMBAD = "main_id,ra,dec,coo_bibcode,pmra,pmdec,pm_bibcode,plx_value,rvz_radvel,sp_type,otype\nTEST STAR,120.0,15.0,x,100.0,-50.0,y,20.0,,M5V,*\n"
GAIA_T = "source_id,ra,dec,ra_error,dec_error,pmra,pmdec,pmra_error,pmdec_error,parallax,parallax_error,radial_velocity,ref_epoch,phot_g_mean_mag,ruwe\n42,120.00001,14.99999,0.1,0.1,101.0,-49.0,0.1,0.1,20.1,0.1,,2016.0,12.0,1.0\n"


def gaia_refs():
    rows = ["source_id,ra,dec,ra_error,dec_error,pmra,pmdec,pmra_error,pmdec_error,parallax,radial_velocity,ref_epoch,phot_g_mean_mag,ruwe"]
    rng = np.random.default_rng(1)
    for i in range(12):
        rows.append(f"{1000 + i},{RA + rng.uniform(-0.03, 0.03)},{DEC + rng.uniform(-0.03, 0.03)},0.1,0.1,1,1,0.1,0.1,1,,2016.0,13,1.0")
    return "\n".join(rows) + "\n"


def sia(n=3):
    rows = "".join(f"<TR><TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/l2/level2_2025W2{i}_1A_0001_1D2_spx_l2b.fits</TD>"
                   f"<TD>{60850 + 180 * i}</TD><TD>{60850.001 + 180 * i}</TD><TD>1.1e-6</TD><TD>1.62e-6</TD><TD>SPHEREx-D2</TD><TD></TD></TR>"
                   for i in range(n))
    return f"""<?xml version="1.0"?><VOTABLE version="1.4"><RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>
<FIELD name="access_url" datatype="char" arraysize="*"/><FIELD name="t_min" datatype="double"/><FIELD name="t_max" datatype="double"/>
<FIELD name="em_min" datatype="double"/><FIELD name="em_max" datatype="double"/><FIELD name="energy_bandpassname" datatype="char" arraysize="*"/>
<FIELD name="obs_id" datatype="char" arraysize="*"/><DATA><TABLEDATA>{rows}</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"""


def cutout(ra, dec, path):
    s = 6.2 / 3600
    h = fitsio.Header({"BUNIT": "MJy/sr", "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRPIX1": 29.5, "CRPIX2": 29.5,
                       "CRVAL1": ra, "CRVAL2": dec, "CD1_1": -s, "CD1_2": 0.0, "CD2_1": 0.0, "CD2_2": s})
    img = np.zeros((58, 58), np.float32) + 0.3
    fitsio.write(path, [fitsio.HDU("PRIMARY", fitsio.Header()), fitsio.HDU("IMAGE", h, img),
                        fitsio.HDU("FLAGS", fitsio.Header(), np.zeros((58, 58), np.int32)),
                        fitsio.HDU("VARIANCE", fitsio.Header(), np.ones((58, 58), np.float32) * 1e-4)])
    return path.read_bytes()


class Resp:
    def __init__(self, status, body):
        self.status_code, self.body = status, body if isinstance(body, bytes) else body.encode()

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        pass


class FakeArchive:
    def __init__(self, tmp, fail_cutouts=False):
        self.tmp, self.fail, self.calls = tmp, fail_cutouts, []

    def get(self, url, timeout, stream):
        self.calls.append(url)
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if "sim-tap" in url:
            return Resp(200, SIMBAD)
        if "gea.esac" in url:
            return Resp(200, GAIA_T if "CIRCLE('ICRS'" in q["QUERY"] and "0.001389" in q["QUERY"] else gaia_refs())
        if u.path == "/SIA":
            return Resp(200, sia() if q["COLLECTION"] == "spherex_qr3" else sia(0))
        if "center" in q:
            if self.fail:
                return Resp(503, "busy")
            ra, dec = (float(x) for x in q["center"].rstrip("d").split(","))
            return Resp(200, cutout(ra, dec, self.tmp / "c.fits"))
        return Resp(404, "nope")


CFG = {"target_id": "test-star", "name": "Test Star", "simbad_id": "TEST STAR", "role": "test"}


def test_acquire_writes_verified_archive_bundle(tmp_path):
    fake = FakeArchive(tmp_path)
    f = Fetcher(tmp_path / "cache", offline=False, session=fake, sleep=lambda s: None)
    r = acquire(f, CFG, out_root=tmp_path / "bundles", detectors=(2,))
    assert r["status"] == "OK" and r["n_included"] == 3
    bdir = tmp_path / "bundles" / "test-star"
    v = bmod.verify(bdir)
    assert v["ok"], v["problems"]
    b = bmod.load(bdir)
    assert b.kind == "archive" and b.target["identity"]["gaia_dr3_source_id"] == 42
    assert b.target["astrometry"]["pmra"] == 101.0          # Gaia DR3 preferred over SIMBAD
    assert len(b.references["stars"]) == 12 and "inspection.json" in {x["path"] for x in b.manifest["files"]}
    assert all(o["release"] == "QR3" and o["sha256"] for o in b.observations())
    # resume: a second run downloads no cutouts again
    n = sum("center=" in c for c in fake.calls)
    acquire(f, CFG, out_root=tmp_path / "bundles", detectors=(2,))
    assert sum("center=" in c for c in fake.calls) == n
    assert bmod.verify(bdir)["ok"]


def test_failed_downloads_are_reported_not_substituted(tmp_path):
    f = Fetcher(tmp_path / "cache", offline=False, session=FakeArchive(tmp_path, fail_cutouts=True), sleep=lambda s: None)
    r = acquire(f, CFG, out_root=tmp_path / "bundles", detectors=(2,))
    assert r["status"] == "NO USABLE IMAGES" and r["n_included"] == 0
    b = bmod.load(tmp_path / "bundles" / "test-star")
    assert all("download failed" in o["exclusion_reason"] for o in b.all_observations())
    assert not list((tmp_path / "bundles" / "test-star" / "images").glob("*.fits"))


def test_verifier_catches_tampering_and_mislabels(tmp_path):
    f = Fetcher(tmp_path / "cache", offline=False, session=FakeArchive(tmp_path), sleep=lambda s: None)
    acquire(f, CFG, out_root=tmp_path / "bundles", detectors=(2,))
    bdir = tmp_path / "bundles" / "test-star"
    img = next((bdir / "images").glob("*.fits"))
    img.write_bytes(img.read_bytes()[:-2880] + b"\0" * 2880)
    (bdir / "stray.txt").write_text("x")
    probs = bmod.verify(bdir)["problems"]
    assert any("checksum mismatch" in p for p in probs) and any("unlisted file stray.txt" in p for p in probs)


def test_synthetic_fixture_cannot_pass_as_archive(tmp_path):
    import shutil
    src = bmod.SYNTHETIC_ROOT / "syn-hpm-1"
    dst = tmp_path / "fake-archive"
    shutil.copytree(src, dst)
    m = json.loads((dst / "manifest.json").read_text())
    m["kind"] = "archive"
    (dst / "manifest.json").write_text(json.dumps(m))
    probs = bmod.verify(dst)["problems"]
    assert any("SYNTHETIC FITS" in p for p in probs) and any("provenance origin 'synthetic'" in p for p in probs)
