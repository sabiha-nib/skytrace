// Hypothesis Arena. The evidence matrix is computed by the Python pipeline (HYPO-1): each explanation, each test,
// its rule, the recorded values it used and its status. Users can write their own hypotheses and attach recorded
// tests to them; their overall line follows the same published rule (rules.js, parity-tested). Nothing here
// produces a probability, and user hypotheses are labelled as interpretations.

import { emit, getDiscovery, state } from "./state.js";
import { OVERALL_RULE, overallStatus } from "./rules.js";
import { $, categoryLabel, clear, el, questionLabel, toast } from "./util.js";

let question = "variability", selectedTest = null, undo = null;
const LABEL = { consistent: "consistent", contradicted: "contradicted", inconclusive: "inconclusive", not_tested: "not tested",
                evidence_unavailable: "evidence unavailable", incompatible: "incompatible" };

const chip = (status, extra = {}) => el("span", { class: `st st-${status.replaceAll(" ", "-")}`, ...extra }, LABEL[status] || status);

export async function renderArena() {
  const body = $("#arena-body");
  clear(body);
  if (!state.inv) {
    body.append(el("div", { class: "empty" }, el("h3", {}, state.target ? "Run the analysis first" : "No stored observations for this target"),
      el("p", {}, "Hypotheses are tested against recorded measurements; without an analysis there is nothing to test.")));
    return;
  }
  body.append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Testing explanations against the record…"));
  let d;
  try { d = await getDiscovery(); } catch (e) { clear(body).append(el("p", { class: "empty" }, e.message)); return; }
  if (state.ws !== "arena") return;
  clear(body);
  const H = d.hypotheses;
  const tests = {};
  for (const q of H.questions) for (const h of q.hypotheses) for (const t of h.tests) tests[`${h.id}/${t.id}`] = { ...t, hyp: h, q: q.question };
  const qd = H.questions.find((q) => q.question === question) || H.questions[0];
  const tabs = el("div", { class: "tabs", role: "tablist" }, ...H.questions.map((q) => {
    const b = el("button", { role: "tab", "aria-selected": q.question === qd.question ? "true" : "false" }, `${questionLabel(q.question)} · ${categoryLabel(q.outcome)}`);
    b.addEventListener("click", () => { question = q.question; selectedTest = null; renderArena(); });
    return b;
  }));
  const detail = el("div", { class: "card", id: "arena-detail", "aria-live": "polite" }, el("h3", {}, "Select a test"),
    el("p", { class: "muted" }, "Each status comes from the rule shown with it, applied to values already in the record."));
  const matrix = el("table", { class: "matrix" },
    el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Explanation"), el("th", { scope: "col" }, "Recorded tests"), el("th", { scope: "col" }, "Overall"))),
    el("tbody", {}, ...qd.hypotheses.map((h) => el("tr", {},
      el("th", { scope: "row" }, h.statement, el("div", { class: "faint" }, h.id)),
      el("td", {}, ...h.tests.map((t) => {
        const b = el("button", { type: "button", class: "testbtn", "aria-pressed": selectedTest === `${h.id}/${t.id}` ? "true" : "false" },
          chip(t.status), " ", t.description);
        b.addEventListener("click", () => { selectedTest = `${h.id}/${t.id}`; showTest(detail, tests[selectedTest]);
          body.querySelectorAll(".testbtn").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); });
        return b;
      })),
      el("td", {}, chip(h.overall, { title: OVERALL_RULE }))))));
  body.append(tabs,
    el("div", { class: "card" }, el("h3", {}, "Evidence matrix ", el("span", { class: "muted" }, `(${H.method})`)),
      el("p", { class: "muted" }, `Overall rule: ${OVERALL_RULE}. Unequal evidence stays unequal: explanations with no implemented test are shown as not tested, not as plausible.`),
      el("div", { class: "table-wrap" }, matrix), legend()),
    el("div", { class: "grid-2" }, detail, userCard(tests)));
  if (selectedTest && tests[selectedTest]) showTest(detail, tests[selectedTest]);
}

function legend() {
  return el("div", { class: "legend st-legend" }, ...Object.keys(LABEL).map((s) => el("span", {}, chip(s))));
}

