// Adaptive Investigation Planner canvas (PLAN-1). The plan comes from the deterministic planner (server, or the
// parity-tested browser port in the static preview); steps run through the shared executor, one registered action
// each. Steps that re-execute analyses or take time ask for confirmation. Every plan and step result is stored in the
// research session. Statuses: suggested · ready · running · completed · blocked · failed · needs review.

import { api, STATIC } from "./api.js";
import { emit, getResearch, getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { execute } from "./executor.js";
import { nowIso } from "./sessioncore.js";
import { clear, el, toast, $ } from "./util.js";

const LABEL = { suggested: "suggested", ready: "ready", running: "running", completed: "completed", blocked: "blocked", failed: "failed", needs_review: "needs review" };
let pendingQuestion = null, armed = new Set(), busy = false;

export function setPlannerQuestion(q) { pendingQuestion = q; }

function facts() {
  const pair = state.selectedKey && state.partnerKey ? [state.selectedKey, state.partnerKey] : null;
  return { has_target_data: !!state.target, has_run: !!state.inv, run_hash: state.inv?.record.content_hash || null, pair,
           server: !STATIC, static: STATIC, network: state.status?.offline ? false : null, has_question: !!state.session?.question?.text,
           targets: state.targets.flatMap((t) => [t.target_id, t.name]) };
}

export async function renderPlanner() {
  const body = $("#planner-body");
  await getSpecs();
  clear(body);
  const s = state.session;
  const last = s?.plans?.[s.plans.length - 1] || null;
  const qv = pendingQuestion ?? state.plan?.question ?? last?.question ?? s?.question?.text ?? "";
  pendingQuestion = null;
  const input = el("textarea", { id: "plan-question", rows: "2", "aria-label": "Research question to plan", placeholder: "e.g. Could this source have changed between the two recorded observation epochs?" }, qv);
  const go = el("button", { class: "btn primary", type: "button", id: "plan-go" }, "Plan");
  go.addEventListener("click", () => makePlan(input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) makePlan(input.value); });
  const f = facts();
  body.append(el("div", { class: "card" }, el("h3", {}, "Research question"),
    el("div", { class: "plan-q" }, input, go),
    el("p", { class: "faint" }, "The planner matches the question against fixed rules and arranges registered actions; it does not interpret free text beyond that, and it never decides an outcome. Ctrl+Enter plans."),
    el("dl", { class: "kv compact evidence-now" },
      el("dt", {}, "Target data"), el("dd", {}, f.has_target_data ? `${state.target.observations.filter((o) => o.included).length} observations` : "none stored"),
      el("dt", {}, "Analysis run"), el("dd", {}, f.has_run ? f.run_hash.slice(0, 12) + "…" : "not yet"),
      el("dt", {}, "Selected pair"), el("dd", {}, f.pair ? f.pair.join(" · ") : "none (select two observations in the Time Machine)"),
      el("dt", {}, "Runs on"), el("dd", {}, STATIC ? "static preview: server-only steps are blocked; precomputed steps serve the build's results" : "the Skytrace server"))));
  if (!state.plan && last) state.plan = fromStored(last);
  if (state.plan) body.append(planCanvas(state.plan));
  else body.append(el("div", { class: "empty" }, el("h3", {}, "No plan yet"), el("p", {}, "Write a question and press Plan."),
    el("ul", { class: "plain" }, ...(state.specs.planner.examples || []).map((x) => el("li", {}, el("button", { class: "linklike", type: "button", onclick: () => makePlan(x) }, x))))));
}

function fromStored(p) {
  return { id: p.id, question: p.question, intent: p.intent, revision: p.revision, confirmed: p.confirmed, answerable: true, explanation: "",
           steps: p.steps.map((x) => ({ ...(state.specs.planner.actions[x.capability] || {}), ...x, action: x.capability, inputs: x.inputs || {}, note: x.note || "" })) };
}

async function makePlan(q) {
  q = (q || "").trim();
  if (!q) { toast("Write a question first"); $("#plan-question")?.focus(); return; }
  let p;
  try { p = await api.plan(q, facts()); } catch (e) { toast(e.message); return; }
  const s = state.session;
  const prev = (s?.plans || []).filter((x) => x.question === p.question);
  p.id = S.newId("p");
  p.revision = prev.length + 1;
  p.confirmed = false;
  state.plan = p;
  armed = new Set();
  if (p.steps.length) await storePlan("plan.create", `Plan r${p.revision}: ${q.slice(0, 120)} (${p.intent.kind}, ${p.steps.length} steps)`);
  renderPlanner();
}

