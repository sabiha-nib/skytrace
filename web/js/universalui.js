// Phase 10 workspaces and panels: Signal Intelligence (SIGNAL-1), the World Model (WORLD-1, CONV-1, LEAD-1, MODAL-1, TIMES-1),
// the Open Science Gateway (HANDOFF-1, the research flight recorder, open-science bundle, multilingual reports), and the
// sections Phase 10 adds to existing workspaces: nine negative-space distinctions (NEGX-1), knowledge-compiler statuses
// (KCOMP-1), novelty-scoped opportunities and external sources (OPP-2, EXTSRC-1), the investigation director (DIRECT-1),
// role agents (AGENTS-1) and the experiment marketplace (EXPMKT-1). Every value comes from the server's universal report
// (or the preview's recording of it); the session holds only what you did (approvals, debates, handoffs, interests).

import { api, STATIC } from "./api.js";
import { emit, state } from "./state.js";
import * as S from "./session.js";
import { $, clear, download, el, localizeExport, renderToken, toast } from "./util.js";
import { kv, needRun, num, syntheticNote, table, tabs } from "./epiui.js";
import { scatter } from "./charts.js";
import { getLang, getMeta, languages, setLang } from "./i18n.js";
import { build as buildHandoff, validate as validateHandoff } from "./handoff.js";
import { verifyChain, nowIso, rid } from "./sessioncore.js";
import { zipStore } from "./zipstore.js";

const VERSION = "0.10.0";

export async function getUniversal() {
  if (!state.inv) return null;
  const iid = state.inv.investigation_id;
  if (state.universal?.iid !== iid) state.universal = { iid, data: await api.universal(iid) };
  return state.universal.data;
}

async function load(body, ws, what = "Reading the recorded analysis…") {
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), what);
  body.append(holder);
  try {
    const d = await getUniversal();
    holder.remove();
    return !ws || state.ws === ws ? d : null;
  } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return null; }
}

const card = (title, ...kids) => el("section", { class: "card" }, el("h3", {}, title), ...kids);
const yes = (b) => el("span", { class: `pill ${b ? "out-ok" : "faint"}` }, b ? "applies" : "does not apply");

