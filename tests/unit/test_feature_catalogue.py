"""The feature catalogue is generated, well formed, and honest about verification."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import feature_catalogue as fc  # noqa: E402


def test_catalogue_shape_and_counts():
    cat = fc.build()
    assert cat["counts"]["concepts"] >= 250 and cat["counts"]["domains"] == 25
    assert len(cat["dimensions"]) == 7
    ids = [x["id"] for x in cat["items"]]
    assert len(ids) == len(set(ids))
    names = [x["concept"] for x in cat["items"]]
    assert len(names) == len(set(names)), "duplicate concept"
    for x in cat["items"]:
        assert all(1 <= v <= 5 for v in x["scores"].values()) and len(x["scores"]) == 7, x["id"]
        assert x["tier"] in "ABCD" and x["status_code"] in "ENPX"
        assert x["tier"] == fc.tier(x["status_code"], "".join(str(v) for v in x["scores"].values()))
        if x["status_code"] == "X":
            assert x["tier"] == "D"


def test_implemented_concepts_cite_existing_verification():
    for x in fc.build()["items"]:
        if x["status_code"] in "EN":
            assert x["verification"] != "—", f"{x['id']} {x['concept']}: implemented but no verification"
        if x["verification"] != "—":
            assert (ROOT / x["verification"]).exists(), f"{x['id']}: {x['verification']} does not exist"
        if x["status_code"] in "PX":
            assert x["verification"] == "—" or "live" in x["verification"], f"{x['id']}: not built, so nothing verifies it"


def test_generated_files_are_current():
    cat = fc.build()
    assert json.loads((ROOT / "docs" / "feature_catalogue.json").read_text()) == json.loads(json.dumps(cat, ensure_ascii=False))
    assert (ROOT / "docs" / "FEATURE_CATALOGUE.md").read_text() == fc.markdown(cat) + "\n"