async function storePlan(kind, summary) {
  const p = state.plan;
  await S.update(kind, summary, (s) => {
    const stored = { id: p.id, question: p.question.slice(0, 500), created_at: p.created_at || nowIso(), revision: p.revision, confirmed: !!p.confirmed,
      intent: { kind: p.intent.kind, aspects: p.intent.aspects, keys: p.intent.keys, detectors: p.intent.detectors, dates: p.intent.dates, pair_requested: p.intent.pair_requested },
      steps: p.steps.map((x) => ({ id: x.id, capability: x.action, status: x.status, depends: x.depends, title: x.title.slice(0, 200),
        inputs: x.inputs || {}, note: String(x.note || "").slice(0, 500), optional: !!x.optional,
        ...(x.result ? { result: x.result } : {}), ...(x.error ? { error: String(x.error).slice(0, 1000) } : {}),
        ...(x.started_at ? { started_at: x.started_at } : {}), ...(x.finished_at ? { finished_at: x.finished_at } : {}) })) };
    p.created_at = stored.created_at;
    s.plans = [...s.plans.filter((x) => x.id !== p.id), stored].slice(-30);
    return s;
  }, p.id);
  if (state.inv) await S.attachRun(state.inv, "current analysis");
}

function planCanvas(p) {
  const wrap = el("div", { class: "card plan-canvas", id: "plan-canvas" });
  wrap.append(el("div", { class: "plan-head" }, el("h3", {}, `Plan${p.revision ? ` · revision ${p.revision}` : ""}`),
    el("span", { class: "pill" }, `intent: ${p.intent.kind}`), p.intent.pair_requested ? el("span", { class: "pill" }, "pair requested") : null),
    el("p", { class: p.answerable ? "muted" : "status-rejected" }, p.explanation || ""));
  if (!p.steps.length) return wrap;
  const runnable = p.steps.filter((x) => x.status === "ready" && !x.review);   // review steps open a view; they run one at a time
  const needConfirm = runnable.filter((x) => x.confirm);
  const all = el("button", { class: "btn primary", type: "button", id: "plan-run", disabled: !runnable.length || busy || null,
                             title: runnable.length ? "" : "No step is ready" }, needConfirm.length && !p.confirmed ? `Confirm and run ${runnable.length} ready step(s)` : `Run ${runnable.length} ready step(s)`);
  all.addEventListener("click", async () => {
    if (needConfirm.length && !p.confirmed) {
      if (!all.dataset.armed) { all.dataset.armed = "1"; all.textContent = `Confirm: ${needConfirm.map((x) => x.title.toLowerCase()).join("; ")} (${needConfirm.map((x) => x.cost).join("; ")})`; return; }
      p.confirmed = true;
    }
    await runSteps(runnable.map((x) => x.id));
  });
  wrap.append(el("div", { class: "controls" }, all, el("span", { class: "faint" }, needConfirm.length ? "Steps marked ‘confirm’ re-execute analyses or take time." : "")));
  const ol = el("ol", { class: "plan-steps" });
  for (const x of p.steps) {
    const li = el("li", { class: `plan-step st-${x.status}`, "data-step": x.id },
      el("div", { class: "plan-step-head" }, el("span", { class: `step-st st-${x.status}` }, LABEL[x.status] || x.status), el("strong", {}, x.title),
        x.confirm ? el("span", { class: "pill small-pill" }, "confirm") : null, x.optional ? el("span", { class: "faint" }, " optional") : null),
      el("div", { class: "faint" }, `${x.action} · capabilities: ${(x.capabilities || []).join(", ")} · cost: ${x.cost}` + (x.depends?.length ? ` · after: ${x.depends.join(", ")}` : "")),
      x.note ? el("div", { class: x.status === "blocked" ? "status-rejected step-note" : "step-note" }, x.note) : null,
      x.error ? el("div", { class: "status-rejected step-note" }, "Failed: " + x.error) : null,
      x.result ? resultTable(x.result) : null);
    const ctl = el("div", { class: "controls" });
    if (["ready", "suggested", "failed"].includes(x.status) && !busy) {
      const b = el("button", { class: "btn small", type: "button" }, x.status === "failed" ? "Retry" : "Run");
      b.addEventListener("click", async () => {
        if (x.confirm && !armed.has(x.id)) { armed.add(x.id); b.textContent = `Confirm (${x.cost})`; return; }
        await runSteps([x.id]);
      });
      ctl.append(b);
    }
    if (x.status === "needs_review") {
      const ta = el("textarea", { rows: "2", "aria-label": `What you saw for ${x.title}`, placeholder: "What did you see? (kept with the plan step)" });
      const ok = el("button", { class: "btn small", type: "button" }, "Mark reviewed");
      ok.addEventListener("click", async () => {
        const v = ta.value.trim();
        if (!v) { toast("Write what you saw first"); return; }
        x.status = "completed"; x.result = { ...(x.result || {}), reviewed: true, review_note: v.slice(0, 1000) }; x.finished_at = nowIso();
        await storePlan("plan.step", `Reviewed: ${x.title}`);
        refreshDependents(); renderPlanner();
      });
      ctl.append(ta, ok);
      if (x.inputs?.a) ctl.append(el("button", { class: "btn small ghost", type: "button", onclick: () => emit("goto", { ws: "time", key: x.inputs.a, partner: x.inputs.b }) }, "Open the pair"));
    }
    if (ctl.children.length) li.append(ctl);
    ol.append(li);
  }
  wrap.append(ol);
  if (p.steps.every((x) => ["completed", "blocked"].includes(x.status) || (x.optional && x.status === "suggested"))) wrap.append(nextBox());
  return wrap;
}

