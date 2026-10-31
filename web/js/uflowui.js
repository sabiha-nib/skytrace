// Uncertainty Flow (UFLOW-1): how uncertainty travels from per-pixel variance to the stated sensitivities, transformation by
// transformation, with the steps that propagate no uncertainty listed as such. Values are recorded medians, never re-estimates.

import { state } from "./state.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { loadEpistemic, needRun, syntheticNote, table, num } from "./epiui.js";

let selected = null;

export async function renderUflow() {
  const live = renderToken("uflow");
  const body = $("#uflow-body");
  clear(body);
  if (!state.inv) { needRun(body, "The uncertainty flow is read from a recorded analysis."); return; }
  const d = await loadEpistemic(body, "uflow");
  if (!d || !live()) return;
  const U = d.uflow;
  if (!selected || !U.nodes.find((n) => n.id === selected)) selected = U.nodes.find((n) => n.id === "u:zcal")?.id || U.nodes[0].id;
  const cols = U.categories.map((c) => U.nodes.filter((n) => n.category === c));
  const W = 900, colW = W / cols.length, rowH = 56;
  const H = Math.max(...cols.map((c) => c.length)) * rowH + 40;
  const pos = new Map();
  cols.forEach((c, i) => c.forEach((n, j) => pos.set(n.id, [i * colW + 12, 30 + j * rowH])));
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "uflow-svg", role: "img", "aria-label": "Uncertainty flow from input variance to output sensitivities" },
    ...U.categories.map((c, i) => el("text", { x: i * colW + 12, y: 16, class: "col-h" }, c)),
    ...U.edges.map((e) => { const [x1, y1] = pos.get(e.source), [x2, y2] = pos.get(e.target); return el("line", { x1: x1 + colW - 30, y1: y1 + 18, x2, y2: y2 + 18, class: "flow" }); }));
  for (const n of U.nodes) {
    const [x, y] = pos.get(n.id);
    const g = el("g", { class: `uf-node${n.id === selected ? " current" : ""}`, tabindex: "0", role: "button", "data-unode": n.id, "aria-label": `${n.quantity} (${n.unit})` },
      el("rect", { x, y, width: colW - 30, height: 36, rx: 6 }), el("text", { x: x + 8, y: y + 15, class: "uf-q" }, n.quantity.slice(0, 26)), el("text", { x: x + 8, y: y + 29, class: "uf-u" }, `${n.method} · ${n.unit}`));
    const pick = () => { selected = n.id; renderUflow(); };
    g.addEventListener("click", pick);
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); } });
    svg.append(g);
  }
  const n = U.nodes.find((x) => x.id === selected);
  const exp = el("button", { class: "btn small", type: "button", id: "uflow-export" }, "Export uncertainty lineage (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-uncertainty-lineage.json", JSON.stringify(U, null, 1), "application/json")) toast("Uncertainty lineage exported"); });
  body.append(syntheticNote(d), el("div", { class: "card" }, el("p", { class: "muted" }, U.note), el("div", { class: "table-wrap uflow-wrap" }, svg)),
    el("div", { class: "card", id: "uflow-detail" }, el("h3", {}, `${n.quantity} (${n.unit})`), table(["Field", "Value"], [
      ["Category", n.category], ["Method", n.method], ["Inputs", n.inputs.map((i) => U.nodes.find((x) => x.id === i)?.quantity || i).join(", ") || "— (recorded in the file)"],
      ["Propagation", n.propagation], ["Assumptions", n.assumptions.join("; ")],
      ["Result (recorded)", n.result ? Object.entries(n.result).map(([k, v]) => `${k} = ${typeof v === "number" ? num(v, 4) : v}`).join(", ") : "—"],
      ["Validation", n.validation.length ? n.validation.map((t) => `${t.defined ? "✓" : "✗"} ${t.test.split("::")[1]}`).join("; ") : "—"]].map(([k, v]) => el("tr", {}, el("th", { scope: "row" }, k), el("td", { class: "wrap small" }, v))))),
    el("div", { class: "card" }, el("h3", {}, "Not propagated"), el("p", { class: "muted" }, "These effects reach the results, but no σ here includes them; what is recorded instead is stated."),
      table(["Step", "Effect", "Recorded as"], U.not_propagated.map((g) => el("tr", {}, el("td", {}, g.step), el("td", {}, g.what), el("td", { class: "small" }, g.recorded_as))), { id: "uflow-gaps" }),
      el("p", { class: "faint small" }, `Parameter uncertainty: ${U.parameter_uncertainty}.`), el("div", { class: "controls" }, exp)));
}
