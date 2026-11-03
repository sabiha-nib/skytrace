"""XSEARCH-1: cross-language search in layers, each labelled. Not semantic search.

  1. exact text: the normalised query occurs in an item's text (in English or in the interface language);
  2. terminology mapping: the query contains a term or synonym from the terminology base (TERM-1) in any of the six
     languages, and the item contains that term's canonical English form or its form in the interface language;
  3. lexical: every remaining query word (or a shared stem of at least five letters) occurs in the item.

Normalisation: Unicode NFKC, lower case, Latin diacritics removed (é → e), everything that is not a letter, combining mark
or digit becomes a space. Script detection by Unicode block: Bengali, Devanagari, Latin (English, Spanish, French and German
share it, so a Latin query is matched against all four). Ranking is a stated order, not a score: layer 1, then layer 2 by the
number of distinct terms matched, then layer 3; ties keep the input order. Ported to web/js/xsearch.js (parity-tested).
"""

from __future__ import annotations

import unicodedata

METHOD = "XSEARCH-1"
LABEL = "exact text, terminology mapping (TERM-1) and lexical matching — not semantic search"
LANGS = ["en", "bn", "hi", "es", "fr", "de"]
MIN_STEM = 5


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not ("̀" <= c <= "ͯ"))
    s = unicodedata.normalize("NFC", s)
    out = "".join(c if unicodedata.category(c)[0] in "LMN" else " " for c in s)
    return " ".join(out.split())


def script(s: str) -> str:
    bn = sum(1 for c in s if "ঀ" <= c <= "৿")
    hi = sum(1 for c in s if "ऀ" <= c <= "ॿ")
    la = sum(1 for c in s if c.isascii() and c.isalpha() or "À" <= c <= "ɏ")
    present = [k for k, v in (("bn", bn), ("hi", hi), ("latin", la)) if v]
    if len(present) > 1:
        return "mixed"
    return present[0] if present else "none"


def index(terms: dict) -> list[dict]:
    out = []
    for t in terms.get("terms", []):
        for lang in LANGS:
            v = t.get(lang) or {}
            for kind, form in [("term", v.get("term"))] + [("synonym", x) for x in v.get("synonyms") or []]:
                n = normalize(form or "")
                if n:
                    out.append({"form": n, "term": t["id"], "lang": lang, "kind": kind})
    out.sort(key=lambda e: (-len(e["form"]), e["form"], e["term"], e["lang"]))
    return out


def _stem_eq(a: str, b: str) -> bool:
    if a == b:
        return True
    k = min(len(a), len(b))
    return k >= MIN_STEM and a[:k] == b[:k]


def expand(query: str, terms: dict, idx: list[dict] | None = None) -> dict:
    idx = idx if idx is not None else index(terms)
    q = normalize(query)
    toks = q.split()
    used = [False] * len(toks)
    padded = f" {q} "
    matches, seen = [], set()
    for e in idx:                                   # layer 2a: whole term forms (longest first)
        if f" {e['form']} " in padded and (e["term"], e["lang"], e["form"]) not in seen:
            seen.add((e["term"], e["lang"], e["form"]))
            matches.append({"term": e["term"], "lang": e["lang"], "form": e["form"], "kind": e["kind"], "how": "term"})
            ft = e["form"].split()
            for i in range(len(toks) - len(ft) + 1):
                if toks[i:i + len(ft)] == ft:
                    for j in range(i, i + len(ft)):
                        used[j] = True
    for i, tk in enumerate(toks):                   # layer 2b: single-word forms by shared stem
        if used[i] or len(tk) < MIN_STEM:
            continue
        for e in idx:
            if " " in e["form"] or not _stem_eq(tk, e["form"]):
                continue
            if (e["term"], e["lang"], e["form"]) in seen:
                used[i] = True
                continue
            seen.add((e["term"], e["lang"], e["form"]))
            matches.append({"term": e["term"], "lang": e["lang"], "form": e["form"], "kind": e["kind"], "how": "stem"})
            used[i] = True
    ids = []
    for m in matches:
        if m["term"] not in ids:
            ids.append(m["term"])
    by_id = {t["id"]: t for t in terms.get("terms", [])}
    return {"method": METHOD, "query": query, "normalized": q, "script": script(query), "tokens": toks, "matches": matches, "terms": ids,
            "english": [by_id[i]["en"]["term"] for i in ids if i in by_id], "residual": [t for t, u in zip(toks, used) if not u]}


def _forms(term: dict, ui_lang: str) -> list[str]:
    out = [normalize(term["en"]["term"])] + [normalize(x) for x in term["en"].get("synonyms") or []]
    v = term.get(ui_lang) or {}
    if ui_lang != "en" and v:
        out += [normalize(v.get("term") or "")] + [normalize(x) for x in v.get("match") or []]
    return [x for x in out if x]


def search(query: str, docs: list[dict], terms: dict, ui_lang: str = "en", idx: list[dict] | None = None, limit: int = 40) -> dict:
    """docs: [{"id", "text"}] — text may already include the item's interface-language label."""
    ex = expand(query, terms, idx)
    q = ex["normalized"]
    by_id = {t["id"]: t for t in terms.get("terms", [])}
    tforms = {i: _forms(by_id[i], ui_lang) for i in ex["terms"] if i in by_id}
    res = []
    for pos, d in enumerate(docs):
        txt = f" {normalize(d.get('text') or '')} "
        layer, via = None, []
        if q and ((len(q) >= 3 and q in txt) or f" {q} " in txt):
            layer, via = 1, ["exact text"]
        hit = [i for i, fs in tforms.items() if any((f" {f} " in txt) or (len(f) >= MIN_STEM and f in txt) for f in fs)]
        if layer is None and hit:
            layer, via = 2, [f"terminology: {by_id[i]['en']['term']}" for i in hit]
        if layer is None:
            rest = ex["residual"] if ex["terms"] else ex["tokens"]
            words = txt.split()
            if rest and all(any(_stem_eq(r, w) or (len(r) >= 3 and w.startswith(r)) for w in words) for r in rest):
                layer, via = 3, ["words"]
        if layer is not None:
            res.append({"id": d.get("id"), "layer": layer, "n_terms": len(hit), "via": via, "pos": pos})
    res.sort(key=lambda r: (r["layer"], -r["n_terms"] if r["layer"] == 2 else 0, r["pos"]))
    return {"method": METHOD, "label": LABEL, "expansion": ex, "results": res[:limit], "n": len(res)}
