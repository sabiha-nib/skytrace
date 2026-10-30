// Evidence Ledger (LEDGER-1): the graph plus inspectors — claims (what supports each, counted by kind, never weighed),
// contradictions (fixed rules), provenance (claim → files and checksums), methods (versions and parameters), completeness
// (missing relationships, listed), and the change history of user-authored material from the research session.

import { emit, getResearch, state } from "./state.js";
import * as S from "./session.js";
import { renderGraph, focusGraph } from "./graph.js";
import { categoryLabel, clear, el, fmtDate, questionLabel, renderToken, shortKey, $ } from "./util.js";

let tab = "graph", claimSel = null;
export function setLedgerTab(t) { tab = t; }
const USER_KINDS = /^(question\.set|context\.update|hypothesis\.|note\.|session\.rename|mission\.review|plan\.create)/;

export async function renderLedger() {
  const live = renderToken("ledger");
  const body = $("#graph-body");
  clear(body);
  const tabs = [["graph", "Graph"], ["claims", "Claim inspector"], ["contradictions", "Contradictions"], ["provenance", "Provenance"], ["methods", "Methods"], ["completeness", "Completeness"], ["history", "Change history"]];
  body.append(el("div", { class: "tabs", role: "tablist" }, ...tabs.map(([id, l]) => {
    const b = el("button", { role: "tab", "aria-selected": id === tab ? "true" : "false", "data-ltab": id }, l);
    b.addEventListener("click", () => { tab = id; renderLedger(); });
    return b;
  })));
  const host = el("div", { id: "ledger-host" });
  body.append(host);
  if (tab === "history") { host.append(historyPanel()); return; }
  if (tab === "graph") { await renderGraph(host); return; }
  if (!state.inv) { host.append(el("p", { class: "empty" }, state.target ? "Run the analysis to build the ledger." : "This target has no stored observations yet.")); return; }
  host.append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the ledger…"));
  let r;
  try { r = await getResearch(); } catch (e) { clear(host).append(el("p", { class: "empty" }, e.message)); return; }
  if (state.ws !== "graph" || !live()) return;
  clear(host);
  const L = r.ledger;
  S.log("ledger.view", "Evidence Ledger opened");
  if (tab === "claims") { S.log("ledger.claim", "Claim inspector opened"); host.append(claimsPanel(L)); }
  if (tab === "contradictions") { S.log("ledger.contradictions", "Contradiction inspector opened"); host.append(contradictionsPanel(L)); }
  if (tab === "provenance") host.append(provenancePanel(L));
  if (tab === "methods") host.append(methodsPanel(L));
  if (tab === "completeness") host.append(completenessPanel(L));
}

function claimsPanel(L) {
  claimSel = claimSel && L.claims.some((c) => c.id === claimSel) ? claimSel : L.claims[0]?.id;
  const c = L.claims.find((x) => x.id === claimSel);
  const list = el("div", { class: "qlist", role: "radiogroup", "aria-label": "Claims" }, ...L.claims.map((x) => {
    const b = el("button", { type: "button", role: "radio", "aria-checked": x.id === claimSel ? "true" : "false", class: "qitem" },
      el("span", { class: "qstatus" }, questionLabel(x.question)), el("span", {}, categoryLabel(x.category)));
    b.addEventListener("click", () => { claimSel = x.id; renderLedger(); });
    return b;
  }));
  const userH = (state.session?.hypotheses || []).filter((h) => h.tests.some((t) => c?.explanations.some((e) => t.startsWith(e.id + "/"))));
  const notes = (state.session?.notebook || []).filter((b) => b.ref?.id === c?.id);
  return el("div", { class: "grid-2" }, el("div", { class: "card" }, el("h3", {}, "Claims"), list),
    c ? el("div", { class: "card", id: "claim-detail" }, el("h3", {}, `${questionLabel(c.question)}: ${categoryLabel(c.category)}`), el("p", {}, c.statement),
      c.flags.length ? el("ul", { class: "limits" }, ...c.flags.map((f) => el("li", { class: "status-rejected" }, f))) : null,
      el("dl", { class: "kv" }, el("dt", {}, "Directly linked support"), el("dd", {}, String(c.support.direct)), el("dt", {}, "Comparisons"), el("dd", {}, String(c.support.comparisons)),
        el("dt", {}, "Observations traced"), el("dd", {}, String(c.support.observations)), el("dt", {}, "Detectors"), el("dd", {}, c.support.detectors.map((d) => `D${d}`).join(" ") || "—"),
        el("dt", {}, "Dates"), el("dd", {}, c.support.dates.length ? `${c.support.dates.length} (${c.support.dates[0]} … ${c.support.dates[c.support.dates.length - 1]})` : "—"),
        el("dt", {}, "Relations"), el("dd", {}, Object.entries(c.support.by_relation).map(([k, v]) => `${k} ×${v}`).join(" · "))),
      el("p", { class: "faint" }, c.support_note),
      el("h4", {}, "Competing explanations (HYPO-1)"), el("ul", { class: "plain" }, ...c.explanations.map((e) => el("li", {}, el("span", { class: `st st-${e.overall.replaceAll(" ", "-")}` }, e.overall), ` ${e.id}: ${e.statement}`))),
      userH.length || notes.length ? [el("h4", {}, "User-authored (research session)"), el("ul", { class: "plain" }, ...userH.map((h) => el("li", {}, el("span", { class: "kind interpretation" }, "your interpretation"), ` ${h.statement}`)),
        ...notes.map((n) => el("li", {}, el("span", { class: "kind interpretation" }, "notebook"), ` ${n.type} block`)))] : null,
      el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => { focusGraph(c.id); tab = "graph"; renderLedger(); } }, "Trace in the graph"))) : el("p", {}, "No claims."));
}