// ------------------------------------------------------------------ Signal Intelligence
let sigSel = 0;
export async function renderSignal() {
  const live = renderToken("signal");
  const body = clear($("#signal-body"));
  if (!state.inv) { needRun(body, "The workbench reads the series a recorded analysis contains."); return; }
  const u = await load(body, "signal");
  if (!u || !live()) return;
  const sg = u.signal;
  if (!sg.series.length) { body.append(el("p", { class: "empty" }, "This record contains no series with at least two points.")); return; }
  sigSel = Math.min(sigSel, sg.series.length - 1);
  const sel = el("select", { id: "sig-series", "aria-label": "Series" }, ...sg.series.map((s, i) => el("option", { value: String(i), selected: i === sigSel || null }, `${s.id} · N = ${s.n}`)));
  sel.addEventListener("change", () => { sigSel = +sel.value; renderSignal(); });
  const s = sg.series[sigSel], a = s.analysis;
  const M = Object.fromEntries(sg.methods.map((m) => [m.id, m]));
  const pts = s.data.t.map((t, i) => ({ x: t, y: s.data.y[i], ey: s.data.dy[i] }));
  const parts = [syntheticNote(u),
    el("p", { class: "muted" }, "Each series comes from the record as measured: nothing is interpolated, filled or resampled. Which methods apply is part of the result; a method that does not apply says why."),
    el("div", { class: "controls" }, el("label", { for: "sig-series" }, "Series"), sel),
    card(`${s.id}`, scatter({ xLabel: s.time_unit || "MJD (d)", yLabel: s.unit, series: [{ points: pts, color: "#8fb3ff" }], title: `${s.id}: values with 1σ errors`, xfmt: (v) => num(v, 6), yfmt: (v) => num(v, 4) }),
      el("ul", { class: "small muted" }, ...sg.series_rules.map((r) => el("li", {}, r)))),
    card("Method selection", table(["Method", "Applies", "Reason", "Assumptions", "Limits"], a.selection.map((x) =>
      el("tr", { "data-sig-method": x.method }, el("td", {}, M[x.method]?.name || x.method), el("td", {}, yes(x.applicable)), el("td", { class: "small" }, x.reason),
        el("td", { class: "small" }, M[x.method]?.assumptions || ""), el("td", { class: "small" }, M[x.method]?.limits || ""))), { id: "sig-selection" })),
    card("Sampling and noise", kv([["N", a.sampling.n], ["Span (d)", num(a.sampling.span)], ["Median spacing (d)", num(a.sampling.median_spacing)], ["Largest gap (d)", num(a.sampling.max_gap)],
      ["Uniform sampling", a.sampling.uniform ? "yes" : "no"], ["Frequency range tested (1/d)", a.sampling.f_min ? `${num(a.sampling.f_min)} – ${num(a.sampling.f_max_heuristic)}` : "—"],
      ["Weighted mean", num(a.noise.weighted_mean)], ["Reduced χ² of a constant", num(a.noise.reduced_chi2_constant)], ["RMS / median error", `${num(a.noise.rms)} / ${num(a.noise.median_error)}`]]),
      el("p", { class: "small" }, a.noise.reading || a.noise.reason || ""), el("p", { class: "faint small" }, a.sampling.note || ""))];
  if (a.window) parts.push(card("Spectral window", scatter({ xLabel: "frequency (1/d)", yLabel: "window power", series: [{ line: a.window.freq.map((f, i) => [f, a.window.power[i]]) }], xfmt: (v) => num(v, 3), yfmt: (v) => num(v, 2) }),
    el("p", { class: "small muted" }, "Computed from the sampling times alone. A periodogram peak where the window is high can be produced by the sampling.")));
  if (a.lomb_scargle) {
    const ls = a.lomb_scargle;
    parts.push(card("Lomb–Scargle periodogram", scatter({ xLabel: "frequency (1/d)", yLabel: "power", series: [{ line: ls.freq.map((f, i) => [f, ls.power[i]]) }], xfmt: (v) => num(v, 3), yfmt: (v) => num(v, 2) }),
      kv([["Peak frequency (1/d)", num(ls.peak.frequency)], ["Period (d)", num(ls.peak.period)], ["Peak power", num(ls.peak.power)], ["Window power there", num(ls.peak.window_power)]]),
      el("p", { class: "small" }, ls.reading), el("p", { class: "faint small" }, ls.rule)));
  }
  if (a.robust_regression) {
    const ts = a.robust_regression.theil_sen, w = a.robust_regression.weighted_least_squares;
    parts.push(card("Robust trend", kv([["Theil–Sen slope", `${num(ts.slope)} ${a.robust_regression.slope_unit}`], ["Slope interquartile range", ts.slope_iqr ? `${num(ts.slope_iqr[0])} – ${num(ts.slope_iqr[1])}` : "—"],
      ["Pairwise slopes positive / negative", `${ts.slopes_positive} / ${ts.slopes_negative}`], ["Weighted least squares", `${num(w.slope)} ± ${num(w.sig_slope)}`]]),
      el("p", { class: "faint small" }, "A trend over the span does not say what happened between observations.")));
  }
  if (a.change_point) parts.push(card("Change point", a.change_point.applicable ? kv([["Between (MJD)", `${num(a.change_point.between[0], 7)} and ${num(a.change_point.between[1], 7)}`],
    ["Mean before / after", `${num(a.change_point.mean_before)} / ${num(a.change_point.mean_after)}`], ["Δχ² against one level", num(a.change_point.delta_chi2)]]) : el("p", {}, a.change_point.reason)));
  if (a.dcf) parts.push(card("Discrete correlation function", a.dcf.applicable ? table(["Lag (d)", "Pairs", "DCF", "Error"], a.dcf.bins.map((b) =>
    el("tr", {}, el("td", {}, `${num(b.lag_lo)} – ${num(b.lag_hi)}`), el("td", {}, b.n_pairs), el("td", {}, num(b.dcf)), el("td", {}, num(b.err))))) : el("p", {}, a.dcf.reason)));
  if (a.fourier) parts.push(card("Fourier transform", kv([["Peak frequency", num(a.fourier.peak_frequency)], ["Peak power", num(a.fourier.peak_power)]])));
  if (a.wavelet) parts.push(card("Haar wavelet", table(["Scale (samples)", "Energy", "Coefficients"], a.wavelet.levels.map((l) => el("tr", {}, el("td", {}, l.scale_samples), el("td", {}, num(l.energy)), el("td", {}, l.n))))));
  if (a.model_comparison) {
    const mc = a.model_comparison;
    parts.push(card("Model comparison", table(["Model", "Parameters", "χ²", "Degrees of freedom", "Reduced χ²", "BIC"], mc.models.map((m) =>
      el("tr", {}, el("td", {}, m.model, m.note ? el("div", { class: "faint small" }, m.note) : null), el("td", {}, m.k), el("td", {}, num(m.chi2)), el("td", {}, m.dof), el("td", {}, num(m.reduced_chi2)),
        el("td", {}, m.bic === null ? el("span", { class: "faint" }, "not reported") : num(m.bic)))), { id: "sig-models" }),
      table(["Assumption check", "Value", "Passed"], mc.assumption_checks.map((c) => el("tr", {}, el("td", {}, c.check), el("td", {}, num(c.value)), el("td", {}, c.passed ? "yes" : "no")))),
      el("p", { class: "small", id: "sig-bic-reading" }, mc.reading),
      el("p", { class: "faint small" }, "No single score ranks the models: compare the fit, the residuals, the number of parameters and what each model means physically.")));
  }
  parts.push(el("p", { class: "faint small" }, sg.not_probabilities));
  body.append(...parts.filter(Boolean));
}

