"""SPHEREx Spectral Image discovery and cutout retrieval at IRSA.

Interfaces used (documented by IRSA; see docs/DATA_FEASIBILITY_REPORT.md):
  * SIA2   https://irsa.ipac.caltech.edu/SIA  with COLLECTION = spherex_qr3 | spherex_qr2
           (release is explicit in the collection name)
  * TAP    https://irsa.ipac.caltech.edu/TAP  tables spherex.plane / spherex.artifact
           (no ingestion delay; release inferred from the file path)
  * Cutouts: append ?center=<ra>,<dec>d&size=<deg> to an on-prem image URL.

Discovery, download and processing are separate steps. Discovery returns
metadata only; nothing here measures anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..provenance import Provenance
from .net import Fetcher, FetchResult
from .tap import parse_votable, tap_sync, validate_votable

IRSA = "https://irsa.ipac.caltech.edu"
SIA_URL = f"{IRSA}/SIA"
TAP_URL = f"{IRSA}/TAP"
RELEASES = {
    "QR3": {"collection": "spherex_qr3", "doi": "10.26131/IRSA662"},
    "QR2": {"collection": "spherex_qr2", "doi": "10.26131/IRSA652"},
}
DETECTOR_BANDS_UM = {1: (0.75, 1.09), 2: (1.10, 1.62), 3: (1.63, 2.41),
                     4: (2.42, 3.82), 5: (3.83, 4.41), 6: (4.42, 5.00)}  # IRSA data-products page
_FNAME = re.compile(r"level2_(?P<obs>[0-9A-Za-z_]+?)D(?P<det>[1-6])_spx_l2b", re.IGNORECASE)
_REL = re.compile(r"/(qr\d)/", re.IGNORECASE)


@dataclass(frozen=True)
class Observation:
    """One SPHEREx Spectral Image (one detector, one pointing) covering a position."""
    release: str
    obs_id: str
    detector: int | None
    t_mid_mjd: float | None
    t_min_mjd: float | None
    t_max_mjd: float | None
    em_min_um: float | None     # image-wide wavelength range; NOT the wavelength at the source
    em_max_um: float | None
    access_url: str
    discovered_via: str         # "SIA:spherex_qr3" or "TAP"
    raw: dict = field(default_factory=dict, compare=False, repr=False)


def parse_filename(url: str) -> tuple[str | None, int | None]:
    m = _FNAME.search(url or "")
    return (m.group("obs"), int(m.group("det"))) if m else (None, None)


def release_from_path(url: str) -> str:
    m = _REL.search(url or "")
    return m.group(1).upper() if m else "UNKNOWN"


def _m_to_um(v):
    return None if v is None else float(v) * 1e6


def _detector(row: dict, url: str) -> int | None:
    name = str(row.get("energy_bandpassname") or "")
    m = re.search(r"D([1-6])\b", name)
    if m:
        return int(m.group(1))
    return parse_filename(url)[1]


def observations_from_sia(rows: list[dict], release: str) -> list[Observation]:
    out = []
    for r in rows:
        url = str(r.get("access_url") or "")
        obs_fn, _ = parse_filename(url)
        tmin, tmax = r.get("t_min"), r.get("t_max")
        out.append(Observation(
            release=release, obs_id=str(r.get("obs_id") or obs_fn or url),
            detector=_detector(r, url),
            t_mid_mjd=(tmin + tmax) / 2 if tmin is not None and tmax is not None else tmin,
            t_min_mjd=tmin, t_max_mjd=tmax,
            em_min_um=_m_to_um(r.get("em_min")), em_max_um=_m_to_um(r.get("em_max")),
            access_url=url, discovered_via=f"SIA:{RELEASES[release]['collection']}", raw=r))
    return sorted(out, key=lambda o: (o.t_mid_mjd or 0, o.detector or 0))


def discover_sia(fetcher: Fetcher, ra: float, dec: float, release: str = "QR3",
                 radius_deg: float = 1 / 3600) -> tuple[list[Observation], Provenance]:
    rel = RELEASES[release]
    res: FetchResult = fetcher.get(
        SIA_URL, {"COLLECTION": rel["collection"], "POS": f"CIRCLE {ra:.7f} {dec:.7f} {radius_deg:.7f}",
                  "RESPONSEFORMAT": "votable"},
        source="IRSA", kind="metadata", release=release, dataset_id=rel["doi"], validate=validate_votable)
    return observations_from_sia(parse_votable(res.content), release), res.provenance


def discover_tap(fetcher: Fetcher, ra: float, dec: float) -> tuple[list[Observation], Provenance]:
    """Cross-check discovery via TAP. Only columns shown in IRSA's cutout tutorial are requested."""
    adql = f"""SELECT a.uri, p.time_bounds_lower, p.energy_bandpassname, p.planeid
               FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid
               WHERE CONTAINS(POINT('ICRS', {ra:.7f}, {dec:.7f}), p.poly) = 1
               ORDER BY p.time_bounds_lower"""
    rows, res = tap_sync(fetcher, TAP_URL, adql, source="IRSA")
    out = []
    for r in rows:
        url = f"{IRSA}/{str(r.get('uri', '')).lstrip('/')}"
        obs_fn, _ = parse_filename(url)
        out.append(Observation(release_from_path(url), obs_fn or str(r.get("planeid")), _detector(r, url),
                               None, r.get("time_bounds_lower"), None, None, None, url, "TAP", r))
    return out, res.provenance


def list_columns(fetcher: Fetcher, table: str) -> list[dict]:
    """Record the actual schema of a TAP table (feasibility step)."""
    rows, _ = tap_sync(fetcher, TAP_URL,
                       f"SELECT column_name, datatype, unit, description FROM TAP_SCHEMA.columns WHERE table_name = '{table}'",
                       source="IRSA")
    return rows


def cutout_url(access_url: str, ra: float, dec: float, size_deg: float) -> str:
    if not access_url.startswith(IRSA + "/"):
        raise ValueError(f"cutouts are only requested from IRSA on-prem URLs, got {access_url!r}")
    if not (0 < size_deg <= 0.5):
        raise ValueError("cutout size must be in (0, 0.5] deg to keep downloads bounded")
    base = access_url.split("?")[0]
    return f"{base}?center={ra:.7f},{dec:.7f}d&size={size_deg:g}"


def validate_fits(content: bytes) -> None:
    if not content.startswith(b"SIMPLE  ="):
        raise ValueError("response is not a FITS file")


def fetch_cutout(fetcher: Fetcher, obs: Observation, ra: float, dec: float,
                 size_deg: float = 0.1) -> FetchResult:
    rel = RELEASES.get(obs.release, {})
    return fetcher.get(cutout_url(obs.access_url, ra, dec, size_deg), source="IRSA", kind="raw",
                       release=obs.release, dataset_id=rel.get("doi", ""), validate=validate_fits)
