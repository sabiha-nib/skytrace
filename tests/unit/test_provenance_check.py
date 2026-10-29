"""PROVCHECK-1 detects tampering, foreign records and non-determinism, and passes a clean record."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from skytrace import analysis, bundle as bmod
from skytrace.provenance_check import verify_record

FIX = Path(__file__).parents[2] / "fixtures" / "synthetic"


@pytest.fixture(scope="module")
def clean():
    b = bmod.load(FIX / "syn-var-1")
    return analysis.run(b).to_dict()


def ids(res):
    return {c["id"] for c in res["checks"] if not c["ok"]}


def test_clean_record_passes_including_determinism(clean, no_network):
    res = verify_record(json.loads(json.dumps(clean)), FIX / "syn-var-1", rerun=True)
    assert res["ok"], [c for c in res["checks"] if not c["ok"]]


def test_edited_number_breaks_record_hash(clean):
    r = copy.deepcopy(clean)
    ev = next(e for e in r["events"] if e["step"] == "astrometry")
    ev["data"]["fit"]["pm_xi_mas_yr"] += 100.0
    assert {"record_hash", "outcome_consistency"} <= ids(verify_record(r, FIX / "syn-var-1"))


def test_record_from_other_bundle(clean):
    assert "bundle_identity" in ids(verify_record(clean, FIX / "syn-hpm-1"))


def test_modified_file_detected(clean, tmp_path):
    d = tmp_path / "syn-var-1"
    shutil.copytree(FIX / "syn-var-1", d)
    img = next((d / "images").glob("*.fits"))
    data = bytearray(img.read_bytes()); data[-10] ^= 0xFF
    img.write_bytes(bytes(data))
    assert "bundle_integrity" in ids(verify_record(clean, d))


def test_unknown_code_and_origin_detected(clean):
    r = copy.deepcopy(clean)
    me = next(e for e in r["events"] if e["step"] == "measure" and e["provenance"])
    me["data"]["quality_code"] = "looks fine to me"
    me["provenance"][0]["origin"] = "live"
    bad = ids(verify_record(r, FIX / "syn-var-1"))
    assert {"status_codes", "data_origin"} <= bad
