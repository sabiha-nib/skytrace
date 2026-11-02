// Scientific Intelligence workspace: one workflow over six intelligence layers, sharing one focus (the question under
// examination) and one investigation. Observation (Command Center, Discovery Genome) · Discovery (Unknown Universe,
// Multi-Discovery Network) · Reasoning (Scientific Adversary, Causality Lab) · Experimental (What-if, Observation Oracle,
// Research Cycle) · Knowledge (Research Memory, Reproduction Network) · Integrity (Discovery Integrity Gate).
// Panels link to each other and to the earlier workspaces that hold the underlying methods.

import { emit, getCorpus, getIntelligence, getSpecs, state } from "./state.js";
import { STATIC } from "./api.js";
import * as S from "./session.js";
import { digest } from "./canon.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { needRun, statusPill, table, kv } from "./epiui.js";
import { focusNode } from "./reasoningui.js";
import { failureWarnings, overlayGate, overlayLedger, recall, sessionEntities } from "./intelcore.js";
import { QLABEL, card, details, fmtNum, kindChip, legend, nowIso, pill, put, short } from "./intelbits.js";
import { adversaryPanel, causalPanel, cyclePanel, oraclePanel, reproPanel, whatifPanel } from "./intelui2.js";

export const LAYERS = [
  ["Observation", [["command", "Command Center"], ["genome", "Discovery Genome"]]],
  ["Discovery", [["unknown", "Unknown Universe"], ["network", "Multi-Discovery Network"]]],
  ["Reasoning", [["adversary", "Scientific Adversary"], ["causal", "Causality Lab"]]],
  ["Experimental", [["whatif", "What-if Lab"], ["oracle", "Observation Oracle"], ["cycle", "Research Cycle"]]],
  ["Knowledge", [["memory", "Research Memory"], ["repro", "Reproduction Network"]]],
  ["Integrity", [["gate", "Integrity Gate"]]],
];
const PANELS = { command: commandPanel, genome: genomePanel, unknown: unknownPanel, network: networkPanel, memory: memoryPanel, gate: gatePanel,
  adversary: adversaryPanel, causal: causalPanel, whatif: whatifPanel, oracle: oraclePanel, cycle: cyclePanel, repro: reproPanel };
let panel = "command", focus = "variability";
export function setIntelPanel(p) { if (PANELS[p]) panel = p; }

export async function renderIntel() {
  const live = renderToken("intel");
  const body = $("#intel-body");
  clear(body);
  if (!state.inv) { needRun(body, "The intelligence layer reads a recorded analysis and every other investigation Skytrace holds."); return; }
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the investigation, its reasoning record and the research memory…");
  body.append(holder);
  let d, corpus, spec;
  try { [d, corpus, spec] = await Promise.all([getIntelligence(), getCorpus(), getSpecs()]); } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return; }
  if (!live() || state.ws !== "intel") return;
  holder.remove();
  const ctx = { d, corpus, spec: spec.intelligence, caps: spec, focus, rerender: renderIntel, go: (p) => { panel = p; renderIntel(); } };
  const focusSel = el("select", { id: "intel-focus", "aria-label": "Question in focus" }, ...["variability", "motion", "data_quality"].map((q) =>
    el("option", { value: q, selected: q === focus || null }, QLABEL[q])));
  focusSel.addEventListener("change", () => { focus = focusSel.value; renderIntel(); });
  const strip = el("nav", { class: "intel-layers", id: "intel-layers", "aria-label": "Intelligence layers" }, ...LAYERS.map(([layer, ps], i) =>
    el("div", { class: "intel-layer" }, el("span", { class: "intel-layer-h" }, `${i + 1} ${layer}`),
      ...ps.map(([id, name]) => {
        const b = el("button", { type: "button", class: `intel-tab${id === panel ? " current" : ""}`, "data-ipanel": id, "aria-current": id === panel ? "page" : null }, name);
        b.addEventListener("click", () => { panel = id; renderIntel(); });
        return b;
      }))));
  const head = el("div", { class: "card intel-head" },
    el("div", { class: "controls" }, el("label", { for: "intel-focus" }, "Question in focus"), focusSel,
      d.synthetic ? kindChip("synthetic") : kindChip("real"), el("span", { class: "faint small mono" }, `run ${short(d.content_hash)}`)),
    strip, details("What the labels mean", legend()));
  const out = el("div", { id: "intel-panel", "data-panel": panel });
  body.append(head, out);
  try { await PANELS[panel](out, ctx); } catch (e) { put(out, el("p", { class: "withheld" }, e.message)); }
}

function goButton(label, p, id) {
  const b = el("button", { class: "btn small ghost", type: "button", ...(id ? { id } : {}) }, label);
  b.addEventListener("click", () => { panel = p; renderIntel(); });
  return b;
}