// ------------------------------------------------------------------ World Model
let worldTab = "world", wq = { from_kind: "", rel: "", to_kind: "", text: "" };
export function setWorldTab(t) { worldTab = t; }
export function worldQuery(w, q) {
  const kinds = Object.fromEntries(w.nodes.map((n) => [n.id, n.kind]));
  const labels = Object.fromEntries(w.nodes.map((n) => [n.id, n.label || ""]));
  const txt = (q.text || "").trim().toLowerCase();
  return w.edges.filter((e) => (!q.rel || e.rel === q.rel) && (!q.from_kind || (kinds[e.from] ?? e.from.split(":")[0]) === q.from_kind)
    && (!q.to_kind || (kinds[e.to] ?? e.to.split(":")[0]) === q.to_kind)
    && (!txt || `${labels[e.from] ?? e.from} ${labels[e.to] ?? e.to}`.toLowerCase().includes(txt)));
}

export async function renderWorld() {
  const live = renderToken("world");
  const body = clear($("#world-body"));
  if (!state.inv) { needRun(body, "The world model is built from a recorded analysis."); return; }
  const u = await load(body, "world");
  if (!u || !live()) return;
  body.append(syntheticNote(u) || "", tabs("World model views", [["world", "Relationships"], ["convergence", "Convergence"], ["leads", "Research leads"], ["modal", "Multimodal"], ["timeline", "Discovery timeline"]],
    worldTab, "data-world-tab", (t) => { worldTab = t; renderWorld(); }));
  const out = el("div", { id: "world-out" });
  body.append(out);
  if (worldTab === "world") {
    const w = u.world;
    const opt = (id, label, vals, cur) => el("label", {}, label, el("select", { id, "aria-label": label }, el("option", { value: "" }, "any"), ...vals.map((v) => el("option", { value: v, selected: v === cur || null }, v))));
    const f = opt("wq-from", "From", w.kinds, wq.from_kind), r = opt("wq-rel", "Relationship", w.relations, wq.rel), t = opt("wq-to", "To", w.kinds, wq.to_kind);
    const tx = el("input", { type: "search", id: "wq-text", value: wq.text, placeholder: "Text in either end (exact)", "aria-label": "Text in either end" });
    const res = el("div", { id: "wq-results" });
    const run = () => {
      wq = { from_kind: $("#wq-from").value, rel: $("#wq-rel").value, to_kind: $("#wq-to").value, text: tx.value };
      const hits = worldQuery(w, wq);
      clear(res).append(el("p", { class: "muted", id: "wq-count" }, `${hits.length} of ${w.edges.length} relationships`),
        table(["From", "Relationship", "To", "Basis (rule)", "Recorded field"], hits.slice(0, 200).map((e) =>
          el("tr", {}, el("td", { class: "mono small" }, e.from), el("td", {}, e.rel), el("td", { class: "mono small" }, e.to), el("td", { class: "small" }, e.basis.rule), el("td", { class: "mono small" }, e.basis.field)))));
    };
    [f, r, t].forEach((x) => x.querySelector("select").addEventListener("change", run));
    tx.addEventListener("input", run);
    out.append(card("Structured query", el("p", { class: "muted small" }, `${w.nodes.length} objects, ${w.edges.length} relationships. ${w.note}`),
      el("div", { class: "controls wrap" }, f, r, t, tx), res));
    run();
  } else if (worldTab === "convergence") {
    const c = u.convergence;
    out.append(...c.outcomes.map((o) => card(`${o.outcome}: ${o.lines} line(s), ${o.independent_by_exposure} exposure-independent`, el("p", {}, o.reading), el("p", { class: "small muted" }, o.method_dependence),
      o.groups.length ? table(["Group", "Pairs", "Exposures", "Reference stars"], o.groups.map((g, i) => el("tr", {}, el("td", {}, i + 1), el("td", {}, g.pairs.length), el("td", { class: "mono small" }, g.exposures.join(", ")), el("td", { class: "mono small" }, g.reference_stars.join(", "))))) : null)),
      card("Repeated use of the same data", el("p", {}, c.repeated_data.reading)), card("Rules", el("ul", {}, ...c.rules.map((r) => el("li", {}, r)))));
  } else if (worldTab === "leads") {
    const l = u.leads;
    out.append(el("p", { class: "muted" }, l.note), l.leads.length ? table(["Lead", "Kind", "Statement", "Possible resolutions", "Status", "Rule"], l.leads.map((x) =>
      el("tr", { "data-lead": x.id }, el("td", { class: "mono small" }, x.id), el("td", {}, x.kind), el("td", { class: "small" }, x.statement), el("td", { class: "small" }, el("ul", {}, ...x.resolutions.map((r) => el("li", {}, r)))),
        el("td", {}, el("span", { class: "pill out-warn" }, x.status)), el("td", { class: "small" }, x.rule))), { id: "leads-table" }) : el("p", { class: "empty" }, "No contradiction was found by the stated rules."));
  } else if (worldTab === "modal") {
    const m = u.multimodal;
    out.append(card("One representation for every measurement", kv(Object.entries(m.counts).map(([k, v]) => [k, v])), el("p", { class: "small muted" }, `Fields: ${m.fields.join(", ")}.`)),
      card("Which cross-modal comparisons are compatible", table(["A", "B", "Compatible when", "What is compared"], m.compatibility.map((r) => el("tr", {}, el("td", {}, r.a), el("td", {}, r.b), el("td", { class: "small" }, r.compatible), el("td", { class: "small" }, r.comparison))))),
      card(`Rows (${Math.min(60, m.rows.length)} of ${m.n_rows})`, table(["Modality", "Quantity", "Unit", "MJD", "λ (µm)", "Detector", "Value", "Error", "Source"], m.rows.slice(0, 60).map((r) =>
        el("tr", {}, el("td", {}, r.modality), el("td", { class: "small" }, r.quantity), el("td", {}, r.unit), el("td", {}, num(r.time_mjd, 8)), el("td", {}, num(r.wavelength_um, 4)), el("td", {}, r.detector),
          el("td", {}, Array.isArray(r.value) ? r.value.map((v) => num(v)).join(", ") : num(r.value)), el("td", {}, num(r.error)), el("td", { class: "mono small" }, r.source))))));
  } else {
    const tl = u.timeline;
    out.append(el("p", { class: "muted" }, tl.note), ...tl.lanes.map((ln) => card(`${ln.lane[0].toUpperCase()}${ln.lane.slice(1)} time`, el("p", { class: "small muted" }, ln.meaning),
      ln.state ? el("p", { class: "banner small" }, ln.state) : null,
      ln.items.length ? (ln.lane === "observation" ? laneChart(ln.items) : null) : null,
      ln.items.length ? table(["Time (UTC)", "Reference"], ln.items.slice(0, 80).map((i) => el("tr", {}, el("td", { class: "mono small" }, i.time || "not recorded"), el("td", { class: "small" }, i.ref)))) : null)));
  }
}

