"""Minimal IVOA TAP (synchronous ADQL) and VOTable helpers.

Uses the standard TAP sync interface (REQUEST=doQuery, LANG=ADQL) with CSV
output, so it needs no astronomy libraries. VOTable parsing prefers
astropy.io.votable when installed and otherwise reads TABLEDATA-encoded
VOTables with the standard library.
"""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET

from .net import Fetcher, FetchResult


def validate_csv(content: bytes) -> None:
    head = content[:2048].decode("utf-8", "replace").lstrip()
    if not head or head.startswith("<"):
        raise ValueError("expected CSV, got XML/HTML (likely a service error page)")


def tap_sync(fetcher: Fetcher, base_url: str, adql: str, *, source: str, dataset_id: str = "",
             release: str = "", max_rec: int = 20000) -> tuple[list[dict], FetchResult]:
    res = fetcher.get(base_url.rstrip("/") + "/sync",
                      {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                       "MAXREC": str(max_rec), "QUERY": " ".join(adql.split())},
                      source=source, kind="metadata", release=release, dataset_id=dataset_id,
                      validate=validate_csv)
    return parse_csv(res.content), res


def _num(v: str):
    if v is None:
        return None
    s = v.strip()
    if s == "":
        return None
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    return s


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8")
    return [{k: _num(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO(text))]


def validate_votable(content: bytes) -> None:
    if b"VOTABLE" not in content[:4096].upper():
        raise ValueError("response is not a VOTable")
    root = ET.fromstring(content)
    for el in root.iter():
        if el.tag.endswith("INFO") and el.get("name") == "QUERY_STATUS" and el.get("value") == "ERROR":
            raise ValueError(f"service reported an error: {(el.text or '').strip()}")


def parse_votable(content: bytes) -> list[dict]:
    try:
        from astropy.io.votable import parse_single_table  # type: ignore
        t = parse_single_table(io.BytesIO(content)).to_table()
        rows = [dict() for _ in range(len(t))]
        for c in t.colnames:
            col = t[c]
            mask = getattr(col, "mask", None)
            for i in range(len(t)):
                masked = mask is not None and bool(mask[i] if mask.shape else mask)
                rows[i][c] = None if masked else _py(col[i])
        return rows
    except ImportError:
        pass
    root = ET.fromstring(content)
    ns = lambda tag: [e for e in root.iter() if e.tag.split("}")[-1] == tag]
    fields = [f.get("name") for f in ns("FIELD")]
    if ns("BINARY") or ns("BINARY2") or ns("FITS"):
        raise ValueError("binary-encoded VOTable needs astropy to parse")
    rows = []
    for tr in ns("TR"):
        cells = [td.text for td in tr if td.tag.split("}")[-1] == "TD"]
        rows.append({f: _num(c) if c is not None else None for f, c in zip(fields, cells)})
    return rows


def _py(v):
    try:
        return v.item()
    except AttributeError:
        return v.decode() if isinstance(v, bytes) else v
