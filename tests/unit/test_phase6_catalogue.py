"""The Phase 6 catalogue covers the brief's 300 concepts in 30 domains, merges synonyms, and cites real evidence and tests."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import phase6_catalogue as pc  # noqa: E402


def test_shape_and_counts():
    cat = pc.build()
    c = cat["counts"]
    assert c["domains"] == 30 and c["brief_concepts"] == 300 and c["distinct"] >= 300
    assert sorted(x["number"] for x in cat["items"] if x["source"] == "brief") == list(range(1, 301))
    ids = [x["id"] for x in cat["items"]]
    assert len(ids) == len(set(ids))
    names = [x["concept"].lower() for x in cat["items"]]
    assert len(names) == len(set(names)), "duplicate concept name"
    for x in cat["items"]:
        assert x["status_code"] in pc.STATUS and x["group"] in pc.GROUP.values(), x["id"]
        if x["source"] == "brief":
            assert x["domain"] == pc.DOMAINS[(x["number"] - 1) // 10]
    assert sum(c["by_status"].values()) == c["distinct"] == c["rows"] - c["merged_synonyms"]


def test_synonyms_point_to_counted_concepts():
    items = {x["id"]: x for x in pc.build()["items"]}
    for x in items.values():
        if x["duplicate_of"]:
            target = items[x["duplicate_of"]]
            assert not target["duplicate_of"], f"{x['id']} → {target['id']} is itself merged"


def _test_exists(ref: str) -> bool:
    path, _, name = ref.partition("::")
    p = ROOT / path
    if not p.exists():
        return False
    return not name or re.search(rf"^def {re.escape(name)}\b", p.read_text(), re.M) is not None


def test_implemented_concepts_cite_existing_evidence_and_tests():
    for x in pc.build()["items"]:
        if x["duplicate_of"]:
            continue
        if x["status_code"] in "EN":
            assert x["evidence"], f"{x['id']}: implemented but no evidence"
            assert x["verification"] != "—", f"{x['id']}: implemented but no verification"
        for p in x["evidence"]:
            assert (ROOT / p).exists(), f"{x['id']}: {p} does not exist"
        if x["verification"] != "—":
            assert _test_exists(x["verification"]), f"{x['id']}: {x['verification']} not found"
        if x["status_code"] in "DX":
            assert x["verification"] == "—" and not x["evidence"], f"{x['id']}: not built, so nothing verifies it"
            assert x["limitations"], f"{x['id']}: a deferred or out-of-scope concept must say why"
        if x["status_code"] == "B":
            assert "blocked" in x["limitations"].lower()


def test_generated_files_are_current():
    cat = pc.build()
    assert json.loads((ROOT / "docs" / "phase6_catalogue.json").read_text()) == json.loads(json.dumps(cat, ensure_ascii=False))
    assert (ROOT / "docs" / "PHASE6_CATALOGUE.md").read_text() == pc.markdown(cat) + "\n"
