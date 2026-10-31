// Negative Space (NEG-1): what was attempted and could not be established. Entries derived from the record and the
// environment come from the server; the session adds failed or refused work (experiments, autopilot steps, reproductions)
// and entries you write. Nothing is erased: entries you add stay in the session history.

import { getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { loadEpistemic, needRun, syntheticNote, table } from "./epiui.js";

let q = "", cat = "all", dist = "all";

function sessionEntries(s) {
  const out = [...(s?.negative || [])];
  for (const x of s?.experiments || []) {
    if (["failed", "refused"].includes(x.status))
      out.push({ id: `S-EXP-${x.id}`, category: "failed analysis", distinction: x.status === "refused" ? "test not run" : "test failed", attempted: `${x.template} experiment`,
        why: "experiment in this session", happened: x.status + (x.result?.error ? `: ${String(x.result.error).slice(0, 160)}` : ""), inputs: [], n_inputs: 0, failure: "technical",
        unknown: "the experiment's outcome", repeatable: "yes", unblock: "see the experiment's error", source: "session:experiments", origin: "session" });
  }
  for (const run of s?.autopilot || []) {
    for (const st of run.steps || []) {
      if (st.status === "failed")
        out.push({ id: `S-AP-${run.started_at}-${st.id}`, category: "failed analysis", distinction: "test failed", attempted: `autopilot step ${st.action}`, why: run.objective,
          happened: `failed: ${st.error || ""}`, inputs: [], n_inputs: 0, failure: "technical", unknown: "the step's result", repeatable: "yes", unblock: "the error names the cause",
          source: "session:autopilot", origin: "session" });
    }
  }
  return out;
}

export async function renderNegative() {
  const live = renderToken("negative");
  const body = $("#negative-body");
  clear(body);
  if (!state.inv) { needRun(body, "The registry is built from a recorded analysis and this session."); return; }
  const d = await loadEpistemic(body, "negative");
  if (!d || !live()) return;
  const sp = (await getSpecs()).epistemic.negative;
  const all = [...d.negative.entries, ...sessionEntries(state.session)];
  const search = el("input", { type: "search", id: "neg-search", value: q, placeholder: "Search what was attempted, what happened, inputs…", "aria-label": "Search negative knowledge" });
  search.addEventListener("input", () => { q = search.value; draw(); });
  const cSel = el("select", { id: "neg-cat", "aria-label": "Category" }, el("option", { value: "all" }, "all categories"), ...sp.categories.map((c) => el("option", { value: c, selected: c === cat || null }, c)));
  const dSel = el("select", { id: "neg-dist", "aria-label": "Distinction" }, el("option", { value: "all" }, "all distinctions"), ...sp.distinctions.map((c) => el("option", { value: c, selected: c === dist || null }, c)));
  cSel.addEventListener("change", () => { cat = cSel.value; draw(); });
  dSel.addEventListener("change", () => { dist = dSel.value; draw(); });
  const out = el("div", { id: "neg-out" });
  const draw = () => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    const list = all.filter((e) => (cat === "all" || e.category === cat) && (dist === "all" || e.distinction === dist) &&
      words.every((w) => [e.attempted, e.why, e.happened, e.unknown, e.unblock, ...(e.inputs || [])].join(" ").toLowerCase().includes(w)));
    clear(out).append(el("p", { class: "muted", id: "neg-count" }, `${list.length} of ${all.length} entries`),
      table(["Category", "Distinction", "Attempted", "What happened", "Failure", "Still unknown", "Repeatable", "What would unblock it", "Origin"], list.slice(0, 200).map((e) =>
        el("tr", { "data-neg": e.id }, el("td", {}, e.category), el("td", {}, e.distinction), el("td", { class: "small" }, e.attempted, el("div", { class: "faint" }, e.why)),
          el("td", { class: "small wrap" }, e.happened, e.n_inputs ? el("div", { class: "faint mono" }, `${e.n_inputs} input(s): ${(e.inputs || []).slice(0, 3).join(", ")}`) : null),
          el("td", {}, e.failure), el("td", { class: "small" }, e.unknown), el("td", { class: "small" }, e.repeatable), el("td", { class: "small" }, e.unblock),
          el("td", { class: "small" }, e.origin || "record"))), { id: "neg-table" }));
  };
  draw();
  const exp = el("button", { class: "btn small", type: "button", id: "neg-export" }, "Export registry (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-negative-knowledge.json", JSON.stringify({ method: "NEG-1", entries: all }, null, 1), "application/json")) toast("Registry exported"); });
  body.append(syntheticNote(d), el("div", { class: "card" }, el("p", { class: "muted" }, d.negative.note),
    el("div", { class: "controls" }, search, cSel, dSel, exp)), out, addForm(sp));
}

function addForm(sp) {
  const f = {
    category: el("select", { id: "neg-new-cat", "aria-label": "New entry category" }, ...sp.categories.map((c) => el("option", { value: c }, c))),
    distinction: el("select", { id: "neg-new-dist", "aria-label": "New entry distinction" }, ...sp.distinctions.map((c) => el("option", { value: c }, c))),
    attempted: el("input", { type: "text", id: "neg-new-attempted", placeholder: "What was attempted", "aria-label": "What was attempted" }),
    happened: el("input", { type: "text", id: "neg-new-happened", placeholder: "What happened", "aria-label": "What happened" }),
    unknown: el("input", { type: "text", id: "neg-new-unknown", placeholder: "What remains unknown", "aria-label": "What remains unknown" }),
    unblock: el("input", { type: "text", id: "neg-new-unblock", placeholder: "What could unblock it", "aria-label": "What could unblock it" }),
  };
  const hyp = el("select", { id: "neg-abandon", "aria-label": "Hypothesis to abandon" }, el("option", { value: "" }, "— or abandon one of your hypotheses —"),
    ...(state.session?.hypotheses || []).map((h) => el("option", { value: h.id }, h.statement.slice(0, 80))));
  hyp.addEventListener("change", () => {
    const h = (state.session?.hypotheses || []).find((x) => x.id === hyp.value);
    if (h) { f.category.value = "abandoned hypothesis"; f.distinction.value = "evidence insufficient"; f.attempted.value = `support the hypothesis: ${h.statement}`.slice(0, 200); }
  });
  const add = el("button", { class: "btn primary", type: "button", id: "neg-add" }, "Add to the registry");
  add.addEventListener("click", async () => {
    if (!f.attempted.value.trim() || !f.happened.value.trim()) { toast("Say what was attempted and what happened"); return; }
    await S.update("negative.add", `Negative knowledge: ${f.attempted.value}`.slice(0, 280), (s) => {
      s.negative = [...(s.negative || []), { id: S.newId("neg"), category: f.category.value, distinction: f.distinction.value, attempted: f.attempted.value.slice(0, 300),
        why: "recorded by you", happened: f.happened.value.slice(0, 500), inputs: hyp.value ? [hyp.value] : [], n_inputs: hyp.value ? 1 : 0, failure: "scientific",
        unknown: f.unknown.value.slice(0, 300) || "—", repeatable: "—", unblock: f.unblock.value.slice(0, 300) || "—", source: "session:user", origin: "you" }].slice(-200);
      return s;
    });
    toast("Added; it stays in the session history"); renderNegative();
  });
  return el("div", { class: "card" }, el("h3", {}, "Record something that did not work"), el("div", { class: "controls" }, f.category, f.distinction, hyp),
    el("div", { class: "controls" }, f.attempted, f.happened), el("div", { class: "controls" }, f.unknown, f.unblock, add));
}
