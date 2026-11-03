"""Extract every interface message from the web interface into web/i18n/source.json (I18N-1).

    python scripts/i18n_extract.py           # writes web/i18n/source.json and prints counts
    python scripts/i18n_extract.py --check   # exits 1 if source.json is out of date

Sources:
  * web/index.html: text nodes and the attributes aria-label, title and placeholder;
  * web/js/**/*.js: string and template literals that read as interface text. A template literal becomes a pattern in which
    each ${...} is a numbered placeholder ({0}, {1}, …); the browser matches rendered text against patterns and translates the
    fixed parts, keeping the substituted values (numbers, identifiers, names) unchanged;
  * src/skytrace/**/*.py: server-side text marked _t("…", lang, …) (reports and exports);
  * keyed messages: t("key", …) calls (new code) — their English text lives in web/i18n/en.json under "keys";
  * controlled vocabulary from the Python engines (statuses, outcome categories, region and requirement names) listed in
    VOCAB_SOURCES, because the interface shows these words as labels.

The English text is the message identifier (gettext style); each message also has a stable key, the first 10 hex digits of
its SHA-1, used by the quality observatory and the tests. Narrative text computed by the Python engines (rule statements,
explanations) is not extracted: it is shown in its original language and marked as such (see docs/I18N.md).
"""

from __future__ import annotations

import hashlib
import html
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "i18n" / "source.json"
CATALOG = ROOT / "web" / "i18n" / "catalog.json"   # what the browser loads: key and English text of every message, keyed English
sys.path.insert(0, str(ROOT / "src"))

# Python constants whose words are displayed as labels (module, attribute). Lists, dicts (values or keys) or tuples of strings.
VOCAB_SOURCES = [("memory", "STATUSES"), ("memory", "KINDS"), ("gate", "STATES"), ("adversary", "STATUSES"), ("fingerprint", "STATES"),
                 ("instcheck", "STATES"), ("whatif", "KINDS"), ("budget", "CLASSES"), ("repronet", "CLASSES"), ("epistemic", "STATUSES"),
                 ("epistemic", "KINDS"), ("entities", "STATUSES"), ("entities", "TYPES"), ("hypotheses", "STATUSES"), ("claims", "REGIONS"),
                 ("unknownmap", "REGIONS"), ("gate", "REQUIREMENTS"), ("adversary", "QUESTIONS"), ("causal", "CRITERIA"), ("whatif", "QUESTIONS"),
                 ("fingerprint", "DIMENSIONS"), ("instcheck", "NAMES"), ("mdnet", "RULES"), ("negspace", "KINDS"), ("scicomp", "OUTCOMES"),
                 ("claims", "RESULTS"), ("reprox", "VERDICTS"), ("capabilities", "ACTIONS"), ("science.assess", "CATEGORIES")]

