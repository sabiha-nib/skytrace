// Observatory Command Center: the research session at a glance, and the missions. Every value is read from the stored
// session, the target's bundle or the recorded analysis (via the research report and the discovery report); empty
// panels say which input is missing. Missions (MISSION-1) are evaluated from the session's recorded activity.

import { emit, getDiscovery, getResearch, getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { evaluate as evalMissions } from "./missions.js";
import { categoryLabel, clear, el, fmtDate, questionLabel, toast, $ } from "./util.js";
import { nowIso } from "./sessioncore.js";

const DET = ["#f3d27a", "#f0a35e", "#e07a5f", "#c5609a", "#8e6bd1", "#5c83d9"];
const OUT_LABEL = { valid: "valid under the tested rules", invalid: "invalid", incompatible: "incompatible", not_available: "data not available", not_checked: "not checked" };

const card = (title, ...kids) => el("div", { class: "card cc-card" }, el("h3", {}, title), ...kids);
const empty = (text, action) => el("div", { class: "cc-empty" }, el("p", { class: "muted" }, text), action || null);

let ccTok = 0;
export async function renderCommand() {
  const t0 = ++ccTok;
  const body = $("#command-body");
  clear(body);
  const s = state.session;
  const t = state.targets.find((x) => x.target_id === state.targetId);
  const obs = state.target?.observations || [];
  const inc = obs.filter((o) => o.included);
  const grid = el("div", { class: "cc-grid" });
  body.append(grid);

  // target and data
  const dates = inc.map((o) => o.t_mid_iso).filter(Boolean).sort();
  grid.append(card("Target and data",
    t ? el("dl", { class: "kv" },
      el("dt", {}, "Target"), el("dd", {}, t.name, t.kind === "synthetic" ? el("span", { class: "pill syn small-pill" }, "synthetic") : null),
      el("dt", {}, "Observations"), el("dd", {}, state.target ? `${inc.length} included of ${obs.length} recorded` : "none stored"),
      el("dt", {}, "Detectors"), el("dd", {}, [...new Set(inc.map((o) => `D${o.detector}`))].join(" ") || "—"),
      el("dt", {}, "Span"), el("dd", {}, dates.length ? `${fmtDate(dates[0])} → ${fmtDate(dates[dates.length - 1])}` : "—"),
      el("dt", {}, "Releases"), el("dd", {}, [...new Set(inc.map((o) => o.release))].join(", ") || "—"))
      : empty("No target selected.")));

  // research question
  const q = s?.question?.text;
  const qin = el("input", { type: "text", id: "cc-question", placeholder: "e.g. Did the source change between the epochs?", "aria-label": "Research question", value: q || "" });
  const qset = el("button", { class: "btn small primary", type: "button", id: "cc-question-set" }, q ? "Update" : "Set question");
  qset.addEventListener("click", async () => {
    const v = qin.value.trim();
    if (!v) { toast("Write the question first"); qin.focus(); return; }
    await S.update("question.set", `Research question: ${v.slice(0, 200)}`, (x) => { x.question = { id: null, text: v.slice(0, 500) }; return x; });
    S.syncContextFromSession();
    if (state.inv) await S.attachRun(state.inv, "current analysis");
    renderCommand();
  });
  const toPlan = el("button", { class: "btn small", type: "button", disabled: !q || null, title: q ? "" : "Set a question first" }, "Plan an investigation");
  toPlan.addEventListener("click", () => emit("goto", { ws: "planner", question: q }));
  grid.append(card("Research question", q ? el("p", { class: "cc-question" }, q) : el("p", { class: "muted" }, "No question yet. Setting one starts a research session."),
    el("div", { class: "controls" }, qin, qset, toPlan)));

  // active analysis
  const m = state.model;
  const run = el("button", { class: "btn small primary", type: "button", onclick: () => emit("run") }, "Run analysis");
  grid.append(card("Active analysis", state.inv ? [el("dl", { class: "kv" },
      el("dt", {}, "Run"), el("dd", { class: "mono" }, state.inv.record.content_hash.slice(0, 16) + "…"),
      el("dt", {}, "Method set"), el("dd", {}, state.inv.record.parameters.analysis_version),
      ...m.outcomes.flatMap((o) => [el("dt", {}, questionLabel(o.question)), el("dd", {}, categoryLabel(o.category))])),
      el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "lab" }) }, "Open the Discovery Lab"))]
    : empty(state.target ? "No analysis run yet." : "This target has no stored observations to analyse.", state.target ? run : null)));

  if (!state.inv) {
    grid.append(card("Session activity", activity(s)));
    const mp = await missionsPanel();
    if (t0 === ccTok) body.append(mp);
    return;
  }
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the recorded analysis…");
  grid.append(holder);
  let r, d;
  try { [r, d] = await Promise.all([getResearch(), getDiscovery()]); } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return; }
  if (state.ws !== "command" || t0 !== ccTok) return;
  holder.remove();

  // coverage timeline
  grid.append(card("Observation coverage", coverageChart(r.compat), el("p", { class: "faint" },
    `${r.compat.sequences.length} compatible sequences (SEQ-1) · ${r.compat.duplicates.length} duplicate files · visit rule: ${r.compat.visit_rule}`)));

  // selected epochs
  const sel = [state.selectedKey, state.partnerKey].filter(Boolean);
  grid.append(card("Selected epochs", sel.length ? el("ul", { class: "plain" }, ...sel.map((k) => {
      const o = r.compat.observations.find((x) => x.key === k);
      return el("li", {}, el("span", { class: "mono" }, k), o ? ` · D${o.detector} · ${fmtDate(o.t_mid_iso)} · visit ${o.visit + 1}` : "");
    })) : empty("No observation selected."),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "time" }) }, "Open the Time Machine"))));

  // data quality
  const qs = r.quality.summary;
  grid.append(card("Data quality", el("ul", { class: "plain dq-summary" }, ...Object.entries(qs).filter(([, n]) => n).map(([k, n]) =>
      el("li", {}, el("span", { class: `dq dq-${k}` }, OUT_LABEL[k]), ` ${n} check(s)`))),
    el("p", { class: "faint" }, "Each check stands on its own rule; there is no overall score."),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "quality" }) }, "Open the checks"))));

  // explanations
  const hs = d.hypotheses.questions.flatMap((x) => x.hypotheses);
  const cnt = (st) => hs.filter((h) => h.overall === st).length;
  grid.append(card("Explanations (HYPO-1)", el("dl", { class: "kv" },
      el("dt", {}, "Contradicted"), el("dd", {}, String(cnt("contradicted"))), el("dt", {}, "Consistent so far"), el("dd", {}, String(cnt("consistent so far"))),
      el("dt", {}, "Inconclusive"), el("dd", {}, String(cnt("inconclusive"))), el("dt", {}, "Untested"), el("dd", {}, String(cnt("untested"))),
      el("dt", {}, "Yours"), el("dd", {}, String(s?.hypotheses?.length || 0))),
    el("p", { class: "faint" }, "Statuses come from stated rules over recorded values; none is a probability."),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "arena" }) }, "Open the Hypothesis Arena"))));

  // evidence completeness
  const L = r.ledger;
  const gaps = L.completeness.gaps.filter((g) => !g.expected);
  grid.append(card("Evidence ledger", el("dl", { class: "kv" },
      el("dt", {}, "Claims"), el("dd", {}, String(L.claims.length)), el("dt", {}, "Contradictions"), el("dd", {}, String(L.contradictions.length)),
      el("dt", {}, "Relationship gaps"), el("dd", {}, String(gaps.length)),
      el("dt", {}, "Flagged claims"), el("dd", {}, L.claims.filter((c) => c.flags.some((f) => !f.startsWith("states an absence"))).map((c) => questionLabel(c.question)).join(", ") || "none")),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "graph", tab: "ledger" }) }, "Open the ledger"))));

  // missing inputs
  const lim = d.questions.filter((x) => x.status !== "answerable");
  grid.append(card("Missing inputs", lim.length ? el("ul", { class: "plain" }, ...lim.map((x) => el("li", {}, el("strong", {}, x.status), ` · ${x.text}`,
    x.plan.missing_inputs.length ? el("div", { class: "faint" }, "needs: " + x.plan.missing_inputs.join("; ")) : null))) : empty("Every registered question has its inputs.")));

  // activity and pending
  grid.append(card("Recent activity", activity(s)));
  const plan = s?.plans?.[s.plans.length - 1];
  const pend = plan ? plan.steps.filter((x) => !["completed"].includes(x.status)) : [];
  grid.append(card("Pending research tasks", pend.length ? el("ul", { class: "plain" }, ...pend.map((x) => el("li", {}, el("span", { class: `step-st st-${x.status}` }, x.status.replace("_", " ")), ` ${x.title}`)))
    : empty(plan ? "The latest plan has no open steps." : "No plan yet."),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "planner" }) }, plan ? "Open the plan" : "Make a plan"))));

  // next useful actions
  const top = r.radar.items.filter((x) => x.can_run_now).slice(0, 3);
  grid.append(card("Next useful actions (Discovery Radar)", top.length ? el("ol", { class: "plain" }, ...top.map((x) => el("li", {}, el("strong", {}, x.proposal), el("div", { class: "faint" }, x.why))))
    : empty("No runnable opportunity."), el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "radar" }) }, "Open the radar"))));

  const mp = await missionsPanel();
  if (t0 === ccTok) body.append(mp);
}