function openGraph(ref) {
  const id = String(ref || "").replace(/^graph:/, "");
  if (!id) return null;
  const b = el("button", { class: "linkish small", type: "button" }, "open in the reasoning graph");
  b.addEventListener("click", () => { focusNode(id); emit("goto", { ws: "reasoning" }); });
  return b;
}

// ------------------------------------------------------------------ Command Center
async function commandPanel(out, { d, corpus, focus: q }) {
  const s = state.session;
  const led = overlayLedger(d.adversary, s);
  const gate = overlayGate(d.gate, led, s);
  const conc = led.conclusions.find((c) => c.question === q) || led.conclusions[0];
  const open = led.conclusions.flatMap((c) => c.questions.flatMap((x) => x.items)).filter((i) => i.status === "open");
  const reg = Object.fromEntries(d.unknown.regions.map((r) => [r.id, r.n]));
  const tile = (title, value, sub, p, id) => el("div", { class: "card ic-card", "data-goto": p }, el("p", { class: "eyebrow" }, title), el("p", { class: "ic-value", id }, value),
    el("p", { class: "small faint" }, sub), goButton("Open", p));
  put(out, el("div", { class: "ic-grid", id: "ic-cards" },
    tile("Integrity gate", gate.outcome, `${gate.counts.met} of ${gate.requirements.length} requirements met`, "gate", "ic-gate"),
    tile("Open challenges", String(open.length), `${open.filter((i) => ["major", "critical"].includes(i.severity)).length} major or critical`, "adversary", "ic-chal"),
    tile("Unknowns", String(d.unknown.regions.slice(3).reduce((a, r) => a + r.n, 0)), `${reg.unresolved} unresolved questions · ${reg.missing} missing observations`, "unknown", "ic-unknown"),
    tile("Research debt", String(d.debt.items.length), Object.entries(d.debt.by_kind).map(([k, n]) => `${n} ${k}`).slice(0, 2).join(" · ") || "none", "gate", "ic-debt"),
    tile("Memory", String(corpus.n), `investigations remembered · ${corpus.memory.by_kind.failure} recorded failures`, "memory", "ic-memory"),
    tile("Relationships", String(corpus.network.edges.length), "stated relationships between investigations", "network", "ic-network")),
  card(`${QLABEL[q]}: where it stands`, conc ? kv([["Outcome", conc.category], ["Knowledge boundary", conc.region], ["Challenges", `${conc.n} raised by rules (${Object.entries(conc.by_status).map(([k, n]) => `${n} ${k}`).join(", ")})`],
    ["Sensitivity", (d.fingerprint.questions.find((x) => x.question === q)?.depends_on || []).join(", ") || "no tested choice changes it"],
    ["Instrumental explanations open", (d.instrumental.by_question[q]?.open || []).join(", ") || (q === "data_quality" ? "not applicable" : "none")]]) : el("p", { class: "empty" }, "No conclusion for this question.")),
  card("Investigations Skytrace holds", el("p", { class: "muted small" }, STATIC ? "In the static preview these are the runs recorded at build time." : "Runs in this server session and saved records whose data are available."),
    table(["Run", "Target", "Created", "Origin", "Data", "Outcomes"], corpus.memory.investigations.map((i) => el("tr", { class: i.record === d.content_hash ? "sel" : "" },
      el("td", { class: "mono small" }, short(i.record) + (i.record === d.content_hash ? " (this run)" : "")), el("td", {}, i.target), el("td", { class: "small" }, i.created_at),
      el("td", { class: "small" }, i.origin), el("td", {}, kindChip(i.synthetic ? "synthetic" : "real")),
      el("td", { class: "small wrap" }, Object.entries(corpus.network.nodes.find((n) => n.record === i.record)?.categories || {}).map(([k, v]) => `${k}: ${v}`).join("; ")))),
    { id: "ic-investigations" })));
}

// ------------------------------------------------------------------ Research Memory
let memQuery = "brightness calibration", memStatus = "all", memAction = "variability";
const ACTIONS = [{ id: "variability", label: "Compare brightness again (wavelength-matched pairs)", question: "variability", concepts: ["calibration", "wavelength"] },
  { id: "motion", label: "Fit the motion again", question: "motion", concepts: ["registration", "reference_stars"] },
  { id: "data_quality", label: "Re-measure the refused exposures", question: "data_quality", concepts: ["detector", "blending"] }];

