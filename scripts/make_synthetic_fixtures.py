"""Generate SYNTHETIC target bundles for development, tests and the offline demo.

These are NOT observations. Every FITS file carries SYNTHETIC = T, every file
has provenance origin "synthetic", targets have names (SYN-...) that cannot be
confused with real objects, and the application watermarks their images.

The files imitate the documented SPHEREx Level-2 layout (IMAGE, FLAGS,
VARIANCE, ZODI, WCS-WAVE; TAN-SIP celestial WCS; -TAB spectral WCS with key W)
so that the real reading/measurement path is exercised end to end. Values
(PSF width, noise, LVF gradient, flag bit numbers) are illustrative choices,
not SPHEREx calibration.

    python scripts/make_synthetic_fixtures.py          # writes fixtures/synthetic/{syn-hpm-1,syn-var-1}
"""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import bundle as bmod  # noqa: E402
from skytrace import fitsio  # noqa: E402
from skytrace.archive.spherex import DETECTOR_BANDS_UM  # noqa: E402
from skytrace.provenance import synthetic  # noqa: E402
from skytrace.science.coords import Astrometry, mjd_to_jyear, propagate  # noqa: E402
from skytrace.wcs import CelestialWCS  # noqa: E402

R_BY_DET = {1: 39, 2: 41, 3: 41, 4: 35, 5: 112, 6: 128}   # documented resolving powers
PIX_ARCSEC = 6.2
OMEGA_SR = (PIX_ARCSEC / 206264.80624709636) ** 2
SIZE = 58                                                  # ~0.1 deg at 6.2"/px
FLAG_BITS = {"MP_TRANSIENT": 0, "MP_OVERFLOW": 1, "MP_SUR_ERROR": 2, "MP_NONFUNC": 3, "MP_MISSING_DATA": 4,
             "MP_HOT": 5, "MP_COLD": 6, "MP_PERSIST": 7, "MP_OUTLIER": 8, "MP_NONLINEAR": 9, "MP_SOURCE": 21}
GEN = "scripts/make_synthetic_fixtures.py"


def lvf(det: int, xd: float, yd: float) -> tuple[float, float]:
    """Illustrative linear variable filter: wavelength runs along detector y, slight x tilt."""
    lo, hi = DETECTOR_BANDS_UM[det]
    wl = lo + (hi - lo) * ((yd - 1) / 2039.0 + 0.004 * (xd - 1020.0) / 1020.0)
    return wl, wl / R_BY_DET[det]


def wcs_wave_table(det: int) -> fitsio.HDU:
    X = np.linspace(1, 2040, 11)
    Y = np.linspace(1, 2040, 11)
    vals = np.zeros((11, 11, 2))
    for j, y in enumerate(Y):
        for i, x in enumerate(X):
            vals[j, i] = lvf(det, x, y)
    h = fitsio.Header({"SYNTHETIC": True})
    return fitsio.HDU("WCS-WAVE", h, {"X": X[None, :], "Y": Y[None, :], "VALUES": vals[None]}, "table", ["X", "Y", "VALUES"])


def make_header(det: int, crval: tuple[float, float], rot_deg: float, x0: int, y0: int, mjd: float) -> fitsio.Header:
    s = PIX_ARCSEC / 3600.0
    th = math.radians(rot_deg)
    h = fitsio.Header()
    h.update({
        "SYNTHETIC": True, "BUNIT": "MJy/sr", "DETECTOR": det,
        "WCSAXES": 2, "CTYPE1": "RA---TAN-SIP", "CTYPE2": "DEC--TAN-SIP", "RADESYS": "ICRS",
        "CRPIX1": SIZE / 2 + 0.5, "CRPIX2": SIZE / 2 + 0.5, "CRVAL1": crval[0], "CRVAL2": crval[1],
        "CD1_1": -s * math.cos(th), "CD1_2": s * math.sin(th), "CD2_1": s * math.sin(th), "CD2_2": s * math.cos(th),
        "A_ORDER": 2, "A_2_0": 2.0e-5, "A_1_1": -1.0e-5, "A_0_2": 1.5e-5,
        "B_ORDER": 2, "B_2_0": -1.2e-5, "B_1_1": 2.0e-5, "B_0_2": 1.0e-5,
        # spectral -TAB WCS (alternate key W) pointing at WCS-WAVE; psi = detector pixel = cutout pixel + offset
        "WCSAXESW": 2, "CTYPE1W": "WAVE-TAB", "CTYPE2W": "WAVE-TAB", "CUNIT1W": "um", "CUNIT2W": "um",
        "CRPIX1W": 0.0, "CRPIX2W": 0.0, "CRVAL1W": float(x0), "CRVAL2W": float(y0), "CDELT1W": 1.0, "CDELT2W": 1.0,
        "PS1_0W": "WCS-WAVE", "PS1_1W": "VALUES", "PS1_2W": "X", "PV1_3W": 1,
        "PS2_0W": "WCS-WAVE", "PS2_1W": "VALUES", "PS2_2W": "Y", "PV2_3W": 2,
        "MJD-AVG": mjd, "COMMENT1": "synthetic test image, not an observation",
    })
    return h


