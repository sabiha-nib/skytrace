"""Reference-star selection (REFSEL-2).

REFSEL-1 used every Gaia DR3 star in G 10-17.5 with a proper motion. REFSEL-2 additionally rejects:
  * RUWE > 1.4 (Lindegren et al. 2021: poorly fitted single-star solutions, likely binaries);
  * duplicated_source = true (Gaia flags possible duplicate or blended detections);
  * astrometric_params_solved < 31 (no 5- or 6-parameter solution, so no proper motion/parallax).
A missing RUWE / flag is accepted (older bundles do not carry it) but counted, so the record shows
how many stars were not quality-checked. Every rejection carries a code.
"""

from __future__ import annotations

METHOD = "REFSEL-2"
RUWE_MAX = 1.4


def _truthy(v) -> bool:
    return v is True or str(v).strip().lower() in ("true", "t", "1")


def select_references(stars: list[dict]) -> tuple[list[dict], dict]:
    kept, codes = [], {"no_proper_motion": 0, "ruwe_high": 0, "duplicated_source": 0, "params_solved_low": 0}
    unchecked = {"ruwe_missing": 0, "duplicated_source_missing": 0}
    for s in stars:
        if s.get("pmra") is None or s.get("pmdec") is None:
            codes["no_proper_motion"] += 1
            continue
        aps = s.get("astrometric_params_solved")
        if aps is not None and int(aps) < 31:
            codes["params_solved_low"] += 1
            continue
        ruwe = s.get("ruwe")
        if ruwe is None:
            unchecked["ruwe_missing"] += 1
        elif float(ruwe) > RUWE_MAX:
            codes["ruwe_high"] += 1
            continue
        dup = s.get("duplicated_source")
        if dup is None:
            unchecked["duplicated_source_missing"] += 1
        elif _truthy(dup):
            codes["duplicated_source"] += 1
            continue
        kept.append(s)
    return kept, {"method": METHOD, "n_input": len(stars), "n_kept": len(kept), "rejected": codes,
                  "accepted_unchecked": unchecked, "ruwe_max": RUWE_MAX}