async function memoryPanel(out, { d, corpus, rerender }) {
  const mem = corpus.memory;
  const byId = Object.fromEntries(mem.items.map((x) => [x.id, x]));
  const qIn = el("input", { type: "search", id: "mem-query", value: memQuery, "aria-label": "Recall from memory", placeholder: "e.g. why did the calibration of brightness fail?" });
  const st = el("select", { id: "mem-status", "aria-label": "Memory status" }, ...["all", ...mem.statuses].map((x) => el("option", { value: x, selected: x === memStatus || null }, x)));
  const go = el("button", { class: "btn primary", type: "button", id: "mem-search" }, "Recall");
  const R = recall(mem, memQuery, 40);
  const results = R.results.map((r) => byId[r.item]).filter((x) => memStatus === "all" || x.status === memStatus);
  go.addEventListener("click", () => { memQuery = qIn.value; memStatus = st.value; rerender(); });
  qIn.addEventListener("keydown", (e) => { if (e.key === "Enter") go.click(); });
  st.addEventListener("change", () => { memStatus = st.value; rerender(); });
  const act = el("select", { id: "mem-action", "aria-label": "Planned action" }, ...ACTIONS.map((a) => el("option", { value: a.id, selected: a.id === memAction || null }, a.label)));
  act.addEventListener("change", () => { memAction = act.value; rerender(); });
  const W = failureWarnings(mem, d.target_id, [ACTIONS.find((a) => a.id === memAction)]);
  const mine = state.session ? sessionEntities(state.session).filter((x) => ["hypothesis", "research_decision", "reproduction", "limitation", "counterfactual"].includes(x.type)) : [];
  // hypothesis evolution across the remembered runs, in creation order
  const invs = [...mem.investigations].sort((a, b) => (a.created_at < b.created_at ? -1 : 1)).filter((i) => i.target === d.target_id);
  const hyps = [...new Set(mem.items.filter((x) => x.kind === "explanation" && x.target === d.target_id).map((x) => x.hypothesis))].sort();
  put(out, card("Scientific recall",
    el("p", { class: "muted small" }, mem.note),
    el("div", { class: "controls" }, qIn, go, el("label", { for: "mem-status" }, "Status"), st),
    el("p", { class: "small", id: "mem-concepts" }, R.concepts.length ? ["Concepts recognised: ", ...R.concepts.flatMap((c) => [el("strong", {}, c.label), ` (via “${c.via}”) `])] : R.note),
    el("p", { class: "faint small" }, `${R.n} item(s) share a concept; ${R.rule}.`),
    el("ol", { class: "mem-list", id: "mem-results" }, ...results.slice(0, 25).map((x) => el("li", { "data-mem": x.id },
      el("div", { class: "next-head" }, pill(x.status), el("span", { class: "pill" }, x.kind), el("span", { class: "mono small" }, `${x.target} · ${short(x.record)}`),
        x.synthetic ? kindChip("synthetic") : null, x.kind === "explanation" || x.kind === "conclusion" && x.status !== "verified" ? kindChip("unverified") : null),
      el("p", { class: "small wrap" }, x.statement), el("p", { class: "faint small" }, `matched: ${R.results.find((r) => r.item === x.id).matched.join(", ")} · rule ${x.status_rule} · source ${x.source.ref}`)))),
    details("Concept vocabulary (fixed; not semantic search)", el("ul", { class: "plain small" }, ...Object.entries(mem.concepts).map(([k, c]) => el("li", {}, el("strong", {}, c.label), `: ${c.terms.join(", ")}`))))),
  card("Memory of failure", el("p", { class: "muted small" }, "Before you repeat an approach, earlier failures and inconclusive results for this target are quoted with their reasons (rule W1: same question; W2: a shared concept)."),
    el("div", { class: "controls" }, el("label", { for: "mem-action" }, "Planned action"), act),
    W.length ? el("ul", { class: "plain", id: "mem-warnings" }, ...W.slice(0, 12).map((w) => el("li", { class: "warn-item" }, pill(w.rule), " ", el("strong", {}, w.what_failed),
      el("div", { class: "faint small" }, `why it was attempted: ${w.why ?? "—"} · to unblock: ${w.unblock ?? "—"} · recorded in ${w.records.length} run(s)`))))
      : el("p", { class: "empty", id: "mem-warnings" }, "No earlier failure of this target matches the planned action.")),
  card("Knowledge evolution", el("p", { class: "muted small" }, "How each conclusion of this target moved across the remembered runs, and what differed between consecutive runs."),
    table(["Question", "Run", "Created", "Outcome", "Boundary", "Memory status", "Differs from previous in"], mem.evolution.filter((e) => e.target === d.target_id).flatMap((e) =>
      e.steps.map((s) => el("tr", { class: s.changed ? "flag" : "" }, el("td", {}, e.question), el("td", { class: "mono small" }, short(s.record)), el("td", { class: "small" }, s.created_at),
        el("td", {}, s.category + (s.changed ? " (changed)" : "")), el("td", { class: "small" }, s.region), el("td", {}, pill(s.status)), el("td", { class: "small" }, s.differs_in.join(", ") || "—")))),
    { id: "mem-evolution" })),
  card("Hypothesis evolution", el("p", { class: "muted small" }, "Each competing explanation's HYPO-1 status in every remembered run of this target (oldest first). A status is a rule outcome, never a probability; 'consistent' means still viable."),
    table(["Explanation", ...invs.map((i) => short(i.record))], hyps.map((h) => el("tr", {}, el("th", { scope: "row" }, h),
      ...invs.map((i) => { const x = mem.items.find((m) => m.kind === "explanation" && m.record === i.record && m.hypothesis === h); return el("td", { class: "small" }, x ? x.hypothesis_status : "—"); }))),
    { id: "mem-hyp" }),
    mine.length ? details(`Held in your session (${mine.length})`, table(["Entity", "Status", "Version", "Created", "Label"], mine.map((x) => el("tr", {}, el("td", { class: "mono small" }, x.id),
      el("td", {}, statusPill(x.status === "not a statement" ? null : x.status)), el("td", {}, String(x.version)), el("td", { class: "small" }, x.created_at ?? "—"), el("td", { class: "small wrap" }, x.label)))))
      : el("p", { class: "faint small" }, "Your own hypotheses, decisions, reproductions and negative entries appear here once your session holds them.")));
}

