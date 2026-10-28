"""Wavelength-compatibility rules for comparing SPHEREx observations over time.

Each SPHEREx detector sits behind a linear variable filter, so the wavelength a
source is observed at depends on where it falls on the detector. Two exposures
of the same star on different dates usually sample different wavelengths; a
flux difference between them is then dominated by the source's spectral shape,
not by variability.

The rule implemented here (version WLMATCH-1):

  Two observations of a source are photometrically comparable only if
    1. they come from the same detector (D1..D6),
    2. |lambda_1 - lambda_2| <= tolerance * min(bandwidth_1, bandwidth_2),
       with tolerance = 0.5 by default (half a spectral channel), and
    3. both have usable photometry (quality status "ok").

Astrometric comparison does not require matched wavelength, but chromatic
effects (wavelength-dependent PSF and distortion) are a known systematic, so
astrometric pairs record their wavelength difference as well.

Every candidate pair is returned with an explicit accept/reject reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

RULE_VERSION = "WLMATCH-1"


@dataclass(frozen=True)
class SourceSample:
    """One observation of one source, reduced to what the matching rule needs."""
    obs_id: str
    detector: int            # 1..6
    mjd: float               # mid-exposure time
    wavelength_um: float     # central wavelength at the source's pixel position
    bandwidth_um: float      # channel bandwidth at that position
    quality: str = "ok"      # "ok" or a short reason it is unusable


@dataclass(frozen=True)
class PairDecision:
    a: str
    b: str
    accepted: bool
    reason: str
    delta_lambda_um: float
    delta_t_days: float
    rule: str = RULE_VERSION


def compare_pair(s1: SourceSample, s2: SourceSample, tolerance: float = 0.5,
                 min_dt_days: float = 0.0) -> PairDecision:
    first, second = sorted((s1, s2), key=lambda s: s.mjd)
    dl = abs(first.wavelength_um - second.wavelength_um)
    dt = second.mjd - first.mjd

    def decide(ok: bool, reason: str) -> PairDecision:
        return PairDecision(first.obs_id, second.obs_id, ok, reason, dl, dt)

    if first.obs_id == second.obs_id:
        return decide(False, "same observation")
    if first.detector != second.detector:
        return decide(False, f"different detectors (D{first.detector} vs D{second.detector})")
    for s in (first, second):
        if s.quality != "ok":
            return decide(False, f"{s.obs_id} unusable: {s.quality}")
        if not (s.bandwidth_um > 0):
            return decide(False, f"{s.obs_id} has no valid bandwidth")
    limit = tolerance * min(first.bandwidth_um, second.bandwidth_um)
    if dl > limit:
        return decide(False, f"wavelength mismatch: |dλ|={dl:.4f} µm > {limit:.4f} µm")
    if dt < min_dt_days:
        return decide(False, f"time baseline {dt:.2f} d < required {min_dt_days:.2f} d")
    return decide(True, f"|dλ|={dl:.4f} µm <= {limit:.4f} µm, same detector")


def match_pairs(samples: list[SourceSample], tolerance: float = 0.5,
                min_dt_days: float = 0.0) -> list[PairDecision]:
    """Evaluate all pairs. Returns every decision (accepted and rejected), sorted."""
    out = [compare_pair(a, b, tolerance, min_dt_days) for a, b in combinations(samples, 2)]
    return sorted(out, key=lambda d: (not d.accepted, d.a, d.b))
