// Browser port of view.InvestigationView.pair_comparison (Python), used only by the static preview, where no
// server is running. It applies the same already-defined rules (WLMATCH-2 compatibility, PAIRDIFF-1 flux
// difference, logged PAIRDIFF-2 calibration, position difference) to two logged measurements of a record.
// Parity with the Python implementation is tested for every pair of both fixtures (tests/unit/test_static_preview.py).
// Pure functions, no DOM: importable from Node.

export const RULE_VERSION = "WLMATCH-2";

// Python f"{x:.nf}" formatting, including nan/inf spelling.
export function pyFixed(x, n) {
  if (Number.isNaN(x)) return "nan";
  if (x === Infinity) return "inf";
  if (x === -Infinity) return "-inf";
  return x.toFixed(n);
}

const orNaN = (v) => (v ? v : NaN);           // Python `x or float("nan")` (0, None -> nan)
const pyMin = (a, b) => (b < a ? b : a);      // Python min(a, b) semantics with NaN

export function comparePair(s1, s2, tolerance = 0.5, minDtDays = 0.0, marginUm = 0.0, sameRelease = false) {
  const [first, second] = s2.mjd < s1.mjd ? [s2, s1] : [s1, s2];
  const dl = Math.abs(first.wavelength_um - second.wavelength_um);
  const dt = second.mjd - first.mjd;
  const decide = (ok, code, reason) => ({ a: first.obs_id, b: second.obs_id, accepted: ok, reason, delta_lambda_um: dl,
                                          delta_t_days: dt, rule: RULE_VERSION, code });
  if (first.obs_id === second.obs_id) return decide(false, "same_observation", "same observation");
  if (first.detector !== second.detector)
    return decide(false, "different_detectors", `different detectors (D${first.detector} vs D${second.detector})`);
  for (const s of [first, second]) {
    if (s.quality !== "ok") return decide(false, "unusable_measurement", `${s.obs_id} unusable: ${s.quality}`);
    if (!(s.bandwidth_um > 0)) return decide(false, "no_bandwidth", `${s.obs_id} has no valid bandwidth`);
  }
  if (sameRelease && first.release !== second.release)
    return decide(false, "different_releases",
      `different releases (${first.release || "?"} vs ${second.release || "?"}): calibrations may differ`);
  const limit = tolerance * pyMin(first.bandwidth_um, second.bandwidth_um);
  if (dl > limit) return decide(false, "wavelength_mismatch", `wavelength mismatch: |dλ|=${pyFixed(dl, 4)} µm > ${pyFixed(limit, 4)} µm`);
  if (dl + marginUm > limit)
    return decide(false, "wavelength_ambiguous",
      `wavelength match ambiguous: |dλ|=${pyFixed(dl, 4)} µm is within the ${pyFixed(marginUm * 1000, 1)} nm ` +
      `wavelength-accuracy margin of the ${pyFixed(limit, 4)} µm limit`);
  if (dt < minDtDays) return decide(false, "baseline_short", `time baseline ${pyFixed(dt, 2)} d < required ${pyFixed(minDtDays, 2)} d`);
  return decide(true, "accepted", `|dλ|=${pyFixed(dl, 4)} µm <= ${pyFixed(limit, 4)} µm, same detector`);
}

function sample(k, m) {
  const q = m.quality_code || (m.quality === "ok" ? "ok" : String(m.quality));
  return { obs_id: k, detector: m.detector, mjd: m.mjd, wavelength_um: orNaN(m.wavelength_um), bandwidth_um: orNaN(m.bandwidth_um),
           quality: q, release: m.release ?? "" };
}

/** measurements: {key: logged measure-event data (only entries with a centroid field count)}, params: record.parameters,
 *  fluxPairs: the variability step's logged pairs. Returns the same object as the Python method. */
export function pairComparison(measurements, params, fluxPairs, a, b) {
  const get = (k) => (measurements[k] && "centroid" in measurements[k] ? measurements[k] : null);
  const ma = get(a), mb = get(b);
  const missing = [[a, ma], [b, mb]].filter(([, m]) => !m).map(([k]) => k);
  if (missing.length) return { error: `no logged measurement for ${missing.join(", ")}` };
  const tol = params.wavelength_tolerance_channels ?? 0.5;
  const d = comparePair(sample(a, ma), sample(b, mb), tol, 0.0, params.wavelength_margin_um ?? 0.0,
                        params.photometry_same_release ?? false);
  const [first, second] = ma.mjd <= mb.mjd ? [ma, mb] : [mb, ma];
  const out = { a: d.a, b: d.b, compatible_for_photometry: d.accepted, reason: d.reason, reason_code: d.code,
                rule: "wavelength_margin_um" in params ? d.rule : "WLMATCH-1",
                delta_t_days: d.delta_t_days, delta_lambda_um: d.delta_lambda_um,
                wavelength_a_um: first.wavelength_um ?? null, wavelength_b_um: second.wavelength_um ?? null,
                tolerance_um: tol * pyMin(orNaN(first.bandwidth_um), orNaN(second.bandwidth_um)),
                t_a_iso: first.t_mid_iso ?? null, t_b_iso: second.t_mid_iso ?? null };
  const pa = first.photometry || {}, pb = second.photometry || {};
  if (d.accepted && pa.status === "ok" && pb.status === "ok") {
    const s = Math.hypot(pa.flux_err_ujy, pb.flux_err_ujy);
    out.flux = { flux_a_ujy: pa.flux_ujy, flux_b_ujy: pb.flux_ujy, delta_ujy: pb.flux_ujy - pa.flux_ujy, sigma_ujy: s,
                 z: s > 0 ? (pb.flux_ujy - pa.flux_ujy) / s : null, method: "PAIRDIFF-1",
                 note: "z is a significance under the stated errors, not a probability" };
    const logged = (fluxPairs || []).find((p) => p.a === d.a && p.b === d.b);
    if (logged && logged.differential) out.flux.reference_calibrated = logged.differential;
  } else {
    out.flux = null;
    out.flux_note = !d.accepted ? "flux comparison not valid: " + d.reason : "photometry not usable in one or both";
  }
  if (first.target_xi_eta_mas && second.target_xi_eta_mas) {
    const dx = second.target_xi_eta_mas[0] - first.target_xi_eta_mas[0];
    const dy = second.target_xi_eta_mas[1] - first.target_xi_eta_mas[1];
    const sx = Math.sqrt(first.target_cov_mas2[0] + second.target_cov_mas2[0]);
    const sy = Math.sqrt(first.target_cov_mas2[1] + second.target_cov_mas2[1]);
    out.position = { d_xi_mas: dx, d_eta_mas: dy, sigma_xi_mas: sx, sigma_eta_mas: sy, separation_mas: Math.hypot(dx, dy),
                     note: "positions from per-exposure Gaia-referenced plate solutions, before parallax removal; " +
                           "chromatic effects not modelled" + (d.accepted ? "" : "; the two exposures are at different wavelengths") };
  } else out.position = null;
  return out;
}
