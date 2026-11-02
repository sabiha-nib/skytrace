// Scientific Intelligence workspace, second half: the What-if Lab (WHATIF-1), the Causality Lab (CAUSAL-1), the Observation
// Oracle (ORACLE-1, EVNEG-1), the Scientific Adversary (ADV-1, INSTCHECK-1), the Research Cycle (CYCLE-1 with the three
// autonomy levels) and the Reproduction Network (REPRONET-1). Session-dependent rules run in intelcore.js (parity-tested).

import { emit, state } from "./state.js";
import { STATIC } from "./api.js";
import * as S from "./session.js";
import { execute } from "./executor.js";
import { download, el, toast } from "./util.js";
import { table, kv } from "./epiui.js";
import { causalWarnings, failureWarnings, hypotheticalVisit, oracleEvaluate, overlayGate, overlayLedger, reproCompare, reproValidate, validateOracleSpec } from "./intelcore.js";
import { QLABEL, card, fmtNum, kindChip, nowIso, pill, put, short } from "./intelbits.js";

const memWarn = (corpus, d, action) => {
  const W = failureWarnings(corpus.memory, d.target_id, [action]);
  return W.length ? el("div", { class: "card warn-card", "data-memwarn": action.id }, el("p", { class: "small" }, el("strong", {}, "Memory of failure: "),
    `${W.length} earlier failure(s) of this target bear on this.`), el("ul", { class: "plain small" }, ...W.slice(0, 4).map((w) => el("li", {}, pill(w.rule), ` ${w.what_failed}`)))) : null;
};

// ------------------------------------------------------------------ What-if Lab
let wiDt = 1.0, wiPos = "static", wiK = 1.0, wiLast = null;
export async function whatifPanel(out, { d, corpus, rerender }) {
  const W = d.whatif;
  const cards = W.questions.map((q) => {
    const body = [];
    if (q.runs?.length) body.push(table(["Change", "Label", "Conclusions that changed", "Stayed"], q.runs.map((r) => el("tr", {}, el("td", { class: "small" }, r.setting), el("td", {}, kindChip(r.label === "simulated" ? "simulated" : "verified")),
      el("td", { class: "small wrap" }, r.changed ? (r.changed.map((c) => `${c.question}: ${c.baseline} → ${c.scenario}`).join("; ") || "none") : r.detected_before !== undefined ? (r.detected_before !== r.detected_after ? `motion detection ${r.detected_before ? "lost" : "gained"} (S ${fmtNum(r.snr_before)} → ${fmtNum(r.snr_after)})` : "none") : "—"),
      el("td", { class: "small" }, r.stable ? r.stable.map((c) => c.question).join(", ") || "—" : r.detected_before !== undefined ? (r.detected_before === r.detected_after ? `motion (S ${fmtNum(r.snr_before)} → ${fmtNum(r.snr_after)})` : "—") : "—")))));
    if (q.scenario) {
      const b = el("button", { class: "btn small ghost", type: "button" }, "Run the full scenario in the Counterfactual Lab");
      b.addEventListener("click", () => emit("goto", { ws: "counterfactual" }));
      body.push(el("p", { class: "small" }, `Full pipeline re-run: ${q.scenario.kind} ${JSON.stringify(q.scenario.change)} `, b));
    }
    if (q.open) body.push(el("p", { class: "small" }, "Instrumental explanations not ruled out: ", q.open.join(", ") || "none"));
    if (q.re_analyses?.length) body.push(el("p", { class: "small" }, "Re-analyses that remove one cause: ", q.re_analyses.map((r) => `${r.explanation}: ${r.re_analysis.what}`).join("; ")));
    if (q.alternatives) body.push(el("p", { class: "small" }, q.alternatives.map((a) => `${a.id} ${a.status}`).join(" · "), ` (${q.n_pairs} distinguishing comparisons in the Observation Oracle)`));
    if (q.motion?.available) body.push(el("p", { class: "small" }, `Motion: S = ${fmtNum(q.motion.before.snr)} → ${fmtNum(q.motion.after.snr)} with one visit at the static position a year later (${q.motion.after.detected ? "still detected" : "not detected"}).`), q.variability ? el("p", { class: "small faint" }, `Brightness: ${q.variability}`) : null);
    return el("div", { class: "card", "data-whatif": q.id }, el("div", { class: "next-head" }, el("strong", {}, `${q.id} ${q.question}`), pill(q.kind), q.kind === "computed here" || q.kind === "scenario" ? kindChip("hypothetical") : null),
      el("p", { class: "small" }, el("strong", {}, "Changed assumption: "), q.changed_assumption), el("p", { class: "small muted" }, q.detail), ...body);
  });
  const mc = W.motion_context;
  const dt = el("input", { type: "number", id: "wi-dt", min: "0.1", max: "20", step: "0.1", value: String(wiDt), "aria-label": "Years after the last visit" });
  const pos = el("select", { id: "wi-pos", "aria-label": "Where the hypothetical visit finds the source" }, el("option", { value: "static", selected: wiPos === "static" || null }, "at its mean position (contradicts motion)"),
    el("option", { value: "track", selected: wiPos === "track" || null }, "on the fitted track (supports motion)"));
  const k = el("input", { type: "number", id: "wi-k", min: "0.1", max: "10", step: "0.1", value: String(wiK), "aria-label": "Error factor" });
  const run = el("button", { class: "btn primary", type: "button", id: "wi-run" }, "Compute");
  const res = el("div", { id: "wi-out" }, wiLast ? visitView(wiLast) : null);
  run.addEventListener("click", () => {
    wiDt = Number(dt.value); wiPos = pos.value; wiK = Number(k.value);
    wiLast = hypotheticalVisit(mc, wiDt, wiPos, wiK, W.detect_threshold);
    res.replaceChildren(visitView(wiLast));
  });
  const rec = el("button", { class: "btn small", type: "button", id: "wi-record" }, "Record this what-if in the session");
  rec.addEventListener("click", async () => {
    if (!wiLast?.available) { toast("Compute a what-if first"); return; }
    await S.update("whatif.record", `What-if (hypothetical): visit +${wiDt} yr ${wiPos}, S ${fmtNum(wiLast.before.snr)} → ${fmtNum(wiLast.after.snr)}`, (s) => {
      s.scenarios = [...(s.scenarios || []), { label: `what-if: hypothetical visit +${wiDt} yr (${wiPos})`, kind: "whatif", at: nowIso(), hypothetical: true, baseline: d.content_hash,
        result: { snr_before: wiLast.before.snr, snr_after: wiLast.after.snr, detected_after: wiLast.after.detected } }].slice(-40);
      return s;
    }, d.content_hash);
    toast("Recorded as a hypothetical scenario; the record is unchanged");
  });
  put(out, card("What-if Lab", el("p", { class: "muted small" }, W.note)), memWarn(corpus, d, { id: "whatif", label: "what-if", question: state.inv ? "variability" : null, concepts: ["calibration", "error_model"] }),
    ...cards,
    card("A hypothetical new visit", kindChip("hypothetical"), el("p", { class: "muted small" }, mc.available ? `${mc.rule}. Refit ${mc.validated ? "reproduces" : "does NOT reproduce"} the recorded fit.` : mc.why),
      mc.available && mc.validated ? el("div", { class: "controls" }, el("label", { for: "wi-dt" }, "Years after the last visit"), dt, el("label", { for: "wi-pos" }, "Source"), pos,
        el("label", { for: "wi-k" }, "Error × "), k, run, rec) : null, res));
}

