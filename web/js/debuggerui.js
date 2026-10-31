// Scientific Debugger (SCIDEBUG-1) and the Reproduction Arena (REPROX-1).
// Breakpoints are the stages the record contains; a selected result shows its computation, recorded inputs and a
// recomputation from recorded values where the record determines it. Differential debugging compares two runs stage by
// stage in the browser (epistemiccore.diff, parity-tested). Reproduction re-executes the run on the server.

import { api, STATIC } from "./api.js";
import { state } from "./state.js";
import { diff } from "./epistemiccore.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, num, outcomePill, syntheticNote, table, tabs } from "./epiui.js";

let tab = "inspect", bp = "statistics", result = null, runA = null, runB = null, lastDiff = null, lastRepro = null, busy = false;
export function setDebuggerTab(t) { tab = t; }

export async function renderDebugger() {
  const live = renderToken("debugger");
  const body = $("#debugger-body");
  clear(body);
  if (!state.inv) { needRun(body, "The debugger inspects a recorded analysis."); return; }
  const d = await loadEpistemic(body, "debugger");
  if (!d || !live()) return;
  body.append(syntheticNote(d), tabs("Debugger", [["inspect", "Breakpoints and results"], ["diff", "Differential debugging"], ["repro", "Reproduce"]], tab, "data-dtab",
    (k) => { tab = k; renderDebugger(); }));
  if (tab === "inspect") body.append(inspectView(d));
  else if (tab === "diff") body.append(await diffView());
  else body.append(reproView());
}

const RESULTS_AT = { statistics: (d) => ["fit:motion", ...Object.keys(d.inspect).filter((k) => k.startsWith("epoch:")), ...Object.keys(d.inspect).filter((k) => k.startsWith("pair:"))],
  assessment: (d) => d.graph.claims, measurement: (d) => d.graph.nodes.filter((n) => n.kind === "measurement").map((n) => n.id) };

function inspectView(d) {
  const bps = el("ol", { class: "compile-stages", "aria-label": "Breakpoints" }, ...d.breakpoints.map((b) => {
    const btn = el("button", { type: "button", class: `stage-btn${bp === b.id ? " current" : ""}`, "data-bp": b.id, "aria-pressed": String(bp === b.id) },
      el("span", {}, b.name), el("span", { class: "faint small" }, `${b.n_events} event(s) · ${b.steps.join(", ")}`));
    btn.addEventListener("click", () => { bp = b.id; result = null; renderDebugger(); });
    return el("li", {}, btn);
  }));
  const readers = el("p", { class: "faint small" }, "Not execution stages of the pipeline, so no breakpoint: hypothesis evaluation (HYPO-1) and report generation, both computed from the record on demand.");
  const bpo = d.breakpoints.find((b) => b.id === bp) || d.breakpoints[0];
  const ids = (RESULTS_AT[bpo.id] || (() => []))(d);
  let panel;
  if (!ids.length) {
    panel = el("div", { class: "card" }, el("h3", {}, bpo.name), kv([["Recorded steps", bpo.steps.join(", ")], ["Events", String(bpo.n_events)],
      ["Statuses", Object.entries(bpo.status_counts).map(([k, v]) => `${v} ${k}`).join(", ")]]),
      el("p", { class: "faint small" }, "This stage records its decisions but no separate result to recompute; inspect its events in the Discovery Lab's step log or trace them in the reasoning graph."));
  } else {
    if (!result || !ids.includes(result)) result = ids[0];
    const sel = el("select", { id: "dbg-result", "aria-label": "Result" }, ...ids.slice(0, 120).map((r) => el("option", { value: r, selected: r === result || null }, r.length > 90 ? r.slice(0, 90) + "…" : r)));
    sel.addEventListener("change", () => { result = sel.value; renderDebugger(); });
    panel = el("div", { class: "card", id: "dbg-panel" }, el("div", { class: "controls" }, el("label", { for: "dbg-result" }, "Result"), sel), resultView(d, result));
  }
  return el("div", {}, el("div", { class: "card" }, bps, readers), panel);
}

