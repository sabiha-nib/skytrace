// Claims: Knowledge Boundary (KBOUND-1), Claim Stress Test (CLAIMX-1) and Blindspots (BLIND-1).
// Regions are categories with stated rules, never confidence levels; stress modes have documented rules; blindspot
// coverage is over a fixed list of checks (session parts applied in the browser by overlayBlindspots).

import { emit, getSpecs, state } from "./state.js";
import { overlayBlindspots } from "./epistemiccore.js";
import { focusNode } from "./reasoningui.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, outcomePill, statusPill, syntheticNote, table, tabs } from "./epiui.js";

let tab = "boundary", openItem = null, claim = "variability";
export function setClaimsTab(t) { tab = t; }

export async function renderClaims() {
  const live = renderToken("claims");
  const body = $("#claims-body");
  clear(body);
  if (!state.inv) { needRun(body, "Claims are read from a recorded analysis."); return; }
  const d = await loadEpistemic(body, "claims");
  if (!d || !live()) return;
  body.append(syntheticNote(d), tabs("Claims", [["boundary", "Knowledge boundary"], ["stress", "Claim stress test"], ["blindspot", "Blindspots"]], tab, "data-cltab",
    (k) => { tab = k; renderClaims(); }));
  if (tab === "boundary") body.append(boundaryView(d.boundary));
  else if (tab === "stress") body.append(stressView(d));
  else body.append(await blindView(d.blindspot));
}

function boundaryView(B) {
  const cols = el("div", { class: "kb-map", role: "list", "aria-label": "Knowledge boundary map" }, ...B.regions.map((r) => el("section", { class: `kb-region r-${r.replace(/\s+/g, "-")}`, role: "listitem", "data-region": r },
    el("h4", {}, B.region_labels[r], el("span", { class: "faint" }, ` ${B.counts[r]}`)),
    ...B.items.filter((i) => i.region === r).map((i) => {
      const b = el("button", { type: "button", class: `kb-item${openItem === i.id ? " current" : ""}`, "data-kb": i.id }, el("span", { class: "pill faint" }, i.kind), " ", (i.statement || "").slice(0, 110));
      b.addEventListener("click", () => { openItem = i.id; renderClaims(); });
      return b;
    }))));
  const it = B.items.find((i) => i.id === openItem) || B.items.find((i) => i.kind === "claim");
  const exp = el("button", { class: "btn small", type: "button", id: "kb-export" }, "Export boundary map (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-knowledge-boundary.json", JSON.stringify(B, null, 1), "application/json")) toast("Boundary exported"); });
  const goto = el("button", { class: "btn small ghost", type: "button" }, "Trace in the reasoning graph");
  goto.addEventListener("click", () => { focusNode(it.id); emit("goto", { ws: "reasoning" }); });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, B.note), cols, el("div", { class: "controls" }, exp)),
    it ? el("div", { class: "card", id: "kb-detail" }, el("h3", {}, it.statement), kv([["Region", B.region_labels[it.region]], ["Rule", `${it.rule}: ${B.rules[it.rule]}`],
      ["Why here", it.why], ["Status", statusPill(it.status)], ["Evidence", Object.entries(it.evidence || {}).map(([k, v]) => `${k} = ${typeof v === "number" ? +v.toPrecision(4) : v}`).join(", ") || "—"],
      ["Assumptions it depends on", it.n_assumptions ? el("ul", { class: "plain small" }, ...it.assumptions.map((a) => el("li", {}, a.label)), it.n_assumptions > it.assumptions.length ? el("li", { class: "faint" }, `+ ${it.n_assumptions - it.assumptions.length} more`) : null) : "—"],
      ["What could change it", el("ul", { class: "plain small" }, ...it.could_change_it.map((t) => el("li", {}, t.test ? `${t.hypothesis} · ${t.test} (${t.status}): ${t.rule}` : t.note)))],
      ["Limitations", el("ul", { class: "plain small" }, ...(it.limitations.length ? it.limitations : ["—"]).map((l) => el("li", {}, l)))]]),
      it.kind !== "question" ? el("div", { class: "controls" }, goto) : null) : null);
}

function stressView(d) {
  const claims = Object.keys(d.stress);
  if (!claims.includes(claim)) claim = claims[0];
  const sel = el("select", { id: "cx-claim", "aria-label": "Claim to stress-test" }, ...claims.map((q) => el("option", { value: q, selected: q === claim || null }, `${q}: ${d.stress[q].category}`)));
  sel.addEventListener("change", () => { claim = sel.value; renderClaims(); });
  const S0 = d.stress[claim];
  // a reproduction recorded in this session for this run settles the reproducibility mode (same rule as CLAIMX-1)
  const rep = (state.session?.debug || []).filter((x) => x.kind === "reproduction" && x.content_hash === state.inv.record.content_hash).pop();
  const S = rep ? { ...S0, modes: S0.modes.map((m) => m.mode !== "reproducibility" ? m : { ...m,
    result: ["exact reproduction", "numerically equivalent reproduction"].includes(rep.verdict) ? "pass" : rep.verdict === "blocked reproduction" ? "blocked" : "fail",
    detail: `${rep.verdict} (recorded in this session${rep.recorded_at_build ? "; replay recorded when the preview was built" : ""})` }) } : S0;
  const exp = el("button", { class: "btn small", type: "button", id: "cx-export" }, "Export stress-test report (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-stress-${claim}.json`, JSON.stringify(S, null, 1), "application/json")) toast("Report exported"); });
  return el("div", {}, el("div", { class: "card" }, el("div", { class: "controls" }, el("label", { for: "cx-claim" }, "Claim"), sel, exp),
    el("h3", {}, `“${S.statement}”`), el("p", {}, ...Object.entries(stressCounts(S)).map(([k, n]) => el("span", {}, outcomePill(k), ` ${n} `))),
    el("p", { class: "faint small" }, S.note)),
    table(["Mode", "Result", "Rule", "Detail"], S.modes.map((m) => el("tr", { "data-mode": m.mode }, el("th", { scope: "row" }, m.name), el("td", {}, outcomePill(m.result)),
      el("td", { class: "small" }, m.rule), el("td", { class: "small wrap" }, m.detail))), { id: "cx-table" }),
    rep ? null : el("p", { class: "faint small" }, "Reproducibility shows “not tested” until the run is re-executed (Scientific Debugger → Reproduce)."));
}

export function stressCounts(S) {
  const c = {};
  for (const m of S.modes) c[m.result] = (c[m.result] || 0) + 1;
  return c;
}

async function blindView(base) {
  const words = (await getSpecs()).frontier.review_causal_words;
  const B = overlayBlindspots(base, state.session, words);
  const exp = el("button", { class: "btn small", type: "button", id: "blind-export" }, "Export blindspot report (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-blindspots.json", JSON.stringify(B, null, 1), "application/json")) toast("Blindspot report exported"); });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, B.note), el("div", { class: "controls" }, exp),
    el("p", {}, ...Object.entries(B.counts).filter(([, n]) => n).map(([k, n]) => el("span", {}, outcomePill(k), ` ${n} `)),
      el("span", { class: "faint" }, ` of ${B.checks.length} defined checks`))),
    table(["Check", "State", "Rule", "What was found"], B.checks.map((r) => el("tr", { "data-blind": r.id }, el("th", { scope: "row" }, r.name), el("td", {}, outcomePill(r.state)),
      el("td", { class: "small" }, r.rule), el("td", { class: "small wrap" }, r.detail, r.items?.length ? el("div", { class: "faint mono" }, r.items.slice(0, 6).join(", ")) : null))), { id: "blind-table" }));
}