function visitView(v) {
  if (!v.available) return el("p", { class: "withheld" }, v.why);
  return el("div", {}, kindChip("hypothetical"), table(["", "|μ| (mas/yr)", "σ (mas/yr)", "S = |μ|/σ", "Detected (S ≥ 5)"], [["recorded visits", v.before], ["with the hypothetical visit", v.after]].map(([n, x]) =>
    el("tr", {}, el("th", { scope: "row" }, n), el("td", {}, fmtNum(x.pm_mas_yr)), el("td", {}, fmtNum(x.sigma_mas_yr)), el("td", { id: n.startsWith("with") ? "wi-snr" : null }, fmtNum(x.snr)), el("td", {}, x.detected ? "yes" : "no")))),
  el("p", { class: "faint small" }, `${v.rule}. ${v.note}`));
}

// ------------------------------------------------------------------ Causality Lab
let clModel = null;
export async function causalPanel(out, { d, spec, rerender }) {
  const L = d.causal;
  if (!clModel || !L.models.find((m) => m.id === clModel)) clModel = L.models.find((m) => m.cause)?.id;
  const M = L.models.find((m) => m.id === clModel);
  // layered layout: depth = longest path from a root
  const par = {}; Object.keys(L.variables).forEach((v) => { par[v] = []; }); L.edges.forEach((e) => par[e.target].push(e.source));
  const depth = {}; const dep = (v) => (depth[v] ??= par[v].length ? 1 + Math.max(...par[v].map(dep)) : 0); Object.keys(L.variables).forEach(dep);
  const cols = []; Object.keys(L.variables).forEach((v) => { (cols[depth[v]] ||= []).push(v); });
  const W = 960, colW = W / cols.length, H = Math.max(...cols.map((c) => c.length)) * 46 + 30;
  const p = new Map(); cols.forEach((c, i) => c.forEach((v, j) => p.set(v, [i * colW + 8, 20 + j * 46])));
  const hot = new Set(M ? [M.cause, M.effect, ...M.confounders] : []);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "cl-svg", id: "cl-graph", role: "img", "aria-label": "Documented causal graph of the measurement process" },
    el("defs", {}, el("marker", { id: "cl-arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse" }, el("path", { d: "M 0 0 L 10 5 L 0 10 z", class: "cl-arrowhead" }))),
    ...L.edges.map((e) => { const [x1, y1] = p.get(e.source), [x2, y2] = p.get(e.target); return el("line", { x1: x1 + colW - 22, y1: y1 + 14, x2: x2, y2: y2 + 14, class: "cl-edge", "marker-end": "url(#cl-arrow)" }); }),
    ...Object.keys(L.variables).map((v) => { const [x, y] = p.get(v); return el("g", { class: `cl-node${hot.has(v) ? " hot" : ""}${M && v === M.cause ? " cause" : ""}${M && v === M.effect ? " effect" : ""}`, "data-var": v },
      el("rect", { x, y, width: colW - 22, height: 28, rx: 5 }), el("title", {}, L.variables[v]), el("text", { x: x + 6, y: y + 18 }, v.replaceAll("_", " "))); }));
  const rows = L.models.map((m) => {
    const tr = el("tr", { "data-model": m.id, class: m.id === clModel ? "sel" : "", tabindex: "0" }, el("th", { scope: "row" }, m.id), el("td", { class: "small" }, m.cause ?? "—"),
      ...spec.causal.criteria.map(([c, n]) => el("td", { class: "cl-crit", title: `${c} ${n}: ${m.criteria[c] ? "met" : "not met"}` }, m.criteria[c] ? "✓" : "·")), el("td", { class: "small" }, m.label),
      el("td", { class: "small" }, m.confounders.join(", ") || "—"));
    tr.addEventListener("click", () => { clModel = m.id; rerender(); });
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") { clModel = m.id; rerender(); } });
    return tr;
  });
  const vs = Object.keys(L.variables);
  const from = el("select", { id: "cl-from", "aria-label": "Proposed cause" }, ...vs.map((v) => el("option", { value: v }, v)));
  const rel = el("select", { id: "cl-rel", "aria-label": "Relationship" }, ...["causes", "correlates with", "precedes", "is plausibly linked to"].map((r) => el("option", { value: r }, r)));
  const to = el("select", { id: "cl-to", "aria-label": "Proposed effect" }, ...vs.map((v) => el("option", { value: v, selected: v === "flux_difference" || null }, v)));
  const add = el("button", { class: "btn small", type: "button", id: "cl-add" }, "Add my proposal");
  add.addEventListener("click", async () => {
    await S.update("causal.propose", `Causal proposal (user): ${from.value} ${rel.value} ${to.value}`, (s) => { s.causal = [...(s.causal || []), { from: from.value, rel: rel.value, to: to.value, label: "user-proposed", at: nowIso() }].slice(-30); return s; });
    rerender();
  });
  const warns = causalWarnings(state.session, L.models, spec.causal.causal_words);
  put(out, card("Causality Lab", el("p", { class: "muted small" }, L.note), el("p", { class: "small" }, kindChip("unverified"), " ", L.assumption), el("div", { class: "table-wrap" }, svg),
    M ? el("p", { class: "small", id: "cl-selected" }, el("strong", {}, `${M.id}: `), `${M.cause} → ${M.effect}. Mechanism: ${M.mechanism}. Confounders (common causes in the graph): ${M.confounders.join(", ") || "none"}. `,
      M.intervention ? `Re-analysis probe: ${M.intervention.what} (Counterfactual Lab; an intervention on the analysis, not on the sky). ` : "", M.C5_note) : null),
  card("Competing causal models", table(["Model", "Cause", ...spec.causal.criteria.map(([c]) => c), "Standing", "Confounders"], rows, { id: "cl-models" }),
    el("p", { class: "faint small" }, "C1 correlation · C2 temporal association · C3 mechanistic plausibility · C4 causal hypothesis · C5 experimentally supported (never reachable with archival observations). No single verdict is given.")),
  card("Temporal inspection", el("p", { class: "muted small" }, L.temporal.rule), table(["Detector", "Visits", "Pearson r", "Association"], L.temporal.variability.map((r) =>
    el("tr", {}, el("td", {}, `D${r.detector}`), el("td", {}, String(r.visits)), el("td", {}, fmtNum(r.r)), el("td", {}, r.association ? "yes" : "no"))), { id: "cl-temporal" }),
    L.temporal.motion ? el("p", { class: "small" }, `Motion: r(ξ) ${fmtNum(L.temporal.motion.r_xi)}, r(η) ${fmtNum(L.temporal.motion.r_eta)} over ${L.temporal.motion.visits} visits — association ${L.temporal.motion.association ? "yes" : "no"}.`) : null),
  card("Your causal proposals", el("p", { class: "muted small" }, "Recorded as user-proposed. A proposal with causal wording is checked against the lab's criteria; correlation alone never establishes causation."),
    el("div", { class: "controls" }, from, rel, to, add),
    warns.length ? el("ul", { class: "plain small", id: "cl-warn" }, ...warns.map((w) => el("li", { class: "warn-item" }, el("strong", {}, w.proposal), el("div", {}, w.warning)))) : el("p", { class: "faint small", id: "cl-warn" }, "No causal-language proposal yet.")));
}

