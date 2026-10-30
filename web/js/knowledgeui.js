// Knowledge Atlas: structured, exact search across what this installation holds — saved investigations, research
// sessions, your notebook, hypotheses, research opportunities, challenges, methods and the glossary — and Astro-Twins
// (TWIN-1) with deterministic comparison. No semantic similarity is claimed: there is no embedding model here, so
// matching is exact (every word must occur, case-insensitive) and every result names where it came from.

import { api } from "./api.js";
import { emit, getFrontier, getSpecs, state } from "./state.js";
import { investigationTwin, overlayChallenges, overlayHorizon, twinCompare } from "./frontiercore.js";
import { digest } from "./canon.js";
import { glossaryEntries } from "./palette.js";
import { STATIC } from "./api.js";
import { clear, download, el, renderToken, toast, $ } from "./util.js";

let tab = "search", query = "", facet = "all", twinA = null, twinB = null;
export function setKnowledgeTab(t) { tab = t; }

async function index() {
  const items = [];
  const add = (type, title, text, source, open) => items.push({ type, title: String(title || ""), text: String(text || ""), source, open });
  try {
    const rec = await api.records();
    for (const r of rec.records || []) add("investigation", r.name, [r.target_id, (r.tags || []).join(" "), r.notes, r.context?.question_text].join(" "), `saved investigation ${r.record_id}`, () => emit("goto", { ws: "records" }));
  } catch { /* listed as unavailable below */ }
  try {
    const ss = await api.sessions();
    for (const s of ss.sessions || []) add("session", s.name, [s.question, s.target_id].join(" "), `research session ${s.session_id}`, null);
  } catch { /* none */ }
  for (const b of state.session?.notebook || []) add("note", `${b.type} (${b.author === "user" ? "your text" : "assistant draft"})`, b.text || JSON.stringify(b.ref || {}), `notebook of “${state.session.name}”`, () => emit("goto", { ws: "notebook" }));
  for (const h of state.session?.hypotheses || []) add("hypothesis", h.statement, (h.tests || []).join(" "), "your hypotheses", () => emit("goto", { ws: "arena" }));
  const reg = await api.capabilities().catch(() => null);
  for (const c of reg?.capabilities || []) add("method", c.name, [c.description, (c.methods || []).join(" "), (c.limitations || []).join(" ")].join(" "), `capability registry ${reg.version}`, null);
  for (const g of glossaryEntries()) add("concept", g.term, g.text, "glossary", null);
  if (state.inv) {
    try {
      const f = await getFrontier();
      const H = overlayHorizon(f.spe.horizon, state.session, state.stability?.target === state.targetId || STATIC, !STATIC);
      for (const c of H.cards) add("opportunity", c.question, [c.category_name, c.method, c.prompted_by.join(" ")].join(" "), `Discovery Horizon (${state.targetId})`, () => emit("goto", { ws: "horizon" }));
      for (const c of overlayChallenges(f.asl, state.session).challenges) add("challenge", c.issue, [c.rule, c.why, c.mode_name].join(" "), `Adversarial Lab (${state.targetId})`, () => emit("goto", { ws: "adversarial" }));
      for (const q of f.info.hypothesis_space) for (const h of q.explanations) add("explanation", `${h.id}: ${h.statement}`, `${q.question} ${h.overall}`, `HYPO-1 (${state.targetId})`, () => emit("goto", { ws: "arena" }));
    } catch { /* frontier unavailable */ }
  }
  return items;
}

export async function renderKnowledge() {
  const live = renderToken("knowledge");
  const body = $("#knowledge-body");
  clear(body);
  body.append(el("div", { class: "tabs", role: "tablist", "aria-label": "Knowledge Atlas" }, ...[["search", "Structured search"], ["twins", "Astro-Twins"]].map(([k, t]) => {
    const b = el("button", { type: "button", role: "tab", "aria-selected": String(tab === k), "data-ktab": k }, t);
    b.addEventListener("click", () => { tab = k; renderKnowledge(); });
    return b;
  })));
  if (tab === "search") {
    const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Indexing what this installation holds…");
    body.append(holder);
    const items = await index();
    if (!live()) return;
    holder.remove();
    body.append(searchView(items));
  } else body.append(await twinsView());
}

