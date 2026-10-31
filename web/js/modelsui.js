// Model Arena (MODELS-1): static vs linear-motion models on the same recorded visit positions. Standard Gaussian criteria
// (χ², dof, χ²ν, Δχ², AIC), residuals and leave-one-visit-out refits. No probability, no invented score, and the
// better-fitting model is not thereby the physical explanation.

import { state } from "./state.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { loadEpistemic, needRun, num, syntheticNote, table } from "./epiui.js";

export async function renderModels() {
  const live = renderToken("models");
  const body = $("#models-body");
  clear(body);
  if (!state.inv) { needRun(body, "Models are fitted to a recorded analysis's visit positions."); return; }
  const d = await loadEpistemic(body, "models");
  if (!d || !live()) return;
  const M = d.models;
  body.append(syntheticNote(d));
  if (!M.available) { body.append(el("p", { class: "empty" }, M.reason)); return; }
  const exp = el("button", { class: "btn small", type: "button", id: "models-export" }, "Export model selection record (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-model-arena.json", JSON.stringify(M, null, 1), "application/json")) toast("Model record exported"); });
  body.append(el("div", { class: "card" }, el("p", { class: "muted" }, M.note), el("p", { class: "small" }, "Criteria: " + M.criteria.join(" · ")),
    el("p", { class: "faint small" }, `${M.visits.length} visits used` + (M.rejected_visits.length ? `; visits rejected by the pipeline: ${M.rejected_visits.join(", ")}` : "") + `. Brightness: ${M.brightness_models}.`),
    el("div", { class: "controls" }, exp)));
  for (const [ax, A] of Object.entries(M.axes)) {
    const best = A.models.reduce((p, x) => (x.aic < p.aic ? x : p));
    body.append(el("div", { class: "card", "data-axis": ax }, el("h3", {}, `Axis ${A.label}`),
      table(["Model", "k", "Parameters", "χ²", "dof", "χ²ν", "AIC"], A.models.map((m) => el("tr", { class: m.model === best.model ? "sel" : "" },
        el("th", { scope: "row" }, `${m.model} · ${m.name}`), el("td", {}, String(m.k)),
        el("td", { class: "small" }, Object.entries(m.params).map(([k, v]) => `${k} = ${num(v, 4)}${k === "pm" ? " mas/yr" : " mas"}`).join(", ") + (m.sigma_pm ? ` (σ ${num(m.sigma_pm, 4)})` : "")),
        el("td", {}, num(m.chi2, 4)), el("td", {}, String(m.dof)), el("td", {}, m.reduced_chi2 === null ? "—" : num(m.reduced_chi2, 3)), el("td", {}, num(m.aic, 4)))), { class: "models-table" }),
      el("p", {}, `Δχ² (M0 − M1) = ${num(A.delta_chi2, 4)} for Δk = ${A.delta_k}; ΔAIC = ${num(A.delta_aic, 4)}. `,
        el("span", { class: "muted" }, A.delta_aic > 2 ? "Under AIC's assumptions the linear-motion model describes these points better." :
          A.delta_aic < -2 ? "Under AIC's assumptions the static model describes these points better." : "AIC does not separate the two models (|ΔAIC| ≤ 2).")),
      residuals(A, M.visits),
      el("p", { class: "small" }, `Validation: refit pm ${num(A.validation.refit_pm, 6)} vs pipeline ${num(A.validation.pipeline_pm, 6)} mas/yr — ${A.validation.agrees ? "agrees (LINFIT-EPOCH-1 reproduced)" : "DIFFERS"}.`),
      A.leave_one_out.length ? el("p", { class: "small" }, "Leave one visit out (pm, mas/yr): " + A.leave_one_out.map((x) => `without visit ${x.dropped_visit + 1}: ${num(x.pm, 4)}`).join("; ")) : null));
  }
}

function residuals(A, visits) {
  const W = 420, H = 140, pad = 34;
  const all = A.models.flatMap((m) => m.residuals_mas);
  const lim = Math.max(1, ...all.map(Math.abs)) * 1.15;
  const t = visits.map((v) => v.t_yr);
  const t0 = Math.min(...t), t1 = Math.max(...t);
  const X = (x) => pad + ((x - t0) / ((t1 - t0) || 1)) * (W - 2 * pad);
  const Y = (y) => H / 2 - (y / lim) * (H / 2 - 14);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "resid-svg", role: "img", "aria-label": `Residuals of M0 and M1 against time for axis ${A.label}` },
    el("line", { x1: pad, x2: W - pad, y1: H / 2, y2: H / 2, class: "axis" }),
    el("text", { x: 4, y: 12, class: "tick" }, `+${lim.toFixed(0)} mas`), el("text", { x: 4, y: H - 4, class: "tick" }, `−${lim.toFixed(0)} mas`));
  A.models.forEach((m, k) => m.residuals_mas.forEach((r, i) => svg.append(el("circle", { cx: X(t[i]) + (k ? 4 : -4), cy: Y(r), r: 4, class: k ? "m1" : "m0" }, el("title", {}, `${m.model} visit ${i + 1}: ${r.toFixed(1)} mas`)))));
  return el("figure", { class: "resid" }, svg, el("figcaption", { class: "faint small" }, "Residuals per visit: ○ M0 static (left of each visit) · ● M1 linear (right). Units: mas."));
}