function resultView(d, rid) {
  let X = d.inspect[rid];
  if (!X && rid.startsWith("meas:")) X = measInspect(rid);
  if (!X) return el("p", { class: "empty" }, "No recorded computation for this result.");
  if (X.error) return el("p", { class: "withheld" }, X.error);
  return el("div", {}, el("h3", {}, rid), kv([["Method", X.method], ["Formula", X.formula], ["Stage", X.stage], ["Record event", X.event ?? "—"],
    ["Parameters", Object.entries(X.parameters || {}).map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(", ") || "—"],
    ["Verdict", el("strong", { id: "dbg-verdict" }, X.verdict)], X.missing_dependencies?.length ? ["Missing dependencies", X.missing_dependencies.join(", ")] : null,
    X.inconsistent_values?.length ? ["Inconsistent values", X.inconsistent_values.join(", ")] : null, X.note ? ["Note", X.note] : null]),
    X.inputs?.length ? el("details", { open: "" }, el("summary", {}, `Inputs (${X.inputs.length})`), table(Object.keys(X.inputs[0]), X.inputs.map((i) => el("tr", {}, ...Object.values(i).map((v) => el("td", { class: "small" }, typeof v === "number" ? num(v, 6) : String(v ?? "—"))))))) : null,
    X.recomputed?.length ? table(["Quantity", "Recomputed", "Recorded", "Agreement"], X.recomputed.map((r) => el("tr", {}, el("th", { scope: "row" }, r.quantity),
      el("td", {}, typeof r.recomputed === "number" ? String(r.recomputed) : String(r.recomputed ?? "—").slice(0, 80)), el("td", {}, typeof r.recorded === "number" ? String(r.recorded) : String(r.recorded ?? "—").slice(0, 80)),
      el("td", {}, outcomePill(r.agreement === "identical" ? "pass" : r.agreement === "different" ? "fail" : r.agreement === "not computable" ? "not tested" : "warning"), " ", r.agreement))), { id: "dbg-recomputed" }) : null,
    X.intermediate ? el("details", {}, el("summary", {}, "Recorded intermediate values"), el("pre", { class: "wrap small" }, JSON.stringify(X.intermediate, null, 1))) : null,
    X.calibrated ? el("details", {}, el("summary", {}, "Calibrated comparison (PAIRDIFF-2)"), el("pre", { class: "wrap small" }, JSON.stringify(X.calibrated, null, 1))) : null);
}

function measInspect(rid) {
  const key = rid.slice(5);
  const ev = state.inv.record.events.findIndex((e) => e.step === "measure" && e.data?.obs_id === key);
  if (ev < 0) return { error: "no such measurement" };
  const e = state.inv.record.events[ev];
  return { result: rid, stage: "measurement", event: ev, method: `${e.data.centroid?.method} + ${e.data.photometry?.method}`, formula: "centroid: 2-D Gaussian fit; flux: Σ w (I − sky) Ω_pix",
    parameters: { aperture_radius_px: state.inv.record.parameters.aperture_radius_px, fit_half_size_px: state.inv.record.parameters.fit_half_size_px },
    inputs: [{ id: `file:${key}`, sha256: e.provenance?.[0]?.content_sha256 }], intermediate: { centroid: e.data.centroid, photometry: e.data.photometry, quality: e.data.quality },
    note: "the pixel stamp is not stored in the record; re-measuring needs a replay of the pipeline on the file (Reproduce)", verdict: "not recomputable from the record alone" };
}

async function candidateRuns() {
  const cur = { iid: state.inv.investigation_id, label: "current run", content_hash: state.inv.record.content_hash };
  let list = [];
  try { list = (await api.presetRuns(state.targetId)) || []; } catch { list = []; }
  if (!list.length) list = (state.session?.runs || []).map((r) => ({ iid: r.investigation_id, label: r.label || r.investigation_id, content_hash: r.content_hash }));
  const seen = new Set();
  return [cur, ...list].filter((r) => r.iid && !seen.has(r.iid) && seen.add(r.iid));
}

