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
                            d / s if s > 0 else float("nan"), fb[0] / fa[0] if fa[0] > 0 else float("nan")))
    return out, skipped
