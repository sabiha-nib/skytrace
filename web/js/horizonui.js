// Discovery Horizon (HORIZON-1) over the Scientific Possibility Engine (SPE-1): the six layers of the investigation,
// then the research opportunities that remain with the recorded evidence, as cards and as a map. The server computes
// the report without session data; overlayHorizon applies what this session has examined (parity-tested).

import { STATIC } from "./api.js";
import { emit, getFrontier, getSpecs, state } from "./state.js";
import { overlayHorizon } from "./frontiercore.js";
import * as S from "./session.js";
import { clear, download, el, renderToken, toast, $ } from "./util.js";

let catFilter = "all", feasFilter = "all", view = "cards";

export function needRun(body, what) {
  body.append(el("div", { class: "empty" }, el("h3", {}, state.target ? "Run the analysis first" : "No stored observations for this target"),
    el("p", {}, what), state.target ? el("button", { class: "btn primary", type: "button", onclick: () => emit("run") }, "Run analysis") : null));
}

export async function loadFrontier(body, ws) {
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Computing from the recorded analysis…");
  body.append(holder);
  try {
    const f = await getFrontier();
    holder.remove();
    return state.ws === ws ? f : null;
  } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return null; }
}

export async function renderHorizon() {
  const live = renderToken("horizon");
  const body = $("#horizon-body");
  clear(body);
  if (!state.inv) { needRun(body, "The Possibility Engine reads the recorded analysis: its inventory, questions, tests, ledger and challenges."); return; }
  const f = await loadFrontier(body, "horizon");
  if (!f || !live()) return;
  const hasStab = state.stability?.target === state.targetId || STATIC;
  const H = overlayHorizon(f.spe.horizon, state.session, hasStab, !STATIC);
  const L = f.spe.layers;
  body.append(el("div", { class: "spe-layers", role: "list", "aria-label": "Possibility Engine layers" }, ...L.map((l) =>
    el("div", { class: "spe-layer", role: "listitem" }, el("span", { class: "n" }, String(l.n)), el("strong", {}, l.name), el("span", { class: "faint" }, l.method),
      el("div", { class: "spe-sum" }, layerSummary(l, H))))));
  body.append(el("p", { class: "muted" }, `${H.note} Ranking: ${H.ranking_rule}.`));
  const cats = Object.keys(H.categories).filter((k) => H.counts[k]);
  const feas = Object.keys(H.by_feasibility).filter((k) => H.by_feasibility[k]);
  const tag = (label, on, fn) => { const b = el("button", { type: "button", class: "tag", "aria-pressed": on ? "true" : "false" }, label); b.addEventListener("click", fn); return b; };
  const views = el("div", { class: "tabs", role: "tablist", "aria-label": "Horizon view" }, ...[["cards", "Opportunity cards"], ["map", "Opportunity map"], ["layers", "Layer details"]].map(([k, t]) => {
    const b = el("button", { type: "button", role: "tab", "aria-selected": String(view === k), "data-hview": k }, t);
    b.addEventListener("click", () => { view = k; renderHorizon(); });
    return b;
  }));
  const exp = el("button", { class: "btn small", type: "button", id: "horizon-export" }, "Export opportunities (JSON)");
  exp.addEventListener("click", async () => {
    if (await download(`skytrace-horizon-${state.inv.record.content_hash.slice(0, 12)}.json`, JSON.stringify({ method: H.method, content_hash: f.content_hash,
      ranking_rule: H.ranking_rule, note: H.note, cards: H.cards }, null, 1), "application/json")) toast("Opportunities exported");
  });
  body.append(el("div", { class: "card" }, el("div", { class: "controls" }, views, exp),
    view === "cards" ? el("div", {}, el("div", { class: "tagrow", "aria-label": "Filter by category" }, tag("all categories", catFilter === "all", () => { catFilter = "all"; renderHorizon(); }),
      ...cats.map((k) => tag(`${k} · ${H.categories[k]} (${H.counts[k]})`, catFilter === k, () => { catFilter = k; renderHorizon(); }))),
      el("div", { class: "tagrow", "aria-label": "Filter by feasibility" }, tag("any feasibility", feasFilter === "all", () => { feasFilter = "all"; renderHorizon(); }),
        ...feas.map((k) => tag(`${k} (${H.by_feasibility[k]})`, feasFilter === k, () => { feasFilter = k; renderHorizon(); })))) : null));
  if (view === "cards") body.append(cardsView(H));
  else if (view === "map") body.append(mapView(H));
  else body.append(layersView(L));
  S.log("horizon.view", "Discovery Horizon opened");
}

function layerSummary(l, H) {
  const s = l.summary || {};
  if (l.n === 1) return `${s.n_items ?? s.items ?? Object.values(s)[0] ?? "—"} evidence items`;
  if (l.n === 2) return `${s.answerable} answerable · ${s["answerable with limits"]} limited · ${s["not answerable"]} not answerable`;
  if (l.n === 3) return `${(l.items || []).length} designs`;
  if (l.n === 4) return `${s.counterfactual_kinds?.length} scenario kinds · ${s.experiment_templates?.length} experiments · ${s.synthetic_templates?.length} synthetic`;
  if (l.n === 5) return `${s.contradictions} contradictions · ${Object.values(s.challenges || {}).reduce((a, b) => a + b, 0)} challenges`;
  return `${H.cards.length} opportunities`;
}