async function recordOf(iid) {
  if (iid === state.inv.investigation_id) return state.inv.record;
  const r = await api.investigation(iid);
  return r.record || r;
}

async function diffView() {
  const runs = await candidateRuns();
  if (runs.length < 2) return el("div", { class: "card" }, el("p", { class: "empty" }, "Differential debugging needs two runs of this target. Re-run the analysis with different parameters (Discovery Lab) — or, in the preview, choose another recorded parameter set — then come back."));
  runA = runs.find((r) => r.iid === runA)?.iid || runs[0].iid;
  runB = runs.find((r) => r.iid === runB && r.iid !== runA)?.iid || runs.find((r) => r.iid !== runA).iid;
  const mk = (id, v) => { const s = el("select", { id, "aria-label": id }, ...runs.map((r) => el("option", { value: r.iid, selected: r.iid === v || null }, `${r.label} · ${String(r.content_hash || "").slice(0, 8)}`))); return s; };
  const sa = mk("diff-a", runA), sb = mk("diff-b", runB);
  const go = el("button", { class: "btn primary", type: "button", id: "diff-run" }, "Compare stage by stage");
  const out = el("div", { id: "diff-out" }, lastDiff ? diffResult(lastDiff) : null);
  go.addEventListener("click", async () => {
    runA = sa.value; runB = sb.value;
    if (runA === runB) { toast("Choose two different runs"); return; }
    clear(out).append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Comparing the two records…"));
    try {
      lastDiff = diff(await recordOf(runA), await recordOf(runB));
      await S.update("debug.diff", `Differential debugging: earliest divergence ${lastDiff.earliest_divergence || "none"}`, (s) => {
        s.debug = [...(s.debug || []), { kind: "diff", a: lastDiff.a, b: lastDiff.b, earliest: lastDiff.earliest_divergence, at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-50);
        return s;
      });
      clear(out).append(diffResult(lastDiff));
    } catch (e) { clear(out).append(el("p", { class: "withheld" }, e.message)); }
  });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, "Compare two runs of the same target. The comparison walks the pipeline stages in order and reports the earliest stage whose recorded values differ, with the input, version, parameter and metadata differences that could explain it."),
    el("div", { class: "controls" }, el("label", { for: "diff-a" }, "Run A"), sa, el("label", { for: "diff-b" }, "Run B"), sb, go)), out);
}

function diffResult(D) {
  const exp = el("button", { class: "btn small", type: "button" }, "Export comparison (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-run-diff.json", JSON.stringify(D, null, 1), "application/json")) toast("Comparison exported"); });
  return el("div", { class: "card" }, el("h3", { id: "diff-earliest" }, D.earliest_divergence ? `Earliest divergence: ${D.earliest_divergence}` : "No stage differs"),
    el("p", {}, D.explanation.join("; ") || "identical records"),
    table(["Stage", "Comparison", "Numeric differences", "Max relative", "Structural / other", "Example"], D.stages.map((s) => el("tr", { "data-dstage": s.id, class: s.id === D.earliest_divergence ? "sel" : "" },
      el("th", { scope: "row" }, s.name), el("td", {}, outcomePill(s.kind === "identical" ? "pass" : s.kind === "different" ? "fail" : "warning"), " ", s.kind), el("td", {}, String(s.numeric)),
      el("td", {}, s.max_rel ? s.max_rel.toExponential(2) : "0"), el("td", {}, `${s.structural} / ${s.other}`),
      el("td", { class: "small mono wrap" }, s.differences[0] ? `${s.differences[0].path}: ${s.differences[0].a} → ${s.differences[0].b}` : "—"))), { id: "diff-table" }),
    kv([["Parameters", D.parameters.map((p) => `${p.key}: ${JSON.stringify(p.a)} → ${JSON.stringify(p.b)}`).join("; ") || "same"], ["Methods", D.methods.map((m) => `${m.role}: ${m.a} → ${m.b}`).join("; ") || "same"],
      ["Software", D.software.map((m) => `${m.package}: ${m.a} → ${m.b}`).join("; ") || "same"], ["Inputs", D.inputs.same ? `same bundle manifest (${String(D.inputs.manifest_a).slice(0, 12)}…)` : "different bundle manifests"]]),
    el("div", { class: "controls" }, exp));
}

