"""Gate E smoke test for the Meta Model API. Records results to data/meta_smoke_test.json.

Steps: list models -> plain completion -> structured JSON -> one tool call.
Requires META_API_KEY in the environment. Prints and records failures verbatim.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace.ai.meta_client import MetaAPIError, MetaClient, MetaUnavailable  # noqa: E402
from skytrace.provenance import utc_now_iso  # noqa: E402


def step(name, fn, results):
    t0 = time.time()
    try:
        out = fn()
        results.append({"step": name, "ok": True, "seconds": round(time.time() - t0, 2), "output": out})
    except (MetaAPIError, MetaUnavailable, Exception) as e:
        results.append({"step": name, "ok": False, "seconds": round(time.time() - t0, 2), "error": f"{type(e).__name__}: {e}"})


def main() -> int:
    results: list[dict] = []
    try:
        c = MetaClient()
    except MetaUnavailable as e:
        print(f"not run: {e}")
        return 2
    step("list_models", lambda: c.list_models(), results)
    step("chat_plain", lambda: c.chat([{"role": "user", "content": "Reply with the single word: ready"}]), results)
    step("chat_json", lambda: c.chat(
        [{"role": "user", "content": 'Return {"ok": true} as JSON.'}],
        response_format={"type": "json_object"}), results)
    tool = {"type": "function", "function": {"name": "get_observation_count", "description": "Number of observations",
                                             "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}
    step("chat_tool_call", lambda: c.chat(
        [{"role": "user", "content": "How many observations are there? Use the tool."}], tools=[tool]), results)
    out = {"run_at": utc_now_iso(), "base_url": c.cfg.base_url, "model": c.cfg.model, "results": results}
    p = ROOT / "data" / "meta_smoke_test.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str))
    for r in results:
        print(f"{'PASS' if r['ok'] else 'FAIL'} {r['step']} ({r['seconds']}s) {r.get('error', '')}")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
