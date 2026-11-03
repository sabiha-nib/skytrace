"""I18N-1 on the server: the same catalogue and language files the browser uses (web/i18n/), for reports and exports.

The English text is the message identifier (gettext style). Server code marks interface text for extraction with
``_t("English text {0}", lang, value)``; scripts/i18n_extract.py collects those calls into the catalogue, and the language
files hold the translations. Only the fixed wording is translated: values substituted into a message (numbers, identifiers,
names, statements recorded by the scientific engines) are inserted unchanged, so a report says the same numbers in every
language. Narrative text recorded by the engines stays in English, its original language, and the report says so.

Translations are machine-made and unreviewed; ``meta(lang)`` returns the status recorded in the language file.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = ROOT / "web" / "i18n"
LANGS = {"en": ("English", "English"), "bn": ("বাংলা", "Bangla"), "hi": ("हिन्दी", "Hindi"), "es": ("Español", "Spanish"),
         "fr": ("Français", "French"), "de": ("Deutsch", "German")}
METHOD = "I18N-1"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def valid(lang: str | None) -> str:
    return lang if lang in LANGS else "en"


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict[str, str], dict]:
    p = I18N_DIR / "catalog.json"
    if not p.exists():
        return {}, {}
    c = json.loads(p.read_text(encoding="utf-8"))
    return {m["k"]: m["s"] for m in c.get("messages", [])}, c.get("keys", {})


@lru_cache(maxsize=8)
def _lang_file(lang: str) -> dict:
    p = I18N_DIR / f"{lang}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# A pattern whose only fixed text is one connective ("{0} of {1}", "{0} and {1}") would match almost any English sentence and
# translate part of recorded engine text; its placeholders therefore match numbers only. Same rule in web/js/i18n.js.
CONNECTIVE = re.compile(r"(?:of|to|and|or|vs\.?|per|in|from)")


@lru_cache(maxsize=8)
def _tables(lang: str) -> tuple[dict[str, str], list]:
    """English text → translation, and compiled template patterns (most specific first), for one language."""
    if lang == "en":
        return {}, []
    src, _ = _catalog()
    tr = _lang_file(lang).get("messages", {})
    by_text, pats = {}, []
    for k, s in src.items():
        out = tr.get(k)
        if not isinstance(out, str) or not out:
            continue
        if re.search(r"\{\d+\}", s):
            parts = re.split(r"(\{\d+\})", s)
            order, rx, fixed = [], "^", ""
            numeric = bool(CONNECTIVE.fullmatch(re.sub(r"\{\d+\}", "", s).strip()))   # "{0} of {1}": numbers only
            for p in parts:
                m = re.fullmatch(r"\{(\d+)\}", p)
                if m:
                    order.append(int(m.group(1)))
                    rx += r"(\d[\d.,]*)" if numeric else r"([\s\S]+?)"
                else:
                    rx += re.escape(p)
                    fixed += p
            pats.append((re.compile(rx + "$"), out, order, fixed.strip()))
        else:
            by_text[norm(s)] = out
    pats.sort(key=lambda x: -len(x[3]))
    return by_text, pats


def meta(lang: str) -> dict:
    lang = valid(lang)
    if lang == "en":
        return {"lang": "en", "name": "English", "status": "source language", "method": METHOD}
    d = _lang_file(lang)
    return {"lang": lang, "name": LANGS[lang][0], "english_name": LANGS[lang][1], "status": d.get("status"),
            "translator": d.get("translator"), "version": d.get("version"), "reviewed": bool(d.get("reviewed")), "method": METHOD}


def _t(text: str, lang: str = "en", *args) -> str:
    """Translate one marked message and fill its {0}, {1}, … placeholders with the given values, unchanged."""
    lang = valid(lang)
    out = text
    if lang != "en":
        out = _lang_file(lang).get("messages", {}).get(_key_of(text)) or text
    return re.sub(r"\{(\d+)\}", lambda m: str(args[int(m.group(1))]) if int(m.group(1)) < len(args) else m.group(0), out)


@lru_cache(maxsize=4096)
def _key_of(text: str) -> str:
    """The message key: the first 10 hex digits of the SHA-1 of the English text (as scripts/i18n_extract.py)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def translate_text(s: str, lang: str) -> str | None:
    """The browser's translateText without number localization: exact message, then template patterns. None = no translation."""
    lang = valid(lang)
    if lang == "en" or not s:
        return None
    m = re.match(r"^(\s*)([\s\S]*?)(\s*)$", s)
    core = norm(m.group(2))
    if not core:
        return None
    by_text, pats = _tables(lang)
    hit = by_text.get(core)
    if hit is not None:
        return m.group(1) + hit + m.group(3)
    for rx, out, order, fixed in pats:
        if fixed and fixed.split()[0] not in core:
            continue
        g = rx.match(core)
        if not g:
            continue
        vals = [by_text.get(norm(v), v) for v in g.groups()]
        res = re.sub(r"\{(\d+)\}", lambda x: vals[order.index(int(x.group(1)))] if int(x.group(1)) in order else x.group(0), out)
        return m.group(1) + res + m.group(3)
    return None