function reproView() {
  const go = el("button", { class: "btn primary", type: "button", id: "rx-run" }, STATIC ? "Show the reproduction recorded at build time" : "Reproduce this run");
  const out = el("div", { id: "rx-out" }, lastRepro && lastRepro.content_hash === state.inv.record.content_hash ? reproResult(lastRepro) : null);
  go.addEventListener("click", async () => {
    if (busy) return;
    if (!STATIC && !go.dataset.armed) { go.dataset.armed = "1"; go.textContent = "Confirm: re-executes the full pipeline (a few seconds)"; return; }
    busy = true;
    clear(out).append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Restoring parameters and replaying the pipeline…"));
    try {
      lastRepro = await api.reproduceX(state.inv.investigation_id);
      await S.update("debug.reproduce", `Reproduction: ${lastRepro.verdict}`, (s) => {
        s.debug = [...(s.debug || []), { kind: "reproduction", verdict: lastRepro.verdict, content_hash: lastRepro.content_hash, recorded_at_build: !!lastRepro.recorded_at_build,
          at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-50);
        if (!["exact reproduction", "numerically equivalent reproduction"].includes(lastRepro.verdict))
          s.negative = [...(s.negative || []), { id: S.newId("neg"), category: "unsuccessful reproduction", distinction: lastRepro.verdict === "blocked reproduction" ? "data unavailable" : "test failed",
            attempted: "re-execute the run", why: "reproducibility of the claims", happened: `${lastRepro.verdict}: ${lastRepro.why}`.slice(0, 300), inputs: [lastRepro.content_hash],
            failure: lastRepro.verdict === "blocked reproduction" ? "technical" : "scientific", unknown: "whether the recorded values repeat", repeatable: "yes",
            unblock: "see the reproduction report", source: "session:reproduction", origin: "session" }].slice(-200);
        return s;
      }, lastRepro.content_hash);
      clear(out).append(reproResult(lastRepro));
    } catch (e) { clear(out).append(el("p", { class: "withheld" }, e.message)); }
    delete go.dataset.armed; busy = false;
  });
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Independent reproduction"),
    el("p", { class: "muted" }, "Fingerprints the environment, verifies inputs and method versions, restores the recorded parameters, replays the pipeline and compares every stage. Importing a record never counts as reproducing it."),
    el("div", { class: "controls" }, go)), out);
}

function reproResult(R) {
  const exp = el("button", { class: "btn small", type: "button", id: "rx-export" }, "Export reproduction report (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-reproduction-${R.content_hash.slice(0, 12)}.json`, JSON.stringify(R, null, 1), "application/json")) toast("Report exported"); });
  return el("div", { class: "card" }, el("h3", { id: "rx-verdict" }, `Verdict: ${R.verdict}`), el("p", {}, R.why),
    R.recorded_at_build ? el("p", { class: "pill" }, "replay recorded when the preview was built") : null,
    el("ol", { class: "plain" }, ...R.steps.map((s) => el("li", {}, outcomePill(s.ok ? "pass" : "warning"), ` ${s.step}: `, el("span", { class: "small" }, s.detail)))),
    R.comparison ? table(["Stage", "Comparison", "Max relative difference"], R.comparison.tolerance.map((t) => el("tr", {}, el("th", { scope: "row" }, t.stage), el("td", {}, t.kind),
      el("td", {}, t.max_rel ? t.max_rel.toExponential(2) : "0")))) : null,
    table(["Package", "Recorded", "Now"], R.environment_comparison.map((r) => el("tr", {}, el("th", { scope: "row" }, r.package), el("td", {}, String(r.recorded)), el("td", {}, String(r.now))))),
    el("p", { class: "faint small" }, `${R.tolerance_rule}. ${R.note}`), el("div", { class: "controls" }, exp));
}
