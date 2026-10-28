"""Independent astrometric references: SIMBAD (identity) and Gaia DR3 (astrometry).

Endpoints are the standard public TAP services. They are queried only by the
acquisition layer, and every row returned keeps its provenance.
"""

from __future__ import annotations

from ..provenance import Provenance
from ..science.coords import Astrometry
from .net import Fetcher
from .tap import tap_sync

SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap"
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap"
GAIA_DR3 = "Gaia DR3 (doi:10.1051/0004-6361/202243940)"


def resolve_simbad(fetcher: Fetcher, identifier: str) -> tuple[dict, Provenance]:
    ident = identifier.replace("'", "''")
    adql = f"""SELECT b.main_id, b.ra, b.dec, b.coo_bibcode, b.pmra, b.pmdec, b.pm_bibcode,
                      b.plx_value, b.rvz_radvel, b.sp_type, b.otype
               FROM basic AS b JOIN ident AS i ON i.oidref = b.oid
               WHERE i.id = '{ident}'"""
    rows, res = tap_sync(fetcher, SIMBAD_TAP, adql, source="SIMBAD")
    if len(rows) != 1:
        raise LookupError(f"SIMBAD returned {len(rows)} objects for {identifier!r}")
    return rows[0], res.provenance


def gaia_by_id(fetcher: Fetcher, source_id: int) -> tuple[Astrometry, dict, Provenance]:
    adql = f"""SELECT source_id, ra, dec, ra_error, dec_error, pmra, pmdec, pmra_error, pmdec_error,
                      parallax, parallax_error, radial_velocity, ref_epoch, phot_g_mean_mag, ruwe
               FROM gaiadr3.gaia_source WHERE source_id = {int(source_id)}"""
    rows, res = tap_sync(fetcher, GAIA_TAP, adql, source="Gaia Archive", dataset_id=GAIA_DR3)
    if len(rows) != 1:
        raise LookupError(f"Gaia DR3 source {source_id} not found")
    return to_astrometry(rows[0]), rows[0], res.provenance


def gaia_cone(fetcher: Fetcher, ra: float, dec: float, radius_deg: float,
              g_min: float = 10.0, g_max: float = 16.0, limit: int = 500) -> tuple[list[dict], Provenance]:
    """Reference-star candidates. The G range excludes stars likely to be saturated or too faint."""
    adql = f"""SELECT TOP {int(limit)} source_id, ra, dec, ra_error, dec_error, pmra, pmdec,
                      pmra_error, pmdec_error, parallax, radial_velocity, ref_epoch, phot_g_mean_mag, ruwe
               FROM gaiadr3.gaia_source
               WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.7f}, {dec:.7f}, {radius_deg:.6f}))
                 AND phot_g_mean_mag BETWEEN {g_min} AND {g_max}
               ORDER BY phot_g_mean_mag"""
    rows, res = tap_sync(fetcher, GAIA_TAP, adql, source="Gaia Archive", dataset_id=GAIA_DR3)
    return rows, res.provenance


def to_astrometry(row: dict) -> Astrometry:
    f = lambda k: float(row[k]) if row.get(k) is not None else 0.0
    return Astrometry(ra=f("ra"), dec=f("dec"), ref_epoch=f("ref_epoch") or 2016.0, pmra=f("pmra"),
                      pmdec=f("pmdec"), parallax=f("parallax"), radial_velocity=f("radial_velocity"),
                      source=f"{GAIA_DR3} source_id={row.get('source_id')}")