// ------------------------------------------------------------------ Observation Oracle
let orQ = null, orH1 = "", orCands = null, orLast = null;
export async function oraclePanel(out, { d, corpus, rerender, focus }) {
  void STATIC;
  const O = d.oracle;
  if (!orQ) orQ = focus === "motion" ? "motion" : "variability";
  if (!orCands || orCands.q !== orQ) orCands = { q: orQ, rows: exampleSpecs(orQ) };
  const qs = el("select", { id: "or-q", "aria-label": "Question" }, ...["motion", "variability"].map((q) => el("option", { value: q, selected: q === orQ || null }, QLABEL[q])));
  qs.addEventListener("change", () => { orQ = qs.value; orLast = null; rerender(); });
  const h1 = el("input", { type: "number", id: "or-h1", step: "any", min: "0", value: orH1, placeholder: orQ === "motion" ? `recorded |μ| ${fmtNum(O.context.recorded_pm_mas_yr)}` : "0.05", "aria-label": orQ === "motion" ? "H1 |μ| (mas/yr)" : "H1 fractional change f" });
  h1.addEventListener("input", () => { orH1 = h1.value; });
  const rows = el("div", { id: "or-cands" }, ...orCands.rows.map((c, i) => candRow(c, i)));
  const addB = el("button", { class: "btn small ghost", type: "button", id: "or-add" }, "Add a candidate");
  addB.addEventListener("click", () => { if (orCands.rows.length < 6) { orCands.rows.push(orQ === "motion" ? { label: `candidate ${orCands.rows.length + 1}`, years: "1", factor: "1" } : { label: `candidate ${orCands.rows.length + 1}`, err: "0.01" }); rerender(); } });
  const runB = el("button", { class: "btn primary", type: "button", id: "or-run" }, "Evaluate the candidates");
  const res = el("div", { id: "or-out" }, orLast ? oracleView(orLast) : null);
  runB.addEventListener("click", async () => {
    const spec = { question: orQ, candidates: orCands.rows.map((c) => (orQ === "motion" ? { label: c.label, added_years_after_last: String(c.years).split(/[,\s]+/).filter(Boolean).map(Number), error_factor: Number(c.factor) } : { label: c.label, fractional_error: Number(c.err) })) };
    if (orH1) spec.h1_value = Number(orH1);
    const errs = validateOracleSpec(spec, O.max_added);
    if (errs.length) { res.replaceChildren(el("p", { class: "withheld" }, errs.join("; "))); return; }
    orLast = oracleEvaluate(O.context, spec, O.threshold);
    await S.log("oracle.plan", `Observation plan (hypothetical): ${orQ}, ${spec.candidates.length} candidate(s); first: ${orLast.ranking?.[0] ?? "none"}`, null, { create: true });
    res.replaceChildren(oracleView(orLast));
  });
  const N = d.negotiation;
  put(out, card("Observation Oracle", el("p", { class: "muted small" }, "Which hypothetical measurements would best separate two explanations, under the stated measurement model. The formula first reproduces the recorded fit; nothing is scheduled and no instrument availability is implied."),
    kindChip("hypothetical"), el("div", { class: "controls" }, el("label", { for: "or-q" }, "Question"), qs, el("label", { for: "or-h1" }, "H1"), h1), rows, el("div", { class: "controls" }, addB, runB), res),
  memWarn(corpus, d, { id: "oracle", label: "plan observations", question: orQ, concepts: [] }),
  card("Evidence negotiation", el("p", { class: "muted small" }, N.note), N.pairs.length ? table(["Question", "A", "B", "Would move A only", "Would move B only", "Shared open"], N.pairs.map((x) =>
    el("tr", {}, el("td", {}, x.question), el("td", {}, `${x.a} (${x.a_status})`), el("td", {}, `${x.b} (${x.b_status})`), el("td", { class: "small" }, x.decides_a.map((t) => `${t.test} ${t.status}`).join(", ") || "—"),
      el("td", { class: "small" }, x.decides_b.map((t) => `${t.test} ${t.status}`).join(", ") || "—"), el("td", { class: "small" }, x.shared_open.join(", ") || "—"))), { id: "or-neg" }) : el("p", { class: "empty", id: "or-neg" }, "Fewer than two viable explanations: nothing to negotiate.")));

  function candRow(c, i) {
    const lab = el("input", { type: "text", value: c.label, "aria-label": `Candidate ${i + 1} label`, class: "or-label" });
    lab.addEventListener("input", () => { c.label = lab.value; });
    const parts = [lab];
    if (orQ === "motion") {
      const y = el("input", { type: "text", value: c.years, "aria-label": `Candidate ${i + 1}: years after the last visit (comma-separated)`, class: "or-years" });
      const f = el("input", { type: "number", step: "0.1", min: "0.1", max: "10", value: c.factor, "aria-label": `Candidate ${i + 1}: error factor`, class: "or-factor" });
      y.addEventListener("input", () => { c.years = y.value; }); f.addEventListener("input", () => { c.factor = f.value; });
      parts.push(el("span", { class: "small faint" }, "years after last visit"), y, el("span", { class: "small faint" }, "error ×"), f);
    } else {
      const e = el("input", { type: "number", step: "any", min: "0.0001", max: "1", value: c.err, "aria-label": `Candidate ${i + 1}: fractional error per exposure`, class: "or-err" });
      e.addEventListener("input", () => { c.err = e.value; });
      parts.push(el("span", { class: "small faint" }, "fractional error per exposure"), e);
    }
    const rm = el("button", { class: "btn small ghost", type: "button", "aria-label": `Remove candidate ${i + 1}` }, "×");
    rm.addEventListener("click", () => { orCands.rows.splice(i, 1); rerender(); });
    return el("div", { class: "controls or-cand" }, ...parts, rm);
  }
}