// ------------------------------------------------------------------ Discovery Genome (+ sensitivity fingerprint, uncertainty budget)
let cmpWith = "";
async function genomePanel(out, { d, corpus, focus: q, rerender }) {
  const qq = q === "data_quality" ? "variability" : q;
  const g = d.genomes.find((x) => x.question === qq);
  const fields = g?.available ? g.field_order.map((f) => [f.replaceAll("_", " "), fieldView(g.fields[f])]) : [];
  const others = corpus.memory.investigations.filter((i) => i.record !== d.content_hash);
  const sel = el("select", { id: "gn-compare", "aria-label": "Compare with another investigation" }, el("option", { value: "" }, "— choose a remembered run —"),
    ...others.map((i) => el("option", { value: i.record, selected: i.record === cmpWith || null }, `${i.target} · ${short(i.record)}${i.created_at ? " · " + i.created_at.slice(0, 16) : ""}`)));
  sel.addEventListener("change", () => { cmpWith = sel.value; rerender(); });
  let cmpView = null;
  if (cmpWith) {
    const a = d.content_hash.slice(0, 16), b = cmpWith.slice(0, 16);
    const C = corpus.genome_comparisons[`${a}|${b}|${qq}`] || corpus.genome_comparisons[`${b}|${a}|${qq}`];
    const swapped = !corpus.genome_comparisons[`${a}|${b}|${qq}`];
    cmpView = C ? compareView(C, swapped) : el("p", { class: "empty" }, "No comparison recorded for this pair (both genomes must exist).");
  }
  const fp = d.fingerprint.questions.find((x) => x.question === q);
  const bq = d.budget.questions[qq];
  const exp = el("button", { class: "btn small", type: "button", id: "gn-export" }, "Export genome (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-genome-${qq}.json`, JSON.stringify({ genome: g, fingerprint: fp, budget: d.budget }, null, 1), "application/json")) toast("Genome exported"); });
  put(out, card(`Discovery genome: ${QLABEL[qq]}`, el("p", { class: "muted small" }, "Thirteen fields, each read from where it is recorded and citing it. A null result has a genome too."),
    g?.available ? el("dl", { class: "kv genome", id: "gn-fields" }, ...fields.flatMap(([k, v]) => [el("dt", {}, k), el("dd", { class: "wrap" }, v)])) : el("p", { class: "empty" }, g?.why || "No genome."),
    el("div", { class: "controls" }, exp)),
  card("Compare two discoveries", el("p", { class: "muted small" }, "Shared observational characteristics, different interpretations, similar weaknesses, related evidence, uncertainty structures and reusable methods, each under a stated rule. Matching structure is not physical similarity; no score is computed."),
    el("div", { class: "controls" }, el("label", { for: "gn-compare" }, "Compare with"), sel), el("div", { id: "gn-cmp" }, cmpView)),
  fp ? card("Sensitivity fingerprint", el("p", { class: "muted small" }, d.fingerprint.note), table(["Dimension", "State", "What was recomputed"], fp.dimensions.map((x) =>
    el("tr", { "data-dim": x.id }, el("th", { scope: "row" }, `${x.id} ${x.name}`), el("td", {}, pill(x.state)), el("td", { class: "small wrap" }, x.detail,
      x.state === "stable" || x.state === "changes" ? el("span", {}, " ", kindChip(x.id === "F3" ? "simulated" : "verified")) : null))), { id: "gn-fingerprint" })) : null,
  bq?.available ? card("Uncertainty budget", el("p", { class: "muted small" }, `${d.budget.note} ${bq.share_rule}.`),
    table(["Source", "Class", "Value", "Share of variance"], [...bq.rows.map((r) => el("tr", {}, el("td", { class: "small" }, r.source + (r.note ? ` (${r.note})` : "")), el("td", {}, pill(r.class)),
      el("td", { class: "small" }, typeof r.value === "object" && r.value ? Object.entries(r.value).map(([k, v]) => `${k} ${fmtNum(v)}`).join(", ") : `${fmtNum(r.value)} ${r.unit}`),
      el("td", {}, r.variance_share === null || r.variance_share === undefined ? "—" : `${(100 * r.variance_share).toFixed(1)} %`))),
    ...d.budget.unquantified.map((r) => el("tr", {}, el("td", { class: "small" }, r.source), el("td", {}, pill("unquantified")), el("td", { class: "small wrap" }, r.why), el("td", {}, "—")))], { id: "gn-budget" })) : null);
}

function itemText(y) {
  if (y === null || y === undefined) return "—";
  if (typeof y === "number") return fmtNum(y, 4);
  if (typeof y !== "object") return String(y);
  if (y.hypothesis && y.test) return `${y.hypothesis} ${y.test} (${y.status})`;
  if (y.mode) return `${y.mode}: ${y.result}`;
  if (y.step) return `${y.step}: ${y.what}`;
  if (y.id) return y.status ? `${y.id} (${y.status})` : y.label ? `${y.id}: ${y.label}` : y.id;
  return Object.values(y).map(itemText).join(" ");
}

function fieldView(v) {
  if (!v || typeof v !== "object") return String(v ?? "—");
  const parts = [];
  if (v.value !== undefined) parts.push(el("span", {}, String(v.value ?? "—")));
  for (const [k, x] of Object.entries(v)) {
    if (["value", "cites"].includes(k) || x === null || x === undefined) continue;
    const txt = Array.isArray(x) ? (x.length ? x.map(itemText).join("; ") : "none") : itemText(x);
    parts.push(el("span", { class: "small" }, ` · ${k.replaceAll("_", " ")}: ${txt}`));
  }
  if (v.cites?.length) parts.push(el("div", { class: "faint small mono" }, "cites: " + v.cites.slice(0, 6).join(", ")));
  return el("span", {}, ...parts);
}

function compareView(C, swapped) {
  const A = swapped ? "second" : "first";
  return el("div", {}, table(["Characteristic", "This run", "Other run", "Rule", "Match"], C.shared_observational.map((s) =>
    el("tr", {}, el("th", { scope: "row" }, s.field), el("td", { class: "small" }, JSON.stringify(swapped ? s.b : s.a)), el("td", { class: "small" }, JSON.stringify(swapped ? s.a : s.b)),
      el("td", { class: "small" }, s.rule), el("td", {}, pill(s.match ? "met" : "not met"))))),
  kv([["Interpretations", `${C.interpretations[swapped ? "b" : "a"].category} (${C.interpretations[swapped ? "b" : "a"].region}) vs ${C.interpretations[swapped ? "a" : "b"].category} (${C.interpretations[swapped ? "a" : "b"].region})`],
    ["Similar weaknesses", C.similar_weaknesses.both.join(", ") || "none"], ["Same explanations, same status", C.evidence_patterns.same_explanations_same_status.join(", ") || "none"],
    ["Uncertainty propagated in both", C.uncertainty_structures.propagated_both.join(", ") || "none"],
    ["Reusable methods", C.reusable_methods.items.map((r) => `${r.method} (${r.from === "a" ? A : "other"})`).join(", ") || "none"]]),
  el("p", { class: "faint small" }, C.note));
}

// ------------------------------------------------------------------ Unknown Universe
let ukRegion = "unresolved";
async function unknownPanel(out, { d, rerender }) {
  const U = d.unknown;
  const W = 900, H = 300, cx = 600, cy = H - 12;
  const regions = U.regions;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "uk-map", id: "uk-map", role: "img", "aria-label": "Map of the research frontier: established knowledge at the centre, unknowns outward" });
  regions.forEach((r, i) => {
    const r0 = 34 + i * 32, r1 = r0 + 30;
    const path = `M ${cx - r1} ${cy} A ${r1} ${r1} 0 0 1 ${cx + r1} ${cy} L ${cx + r0} ${cy} A ${r0} ${r0} 0 0 0 ${cx - r0} ${cy} Z`;
    const g = el("g", { class: `uk-band uk-${i}${r.id === ukRegion ? " current" : ""}`, tabindex: "0", role: "button", "data-region": r.id, "aria-label": `${r.name}: ${r.n} item(s)` },
      el("path", { d: path }), el("text", { x: cx, y: cy - r0 - 10, class: "uk-count" }, String(r.n)),
      el("rect", { x: 8, y: 22 + i * 32, width: 16, height: 16, rx: 3, class: "uk-swatch" }),
      el("text", { x: 32, y: 35 + i * 32, class: "uk-label" }, `${r.rule_id} ${r.name} · ${r.n}`));
    const pick = () => { ukRegion = r.id; rerender(); };
    g.addEventListener("click", pick);
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); } });
    svg.append(g);
  });
  const R = regions.find((r) => r.id === ukRegion) || regions[0];
  const exp = el("button", { class: "btn small", type: "button", id: "uk-export" }, "Export the map (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-unknown-universe.json", JSON.stringify(U, null, 1), "application/json")) toast("Map exported"); });
  put(out, card("The unknown universe of this target", el("p", { class: "muted small" }, U.note), el("div", { class: "table-wrap" }, svg),
    el("p", { class: "faint small" }, `Inner bands hold what the records establish; outer bands what they leave open. ${U.n_runs_considered} recorded run(s) of this target were considered for unexplored parameters.`),
    el("div", { class: "controls" }, exp)),
  card(`${R.name} (${R.n})`, el("p", { class: "small" }, el("strong", {}, `${R.rule_id}: `), R.rule),
    R.items.length ? el("ul", { class: "plain", id: "uk-items" }, ...R.items.map((i) => el("li", { "data-ukitem": i.id }, el("p", { class: "small wrap" }, i.label,
      R.id === "weak" || R.id === "supported" ? el("span", {}, " ", kindChip("unverified")) : null),
    el("p", { class: "faint small" }, `basis: ${i.basis} · ref: ${i.ref ?? "—"}`, i.ref && String(i.ref).startsWith("graph:") ? el("span", {}, " · ", openGraph(i.ref)) : null))))
      : el("p", { class: "empty", id: "uk-items" }, "No recorded item meets this region's rule — not a statement that nothing is unknown here.")));
}

