"""The Phase 10 innovation catalogue: 800 distinct ideas in at least 60 domains, the ten requested fields on every idea, and class A
only where the cited evidence files and the verifying test function exist. B, C and D ideas claim no evidence."""

import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["name", "scientific_problem", "user_value", "technical_design", "required_inputs", "dependencies", "complexity", "scientific_limitations",
          "validation_strategy", "implementation_status"]


def _cat():
    spec = importlib.util.spec_from_file_location("p10cat", ROOT / "scripts" / "phase10_catalogue.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.build()


def test_catalogue_has_800_distinct_ideas_in_60_domains_with_every_field():
    cat = _cat()
    items = cat["items"]
    assert len(items) == 800 and cat["fields"] == FIELDS
    assert len(Counter(x["domain"] for x in items)) >= 60
    assert len({x["name"].lower() for x in items}) == 800 and len({x["id"] for x in items}) == 800
    for x in items:
        for f in FIELDS:
            assert x[f], (x["id"], f)
        assert x["class"] in "ABCD" and x["implementation_status"] == cat["classes"][x["class"]]
        assert x["complexity"] in ("low", "medium", "high")
    assert cat["counts"]["new_in_phase10"] == 200


def test_class_a_cites_existing_evidence_and_tests_and_others_claim_nothing():
    for x in _cat()["items"]:
        if x["class"] == "A":
            assert x["evidence"], x["id"]
            for e in x["evidence"]:
                assert (ROOT / e).exists(), (x["id"], e)
            f, _, fn = x["verification"].partition("::")
            assert (ROOT / f).exists() and f"def {fn}(" in (ROOT / f).read_text(), (x["id"], x["verification"])
        else:
            assert x["evidence"] == [] and x["verification"] == "—", x["id"]


def test_no_idea_claims_semantics_probabilities_or_novelty_it_does_not_have():
    for x in _cat()["items"]:
        if x["class"] == "A":
            text = " ".join(str(x[f]) for f in ("name", "technical_design", "user_value")).lower().replace("no semantic search", "")
            assert "semantic search" not in text and "globally novel" not in text and "false-alarm probability" not in text.replace("no false-alarm probability", "")