function exampleSpecs(q) {
  const ex = { motion: [{ label: "one more visit a year after the last", years: "1", factor: "1" }, { label: "three more visits, one per year", years: "1, 2, 3", factor: "1" },
    { label: "one visit at half the error, two years on", years: "2", factor: "0.5" }], variability: [{ label: "1 % per-exposure precision", err: "0.01" }, { label: "0.5 % per-exposure precision", err: "0.005" }] };
  return ex[q].map((x) => ({ ...x }));
}

function oracleView(R) {
  if (!R.available) return el("p", { class: "withheld" }, R.why);
  return el("div", {}, kindChip("hypothetical"), table(["Set", "Label", "S (expected)", "E[Δχ²]", R.question === "motion" ? "σ_μ (mas/yr)" : "fractional error", "Separates H0/H1 (S ≥ 5)"], R.rows.map((r) =>
    el("tr", { "data-orrow": r.id, class: R.ranking[0] === r.id ? "sel" : "" }, el("td", {}, r.id), el("td", { class: "small" }, r.label), el("td", {}, fmtNum(r.expected_significance)), el("td", {}, fmtNum(r.expected_delta_chi2)),
      el("td", {}, fmtNum(R.question === "motion" ? r.sigma_mu_mas_yr : r.fractional_error)), el("td", {}, r.discriminates ? "yes" : "no"))), { id: "or-table" }),
  kv([["Ranking", R.ranking.join(" > ") || "—"], ["Rule", R.ranking_rule], ["Hypotheses", `H0: ${R.hypotheses.H0}; ${R.hypotheses.H1}`], ["Information gain", R.information_gain_note]]),
  el("ul", { class: "plain small" }, ...R.assumptions.map((a) => el("li", {}, a))), R.warnings.length ? el("p", { class: "small warn-item" }, R.warnings.join(" ")) : null);
}