function cardsView(H) {
  const cards = H.cards.filter((c) => (catFilter === "all" || c.category === catFilter) && (feasFilter === "all" || c.feasibility === feasFilter));
  if (!cards.length) return el("p", { class: "empty" }, "No opportunity matches these filters.");
  return el("ol", { class: "horizon-cards" }, ...cards.map((c) => {
    const plan = el("button", { class: "btn small", type: "button" }, "Plan this question");
    plan.addEventListener("click", () => emit("goto", { ws: "planner", question: c.question }));
    const track = el("button", { class: "btn small ghost", type: "button" }, "Note in the session");
    track.addEventListener("click", async () => {
      await S.update("opportunity.track", `Tracked opportunity ${c.id}: ${c.question.slice(0, 180)}`, (s) => {
        s.annotations = [...s.annotations, { id: S.newId("a"), target: { kind: "opportunity", id: c.id }, text: `Tracking: ${c.question}`.slice(0, 2000),
          created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-200);
        return s;
      }, c.id);
      toast("Noted in the session");
    });
    const open = c.category === "C1" && c.refs.length >= 2 ? el("button", { class: "btn small", type: "button" }, "Open the pair") : null;
    open?.addEventListener("click", () => emit("goto", { ws: "time", key: c.refs[0], partner: c.refs[1] }));
    const tracked = (state.session?.annotations || []).some((a) => a.target?.kind === "opportunity" && a.target.id === c.id);
    return el("li", { class: `horizon-card feas-${c.feasibility.replace(/ /g, "-")}`, "data-cat": c.category },
      el("div", { class: "next-head" }, el("span", { class: "rank" }, `#${c.rank}`), el("span", { class: "pill" }, `${c.category} · ${c.category_name}`),
        el("span", { class: "pill feas" }, c.feasibility), tracked ? el("span", { class: "pill" }, "tracked") : null),
      el("h4", {}, c.question),
      el("dl", { class: "kv compact" },
        el("dt", {}, "Prompted by"), el("dd", { class: "wrap" }, c.prompted_by.join("; ")),
        el("dt", {}, "Required data"), el("dd", {}, c.required_data.join("; ")), el("dt", {}, "Available data"), el("dd", {}, c.available_data.join("; ")),
        el("dt", {}, "Proposed method"), el("dd", {}, c.method), el("dt", {}, "Limitations"), el("dd", {}, c.limitations.join("; ")),
        el("dt", {}, "Expected output"), el("dd", {}, c.expected_output), el("dt", {}, "Why this rank"), el("dd", { class: "faint" }, c.priority_reason)),
      el("div", { class: "controls" }, open, plan, track));
  }));
}

function mapView(H) {
  const KIND = ["evidence", "question", "method", "required evidence"];
  const cols = KIND.map((k) => H.map.nodes.filter((n) => n.kind === k));
  const rowH = 26, W = 1100, colW = W / 4, H_ = Math.max(...cols.map((c) => c.length), 1) * rowH + 40;
  const pos = new Map();
  cols.forEach((c, i) => c.forEach((n, j) => pos.set(n.id, [i * colW + 8, 30 + j * rowH])));
  const svg = el("svg", { class: "hz-map", viewBox: `0 0 ${W} ${H_}`, role: "img", "aria-label": `Opportunity map: ${H.map.nodes.length} nodes, ${H.map.edges.length} links, built from the cards` });
  KIND.forEach((k, i) => svg.append(el("text", { x: i * colW + 8, y: 16, class: "hz-col" }, k)));
  for (const e of H.map.edges) {
    const [x1, y1] = pos.get(e.s), [x2, y2] = pos.get(e.t);
    svg.append(el("line", { x1: x1 + colW - 30, y1: y1 - 4, x2, y2: y2 - 4, class: `hz-edge rel-${e.rel.replace(/ /g, "-")}` }));
  }
  for (const n of H.map.nodes) {
    const [x, y] = pos.get(n.id);
    const t = el("text", { x, y, class: `hz-node k-${n.kind.replace(/ /g, "-")}` }, n.label.length > 46 ? n.label.slice(0, 45) + "…" : n.label);
    t.append(el("title", {}, n.label));
    svg.append(t);
  }
  return el("div", { class: "card" }, el("p", { class: "muted" }, "Evidence → research question → method → required evidence. Every node and link comes from the cards above; nothing is inferred."),
    el("div", { class: "hz-scroll" }, svg));
}

function layersView(L) {
  return el("div", {}, ...L.map((l) => el("details", { class: "card", open: l.n <= 2 || null }, el("summary", {}, el("strong", {}, `${l.n}. ${l.name}`), " ", el("span", { class: "faint" }, l.method)),
    l.items ? el("ul", { class: "plain" }, ...l.items.slice(0, 30).map((it) => el("li", {}, it.text || it.id, it.status ? el("span", { class: "pill" }, it.status) : null,
      it.current ? el("span", { class: "faint" }, ` · now: ${it.current}`) : null, it.why_not ? el("div", { class: "faint" }, it.why_not) : null,
      it.actions ? el("div", { class: "faint" }, `PLAN-1 (${it.plan_intent}): ` + it.actions.map((a) => `${a.action} [${a.status}]`).join(" → ")) : null))) : null,
    l.summary ? el("pre", { class: "json small" }, JSON.stringify(l.summary, null, 1)) : null)));
}

export { getSpecs };
