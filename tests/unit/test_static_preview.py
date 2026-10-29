"""Static preview: the browser port of pair_comparison must equal the Python method for every pair."""

import itertools
import json
import math
import shutil
import subprocess

import pytest

from test_report_ai import view

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
NODE = shutil.which("node")


def _same(x, y, path=""):
    if isinstance(x, float) and math.isnan(x):
        x = None
    if isinstance(x, dict):
        assert isinstance(y, dict) and set(x) == set(y), (path, set(x) ^ set(y or {}))
        for k in x:
            _same(x[k], y[k], f"{path}.{k}")
    elif isinstance(x, (list, tuple)):
        assert len(x) == len(y), path
        for i, (a, b) in enumerate(zip(x, y)):
            _same(a, b, f"{path}[{i}]")
    elif isinstance(x, float) or isinstance(y, float):
        assert y is not None and x is not None and abs(x - y) <= 1e-12 * max(1.0, abs(x)), (path, x, y)
    else:
        assert x == y, (path, x, y)


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("tid", ["syn-hpm-1", "syn-var-1"])
def test_js_pair_comparison_matches_python(tid, tmp_path):
    v = view(tid)
    keys = sorted(v.measure_events)               # includes failed measurements (no centroid)
    pairs = list(itertools.combinations(keys, 2)) + [(keys[3], keys[1]), (keys[0], keys[0])]
    inp = {"measurements": {k: v.measure_events[k]["data"] for k in keys}, "params": v.r["parameters"],
           "flux_pairs": v.flux_pairs(), "pairs": pairs}
    f = tmp_path / "in.json"
    f.write_text(json.dumps(inp))
    r = subprocess.run([NODE, str(ROOT / "tests/js/pair_parity.mjs"), str(f), str(ROOT / "web/js/static/compare.js")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    assert len(js) == len(pairs)
    for (a, b), got in zip(pairs, js):
        _same(json.loads(json.dumps(v.pair_comparison(a, b))), got, f"{a}|{b}")


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("tid", ["syn-hpm-1", "syn-var-1"])
def test_js_content_hash_matches_python(tid, tmp_path):
    """The browser recomputes the record hash exactly as Python's stable_hash, and detects any edit."""
    from test_report_ai import _record
    rec = json.loads(_record(tid))
    run = lambda path: json.loads(subprocess.run([NODE, str(ROOT / "tests/js/record_hash.mjs"), str(path),
                                                  str(ROOT / "web/js/static/hash.js")], capture_output=True, text=True,
                                                 timeout=120, check=True).stdout)
    f = tmp_path / "rec.json"
    f.write_text(json.dumps(rec, indent=1))          # the server's export format
    r = run(f)
    assert r["ok"] and r["computed"] == rec["content_hash"]
    rec["events"][3]["detail"] += " (edited)"
    f.write_text(json.dumps(rec, indent=1))
    assert not run(f)["ok"]
    rec["events"][3]["detail"] = rec["events"][3]["detail"].replace(" (edited)", "")
    rec["parameters"]["aperture_radius_px"] = 2.0000001
    f.write_text(json.dumps(rec, indent=1))
    assert not run(f)["ok"]