// ------------------------------------------------------------------ Scientific Adversary
export async function adversaryPanel(out, { d, focus, rerender }) {
  const led = overlayLedger(d.adversary, state.session);
  const C = led.conclusions.find((c) => c.question === focus) || led.conclusions[0];
  const refs = [...(state.session?.experiments || []).map((x) => `experiment:${x.id}`), ...(state.session?.debug || []).filter((x) => x?.kind === "reproduction").map((x, i) => `reproduction:${i}`),
    ...(state.session?.scenarios || []).map((x, i) => `scenario:${i}`)];
  const mark = async (i, status, note, ref) => {
    await S.update("challenge.mark", `Challenge ${i.id}: ${status}${ref ? ` (by ${ref})` : ""}`, (s) => {
      s.challenges = [...(s.challenges || []).filter((m) => m.id !== i.id), { id: i.id, status, note: note || null, ref: ref || null, at: nowIso() }].slice(-300);
      return s;
    }, i.id);
    rerender();
  };
  const IC = d.instrumental;
  put(out, card(`Scientific adversary: ${QLABEL[C.question]} — ${C.category}`, el("p", { class: "muted small" }, led.note),
    el("p", { id: "adv-counts" }, ...Object.entries(C.by_severity).filter(([, n]) => n).map(([k, n]) => el("span", {}, pill(k), ` ${n} `)), " · ",
      ...Object.entries(C.by_status || { open: C.n }).map(([k, n]) => el("span", {}, pill(k), ` ${n} `)))),
  ...C.questions.map((q) => el("details", { class: "card", "data-advq": q.id, open: q.items.some((i) => i.status === "open" && ["major", "critical"].includes(i.severity)) ? "" : null },
    el("summary", {}, el("strong", {}, `${q.id === "other" ? "" : q.id + " "}${q.question}`), ` (${q.items.length})`),
    q.items.length ? el("ul", { class: "plain" }, ...q.items.map((i) => {
      const note = el("input", { type: "text", placeholder: "your note", "aria-label": `Note on ${i.id}`, class: "adv-note" });
      const ref = el("select", { "aria-label": `Recorded item that resolves ${i.id}`, class: "adv-ref" }, el("option", { value: "" }, "— resolved by… —"), ...refs.map((r) => el("option", { value: r }, r)));
      const ack = el("button", { class: "btn small ghost adv-ack", type: "button" }, "Acknowledge");
      const res = el("button", { class: "btn small ghost adv-resolve", type: "button" }, "Resolve");
      ack.addEventListener("click", () => mark(i, "acknowledged", note.value));
      res.addEventListener("click", () => { if (!ref.value) { toast("Resolving needs a recorded item (an experiment, reproduction or scenario in your session)"); return; } mark(i, "resolved", note.value, ref.value); });
      return el("li", { class: `adv-item sev-${i.severity}`, "data-chal": i.id }, el("div", { class: "next-head" }, pill(i.severity), pill(i.status), el("strong", {}, i.objection)),
        el("p", { class: "small" }, el("strong", {}, "Why it matters: "), i.rationale ?? "—"), el("p", { class: "small faint" }, `rule: ${i.rule} · evidence: ${i.evidence.join(", ") || "—"}`),
        el("p", { class: "small" }, el("strong", {}, "Follow-up test: "), i.follow_up), i.note ? el("p", { class: "small" }, `note: ${i.note}`) : null, i.resolved_by ? el("p", { class: "small" }, `resolved by ${i.resolved_by}`) : null,
        el("div", { class: "controls" }, note, ack, ref, res));
    })) : el("p", { class: "empty small" }, q.note))),
  card("Instrumental reality check", el("p", { class: "muted small" }, IC.note), table(["Check", "Question", "State", "Detail"], IC.checks.filter((r) => !r.question || r.question === C.question || C.question === "data_quality").map((r) =>
    el("tr", { "data-inst": r.id }, el("th", { scope: "row" }, `${r.id} ${r.name}`), el("td", {}, r.question ?? "all"), el("td", {}, pill(r.state)), el("td", { class: "small wrap" }, r.detail))), { id: "adv-inst" })));
}

