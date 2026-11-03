"""HANDOFF-1: the discovery handoff protocol — a versioned JSON document that passes recorded work to another researcher.

Schema ``skytrace.handoff/1`` (version "1.0"). It states what was established (rule-based outcomes, verbatim), what is open
(research leads and unresolved explanations), what is unknown (negative-space distinctions), the evidence that would help
(opportunities with their novelty scope), provenance, limitations and how to reproduce the record, together with language
metadata: the interface language the handoff was prepared in, the language of the scientific content (English, the language
the engines record in) and the translation status. ``digest`` is the SKY-CANON-1 SHA-256 of the document without it.

Import validates structure, types, the language metadata, the synthetic label against the provenance and the digest. An
imported handoff describes recorded work; it never counts as a reproduction and implies no live collaboration.
Ported to web/js/handoff.js (parity-tested).
"""

from __future__ import annotations

import json
import re

from . import canon

SCHEMA = "skytrace.handoff/1"
VERSIONS = ["1.0"]
LANGS = ["en", "bn", "hi", "es", "fr", "de"]
NOTE = ("This handoff describes recorded work. It implies no live collaboration; importing it is not a reproduction, and a "
        "reproduction shows that a calculation repeats, not that its conclusion is true.")
REQUIRED = {"schema": str, "version": str, "created_at": str, "generator": dict, "language": dict, "investigation": dict, "established": list,
            "open": list, "unknown": list, "evidence_needed": list, "provenance": list, "limitations": list, "reproduction": dict, "note": str, "digest": str}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
MAX_ITEMS = 200


def build(rec: dict, uni: dict, lang: str, meta: dict, created_at: str, version: str) -> dict:
    outs = [e for e in rec["events"] if e["step"] == "assess"]
    outcomes = ((outs[0].get("data") or {}).get("outcomes") or []) if outs else []
    prov, seen = [], set()
    for e in rec["events"]:
        for p in e.get("provenance") or []:
            k = (p.get("source"), p.get("content_sha256"))
            if k in seen:
                continue
            seen.add(k)
            prov.append({"source": p.get("source") or "", "origin": p.get("origin") or "", "release": p.get("release") or "",
                         "retrieved_at": p.get("retrieved_at") or "", "content_sha256": p.get("content_sha256") or ""})
    synthetic = any(p["origin"] == "synthetic" for p in prov)
    neg = uni.get("negative") or {}
    doc = {
        "schema": SCHEMA, "version": VERSIONS[-1], "created_at": created_at,
        "generator": {"software": "skytrace", "version": version},
        "language": {"interface": lang if lang in LANGS else "en", "content": "en",
                     "translation": {"status": meta.get("status") or "source language", "translator": meta.get("translator") or "", "reviewed": bool(meta.get("reviewed"))}},
        "investigation": {"target": rec.get("target") or "", "content_hash": rec.get("content_hash") or "", "synthetic": synthetic,
                          "record_schema": rec.get("schema") or ""},
        "established": [{"question": o.get("question") or "", "category": o.get("category") or "", "statement": o.get("statement") or "", "rule": "ASSESS-2"}
                        for o in outcomes][:MAX_ITEMS],
        "open": ([{"id": l["id"], "kind": l["kind"], "statement": l["statement"]} for l in (uni.get("leads") or {}).get("leads") or []]
                 + [{"id": f"NEG-{i}", "kind": "unresolved explanation", "statement": x["statement"]}
                    for i, x in enumerate(neg.get("items") or []) if x["distinction"] == "unresolved explanation"])[:MAX_ITEMS],
        "unknown": [{"distinction": x["distinction"], "statement": x["statement"], "does_not_mean": x["does_not_mean"]}
                    for x in neg.get("items") or [] if x["distinction"] in ("unknown quantity", "unexplored region", "insufficient sensitivity", "unavailable dataset")][:MAX_ITEMS],
        "evidence_needed": [{"question": i["question"] or "", "data_needed": i["data_needed"] or "", "novelty_scope": i["novelty"]["scope"]}
                            for i in (uni.get("opportunities") or {}).get("items") or []][:MAX_ITEMS],
        "provenance": prov[:MAX_ITEMS],
        "limitations": sorted({lim for o in outcomes for lim in o.get("limitations") or []})[:MAX_ITEMS],
        "reproduction": {"content_hash": rec.get("content_hash") or "", "parameters": rec.get("parameters") or {},
                         "instruction": "re-run the analysis on the same data bundle with these parameters; an identical content hash means an identical result"},
        "note": NOTE,
    }
    doc["digest"] = canon.digest(doc)
    return doc


def validate(doc) -> list[str]:
    errs = []
    if not isinstance(doc, dict):
        return ["the handoff must be a JSON object"]
    if doc.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    if doc.get("version") not in VERSIONS:
        errs.append(f"unknown version {json.dumps(doc.get('version'), ensure_ascii=False)}; this release reads {', '.join(VERSIONS)}")
    for k, t in REQUIRED.items():
        if k not in doc:
            errs.append(f"$.{k}: missing")
        elif not isinstance(doc[k], t):
            errs.append(f"$.{k}: must be {'an object' if t is dict else 'a list' if t is list else 'a string'}")
    if errs:
        return errs
    extra = sorted(set(doc) - set(REQUIRED))
    if extra:
        errs.append("unknown field(s): " + ", ".join(extra))
    if not ISO.match(doc["created_at"]):
        errs.append("$.created_at: must be an ISO 8601 time with a zone")
    lg = doc["language"]
    if lg.get("interface") not in LANGS:
        errs.append(f"$.language.interface: must be one of {', '.join(LANGS)}")
    if lg.get("content") != "en":
        errs.append("$.language.content: the scientific content is recorded in English (en)")
    if not isinstance(lg.get("translation"), dict) or not isinstance(lg["translation"].get("reviewed"), bool):
        errs.append("$.language.translation: must state the translation status and whether it was reviewed")
    inv = doc["investigation"]
    if not HEX64.match(str(inv.get("content_hash") or "")):
        errs.append("$.investigation.content_hash: must be 64 hexadecimal digits")
    if not isinstance(inv.get("synthetic"), bool):
        errs.append("$.investigation.synthetic: must be true or false")
    elif any(isinstance(p, dict) and p.get("origin") == "synthetic" for p in doc["provenance"]) and not inv["synthetic"]:
        errs.append("$.investigation.synthetic: the provenance lists synthetic data, so the handoff must be labelled synthetic")
    for k in ("established", "open", "unknown", "evidence_needed", "provenance", "limitations"):
        if len(doc[k]) > MAX_ITEMS:
            errs.append(f"$.{k}: more than {MAX_ITEMS} items")
        if any(not isinstance(x, (dict, str)) for x in doc[k]):
            errs.append(f"$.{k}: items must be objects or strings")
    if doc["reproduction"].get("content_hash") != inv.get("content_hash"):
        errs.append("$.reproduction.content_hash: must equal the investigation's content hash")
    if not errs:
        body = {k: v for k, v in doc.items() if k != "digest"}
        try:
            d = canon.digest(body)
        except Exception as e:      # noqa: BLE001 — a value the canonical form refuses is a validation error
            return [f"not canonicalisable: {e}"]
        if d != doc["digest"]:
            errs.append("$.digest: does not match the document's content (edited or incomplete)")
    return errs
