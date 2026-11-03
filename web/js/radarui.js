// Discovery Radar (RADAR-1): research opportunities with their reasons, evidence, data needs, method, limits and
// whether they can run now. Items whose pair was already examined in this session are marked so (session data);
// the list itself is computed by the server (or recorded at build time for the static preview).

import { emit, getResearch, state } from "./state.js";
import * as S from "./session.js";
import { execute } from "./executor.js";
import { clear, el, renderToken, toast, $ } from "./util.js";
import { radarExtras } from "./universalui.js";

const SIGNAL = { R1: "significant pair to inspect", R2: "unresolved explanation", R3: "untestable explanation", R4: "unused measurements",
                 R5: "sensitivity not examined", R6: "evidence conflict", R7: "data-quality gap", R8: "unobserved interval", R9: "relationship gap" };
let filter = "all";

export async function renderRadar() {
  const live = renderToken("radar");
  const body = $("#radar-body");
  clear(body);
  if (!state.inv) {
    body.append(el("div", { class: "empty" }, el("h3", {}, state.target ? "Run the analysis first" : "No stored observations for this target"),
      el("p", {}, "The radar reads the recorded analysis, the quality checks and the evidence ledger."), state.target ? el("button", { class: "btn primary", onclick: () => emit("run") }, "Run analysis") : null));
    return;
  }
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Scanning…");
  body.append(holder);
  let r;
  try { r = await getResearch(); } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return; }
  if (state.ws !== "radar" || !live()) return;
  holder.remove();
  S.log("radar.view", "Discovery Radar opened");
  const R = r.radar;
  const examined = new Set(state.session?.examined || []);
  const sigs = [...new Set(R.items.map((x) => x.signal))];
  const fsel = el("div", { class: "tagrow", role: "group", "aria-label": "Filter by signal" }, ...["all", "runnable", ...sigs].map((s) => {
    const b = el("button", { type: "button", class: "tag", "aria-pressed": filter === s ? "true" : "false" }, s === "all" ? "all" : s === "runnable" ? "can run now" : `${s} · ${SIGNAL[s]}`);
    b.addEventListener("click", () => { filter = s; renderRadar(); });
    return b;
  }));
  const items = R.items.filter((x) => filter === "all" || (filter === "runnable" ? x.can_run_now : x.signal === filter));
  body.append(el("div", { class: "card" }, el("h3", {}, `${R.method}: ${R.items.length} opportunities`),
    el("p", { class: "muted" }, `${R.note}. Ranking rule: those that can run now first, then by signal in the order ${R.order.join(" → ")}.`), fsel),
    el("ol", { class: "radar-list" }, ...items.map((x) => {
      const pairKey = x.refs.length === 2 ? `${x.refs[0]}|${x.refs[1]}` : null;
      const seen = pairKey && examined.has(pairKey);
      const act = x.action && x.can_run_now ? el("button", { class: "btn small", type: "button" }, actionLabel(x)) : null;
      act?.addEventListener("click", async () => {
        try {
          if (x.action === "inspect_pair") await execute("inspect_pair", { a: x.refs[0], b: x.refs[1] });
          else if (x.action === "inspect_ledger") emit("goto", { ws: "graph", tab: x.signal === "R6" ? "contradictions" : "completeness" });
          else if (x.action === "evaluate_hypotheses") emit("goto", { ws: "arena" });
          else if (x.action === "check_quality") emit("goto", { ws: "quality", qtab: "checks" });
          else if (x.action === "run_stability") emit("goto-lab", "rerun-stability");
          else await execute(x.action, {});
          await S.log("radar.act", `Radar: ${x.proposal.slice(0, 200)}`, x.id);
        } catch (e) { toast(e.message, 6000); }
      });
      return el("li", { class: `radar-item${x.can_run_now ? "" : " blocked"}`, "data-signal": x.signal },
        el("div", { class: "next-head" }, el("span", { class: "rank" }, `#${x.rank}`), el("strong", {}, x.proposal),
          el("span", { class: `pill ${x.can_run_now ? "archive" : "none"}` }, x.can_run_now ? "can run now" : x.run_note || "cannot run here"),
          seen ? el("span", { class: "pill" }, "examined in this session") : null),
        el("dl", { class: "kv compact" }, el("dt", {}, "Why"), el("dd", {}, x.why), el("dt", {}, "Evidence"), el("dd", { class: "wrap" }, x.evidence.slice(0, 6).join(", ") + (x.evidence.length > 6 ? ` … (+${x.evidence.length - 6})` : "")),
          el("dt", {}, "Data needed"), el("dd", {}, x.data_needed), el("dt", {}, "Method"), el("dd", {}, x.action || "no implemented action"),
          el("dt", {}, "Cannot establish"), el("dd", {}, x.cannot_establish), el("dt", {}, "Rank"), el("dd", { class: "faint" }, x.rank_reason)),
        act ? el("div", { class: "controls" }, act) : null);
    })));
  radarExtras(body);
}

function actionLabel(x) {
  return { inspect_pair: "Open the pair", inspect_ledger: "Open in the ledger", evaluate_hypotheses: "Open the explanation", check_quality: "Open the check",
           run_stability: "Run the stability check" }[x.action] || "Run";
}
