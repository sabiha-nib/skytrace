"""SKY-CANON-1: one canonical JSON text for data written by either Python or the browser.

Research sessions are written by the server (Python) and by the static preview (JavaScript), and their integrity hash
must agree. Python's `json.dumps` and JavaScript's `JSON.stringify` differ only in how they spell some numbers
(`1e-05` vs `0.00001`, `1e+16` vs `10000000000000000`) and in key order. SKY-CANON-1 fixes both:

* object keys sorted (keys must be ASCII, so code-point and UTF-16 order agree), no whitespace;
* strings escaped exactly as both `json.dumps(..., ensure_ascii=False)` and `JSON.stringify` do (lone surrogates refused);
* numbers spelled as ECMAScript `Number.prototype.toString` spells them (the shortest round-trip digits, which Python's
  `repr` also produces, laid out by the ECMAScript rules); integer-valued numbers limited to ±2^53; NaN and infinities refused.

`web/js/canon.js` implements the same rules; `tests/unit/test_research_session.py` checks they produce identical text and
hashes on a corpus that exercises every rule.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal

METHOD = "SKY-CANON-1"
MAX_SAFE_INT = 2 ** 53
_ASCII_KEY = re.compile(r"^[\x20-\x7e]{1,64}$")


class CanonError(ValueError):
    pass


def js_number(x) -> str:
    """ECMAScript Number::toString(10) for a finite number."""
    if isinstance(x, bool):
        raise CanonError("booleans are not numbers")
    if isinstance(x, int):
        if abs(x) > MAX_SAFE_INT:
            raise CanonError(f"integer {x} is outside ±2^53")
        return str(x)
    if not math.isfinite(x):
        raise CanonError("NaN and infinities are not allowed")
    if x.is_integer() and abs(x) > MAX_SAFE_INT:     # JavaScript cannot tell such a float from an unsafe integer
        raise CanonError(f"integer-valued number {x!r} is outside ±2^53")
    if x == 0:
        return "0"
    if x < 0:
        return "-" + js_number(-x)
    sign, digits, exp = Decimal(repr(x)).as_tuple()
    ds = "".join(map(str, digits)).rstrip("0") or "0"
    exp += len(digits) - len("".join(map(str, digits)).rstrip("0") or "0")
    k = len(ds)
    n = k + exp                         # value = 0.ds × 10^n
    if k <= n <= 21:
        return ds + "0" * (n - k)
    if 0 < n <= 21:
        return ds[:n] + "." + ds[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + ds
    e = n - 1
    es = ("+" if e >= 0 else "-") + str(abs(e))
    return (ds if k == 1 else ds[0] + "." + ds[1:]) + "e" + es


def _string(s: str) -> str:
    for ch in s:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            raise CanonError("lone surrogate in string")
    return json.dumps(s, ensure_ascii=False)


def dumps(obj) -> str:
    """Canonical JSON text (SKY-CANON-1)."""
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, (int, float)):
        return js_number(obj)
    if isinstance(obj, str):
        return _string(obj)
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(dumps(v) for v in obj) + "]"
    if isinstance(obj, dict):
        for k in obj:
            if not isinstance(k, str) or not _ASCII_KEY.match(k):
                raise CanonError(f"object key {k!r} is not 1–64 printable ASCII characters")
        return "{" + ",".join(_string(k) + ":" + dumps(obj[k]) for k in sorted(obj)) + "}"
    raise CanonError(f"type {type(obj).__name__} cannot be serialised")


def digest(obj) -> str:
    return hashlib.sha256(dumps(obj).encode("utf-8")).hexdigest()
