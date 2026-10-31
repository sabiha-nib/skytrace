// FutureLab (FUTURE-1): hypothetical future measurements, computed with formulas that first reproduce the recorded fit.
// Every scenario states its assumptions; nothing here schedules or implies an observation.

import { state } from "./state.js";
import { pairPrecision, sigmaPm } from "./epistemiccore.js";
import * as S from "./session.js";
import { el, renderToken, toast, $, clear } from "./util.js";
import { loadEpistemic, needRun, num, syntheticNote, table } from "./epiui.js";

export async function renderFuture() {
  const live = renderToken("future");
  const body = $("#future-body");
  clear(body);
  if (!state.inv) { needRun(body, "Scenarios start from a recorded analysis's errors and baseline."); return; }
  const d = await loadEpistemic(body, "future");
  if (!d || !live()) return;
  const F = d.future;
  const v = F.validation;
  body.append(syntheticNote(d), el("div", { class: "banner hyp" }, el("strong", {}, "Hypothetical. "), F.note),
    el("div", { class: "card", id: "future-validation" }, el("h3", {}, "Formula validation"), el("p", {}, v.valid ? "The sensitivity formula reproduces the recorded fit's σ from the recorded visits:" : `Not validated: ${v.reason || "the formula does not reproduce the recorded σ"} — no scenario is computed.`),
      v.axes ? table(["Axis", "Formula σ (mas/yr)", "Recorded σ", "Agrees"], Object.entries(v.axes).map(([k, a]) => el("tr", {}, el("th", { scope: "row" }, k), el("td", {}, num(a.formula_inflated, 6)), el("td", {}, num(a.recorded, 6)), el("td", {}, a.agrees ? "yes" : "no")))) : null,
      el("p", { class: "faint small" }, v.rule || "")));
  for (const s of F.scenarios) {
    const cols = s.id === "metadata" ? ["Missing input", "Would unblock", "Kind"] : s.id === "precision" ? ["Scenario", "Required flux error (µJy)", "Recorded median (µJy)", "Met now"] : ["Scenario", "σ pm (mas/yr)", "5σ sensitivity (mas/yr)", "Baseline / visits"];
    const rows = s.rows.map((r) => el("tr", { class: r.hypothetical === false ? "sel" : "" }, ...(s.id === "metadata" ? [el("td", { class: "small" }, r.input), el("td", {}, r.unblocks), el("td", {}, r.kind)]
      : s.id === "precision" ? [el("td", {}, r.label), el("td", {}, num(r.required_flux_err_ujy, 4)), el("td", {}, num(r.recorded_median_flux_err_ujy, 4)), el("td", {}, r.met_now ? "yes" : "no")]
        : [el("td", {}, r.label, r.hypothetical ? el("span", { class: "pill sim" }, "hypothetical") : el("span", { class: "pill" }, "recorded")), el("td", {}, num(r.sigma_pm, 4)), el("td", {}, num(r.sensitivity_5sigma, 4)),
          el("td", {}, r.baseline_yr !== undefined ? `${num(r.baseline_yr, 3)} yr` : `${r.visits} visits`)])));
    body.append(el("div", { class: "card", "data-scenario": s.id }, el("h3", {}, s.title), table(cols, rows.length ? rows : [el("tr", {}, el("td", { colspan: cols.length }, "Nothing missing."))]),
      el("p", { class: "faint small" }, "Assumptions: " + s.assumptions.join("; "))));
  }
  body.append(calculator(d));
}

function calculator(d) {
  const base = d.future.scenarios.find((s) => s.id === "baseline");
  const ev = state.inv.record.events.find((e) => e.step === "astrometry")?.data;
  if (!base || !ev || !d.future.validation.valid) return el("p", { class: "faint" }, "The interactive calculator needs a validated motion fit.");
  const eps = ev.epochs.filter((_, j) => !(ev.fit?.rejected || []).includes(j));
  const times = eps.map((e) => e.t_mjd / 365.25);
  const sig = eps.map((e) => Math.max(e.sig_xi_mas, e.sig_eta_mas));
  const median = [...sig].sort((a, b) => a - b)[Math.floor(sig.length / 2)];
  const extra = el("input", { type: "number", id: "fl-years", min: "0.1", max: "10", step: "0.1", value: "1", "aria-label": "Years after the last visit" });
  const err = el("input", { type: "number", id: "fl-sigma", min: "1", max: "5000", step: "1", value: String(Math.round(median)), "aria-label": "Per-visit error (mas)" });
  const frac = el("input", { type: "number", id: "fl-frac", min: "0.005", max: "1", step: "0.005", value: "0.05", "aria-label": "Fractional change" });
  const out = el("p", { id: "fl-out", class: "wrap" });
  const flux = state.inv.record.events.find((e) => e.step === "variability")?.data?.pairs?.map((p) => p.flux_a_ujy).filter((x) => typeof x === "number").sort((a, b) => a - b);
  const scale = state.inv.record.events.find((e) => e.step === "variability")?.data?.calibration_check?.error_scale || 1;
  const calc = () => {
    const y = Number(extra.value), s = Number(err.value), f = Number(frac.value);
    if (!(y > 0 && s > 0 && f > 0)) { out.textContent = "Enter positive numbers."; return null; }
    const now = sigmaPm(times, sig);
    const fut = sigmaPm([...times, Math.max(...times) + y], [...sig, s]);
    const medFlux = flux?.length ? flux[Math.floor(flux.length / 2)] : null;
    const req = medFlux ? pairPrecision(f, medFlux, scale) : null;
    out.textContent = `Hypothetical: one visit ${y} yr after the last with σ = ${s} mas → 5σ motion sensitivity ${num(5 * fut, 4)} mas/yr (now ${num(5 * now, 4)}). ` +
      (req ? `Detecting a ${(f * 100).toFixed(1)}% change in one matched pair needs flux errors ≤ ${num(req, 4)} µJy (median flux ${num(medFlux, 5)} µJy, error scale ${num(scale, 4)}).` : "");
    return { y, s, f, motion_sensitivity: 5 * fut, required_flux_err: req };
  };
  const go = el("button", { class: "btn primary", type: "button", id: "fl-calc" }, "Calculate");
  go.addEventListener("click", calc);
  const keep = el("button", { class: "btn small", type: "button", id: "fl-keep" }, "Keep in the session");
  keep.addEventListener("click", async () => {
    const r = calc();
    if (!r) return;
    await S.log("future.scenario", `FutureLab (hypothetical): +${r.y} yr at ${r.s} mas → ${num(r.motion_sensitivity, 4)} mas/yr 5σ`, null, { create: true });
    toast("Scenario kept in the session history (labelled hypothetical)");
  });
  return el("div", { class: "card" }, el("h3", {}, "Your own scenario"), el("div", { class: "controls" }, el("label", { for: "fl-years" }, "Years after last visit"), extra,
    el("label", { for: "fl-sigma" }, "Per-visit error (mas)"), err, el("label", { for: "fl-frac" }, "Brightness change (fraction)"), frac, go, keep), out,
    el("p", { class: "faint small" }, "Computed in your browser with the same formula as the server (parity-tested). Hypothetical: no observation is scheduled."));
}