function laneChart(items) {
  const ts = items.map((i) => i.mjd).filter((x) => x != null);
  return scatter({ height: 120, xLabel: "MJD", yLabel: "", series: [{ points: ts.map((x) => ({ x, y: 0 })), color: "#8fb3ff" }], xfmt: (v) => num(v, 6), yfmt: () => "", title: "Observation times" });
}

// ------------------------------------------------------------------ Negative space: nine distinctions (in the Negative Space workspace)
export async function negativeNine(container) {
  const holder = el("section", { class: "card", id: "negx" }, el("h3", {}, "Nine distinctions of absence (NEGX-1)"));
  container.append(holder);
  let u;
  try { u = await getUniversal(); } catch (e) { holder.append(el("p", { class: "empty" }, e.message)); return; }
  if (!u) return;
  const n = u.negative;
  let pick = "all";
  const sel = el("select", { id: "negx-dist", "aria-label": "Distinction" }, el("option", { value: "all" }, "all distinctions"), ...n.distinctions.map((d) => el("option", { value: d }, `${d} (${n.counts[d]})`)));
  const out = el("div");
  const draw = () => {
    const list = n.items.filter((x) => pick === "all" || x.distinction === pick);
    clear(out).append(table(["Distinction", "Statement", "What it does not mean", "Source"], list.slice(0, 150).map((x) =>
      el("tr", { "data-negx": x.distinction }, el("td", {}, x.distinction), el("td", { class: "small wrap" }, x.statement), el("td", { class: "small" }, x.does_not_mean), el("td", { class: "mono small" }, x.source)))));
  };
  sel.addEventListener("change", () => { pick = sel.value; draw(); });
  holder.append(el("p", { class: "muted small" }, n.note), el("div", { class: "controls" }, sel), out);
  draw();
}

// ------------------------------------------------------------------ Knowledge compiler statuses (in the Scientific Compiler)
export async function compilerStatuses(container) {
  const holder = el("section", { class: "card", id: "kcomp" }, el("h3", {}, "Knowledge compiler status by stage (KCOMP-1)"));
  container.append(holder);
  let u;
  try { u = await getUniversal(); } catch (e) { holder.append(el("p", { class: "empty" }, e.message)); return; }
  const k = u.compiler, cls = { Passed: "out-ok", "Passed with warnings": "out-warn", Incomplete: "out-warn", Failed: "out-bad", "Not evaluated": "faint" };
  holder.append(table(["Stage", "Status", "Pass", "Warning", "Fail"], k.stages.map((s) => el("tr", { "data-kcomp": s.id }, el("td", {}, s.name), el("td", {}, el("span", { class: `pill ${cls[s.status]}` }, s.status)),
    el("td", {}, s.counts.pass ?? 0), el("td", {}, s.counts.warning ?? 0), el("td", {}, s.counts.fail ?? 0)))),
  el("p", { class: "small" }, k.meaning), el("p", { class: "faint small" }, k.rule));
}