function contradictionsPanel(L) {
  return el("div", { class: "card" }, el("h3", {}, `Contradiction inspector: ${L.contradictions.length} found`),
    el("dl", { class: "kv compact" }, ...Object.entries(L.rules).flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])),
    L.contradictions.length ? el("ol", { class: "plain contradictions" }, ...L.contradictions.map((x) => el("li", {}, el("strong", {}, `${x.rule} · ${x.kind}`), el("div", {}, x.detail),
      el("div", { class: "faint" }, x.meaning), el("div", { class: "faint mono wrap" }, x.items.map(shortKey).join(" · "))))) : el("p", { class: "muted" }, "No rule found conflicting values in this run."),
    el("p", { class: "faint" }, "Conflicts between your own hypotheses and the recorded tests appear in the Hypothesis Arena, where a contradicted test makes the hypothesis contradicted."));
}

function provenancePanel(L) {
  return el("div", {}, ...L.claims.map((c) => el("div", { class: "card" }, el("h3", {}, `${questionLabel(c.question)}: files behind the claim`),
    c.provenance.files.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Observation", "File", "SHA-256"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...c.provenance.files.map((f) => el("tr", {}, el("td", { class: "mono" }, shortKey(f.observation)), el("td", { class: "mono wrap" }, f.file || "not recorded"), el("td", { class: "mono wrap" }, f.sha256 || "not recorded"))))))
      : el("p", { class: "muted" }, "No observation is traced to this claim (it states an absence or has no linked support)."),
    c.provenance.missing_sha256.length ? el("p", { class: "status-rejected" }, `${c.provenance.missing_sha256.length} observation(s) without a checksum`) : null)));
}

function methodsPanel(L) {
  return el("div", {}, ...L.claims.map((c) => el("div", { class: "card" }, el("h3", {}, `${questionLabel(c.question)}: methods and parameters`),
    el("dl", { class: "kv compact" }, el("dt", {}, "Methods linked"), el("dd", {}, c.methods.join(", ")),
      ...Object.entries(c.parameters).flatMap(([k, v]) => [el("dt", {}, k), el("dd", { class: "mono" }, String(v))]),
      el("dt", {}, "Criteria"), el("dd", { class: "wrap" }, typeof c.criteria === "string" ? c.criteria : JSON.stringify(c.criteria || {})),
      el("dt", {}, "Limitations"), el("dd", {}, (c.limitations || []).join("; ") || "—")))));
}

function completenessPanel(L) {
  const C = L.completeness;
  return el("div", { class: "card" }, el("h3", {}, "Evidence completeness"), el("p", { class: "muted" }, `${C.note}. ${C.n_nodes} nodes, ${C.n_edges} relationships.`),
    Object.keys(C.counts).length ? el("ul", { class: "plain" }, ...Object.entries(C.counts).map(([k, n]) => el("li", {}, `${k}: ${n}`))) : el("p", { class: "status-ok" }, "No missing relationship found."),
    C.gaps.length ? el("details", {}, el("summary", {}, `List (${C.gaps.length})`), el("ul", { class: "limits" }, ...C.gaps.slice(0, 200).map((g) => el("li", {}, `${g.kind}: ${shortKey(g.id)}${g.expected ? " (expected for synthetic data)" : ""}`)))) : null);
}

function historyPanel() {
  const h = (state.session?.history || []).filter((x) => USER_KINDS.test(x.kind));
  return el("div", { class: "card" }, el("h3", {}, "Change history of user-authored material"),
    el("p", { class: "muted" }, "From the research session's append-only history: questions, hypotheses, notes, reviews and plans. Earlier versions of edited hypotheses and notes are kept with them."),
    h.length ? el("ol", { class: "activity", reversed: true }, ...h.slice().reverse().map((x) => el("li", {}, el("span", { class: "faint" }, `${fmtDate(x.at)} · ${x.kind}`), ` ${x.summary}`)))
      : el("p", { class: "muted" }, state.session ? "Nothing user-authored has changed yet." : "No research session yet."));
}
