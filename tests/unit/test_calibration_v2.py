"""Phase 3 calibration methods: REFSEL-2, LINFIT-EPOCH-1, WLMATCH-2 codes, PAIRDIFF-2, SIA detector parsing."""

import math

import numpy as np
import pytest

from skytrace.archive.spherex import observations_from_sia
from skytrace.science.astrometry import epoch_average, fit_linear_motion, group_epochs
from skytrace.science.refsel import select_references
from skytrace.science.variability import FluxPair, differential_pair, robust_scatter
from skytrace.science.wavelength import PAIR_CODES, SourceSample, compare_pair, match_pairs


def test_refsel2_cuts_and_counts():
    stars = [
        {"source_id": 1, "pmra": 1, "pmdec": 1, "ruwe": 1.0, "duplicated_source": False, "astrometric_params_solved": 31},
        {"source_id": 2, "pmra": 1, "pmdec": 1, "ruwe": 2.0},
        {"source_id": 3, "pmra": None, "pmdec": None},
        {"source_id": 4, "pmra": 1, "pmdec": 1, "ruwe": 1.1, "duplicated_source": "true"},
        {"source_id": 5, "pmra": 1, "pmdec": 1, "astrometric_params_solved": 3},
        {"source_id": 6, "pmra": 1, "pmdec": 1},
    ]
    kept, rec = select_references(stars)
    assert [s["source_id"] for s in kept] == [1, 6]
    assert rec["rejected"] == {"no_proper_motion": 1, "ruwe_high": 1, "duplicated_source": 1, "params_solved_low": 1}
    assert rec["accepted_unchecked"]["ruwe_missing"] == 1


def test_epoch_grouping_and_error_floor():
    t = [0.0, 0.1, 0.2, 10.0, 10.1, 30.0]
    groups = group_epochs(t, gap_days=3.0)
    assert groups == [[0, 1, 2], [3, 4], [5]]
    xi = [0.0, 100.0, -100.0, 5.0, 5.0, 7.0]
    ep = epoch_average(t, xi, xi, [10.0] * 6, [10.0] * 6, groups)
    # formal error 10/sqrt(3) = 5.8, empirical 100/sqrt(3) = 57.7: the larger is used
    assert ep[0]["sig_xi_mas"] == pytest.approx(100 / math.sqrt(3), rel=1e-9)
    assert ep[1]["sig_xi_mas"] == pytest.approx(10 / math.sqrt(2))     # n < 3: formal only
    assert ep[2]["n_exposures"] == 1


def test_epoch_fit_does_not_shrink_correlated_errors():
    """Within-visit offsets shared by all exposures (correlated) must not produce an over-confident pm."""
    rng = np.random.default_rng(1)
    t, x, s = [], [], []
    for k, t0 in enumerate([0.0, 180.0, 365.0, 545.0]):
        offset = rng.normal(0, 200)                 # per-visit systematic, mas
        for j in range(12):
            t.append(t0 + j * 0.05); x.append(offset + rng.normal(0, 50)); s.append(50.0)
    groups = group_epochs(t, 3.0)
    ep = epoch_average(t, x, x, s, s, groups)
    ty = [e["t_mjd"] / 365.25 for e in ep]
    fe = fit_linear_motion(ty, [e["xi_mas"] for e in ep], [e["eta_mas"] for e in ep],
                           [e["sig_xi_mas"] for e in ep], [e["sig_eta_mas"] for e in ep])
    fx = fit_linear_motion([v / 365.25 for v in t], x, x, s, s)
    # truth is 0 mas/yr; the epoch fit must cover it within 3 sigma
    assert abs(fe.pm_xi_mas_yr) < 3 * fe.sig_xi
    assert fe.sig_xi > fx.sig_xi * 0.9  # never more confident than the per-exposure fit by construction of the floor


def test_pair_codes_structured():
    a = SourceSample("a", 2, 0.0, 1.500, 0.010, "ok", "QR3")
    assert compare_pair(a, SourceSample("b", 3, 1, 1.5, 0.01, "ok", "QR3")).code == "different_detectors"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.5, 0.01, "photometry_flagged", "QR3")).code == "unusable_measurement"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.5, 0.01, "ok", "QR2"), same_release=True).code == "different_releases"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.5, 0.01, "ok", "QR2")).code == "accepted"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.5049, 0.01, "ok", "QR3"), margin_um=0.002).code == "wavelength_ambiguous"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.5049, 0.01, "ok", "QR3")).code == "accepted"
    assert compare_pair(a, SourceSample("b", 2, 1, 1.51, 0.01, "ok", "QR3")).code == "wavelength_mismatch"
    for d in match_pairs([a, SourceSample("b", 2, 1, 1.5, 0.01), SourceSample("c", 1, 2, 1.0, 0.01)]):
        assert d.code in PAIR_CODES


def _refs(gain, n=6, wl=1.5, noise=None):
    rng = np.random.default_rng(3)
    out = []
    for i in range(n):
        f = 1000.0 * (i + 1)
        e = 10.0
        out.append({"source_id": i, "flux_ujy": f * gain + (noise and rng.normal(0, e) or 0.0), "flux_err_ujy": e,
                    "status": "ok", "wavelength_um": wl, "bandwidth_um": 0.01})
    return out


def test_pairdiff2_removes_calibration_offset():
    """A 5% gain change between exposures makes PAIRDIFF-1 flag a constant star; PAIRDIFF-2 does not."""
    fa, fb, e = 5000.0, 5250.0, 10.0
    pair = FluxPair("a", "b", 10, 0, fa, fb, fb - fa, math.hypot(e, e), (fb - fa) / math.hypot(e, e), fb / fa,
                    err_a_ujy=e, err_b_ujy=e)
    assert abs(pair.z) > 5
    dp = differential_pair(pair, _refs(1.0), _refs(1.05), 0.5, 0.002)
    assert dp["calibrated"] and dp["n_refs"] == 6
    assert dp["ratio_median"] == pytest.approx(1.05)
    assert abs(dp["z_cal"]) < 1e-6


def test_pairdiff2_needs_three_matched_refs():
    pair = FluxPair("a", "b", 10, 0, 1.0, 1.0, 0, 1, 0, 1, err_a_ujy=1, err_b_ujy=1)
    refs_b = _refs(1.0, wl=1.52)      # references fell at a different wavelength in exposure b
    dp = differential_pair(pair, _refs(1.0), refs_b, 0.5, 0.002)
    assert not dp["calibrated"] and dp["n_refs"] == 0 and "need 3" in dp["note"]


def test_robust_scatter():
    assert math.isnan(robust_scatter([1, 2]))
    v = np.random.default_rng(0).normal(0, 2.0, 4000)
    assert robust_scatter(v) == pytest.approx(2.0, rel=0.05)


def test_sia_detector_from_publisher_did():
    # Identifiers below are format examples built from the documented file-name pattern, not real observations.
    rows = [{"access_url": "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/cutout?x=1", "t_min": 60800.0,
             "t_max": 60800.01, "energy_bandpassname": "Infrared", "obs_id": "2025W20_1A_0123_4",
             "obs_publisher_did": "ivo://irsa.ipac/spherex_qr2?level2_2025W20_1A_0123_4D3_spx_l2b-v24-2025-200",
             "em_min": 1.63e-6, "em_max": 2.41e-6}]
    (o,) = observations_from_sia(rows, "QR2")
    assert o.detector == 3 and o.obs_id == "2025W20_1A_0123_4"
