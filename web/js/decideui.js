// Questions & next steps: NEXT-X decision records (NEXTX-1) and the Question Forge (QFORGE-1).
// Recommendations follow one stated ordering rule and say why the items below were not placed higher; no optimality is
// claimed. Every question cites the record item that prompted it.

import { emit, state } from "./state.js";
import { setPlannerQuestion } from "./plannerui.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, syntheticNote, tabs } from "./epiui.js";

let tab = "next", qcat = "all";
export function setDecideTab(t) { tab = t; }

export async function renderDecide() {
  const live = renderToken("decide");
  const body = $("#decide-body");
  clear(body);
  if (!state.inv) { needRun(body, "Decisions and questions come from a recorded analysis."); return; }
  const d = await loadEpistemic(body, "decide");
  if (!d || !live()) return;
  body.append(syntheticNote(d), tabs("Decisions", [["next", "Next steps (NEXT-X)"], ["questions", "Question Forge"]], tab, "data-qtab-epi", (k) => { tab = k; renderDecide(); }));
  body.append(tab === "next" ? nextView(d.next) : questionView(d.questions));
}

function nextView(N) {
  const exp = el("button", { class: "btn small", type: "button", id: "nx-export" }, "Export decision record (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-decision-record.json", JSON.stringify(N, null, 1), "application/json")) toast("Decision record exported"); });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, N.note), el("p", { class: "small" }, "Ordering rule: " + N.order_rule), el("div", { class: "controls" }, exp)),
    el("ol", { class: "nx-list", id: "nx-list" }, ...N.recommendations.map((r) => {
      const rec = el("button", { class: "btn small ghost", type: "button" }, "Record this decision");
      rec.addEventListener("click", async () => {
        await S.log("decision.record", `Decision: ${r.action}`.slice(0, 280), r.id, { create: true });
        toast("Decision recorded in the session history");
      });
      return el("li", { class: "nx-item", "data-nx": r.id }, el("div", { class: "next-head" }, el("span", { class: "pill" }, `#${r.rank}`), el("strong", {}, r.action),
        el("span", { class: "pill" }, r.feasibility), el("span", { class: "pill faint" }, r.kind)),
        kv([["Reasoning", r.reasoning], ["Bears on", r.claim], ["Evidence used", r.evidence.join(", ") || "—"], ["Needs", r.inputs || "—"], ["Limitations", r.limitations],
          ["Why ranked here", r.ranking_reason], r.why_not_higher ? ["Why not higher", r.why_not_higher] : null]), el("div", { class: "controls" }, rec));
    })));
}

function questionView(Q) {
  const cats = ["all", ...Q.categories.filter((c) => Q.counts[c])];
  const filt = el("div", { class: "tagrow", "aria-label": "Question category" }, ...cats.map((c) => {
    const b = el("button", { type: "button", class: "tag", "aria-pressed": String(qcat === c), "data-qcat": c }, c === "all" ? "all" : `${c} (${Q.counts[c]})`);
    b.addEventListener("click", () => { qcat = c; renderDecide(); });
    return b;
  }));
  const list = Q.questions.filter((q) => qcat === "all" || q.category === qcat);
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, Q.note), filt),
    el("ol", { class: "nx-list", id: "qf-list" }, ...list.map((q) => {
      const plan = el("button", { class: "btn small ghost", type: "button" }, "Plan this question");
      plan.addEventListener("click", () => { setPlannerQuestion(q.question); emit("goto", { ws: "planner" }); });
      return el("li", { class: "nx-item", "data-qf": q.id }, el("div", { class: "next-head" }, el("span", { class: "pill" }, q.category), el("strong", {}, q.question)),
        kv([["Prompted by", q.prompted_by], ["Motivation", q.motivation], ["Available", q.available.join("; ") || "—"], ["Missing", q.missing.join("; ") || "—"],
          ["Possible method", q.method], ["Expected output", q.expected], ["Limitations", (q.limitations || []).join("; ") || "—"]]), el("div", { class: "controls" }, plan));
    })));
}
