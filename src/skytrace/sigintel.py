"""SIGNAL-1: time-series methods on the series a recorded investigation actually contains, with method selection justified.

Series (built from the record, never interpolated or filled):
  * photometry groups: the target's aperture fluxes (APPHOT-1) on one detector whose wavelengths at the target agree with the
    group's first member within the WLMATCH-2 tolerance (half a channel minus a 2 nm margin), so brightness is compared at one
    wavelength. These are raw fluxes: exposure-level calibration changes are not removed (PAIRDIFF-2 works per pair only);
  * astrometry: the visit-averaged ξ and η offsets (LINFIT-EPOCH-1) with their errors.

Methods, each with its applicability rule, assumptions and limits (``METHODS``): sampling diagnostics, the spectral window,
noise model checks, the generalised Lomb–Scargle periodogram (floating mean, weighted; Zechmeister & Kürster 2009), the
Fourier transform (only for uniform sampling), a Haar wavelet decomposition (only for uniform sampling), the discrete
correlation function for uneven sampling (Edelson & Krolik 1988), robust regression (Theil–Sen slope beside weighted least
squares), single change-point detection (two-segment constant model) and model comparison by BIC only when the stated
assumptions hold.

Nothing here is a probability: no false-alarm probability is computed, because its value depends on a noise model the data do
not establish. A periodogram peak is reported with its power and the window power at the same frequency, and is called a
candidate only by a stated rule. Deterministic; no network, no model calls.
"""

from __future__ import annotations

import math

import numpy as np

METHOD = "SIGNAL-1"
MIN_LS = 12            # points needed before a periodogram is computed
MIN_DCF = 6
MIN_CP = 6             # change point: at least 3 points per segment
MIN_TREND = 3
UNIFORM_CV = 0.1       # cadence coefficient of variation below which sampling counts as uniform
LS_CANDIDATE_POWER = 0.5
WINDOW_ALIAS = 0.5     # a peak where the spectral window exceeds this is attributed to the sampling
OVERSAMPLE = 5
MAX_FREQ = 2000

SERIES_RULES = ["photometry groups: one detector, wavelengths within the WLMATCH-2 tolerance of the group's first member; raw APPHOT-1 fluxes, not reference-calibrated",
                "astrometry: visit-averaged offsets (LINFIT-EPOCH-1) as recorded",
                "no point is interpolated, filled or resampled"]
NOT_PROBABILITIES = "power, χ², BIC and DCF values are statistics under stated assumptions; none is a probability"

METHODS = [
    {"id": "sampling", "name": "Sampling diagnostics", "applies": "always (N ≥ 2)",
     "assumptions": "times are the recorded mid-exposure or visit-mean times",
     "limits": "describes when the series was observed, not what happened between observations"},
    {"id": "window", "name": "Spectral window", "applies": "N ≥ 3",
     "assumptions": "the window is computed from the sampling times only",
     "limits": "a periodogram peak at a frequency where the window is high can be produced by the sampling alone"},
    {"id": "noise", "name": "Noise model check", "applies": "N ≥ 2 with stated errors",
     "assumptions": "independent Gaussian errors as stated",
     "limits": "χ² of a constant model tests the stated errors and the constant model together; it cannot tell which fails"},
    {"id": "lomb_scargle", "name": "Generalised Lomb–Scargle periodogram", "applies": f"N ≥ {MIN_LS}",
     "assumptions": "a single sinusoid plus a constant, independent Gaussian errors",
     "limits": "no false-alarm probability is computed; periods longer than the span or shorter than the sampling allows are not tested"},
    {"id": "fourier", "name": "Discrete Fourier transform", "applies": f"N ≥ 8 and uniform sampling (cadence CV < {UNIFORM_CV})",
     "assumptions": "uniform sampling",
     "limits": "with uneven sampling the transform mixes the signal with the window; use Lomb–Scargle instead"},
    {"id": "wavelet", "name": "Haar wavelet decomposition", "applies": "N ≥ 8 and uniform sampling",
     "assumptions": "uniform sampling; power-of-two length (the series is truncated, never padded)",
     "limits": "scale-localised variance only; no significance is attached"},
    {"id": "dcf", "name": "Discrete correlation function", "applies": f"N ≥ {MIN_DCF}",
     "assumptions": "stationarity over the span; errors as stated",
     "limits": "lag bins with few pairs are noisy; the number of pairs is shown for every bin"},
    {"id": "robust_regression", "name": "Robust trend (Theil–Sen)", "applies": f"N ≥ {MIN_TREND}",
     "assumptions": "a monotonic linear trend",
     "limits": "a trend over the span does not say what happened between observations"},
    {"id": "change_point", "name": "Single change point", "applies": f"N ≥ {MIN_CP} (at least 3 points per segment)",
     "assumptions": "two constant segments; independent Gaussian errors",
     "limits": "one change point at most; the location is restricted to gaps between observations"},
    {"id": "model_comparison", "name": "Model comparison (BIC)", "applies": "assumptions checked first",
     "assumptions": "independent Gaussian errors as stated, nested models, N > k + 2; reduced χ² of the best model between 0.5 and 2",
     "limits": "BIC is reported only when the assumptions hold; it is never the only criterion"},
]


