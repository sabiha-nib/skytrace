import numpy as np

from skytrace.science import flags as fl
from skytrace.science.wavelength import SourceSample, compare_pair, match_pairs


def s(obs, det, mjd, wl, bw=0.03, q="ok"):
    return SourceSample(obs, det, mjd, wl, bw, q)


def test_matched_pair_accepted():
    d = compare_pair(s("a", 2, 60800, 1.300), s("b", 2, 60990, 1.310))
    assert d.accepted and abs(d.delta_lambda_um - 0.01) < 1e-12
    assert d.delta_t_days == 190


def test_wavelength_mismatch_rejected():
    d = compare_pair(s("a", 2, 60800, 1.30), s("b", 2, 60990, 1.40))
    assert not d.accepted and d.reason.startswith("wavelength mismatch")


def test_different_detector_rejected_even_if_close_in_wavelength():
    d = compare_pair(s("a", 2, 60800, 1.62), s("b", 3, 60990, 1.63))
    assert not d.accepted and "different detectors" in d.reason


def test_quality_and_bandwidth():
    assert "unusable" in compare_pair(s("a", 1, 1, 1.0), s("b", 1, 2, 1.0, q="flagged")).reason
    assert "no valid bandwidth" in compare_pair(s("a", 1, 1, 1.0, bw=float("nan")), s("b", 1, 2, 1.0)).reason


def test_order_independent_and_all_decisions_returned():
    ss = [s("a", 1, 3, 1.0), s("b", 1, 1, 1.001), s("c", 1, 2, 1.2)]
    out = match_pairs(ss)
    assert len(out) == 3 and sum(d.accepted for d in out) == 1
    acc = [d for d in out if d.accepted][0]
    assert (acc.a, acc.b) == ("b", "a")  # earlier observation first


def test_flags_documented_fallback_reports_unresolved():
    fmap = fl.resolve_bits(None)
    assert fmap.origin == "documented" and fmap.bits == {"MP_TRANSIENT": 0, "MP_SOURCE": 21}
    assert "MP_OVERFLOW" in fmap.unresolved


def test_flags_from_header_and_mask():
    fmap = fl.resolve_bits({"MP_TRANSIENT": 0, "MP_OVERFLOW": 3, "MP_SOURCE": 21, "EXTNAME": "FLAGS"})
    assert fmap.origin == "header"
    f = np.zeros((5, 5), np.int32)
    f[1, 1] = 1 << 3        # overflow -> reject
    f[2, 2] = 1 << 21       # source -> info only
    rej = fmap.mask(f, fl.REJECT)
    assert rej[1, 1] and not rej[2, 2] and rej.sum() == 1
    summ = fl.summarize(f, np.ones_like(f, bool), fmap)
    assert summ.n_reject == 1 and summ.reject_names == ("MP_OVERFLOW",)
