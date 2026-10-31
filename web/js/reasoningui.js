// Reasoning Graph (EPI-1) and Lineage-X (LINEAGE-1). Select a claim and trace it backwards to files, measurements,
// transformations, methods, assumptions and uncertainty; select a file and trace forward to everything that depends on it.
// Statuses come from the server's grounded rules; tracing runs in the browser (epistemiccore.trace, parity-tested).

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { trace } from "./epistemiccore.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, statusPill, syntheticNote, tabs, STATIC } from "./epiui.js";

let tab = "graph", selected = null, dir = "back", kindFilter = "all", linSel = "claim:variability";
export function setReasoningTab(t) { tab = t; }
export function focusNode(id) { selected = id; tab = "graph"; }

const LAYERS = [["source", "Sources"], ["observation", "Observations"], ["measurement", "Measurements"], ["derived", "Derived quantities"], ["inference", "Inferences"],
  ["claim", "Claims"], ["conclusion", "Conclusion"]];
const CONTEXT = [["transformation", "Transformations"], ["method", "Methods"], ["model", "Models"], ["assumption", "Assumptions"], ["uncertainty", "Uncertainty"],
  ["limitation", "Limitations"], ["contradiction", "Contradictions"], ["hypothesis", "Competing hypotheses"]];

export async function renderReasoning() {
  const live = renderToken("reasoning");
  const body = $("#reasoning-body");
  clear(body);
  if (!state.inv) { needRun(body, "The reasoning graph is built from a recorded analysis."); return; }
  const d = await loadEpistemic(body, "reasoning");
  if (!d || !live()) return;
  body.append(syntheticNote(d), tabs("Reasoning", [["graph", "Reasoning graph"], ["lineage", "Lineage-X"]], tab, "data-rtab-epi", (k) => { tab = k; renderReasoning(); }));
  if (tab === "graph") body.append(graphView(d.graph));
  else body.append(await lineageView(d));
}

function graphView(G) {
  const byId = new Map(G.nodes.map((n) => [n.id, n]));
  if (!selected || !byId.has(selected)) selected = G.claims.includes("claim:variability") ? "claim:variability" : G.claims[0];
  const sel = el("select", { id: "epi-node", "aria-label": "Object to trace" },
    el("optgroup", { label: "Claims" }, ...G.nodes.filter((n) => ["claim", "conclusion"].includes(n.kind)).map((n) => opt(n))),
    el("optgroup", { label: "Derived quantities" }, ...G.nodes.filter((n) => n.kind === "derived" && !n.id.startsWith("pos:")).slice(0, 80).map((n) => opt(n))),
    el("optgroup", { label: "Source files" }, ...G.nodes.filter((n) => n.kind === "source").map((n) => opt(n))));
  sel.value = selected;
  sel.addEventListener("change", () => { selected = sel.value; renderReasoning(); });
  const dirSel = el("div", { class: "tagrow", role: "group", "aria-label": "Direction" }, ...[["back", "Trace backward (what it rests on)"], ["forward", "Trace forward (what depends on it)"]].map(([k, t]) => {
    const b = el("button", { type: "button", class: "tag", "aria-pressed": String(dir === k), "data-dir": k }, t);
    b.addEventListener("click", () => { dir = k; renderReasoning(); });
    return b;
  }));
  const T = trace(G, selected, dir);
  const node = byId.get(selected);
  const inTrace = T.nodes.map((x) => ({ ...byId.get(x.id), depth: x.depth }));
  const layerCols = el("div", { class: "epi-layers", role: "list", "aria-label": "Trace by layer" }, ...LAYERS.map(([k, label]) => {
    const items = inTrace.filter((n) => n.kind === k);
    const self = node.kind === k ? [node] : [];
    return el("div", { class: "epi-col", role: "listitem" }, el("h4", {}, label, el("span", { class: "faint" }, ` ${items.length + self.length}`)),
      ...[...self, ...items].slice(0, 6).map((n) => nodeChip(n, n.id === selected)),
      items.length > 6 ? el("p", { class: "faint small" }, `+ ${items.length - 6} more`) : null);
  }));
  const ctx = el("div", { class: "epi-context" }, ...CONTEXT.map(([k, label]) => {
    const items = inTrace.filter((n) => n.kind === k);
    if (!items.length) return null;
    return el("details", { class: "epi-ctx", open: ["method", "assumption"].includes(k) && dir === "back" ? "" : null },
      el("summary", {}, `${label} (${items.length})`), el("ul", { class: "plain small" }, ...items.slice(0, 60).map((n) => el("li", {}, statusPill(n.status), " ", btnNode(n)))));
  }));
  const exp = el("button", { class: "btn small", type: "button", id: "epi-export" }, "Export trace (JSON)");
  exp.addEventListener("click", async () => {
    if (await download(`skytrace-trace-${selected.replace(/[^a-z0-9]+/gi, "_").slice(0, 40)}.json`, JSON.stringify({ start: node, direction: dir, method: "EPI-1", nodes: inTrace }, null, 1), "application/json")) toast("Trace exported");
  });
  const legend = el("details", { class: "small" }, el("summary", {}, "How statuses are assigned"), el("ul", { class: "plain" },
    ...Object.entries(G.status_rules).map(([k, v]) => el("li", {}, el("strong", {}, k), " ", v))), el("p", { class: "faint" }, G.note));
  const counts = el("p", { class: "small" }, ...Object.entries(G.status_counts).map(([s, n]) => el("span", {}, statusPill(s), ` ${n} `)));
  return el("div", {}, el("div", { class: "card" }, el("div", { class: "controls" }, el("label", { for: "epi-node" }, "Object"), sel, dirSel, exp),
    el("div", { class: "epi-selected", id: "epi-selected" }, el("h3", {}, node.label), kv([["Kind", node.kind], ["Status", statusPill(node.status)],
      ["Rule", node.status_rule ? `${node.status_rule}: ${G.status_rules[node.status_rule]}` : "procedures carry no status"], ["Identifier", el("span", { class: "mono" }, node.id)],
      node.sha256 ? ["File SHA-256", el("span", { class: "mono" }, node.sha256)] : null, node.category ? ["Category", node.category] : null])),
    el("p", { class: "muted", id: "epi-summary" }, `${T.nodes.length} objects ${dir === "back" ? "upstream" : "downstream"}: ` +
      Object.entries(T.by_kind).map(([k, n]) => `${n} ${k}`).join(", ") + ".")),
    el("div", { class: "card" }, el("h3", {}, dir === "back" ? "What it rests on" : "What depends on it"), layerCols, ctx),
    el("div", { class: "card" }, el("h3", {}, "Whole graph"), counts, legend));
}