function activity(s) {
  if (!s?.history?.length) return empty("No session yet: nothing has been recorded.");
  return el("ol", { class: "activity", reversed: true }, ...s.history.slice(-8).reverse().map((h) =>
    el("li", {}, el("span", { class: "faint" }, fmtDate(h.at)), " ", h.summary)));
}

function coverageChart(c) {
  const obs = c.observations.filter((o) => o.t_mid_mjd != null);
  if (!obs.length) return empty("No dated observations.");
  const t0 = Math.min(...obs.map((o) => o.t_mid_mjd)), t1 = Math.max(...obs.map((o) => o.t_mid_mjd));
  const W = 420, H = 150, L = 34, R = 10, T = 10, B = 26;
  const X = (t) => L + ((t - t0) / Math.max(1, t1 - t0)) * (W - L - R);
  const Y = (d) => T + (d - 1) * ((H - T - B) / 5);
  const svg = el("svg", { class: "chart cc-coverage", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Observation times per detector, ${obs.length} observations` });
  for (let d = 1; d <= 6; d++) svg.append(el("text", { x: 4, y: Y(d) + 4 }, `D${d}`));
  for (const [det, cov] of Object.entries(c.coverage.per_detector))
    for (const g of cov.gaps) {
      const a = cov.visits.find((v) => v.visit === g.after_visit), b = cov.visits.find((v) => v.visit === g.after_visit + 1);
      if (a && b) svg.append(el("line", { class: "gapline", x1: X(a.t_mid_mjd), x2: X(b.t_mid_mjd), y1: Y(+det), y2: Y(+det) }));
    }
  for (const o of obs) {
    const ci = el("circle", { cx: X(o.t_mid_mjd), cy: Y(o.detector), r: 3.2 });
    ci.style.fill = DET[o.detector - 1];
    ci.append(el("title", {}, `${o.key} · ${o.t_mid_iso}`));
    svg.append(ci);
  }
  svg.append(el("line", { class: "axis-line", x1: L, x2: W - R, y1: H - B + 6, y2: H - B + 6 }),
             el("text", { x: L, y: H - 4 }, obs.map((o) => o.t_mid_iso).sort()[0].slice(0, 10)),
             el("text", { x: W - R, y: H - 4, "text-anchor": "end" }, obs.map((o) => o.t_mid_iso).sort().pop().slice(0, 10)));
  return svg;
}

// ------------------------------------------------------------------ missions (MISSION-1)
async function missionsPanel() {
  const spec = await getSpecs();
  const s = state.session;
  const status = s ? evalMissions(spec.missions, s) : [];
  const active = new Set((s?.missions || []).filter((m) => m.status === "active").map((m) => m.template_id));
  const list = spec.missions.filter((m) => state.level === "research" || m.level === "beginner" || active.has(m.id));
  const wrap = el("section", { class: "card", id: "missions", "aria-labelledby": "missions-title" }, el("h3", { id: "missions-title" }, "Missions"),
    el("p", { class: "muted" }, "Guided task sequences. A task is done when the session records it (or, for reviews, when you write the review). Completing a mission means the steps were done — not that a conclusion is right. Nothing is scored."));
  const grid = el("div", { class: "mission-grid" });
  for (const m of list) {
    const st = status.find((x) => x.template_id === m.id);
    const ms = (s?.missions || []).find((x) => x.template_id === m.id);
    const head = el("div", { class: "mission-head" }, el("strong", {}, m.title), el("span", { class: "faint" }, m.level === "beginner" ? " · guided" : " · research"));
    const box = el("div", { class: `mission${st?.complete ? " complete" : ""}`, "data-mission": m.id }, head, el("p", { class: "faint" }, m.objective));
    if (!ms) {
      const b = el("button", { class: "btn small", type: "button" }, "Start mission");
      b.addEventListener("click", async () => {
        await S.update("mission.start", `Mission started: ${m.title}`, (x) => { x.missions = [...x.missions, { template_id: m.id, started_at: nowIso(), status: "active", reviews: [] }].slice(-20); return x; });
        if (state.inv) await S.attachRun(state.inv, "current analysis");
        renderCommand();
      });
      box.append(el("p", { class: "faint" }, "Prerequisites: " + m.prerequisites.join("; ")), el("div", { class: "controls" }, b));
    } else {
      box.append(el("p", { class: "mission-progress" }, st?.complete ? "All tasks done." : `${st?.n_done ?? 0} of ${st?.n_tasks ?? m.tasks.length} tasks done`),
        el("ol", { class: "tasks" }, ...m.tasks.map((t) => {
          const done = st?.tasks.find((x) => x.id === t.id)?.done;
          const li = el("li", { class: done ? "done" : "" }, el("span", { class: "task-st" }, done ? "done" : "open"), ` ${t.title}`, t.note ? el("div", { class: "faint" }, t.note) : null);
          if ("review" in t.criterion && !done) {
            const ta = el("textarea", { rows: "2", "aria-label": `Review for ${m.title}`, placeholder: "What did you check, and what does it not establish?" });
            const save = el("button", { class: "btn small", type: "button" }, "Save review");
            save.addEventListener("click", async () => {
              const v = ta.value.trim();
              if (!v) { toast("Write the review first"); return; }
              await S.update("mission.review", `Review written for ${m.title}`, (x) => {
                const mm = x.missions.find((y) => y.template_id === m.id);
                mm.reviews = [...mm.reviews, { task_id: t.id, note: v.slice(0, 1000), at: nowIso() }].slice(-50);
                return x;
              });
              renderCommand();
            });
            li.append(ta, save);
          }
          return li;
        })));
      if (st?.complete && ms.status === "active") {
        const fin = el("button", { class: "btn small", type: "button" }, "Mark mission completed");
        fin.addEventListener("click", async () => { await S.update("mission.complete", `Mission completed: ${m.title}`, (x) => { x.missions.find((y) => y.template_id === m.id).status = "completed"; return x; }); renderCommand(); });
        box.append(fin);
      }
    }
    grid.append(box);
  }
  wrap.append(grid);
  return wrap;
}
