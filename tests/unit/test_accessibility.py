"""Colour contrast of the theme's text tokens on every surface (WCAG 2.x AA: 4.5:1 for body-size text)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT = ["text", "muted", "faint", "accent", "violet", "ok", "warn", "bad", "syn"]
SURFACES = ["ink", "ink-2", "panel", "panel-2"]


def tokens():
    css = (ROOT / "web/css/app.css").read_text()
    root = css[css.index(":root"):css.index("}", css.index(":root"))]
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", root))


def luminance(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_text_tokens_meet_aa_on_every_surface():
    t = tokens()
    bad = [(fg, bg, round(ratio(t[fg], t[bg]), 2)) for fg in TEXT for bg in SURFACES if ratio(t[fg], t[bg]) < 4.5]
    assert bad == []


def test_primary_button_text_contrast():
    t = tokens()
    assert ratio(t["accent-ink"], t["accent"]) >= 4.5


def test_reduced_motion_disables_animation():
    css = (ROOT / "web" / "css" / "app.css").read_text()
    blocks = re.findall(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", css, re.S)
    assert blocks and any("animation" in b and ("none" in b or "0s" in b or "0.01ms" in b) for b in blocks)