function opt(n) { return el("option", { value: n.id }, `${n.label.slice(0, 90)}`); }
function nodeChip(n, current) {
  const b = el("button", { type: "button", class: `epi-node k-${n.kind}${current ? " current" : ""}`, "data-node": n.id, title: n.label }, statusPill(n.status), el("span", {}, n.label.slice(0, 70)));
  b.addEventListener("click", () => { selected = n.id; renderReasoning(); });
  return b;
}
function btnNode(n) {
  const b = el("button", { type: "button", class: "linkish", "data-node": n.id }, n.label.slice(0, 160));
  b.addEventListener("click", () => { selected = n.id; renderReasoning(); });
  return b;
}

async function lineageView(d) {
  const results = [...d.graph.claims, "fit:motion"].filter((r) => d.lineage[r]);
  const pairs = d.graph.nodes.filter((n) => n.id.startsWith("pair:")).map((n) => n.id);
  if (!results.includes(linSel) && !pairs.includes(linSel)) linSel = results[0];
  const sel = el("select", { id: "lin-result", "aria-label": "Result" }, el("optgroup", { label: "Claims and fit" }, ...results.map((r) => el("option", { value: r }, r))),
    el("optgroup", { label: STATIC ? "Comparisons (server only)" : "Comparisons" }, ...pairs.slice(0, 60).map((r) => el("option", { value: r }, r.slice(5, 90)))));
  sel.value = linSel;
  sel.addEventListener("change", () => { linSel = sel.value; renderReasoning(); });
  const out = el("div", { id: "lin-out" });
  let L = d.lineage[linSel];
  if (!L) {
    try { L = await api.lineage(state.inv.investigation_id, linSel); } catch (e) { out.append(el("p", { class: "withheld" }, e.message)); }
  }
  if (L) out.append(lineageBody(L));
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Exactly how did the original files become this result?"),
    el("p", { class: "muted" }, "Each stage refers to a recorded event or manifest entry. A stage the record does not contain is shown as missing, never filled in."),
    el("div", { class: "controls" }, el("label", { for: "lin-result" }, "Result"), sel)), out);
}

function lineageBody(L) {
  const exp = el("button", { class: "btn small", type: "button", id: "lin-export" }, "Export lineage report (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-lineage-${L.result.replace(/[^a-z0-9]+/gi, "_").slice(0, 40)}.json`, JSON.stringify(L, null, 1), "application/json")) toast("Lineage exported"); });
  return el("div", {}, el("ol", { class: "lineage", "aria-label": "Lineage stages" }, ...L.stages.map((s) => el("li", { class: `lin-stage ${s.present ? "present" : "missing"}`, "data-stage": s.stage },
    el("div", { class: "next-head" }, el("strong", {}, s.stage), el("span", { class: `pill ${s.present ? "out-ok" : "out-bad"}` }, s.present ? "recorded" : "missing"),
      el("span", { class: "faint" }, s.transformation)),
    s.units ? el("p", { class: "small" }, Object.entries(s.units).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") || "—" : v}`).join(" · ")) : null,
    s.note ? el("p", { class: "faint small" }, s.note) : null,
    s.fingerprints?.length ? el("details", {}, el("summary", {}, `${s.fingerprints.length} fingerprint(s)`),
      el("pre", { class: "wrap small" }, s.fingerprints.map((f) => Object.entries(f).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")).join("\n"))) : null))),
    el("div", { class: "card" }, kv([["Missing stages", L.missing.length ? L.missing.join(", ") : "none"], ["Analysis version", L.versions.analysis_version],
      ["Software recorded", Object.entries(L.versions.software || {}).map(([k, v]) => `${k} ${v}`).join(", ")],
      ["Changed since", L.dependency_changes.length ? L.dependency_changes.map((c) => `${c.package} ${c.recorded} → ${c.now}`).join(", ") : "no recorded dependency differs from this installation"]]),
      el("p", { class: "faint small" }, L.note), el("div", { class: "controls" }, exp)));
}

export { emit };
