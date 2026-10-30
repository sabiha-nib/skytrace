"""SKY-CANON-1, SCHEMA-1 and SESSION-1: identical in Python and the browser; integrity, validation, migration."""

import copy
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from skytrace import canon, schema, session

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")


def corpus_numbers():
    rnd = random.Random(7)
    xs = [0.0, -0.0, 1.0, -1.0, 0.1, 0.5, 2.5, 1e-7, 1e-6, 1.5e-6, 1e-5, 0.000123, 123456789.0, 1e15, 1e16, 1e20, 1e21, 1.5e21,
          1e22, 1e-300, 5e-324, 1.7976931348623157e308, 123.456, -987.654321, 2 ** 53, -(2 ** 53), 3, -7]
    xs += [rnd.uniform(-1, 1) * 10 ** rnd.randint(-12, 25) for _ in range(400)]
    xs += [float(rnd.randint(-10 ** 6, 10 ** 6)) / rnd.choice([1, 3, 7, 1000, 2 ** 10]) for _ in range(200)]
    return xs


def corpus_values():
    return [None, True, False, "", "plain", "quote \" backslash \\ tab \t newline \n cr \r ctrl \u0001 \u001f del \x7f",
            "unicode µm Δλ — 中文 😀    ", {"b": 1, "a": [1, 2.5, {"z": None, "y": "x"}]}, [], {},
            {"key with space": 1, "A": 2, "a": 3, "_": 4, "~": 5}, {"non-ascii-key-µ": 1}, "lone \ud800 surrogate",
            {"n": float("nan")} if False else {"n": 1e-7}, [1e21, 1e-7, 123e-20]]


def session_samples():
    s = session.new("Test session", "syn-var-1", at="2026-10-30T10:00:00+00:00")
    good = copy.deepcopy(s)
    good["question"] = {"id": "Q-VAR", "text": "Did it change?"}
    good["runs"] = [{"investigation_id": "abc123", "content_hash": "a" * 64, "label": "default", "attached_at": "2026-10-30T10:01:00+00:00",
                     "params": {"aperture_radius_px": 2.5, "apply_parallax": True}}]
    good["active_hash"] = "a" * 64
    good["notebook"] = [{"id": "n1", "type": "paragraph", "text": "Note µ 😀", "author": "user",
                         "created_at": "2026-10-30T10:02:00+00:00", "modified_at": "2026-10-30T10:02:00+00:00"},
                        {"id": "n2", "type": "observation", "ref": {"kind": "observation", "id": "SYNTHETIC:SYN11_23:D1"}, "author": "user",
                         "created_at": "2026-10-30T10:02:00+00:00", "modified_at": "2026-10-30T10:02:00+00:00"}]
    good["plans"] = [{"id": "p1", "question": "q", "created_at": "2026-10-30T10:03:00+00:00", "revision": 1, "confirmed": False,
                      "intent": {"kind": "change_brightness", "keys": []},
                      "steps": [{"id": "s1", "capability": "run_analysis", "status": "completed", "depends": [], "title": "Run",
                                 "result": {"content_hash": "a" * 64, "n_pairs": 46, "ok": True, "x": 1e-7}},
                                {"id": "s2", "capability": "evaluate_hypotheses", "status": "ready", "depends": ["s1"], "title": "Test"}]}]
    good["experiments"] = [{"id": "e1", "template": "reproducibility", "created_at": "2026-10-30T10:04:00+00:00", "status": "completed",
                            "config": {"target": "syn-var-1"}, "result": {"identical": True, "hashes": ["a" * 64, "a" * 64]}}]
    good = session.log(good, "question.set", "Question set", "Q-VAR", at="2026-10-30T10:05:00+00:00")
    good["modified_at"] = "2026-10-30T10:05:00+00:00"
    good = session.finalize(good)
    tampered = copy.deepcopy(good)
    tampered["name"] = "renamed without rehashing"
    bad_dep = copy.deepcopy(good)
    bad_dep["plans"][0]["steps"][0]["depends"] = ["s2"]
    bad_dep = session.finalize(bad_dep)
    bad_field = copy.deepcopy(good)
    bad_field["surprise"] = 1
    bad_schema = dict(good, schema="skytrace.research_session/9")
    bad_active = session.finalize(dict(good, active_hash="b" * 64))
    bad_seq = copy.deepcopy(good)
    bad_seq["history"][1]["seq"] = 1
    bad_seq = session.finalize(bad_seq)
    no_hash = {k: v for k, v in good.items() if k != "content_hash"}
    return [good, tampered, bad_dep, bad_field, bad_schema, bad_active, bad_seq, no_hash, "not an object"]


def py_canon(v):
    try:
        return canon.dumps(v)
    except canon.CanonError:
        return "ERR"