def header_comment(lang: str) -> str:
    """The metadata line written at the top of a translated Markdown or text export (also used by the browser export)."""
    mt = meta(lang)
    if mt["lang"] == "en":
        return ""
    return (f"<!-- language: {mt['name']} ({mt['lang']}); interface translation: {mt['status']}; translator: {mt['translator']}; "
            f"numbers, identifiers, units and recorded scientific text are unchanged from the English original -->")


NUM = re.compile(r"(?<![\w.])[−+-]?\d+(?:[.,]\d+)*(?:[eE][−+-]?\d+)?")


def numbers(text: str) -> list[str]:
    """Every number written in a text, in order: the check that a translation did not change a value (TRQ-NUM)."""
    return NUM.findall(text)


# ------------------------------------------------------------------ I18N-Q1: translation quality observatory
IDS = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*-\d+\b")
NATIVE = {"bn": ("ঀ", "৿"), "hi": ("ऀ", "ॿ")}


def _has_native(s: str, lang: str) -> bool:
    lo, hi = NATIVE[lang]
    return any(lo <= c <= hi for c in s)


def quality() -> dict:
    """Counts, never percentages: completeness, placeholders, Unicode, preserved numbers and identifiers, terminology
    consistency and text expansion, per language. Computed from the files in web/i18n/ (scripts/i18n_quality.py)."""
    import unicodedata
    src, keys_en = _catalog()
    tpath = I18N_DIR / "terms.json"
    terms = json.loads(tpath.read_text(encoding="utf-8"))["terms"] if tpath.exists() else []
    out = {"schema": "skytrace.i18n-quality/1", "method": "I18N-Q1", "n_messages": len(src), "n_keyed": len(keys_en), "n_terms": len(terms), "languages": {}}
    num_re = re.compile(r"\d+(?:\.\d+)?")
    for lang in [x for x in LANGS if x != "en"]:
        d = _lang_file(lang)
        msgs, kd = d.get("messages", {}), d.get("keys", {})
        missing = [k for k in src if not msgs.get(k)]
        ph, bad_u, non_nfc, ident, ident_words, nums, ids, no_native, ratios = [], [], [], [], [], [], [], [], []
        for k, en in src.items():
            tr = msgs.get(k)
            if not tr:
                continue
            if sorted(re.findall(r"\{[0-9a-z_]+\}", tr)) != sorted(re.findall(r"\{[0-9a-z_]+\}", en)):
                ph.append(k)
            if "�" in tr or any(unicodedata.category(c) == "Cc" and c not in "\n\t" for c in tr):
                bad_u.append(k)
            if unicodedata.normalize("NFC", tr) != tr:
                non_nfc.append(k)
            if tr == en:
                (ident_words if re.search(r"[A-Za-z]{3,}", re.sub(r"\{\d+\}", "", en)) else ident).append(k)
            base = re.sub(r"\{\d+\}", "", en)
            trb = re.sub(r"\{\d+\}", "", tr)
            if any(n not in trb and n.replace(".", ",") not in trb for n in num_re.findall(base)):
                nums.append(k)
            if any(i not in tr for i in IDS.findall(en)):
                ids.append(k)
            if lang in NATIVE and re.search(r"[A-Za-z]{3,}", base) and not _has_native(tr, lang) and tr != en:
                no_native.append(k)
            if len(en) >= 12:
                ratios.append((len(tr) / len(en), k))
        cons, incons = 0, []
        for t in terms:
            pat = re.compile(r"(?<![A-Za-z])" + re.escape(t["en"]["term"]) + r"(?![A-Za-z])", re.I)
            forms = [x.lower() for x in [t[lang]["term"]] + t[lang].get("synonyms", []) + t[lang].get("match", [])]
            for k, en in src.items():
                tr = msgs.get(k)
                if not tr or not pat.search(re.sub(r"'[^']*'", "", en)):     # quoted identifiers are not terms
                    continue
                if any(f in tr.lower() for f in forms):
                    cons += 1
                else:
                    incons.append({"term": t["id"], "key": k, "en": en[:120], "tr": tr[:120]})
        ratios.sort(reverse=True)
        rs = sorted(r for r, _ in ratios)
        out["languages"][lang] = {
            "name": LANGS[lang][0], "status": d.get("status"), "translator": d.get("translator"), "version": d.get("version"), "reviewed": bool(d.get("reviewed")),
            "translated": len(src) - len(missing), "missing": missing[:50], "n_missing": len(missing),
            "keyed_translated": sum(1 for k in keys_en if kd.get(k)), "placeholder_mismatches": ph, "unicode_problems": bad_u, "not_nfc": non_nfc,
            "identical_symbols": len(ident), "identical_words": len(ident_words), "identical_words_sample": [src[k] for k in ident_words[:20]],
            "numbers_changed": nums, "identifiers_changed": ids, "without_native_script": len(no_native) if lang in NATIVE else None,
            "without_native_script_sample": [src[k] for k in no_native[:10]] if lang in NATIVE else [],
            "terminology": {"consistent": cons, "inconsistent": len(incons), "examples": incons[:12]},
            "expansion": {"median_ratio": round(rs[len(rs) // 2], 3) if rs else None, "max_ratio": round(rs[-1], 3) if rs else None,
                          "longest": [{"key": k, "en": src[k][:80], "ratio": round(r, 2)} for r, k in ratios[:8]]}}
    return out