def render(det, header, stars, rng, sky, noise, hot=3, overflow_at=None):
    """stars: list of (ra, dec, flux_ujy). Returns IMAGE, VARIANCE, FLAGS, ZODI."""
    w = CelestialWCS(header)
    sigma = 0.55 + 0.12 * det          # illustrative: PSF widens with wavelength
    yy, xx = np.indices((SIZE, SIZE))
    img = np.full((SIZE, SIZE), sky, float)
    for ra, dec, f in stars:
        x, y = w.world_to_pixel(ra, dec)
        x, y = float(x), float(y)
        if -5 < x < SIZE + 5 and -5 < y < SIZE + 5:
            peak = f / (2 * math.pi * sigma ** 2 * OMEGA_SR * 1e12)
            img += peak * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / sigma ** 2)
    var = noise ** 2 + 0.004 * np.clip(img - sky, 0, None)
    img = img + rng.normal(0, np.sqrt(var))
    flags = np.zeros((SIZE, SIZE), np.int32)
    for _ in range(hot):
        hx, hy = rng.integers(0, SIZE, 2)
        img[hy, hx] += 50 * noise
        flags[hy, hx] |= 1 << FLAG_BITS["MP_HOT"]
    if overflow_at is not None:
        ox, oy = (int(round(v)) for v in overflow_at)
        flags[oy - 1:oy + 2, ox - 1:ox + 2] |= 1 << FLAG_BITS["MP_OVERFLOW"]
    zodi = np.full((SIZE, SIZE), sky, float)
    return img.astype(np.float32), var.astype(np.float32), flags, zodi.astype(np.float32)


def mjd_to_iso(mjd: float) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=mjd)).isoformat(timespec="seconds")