def _f(x, nd=6):
    if x is None:
        return None
    x = float(x)
    if not math.isfinite(x):
        return None
    return float(f"{x:.{nd}g}") if abs(x) >= 1e-300 else 0.0


# ------------------------------------------------------------------ methods (pure functions; known-answer tested)
def sampling(t) -> dict:
    t = np.sort(np.asarray(t, float))
    n = len(t)
    if n < 2:
        return {"n": n, "applicable": False, "reason": "fewer than 2 points"}
    dt = np.diff(t)
    pos = dt[dt > 0]
    med = float(np.median(pos)) if len(pos) else 0.0
    cv = float(np.std(pos) / np.mean(pos)) if len(pos) > 1 and np.mean(pos) > 0 else 0.0
    span = float(t[-1] - t[0])
    return {"n": n, "applicable": True, "span": _f(span), "median_spacing": _f(med), "min_spacing": _f(pos.min() if len(pos) else 0.0),
            "max_gap": _f(dt.max()), "cadence_cv": _f(cv), "uniform": bool(cv < UNIFORM_CV and len(pos) == n - 1),
            "f_min": _f(1.0 / span) if span > 0 else None,
            "f_max_heuristic": _f(0.5 / med) if med > 0 else None,
            "note": "for uneven sampling 0.5/median spacing is a heuristic upper frequency, not a Nyquist limit"}


def freq_grid(t, f_min=None, f_max=None) -> np.ndarray:
    s = sampling(t)
    if not s["applicable"] or not s["span"]:
        return np.array([])
    f_min = f_min or s["f_min"]
    f_max = f_max or s["f_max_heuristic"] or f_min
    df = 1.0 / (OVERSAMPLE * s["span"])
    n = int(min(MAX_FREQ, max(1, math.floor((f_max - f_min) / df) + 1)))
    return f_min + df * np.arange(n)


def window(t, freqs) -> np.ndarray:
    t = np.asarray(t, float)
    w = np.exp(-2j * np.pi * np.outer(freqs, t)).sum(axis=1) / len(t)
    return np.abs(w) ** 2


def lomb_scargle(t, y, dy, freqs) -> np.ndarray:
    """Generalised Lomb–Scargle (Zechmeister & Kürster 2009): weighted, floating mean. Power in [0, 1]."""
    t, y, dy = (np.asarray(a, float) for a in (t, y, dy))
    w = 1.0 / dy ** 2
    w = w / w.sum()
    ybar = (w * y).sum()
    YY = (w * (y - ybar) ** 2).sum()
    out = np.zeros(len(freqs))
    if YY <= 0:
        return out
    for i, f in enumerate(freqs):
        om = 2 * np.pi * f
        c, s = np.cos(om * t), np.sin(om * t)
        C, S = (w * c).sum(), (w * s).sum()
        YC = (w * y * c).sum() - ybar * C
        YS = (w * y * s).sum() - ybar * S
        CC = (w * c * c).sum() - C * C
        SS = (w * s * s).sum() - S * S
        CS = (w * c * s).sum() - C * S
        D = CC * SS - CS * CS
        if D <= 1e-15:
            continue
        out[i] = (SS * YC * YC + CC * YS * YS - 2 * CS * YC * YS) / (YY * D)
    return np.clip(out, 0.0, 1.0)


