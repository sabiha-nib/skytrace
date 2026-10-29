"""Perturbation stability of the assessment (STAB-1).

Re-runs the deterministic analysis with small, pre-declared changes to the
measurement parameters and reports whether any outcome category changes. An
outcome that flips under a reasonable parameter change is fragile and is
reported as such; this is a robustness diagnostic, not a significance test.

The perturbation set is fixed here (not chosen per target):
  aperture radius ±0.5 px, wavelength tolerance 0.3 channel, epoch clip 3σ and 6σ.
"""

from __future__ import annotations

from . import analysis
from . import bundle as bmod

METHOD = "STAB-1"


def perturbations(base: dict) -> list[tuple[str, dict]]:
    p = {**analysis.DEFAULTS, **base}
    ap = p["aperture_radius_px"]
    out = [(f"aperture {ap - 0.5:.1f} px", {"aperture_radius_px": max(1.0, ap - 0.5)}),
           (f"aperture {ap + 0.5:.1f} px", {"aperture_radius_px": min(5.0, ap + 0.5)}),
           ("wavelength tolerance 0.3 channel", {"wavelength_tolerance_channels": 0.3}),
           ("epoch clip 3σ", {"epoch_clip_sigma": 3.0}),
           ("epoch clip 6σ", {"epoch_clip_sigma": 6.0})]
    return [(label, {**base, **change}) for label, change in out]


def _summary(record: dict) -> dict:
    ev = next((e for e in record["events"] if e["step"] == "assess"), None)
    outs = {o["question"]: o for o in (ev or {}).get("data", {}).get("outcomes", [])}
    m = outs.get("motion", {}).get("evidence", {})
    v = outs.get("variability", {}).get("evidence", {})
    return {"categories": {q: o["category"] for q, o in outs.items()},
            "pm_measured_mas_yr": m.get("pm_measured_mas_yr"), "pm_sigma_mas_yr": m.get("pm_sigma_mas_yr"),
            "max_abs_z_calibrated": v.get("max_abs_z_calibrated"), "n_matched_pairs": v.get("n_matched_pairs"),
            "content_hash": record.get("content_hash")}


def run(b: bmod.Bundle, base_params: dict | None = None) -> dict:
    base_params = dict(base_params or {})
    base = _summary(analysis.run(b, base_params).to_dict())
    rows, changed = [], {}
    for label, params in perturbations(base_params):
        s = _summary(analysis.run(b, params).to_dict())
        diff = {q: (base["categories"].get(q), c) for q, c in s["categories"].items() if c != base["categories"].get(q)}
        for q in diff:
            changed.setdefault(q, []).append(label)
        rows.append({"label": label, "params": params, **s, "changed": {q: list(v) for q, v in diff.items()}})
    questions = sorted(base["categories"])
    return {"method": METHOD, "target": b.target_id, "synthetic": b.kind == "synthetic", "base_params": base_params,
            "base": base, "runs": rows,
            "stable": {q: q not in changed for q in questions}, "fragile_under": changed,
            "note": "An outcome that changes under these small parameter changes is fragile; it should be "
                    "reported with that caveat or not at all."}