// ------------------------------------------------------------------ Research Cycle (bounded autonomy)
let cyLevel = "advisory", cyRun = null, cyBusy = false;
export async function cyclePanel(out, { d, rerender }) {
  const levels = d.cycle.levels;
  const L = levels.find((l) => l.id === cyLevel);
  const gate = overlayGate(d.gate, overlayLedger(d.adversary, state.session), state.session);
  const props = d.cycle.proposals.filter((p) => !(p.rule === "A1" && gate.requirements.find((r) => r.id === "G3").state === "met"));
  const sel = el("select", { id: "cy-level", "aria-label": "Autonomy level" }, ...levels.map((l) => el("option", { value: l.id, selected: l.id === cyLevel || null }, `${l.name} — executes ${l.executes}`)));
  sel.addEventListener("change", () => { cyLevel = sel.value; rerender(); });
  const allowed = (p) => L.allows.includes(p.permission);
  const runStep = async (p, how) => {
    const step = { action: p.action, rule: p.rule, permission: p.permission, level: cyLevel, approved: how, started_at: nowIso() };
    try {
      const r = await execute(p.action, {});
      Object.assign(step, { status: r.status, result: r.result, finished_at: nowIso() });
    } catch (e) { Object.assign(step, { status: "failed", error: String(e.message).slice(0, 300), finished_at: nowIso() }); }
    return step;
  };
  const save = async (run) => {
    await S.update("cycle.run", `Research cycle (${run.level}): ${run.steps.map((s) => `${s.action} ${s.status}`).join(", ") || "proposals only"}`.slice(0, 280), (s) => {
      s.cycles = [...(s.cycles || []).filter((c) => c.id !== run.id), run].slice(-20); return s;
    }, run.id);
  };
  if (!cyRun || cyRun.record !== d.content_hash) cyRun = { id: S.newId("cyc"), record: d.content_hash, level: cyLevel, started_at: nowIso(), steps: [] };
  cyRun.level = cyLevel;
  const stepRows = props.map((p) => {
    const done = cyRun.steps.find((s) => s.action === p.action);
    const btn = el("button", { class: "btn small cy-run", type: "button", disabled: cyLevel !== "supervised" || !allowed(p) || done || cyBusy ? "" : null }, "Approve and run");
    btn.addEventListener("click", async () => {
      if (cyLevel !== "supervised" || cyBusy) return;
      cyBusy = true; btn.textContent = "Running…";
      cyRun.steps.push(await runStep(p, "approved this step"));
      cyBusy = false; await save(cyRun); rerender();
    });
    return el("li", { "data-step": p.action, class: done ? `cy-done cy-${done.status}` : "" }, el("div", { class: "next-head" }, el("strong", {}, p.title), pill(p.permission), done ? pill(done.status) : pill(cyLevel === "advisory" || allowed(p) ? "proposed" : "refused")),
      el("p", { class: "small" }, `${p.rule}: ${p.rule_text} — ${p.why}`), el("p", { class: "faint small" }, `addresses: ${p.addresses.join(", ")}`),
      done?.error ? el("p", { class: "withheld small" }, done.error) : done?.result ? el("p", { class: "small mono" }, JSON.stringify(done.result).slice(0, 200)) : null,
      cyLevel === "supervised" ? btn : null);
  });
  const wf = d.cycle.restricted_workflow;
  const auth = el("input", { type: "checkbox", id: "cy-auth" });
  const start = el("button", { class: "btn primary", type: "button", id: "cy-start" }, "Run the predefined workflow");
  start.addEventListener("click", async () => {
    if (cyLevel !== "restricted" || cyBusy) return;
    if (!auth.checked) { toast("Tick the authorization: it lists every step the workflow will run"); return; }
    cyBusy = true; start.textContent = "Running…";
    for (const a of wf) {
      const p = { action: a, rule: "workflow", permission: d.cycle.workflow_permissions[a] };
      if (!L.allows.includes(p.permission)) { cyRun.steps.push({ ...p, level: cyLevel, status: "skipped", error: `permission ${p.permission} not allowed at this level`, started_at: nowIso() }); continue; }
      if (cyRun.steps.find((s) => s.action === a && s.status === "completed")) continue;
      cyRun.steps.push(await runStep(p, "authorized the predefined workflow"));
    }
    cyBusy = false; await save(cyRun); rerender();
  });
  const rep = el("button", { class: "btn small", type: "button", id: "cy-report" }, "Download the cycle report (Markdown)");
  rep.addEventListener("click", async () => { if (await download(`skytrace-research-cycle-${short(d.content_hash)}.md`, cycleReport(d, cyRun, props, gate), "text/markdown")) toast("Report prepared for review"); });
  put(out, card("Research cycle", el("p", { class: "muted small" }, d.cycle.note),
    el("div", { class: "controls" }, el("label", { for: "cy-level" }, "Autonomy level"), sel),
    el("p", { class: "small", id: "cy-explain" }, cyLevel === "advisory" ? "Advisory: the cycle proposes; nothing is executed." : cyLevel === "supervised" ? "Supervised: each step runs only when you approve it." :
      `Restricted automation: one authorization runs exactly these registered actions, in order: ${wf.join(" → ")}.`),
    el("ol", { class: "plain cy-steps", id: "cy-steps" }, ...stepRows),
    cyLevel === "restricted" ? el("div", { class: "controls" }, auth, el("label", { for: "cy-auth" }, `I authorize ${wf.length} steps: ${wf.join(", ")}`), start) : null,
    el("div", { class: "controls" }, rep)),
  card("Proposed for you to decide (never executed by the cycle)", el("ul", { class: "plain small", id: "cy-later" }, ...d.cycle.for_you_to_decide.map((x) => el("li", {}, kindChip("hypothetical"), ` ${x.kind}: ${x.what}${x.spec ? " " + JSON.stringify(x.spec) : ""}`)))),
  cyRun.steps.length ? card("Audit log", table(["Step", "Permission", "Level", "Approved", "Status", "Started", "Finished"], cyRun.steps.map((s) => el("tr", {}, el("td", {}, s.action), el("td", {}, s.permission),
    el("td", {}, s.level), el("td", { class: "small" }, s.approved ?? "—"), el("td", {}, pill(s.status)), el("td", { class: "small" }, s.started_at ?? "—"), el("td", { class: "small" }, s.finished_at ?? "—"))), { id: "cy-log" })) : null);
}