// ------------------------------------------------------------------ Multi-Discovery Network
let netRule = "all";
async function networkPanel(out, { d, corpus, rerender }) {
  const N = corpus.network;
  const sel = el("select", { id: "net-rule", "aria-label": "Relationship rule" }, el("option", { value: "all" }, "all rules"),
    ...Object.entries(N.rules).map(([k, r]) => el("option", { value: k, selected: k === netRule || null }, `${k} ${r.name} (${N.counts[k]})`)));
  sel.addEventListener("change", () => { netRule = sel.value; rerender(); });
  const edges = N.edges.filter((e) => netRule === "all" || e.rules.includes(netRule));
  const W = 900, H = 360, R0 = 140;
  const pos = new Map(N.nodes.map((n, i) => { const a = (2 * Math.PI * i) / Math.max(1, N.nodes.length) - Math.PI / 2; return [n.id, [W / 2 + R0 * 1.9 * Math.cos(a), H / 2 + R0 * Math.sin(a)]]; }));
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "net-svg", id: "net-graph", role: "img", "aria-label": "Investigations and the stated relationships between them" },
    ...edges.map((e) => { const [x1, y1] = pos.get(e.a), [x2, y2] = pos.get(e.b); return el("line", { x1, y1, x2, y2, class: `net-edge${e.rules.includes("N2") ? " conflict" : ""}` }); }),
    ...N.nodes.map((n) => { const [x, y] = pos.get(n.id); return el("g", { class: `net-node${n.record === d.content_hash ? " current" : ""}`, "data-node": n.id },
      el("circle", { cx: x, cy: y, r: 9 }), el("text", { x: x + 12, y: y + 4 }, `${n.target} ${n.id.slice(0, 6)}`)); }));
  const byId = Object.fromEntries(N.nodes.map((n) => [n.id, n]));
  put(out, card("Multi-discovery network", el("p", { class: "muted small" }, N.note), el("div", { class: "controls" }, el("label", { for: "net-rule" }, "Show"), sel),
    el("div", { class: "table-wrap" }, svg)),
  card(`Relationships (${edges.length})`, edges.length ? el("ul", { class: "plain", id: "net-edges" }, ...edges.slice(0, 60).map((e) => el("li", { "data-edge": `${e.a}|${e.b}` },
    el("p", {}, el("strong", { class: "mono small" }, `${byId[e.a].target} ${e.a.slice(0, 8)} — ${byId[e.b].target} ${e.b.slice(0, 8)}`)),
    el("ul", { class: "plain small" }, ...e.relationships.filter((r) => netRule === "all" || r.rule === netRule).map((r) => el("li", {}, pill(r.rule), ` ${r.name}: ${r.basis}`,
      el("div", { class: "faint" }, `limitation: ${r.limitation}`)))))))
    : el("p", { class: "empty", id: "net-edges" }, "No pair of investigations meets this rule.")));
}

