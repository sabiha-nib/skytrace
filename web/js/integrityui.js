// Integrity Firewall (INTEG-1): export-readiness checks on the investigation report, your notebook, the discovery story or
// any text you paste. Advice only — nothing is blocked and nothing is rewritten. Runs in the browser with the same rules
// as the server (epistemiccore.integrityCheck, parity-tested).

import { api } from "./api.js";
import { getSpecs, state } from "./state.js";
import { integrityCheck } from "./epistemiccore.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { loadEpistemic, needRun, outcomePill, syntheticNote, table } from "./epiui.js";

let source = "report", pasted = "", last = null;

function notebookText(s) {
  return (s?.notebook || []).map((b) => (b.type === "heading" ? `## ${b.text || ""}` : (b.author === "assistant-draft" ? "[draft] " : "") + (b.text || ""))).join("\n\n");
}

export async function renderIntegrity() {
  const live = renderToken("integrity");
  const body = $("#integrity-body");
  clear(body);
  if (!state.inv) { needRun(body, "Texts are checked against a recorded analysis."); return; }
  const d = await loadEpistemic(body, "integrity");
  if (!d || !live()) return;
  const spec = (await getSpecs()).epistemic.integrity;
  const sel = el("select", { id: "integ-source", "aria-label": "Document to check" }, ...[["report", "Investigation report (Report Studio)"], ["notebook", "Your research notebook"],
    ["paste", "Text you paste"]].map(([k, t]) => el("option", { value: k, selected: k === source || null }, t)));
  const area = el("textarea", { id: "integ-text", rows: "8", "aria-label": "Text to check", placeholder: "Paste the text you intend to share…" }, pasted);
  area.hidden = source !== "paste";
  sel.addEventListener("change", () => { source = sel.value; area.hidden = source !== "paste"; });
  area.addEventListener("input", () => { pasted = area.value; });
  const out = el("div", { id: "integ-out" }, last ? result(last) : null);
  const go = el("button", { class: "btn primary", type: "button", id: "integ-run" }, "Check export readiness");
  go.addEventListener("click", async () => {
    let text;
    try {
      text = source === "report" ? await api.report(state.inv.investigation_id) : source === "notebook" ? notebookText(state.session) : pasted;
    } catch (e) { clear(out).append(el("p", { class: "withheld" }, e.message)); return; }
    if (!text || !text.trim()) { toast(source === "notebook" ? "Your notebook is empty" : "Nothing to check"); return; }
    last = { source, ...integrityCheck(text, d.facts, spec) };
    await S.log("integrity.check", `Integrity firewall on the ${source}: ${last.outcome}`, null, { create: true });
    clear(out).append(result(last));
  });
  body.append(syntheticNote(d), el("div", { class: "card" }, el("p", { class: "muted" }, "Before you share a report, claim or conclusion, the firewall checks it against the recorded investigation: synthetic data labelled, numbers present in the record, the run cited, outcomes matching the record, units, no probability language, scenarios labelled, limitations acknowledged, valid provenance, compatible comparisons, real methods, no overstatement. It never blocks an export and never changes your text."),
    el("div", { class: "controls" }, el("label", { for: "integ-source" }, "Document"), sel, go), area,
    el("p", { class: "faint small" }, `The investigation report itself was checked when the record was analysed: ${d.report_check.outcome}.`)), out);
}

function result(R) {
  const exp = el("button", { class: "btn small", type: "button", id: "integ-export" }, "Export readiness report (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-export-readiness.json", JSON.stringify(R, null, 1), "application/json")) toast("Readiness report exported"); });
  return el("div", { class: "card" }, el("h3", { id: "integ-outcome" }, outcomePill(R.outcome), ` ${R.outcome}`),
    el("p", { class: "small" }, `${R.n_high} high-severity and ${R.n_warning} warning item(s). ${R.note}`),
    table(["Check", "Severity", "Result", "Detail"], R.checks.map((c) => el("tr", { "data-icheck": c.id, class: c.ok ? "" : "flag" }, el("th", { scope: "row" }, `${c.id} · ${c.name}`),
      el("td", {}, c.severity), el("td", {}, outcomePill(c.ok ? "pass" : c.severity === "high" ? "fail" : "warning")),
      el("td", { class: "small wrap" }, c.detail, c.items?.length ? el("div", { class: "faint mono" }, c.items.slice(0, 8).join(", ")) : null))), { id: "integ-table" }),
    el("div", { class: "controls" }, exp));
}