// ------------------------------------------------------------------ Radar additions: novelty scope and external sources
export async function radarExtras(outer) {
  const container = el("div", { id: "radar-extras" });
  outer.append(container);
  let u;
  try { u = await getUniversal(); } catch (e) { container.append(el("p", { class: "empty" }, e.message)); return; }
  const o = u.opportunities, src = u.sources;
  const watched = new Set((state.session?.monitors || []).map((m) => m.source));
  container.append(card("Novelty scope of each opportunity (OPP-2)", el("p", { class: "muted small" }, o.note),
    table(["Opportunity", "Feasibility", "Novelty scope", "Indexed sources", "Independent verification"], o.items.slice(0, 40).map((i) =>
      el("tr", { "data-opp": i.id }, el("td", { class: "small" }, i.question), el("td", {}, i.feasibility), el("td", {}, el("span", { class: "pill" }, i.novelty.scope), el("div", { class: "faint small" }, i.novelty.rule)),
        el("td", { class: "small" }, i.novelty.underexplored_in_indexed_sources), el("td", { class: "small" }, i.novelty.independently_verified))), { id: "opp-novelty" })),
  card("External sources (EXTSRC-1)", el("p", { class: "muted small" }, src.note),
    table(["Source", "Kind", "Provider", "State", "Why", "Interest"], src.sources.map((s) => {
      const b = el("button", { class: "btn small", type: "button", "data-watch": s.id }, watched.has(s.id) ? "Interested" : "Note interest");
      b.addEventListener("click", async () => {
        await S.update("monitor.interest", `Interest noted in ${s.name} (not connected; nothing is contacted)`, (x) => {
          x.monitors = [...(x.monitors || []).filter((m) => m.source !== s.id), { source: s.id, at: nowIso(), state: "not connected" }].slice(-50); return x;
        });
        b.textContent = "Interested";
      });
      return el("tr", { "data-source": s.id }, el("td", {}, s.name), el("td", {}, s.kind), el("td", { class: "small" }, s.provider), el("td", {}, el("span", { class: "pill faint" }, s.state)), el("td", { class: "small" }, s.why), el("td", {}, b));
    }), { id: "ext-sources" })));
}

// ------------------------------------------------------------------ Investigation director (in the Research Autopilot)
export async function directorCard(container) {
  const holder = el("section", { class: "card", id: "director" }, el("h3", {}, "Investigation Director (DIRECT-1)"));
  container.prepend(holder);
  if (!state.inv) { holder.append(el("p", { class: "muted" }, "Run an analysis first.")); return; }
  let u;
  try { u = await getUniversal(); } catch (e) { holder.append(el("p", { class: "empty" }, e.message)); return; }
  const plan = u.director;
  const runs = (state.session?.director || []).filter((r) => r.content_hash === u.content_hash);
  const cur = runs[runs.length - 1];
  const start = el("button", { class: "btn", type: "button", id: "dir-start" }, cur ? "Start a new director run" : "Start a director run");
  start.addEventListener("click", async () => {
    await S.update("director.start", `Director run started (${plan.steps.length} proposed steps)`, (s) => {
      const r = { id: rid(4), content_hash: u.content_hash, started_at: nowIso(), steps: plan.steps.map((x) => ({ id: x.id, action: x.action, workspace: x.workspace, status: "proposed" })),
        log: [{ at: nowIso(), event: "proposed", step: null, note: `${plan.steps.length} steps` }] };
      s.director = [...(s.director || []), r].slice(-20); return s;
    }, null);
    directorRefresh(container);
  });
  const act = async (stepId, event) => {
    await S.update(`director.${event}`, `Director step ${stepId} ${event}`, (s) => {
      const r = s.director[s.director.length - 1];
      const st = r.steps.find((x) => x.id === stepId);
      st.status = event === "approve" ? "approved" : event === "execute" ? "executed" : "declined";
      r.log.push({ at: nowIso(), event, step: stepId });
      return s;
    }, stepId);
    if (event === "execute") { const st = plan.steps.find((x) => x.id === stepId); emit("goto", { ws: st.workspace }); return; }
    directorRefresh(container);
  };
  holder.append(el("ul", { class: "small muted" }, ...plan.rules.map((r) => el("li", {}, r))), el("div", { class: "controls" }, start),
    table(["Step", "Action", "Reason", "Status", ""], plan.steps.map((x) => {
      const st = cur?.steps.find((y) => y.id === x.id)?.status || "not started";
      const ap = el("button", { class: "btn small", type: "button", "data-dir-approve": x.id, disabled: !cur || st !== "proposed" || null }, "Approve");
      const ex = el("button", { class: "btn small", type: "button", "data-dir-execute": x.id, disabled: !cur || st !== "approved" || null }, "Open the result");
      const de = el("button", { class: "btn small ghost", type: "button", "data-dir-decline": x.id, disabled: !cur || st !== "proposed" || null }, "Decline");
      ap.addEventListener("click", () => act(x.id, "approve")); ex.addEventListener("click", () => act(x.id, "execute")); de.addEventListener("click", () => act(x.id, "decline"));
      return el("tr", { "data-dir-step": x.id }, el("td", { class: "mono small" }, x.id), el("td", {}, x.action), el("td", { class: "small" }, x.reason), el("td", {}, el("span", { class: "pill" }, st)), el("td", {}, ap, ex, de));
    }), { id: "dir-steps" }),
    cur ? el("details", { open: true }, el("summary", {}, `Audit log of run ${cur.id} (${cur.log.length} entries)`),
      table(["Time (UTC)", "Event", "Step"], cur.log.map((l) => el("tr", {}, el("td", { class: "mono small" }, l.at), el("td", {}, l.event), el("td", { class: "mono small" }, l.step || "—"))), { id: "dir-log" })) : null);
}
function directorRefresh(container) { container.querySelector("#director")?.remove(); directorCard(container); }

