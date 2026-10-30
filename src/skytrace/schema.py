"""SCHEMA-1: a small declarative schema language, interpreted identically in Python and the browser.

Persisted structures that both sides write (research sessions, notebook blocks, plans, workflows) are described once,
as data, and checked by this interpreter here and by `web/js/schema.js` in the browser. The schema documents travel
with the application (`GET /api/schemas`, `data/schemas.json` in the static preview), so there is one source of truth.

Spec forms:
  {"t": "obj", "f": {name: [spec, required]}, "extra": false}
  {"t": "arr", "items": spec, "max": n}            {"t": "map", "keys": regex, "values": spec, "max": n}
  {"t": "str", "min": n, "max": n, "re": regex, "enum": [...]}
  {"t": "num", "min": x, "max": x}  {"t": "int", "min": n, "max": n}  {"t": "bool"}  {"t": "null"}
  {"t": "const", "v": value}  {"t": "any", "of": [spec, ...]}  {"t": "json", "max_bytes": n, "depth": n}
Regexes use only syntax common to Python `re` and JavaScript (anchored character classes and counts).
"""

from __future__ import annotations

import math
import re

from . import canon

METHOD = "SCHEMA-1"


def _depth(v, d=0):
    if isinstance(v, dict):
        return max([_depth(x, d + 1) for x in v.values()] or [d + 1])
    if isinstance(v, list):
        return max([_depth(x, d + 1) for x in v] or [d + 1])
    return d


def check(spec: dict, v, path: str = "$") -> list[str]:
    """All violations as 'path: message' strings (empty list = valid)."""
    t = spec["t"]
    if t == "any":
        errs = [check(s, v, path) for s in spec["of"]]
        return [] if any(not e for e in errs) else [f"{path}: matches none of the allowed forms"]
    if t == "const":
        return [] if v == spec["v"] and type(v) is type(spec["v"]) else [f"{path}: must be {spec['v']!r}"]
    if t == "null":
        return [] if v is None else [f"{path}: must be null"]
    if t == "bool":
        return [] if isinstance(v, bool) else [f"{path}: must be true or false"]
    if t in ("num", "int"):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v, float) and not math.isfinite(v)):
            return [f"{path}: must be a finite number"]
        if t == "int" and not (isinstance(v, int) or float(v).is_integer()):
            return [f"{path}: must be an integer"]
        if "min" in spec and v < spec["min"]:
            return [f"{path}: must be ≥ {spec['min']}"]
        if "max" in spec and v > spec["max"]:
            return [f"{path}: must be ≤ {spec['max']}"]
        return []
    if t == "str":
        if not isinstance(v, str):
            return [f"{path}: must be text"]
        n = len(v.encode("utf-16-le")) // 2         # JavaScript string length (UTF-16 code units)
        if n < spec.get("min", 0):
            return [f"{path}: must have at least {spec.get('min', 0)} characters"]
        if "max" in spec and n > spec["max"]:
            return [f"{path}: must have at most {spec['max']} characters"]
        if "enum" in spec and v not in spec["enum"]:
            return [f"{path}: must be one of {', '.join(spec['enum'])}"]
        if "re" in spec and not re.search(spec["re"], v):
            return [f"{path}: has an invalid format"]
        return []
    if t == "arr":
        if not isinstance(v, list):
            return [f"{path}: must be a list"]
        if "max" in spec and len(v) > spec["max"]:
            return [f"{path}: must have at most {spec['max']} items"]
        out = []
        for i, x in enumerate(v):
            out += check(spec["items"], x, f"{path}[{i}]")
        return out
    if t == "map":
        if not isinstance(v, dict):
            return [f"{path}: must be an object"]
        if "max" in spec and len(v) > spec["max"]:
            return [f"{path}: must have at most {spec['max']} entries"]
        out = []
        for k in sorted(v):
            if not re.search(spec["keys"], k):
                out.append(f"{path}: key {k!r} has an invalid format")
            else:
                out += check(spec["values"], v[k], f"{path}.{k}")
        return out
    if t == "obj":
        if not isinstance(v, dict):
            return [f"{path}: must be an object"]
        out = []
        for k in sorted(v):
            if k not in spec["f"] and not spec.get("extra", False):
                out.append(f"{path}: unknown field {k!r}")
        for k, (s, req) in sorted(spec["f"].items()):
            if k in v:
                out += check(s, v[k], f"{path}.{k}")
            elif req:
                out.append(f"{path}: missing field {k!r}")
        return out
    if t == "json":
        try:
            text = canon.dumps(v)
        except canon.CanonError as e:
            return [f"{path}: {e}"]
        if len(text.encode("utf-8")) > spec.get("max_bytes", 20000):
            return [f"{path}: larger than {spec.get('max_bytes', 20000)} bytes"]
        if _depth(v) > spec.get("depth", 6):
            return [f"{path}: nested deeper than {spec.get('depth', 6)} levels"]
        return []
    raise ValueError(f"unknown schema type {t!r}")


# ------------------------------------------------------------------ small constructors used by the schemas
def S(max_=None, min_=0, re_=None, enum=None):
    d = {"t": "str", "min": min_}
    if max_ is not None:
        d["max"] = max_
    if re_:
        d["re"] = re_
    if enum:
        d["enum"] = list(enum)
    return d


def O(fields: dict, extra=False):
    return {"t": "obj", "f": {k: [v[0], v[1]] for k, v in fields.items()}, "extra": extra}


def A(items, max_):
    return {"t": "arr", "items": items, "max": max_}


def OPT(spec):
    return {"t": "any", "of": [spec, {"t": "null"}]}


INT = lambda lo, hi: {"t": "int", "min": lo, "max": hi}  # noqa: E731
NUM = lambda lo, hi: {"t": "num", "min": lo, "max": hi}  # noqa: E731
BOOL = {"t": "bool"}
ISO = S(40, 10, r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.+Z-]{5,30}$")
HEX64 = S(64, 64, r"^[0-9a-f]{64}$")
ID = S(40, 1, r"^[A-Za-z0-9_.:-]{1,40}$")
