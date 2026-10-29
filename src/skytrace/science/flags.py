"""SPHEREx FLAGS-extension bit handling.

Bit numbers are only taken from (a) the FLAGS header of the actual file, when it
defines MP_* keywords, or (b) values documented by IRSA. Unknown bit numbers
are reported, never guessed.

Documented (IRSA "Introduction to SPHEREx Spectral Images" tutorial):
  MP_TRANSIENT = bit 0  (transient detected during sample-up-the-ramp fitting)
  MP_SOURCE    = bit 21 (pixel mapped to a known source; informational)
The full table is in the SPHEREx Explanatory Supplement, Table 10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

DOCUMENTED_BITS: dict[str, int] = {"MP_TRANSIENT": 0, "MP_SOURCE": 21}

# Policy (version FLAGPOL-1). Names only; bit numbers resolved per file.
REJECT = ("MP_TRANSIENT", "MP_OVERFLOW", "MP_SUR_ERROR", "MP_NONFUNC", "MP_MISSING_DATA",
          "MP_HOT", "MP_COLD", "MP_PERSIST", "MP_OUTLIER", "MP_PHANTOM", "MP_PHANMISS")
WARN = ("MP_NONLINEAR", "MP_DICHROIC", "MP_FULLSAMPLE", "MP_REFERENCE")
INFO = ("MP_SOURCE",)
POLICY_VERSION = "FLAGPOL-1"


@dataclass(frozen=True)
class FlagMap:
    bits: dict[str, int]
    origin: str                       # "header" or "documented"
    unresolved: tuple[str, ...] = field(default_factory=tuple)

    def mask(self, flags: np.ndarray, names) -> np.ndarray:
        m = np.zeros(flags.shape, dtype=bool)
        for n in names:
            if n in self.bits:
                m |= (flags.astype(np.int64) >> self.bits[n]) & 1 == 1
        return m


def resolve_bits(header: Mapping | None = None) -> FlagMap:
    """Read MP_* bit definitions from a FLAGS header if present, else use documented bits."""
    bits: dict[str, int] = {}
    if header is not None:
        import re
        for k, v in dict(header).items():
            ku = str(k).upper()
            # style 1:  MP_OVERFLOW = 5
            if ku.startswith("MP_") and isinstance(v, (int, np.integer)) and not isinstance(v, bool) and 0 <= int(v) < 64:
                bits[ku] = int(v)
            # style 2:  BIT05 = 'MP_OVERFLOW'  (or FLAG05)
            m = re.fullmatch(r"(?:BIT|FLAG)_?(\d{1,2})", ku)
            if m and isinstance(v, str) and v.strip().upper().startswith("MP_"):
                bits[v.strip().upper()] = int(m.group(1))
    origin = "header" if bits else "documented"
    if not bits:
        bits = dict(DOCUMENTED_BITS)
    wanted = set(REJECT) | set(WARN) | set(INFO)
    return FlagMap(bits, origin, tuple(sorted(wanted - set(bits))))


@dataclass(frozen=True)
class FlagSummary:
    n_pixels: int
    n_reject: int
    n_warn: int
    reject_names: tuple[str, ...]
    warn_names: tuple[str, ...]
    unresolved: tuple[str, ...]
    policy: str = POLICY_VERSION


def summarize(flags: np.ndarray, region: np.ndarray, fmap: FlagMap) -> FlagSummary:
    """Summarise flags inside a boolean region (e.g. a photometric aperture)."""
    f = flags[region]
    rej = [n for n in REJECT if n in fmap.bits and fmap.mask(f, [n]).any()]
    warn = [n for n in WARN if n in fmap.bits and fmap.mask(f, [n]).any()]
    return FlagSummary(int(region.sum()), int(fmap.mask(f, REJECT).sum()), int(fmap.mask(f, WARN).sum()),
                       tuple(rej), tuple(warn), fmap.unresolved)
