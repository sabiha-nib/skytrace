// Evidence graph: nodes and edges come from the server, which derives them only from recorded events,
// the bundle manifest and discovery records. Selecting a node traces its chain without passing through
// shared hubs (methods, references, limitations), so a trace shows only what supports that node.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { $, DET_COLORS, categoryLabel, clear, el, fmt, questionLabel, shortKey } from "./util.js";

const COLS = [["source", "reference"], ["target"], ["observation"], ["measurement"], ["comparison"], ["claim"], ["method", "limitation"]];
const COL_LABEL = ["Data sources", "Target", "Observations", "Measurements", "Comparisons", "Claims", "Methods & limitations"];
const KIND_COLOR = { source: "#6cc6a4", reference: "#6cc6a4", target: "#5fd0e4", comparison: "#a48cf2", claim: "#dde5f3", method: "#8fb3ff", limitation: "#e48b5c" };
let data = null, selected = null, pendingFocus = null;

export function focusGraph(id) { pendingFocus = id; }

export async function renderGraph() {
  const body = $("#graph-body");
  clear(body);
  if (!state.inv) { body.append(el("p", { class: "empty" }, state.target ? "Run the analysis to build the evidence graph." : "This target has no stored observations yet.")); return; }
  body.append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Building the graph…"));
  try { data = await api.graph(state.inv.investigation_id); } catch (e) { clear(body).append(el("p", { class: "empty" }, e.message)); return; }
  clear(body);
  const counts = data.counts;
  const svgHost = el("div");
  const side = el("div", { class: "card", id: "graph-detail", "aria-live": "polite" }, el("h3", {}, "Select a node"),
    el("p", { class: "muted" }, "Claims are on the right of the target's data. Select one to see which observations and comparisons support it."));
  body.append(el("p", { class: "muted" }, Object.entries(counts).filter(([, v]) => v).map(([k, v]) => `${v} ${k}${v === 1 ? "" : "s"}`).join(" · ") + ` · ${data.edges.length} relationships`),
    el("div", { class: "graph-layout" }, svgHost, side));
  draw(svgHost);
  if (pendingFocus) { select(pendingFocus); pendingFocus = null; }
}

