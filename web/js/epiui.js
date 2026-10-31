// Shared pieces for the Phase 8 workspaces: loading the epistemic report, status and outcome pills, tab bars,
// small tables. Every value shown comes from the server's report (or the preview's recording of it).

import { emit, getEpistemic, getSpecs, state } from "./state.js";
import { STATIC } from "./api.js";
import { el } from "./util.js";

export { STATIC };

export function needRun(body, what) {
  body.append(el("div", { class: "empty" }, el("h3", {}, state.target ? "Run the analysis first" : "No stored observations for this target"),
    el("p", {}, what), state.target ? el("button", { class: "btn primary", type: "button", onclick: () => emit("run") }, "Run analysis") : null));
}

export async function loadEpistemic(body, ws) {
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Building the reasoning record from the recorded analysis…");
  body.append(holder);
  try {
    const d = await getEpistemic();
    holder.remove();
    return state.ws === ws ? d : null;
  } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return null; }
}

export async function epiSpecs() { return (await getSpecs()).epistemic; }

const STATUS_CLASS = { "directly recorded": "st-rec", measured: "st-meas", derived: "st-der", "model-dependent": "st-model", assumed: "st-asm",
  hypothesized: "st-hyp", simulated: "st-sim", "user-authored": "st-user", unsupported: "st-unsup", unknown: "st-unk" };
export function statusPill(s) {
  if (!s) return el("span", { class: "pill faint" }, "procedure");
  return el("span", { class: `pill epi ${STATUS_CLASS[s] || ""}`, title: `epistemic status: ${s}` }, s);
}

const OUT_CLASS = { pass: "ok", warning: "warn", fail: "bad", "not applicable": "faint", "not tested": "faint", inconclusive: "warn", blocked: "bad",
  examined: "ok", "partially examined": "warn", "not examined": "bad", unknown: "faint", ready: "ok", "ready with warnings": "warn", "needs attention": "bad" };
export function outcomePill(o) { return el("span", { class: `pill out-${OUT_CLASS[o] || "faint"}` }, o); }

export function tabs(label, items, current, attr, onPick) {
  return el("div", { class: "tabs", role: "tablist", "aria-label": label }, ...items.map(([k, t]) => {
    const b = el("button", { type: "button", role: "tab", "aria-selected": String(current === k), [attr]: k }, t);
    b.addEventListener("click", () => onPick(k));
    return b;
  }));
}

export function table(headers, rows, attrs = {}) {
  return el("div", { class: "table-wrap" }, el("table", attrs, el("thead", {}, el("tr", {}, ...headers.map((h) => el("th", { scope: "col" }, h)))),
    el("tbody", {}, ...rows)));
}

export function kv(pairs) {
  return el("dl", { class: "kv compact" }, ...pairs.filter(Boolean).flatMap(([k, v]) => [el("dt", {}, k), el("dd", { class: "wrap" }, v ?? "—")]));
}

export const num = (v, d = 3) => (typeof v === "number" ? (Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(Math.min(d, 3)) : v.toPrecision(d)) : v ?? "—");

export function syntheticNote(d) {
  return d?.synthetic ? el("p", { class: "banner syn small" }, el("strong", {}, "Synthetic test data. "), "Every object, status and check below describes generated data, not the sky.") : null;
}
