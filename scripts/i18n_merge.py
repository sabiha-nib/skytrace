"""Merge translation batches into the language files web/i18n/<lang>.json (I18N-1).

    python scripts/i18n_merge.py BATCH.tsv [...]     # merge one or more batches
    python scripts/i18n_merge.py --todo [N] [--from K] # print up to N untranslated messages (key, English) for the next batch
    python scripts/i18n_merge.py --prune               # drop translations whose English source no longer exists

A batch is a tab-separated file, one message per line:  key <TAB> bn <TAB> hi <TAB> es <TAB> fr <TAB> de
(the key is the message key from web/i18n/source.json; "@name" lines are keyed messages). A translation is refused when its
placeholders ({0}, {1}, … or {name}) differ from the English message's, or when it contains a replacement character. The
language files record that the translations were written by an AI model and have not been reviewed by a native speaker.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "web" / "i18n"
LANGS = {"bn": "বাংলা", "hi": "हिन्दी", "es": "Español", "fr": "Français", "de": "Deutsch"}
ORDER = ["bn", "hi", "es", "fr", "de"]
STATUS = "machine-translated by an AI model; not reviewed by a native speaker"
TRANSLATOR = "Claude (Anthropic AI model), Skytrace Phase 10"


def placeholders(s: str) -> list[str]:
    return sorted(re.findall(r"\{[0-9a-z_]+\}", s))


def load_lang(code: str) -> dict:
    p = I18N / f"{code}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema": "skytrace.i18n/1", "lang": code, "name": LANGS[code], "status": STATUS, "translator": TRANSLATOR,
            "version": "0.10.0", "reviewed": False, "messages": {}, "keys": {}}


def save_lang(code: str, d: dict) -> None:
    d["messages"] = dict(sorted(d["messages"].items()))
    d["keys"] = dict(sorted(d.get("keys", {}).items()))
    (I18N / f"{code}.json").write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=False) + "\n", encoding="utf-8")


def source() -> tuple[dict, dict]:
    src = json.loads((I18N / "source.json").read_text(encoding="utf-8"))
    en = json.loads((I18N / "en.json").read_text(encoding="utf-8")) if (I18N / "en.json").exists() else {"keys": {}}
    return {m["key"]: m["text"] for m in src["messages"]}, en.get("keys", {})


def merge(paths: list[str]) -> int:
    msgs, keys = source()
    langs = {c: load_lang(c) for c in ORDER}
    bad, n = [], 0
    for p in paths:
        for ln, line in enumerate(Path(p).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 6:
                bad.append(f"{p}:{ln}: expected 6 fields, got {len(parts)}")
                continue
            k, *tr = parts
            if k.startswith("@"):
                en = keys.get(k[1:])
                plural = isinstance(en, dict)
            else:
                en, plural = msgs.get(k), False
            if en is None:
                bad.append(f"{p}:{ln}: unknown key {k}")
                continue
            for code, text in zip(ORDER, tr):
                text = text.strip().replace("\\n", "\n")
                if "�" in text or not text:
                    bad.append(f"{p}:{ln}: {code}: empty or replacement character")
                    continue
                if plural:
                    try:
                        val = json.loads(text)
                    except ValueError:
                        bad.append(f"{p}:{ln}: {code}: plural forms must be JSON")
                        continue
                    langs[code]["keys"][k[1:]] = val
                    continue
                if placeholders(text) != placeholders(en):
                    bad.append(f"{p}:{ln}: {code}: placeholders {placeholders(text)} differ from {placeholders(en)} in {en[:60]!r}")
                    continue
                if k.startswith("@"):
                    langs[code]["keys"][k[1:]] = text
                else:
                    langs[code]["messages"][k] = text
            n += 1
    for c, d in langs.items():
        save_lang(c, d)
    print(f"merged {n} lines; {len(bad)} problem(s)")
    for b in bad[:60]:
        print("  ", b)
    return 1 if bad else 0


def todo(limit: int, start: int) -> int:
    msgs, keys = source()
    de = load_lang("de")
    have = set(de["messages"])
    rest = [(k, t) for k, t in sorted(msgs.items(), key=lambda kv: kv[1].lower()) if k not in have]
    rest += [("@" + k, json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for k, v in sorted(keys.items()) if k not in de.get("keys", {})]
    print(f"# {len(rest)} untranslated (of {len(msgs) + len(keys)})")
    for k, t in rest[start:start + limit]:
        print(f"{k}\t{t!r}")
    return 0


def prune() -> int:
    msgs, keys = source()
    for c in ORDER:
        d = load_lang(c)
        before = len(d["messages"])
        d["messages"] = {k: v for k, v in d["messages"].items() if k in msgs}
        d["keys"] = {k: v for k, v in d.get("keys", {}).items() if k in keys}
        save_lang(c, d)
        print(c, before, "→", len(d["messages"]))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--todo":
        n = int(a[1]) if len(a) > 1 and a[1].isdigit() else 80
        st = int(a[a.index("--from") + 1]) if "--from" in a else 0
        sys.exit(todo(n, st))
    if a and a[0] == "--prune":
        sys.exit(prune())
    sys.exit(merge(a))