function searchView(items) {
  const types = ["all", ...new Set(items.map((x) => x.type))];
  const input = el("input", { type: "search", id: "ka-search", value: query, placeholder: "Search (every word must occur)", "aria-label": "Search the knowledge atlas" });
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const hits = items.filter((x) => (facet === "all" || x.type === facet) && words.every((w) => (x.title + " " + x.text + " " + x.source).toLowerCase().includes(w)));
  const results = el("ol", { class: "ka-results", id: "ka-results" }, ...hits.slice(0, 80).map((x) => {
    const b = x.open ? el("button", { class: "btn small", type: "button" }, "Open") : null;
    b?.addEventListener("click", x.open);
    return el("li", {}, el("span", { class: "pill" }, x.type), el("strong", {}, x.title.slice(0, 160)), el("div", { class: "faint" }, x.text.slice(0, 220)),
      el("div", { class: "faint small" }, `source: ${x.source}`), b);
  }));
  input.addEventListener("input", () => { query = input.value; const r = searchView(items); $("#ka-wrap").replaceWith(r); const i = $("#ka-search"); i.focus(); i.selectionStart = i.selectionEnd = i.value.length; });
  const counts = Object.fromEntries(types.map((t) => [t, t === "all" ? items.length : items.filter((x) => x.type === t).length]));
  return el("div", { id: "ka-wrap" }, el("div", { class: "card" }, el("p", { class: "muted" }, "Exact, structured search: no embedding model or semantic similarity is used. Every result shows where it is stored."),
    input, el("div", { class: "tagrow", "aria-label": "Filter by type" }, ...types.map((t) => {
      const b = el("button", { type: "button", class: "tag", "aria-pressed": facet === t ? "true" : "false" }, `${t} (${counts[t]})`);
      b.addEventListener("click", () => { facet = t; const r = searchView(items); $("#ka-wrap").replaceWith(r); });
      return b;
    })), el("p", { class: "faint" }, query ? `${hits.length} result(s)` : `${items.length} items indexed`)), results);
}

async function twinsView() {
  const sp = (await getSpecs()).frontier.twin;
  const twins = [];
  if (state.inv) {
    try { const f = await getFrontier(); twins.push({ label: `Analysis twin · run ${f.twins.analysis.id}`, t: f.twins.analysis }, { label: `Target twin · ${f.twins.target.id}`, t: f.twins.target }); } catch { /* none */ }
  }
  if (state.session) twins.push({ label: `Investigation twin · session ${state.session.session_id}`, t: await investigationTwin(state.session, digest) });
  for (const t of state.twins || []) twins.push(t);
  const pick = (id, cur) => el("select", { id, "aria-label": id === "twin-a" ? "First twin" : "Second twin" }, ...twins.map((x, i) => el("option", { value: String(i), selected: i === cur || null }, x.label)));
  if (twinA === null || twinA >= twins.length) twinA = 0;
  if (twinB === null || twinB >= twins.length) twinB = Math.min(1, twins.length - 1);
  const a = pick("twin-a", twinA), b = pick("twin-b", twinB);
  a.addEventListener("change", () => { twinA = Number(a.value); renderKnowledge(); });
  b.addEventListener("change", () => { twinB = Number(b.value); renderKnowledge(); });
  if (!twins.length) return el("p", { class: "empty" }, "No twin yet: run an analysis or start a session.");
  const A = twins[twinA].t, B = twins[twinB].t;
  const cmp = twinCompare(A, B, sp.sections);
  const exp = el("button", { class: "btn small", type: "button", id: "twin-export" }, "Export both twins and the comparison (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-twins.json", JSON.stringify({ a: A, b: B, comparison: cmp }, null, 1), "application/json")) toast("Twins exported"); });
  const integrity = el("span", { class: "pill", id: "twin-integrity" }, "checking integrity…");
  Promise.all([A, B].map(async (t) => (await digest(Object.fromEntries(Object.entries(t).filter(([k]) => k !== "content_hash")))) === t.content_hash))
    .then(([x, y]) => { integrity.textContent = x && y ? "both content hashes recompute" : "a content hash does not recompute"; integrity.className = `pill ${x && y ? "archive" : "none"}`; });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, sp.semantics + " Kinds: " + sp.kinds.join(", ") + ". Twins of different kinds are not compared."),
    el("div", { class: "controls" }, a, b, exp), integrity),
    el("div", { class: "card" }, el("h3", {}, cmp.comparable ? (cmp.identical ? "Identical" : `Differences (${Object.values(cmp.counts).reduce((x, y) => x + y, 0)})`) : "Not comparable"),
      cmp.comparable ? el("div", {}, ...sp.sections.map((s) => el("details", { open: cmp.differences[s].length && cmp.differences[s].length < 30 || null },
        el("summary", {}, `${s}: ${cmp.differences[s].length} difference(s)`),
        cmp.differences[s].length ? el("table", { class: "twin-diff" }, el("tbody", {}, ...cmp.differences[s].slice(0, 200).map((d) => el("tr", {}, el("th", { scope: "row", class: "mono" }, d.path),
          el("td", { class: "wrap" }, JSON.stringify(d.a)), el("td", { class: "wrap" }, JSON.stringify(d.b)))))) : null)))
        : el("p", {}, cmp.reason)),
    el("details", { class: "card" }, el("summary", {}, "First twin (JSON)"), el("pre", { class: "json small" }, JSON.stringify(A, null, 1))));
}
