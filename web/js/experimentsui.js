// Scientific Experiment Studio (EXP-1) and research automation (WF-1).
// Experiments: a definition (question, hypothesis, dataset, method, parameters, baseline, expected output, criterion,
// limitations), executed by the server in bounded runs (or served from the build's recorded results in the static
// preview), evaluated against the stated criterion only. Workflows: declared steps × targets, validated before they run,
// executed step by step through the shared executor with per-item records, cancellation and retry.

import { api, STATIC } from "./api.js";
import { getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { execute, recordExperiment, setHooks } from "./executor.js";
import { nowIso } from "./sessioncore.js";
import { clear, download, el, fmtDate, toast, $ } from "./util.js";

let tab = "experiments", template = "sensitivity", sets = [{ aperture_radius_px: 2.5 }], ncQuestion = "variability", last = null, running = false;
let wfText = null, wfLog = null, cancel = false;
const PARAMS = { aperture_radius_px: [1, 5, 0.1], fit_half_size_px: [3, 8, 1], wavelength_tolerance_channels: [0.1, 1, 0.05], epoch_clip_sigma: [2, 10, 0.5],
                 wavelength_margin_um: [0, 0.01, 0.001], epoch_gap_days: [0.5, 60, 0.5] };
let loadTargetHook = null;
export function setTargetLoader(fn) { loadTargetHook = fn; }

export async function renderExperiments() {
  const body = $("#experiments-body");
  const spec = await getSpecs();
  clear(body);
  body.append(el("div", { class: "tabs", role: "tablist" }, ...[["experiments", "Experiments"], ["workflows", "Workflows (automation)"]].map(([id, l]) => {
    const b = el("button", { role: "tab", "aria-selected": id === tab ? "true" : "false" }, l);
    b.addEventListener("click", () => { tab = id; renderExperiments(); });
    return b;
  })));
  if (tab === "workflows") return renderWorkflows(body, spec);
  const T = spec.experiment_templates;
  const pick = el("div", { class: "qlist", role: "radiogroup", "aria-label": "Experiment template" }, ...Object.entries(T).map(([id, t]) => {
    const b = el("button", { type: "button", role: "radio", "aria-checked": id === template ? "true" : "false", class: "qitem", "data-template": id },
      el("span", { class: "qstatus" }, id.replace("_", " ")), el("span", {}, t.title));
    b.addEventListener("click", () => { template = id; last = null; renderExperiments(); });
    return b;
  }));
  const s = state.session;
  const hyp = el("select", { id: "exp-hyp", "aria-label": "Hypothesis this experiment bears on" }, el("option", { value: "" }, "— none chosen —"),
    ...(s?.hypotheses || []).map((h) => el("option", { value: h.statement }, h.statement.slice(0, 120))));
  const cfg = el("div", { class: "exp-config" });
  if (template === "parameter") {
    sets.forEach((set, i) => {
      const [k, v] = Object.entries(set)[0] || ["aperture_radius_px", 2.5];
      const name = el("select", { "aria-label": `Parameter of set ${i + 1}` }, ...Object.keys(PARAMS).map((p) => el("option", { value: p, selected: p === k || null }, p)));
      const val = el("input", { type: "number", "aria-label": `Value of set ${i + 1}`, value: v, min: PARAMS[k][0], max: PARAMS[k][1], step: PARAMS[k][2] });
      const upd = () => { sets[i] = { [name.value]: Number(val.value) }; };
      name.addEventListener("change", () => { const [lo, hi, st] = PARAMS[name.value]; val.min = lo; val.max = hi; val.step = st; upd(); });
      val.addEventListener("change", upd);
      const rm = el("button", { class: "btn small ghost", type: "button", "aria-label": `Remove set ${i + 1}`, disabled: sets.length === 1 || null }, "Remove");
      rm.addEventListener("click", () => { sets.splice(i, 1); renderExperiments(); });
      cfg.append(el("div", { class: "controls" }, el("span", {}, `Set ${i + 1}`), name, val, el("span", { class: "faint" }, `[${PARAMS[k][0]}, ${PARAMS[k][1]}]`), rm));
    });
    const add = el("button", { class: "btn small", type: "button", disabled: sets.length >= spec.experiment_max_runs - 2 || null }, "Add parameter set");
    add.addEventListener("click", () => { sets.push({ aperture_radius_px: 3.0 }); renderExperiments(); });
    cfg.append(add, STATIC ? el("p", { class: "status-rejected" }, "Custom parameter sets need the local server (python run.py); the static preview has the standard experiments recorded at build time.") : null);
  } else if (template === "negative_control") {
    const q = el("select", { id: "exp-ncq", "aria-label": "Effect that must be absent" }, ...["variability", "motion"].map((x) => el("option", { value: x, selected: x === ncQuestion || null }, x)));
    q.addEventListener("change", () => { ncQuestion = q.value; });
    cfg.append(el("label", {}, "Effect absent by construction in the control: ", q));
  }
  const def = el("dl", { class: "kv exp-def" },
    el("dt", {}, "Research question"), el("dd", {}, s?.question?.text || el("span", { class: "faint" }, "none set (Command Center)")),
    el("dt", {}, "Hypothesis"), el("dd", {}, hyp),
    el("dt", {}, "Input dataset"), el("dd", {}, state.target ? `${state.targetId} (${state.target.observations.filter((o) => o.included).length} observations; synthetic: ${state.model?.synthetic ? "yes" : "unknown until analysed"})` : "no data for this target"),
    el("dt", {}, "Method"), el("dd", {}, `analysis pipeline ${state.inv?.record.parameters.analysis_version || ""} · ${T[template].title}`),
    el("dt", {}, "Baseline"), el("dd", {}, "the default parameters"),
    el("dt", {}, "Expected output / criterion"), el("dd", {}, T[template].criterion),
    el("dt", {}, "Known limitations"), el("dd", {}, `at most ${spec.experiment_max_runs} analyses; synthetic fixtures only; a run that completes is not a valid experiment by itself`));
  const go = el("button", { class: "btn primary", type: "button", id: "exp-run", disabled: !state.target || running || null, title: state.target ? "" : "This target has no stored observations" },
    running ? "Running…" : "Run experiment");
  go.addEventListener("click", async () => {
    if (!go.dataset.armed) { go.dataset.armed = "1"; go.textContent = `Confirm: runs up to ${template === "parameter" ? sets.length + 1 : template === "robustness" || template === "sensitivity" ? 6 + 1 : 2} analyses`; return; }
    running = true; renderExperiments();
    const c = { template, ...(template === "parameter" ? { configs: sets } : {}), ...(template === "negative_control" ? { question: ncQuestion } : {}) };
    try {
      last = await api.experiment(state.targetId, c);
      last.config = { ...c, hypothesis: $("#exp-hyp")?.value || null, question: c.question ?? null, research_question: s?.question?.text || null };
      await recordExperiment(last);
    } catch (e) { toast(e.message, 7000); last = { error: e.message }; }
    running = false; renderExperiments();
  });
  body.append(el("div", { class: "grid-2" }, el("div", { class: "card" }, el("h3", {}, "Template"), pick),
    el("div", { class: "card" }, el("h3", {}, "Experiment definition"), def, cfg, el("div", { class: "controls" }, go))));
  if (last && !last.error) body.append(resultView(last));
  body.append(historyView());
}

function resultView(r) {
  const ev = r.evaluation || {};
  const rows = r.runs.map((x) => el("tr", {}, el("td", {}, x.label), el("td", { class: "mono" }, x.target), el("td", { class: "mono wrap" }, JSON.stringify(x.params)),
    el("td", { class: x.ok ? "status-ok" : "status-rejected" }, x.ok ? "completed" : `failed: ${x.error}`), el("td", { class: "mono" }, x.content_hash ? x.content_hash.slice(0, 12) : "—"),
    el("td", { class: "wrap" }, x.categories ? Object.entries(x.categories).map(([q, c]) => `${q}: ${c.replaceAll("_", " ")}`).join("; ") : "—"),
    el("td", { class: "num" }, x.pm_measured_mas_yr != null ? x.pm_measured_mas_yr.toFixed(0) : "—"), el("td", { class: "num" }, x.max_abs_z_calibrated != null ? x.max_abs_z_calibrated.toFixed(1) : "—")));
  const evNode = ev.rows ? el("ul", { class: "plain" }, ...ev.rows.map((x) => el("li", {}, el("span", { class: x.passed ? "status-ok" : "status-rejected" }, x.passed ? "meets" : "does not meet"), ` ${x.label}: ${x.detail}`)))
    : ev.pairs ? el("div", {}, el("p", {}, `${ev.n_agree} of ${ev.n_pairs} calibrated pairs: PAIRDIFF-1 and PAIRDIFF-2 agree on detection.`),
        ev.motion ? el("p", {}, `Motion fits agree within 3σ: ${ev.motion.agree_within_3sigma ? "yes" : "no"} (ξ ${ev.motion.axes.xi.difference_sigma?.toFixed(2)}σ, η ${ev.motion.axes.eta.difference_sigma?.toFixed(2)}σ). ${ev.motion.note}`) : null)
    : el("p", {}, ev.detail || "");
  return el("div", { class: "card", id: "exp-result" }, el("h3", {}, `${r.title}: `, el("span", { class: ev.passed ? "status-ok" : ev.passed === false ? "status-rejected" : "muted" },
      ev.passed === true ? "criterion met" : ev.passed === false ? "criterion not met" : "no evaluation")),
    r.recorded_at_build ? el("p", { class: "banner preview" }, "Recorded when this preview was built: the server executed these analyses then; nothing was re-executed in your browser.") : null,
    el("p", { class: "muted" }, `Criterion: ${r.criterion}`), evNode,
    el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Run", "Target", "Parameters", "Status", "Content hash", "Outcomes", "pm (mas/yr)", "max |z| cal."].map((h) => el("th", { scope: "col" }, h)))), el("tbody", {}, ...rows))),
    el("p", { class: "faint" }, r.validity_note));
}

function historyView() {
  const xs = state.session?.experiments || [];
  return el("div", { class: "card" }, el("h3", {}, "Experiments in this session"), xs.length ? el("ul", { class: "plain" }, ...xs.slice().reverse().map((e) =>
    el("li", {}, el("strong", {}, e.template.replace("_", " ")), ` · ${fmtDate(e.created_at)} · ${e.result?.evaluation?.passed === true ? "criterion met" : e.result?.evaluation?.passed === false ? "criterion not met" : "—"}`,
      e.result?.recorded_at_build ? el("span", { class: "faint" }, " · recorded at build time") : null))) : el("p", { class: "muted" }, "None yet."));
}

// ------------------------------------------------------------------ workflows
function renderWorkflows(body, spec) {
  if (wfText === null) wfText = JSON.stringify(spec.workflow_templates[0], null, 1);
  const tpl = el("select", { "aria-label": "Workflow template" }, ...spec.workflow_templates.map((w, i) => el("option", { value: i }, w.name)));
  const useTpl = el("button", { class: "btn small", type: "button" }, "Load template");
  useTpl.addEventListener("click", () => { wfText = JSON.stringify(spec.workflow_templates[+tpl.value], null, 1); wfLog = null; renderExperiments(); });
  const ta = el("textarea", { id: "wf-text", rows: "14", class: "mono", "aria-label": "Workflow document (JSON)" }, wfText);
  ta.addEventListener("input", () => { wfText = ta.value; });
  const out = el("div", { id: "wf-validation", "aria-live": "polite" });
  const parse = () => { try { return JSON.parse(ta.value); } catch { return null; } };
  const validate = async () => {
    const w = parse();
    if (!w) { out.replaceChildren(el("p", { class: "status-rejected" }, "Not JSON.")); return null; }
    const r = await api.validateWorkflow(w);
    out.replaceChildren(r.valid ? el("p", { class: "status-ok" }, `Valid: ${w.targets.length} target(s) × ${w.steps.length} step(s).`)
      : el("ul", { class: "limits" }, ...r.errors.map((x) => el("li", { class: "status-rejected" }, x))));
    return r.valid ? w : null;
  };
  const vb = el("button", { class: "btn small", type: "button", id: "wf-validate" }, "Validate");
  vb.addEventListener("click", validate);
  const file = el("input", { type: "file", accept: "application/json,.json", id: "wf-import", class: "sr-only" });
  const pick = el("label", { class: "btn small", for: "wf-import" }, "Import workflow…");
  file.addEventListener("change", async () => {
    const f = file.files[0]; file.value = "";
    if (!f || f.size > 20000) { toast("Import refused: missing or larger than 20 kB"); return; }
    wfText = await f.text(); wfLog = null; renderExperiments(); setTimeout(() => $("#wf-validate")?.click(), 0);
  });
  const exp = el("button", { class: "btn small", type: "button" }, "Export workflow");
  exp.addEventListener("click", async () => { const w = parse(); if (!w) { toast("Not JSON"); return; } if (await download(`skytrace-workflow-${(w.name || "workflow").replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.json`, JSON.stringify(w, null, 1), "application/json")) toast("Workflow exported"); });
  const run = el("button", { class: "btn primary small", type: "button", id: "wf-run", disabled: running || null }, "Validate and run");
  run.addEventListener("click", async () => {
    const w = await validate();
    if (!w) return;
    if (!run.dataset.armed) { run.dataset.armed = "1"; run.textContent = `Confirm: ${w.targets.length * w.steps.length} executions`; return; }
    await runWorkflow(w, null);
  });
  const stop = el("button", { class: "btn small ghost", type: "button", id: "wf-cancel", disabled: !running || null }, "Cancel after the current step");
  stop.addEventListener("click", () => { cancel = true; stop.textContent = "Cancelling…"; });
  body.append(el("div", { class: "card" }, el("h3", {}, "Workflow"),
    el("p", { class: "muted" }, `A workflow declares its targets (≤ ${spec.workflow_limits.max_targets}) and steps (≤ ${spec.workflow_limits.max_steps}); each step is a registered action. Nothing runs until it validates; imported workflows are validated the same way.`),
    el("div", { class: "controls" }, tpl, useTpl, file, pick, exp), ta, el("div", { class: "controls" }, vb, run, stop), out), logView());
}

async function runWorkflow(w, onlyFailed) {
  running = true; cancel = false;
  const prevTarget = state.targetId;
  wfLog = onlyFailed ? wfLog : { name: w.name, started_at: nowIso(), workflow: w, items: w.targets.map((t) => ({ target: t, steps: w.steps.map((s) => ({ id: s.id, action: s.action, status: "pending" })) })) };
  renderExperiments();
  for (const item of wfLog.items) {
    if (cancel) break;
    if (onlyFailed && !item.steps.some((s) => s.status === "failed" || s.status === "cancelled")) continue;
    try { await loadTargetHook(item.target); } catch (e) { item.steps.forEach((s) => { s.status = "failed"; s.error = `target: ${e.message}`; }); continue; }
    for (const st of item.steps) {
      if (cancel) { if (st.status === "pending") st.status = "cancelled"; continue; }
      if (onlyFailed && st.status === "completed") continue;
      const def = w.steps.find((x) => x.id === st.id);
      const dep = def.depends.map((d) => item.steps.find((x) => x.id === d));
      if (dep.some((d) => d.status !== "completed")) { st.status = "skipped"; st.error = "a dependency did not complete"; continue; }
      st.status = "running"; renderExperiments();
      try { const r = await execute(def.action, def.inputs || {}); st.status = r.status === "needs_review" ? "needs_review" : "completed"; st.result = r.result; delete st.error; }
      catch (e) { st.status = "failed"; st.error = e.message; }
      renderExperiments();
    }
  }
  if (cancel) wfLog.items.forEach((it) => it.steps.forEach((s) => { if (s.status === "pending") s.status = "cancelled"; }));
  wfLog.finished_at = nowIso();
  const n = (k) => wfLog.items.reduce((a, it) => a + it.steps.filter((s) => s.status === k).length, 0);
  await S.update("workflow.run", `Workflow “${w.name}”: ${n("completed")} completed, ${n("failed")} failed, ${n("cancelled")} cancelled`, (x) => {
    let rec = { name: w.name.slice(0, 120), started_at: wfLog.started_at, finished_at: wfLog.finished_at, items: wfLog.items.map((it) => ({ target: it.target, steps: it.steps.map((s) => ({ id: s.id, status: s.status, error: s.error ? s.error.slice(0, 200) : null })) })) };
    x.workflows = [...(x.workflows || []), rec].slice(-20);
    return x;
  });
  running = false; cancel = false;
  if (prevTarget && prevTarget !== state.targetId) await loadTargetHook(prevTarget);
  renderExperiments();
}

function logView() {
  if (!wfLog) return el("div", { class: "card" }, el("h3", {}, "Execution record"), el("p", { class: "muted" }, "Not run yet."));
  const failed = wfLog.items.some((it) => it.steps.some((s) => ["failed", "cancelled"].includes(s.status)));
  const retry = el("button", { class: "btn small", type: "button", disabled: !failed || running || null }, "Retry failed or cancelled items");
  retry.addEventListener("click", () => runWorkflow(wfLog.workflow, true));
  return el("div", { class: "card", id: "wf-log" }, el("h3", {}, `Execution record · ${wfLog.name}`),
    el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Target"), ...wfLog.workflow.steps.map((s) => el("th", { scope: "col" }, `${s.id} (${s.action})`)))),
      el("tbody", {}, ...wfLog.items.map((it) => el("tr", {}, el("th", { scope: "row" }, it.target), ...it.steps.map((s) =>
        el("td", { class: `wf-${s.status}` }, el("span", { class: `step-st st-${s.status === "pending" ? "suggested" : s.status === "cancelled" || s.status === "skipped" ? "blocked" : s.status}` }, s.status),
          s.error ? el("div", { class: "faint wrap" }, s.error) : s.result ? el("div", { class: "faint wrap" }, Object.entries(s.result).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === "string" && v.length > 20 ? v.slice(0, 12) + "…" : v}`).join(" · ")) : null))))))),
    el("div", { class: "controls" }, retry));
}

export { setHooks };