// ------------------------------------------------------------------ Role agents (in Review & Story)
export async function agentsCard(container) {
  const holder = el("section", { class: "card", id: "agents" }, el("h3", {}, "Role agents and their debate (AGENTS-1)"));
  container.append(holder);
  let u;
  try { u = await getUniversal(); } catch (e) { holder.append(el("p", { class: "empty" }, e.message)); return; }
  const a = u.agents, names = Object.fromEntries(a.roles.map((r) => [r.id, r.name]));
  const rec = el("button", { class: "btn small", type: "button", id: "agents-record" }, "Record this debate in the session");
  rec.addEventListener("click", async () => {
    await S.update("debate.record", `Role-agent debate recorded (${a.rounds.length} rounds)`, (s) => {
      s.debates = [...(s.debates || []), { at: nowIso(), content_hash: u.content_hash, method: a.method, rounds: a.rounds.map((r) => ({ question: r.question, n: r.messages.length, close: r.close })) }].slice(-20); return s;
    });
    toast("Debate recorded in the session");
  });
  holder.append(el("p", { class: "banner warn small" }, a.caveat),
    ...a.rounds.map((r) => el("div", { class: "debate", "data-round": r.question }, el("h4", {}, r.question),
      el("ol", {}, ...r.messages.map((m) => el("li", {}, el("strong", {}, `${names[m.agent]} · ${m.kind}: `), el("span", { lang: "en" }, m.text), el("span", { class: "faint mono small" }, `  [${m.cites.join(", ")}]`)))),
      el("p", { class: "small" }, el("strong", {}, "Close: "), r.close), el("p", { class: "faint small" }, r.close_rule))),
    el("div", { class: "controls" }, rec));
}

// ------------------------------------------------------------------ Experiment marketplace (in the Experiment Studio)
export async function marketCard(container) {
  const holder = el("section", { class: "card", id: "market" }, el("h3", {}, "Experiment marketplace (EXPMKT-1)"));
  container.append(holder);
  let u = null;
  try { u = await getUniversal(); } catch { u = null; }
  const m = u?.market;
  if (!m) { holder.append(el("p", { class: "muted" }, "Run an analysis to list the methods and templates with their validation status.")); return; }
  holder.append(el("p", { class: "muted small" }, m.rule), table(["Item", "Kind", "Validation", "Evidence", ""], m.items.map((i) =>
    el("tr", { "data-market": i.id }, el("td", {}, i.name, i.recommended ? el("span", { class: "pill out-ok" }, "recommended") : el("span", { class: "pill faint" }, "not recommended")),
      el("td", {}, i.kind), el("td", { class: "small" }, i.status), el("td", { class: "mono small" }, i.evidence || "—"),
      el("td", {}, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: i.action }) }, "Open")))), { id: "market-table" }));
}

// ------------------------------------------------------------------ Open Science Gateway
let gwTab = "handoff", replayAt = null, replayTimer = null;
export async function renderGateway() {
  const live = renderToken("gateway");
  const body = clear($("#gateway-body"));
  body.append(tabs("Gateway", [["handoff", "Discovery handoff"], ["recorder", "Flight recorder"], ["bundle", "Open-science bundle"], ["reports", "Reports in six languages"]],
    gwTab, "data-gw-tab", (t) => { gwTab = t; renderGateway(); }));
  const out = el("div", { id: "gw-out" });
  body.append(out);
  if (gwTab === "recorder") { recorder(out); return; }
  if (gwTab === "handoff") { await handoffPanel(out, live); return; }
  if (gwTab === "bundle") { await bundlePanel(out, live); return; }
  reportsPanel(out);
}

async function currentHandoff() {
  const u = await getUniversal();
  return buildHandoff(state.inv.record, u, getLang(), getMeta(), nowIso(), VERSION);
}