def test_js_number_rules():
    assert [canon.js_number(x) for x in (0.0, -0.0, 1e-7, 1e-6, 1.5, 100.0, 2 ** 53, 1e-5, 123e-20, 1.5e300 / 1e290, 0.1 + 0.2)] == \
        ["0", "0", "1e-7", "0.000001", "1.5", "100", "9007199254740992", "0.00001", "1.23e-18", "15000000000", "0.30000000000000004"]
    assert canon.js_number(1.25e-7) == "1.25e-7" and canon.js_number(1.2345e-3) == "0.0012345"
    for bad in (float("nan"), float("inf"), 2 ** 53 + 1, 1e21):
        with pytest.raises(canon.CanonError):
            canon.js_number(bad)


def test_canon_refusals_and_order():
    assert canon.dumps({"b": 1, "a": {"d": [True, None], "c": "x"}}) == '{"a":{"c":"x","d":[true,null]},"b":1}'
    for bad in ({"µ": 1}, "\ud800", {"x": float("nan")}, {1: 2}, {"x": object()}):
        with pytest.raises(canon.CanonError):
            canon.dumps(bad)


def test_session_new_validates_and_hashes():
    s = session.new("A", "syn-var-1")
    assert session.validate(s) == []
    v = session.verify(s)
    assert v["valid"] and v["hash_ok"] is True
    s2 = dict(s, name="B")
    assert session.verify(s2)["hash_ok"] is False


def test_session_rules():
    good, tampered, bad_dep, bad_field, bad_schema, bad_active, bad_seq, no_hash, notobj = session_samples()
    assert session.verify(good)["hash_ok"] is True
    assert session.verify(tampered)["hash_ok"] is False
    assert any("do not precede" in e for e in session.validate(bad_dep))
    assert any("unknown field 'surprise'" in e for e in session.validate(bad_field))
    assert "not a supported session format" in session.validate(bad_schema)[0]
    assert any("active_hash" in e for e in session.validate(bad_active))
    assert any("sequence numbers" in e for e in session.validate(bad_seq))
    assert session.verify(no_hash)["hash_ok"] is None and session.verify(no_hash)["valid"]
    assert session.validate(notobj)


def test_migration_from_v05_saved_record():
    saved = {"record_id": "r1", "name": "old", "target_id": "syn-var-1", "investigation_id": "iid1", "content_hash": "c" * 64,
             "parameters": {"aperture_radius_px": 2.0, "detectors": [1, 2], "bundle": "syn-var-1", "apply_parallax": True},
             "context": {"question": "Q-MOT", "question_text": "Does it move?",
                         "hypotheses": [{"id": "U1", "statement": "real motion", "tests": ["M-REGISTRATION/T-REG"], "created_at": "2026-10-29T01:02:03.000Z"},
                                        {"statement": ""}, "junk"]}}
    s = session.from_saved_record(saved)
    assert session.validate(s) == [] and session.verify(s)["hash_ok"]
    assert s["question"]["id"] == "Q-MOT" and len(s["hypotheses"]) == 1 and s["runs"][0]["content_hash"] == "c" * 64
    assert "detectors" not in s["runs"][0]["params"] and "bundle" not in s["runs"][0]["params"]
    assert s["history"][-1]["kind"] == "session.migrate"


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_matches_python(tmp_path):
    vals, nums = corpus_values(), corpus_numbers()
    checks = [[session.SESSION_SCHEMA, s] for s in session_samples() if isinstance(s, dict)]
    checks += [[schema.S(5, 2, r"^[a-z]+$"), x] for x in ("ab", "a", "abcdef", "AB", 3, "µµ")]
    checks += [[schema.INT(0, 10), x] for x in (0, 10, 11, 2.5, True, "1", float("inf") if False else -1)]
    checks += [[{"t": "json", "max_bytes": 30, "depth": 2}, x] for x in ({"a": [1]}, {"a": {"b": {"c": 1}}}, "x" * 40, {"µ": 1})]
    job = {"canon": vals, "numbers": nums, "checks": checks, "session_schema": session.SESSION_SCHEMA,
           "sessions": [s for s in session_samples()]}
    f = tmp_path / "job.json"
    f.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/session_parity.mjs"), str(ROOT), str(f)], capture_output=True, text=True, timeout=60, check=True)
    js = json.loads(r.stdout)
    assert js["canon"] == [py_canon(v) for v in vals]
    assert js["numbers"] == [py_canon(x) for x in nums]
    assert js["hashes"] == [canon.digest(v) if py_canon(v) != "ERR" else "ERR" for v in vals]
    assert js["checks"] == [schema.check(spec, v) for spec, v in checks]
    py_sessions = [session.verify(s) for s in job["sessions"]]
    for a, b in zip(js["sessions"], py_sessions):
        assert a == b