function cycleReport(d, run, props, gate) {
  return [`# Research cycle — ${d.target_id} (run ${short(d.content_hash)})`, "", d.synthetic ? "**Synthetic test data.** This report describes a software test." : "", "",
    `Autonomy level: ${run.level}. Every step below is a registered action, executed only as the level allows; nothing altered source data or was published.`, "",
    "## Unanswered items and proposals", ...props.map((p) => `- ${p.title} (${p.permission}) — ${p.rule}: ${p.rule_text}; ${p.why}`), "",
    "## Executed steps", ...(run.steps.length ? run.steps.map((s) => `- ${s.action}: ${s.status}${s.error ? ` (${s.error})` : ""} — approved: ${s.approved ?? "—"} at ${s.started_at}`) : ["- none"]), "",
    `## Integrity gate now: ${gate.outcome}`, ...gate.requirements.map((r) => `- ${r.id} ${r.name}: ${r.state}`), "",
    "## Still unresolved", ...gate.requirements.filter((r) => r.state !== "met").map((r) => `- ${r.name}: ${r.detail}`), "",
    "## Proposed for you to decide", ...d.cycle.for_you_to_decide.map((x) => `- ${x.kind}: ${x.what}`), "",
    "No conclusion in this report is established by the cycle. It is prepared for your review."].join("\n");
}

