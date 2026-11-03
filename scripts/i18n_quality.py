"""Write web/i18n/quality.json, the translation quality observatory's static part (I18N-Q1).

    python scripts/i18n_quality.py           # writes web/i18n/quality.json and prints the per-language summary
    python scripts/i18n_quality.py --check   # exits 1 if quality.json is out of date

Counts only (no percentages): completeness, placeholder mismatches, Unicode problems, numbers and identifiers that changed,
terminology consistency against web/i18n/terms.json and text expansion. The interface adds what it measures in the browser:
messages rendered without a translation and text that overflows its box in the current page.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skytrace import i18n  # noqa: E402

OUT = ROOT / "web" / "i18n" / "quality.json"


def main() -> int:
    q = i18n.quality()
    text = json.dumps(q, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("quality.json up to date" if ok else "quality.json is out of date: run python scripts/i18n_quality.py")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    for lang, v in q["languages"].items():
        print(lang, f"{v['translated']}/{q['n_messages']}", "ph", len(v["placeholder_mismatches"]), "uni", len(v["unicode_problems"]), "nfc", len(v["not_nfc"]),
              "nums", len(v["numbers_changed"]), "ids", len(v["identifiers_changed"]), "terms", v["terminology"]["consistent"], "/", v["terminology"]["inconsistent"],
              "native-missing", v["without_native_script"], "exp", v["expansion"]["median_ratio"], v["expansion"]["max_ratio"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
