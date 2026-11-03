// Research Autopilot: a controlled orchestrator, not an autonomous agent. You state an objective; PLAN-1 proposes a
// workflow of registered actions; you choose a permission level; every step is validated against that level and its
// preconditions; nothing runs until you authorize it; each execution is recorded in the session; failures stop the
// run and are shown; afterwards the Discovery Horizon proposes the next step. Network actions are never authorized
// here, and imported workflows never run automatically.

import { api, STATIC } from "./api.js";
import { execute } from "./executor.js";
import { facts } from "./plannerui.js";
import { overlayHorizon } from "./frontiercore.js";
import { emit, getFrontier, getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { clear, el, renderToken, toast, $ } from "./util.js";
import { directorCard } from "./universalui.js";

let plan = null, level = "plan", running = false, cancel = false, log = [];

export async function renderAutopilot() {
  const live = renderToken("autopilot");
  const body = $("#autopilot-body");
  clear(body);
  const sp = (await getSpecs()).frontier.autopilot;
  if (!live()) return;
  directorCard(body);
  const obj = el("textarea", { id: "ap-objective", rows: "2", "aria-label": "Research objective", placeholder: "e.g. Challenge my interpretation of the brightness change." }, plan?.question || "");
  const propose = el("button", { class: "btn primary", type: "button", id: "ap-propose" }, "Propose a workflow");
  propose.addEventListener("click", async () => {
    const q = obj.value.trim();
    if (!q) { toast("State an objective first"); obj.focus(); return; }
    try { plan = await api.plan(q, facts()); plan.question = q; log = []; } catch (e) { toast(e.message, 6000); return; }
    await S.log("autopilot.plan", `Autopilot proposed ${plan.steps?.length || 0} step(s) for: ${q.slice(0, 160)}`, null, { create: true });
    renderAutopilot();
  });
  const lv = el("select", { id: "ap-level", "aria-label": "Permission level" }, ...sp.levels.map((l) => el("option", { value: l.id, selected: l.id === level || null }, l.name)));
  lv.addEventListener("change", () => { level = lv.value; renderAutopilot(); });
  body.append(el("div", { class: "card" }, el("h3", {}, "Objective"), obj, el("div", { class: "controls" }, propose, el("label", { for: "ap-level" }, "Permission level"), lv),
    el("p", { class: "muted" }, "Levels: " + sp.levels.map((l) => `${l.name} (${l.allows.join(" + ")}${l.plans ? ", can plan" : ""})`).join(" · ") +
      ". Network access is never granted here. A step that the level does not allow is skipped and named, never run.")));
  if (!plan) { body.append(el("p", { class: "empty" }, "No workflow yet. The objective is matched by PLAN-1's fixed rules to registered actions; nothing is improvised.")); return; }
  if (!plan.answerable) { body.append(el("div", { class: "card" }, el("p", { class: "status-rejected" }, plan.explanation))); return; }
  const L = sp.levels.find((l) => l.id === level);
  const rows = plan.steps.map((st) => {
    const perm = sp.permission[st.action];
    const allowed = L.allows.includes(perm) && level !== "plan";
    const verdict = st.status === "blocked" ? `blocked: ${st.note}` : st.status === "completed" ? "already done" : perm === "network" ? "never authorized here (network)" :
      level === "plan" ? "not run: the plan-only level runs nothing" : !allowed ? `skipped at this level (needs ${perm} permission)` : "will run";
    return { st, perm, allowed: allowed && st.status !== "blocked" && st.status !== "completed", verdict };
  });
  const auth = el("input", { type: "checkbox", id: "ap-auth" });
  const n = rows.filter((r) => r.allowed).length;
  const run = el("button", { class: "btn primary", type: "button", id: "ap-run", disabled: running || !n || null }, `Run ${n} authorized step(s)`);
  run.addEventListener("click", async () => {
    if (!auth.checked) { toast("Tick the authorization box first"); return; }
    await runSteps(rows.filter((r) => r.allowed));
  });
  const stop = el("button", { class: "btn small ghost", type: "button", id: "ap-cancel", disabled: !running || null }, "Cancel after the current step");
  stop.addEventListener("click", () => { cancel = true; stop.textContent = "Cancelling…"; });
  body.append(el("div", { class: "card" }, el("h3", {}, `Proposed workflow · ${plan.intent.kind} · ${plan.method}`), el("p", { class: "muted" }, plan.explanation),
    el("div", { class: "table-wrap" }, el("table", { id: "ap-steps" }, el("thead", {}, el("tr", {}, ...["#", "Step", "Action", "Permission", "Plan status", "At this level", "Result"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...rows.map((r, i) => {
        const done = log.find((x) => x.id === r.st.id);
        return el("tr", { class: done ? `ap-${done.status}` : "" }, el("td", {}, String(i + 1)), el("td", {}, r.st.title), el("td", { class: "mono" }, r.st.action), el("td", {}, r.perm),
          el("td", {}, r.st.status), el("td", {}, r.verdict), el("td", { class: "wrap" }, done ? `${done.status}${done.error ? ": " + done.error : done.result ? " · " + Object.entries(done.result).slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(", ") : ""}` : "—"));
      })))),
    level === "plan" || level === "inspect" && !n ? el("p", { class: "faint" }, level === "plan" ? "Plan only: review the workflow; nothing runs at this level." : "Nothing at this level can run.") : null,
    el("div", { class: "controls" }, el("label", { class: "chk" }, auth, ` I authorize these ${n} step(s) at the “${L.name}” level`), run, stop)));
  if (log.length && !running) body.append(await nextStep());
}

async function runSteps(rows) {
  running = true; cancel = false; log = [];
  renderAutopilot();
  const started = new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
  for (const r of rows) {
    if (cancel) { log.push({ id: r.st.id, status: "cancelled" }); continue; }
    try {
      const out = await execute(r.st.action, r.st.inputs || {});
      log.push({ id: r.st.id, action: r.st.action, status: out.status, result: out.result });
      if (out.status === "needs_review") { cancel = true; toast("A step needs your judgement; the run stops here.", 6000); }
    } catch (e) { log.push({ id: r.st.id, action: r.st.action, status: "failed", error: e.message.slice(0, 200) }); cancel = true; toast(`Step failed: ${e.message}`, 7000); }
    renderAutopilot();
  }
  await S.update("autopilot.run", `Autopilot (${level}): ${log.filter((x) => x.status === "completed").length} completed, ${log.filter((x) => x.status === "failed").length} failed, ` +
    `${log.filter((x) => x.status === "cancelled").length} cancelled`, (s) => {
    s.autopilot = [...(s.autopilot || []), { objective: plan.question.slice(0, 500), level, started_at: started, steps: log.map((x) => ({ id: x.id, action: x.action || null, status: x.status,
      error: x.error || null, result: x.result ? Object.fromEntries(Object.entries(x.result).slice(0, 6)) : null })) }].slice(-20);
    return s;
  });
  running = false;
  renderAutopilot();
}

async function nextStep() {
  try {
    const f = await getFrontier();
    const H = overlayHorizon(f.spe.horizon, state.session, state.stability?.target === state.targetId || STATIC, !STATIC);
    const c = H.cards[0];
    if (!c) return el("p", { class: "muted" }, "No further opportunity is open.");
    const b = el("button", { class: "btn small", type: "button" }, "Open the Discovery Horizon");
    b.addEventListener("click", () => emit("goto", { ws: "horizon" }));
    return el("div", { class: "card" }, el("h3", {}, "Proposed next step"), el("p", {}, c.question), el("p", { class: "faint" }, `${c.method} · ${c.priority_reason}`), el("div", { class: "controls" }, b));
  } catch (e) { return el("p", { class: "faint" }, e.message); }
}
