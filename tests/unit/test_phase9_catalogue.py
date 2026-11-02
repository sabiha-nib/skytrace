"""The Phase 9 capability catalogue: 600 distinct concepts in at least 50 domains, every field present, and category A only where
the cited evidence files and the verifying test function exist. B, C and D concepts claim no evidence."""

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["name", "research_problem", "proposed_capability", "scientific_value", "required_data", "dependencies", "complexity", "validation", "risks",
          "category", "status"]


def _cat():
    spec = importlib.util.spec_from_file_location("p9cat", ROOT / "scripts" / "phase9_catalogue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.build()


def test_catalogue_has_600_distinct_concepts_in_50_domains_with_every_field():
    mod, cat = _cat()
    items = cat["items"]
    assert len(items) == 600
    doms = Counter(x["domain"] for x in items)
    assert len(doms) >= 50 and min(doms.values()) >= 1
    assert len({x["name"].lower() for x in items}) == 600
    assert len({x["id"] for x in items}) == 600
    for x in items:
        for f in FIELDS:
            assert x[f], (x["id"], f)
        assert x["category"] in "ABCD" and x["status"] == mod.CATEGORY[x["category"]]
        assert x["complexity"] in ("low", "medium", "high")
    assert cat["counts"]["by_category"] == {f"{k} {v}": sum(1 for x in items if x["category"] == k) for k, v in mod.CATEGORY.items()}


def test_category_a_cites_existing_evidence_and_an_existing_test_and_others_cite_none():
    _, cat = _cat()
    for x in cat["items"]:
        if x["category"] == "A":
            assert x["evidence"], x["id"]
            for e in x["evidence"]:
                assert (ROOT / e).exists(), (x["id"], e)
            f, _, t = x["verification"].partition("::")
            assert (ROOT / f).exists(), (x["id"], f)
            assert t, (x["id"], "an A concept names its verifying test function")
            assert re.search(rf"^\s*def {re.escape(t)}\b", (ROOT / f).read_text(), re.M), (x["id"], t)
        else:
            assert not x["evidence"] and x["verification"] == "—", x["id"]


def test_generated_documents_match_the_script():
    mod, cat = _cat()
    assert json.loads((ROOT / "docs" / "phase9_catalogue.json").read_text()) == cat
    md = (ROOT / "docs" / "PHASE9_CATALOGUE.md").read_text()
    assert md == mod.markdown(cat) + "\n"
    assert "roadmap, not a build list" in md