def noise(y, dy) -> dict:
    y, dy = np.asarray(y, float), np.asarray(dy, float)
    n = len(y)
    if n < 2 or np.any(dy <= 0):
        return {"applicable": False, "reason": "fewer than 2 points or missing errors"}
    w = 1 / dy ** 2
    mu = float((w * y).sum() / w.sum())
    chi2 = float((((y - mu) / dy) ** 2).sum())
    var = float(np.var(y, ddof=1))
    mean_err2 = float(np.mean(dy ** 2))
    return {"applicable": True, "weighted_mean": _f(mu), "chi2_constant": _f(chi2), "dof": n - 1, "reduced_chi2_constant": _f(chi2 / (n - 1)),
            "rms": _f(math.sqrt(var)), "median_error": _f(np.median(dy)),
            "excess_variance": _f((var - mean_err2) / mu ** 2) if mu != 0 else None,
            "reading": ("scatter consistent with the stated errors under a constant model" if chi2 / (n - 1) < 2
                        else "scatter exceeds the stated errors under a constant model: either the source varies or the errors are underestimated")}


def theil_sen(t, y) -> dict:
    t, y = np.asarray(t, float), np.asarray(y, float)
    n = len(t)
    sl = [(y[j] - y[i]) / (t[j] - t[i]) for i in range(n) for j in range(i + 1, n) if t[j] != t[i]]
    if len(sl) < 1:
        return {"applicable": False, "reason": "no pair of distinct times"}
    sl = np.sort(np.asarray(sl))
    m = float(np.median(sl))
    b = float(np.median(y - m * t))
    return {"applicable": True, "slope": _f(m), "intercept": _f(b), "n_pairs": len(sl),
            "slope_iqr": [_f(np.percentile(sl, 25)), _f(np.percentile(sl, 75))],
            "slopes_positive": int((sl > 0).sum()), "slopes_negative": int((sl < 0).sum())}


def wls_line(t, y, dy) -> dict:
    t, y, dy = (np.asarray(a, float) for a in (t, y, dy))
    w = 1 / dy ** 2
    A = np.vstack([np.ones_like(t), t]).T
    cov = np.linalg.inv(A.T @ (A * w[:, None]))
    p = cov @ (A.T @ (w * y))
    chi2 = float((((y - A @ p) / dy) ** 2).sum())
    return {"intercept": _f(p[0]), "slope": _f(p[1]), "sig_slope": _f(math.sqrt(cov[1, 1])), "chi2": _f(chi2), "dof": len(t) - 2}


def change_point(t, y, dy) -> dict:
    t, y, dy = (np.asarray(a, float) for a in (t, y, dy))
    o = np.argsort(t)
    t, y, dy = t[o], y[o], dy[o]
    n = len(t)
    if n < MIN_CP:
        return {"applicable": False, "reason": f"N = {n} < {MIN_CP}"}
    w = 1 / dy ** 2

    def seg(a, b):
        ww = w[a:b]
        mu = (ww * y[a:b]).sum() / ww.sum()
        return float((ww * (y[a:b] - mu) ** 2).sum()), float(mu)

    c0, mu0 = seg(0, n)
    best = None
    for k in range(3, n - 2):
        if t[k] == t[k - 1]:
            continue
        c1, m1 = seg(0, k)
        c2, m2 = seg(k, n)
        if best is None or c1 + c2 < best[0]:
            best = (c1 + c2, k, m1, m2)
    if best is None:
        return {"applicable": False, "reason": "no admissible split between distinct times"}
    chi2_1, k, m1, m2 = best
    return {"applicable": True, "index": k, "between": [_f(t[k - 1]), _f(t[k])], "mean_before": _f(m1), "mean_after": _f(m2),
            "chi2_constant": _f(c0), "chi2_two_segment": _f(chi2_1), "delta_chi2": _f(c0 - chi2_1), "n": n}