// ------------------------------------------------------------------ Discovery Integrity Gate (+ research debt, time capsule, handoff, knowledge export)
async function gatePanel(out, { d, spec, rerender }) {
  const s = state.session;
  const led = overlayLedger(d.adversary, s);
  const G = overlayGate(d.gate, led, s);
  const done = s?.completion && s.completion.record === d.content_hash ? s.completion : null;
  const mark = el("button", { class: "btn primary", type: "button", id: "gt-mark", disabled: G.outcome !== "ready to mark complete" || done ? "" : null },
    done ? "Marked complete" : "Mark the investigation complete");
  mark.addEventListener("click", async () => {
    if (G.outcome !== "ready to mark complete") return;
    await S.update("gate.complete", `Investigation ${short(d.content_hash)} marked complete (GATE-1: every requirement met)`, (x) => {
      x.completion = { record: d.content_hash, at: nowIso(), outcome: G.outcome, requirements: G.requirements.map((r) => ({ id: r.id, state: r.state })), synthetic: G.synthetic };
      return x;
    }, d.content_hash);
    toast("Marked complete — this records that the gate's requirements were met, not that the conclusions are true"); rerender();
  });
  const capsule = el("button", { class: "btn", type: "button", id: "gt-capsule" }, "Freeze a time capsule");
  capsule.addEventListener("click", async () => {
    const c = await buildCapsule(d, G, led);
    await S.update("capsule.freeze", `Time capsule ${short(c.digest)} of run ${short(d.content_hash)}`, (x) => { x.capsules = [...(x.capsules || []), { digest: c.digest, at: c.frozen_at, record: d.content_hash, gate: G.outcome }].slice(-20); return x; }, c.digest);
    if (await download(`skytrace-capsule-${short(c.digest)}.json`, JSON.stringify(c, null, 1), "application/json")) toast("Time capsule frozen and exported");
    rerender();
  });
  const handoff = el("button", { class: "btn", type: "button", id: "gt-handoff" }, "Prepare a handoff (Markdown)");
  handoff.addEventListener("click", async () => { if (await download(`skytrace-handoff-${short(d.content_hash)}.md`, handoffText(d, G, led), "text/markdown")) toast("Handoff prepared"); });
  const kexp = el("button", { class: "btn", type: "button", id: "gt-export" }, "Export the knowledge package (JSON)");
  kexp.addEventListener("click", async () => {
    const ents = [...d.entities.items, ...(state.session ? sessionEntities(state.session) : [])];
    const pkg = { schema: "skytrace.knowledge/1", method: spec.methods.entity, entity_schema: spec.entity, exported_at: nowIso(), record: d.content_hash, synthetic: d.synthetic,
      session: state.session?.content_hash ?? null, entities: ents, gate: G, unknown_counts: Object.fromEntries(d.unknown.regions.map((r) => [r.id, r.n])),
      note: "Every entity carries a stable id, a version, provenance, a creation time and an epistemic status. The digest covers everything except itself." };
    pkg.digest = await digest(pkg);
    if (await download(`skytrace-knowledge-${short(d.content_hash)}.json`, JSON.stringify(pkg, null, 1), "application/json")) toast("Knowledge package exported");
  });
  put(out, card("Discovery integrity gate", el("h3", { id: "gt-outcome" }, pill(G.outcome)), el("p", { class: "muted small" }, G.meaning),
    table(["Requirement", "State", "Detail"], G.requirements.map((r) => el("tr", { "data-req": r.id, class: r.state === "met" ? "" : "flag" }, el("th", { scope: "row" }, `${r.id} ${r.name}`), el("td", {}, pill(r.state)),
      el("td", { class: "small wrap" }, r.detail, r.id === "G3" && r.state !== "met" ? el("span", {}, " ", goButton("Research cycle", "cycle")) : null,
        ["G6", "G7"].includes(r.id) && r.state !== "met" ? el("span", {}, " ", goButton("Examine challenges", "adversary")) : null))), { id: "gt-table" }),
    el("div", { class: "controls" }, mark, done ? el("span", { class: "small faint" }, `on ${done.at}`) : null)),
  card(`Research debt (${d.debt.items.length})`, el("p", { class: "muted small" }, d.debt.note), el("ul", { class: "plain small", id: "gt-debt" }, ...d.debt.items.map((i) =>
    el("li", {}, el("span", { class: "pill" }, i.kind), ` ${i.label} `, el("span", { class: "faint" }, `(${i.source})`))))),
  card("Preserve and hand over", el("p", { class: "muted small" }, "A time capsule freezes what is known now: the record, its reasoning-record digest, the gate, open questions and unknowns, with a SHA-256 digest of the whole. A handoff lists outstanding questions, required evidence and reproduction instructions for another researcher (no live collaboration is implied). The knowledge package exports every entity with its schema."),
    el("div", { class: "controls" }, capsule, handoff, kexp),
    (s?.capsules || []).length ? table(["Capsule", "Frozen", "Run", "Gate"], s.capsules.map((c) => el("tr", {}, el("td", { class: "mono small" }, short(c.digest)), el("td", { class: "small" }, c.at),
      el("td", { class: "mono small" }, short(c.record)), el("td", {}, c.gate))), { id: "gt-capsules" }) : null),
  card("Entities", el("p", { class: "muted small" }, d.entities.summary.note), kv([["Objects", String(d.entities.summary.n)], ["Validation", d.entities.errors.length ? d.entities.errors.join("; ") : "every entity valid; every provenance reference resolves"],
    ["By status", Object.entries(d.entities.summary.by_status).filter(([, n]) => n).map(([k, n]) => `${n} ${k}`).join(", ")]])));
}