// ------------------------------------------------------------------ Reproduction Network
let rpOther = "", rpLast = null;
export async function reproPanel(out, { d, corpus, rerender }) {
  const M = d.reproduction;
  const dl = el("button", { class: "btn primary", type: "button", id: "rp-manifest" }, "Download this run's reproduction manifest");
  dl.addEventListener("click", async () => { if (await download(`skytrace-reproduction-${short(M.record)}.json`, JSON.stringify(M, null, 1), "application/json")) toast("Manifest downloaded"); });
  const same = corpus.memory.investigations.filter((i) => i.target === d.target_id && i.record !== d.content_hash && i.iid);
  const other = el("select", { id: "rp-other", "aria-label": "Another recorded run" }, el("option", { value: "" }, "— another run of this target —"),
    ...same.map((i) => el("option", { value: i.iid, selected: i.iid === rpOther || null }, `${short(i.record)} · ${Object.entries(i.parameters).filter(([k]) => !["analysis_version", "reader", "max_observations"].includes(k)).length} parameters`)));
  const cmpB = el("button", { class: "btn", type: "button", id: "rp-compare-run" }, "Compare manifests");
  const paste = el("textarea", { id: "rp-paste", rows: "4", "aria-label": "Paste a reproduction manifest", placeholder: "Paste a skytrace.reproduction/1 manifest from another machine…" });
  const cmpP = el("button", { class: "btn", type: "button", id: "rp-compare-paste" }, "Compare with the pasted manifest");
  const res = el("div", { id: "rp-out" }, rpLast ? compView(rpLast) : null);
  cmpB.addEventListener("click", async () => {
    rpOther = other.value;
    if (!rpOther) { toast("Choose another run"); return; }
    try {
      const { api } = await import("./api.js");
      const o = await api.intelligence(rpOther);
      rpLast = await reproCompare(M, o.reproduction);
      res.replaceChildren(compView(rpLast));
    } catch (e) { res.replaceChildren(el("p", { class: "withheld" }, e.message)); }
  });
  cmpP.addEventListener("click", async () => {
    let m;
    try { m = JSON.parse(paste.value); } catch { res.replaceChildren(el("p", { class: "withheld" }, "Not JSON")); return; }
    const errs = await reproValidate(m);
    if (errs.length) { res.replaceChildren(el("p", { class: "withheld" }, `The manifest is not valid: ${errs.join("; ")}`)); return; }
    rpLast = await reproCompare(M, m);
    await S.log("repro.compare", `Reproduction comparison with ${short(m.record)}: ${rpLast.status}`, null, { create: true });
    res.replaceChildren(compView(rpLast));
  });
  put(out, card("Reproduction network", el("p", { class: "muted small" }, M.note),
    kv([["Record", M.record], ["Record hash recomputes", M.record_hash_ok ? "yes" : "no"], ["Dataset", `${M.dataset.bundle} (${M.dataset.kind}), ${M.dataset.files.length} files, manifest ${short(M.dataset.manifest_sha256)}`],
      ["Software", Object.entries(M.software).map(([k, v]) => `${k} ${v}`).join(", ")], ["Methods", Object.values(M.methods).flat().join(", ")], ["Seed", M.seed ?? "none recorded"],
      ["Stages", M.stages.map((s) => `${s.id} (${s.n_events})`).join(", ")], ["Manifest digest", M.manifest_digest]]),
    el("div", { class: "controls" }, dl)),
  card("Compare with another reproduction", el("p", { class: "muted small" }, "Classes, in order: exact match · different input data · methodological · missing dependency · numerical · unexplained divergence. A match shows the calculation repeats; it is not scientific validity."),
    el("div", { class: "controls" }, other, cmpB), paste, el("div", { class: "controls" }, cmpP), res));
}

function compView(C) {
  return el("div", { class: "card" }, el("h3", { id: "rp-status" }, pill(C.status), ` ${C.status}`), kv([["All classes", C.classes.join(", ")], ["Detail", C.detail.join("; ") || "—"],
    ["Stages differing", C.stages_differing.join(", ") || "none"], ["Earliest divergence", C.earliest_divergence ?? "none"], ["Outcomes differing", C.outcomes_differing.join(", ") || "none"],
    ["Environment differences", C.environment_differences.join(", ") || "none"], ["Both manifests valid", C.valid_a && C.valid_b ? "yes" : "no"]]), el("p", { class: "faint small" }, C.note));
}
