"""The Phase 8 catalogue covers the brief's 500 concepts in 50 domains, merges synonyms, cites real evidence, tests and
Phase 7 entries, and never counts an existing capability as new."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import phase8_catalogue as pc  # noqa: E402

P7 = {x["id"]: x for x in json.loads((ROOT / "docs" / "phase7_catalogue.json").read_text())["items"]}


def test_shape_and_counts():
    cat = pc.build()
    c = cat["counts"]
    assert c["domains"] == 50 and c["brief_concepts"] == 500 and c["distinct"] >= 500
    assert sorted(x["number"] for x in cat["items"] if x["source"] == "brief") == list(range(1, 501))
    ids = [x["id"] for x in cat["items"]]
    assert len(ids) == len(set(ids))
    names = [x["name"].lower() for x in cat["items"]]
    assert len(names) == len(set(names)), "duplicate concept name"
    for x in cat["items"]:
        assert x["status_code"] in pc.STATUS and x["group"] in pc.GROUP.values(), x["id"]
        if x["source"] == "brief":
            assert x["domain"] == pc.DOMAINS[(x["number"] - 1) // 10]
        for f in ("description", "user_value", "scientific_value", "status", "priority", "verification"):
            assert x[f], f"{x['id']}: missing {f}"
    assert sum(c["by_status"].values()) == c["distinct"] == c["rows"] - c["merged_synonyms"]


def test_existing_concepts_cite_real_phase7_entries_and_new_ones_do_not():
    for x in pc.build()["items"]:
        if x["duplicate_of"]:
            continue
        if x["phase7"]:
            assert x["phase7"] in P7, f"{x['id']} cites unknown Phase 7 entry {x['phase7']}"
            assert P7[x["phase7"]]["status_code"] in "EN", f"{x['id']} carries a Phase 7 entry that was not implemented"
            assert x["status_code"] == "E", f"{x['id']}: a Phase 7 capability is existing, not new"
        if x["status_code"] == "N":
            assert not x["phase7"], f"{x['id']}: new in 0.8 but cites Phase 7"


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
    return not name or re.search(rf"^(async )?def {re.escape(name)}\b", p.read_text(), re.M) is not None


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
        if x["status_code"] in "DXB":
            assert x["verification"] == "—" and not x["evidence"], f"{x['id']}: not built, so nothing verifies it"
            assert x["limitations"], f"{x['id']}: a deferred, blocked or out-of-scope concept must say why"
        if x["status_code"] == "B":
            assert "blocked" in x["limitations"].lower()


def test_generated_files_are_current():
    cat = pc.build()
    assert json.loads((ROOT / "docs" / "phase8_catalogue.json").read_text()) == json.loads(json.dumps(cat, ensure_ascii=False))
    assert (ROOT / "docs" / "PHASE8_CATALOGUE.md").read_text() == pc.markdown(cat) + "\n"