async function buildCapsule(d, G, led) {
  const open = led.conclusions.flatMap((c) => c.questions.flatMap((q) => q.items)).filter((i) => i.status === "open").map((i) => i.id);
  const c = { schema: "skytrace.capsule/1", method: "CAPSULE-1", frozen_at: nowIso(), record: d.content_hash, target: d.target_id, synthetic: d.synthetic,
    reasoning_record_digest: await digest(d.entities.items.map((x) => x.id)), session: state.session?.content_hash ?? null, gate: G,
    conclusions: led.conclusions.map((x) => ({ question: x.question, category: x.category, region: x.region })), open_challenges: open,
    unknowns: Object.fromEntries(d.unknown.regions.map((r) => [r.id, r.items.map((i) => i.id)])), methods: d.reproduction.methods, data: d.reproduction.dataset,
    note: "A frozen description of what was known at this moment. It is not a new observation and does not change the record." };
  c.digest = await digest(c);
  return c;
}

function handoffText(d, G, led) {
  const L = [`# Investigation handoff — ${d.target_id} (run ${short(d.content_hash)})`, "", d.synthetic ? "**Synthetic test data.** Nothing here is an astronomical result." : "", "",
    "## Where it stands", ...led.conclusions.map((c) => `- ${c.question}: ${c.category} (knowledge boundary: ${c.region})`), "",
    `## Integrity gate: ${G.outcome}`, ...G.requirements.map((r) => `- ${r.id} ${r.name}: ${r.state} — ${r.detail}`), "",
    "## Outstanding questions", ...(d.unknown.regions.find((r) => r.id === "unresolved")?.items || []).slice(0, 20).map((i) => `- ${i.label} (${i.basis})`), "",
    "## Evidence still required", ...d.cycle.proposals.map((p) => `- ${p.title} — ${p.why} (rule ${p.rule})`),
    ...(d.unknown.regions.find((r) => r.id === "missing")?.items || []).slice(0, 10).map((i) => `- ${i.label}`), "",
    "## Open challenges", ...led.conclusions.flatMap((c) => c.questions.flatMap((q) => q.items.filter((i) => i.status === "open").map((i) => `- [${i.severity}] ${i.objection} — follow-up: ${i.follow_up}`))).slice(0, 25), "",
    "## How to reproduce", `1. Obtain the bundle \`${d.reproduction.dataset.bundle}\` (manifest SHA-256 \`${d.reproduction.dataset.manifest_sha256}\`).`,
    "2. Install Skytrace " + (d.reproduction.software?.skytrace || "") + " and run `python scripts/analyze_target.py " + d.target_id + "` with the configuration below.",
    "3. Compare your reproduction manifest with this run's in the Reproduction Network (exact, numerical, methodological, missing dependency, different input or unexplained).", "",
    "```json", JSON.stringify(d.reproduction.configuration, null, 1), "```", "", "## Limitations", ...d.reproduction.limitations.slice(0, 15).map((l) => `- ${l}`), "",
    "This handoff describes recorded work. It does not imply live collaboration, and a reproduction shows the calculation repeats, not that it is true."];
  return L.filter((x, i, a) => !(x === "" && a[i - 1] === "")).join("\n");
}
