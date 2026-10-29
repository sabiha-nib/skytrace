"""ASSESS-2: every documented outcome is reachable and carries sensitivity, inputs and threshold provenance."""

from skytrace.science import assess


def motion(pm=(0.0, 0.0), sig=(50.0, 50.0), consistent=True, baseline=1.5, plx=True):
    return {"fit": {"pm_xi_mas_yr": pm[0], "pm_eta_mas_yr": pm[1], "sig_xi": sig[0], "sig_eta": sig[1],
                    "n_epochs": 4, "baseline_yr": baseline, "reduced_chi2": 1.0},
            "comparison": {"z_pmra": 0.0, "z_pmdec": 0.0, "consistent_within_3sigma": consistent},
            "fit_kind": "epoch", "catalogue": {"source": "test"},
            "parallax": {"applied": plx, "systematic_bound_mas": 5.0}}


def cat(m, catalogue=(0.0, 0.0), rms=(20.0,), gaps=(0.5,), n=20, err=None):
    return assess.assess_motion(m, {"pmra": catalogue[0], "pmdec": catalogue[1]}, n, list(rms), list(gaps), err)


def test_motion_outcomes():
    assert cat(None, n=1)["category"] == "insufficient_evidence"
    o = cat(None, n=20, err="singular matrix")
    assert o["category"] == "measurement_failed" and "not evidence" in o["statement"]
    o = cat(motion((3000, -3000)), (3000, -3000))
    assert o["category"] == "motion_detected"
    assert cat(motion((3000, -3000), consistent=False), (1000, 0), rms=(20,))["category"] == "motion_inconsistent"
    o = cat(motion((10, 10)), (5, 5))
    assert o["category"] == "no_motion_at_sensitivity" and "not proof" in o["statement"]
    assert abs(o["sensitivity"]["min_detectable_pm_mas_yr_5sigma"] - 250.0) < 1e-9
    # catalogue predicts a detectable motion, not recovered, registration noise larger than expected step
    assert cat(motion((10, 10), consistent=False), (1000, 0), rms=(800,))["category"] == "registration_limited"
    # same, but registration is good: inconsistent
    assert cat(motion((10, 10), consistent=False), (1000, 0), rms=(20,))["category"] == "motion_inconsistent"


def fp(z, calibrated=True, zc=None, flux=1000.0, sigma=10.0):
    d = {"calibrated": calibrated}
    if calibrated:
        d["z_cal"] = z if zc is None else zc
    return {"z": z, "flux_a_ujy": flux, "sigma_ujy": sigma, "differential": d}


def test_variability_outcomes():
    v = assess.assess_variability
    assert v([], [], 0)["category"] == "insufficient_evidence"
    assert v([], [{"z": 40.0}], 3)["category"] == "spectral_difference_only"
    o = v([fp(8.0)], [], 1, {"error_scale": 1.0, "status": "ok"})
    assert o["category"] == "variability_candidate" and "not a confirmed" in o["statement"]
    # PAIRDIFF-1 significant but the reference-calibrated z is not: no candidate
    assert v([fp(8.0, zc=0.5)], [], 1, {"error_scale": 1.0})["category"] == "no_variability_at_sensitivity"
    # CALCHECK scale reduces the calibrated z below threshold
    assert v([fp(6.0)], [], 1, {"error_scale": 1.5})["category"] == "no_variability_at_sensitivity"
    o = v([fp(9.0, calibrated=False)], [], 1)
    assert o["category"] == "calibration_limited"
    assert v([fp(9.0)], [], 1, {"error_scale": 4.0})["category"] == "calibration_limited"
    o = v([fp(1.0)], [], 1, {"error_scale": 1.0})
    assert o["category"] == "no_variability_at_sensitivity" and "not proof" in o["statement"]
    assert abs(o["sensitivity"]["min_detectable_fractional_change_5sigma"] - 0.05) < 1e-9


def test_every_outcome_documents_itself():
    outs = [cat(None, n=1), cat(motion((3000, 0)), (3000, 0)), assess.assess_variability([fp(1.0)], [], 1),
            assess.assess_quality(10, 0, {}), assess.assess_quality(10, 8, {"photometry_flagged": 8})]
    for o in outs:
        for k in ("statement", "evidence", "criteria", "limitations", "inputs", "sensitivity", "rules", "threshold_provenance"):
            assert k in o
        assert o["category"] in assess.CATEGORIES[o["question"]]
        assert o["rules"] == "ASSESS-2"
    assert outs[3]["category"] == "all_usable" and outs[4]["category"] == "instrumental"