async function handoffPanel(out, live) {
  const exp = el("button", { class: "btn", type: "button", id: "ho-export", disabled: !state.inv || null }, "Export handoff (JSON)");
  exp.addEventListener("click", async () => {
    const h = await currentHandoff();
    if (await download(`skytrace-handoff-${h.investigation.content_hash.slice(0, 12)}.json`, JSON.stringify(h, null, 1), "application/json")) {
      await S.update("handoff.export", `Handoff exported (${h.digest.slice(0, 12)}…)`, (s) => { s.handoffs = [...(s.handoffs || []), { at: h.created_at, direction: "export", digest: h.digest, content_hash: h.investigation.content_hash, language: h.language.interface }].slice(-30); return s; });
      toast("Handoff exported");
    }
  });
  const file = el("input", { type: "file", id: "ho-file", accept: "application/json,.json", "aria-label": "Handoff file to check" });
  const res = el("div", { id: "ho-result" });
  file.addEventListener("change", async () => {
    clear(res);
    const f = file.files?.[0];
    if (!f) return;
    if (f.size > 2_000_000) { res.append(el("p", { class: "banner bad" }, "The file is larger than 2 MB; a handoff is much smaller.")); return; }
    let doc;
    const text = await f.text();
    file.value = "";                                   // choosing the same file again (after editing it) checks it again
    try { doc = JSON.parse(text); } catch { res.append(el("p", { class: "banner bad" }, "the file is not JSON")); return; }
    const errs = await validateHandoff(doc);
    if (errs.length) { res.append(el("div", { class: "banner bad", id: "ho-invalid" }, el("strong", {}, "Not accepted. "), el("ul", {}, ...errs.map((e) => el("li", {}, e))))); return; }
    await S.update("handoff.import", `Handoff checked (${doc.digest.slice(0, 12)}…)`, (s) => { s.handoffs = [...(s.handoffs || []), { at: nowIso(), direction: "import", digest: doc.digest, content_hash: doc.investigation.content_hash, language: doc.language.interface }].slice(-30); return s; });
    res.append(el("p", { class: "banner ok", id: "ho-valid" }, "Valid handoff. It describes recorded work; importing it is not a reproduction."),
      kv([["Target", doc.investigation.target], ["Record", doc.investigation.content_hash], ["Synthetic", doc.investigation.synthetic ? "yes" : "no"],
        ["Prepared in", `${doc.language.interface} (content in ${doc.language.content}; ${doc.language.translation.status})`], ["Established", doc.established.length], ["Open", doc.open.length], ["Unknown", doc.unknown.length]]),
      table(["Question", "Outcome", "Statement"], doc.established.map((e) => el("tr", {}, el("td", {}, e.question), el("td", {}, e.category), el("td", { class: "small", lang: "en" }, e.statement)))));
  });
  out.append(card("Discovery handoff protocol (HANDOFF-1)",
    el("p", { class: "muted" }, "A versioned JSON document (skytrace.handoff/1) for the next researcher: what was established, what is open, what is unknown, the evidence that would help, provenance, limitations and how to reproduce — with the interface language, the content language and the translation status. Its digest lets the receiver detect any edit."),
    el("div", { class: "controls" }, exp), el("h4", {}, "Check a handoff you received"), el("div", { class: "controls" }, file), res,
    el("p", { class: "faint small" }, "Checking is local: the file is read in this browser and nothing is uploaded.")));
  const hist = state.session?.handoffs || [];
  if (hist.length) out.append(card("Handoffs in this session", table(["Time (UTC)", "Direction", "Digest", "Record", "Language"], hist.slice().reverse().map((h) =>
    el("tr", {}, el("td", { class: "mono small" }, h.at), el("td", {}, h.direction), el("td", { class: "mono small" }, `${h.digest.slice(0, 16)}…`), el("td", { class: "mono small" }, `${String(h.content_hash).slice(0, 16)}…`), el("td", {}, h.language))))));
  void live;
}

async function recorder(out) {
  const s = state.session;
  if (!s) { out.append(el("p", { class: "empty" }, "No research session yet: the flight recorder replays a session's history.")); return; }
  const h = s.history || [];
  const v = await verifyChain(h);
  if (replayAt === null || replayAt > h.length) replayAt = h.length;
  const slider = el("input", { type: "range", min: "1", max: String(h.length), value: String(replayAt), id: "fr-slider", "aria-label": "Replay position" });
  const view = el("div", { id: "fr-view" });
  const play = el("button", { class: "btn small", type: "button", id: "fr-play" }, "Play");
  const draw = () => {
    const upto = h.slice(0, replayAt);
    const e = upto[upto.length - 1];
    const counts = {};
    for (const x of upto) { const k = x.kind.split(".")[0]; counts[k] = (counts[k] || 0) + 1; }
    clear(view).append(el("p", {}, el("strong", {}, `Event ${replayAt} of ${h.length}: `), `${e?.kind} — ${e?.summary}`, el("span", { class: "faint mono small" }, `  ${e?.at || ""}${e?.h ? "  link " + e.h.slice(0, 12) + "…" : ""}`)),
      table(["Kind of activity", "Events up to here"], Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => el("tr", {}, el("td", {}, k), el("td", {}, n)))),
      el("ol", { class: "small", start: String(Math.max(1, replayAt - 9)) }, ...upto.slice(-10).map((x) => el("li", {}, `${x.kind}: ${x.summary}`))));
  };
  slider.addEventListener("input", () => { replayAt = +slider.value; draw(); });
  play.addEventListener("click", () => {
    if (replayTimer) { clearInterval(replayTimer); replayTimer = null; play.textContent = "Play"; return; }
    if (replayAt >= h.length) replayAt = 1;
    play.textContent = "Pause";
    replayTimer = setInterval(() => {
      if (!document.body.contains(slider) || replayAt >= h.length) { clearInterval(replayTimer); replayTimer = null; play.textContent = "Play"; return; }
      replayAt++; slider.value = String(replayAt); draw();
    }, 600);
  });
  out.append(card("Research flight recorder (FLIGHT-1)",
    el("p", { class: "muted" }, "Replays this session's append-only history event by event. Entries are linked by a SHA-256 hash chain (VAULT-1), so an edited or removed entry is detectable. This is tamper-evident, not cryptographic immutability: there is no signature and no external anchor, and whoever holds the file can rewrite the whole chain."),
    kv([["Events", h.length], ["Chain links verified", `${v.verified} of ${v.links}`], ["Broken links", v.broken.length], ["Older unchained entries", v.unchained]]),
    el("div", { class: "controls" }, play, slider), view));
  draw();
}

