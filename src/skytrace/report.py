"""Investigation log and evidence-backed reports.

The log records every step that actually ran, including rejected observations
and failed measurements. Reports are generated only from the log, never
written freehand, so every number in a report traces to a logged result.
"""

from __future__ import annotations

import json
import math
import platform
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from . import __version__
from .provenance import Provenance, stable_hash, utc_now_iso

SCHEMA_VERSION = "skytrace.investigation/1"


def _jsonable(o: Any):
    if is_dataclass(o):
        return _jsonable(asdict(o))
    if isinstance(o, Provenance):
        return o.to_dict()
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None  # NaN/inf become explicit nulls (missing), never zero
    if hasattr(o, "item"):
        return _jsonable(o.item())
    return o


@dataclass
class Event:
    step: str
    status: str          # "ok", "rejected", "failed", "skipped", "info"
    detail: str
    data: dict = field(default_factory=dict)
    provenance: list[dict] = field(default_factory=list)


@dataclass
class Investigation:
    target: str
    parameters: dict
    events: list[Event] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    def log(self, step: str, status: str, detail: str, data: dict | None = None,
            provenance: list[Provenance] | None = None) -> None:
        self.events.append(Event(step, status, detail, _jsonable(data or {}),
                                 [p.to_dict() for p in (provenance or [])]))

    def to_dict(self) -> dict:
        body = {
            "schema": SCHEMA_VERSION,
            "target": self.target,
            "parameters": _jsonable(self.parameters),
            "events": [_jsonable(e) for e in self.events],
            "software": {"skytrace": __version__, "python": platform.python_version(), **_versions()},
            "created_at": self.created_at,
        }
        body["content_hash"] = stable_hash({k: v for k, v in body.items() if k not in ("created_at", "software")})
        return body

    def data_origins(self) -> set[str]:
        return {p["origin"] for e in self.events for p in e.provenance}


def _versions() -> dict:
    out = {}
    for mod in ("numpy", "scipy", "astropy"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            out[mod] = None
    return out


def render_markdown(inv: Investigation) -> str:
    d = inv.to_dict()
    origins = sorted(inv.data_origins())
    lines = [f"# Investigation: {inv.target}", ""]
    if "synthetic" in origins:
        lines += ["> **SYNTHETIC DATA.** This report was produced from generated test images. "
                  "It is a software test, not an astronomical result.", ""]
    if "fixture" in origins:
        lines += ["> Contains **fixture** data (committed demo files), not a live archive retrieval.", ""]
    lines += [f"- Data origins: {', '.join(origins) or 'none recorded'}",
              f"- Content hash: `{d['content_hash']}`",
              f"- Software: skytrace {d['software']['skytrace']}, numpy {d['software']['numpy']}, "
              f"scipy {d['software']['scipy']}, astropy {d['software']['astropy']}",
              "", "## Parameters", "", "```json", json.dumps(d["parameters"], indent=2, sort_keys=True), "```",
              "", "## Steps", "", "| # | Step | Status | Detail |", "|---|---|---|---|"]
    for i, e in enumerate(d["events"], 1):
        lines.append(f"| {i} | {e['step']} | {e['status']} | {e['detail'].replace('|', '/')} |")
    rejected = [e for e in d["events"] if e["status"] in ("rejected", "failed")]
    lines += ["", f"## Rejected or failed ({len(rejected)})", ""]
    lines += [f"- **{e['step']}**: {e['detail']}" for e in rejected] or ["- none"]
    lines += ["", "## Sources", ""]
    seen = set()
    for e in d["events"]:
        for p in e["provenance"]:
            key = (p["source"], p["source_url"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {p['source']} [{p['origin']}] {p.get('release') or ''} {p.get('dataset_id') or ''} "
                         f"retrieved {p['retrieved_at']}: {p['source_url'] or '(derived)'}")
    if not seen:
        lines.append("- none")
    return "\n".join(lines) + "\n"
