"""Flux comparison between wavelength-matched observations.

Method PAIRDIFF-1: for each accepted pair (see wavelength.match_pairs) with
"ok" photometry in both, compute

    delta = f2 - f1,   sigma = sqrt(s1^2 + s2^2),   z = delta / sigma
    ratio = f2 / f1 (when f1 > 0)

z is the significance of a flux difference under the stated per-measurement
errors. It is NOT the probability that the source is variable and it is not a
classification. Systematics not in the error model (residual wavelength
mismatch within tolerance, PSF variation across the detector, calibration
drift) can produce |z| > 3 for constant sources; the residual wavelength
mismatch is recorded with every pair so it can be inspected.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .wavelength import PairDecision

METHOD = "PAIRDIFF-1"


@dataclass(frozen=True)
class FluxPair:
    a: str
    b: str
    delta_t_days: float
    delta_lambda_um: float
    flux_a_ujy: float
    flux_b_ujy: float
    delta_ujy: float
    sigma_ujy: float
    z: float
    ratio: float
    method: str = METHOD
    err_a_ujy: float = float("nan")
    err_b_ujy: float = float("nan")


def compare_fluxes(pairs: list[PairDecision], phot: dict[str, tuple[float, float, str]]) -> tuple[list[FluxPair], list[tuple[str, str, str]]]:
    """phot maps obs_id -> (flux_ujy, err_ujy, status). Returns (results, skipped-with-reason)."""
    out, skipped = [], []
    for p in pairs:
        if not p.accepted:
            continue
        fa, fb = phot.get(p.a), phot.get(p.b)
        if fa is None or fb is None:
            skipped.append((p.a, p.b, "missing photometry"))
            continue
        if fa[2] != "ok" or fb[2] != "ok":
            skipped.append((p.a, p.b, f"photometry status {fa[2]}/{fb[2]}"))
            continue
        d = fb[0] - fa[0]
        s = math.hypot(fa[1], fb[1])
        out.append(FluxPair(p.a, p.b, p.delta_t_days, p.delta_lambda_um, fa[0], fb[0], d, s,
                            d / s if s > 0 else float("nan"), fb[0] / fa[0] if fa[0] > 0 else float("nan"),
                            err_a_ujy=fa[1], err_b_ujy=fb[1]))
    return out, skipped


# ---------------------------------------------------------------------------- PAIRDIFF-2
METHOD_DIFF = "PAIRDIFF-2"
MIN_CAL_REFS = 3
MIN_REF_SNR = 10.0


def _ref_index(ref_phot) -> dict:
    return {r["source_id"]: r for r in (ref_phot or []) if r.get("status") == "ok" and r.get("flux_ujy") and
            r.get("flux_err_ujy") and r["flux_ujy"] / r["flux_err_ujy"] >= MIN_REF_SNR and r.get("wavelength_um")}


def differential_pair(pair: FluxPair, refs_a, refs_b, tolerance: float, margin_um: float) -> dict:
    """Reference-normalised comparison of one wavelength-matched pair (PAIRDIFF-2).

    Uses reference stars measured in BOTH exposures, each itself wavelength-matched between the
    two exposures under the same rule as the target. The median flux ratio m = f_b/f_a of those
    references estimates the calibration change between the exposures; its uncertainty is
    1.2533 * 1.4826 * MAD / sqrt(n). The target's ratio is divided by m:
        z_cal = (f_b/m - f_a) / sqrt(s_a^2 + (s_b/m)^2 + (f_b * s_m / m^2)^2)
    Each reference's own normalised z (leave-one-out median) is returned so the scatter of
    constant stars can be checked against the error model (CALCHECK-1).
    """
    ia, ib = _ref_index(refs_a), _ref_index(refs_b)
    common = []
    for sid in sorted(set(ia) & set(ib), key=str):
        ra, rb = ia[sid], ib[sid]
        lim = tolerance * min(ra["bandwidth_um"] or 0, rb["bandwidth_um"] or 0)
        if abs(ra["wavelength_um"] - rb["wavelength_um"]) + margin_um <= lim:
            common.append((sid, ra, rb))
    out = {"method": METHOD_DIFF, "n_refs": len(common), "calibrated": len(common) >= MIN_CAL_REFS}
    if not out["calibrated"]:
        out["note"] = f"{len(common)} wavelength-matched reference stars (need {MIN_CAL_REFS}); calibration change not estimated"
        return out
    ratios = np.array([rb["flux_ujy"] / ra["flux_ujy"] for _, ra, rb in common])
    m = float(np.median(ratios))
    mad = float(np.median(np.abs(ratios - m))) * 1.4826
    s_m = 1.2533 * mad / math.sqrt(len(ratios)) if len(ratios) > 1 else float("nan")
    fa, fb, sa, sb = pair.flux_a_ujy, pair.flux_b_ujy, pair.err_a_ujy, pair.err_b_ujy
    denom = math.sqrt(sa ** 2 + (sb / m) ** 2 + (fb * s_m / m ** 2) ** 2)
    z_refs = []
    for i, (sid, ra, rb) in enumerate(common):
        others = np.delete(ratios, i)
        mi = float(np.median(others)) if others.size else m
        d = math.sqrt(ra["flux_err_ujy"] ** 2 + (rb["flux_err_ujy"] / mi) ** 2)
        z_refs.append((rb["flux_ujy"] / mi - ra["flux_ujy"]) / d)
    out.update({"ratio_median": m, "ratio_sigma": s_m, "z_cal": (fb / m - fa) / denom if denom > 0 else float("nan"),
                "ref_z": z_refs, "ref_ids": [c[0] for c in common]})
    return out


def robust_scatter(values) -> float:
    v = np.asarray([x for x in values if x is not None and math.isfinite(x)], float)
    if v.size < 5:
        return float("nan")
    return float(1.4826 * np.median(np.abs(v - np.median(v))))