SKIP_FILES = {"web/js/static/hash.js", "web/js/i18n.js"}
CODEY = re.compile(r"^(?:[#.\[@:/]|https?:|data:|M\d|[a-z]+/[a-z0-9.+-]+$|\w+\.(?:js|json|css|png|svg|md|zip|csv|txt)$)")
WORD = re.compile(r"[A-Za-z]{2,}")
CSS_CLASSES = set(re.findall(r"\.([a-zA-Z][\w-]*)", (ROOT / "web" / "css" / "app.css").read_text(encoding="utf-8")))


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _is_message(t: str) -> bool:
    s = re.sub(r"\{\d+\}", "", t).strip()
    if t.startswith("{") and re.match(r"[:;,·—–-]", s):          # "{0}: text" — the colon follows a value, it is not a selector
        s = s[1:].strip()
    if not WORD.search(s) or len(s) < 2 or CODEY.match(s):
        return False
    if s.startswith("<") or "${" in s or ").join" in s or s.startswith("```") or re.fullmatch(r"[a-z]+[A-Z]\w*", s):   # markup, code
        return False
    toks0 = s.split()
    if "sans-serif" in s or (all(re.fullmatch(r"[a-z][a-z0-9-]*", x) and (x in CSS_CLASSES or "-" in x) for x in toks0)
                             and any("-" in x for x in toks0)) or s in ("ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Escape", "Enter"):
        return False
    if "{" in t and re.fullmatch(r"(?:of|to|and|or|vs\.?|per|in|from)", s):   # "{0} of {1}": a phrase around values, not a key
        return True
    if re.fullmatch(r"[a-z0-9_\-]+", s):          # lowercase identifiers and keys: vocabulary is handled separately
        return False
    if re.fullmatch(r"[\w\-]+(?:[.:/][\w\-]+)+", s):   # dotted ids, paths, selectors
        return False
    if re.search(r"[{}]\s*$|=>|\bfunction\b|\bconst\b|^\s*[a-z-]+\s*:\s*[^ ]+;", s):  # code or CSS
        return False
    if re.search(r";\s*$", s) and (len(WORD.findall(s)) < 4 or re.search(r"[=(){}]", s)):   # a statement, not a sentence ending in ";"
        return False
    if re.fullmatch(r"[A-Z0-9_\-]+(?:-\d+)?", s):    # method ids, constants
        return False
    if s.startswith(("aria-", "data-", "skytrace-", "url(", "application/", "text/", "image/")) or "querySelector" in s:
        return False
    toks = s.split()
    if toks and all(re.fullmatch(r"[a-z][\w-]*", x) for x in toks) and all(x in CSS_CLASSES for x in toks):   # class lists
        return False
    if re.match(r"(?:rgba?|hsla?|rotate|translate|scale|matrix)\(", s):   # colours and SVG transforms
        return False
    if t.startswith("?") or re.fullmatch(r"[a-z_]+\.\{\d+\}", t):        # query strings, event kinds
        return False
    if "," in s and re.fullmatch(r"[a-z0-9\-.\[\]=,#:\s]+", s) and re.search(r"[.\[]", s):   # CSS selector lists
        return False
    if " " not in s and "/" in s:                     # paths and file patterns
        return False
    if re.fullmatch(r"[\w.\-]+\.(?:json|js|md|zip|csv|png|txt|html)", s) or re.search(r"\{\d+\}\.(?:json|md|zip|csv|png)$", s):
        return False
    return True