function resultTable(r) {
  return el("dl", { class: "kv compact step-result" }, ...Object.entries(r).flatMap(([k, v]) => [el("dt", {}, k.replaceAll("_", " ")),
    el("dd", { class: typeof v === "string" && /^[0-9a-f]{64}$/.test(v) ? "mono wrap" : "" }, v === null ? "—" : typeof v === "boolean" ? (v ? "yes" : "no") : String(v))]));
}

function refreshDependents() {
  const p = state.plan;
  const st = Object.fromEntries(p.steps.map((x) => [x.id, x.status]));
  for (const x of p.steps) {
    if (x.status === "blocked" && String(x.note || "").startsWith("waits for") && x.depends.every((d) => st[d] === "completed")) { x.status = x.optional ? "suggested" : "ready"; x.note = ""; }
  }
}

async function runSteps(ids) {
  const p = state.plan;
  busy = true;
  for (const id of ids) {
    const x = p.steps.find((y) => y.id === id);
    if (!x || !["ready", "suggested", "failed"].includes(x.status)) continue;
    if (x.depends.some((d) => p.steps.find((y) => y.id === d)?.status !== "completed")) { x.note = "waits for: " + x.depends.join(", "); continue; }
    x.status = "running"; x.error = undefined; x.started_at = nowIso();
    renderPlanner();
    try {
      const r = await execute(x.action, x.inputs || {});
      x.status = r.status; x.result = r.result; x.finished_at = nowIso();
    } catch (e) { x.status = "failed"; x.error = e.message; x.finished_at = nowIso(); }
    await storePlan("plan.step", `${x.title}: ${x.status}${x.error ? " — " + x.error.slice(0, 120) : ""}`);
  }
  busy = false;
  refreshDependents();
  renderPlanner();
}

function nextBox() {
  const box = el("div", { class: "plan-next" }, el("h4", {}, "Next scientifically useful step"), el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the radar…"));
  getResearch().then((r) => {
    const top = r?.radar.items.filter((x) => x.can_run_now).slice(0, 2) || [];
    box.replaceChildren(el("h4", {}, "Next scientifically useful step"),
      top.length ? el("ul", { class: "plain" }, ...top.map((x) => el("li", {}, el("strong", {}, x.proposal), el("div", { class: "faint" }, `${x.why} · cannot establish: ${x.cannot_establish}`))))
        : el("p", { class: "muted" }, "The radar has no runnable opportunity."),
      el("p", { class: "faint" }, "Remaining uncertainties: see the Uncertainty tab and the blocked or optional steps above."));
  }).catch((e) => box.replaceChildren(el("p", {}, e.message)));
  return box;
}