def dcf(t, y, dy, n_bins: int = 6) -> dict:
    """Discrete correlation function (Edelson & Krolik 1988) of a series with itself, lag bins of equal width."""
    t, y, dy = (np.asarray(a, float) for a in (t, y, dy))
    n = len(t)
    if n < MIN_DCF:
        return {"applicable": False, "reason": f"N = {n} < {MIN_DCF}"}
    mu, sd = y.mean(), y.std(ddof=1)
    e2 = float(np.mean(dy ** 2))
    denom = sd ** 2 - e2
    if denom <= 0:
        return {"applicable": False, "reason": "the scatter does not exceed the measurement errors: the normalisation sd² − σ² is not positive"}
    lags, udcf = [], []
    for i in range(n):
        for j in range(i + 1, n):
            lags.append(abs(t[j] - t[i]))
            udcf.append((y[i] - mu) * (y[j] - mu) / denom)
    lags, udcf = np.asarray(lags), np.asarray(udcf)
    edges = np.linspace(0, lags.max(), n_bins + 1)
    bins = []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (lags >= a) & (lags < b if b < edges[-1] else lags <= b)
        if sel.sum() == 0:
            bins.append({"lag_lo": _f(a), "lag_hi": _f(b), "n_pairs": 0, "dcf": None})
            continue
        bins.append({"lag_lo": _f(a), "lag_hi": _f(b), "n_pairs": int(sel.sum()), "dcf": _f(udcf[sel].mean()),
                     "err": _f(udcf[sel].std(ddof=1) / math.sqrt(sel.sum())) if sel.sum() > 1 else None})
    return {"applicable": True, "bins": bins}