def build(spec: dict) -> Path:
    out = bmod.SYNTHETIC_ROOT / spec["target_id"]
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    rng = np.random.default_rng(spec["seed"])
    tgt = Astrometry(spec["ra"], spec["dec"], 2016.0, spec["pmra"], spec["pmdec"])
    refs = []
    for i in range(spec["n_refs"]):
        dx, dy = rng.uniform(-0.042, 0.042, 2)
        refs.append({"source_id": f"SYN-REF-{spec['seed']}-{i:03d}", "ra": spec["ra"] + dx / math.cos(math.radians(spec["dec"])),
                     "dec": spec["dec"] + dy, "ref_epoch": 2016.0, "pmra": float(rng.normal(0, 8)),
                     "pmdec": float(rng.normal(0, 8)), "flux_ujy": float(10 ** rng.uniform(2.9, 3.9)),
                     "g_mag_synthetic": None})
    # one catalogue error: injected 4" away from where the catalogue says (exercises outlier rejection)
    bad_ref = refs[0]
    true_offsets = {bad_ref["source_id"]: (4.0 / 3600.0, 0.0)}
    files, observations = {}, []
    prov = lambda note: {"provenance": synthetic(note).to_dict()}
    passes = spec["passes"]
    for p_i, (mjd0, ybase) in enumerate(passes):
        for v_i in range(2):
            mjd = mjd0 + 2.5 * v_i
            ep = float(mjd_to_jyear(mjd))
            tra, tdec = propagate(tgt, ep)
            crval = (tra + rng.normal(0, 8) * PIX_ARCSEC / 3600 / math.cos(math.radians(tdec)),
                     tdec + rng.normal(0, 8) * PIX_ARCSEC / 3600)
            rot = float(rng.normal(0, 0.4))
            obs_id = f"SYN{p_i + 1}{v_i + 1}_{spec['seed']}"
            for det in range(1, 7):
                key = f"SYNTHETIC:{obs_id}:D{det}"
                yd = ybase + rng.normal(0, 3) + 25 * det
                xd = 1020 + rng.normal(0, 150)
                x0, y0 = int(round(xd)) - SIZE // 2, int(round(yd)) - SIZE // 2
                h = make_header(det, crval, rot, x0, y0, mjd)
                wl, bw = lvf(det, xd, yd)
                factor = spec["variability"][p_i]
                stars = [(tra, tdec, spec["sed"](wl) * factor)]
                for r in refs:
                    ra_r, dec_r = propagate(Astrometry(r["ra"], r["dec"], 2016.0, r["pmra"], r["pmdec"]), ep)
                    off = true_offsets.get(r["source_id"], (0.0, 0.0))
                    stars.append((ra_r + off[0], dec_r + off[1], r["flux_ujy"] * (wl / 1.5) ** -0.3))
                over = None
                if (p_i, v_i, det) in spec.get("overflow", []):
                    over = CelestialWCS(h).world_to_pixel(tra, tdec)
                img, var, flags, zodi = render(det, h, stars, rng, spec["sky"], spec["noise"], overflow_at=over)
                fh = fitsio.Header({"SYNTHETIC": True})
                fh.update({k: v for k, v in FLAG_BITS.items()})
                hdus = [fitsio.HDU("PRIMARY", fitsio.Header({"SYNTHETIC": True, "ORIGIN": "SKYTRACE synthetic generator"})),
                        fitsio.HDU("IMAGE", h, img), fitsio.HDU("FLAGS", fh, flags),
                        fitsio.HDU("VARIANCE", fitsio.Header({"SYNTHETIC": True, "BUNIT": "(MJy/sr)^2"}), var),
                        fitsio.HDU("ZODI", fitsio.Header({"SYNTHETIC": True, "BUNIT": "MJy/sr"}), zodi)]
                if (p_i, v_i, det) not in spec.get("no_wave", []):
                    hdus.append(wcs_wave_table(det))
                rel = f"images/SYNTHETIC_{obs_id}_D{det}.fits"
                fitsio.write(out / rel, hdus)
                files[rel] = {"role": "image", "obs_key": key, **prov(f"seed={spec['seed']}")}
                lo, hi = DETECTOR_BANDS_UM[det]
                observations.append({"key": key, "release": "SYNTHETIC", "obs_id": obs_id, "detector": det,
                                     "t_min_mjd": mjd - 0.0006, "t_max_mjd": mjd + 0.0006, "t_mid_mjd": mjd,
                                     "t_mid_iso": mjd_to_iso(mjd), "em_min_um": lo, "em_max_um": hi,
                                     "access_url": "", "file": rel, "included": True})
    for k in range(2):  # search results that the selection step excludes (exercises the rejection path)
        observations.append({"key": f"SYNTHETIC:SYNX{k}_{spec['seed']}:D{k + 2}", "release": "SYNTHETIC",
                             "obs_id": f"SYNX{k}_{spec['seed']}", "detector": k + 2, "t_mid_mjd": passes[0][0] + 40 + k,
                             "t_mid_iso": mjd_to_iso(passes[0][0] + 40 + k), "em_min_um": None, "em_max_um": None,
                             "access_url": "", "file": None, "included": False,
                             "exclusion_reason": "target falls within 4 px of the image edge at this epoch"})
    target = {"target_id": spec["target_id"], "name": spec["name"], "kind": "synthetic", "role": spec["role"],
              "identity": {"catalogue": "synthetic (generated)", "description": spec["description"]},
              "astrometry": {"ra": spec["ra"], "dec": spec["dec"], "ref_epoch": 2016.0, "pmra": spec["pmra"],
                             "pmdec": spec["pmdec"], "parallax": 0.0, "radial_velocity": 0.0,
                             "source": "synthetic catalogue (generator input)"}}
    bmod.write_json(out / "target.json", target)
    bmod.write_json(out / "references.json", {"catalogue": "synthetic reference catalogue", "stars": refs,
                                              "notes": f"{bad_ref['source_id']} is deliberately injected 4\" from its catalogue position"})
    bmod.write_json(out / "discovery.json", {
        "observations": observations,
        "selection": {"criteria": ["image footprint contains the target at the observation epoch",
                                   "target at least 4 px from the image edge"],
                      "note": "synthetic search results"}})
    for n in ("target.json", "references.json", "discovery.json"):
        files[n] = {"role": n.split(".")[0], **prov(f"seed={spec['seed']}")}
    bmod.write_manifest(out, spec["target_id"], "synthetic", files, GEN,
                        notes="SYNTHETIC test data generated by code. Not an astronomical observation.")
    return out


SPECS = [
    {"target_id": "syn-hpm-1", "name": "SYN-HPM-1", "seed": 11, "ra": 210.25, "dec": -32.6, "pmra": 3200.0, "pmdec": -3400.0,
     "role": "synthetic high-proper-motion star (tests motion recovery)",
     "description": "Generated star moving 4.67\"/yr among 18 reference stars; constant brightness.",
     "n_refs": 18, "sky": 0.3, "noise": 0.012, "variability": [1.0, 1.0, 1.0, 1.0],
     "sed": lambda wl: 6000.0 * (wl / 1.2) ** -1.2 * (1 - 0.35 * math.exp(-((wl - 3.3) / 0.25) ** 2)),
     "passes": [(60832.0, 520.0), (61014.0, 1420.0), (61197.0, 532.0), (61379.0, 1010.0)],
     "no_wave": [(1, 1, 6)]},
    {"target_id": "syn-var-1", "name": "SYN-VAR-1", "seed": 23, "ra": 77.0, "dec": 30.4, "pmra": 3.0, "pmdec": -27.0,
     "role": "synthetic variable star (tests wavelength-matched variability)",
     "description": "Generated star that dims to 62% of its brightness in the third pass; negligible motion.",
     "n_refs": 16, "sky": 0.35, "noise": 0.012, "variability": [1.0, 1.0, 0.62, 0.8],
     "sed": lambda wl: 4000.0 * (wl / 1.5) ** -0.5,
     "passes": [(60845.0, 700.0), (61027.0, 1500.0), (61210.0, 708.0), (61392.0, 1200.0)],
     "overflow": [(3, 1, 1)]},
]


if __name__ == "__main__":
    for s in SPECS:
        print("wrote", build(s))