def _template_to_pattern(body: str) -> str:
    out, i, n, k = [], 0, len(body), 0
    while i < n:
        if body.startswith("${", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                elif body[j] == "`":                    # skip nested template literal
                    j += 1
                    while j < n and body[j] != "`":
                        j += 2 if body[j] == "\\" else 1
                j += 1
            out.append("{%d}" % k)
            k += 1
            i = j
        elif body[i] == "\\" and i + 1 < n:
            out.append({"n": "\n", "t": "\t", "`": "`", "$": "$", "\\": "\\"}.get(body[i + 1], body[i + 1]))
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def _js_literals(src: str):
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            i = src.find("\n", i)
            i = n if i < 0 else i
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            i = src.find("*/", i + 2)
            i = n if i < 0 else i + 2
            continue
        if c in "\"'":
            j, buf = i + 1, []
            while j < n and src[j] != c and src[j] != "\n":
                if src[j] == "\\" and j + 1 < n:
                    buf.append({"n": "\n", "t": "\t"}.get(src[j + 1], src[j + 1]))
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            yield "".join(buf), False, src[max(0, i - 40):i]
            i = j + 1
            continue
        if c == "`":
            j, depth = i + 1, 0
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src.startswith("${", j):
                    depth += 1
                    j += 2
                    continue
                if src[j] == "}" and depth:
                    depth -= 1
                elif src[j] == "`" and not depth:
                    break
                elif src[j] == "`" and depth:            # nested template: skip it
                    k = j + 1
                    while k < n and src[k] != "`":
                        k += 2 if src[k] == "\\" else 1
                    j = k
                j += 1
            body = src[i + 1:j]
            yield _template_to_pattern(body), "${" in body, src[max(0, i - 40):i]
            for m in re.finditer(r"`((?:[^`\\]|\\.)*)`", body):    # nested literals inside placeholders
                yield _template_to_pattern(m.group(1)), "${" in m.group(1), ""
            for m in re.finditer(r"\"((?:[^\"\\\n]|\\.)*)\"", body):
                yield m.group(1), False, ""
            i = j + 1
            continue
        i += 1


NOT_UI_CONTEXT = re.compile(r"(?:import\s.*from\s*|querySelector(?:All)?\(|\$\$?\(|closest\(|matches\(|addEventListener\(|setAttribute\(|"
                            r"getAttribute\(|dataset\.|localStorage\.\w+\(|\.(?:startsWith|endsWith|includes|split|replace|test|match)\(|"
                            r"new RegExp\(|createElementNS?\(|\bel\(|fetch\(|api\.\w+\()\s*$")


def js_messages() -> dict[str, dict]:
    msgs: dict[str, dict] = {}
    files = sorted((ROOT / "web" / "js").rglob("*.js"))
    for f in files:
        rel = str(f.relative_to(ROOT))
        if rel in SKIP_FILES:
            continue
        for text, is_tpl, before in _js_literals(f.read_text(encoding="utf-8")):
            if NOT_UI_CONTEXT.search(before) and not re.search(r"\bel\(\s*$", before) is None:
                pass
            if re.search(r"(?:querySelector(?:All)?|\$\$?|closest|matches|addEventListener|getAttribute|createElementNS?|import\s.*from)\s*\(?\s*$", before):
                continue
            if re.search(r"\bel\(\s*$", before):          # first argument of el() is a tag name
                continue
            t = text.strip() if not is_tpl else text
            if not _is_message(t.strip()):
                continue
            t = t.strip()
            e = msgs.setdefault(t, {"text": t, "kind": "pattern" if re.search(r"\{\d+\}", t) else "text", "files": []})
            if rel not in e["files"]:
                e["files"].append(rel)
    return msgs


def html_messages() -> dict[str, dict]:
    s = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    body = s[s.find("<body"):]
    msgs = {}
    for m in re.finditer(r">([^<>]+)<", body):
        t = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
        if t and _is_message(t):
            msgs.setdefault(t, {"text": t, "kind": "text", "files": ["web/index.html"]})
    for m in re.finditer(r'(?:aria-label|title|placeholder)="([^"]+)"', body):
        t = html.unescape(m.group(1).strip())
        if _is_message(t):
            msgs.setdefault(t, {"text": t, "kind": "text", "files": ["web/index.html"]})
    return msgs


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from _strings(k)
            if isinstance(x, (str, list, tuple)) and not isinstance(x, dict):
                yield from _strings(x)
            elif isinstance(x, dict):
                for kk in ("title", "name", "label"):
                    if isinstance(x.get(kk), str):
                        yield x[kk]
    elif isinstance(v, (list, tuple)):
        for x in v:
            if isinstance(x, dict):
                for kk in ("title", "name", "label"):
                    if isinstance(x.get(kk), str):
                        yield x[kk]
            else:
                yield from _strings(x)


PY_T = re.compile(r"""\b_t\(\s*(?P<q>["'])(?P<s>(?:\\.|(?!(?P=q)).)*)(?P=q)\s*[,)]""")


def python_messages() -> dict[str, dict]:
    """Server-side interface text marked _t("…", lang, …) (reports and exports; see src/skytrace/i18n.py)."""
    msgs = {}
    for f in sorted((ROOT / "src" / "skytrace").rglob("*.py")):
        rel = str(f.relative_to(ROOT))
        if rel.endswith("skytrace/i18n.py"):
            continue
        for m in PY_T.finditer(f.read_text(encoding="utf-8")):
            t = m.group("s").encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") if "\\" in m.group("s") else m.group("s")
            t = t.strip()
            if not t or not WORD.search(t):
                continue
            e = msgs.setdefault(t, {"text": t, "kind": "pattern" if re.search(r"\{\d+\}", t) else "text", "files": []})
            if rel not in e["files"]:
                e["files"].append(rel)
    return msgs


# Phase 10 notes, rules and labels the interface shows verbatim (any length; every string value, dict keys excluded)
LONG_SOURCES = [("universal", n) for n in ("AGENT_CAVEAT", "DOES_NOT_MEAN", "DISTINCTIONS", "COMPILER_STATUSES", "NOVELTY_SCOPES", "LEAD_NOTE", "NEG_NOTE",
                                           "WORLD_NOTE", "OPP_NOTE", "KCOMP_MEANING", "EXT_NOTE", "EXPLAIN_NOTE", "TIMES_NOTE", "MODAL_RULES", "CONV_RULES",
                                           "DIRECTOR_RULES", "LANE_MEANING", "EVENT_STATE", "ROLES")] + \
               [("sigintel", n) for n in ("METHODS", "SERIES_RULES", "NOT_PROBABILITIES")]
SKIP_FIELDS = {"id", "a", "b"}


def _values(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in SKIP_FIELDS:
                yield from _values(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _values(x)


def vocab_messages() -> dict[str, dict]:
    msgs = {}
    for mod, attr in LONG_SOURCES:
        try:
            v = getattr(importlib.import_module(f"skytrace.{mod}"), attr)
        except (ImportError, AttributeError):
            continue
        for s in _values(v):
            s = s.strip()
            if not s or not WORD.search(s) or (" " not in s and not s.isalpha()):
                continue
            e = msgs.setdefault(s, {"text": s, "kind": "vocabulary", "files": []})
            src = f"src/skytrace/{mod}.py:{attr}"
            if src not in e["files"]:
                e["files"].append(src)
    for mod, attr in VOCAB_SOURCES:
        try:
            v = getattr(importlib.import_module(f"skytrace.{mod}"), attr)
        except (ImportError, AttributeError):
            continue
        for s in _strings(v):
            s = s.strip()
            if not s or not WORD.search(s) or re.fullmatch(r"[A-Z]+\d*(?:-\d+)?", s) or len(s) > 140:
                continue
            if re.fullmatch(r"[a-z_]+", s) and "_" in s:     # snake_case identifiers stay untranslated
                continue
            e = msgs.setdefault(s, {"text": s, "kind": "vocabulary", "files": []})
            src = f"src/skytrace/{mod.replace('.', '/')}.py:{attr}"
            if src not in e["files"]:
                e["files"].append(src)
    return msgs


def keyed_messages() -> dict[str, dict]:
    en = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8")) if (ROOT / "web" / "i18n" / "en.json").exists() else {}
    return {f"@{k}": {"text": v, "kind": "keyed", "key_name": k, "files": ["web/i18n/en.json"]} for k, v in (en.get("keys") or {}).items()}


def build() -> dict:
    allm: dict[str, dict] = {}
    for part in (html_messages(), js_messages(), python_messages(), vocab_messages()):
        for t, e in part.items():
            if t in allm:
                allm[t]["files"] = sorted(set(allm[t]["files"]) | set(e["files"]))
                if e["kind"] == "vocabulary":
                    allm[t]["kind"] = allm[t]["kind"] if allm[t]["kind"] != "text" else "text"
            else:
                allm[t] = dict(e)
    items = [{"key": _key(t), **e} for t, e in sorted(allm.items())]
    keyed = [{"key": e["key_name"], **{k: v for k, v in e.items() if k != "key_name"}} for e in keyed_messages().values()]
    words = sum(len(re.sub(r"\{\w+\}", "", x["text"] if isinstance(x["text"], str) else " ".join(x["text"].values())).split()) for x in items + keyed)
    return {"schema": "skytrace.i18n-source/1", "method": "I18N-1", "n": len(items) + len(keyed), "words": words,
            "by_kind": {k: sum(1 for x in items + keyed if x["kind"] == k) for k in ("text", "pattern", "vocabulary", "keyed")},
            "messages": items, "keyed": keyed}


def catalog_text(cat: dict) -> str:
    en = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8")) if (ROOT / "web" / "i18n" / "en.json").exists() else {}
    c = {"schema": "skytrace.i18n-catalog/1", "method": "I18N-1", "messages": [{"k": x["key"], "s": x["text"]} for x in cat["messages"]],
         "keys": en.get("keys", {})}
    return json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n"


def main() -> int:
    cat = build()
    text = json.dumps(cat, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        ok = (OUT.exists() and OUT.read_text(encoding="utf-8") == text and CATALOG.exists()
              and CATALOG.read_text(encoding="utf-8") == catalog_text(cat))
        print("source.json up to date" if ok else "source.json is out of date: run python scripts/i18n_extract.py")
        return 0 if ok else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    CATALOG.write_text(catalog_text(cat), encoding="utf-8")
    print(json.dumps({k: cat[k] for k in ("n", "words", "by_kind")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