function showTest(box, t) {
  box.replaceChildren(el("h3", {}, t.description),
    el("dl", { class: "kv" },
      el("dt", {}, "Explanation"), el("dd", {}, t.hyp.statement),
      el("dt", {}, "Status"), el("dd", {}, chip(t.status)),
      el("dt", {}, "Rule"), el("dd", {}, t.rule),
      el("dt", {}, "Result"), el("dd", {}, t.detail),
      Object.keys(t.values || {}).length ? [el("dt", { class: "lvl-investigate" }, "Recorded values"), el("dd", { class: "lvl-investigate" }, el("pre", { class: "json" }, JSON.stringify(t.values, null, 1)))] : null,
      el("dt", {}, "Kind"), el("dd", {}, "recorded test (deterministic rule over the investigation record)")),
    el("div", { class: "controls" },
      el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "lab", tab: t.q === "motion" ? "motion" : "variability" }) }, "See the measurements"),
      el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "graph", focus: `claim:${t.q}` }) }, "Trace in the Evidence Graph")));
}

// ------------------------------------------------------------------ user hypotheses (interpretations)
function userCard(tests) {
  const ctx = state.context;
  const text = el("textarea", { id: "hyp-text", rows: "2", placeholder: "e.g. The dimming is intrinsic and repeats on other detectors", "aria-label": "Your hypothesis" });
  const picks = el("div", { class: "picks", role: "group", "aria-label": "Recorded tests to attach" }, ...Object.entries(tests).map(([id, t]) =>
    el("label", { class: "pick" }, el("input", { type: "checkbox", value: id }), ` ${t.hyp.id}: ${t.description} `, chip(t.status))));
  const add = el("button", { class: "btn primary", type: "button", id: "hyp-add" }, "Add hypothesis");
  add.addEventListener("click", () => {
    const statement = text.value.trim();
    const chosen = [...picks.querySelectorAll("input:checked")].map((i) => i.value);
    if (!statement) { toast("Write the hypothesis first."); text.focus(); return; }
    ctx.hypotheses.push({ id: `U${Date.now().toString(36)}`, statement, tests: chosen, kind: "interpretation", created_at: new Date().toISOString() });
    emit("context-changed"); renderArena(); toast("Hypothesis added. Save the investigation to keep it.");
  });
  const list = el("ul", { class: "userhyps" }, ...ctx.hypotheses.map((h, i) => {
    const st = h.tests.map((id) => tests[id]?.status).filter(Boolean);
    const missing = h.tests.filter((id) => !tests[id]);
    const remove = el("button", { class: "btn small ghost", type: "button", "aria-label": `Remove hypothesis: ${h.statement}` }, "Remove");
    remove.addEventListener("click", () => {
      const [gone] = ctx.hypotheses.splice(i, 1);
      undo = { h: gone, i };
      emit("context-changed"); renderArena();
      const box = $("#undo-box");
      if (box) { box.hidden = false; setTimeout(() => { if (undo?.h === gone) { undo = null; box.hidden = true; } }, 8000); }
    });
    return el("li", {}, el("div", { class: "next-head" }, el("strong", {}, h.statement), chip(st.length ? overallStatus(st) : "untested", { title: OVERALL_RULE }), remove),
      el("div", { class: "faint" }, "Your interpretation · ", st.length ? `${st.length} recorded test(s) attached` : "no recorded test attached: untested"),
      el("ul", { class: "limits" }, ...h.tests.filter((id) => tests[id]).map((id) => el("li", {}, chip(tests[id].status), ` ${tests[id].description}: ${tests[id].detail}`)),
        ...missing.map((id) => el("li", {}, chip("evidence_unavailable"), ` ${id}: this test does not exist in the current analysis`))));
  }));
  const undoBox = el("div", { class: "undo", id: "undo-box", hidden: !undo, role: "status" }, "Hypothesis removed. ",
    el("button", { class: "btn small", type: "button", onclick: () => { if (undo) { ctx.hypotheses.splice(undo.i, 0, undo.h); undo = null; emit("context-changed"); renderArena(); } } }, "Undo"));
  return el("div", { class: "card" }, el("h3", {}, "Your hypotheses ", el("span", { class: "muted" }, "(interpretations, saved with the investigation)")),
    ctx.question_text ? el("p", {}, el("strong", {}, "Research question: "), ctx.question_text) : el("p", { class: "muted" }, "Choose a research question in the Discovery Engine to keep it with your hypotheses."),
    ctx.hypotheses.length ? list : el("p", { class: "muted" }, "None yet."), undoBox,
    el("details", { class: "explanations", open: !ctx.hypotheses.length || null }, el("summary", {}, "Write a hypothesis"),
      el("label", { for: "hyp-text" }, "Statement"), text,
      el("p", { class: "muted" }, "Attach the recorded tests that bear on it. Its overall line then follows the same rule as the matrix; with no test attached it stays untested."),
      picks, el("div", { class: "controls" }, add)));
}