def haar(y) -> dict:
    y = np.asarray(y, float)
    n = 1 << int(math.floor(math.log2(len(y)))) if len(y) else 0
    if n < 8:
        return {"applicable": False, "reason": "fewer than 8 points"}
    a = y[:n].copy()
    levels = []
    while len(a) > 1:
        d = (a[0::2] - a[1::2]) / math.sqrt(2)
        a = (a[0::2] + a[1::2]) / math.sqrt(2)
        levels.append({"scale_samples": int(n // len(d)), "energy": _f((d ** 2).sum()), "n": len(d)})
    return {"applicable": True, "used": n, "truncated": len(y) - n, "levels": levels}


def dft(t, y) -> dict:
    y = np.asarray(y, float) - float(np.mean(y))
    n = len(y)
    if n < 8:
        return {"applicable": False, "reason": "fewer than 8 points"}
    dt = float(np.median(np.diff(np.sort(np.asarray(t, float)))))
    p = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(n, dt)
    k = int(np.argmax(p[1:]) + 1) if len(p) > 1 else 0
    return {"applicable": True, "peak_frequency": _f(f[k]), "peak_power": _f(p[k]), "n_freq": len(f)}


def model_comparison(t, y, dy) -> dict:
    """Constant, linear and two-segment models: χ², and BIC only when the stated assumptions hold (no single score)."""
    t, y, dy = (np.asarray(a, float) for a in (t, y, dy))
    n = len(t)
    models = []
    nz = noise(y, dy)
    if nz.get("applicable"):
        models.append({"model": "constant", "k": 1, "chi2": nz["chi2_constant"]})
    if n >= 3:
        lin = wls_line(t, y, dy)
        models.append({"model": "linear trend", "k": 2, "chi2": lin["chi2"]})
    cp = change_point(t, y, dy)
    if cp.get("applicable"):
        models.append({"model": "two constant segments", "k": 3, "chi2": cp["chi2_two_segment"],
                       "note": "the split location was chosen to minimise χ², so k counts it as a parameter"})
    checks = []
    for m in models:
        m["dof"] = n - m["k"]
        m["reduced_chi2"] = _f(m["chi2"] / m["dof"]) if m["dof"] > 0 else None
    best = min((m for m in models if m["dof"] > 0), key=lambda m: m["chi2"] / m["dof"], default=None)
    ok_n = n > 3 + 2
    checks.append({"check": "N > k + 2 for every model", "passed": ok_n, "value": n})
    rc = best["reduced_chi2"] if best else None
    ok_rc = rc is not None and 0.5 <= rc <= 2
    checks.append({"check": "reduced χ² of the best-fitting model in [0.5, 2] (errors as stated)", "passed": ok_rc, "value": rc})
    holds = ok_n and ok_rc and bool(models)
    for m in models:
        m["bic"] = _f(m["chi2"] + m["k"] * math.log(n)) if holds else None
    return {"models": models, "assumption_checks": checks, "bic_reported": holds,
            "reading": ("BIC values are shown because the stated assumptions hold; differences below 2 are not distinguished" if holds else
                        "BIC is not reported: " + "; ".join(c["check"] for c in checks if not c["passed"]) + " failed")}


# ------------------------------------------------------------------ series from a record
def _wl_tol(bw: float, margin: float = 0.002) -> float:
    return max(0.0, 0.5 * bw - margin)


def photometry_groups(rec: dict) -> list[dict]:
    meas = [ev["data"] for ev in rec["events"] if ev["step"] == "measure" and ev["status"] == "ok"
            and ((ev.get("data") or {}).get("photometry") or {}).get("status") == "ok" and (ev["data"].get("wavelength_um") is not None)]
    groups = []
    for det in sorted({m["detector"] for m in meas}):
        ms = sorted((m for m in meas if m["detector"] == det), key=lambda m: m["wavelength_um"])
        used = set()
        for i, seed in enumerate(ms):
            if i in used:
                continue
            tol = _wl_tol(seed.get("bandwidth_um") or 0.0)
            mem = [j for j in range(i, len(ms)) if j not in used and abs(ms[j]["wavelength_um"] - seed["wavelength_um"]) <= tol]
            used.update(mem)
            pts = sorted((ms[j] for j in mem), key=lambda m: m["mjd"])
            if len(pts) < 2:
                continue
            groups.append({"id": f"D{det}@{seed['wavelength_um']:.4f}µm", "detector": det, "wavelength_um": _f(seed["wavelength_um"]),
                           "tolerance_um": _f(tol), "lambda_spread_um": _f(max(p["wavelength_um"] for p in pts) - min(p["wavelength_um"] for p in pts)),
                           "t": [p["mjd"] for p in pts], "y": [p["photometry"]["flux_ujy"] for p in pts],
                           "dy": [p["photometry"]["flux_err_ujy"] for p in pts], "obs": [p["obs_id"] for p in pts],
                           "unit": "µJy", "time_unit": "MJD (d)"})
    groups.sort(key=lambda g: (-len(g["t"]), g["id"]))
    return groups


def astrometry_series(rec: dict) -> list[dict]:
    a = next((ev["data"] for ev in rec["events"] if ev["step"] == "astrometry" and ev["status"] == "ok"), None)
    if not a or not a.get("epochs"):
        return []
    ep = a["epochs"]
    out = []
    for ax in ("xi", "eta"):
        out.append({"id": f"astrometry {('ξ' if ax == 'xi' else 'η')} (visit means)", "axis": ax, "t": [e["t_mjd"] for e in ep],
                    "y": [e[f"{ax}_mas"] for e in ep], "dy": [e[f"sig_{ax}_mas"] for e in ep], "unit": "mas", "time_unit": "MJD (d)"})
    return out


def analyse(series: dict) -> dict:
    """Every method on one series, each marked applicable or not with the reason (method selection is part of the result)."""
    t, y, dy = series["t"], series["y"], series["dy"]
    n = len(t)
    s = sampling(t)
    res = {"sampling": s, "noise": noise(y, dy)}
    sel = []

    def choose(mid, ok, why):
        sel.append({"method": mid, "applicable": bool(ok), "reason": why})
        return ok

    if choose("window", n >= 3, f"N = {n}" + (" ≥ 3" if n >= 3 else " < 3")):
        fr = freq_grid(t)
        w = window(t, fr)
        res["window"] = {"freq": [_f(x) for x in fr[:: max(1, len(fr) // 200)]], "power": [_f(x) for x in w[:: max(1, len(fr) // 200)]],
                         "unit": "1/d", "n_freq": len(fr)}
    if choose("lomb_scargle", n >= MIN_LS, f"N = {n}" + (f" ≥ {MIN_LS}" if n >= MIN_LS else f" < {MIN_LS}: too few points for a periodogram")):
        fr = freq_grid(t)
        p = lomb_scargle(t, y, dy, fr)
        w = window(t, fr)
        k = int(np.argmax(p))
        alias = bool(w[k] > WINDOW_ALIAS)
        cand = bool(p[k] >= LS_CANDIDATE_POWER and not alias)
        step = max(1, len(fr) // 400)
        res["lomb_scargle"] = {"freq": [_f(x) for x in fr[::step]], "power": [_f(x) for x in p[::step]], "unit": "1/d",
                               "peak": {"frequency": _f(fr[k]), "period": _f(1 / fr[k]) if fr[k] else None, "power": _f(p[k]),
                                        "window_power": _f(w[k])},
                               "periodicity_candidate": cand,
                               "rule": f"candidate only if the peak power ≥ {LS_CANDIDATE_POWER} and the window power there ≤ {WINDOW_ALIAS}; no false-alarm probability is computed",
                               "reading": ("a periodicity candidate under the stated rule — not a detected period" if cand else
                                           "the peak coincides with a strong window feature: attributable to the sampling" if alias else
                                           "no peak meets the stated rule")}
    uni = s.get("uniform", False)
    if choose("fourier", n >= 8 and uni, "uniform sampling" if uni and n >= 8 else ("uneven sampling: Lomb–Scargle is the method for uneven times" if not uni else f"N = {n} < 8")):
        res["fourier"] = dft(t, y)
    if choose("wavelet", n >= 8 and uni, "uniform sampling" if uni and n >= 8 else ("uneven sampling" if not uni else f"N = {n} < 8")):
        res["wavelet"] = haar(y)
    if choose("dcf", n >= MIN_DCF, f"N = {n}" + (f" ≥ {MIN_DCF}" if n >= MIN_DCF else f" < {MIN_DCF}")):
        res["dcf"] = dcf(t, y, dy)
    if choose("robust_regression", n >= MIN_TREND, f"N = {n}" + (f" ≥ {MIN_TREND}" if n >= MIN_TREND else f" < {MIN_TREND}")):
        res["robust_regression"] = {"theil_sen": theil_sen(t, y), "weighted_least_squares": wls_line(t, y, dy), "slope_unit": f"{series['unit']} per day"}
    if choose("change_point", n >= MIN_CP, f"N = {n}" + (f" ≥ {MIN_CP}" if n >= MIN_CP else f" < {MIN_CP}")):
        res["change_point"] = change_point(t, y, dy)
    choose("model_comparison", n >= 3, "assumption checks decide whether BIC is shown")
    if n >= 3:
        res["model_comparison"] = model_comparison(t, y, dy)
    res["selection"] = sel
    return res


def workbench(rec: dict, max_groups: int = 4) -> dict:
    groups = photometry_groups(rec)
    astro = astrometry_series(rec)
    series = []
    for g in groups[:max_groups] + astro:
        series.append({**{k: g[k] for k in g if k not in ("t", "y", "dy")}, "n": len(g["t"]),
                       "data": {"t": [_f(x, 10) for x in g["t"]], "y": [_f(x) for x in g["y"]], "dy": [_f(x) for x in g["dy"]]},
                       "analysis": analyse(g)})
    return {"method": METHOD, "methods": METHODS, "n_photometry_groups": len(groups), "series": series,
            "series_rules": SERIES_RULES, "not_probabilities": NOT_PROBABILITIES}