function draw(host) {
  const byCol = COLS.map((kinds) => data.nodes.filter((n) => kinds.includes(n.kind)));
  const W = 1000, rowH = 12, top = 36;
  const gap = (nodes) => (nodes.length <= 8 ? 40 : rowH);          // few nodes (claims, sources): room for labels
  const H = Math.max(260, Math.max(...byCol.map((c) => c.length * gap(c))) + top + 20);
  const svg = el("svg", { class: "graph-svg", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Evidence graph" });
  const colX = (i) => 150 + i * ((W - 150 - 200) / (COLS.length - 1));
  const pos = {};
  byCol.forEach((nodes, i) => {
    const g = gap(nodes), h = nodes.length * g;
    const y0 = top + Math.max(0, (H - top - 20 - h) / 2);
    nodes.forEach((n, j) => { pos[n.id] = [colX(i), y0 + j * g + g / 2]; });
    svg.append(el("text", { class: "col-label", x: colX(i), y: 16, "text-anchor": "middle" }, COL_LABEL[i]));
  });
  const edgeG = el("g");
  for (const e of data.edges) {
    const [x1, y1] = pos[e.source], [x2, y2] = pos[e.target];
    const mx = (x1 + x2) / 2;
    edgeG.append(el("path", { class: "edge", d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, dataset: { s: e.source, t: e.target } }));
  }
  svg.append(edgeG);
  const nodeG = el("g");
  for (const n of data.nodes) {
    const [x, y] = pos[n.id];
    const g = el("g", { class: "node", tabindex: "0", dataset: { id: n.id }, role: "button", "aria-label": `${n.kind}: ${n.label}` });
    const c = el("circle", { cx: x, cy: y, r: ["claim", "target"].includes(n.kind) ? 6 : 4 });
    c.style.fill = n.kind === "observation" || n.kind === "measurement" ? (DET_COLORS[n.detector || (n.label.match(/:D(\d)$/) || [])[1]] || "#aaa") : KIND_COLOR[n.kind] || "#aaa";
    if (n.kind === "measurement" && n.status !== "ok") c.style.fillOpacity = ".3";
    g.append(c, el("title", {}, `${n.kind}: ${n.label}`));
    if (["claim", "method", "limitation", "target", "source", "reference"].includes(n.kind)) {
      const right = n.kind === "method" || n.kind === "limitation";
      const short = (s, max) => (s.length > max ? s.slice(0, max - 1) + "…" : s);
      if (n.kind === "claim") {   // label above the node, clear of the comparison column, in plain words
        const [q, cat] = n.label.split(": ");
        g.append(el("text", { x, y: y - 16, "text-anchor": "middle", class: "claim-q" }, short(questionLabel(q), 22)),
                 el("text", { x, y: y - 6, "text-anchor": "middle", class: "claim-c" }, short(categoryLabel(cat), 26)));
      } else {
        const max = right ? 30 : 20;
        g.append(el("text", { x: right ? x + 9 : x - 9, y: y + 3.5, "text-anchor": right ? "start" : "end" }, short(n.label, max)));
      }
    }
    g.addEventListener("click", () => select(n.id));
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") select(n.id); });
    nodeG.append(g);
  }
  svg.append(nodeG);
  host.append(svg);
}

// Support paths run claim -> comparisons -> measurements -> observations -> data sources.
// Expansion follows only these kind-to-kind steps, so shared nodes (methods, other claims) never pull in
// unrelated evidence. The selected node's direct neighbours are always shown.
const STEPS = {
  claim: ["comparison", "measurement", "method", "limitation", "reference", "target"],
  comparison: ["measurement", "method"],
  measurement: ["observation", "method", "reference"],
  observation: ["source", "target"],
};

function trace(id) {
  const adj = {};
  for (const e of data.edges) { (adj[e.source] ||= []).push(e.target); (adj[e.target] ||= []).push(e.source); }
  const kind = Object.fromEntries(data.nodes.map((n) => [n.id, n.kind]));
  const seen = new Set([id, ...(adj[id] || [])]);
  const q = [id];
  while (q.length) {
    const n = q.shift();
    for (const m of adj[n] || []) {
      if ((STEPS[kind[n]] || []).includes(kind[m]) && !q.includes(m)) {
        if (!seen.has(m) || n === id) { seen.add(m); if (STEPS[kind[m]]) q.push(m); }
      }
    }
  }
  return seen;
}

function select(id) {
  const n = data?.nodes.find((x) => x.id === id);
  if (!n) return;
  selected = id;
  const keep = trace(id);
  document.querySelectorAll(".graph-svg .node").forEach((g) => { g.classList.toggle("dim", !keep.has(g.dataset.id)); g.classList.toggle("sel", g.dataset.id === id); });
  document.querySelectorAll(".graph-svg .edge").forEach((p) => p.classList.toggle("hl", keep.has(p.dataset.s) && keep.has(p.dataset.t)));
  const box = $("#graph-detail");
  const ev = n.event != null ? state.model.events[n.event] : null;
  const rel = data.edges.filter((e) => e.source === id || e.target === id);
  const key = n.id.replace(/^(obs|meas):/, "");
  const supporting = [...keep].filter((k) => k.startsWith("obs:")).length;
  box.replaceChildren(el("h3", {}, n.kind[0].toUpperCase() + n.kind.slice(1)), el("p", {}, n.statement || n.label),
    el("dl", { class: "kv" },
      n.category ? [el("dt", {}, "Outcome"), el("dd", {}, n.category)] : null,
      n.quality ? [el("dt", {}, "Quality"), el("dd", {}, n.quality)] : null,
      n.z != null ? [el("dt", {}, "z (raw, PAIRDIFF-1)"), el("dd", {}, fmt(n.z, 2))] : null,
      n.kind === "comparison" ? [el("dt", {}, "z (reference-calibrated)"), el("dd", {}, n.z_calibrated != null ? `${fmt(n.z_calibrated, 2)} (${n.n_refs} reference stars)` : `not calibrated (${n.n_refs ?? 0} matched reference stars; 3 needed)`)] : null,
      n.obs_id ? [el("dt", {}, "Archive observation"), el("dd", { class: "mono" }, n.obs_id)] : null,
      n.release ? [el("dt", {}, "Release"), el("dd", {}, n.release)] : null,
      n.file ? [el("dt", {}, "Stored file"), el("dd", { class: "mono wrap" }, n.file)] : null,
      n.sha256 ? [el("dt", {}, "SHA-256 (manifest)"), el("dd", { class: "mono wrap" }, n.sha256)] : null,
      n.source_url ? [el("dt", {}, "Source URL"), el("dd", { class: "mono wrap" }, n.source_url)] : null,
      n.dataset_id ? [el("dt", {}, "Dataset"), el("dd", {}, n.dataset_id)] : null,
      n.role ? [el("dt", {}, "Role"), el("dd", {}, n.role.replaceAll("_", " "))] : null,
      n.t_mid_iso ? [el("dt", {}, "Observed"), el("dd", {}, n.t_mid_iso)] : null,
      n.origin ? [el("dt", {}, "Origin"), el("dd", {}, n.origin)] : null,
      el("dt", {}, "Relationships"), el("dd", {}, String(rel.length)),
      n.kind === "claim" ? [el("dt", {}, "Traced observations"), el("dd", {}, String(supporting))] : null,
      ev ? [el("dt", {}, "Recorded as"), el("dd", {}, `step ${ev.step} (${ev.status}): ${ev.detail}`)] : null),
    el("details", {}, el("summary", {}, `Relationships (${rel.length})`),
      el("ul", { class: "limits" }, ...rel.slice(0, 60).map((e) => el("li", {}, `${e.source === id ? "→ " + e.rel + " " + label(e.target) : label(e.source) + " " + e.rel + " →"}`)))),
    (n.kind === "observation" || n.kind === "measurement") ? el("div", { class: "controls" },
      el("button", { class: "btn small", onclick: () => emit("goto", { ws: "explorer", key }) }, "Open in Sky Explorer")) : null,
    n.kind === "claim" ? el("div", { class: "controls" },
      el("button", { class: "btn small", onclick: () => emit("ask", `Which observations support the ${n.id.split(":")[1].replace("_", " ")} outcome, and how certain is it?`) }, "Ask the copilot")) : null);
}

function label(id) { const n = data.nodes.find((x) => x.id === id); return n ? (n.kind === "observation" || n.kind === "measurement" ? shortKey(n.label.replace("measurement ", "")) : n.label) : id; }