async function bundlePanel(out) {
  if (!state.inv) { needRun(out, "The bundle packages a recorded analysis."); return; }
  const u = await getUniversal();
  const rec = state.inv.record;
  const prov = rec.events.flatMap((e) => e.provenance || []);
  const synthetic = prov.some((p) => p.origin === "synthetic");
  const checks = [
    ["Identified by a content hash", !!rec.content_hash, rec.content_hash?.slice(0, 16) + "…"],
    ["Every file has a checksum", prov.every((p) => p.content_sha256), `${prov.filter((p) => p.content_sha256).length} of ${prov.length}`],
    ["Archive sources have URLs", prov.filter((p) => p.origin === "archive").every((p) => p.source_url), synthetic ? "synthetic data: no archive URL by construction" : ""],
    ["Synthetic data labelled", !synthetic || !!u.synthetic, synthetic ? "SYNTHETIC label carried in every file" : "not synthetic"],
    ["Limitations stated", (rec.events.find((e) => e.step === "assess")?.data?.outcomes || []).every((o) => (o.limitations || []).length), ""],
    ["Machine-readable handoff", true, "skytrace.handoff/1"],
    ["Software licence declared", false, "this repository declares no licence: choose one before publishing"],
  ];
  const dl = el("button", { class: "btn", type: "button", id: "osg-download" }, "Download the bundle (ZIP)");
  dl.addEventListener("click", async () => {
    const h = await currentHandoff();
    const lang = getLang();
    const enReport = await api.report(state.inv.investigation_id, "en");
    const files = [["README.md", [`# Skytrace open-science bundle — ${rec.target}`, "", synthetic ? "**SYNTHETIC test data.** Nothing here is an astronomical result." : "", "",
      `Record ${rec.content_hash}; Skytrace ${VERSION}; prepared ${h.created_at} in interface language ${lang}.`, "",
      "Files: record.json (the investigation record), report.en.md (English), " + (lang !== "en" ? `report.${lang}.md (interface language; machine-translated wording), ` : "") + "handoff.json (skytrace.handoff/1), checklist.json.",
      "", "Nothing in this bundle was published by Skytrace. Publishing it is your decision and needs a licence and the data providers' terms."].join("\n")],
      ["record.json", await api.recordText(state.inv.investigation_id)], ["report.en.md", enReport], ["handoff.json", JSON.stringify(h, null, 1)],
      ["checklist.json", JSON.stringify({ method: "OSG-1", checks: checks.map(([k, ok, note]) => ({ check: k, passed: ok, note })) }, null, 1)]];
    if (lang !== "en") files.splice(3, 0, [`report.${lang}.md`, STATIC ? localizeExport(enReport, "text/markdown") : await api.report(state.inv.investigation_id, lang)]);
    if (await download(`skytrace-open-science-${rec.content_hash.slice(0, 12)}.zip`, zipStore(files), "application/zip")) {
      await S.log("gateway.bundle", `Open-science bundle downloaded (${files.length} files)`, rec.content_hash, { create: true });
      toast("Bundle downloaded");
    }
  });
  out.append(card("Open Science Gateway (OSG-1)", el("p", { class: "muted" }, "Prepares what is needed to share an investigation openly: the record, the report in English and in your interface language, the handoff and a checklist. Nothing is published, uploaded or sent: the bundle is downloaded to your computer, and publishing it is your decision."),
    table(["Check", "Passed", "Note"], checks.map(([k, ok, note]) => el("tr", {}, el("td", {}, k), el("td", {}, el("span", { class: `pill ${ok ? "out-ok" : "out-warn"}` }, ok ? "yes" : "no")), el("td", { class: "small" }, note))), { id: "osg-checks" }),
    el("div", { class: "controls" }, dl)));
}

function reportsPanel(out) {
  if (!state.inv) { needRun(out, "Reports are written from a recorded analysis."); return; }
  const iid = state.inv.investigation_id;
  const btns = languages().map((l) => {
    const b = el("button", { class: "btn small", type: "button", "data-report-lang": l.code, lang: l.code, translate: "no" }, `${l.name} (.${l.code}.md)`);
    b.addEventListener("click", async () => {
      const prev = getLang();
      let text;
      if (l.code === "en") text = await api.report(iid, "en");
      else if (!STATIC) text = await api.report(iid, l.code);
      else { await setLang(l.code, { persist: false }); try { text = localizeExport(await api.report(iid, "en"), "text/markdown"); } finally { await setLang(prev, { persist: false }); } }
      const base = `skytrace-${state.inv.record.target.replace(/\W+/g, "-")}-${iid}`;
      if (await download(`${base}-report.${l.code}.md`, text, "text/markdown", { raw: true })) toast("Report downloaded");
    });
    return b;
  });
  out.append(card("Reports in six languages", el("p", { class: "muted" }, "The same report in each interface language. The report's wording is translated; every number, identifier, unit, method name and engine statement is written unchanged, and each translated report begins with its language and translation status."),
    el("div", { class: "controls wrap", id: "report-langs" }, ...btns),
    el("p", { class: "faint small" }, STATIC ? "In this preview the translation is applied in your browser with the same dictionaries the server uses." : "Written by the server (I18N-1).")));
}
