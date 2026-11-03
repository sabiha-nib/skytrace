// Review Room (REVIEW-1), Reproducibility Challenge (REPRO-1) and Discovery Story.
// Review roles are software rule sets, not people. The audit's verdict follows one stated rule. The story is written
// only from recorded outcomes and their own statements: an inconclusive result stays inconclusive.

import { reviewBoardView } from "./epitabs.js";
import { api, STATIC } from "./api.js";
import { emit, getDiscovery, getFrontier, getSpecs, state } from "./state.js";
import { overlayChallenges, overlayReview } from "./frontiercore.js";
import { parse } from "./planner.js";
import * as S from "./session.js";
import { loadFrontier, needRun } from "./horizonui.js";
import { categoryLabel, clear, download, el, questionLabel, renderToken, toast, $ } from "./util.js";
import { agentsCard } from "./universalui.js";

let tab = "review", lastAudit = null;
export function setReviewTab(t) { tab = t; }

export async function renderReview() {
  const live = renderToken("review");
  const body = $("#review-body");
  clear(body);
  if (!state.inv) { needRun(body, "The Review Room reads the recorded analysis, its checks and your session."); return; }
  const f = await loadFrontier(body, "review");
  if (!f || !live()) return;
  body.append(el("div", { class: "tabs", role: "tablist", "aria-label": "Review Room" }, ...[["review", "Review"], ["board", "Review board"], ["repro", "Reproducibility Challenge"], ["story", "Discovery Story"], ["agents", "Role agents"]].map(([k, t]) => {
    const b = el("button", { type: "button", role: "tab", "aria-selected": String(tab === k), "data-rtab": k }, t);
    b.addEventListener("click", () => { tab = k; renderReview(); });
    return b;
  })));
  if (tab === "review") body.append(await reviewView(f));
  else if (tab === "board") body.append(await reviewBoardView(renderReview));
  else if (tab === "repro") body.append(reproView(f));
  else if (tab === "agents") agentsCard(body);
  else body.append(await storyView(f));
}

async function reviewView(f) {
  const sp = await getSpecs();
  const q = state.session?.question?.text || "";
  const intent = q ? parse(sp.planner, q, state.targets.flatMap((t) => [t.target_id, t.name])).kind : null;
  const R = overlayReview(f.review, state.session, intent, sp.frontier.review_causal_words);
  const roles = Object.keys(R.counts);
  const exp = el("button", { class: "btn small", type: "button", id: "review-export" }, "Export review report (Markdown)");
  exp.addEventListener("click", async () => {
    const L = [`# Review report — ${state.targetId}`, "", `Run ${f.content_hash} · ${R.method}. ${R.note}`, ""];
    for (const r of roles) {
      L.push(`## ${R.findings.find((x) => x.role === r)?.role_name || r}`, "");
      for (const x of R.findings.filter((y) => y.role === r)) L.push(`- **${x.outcome}** — ${x.check}: ${x.detail} _(cites: ${x.cites.join(", ")})_`);
      L.push("");
    }
    if (await download(`skytrace-review-${f.content_hash.slice(0, 12)}.md`, L.join("\n"), "text/markdown")) { await S.log("review.export", "Review report exported", null, { create: true }); toast("Review report exported"); }
  });
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, R.note),
    el("p", {}, ...roles.map((r) => el("span", { class: "pill" }, `${r}: ${R.counts[r].met} met · ${R.counts[r]["not met"]} not met · ${R.counts[r]["not checked"]} not checked`))),
    el("div", { class: "controls" }, exp)),
    ...roles.map((r) => el("div", { class: "card" }, el("h3", {}, R.findings.find((x) => x.role === r)?.role_name || r),
      el("ul", { class: "review-list" }, ...R.findings.filter((x) => x.role === r).map((x) => el("li", { class: `rv-${x.outcome.replace(/ /g, "-")}` },
        el("span", { class: "pill" }, x.outcome), el("strong", {}, x.check), el("div", {}, x.detail), el("div", { class: "faint small" }, `cites: ${x.cites.join(", ")}`)))))));
}

function reproView(f) {
  const A = lastAudit && lastAudit.content_hash === f.content_hash ? lastAudit : f.repro;
  const run = el("button", { class: "btn primary", type: "button", id: "repro-run" }, STATIC ? "Show the re-execution recorded at build time" : "Re-execute and audit");
  run.addEventListener("click", async () => {
    if (!STATIC && !run.dataset.armed) { run.dataset.armed = "1"; run.textContent = "Confirm: re-runs the pipeline (a few seconds)"; return; }
    run.disabled = true; run.textContent = "Running…";
    try {
      lastAudit = await api.reproduce(state.inv.investigation_id);
      await S.log("repro.run", `REPRO-1: ${lastAudit.verdict}${lastAudit.recorded_at_build ? " (recorded at build)" : ""}`, null, { create: true });
    } catch (e) { toast(e.message, 7000); }
    renderReview();
  });
  const exp = el("button", { class: "btn small", type: "button", id: "repro-export" }, "Export audit (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-repro-${A.content_hash.slice(0, 12)}.json`, JSON.stringify(A, null, 1), "application/json")) toast("Audit exported"); });
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, `Verdict: ${A.verdict}`), A.recorded_at_build ? el("p", {}, el("span", { class: "pill" }, "re-execution recorded when the preview was built")) : null,
    el("pre", { class: "wrap small" }, A.verdict_rule), el("p", { class: "faint" }, `Tolerance: ${A.tolerance}. Importing a record never counts as reproducing it.`),
    el("div", { class: "controls" }, run, exp)),
    el("div", { class: "card table-wrap" }, el("table", { id: "repro-table" }, el("thead", {}, el("tr", {}, ...["Check", "Rule", "Outcome", "Detail"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...A.checks.map((c) => el("tr", { class: `rp-${c.outcome.replace(/ /g, "-")}` }, el("th", { scope: "row" }, `${c.id} · ${c.name}`), el("td", { class: "faint" }, c.rule),
        el("td", {}, el("strong", {}, c.outcome)), el("td", { class: "wrap" }, c.detail)))))));
}

// ---------------------------------------------------------------- Discovery Story
async function storyView(f) {
  const d = await getDiscovery();
  const m = state.model;
  const s = state.session;
  const A = overlayChallenges(f.asl, s);
  const syn = m.synthetic;
  const outs = m.outcomes;
  const q = s?.question?.text;
  const pos = outs.filter((o) => ["variability_candidate", "motion_detected", "motion_inconsistent"].includes(o.category));
  const answered = d.questions.filter((x) => x.status !== "not answerable").length;
  const ch = [];
  ch.push(["1. The research question", q ? `“${q}”` : "No research question was recorded in the session; the story follows the standard questions of the analysis."]);
  ch.push(["2. Motivation", `Repeated SPHEREx-like observations of ${state.target?.target?.name || state.targetId} allow a comparison over time. ` + (syn ? "These are SYNTHETIC test data generated by code: nothing here is an astronomical result." : "")]);
  const inv = d.inventory.summary || {};
  ch.push(["3. The available observations", `${inv.n_included ?? "—"} included observations (${inv.n_excluded ?? 0} excluded at selection) on ${(inv.detectors || []).join(", ") || "—"}, ` +
    `dates ${(inv.dates || []).slice(0, 1).join("")}–${(inv.dates || []).slice(-1).join("")}; ${inv.n_items ?? "—"} evidence items in the inventory; ${answered} of ${d.questions.length} standard questions are answerable with these data.`]);
  ch.push(["4. Methods", `Recorded method versions: ${Object.entries(state.inv.record.parameters.methods || {}).map(([k, v]) => `${k} ${Array.isArray(v) ? v.join("/") : v}`).join("; ")}. Decisions use ASSESS-2 thresholds fixed before the data were examined.`]);
  ch.push(["5. Results", outs.map((o) => `${questionLabel(o.question)}: ${categoryLabel(o.category)} — ${o.statement}`).join(" ")]);
  ch.push(["6. The evidence", (f.spe.layers[4].summary.claims || []).map((c) => `${c.id}: ${c.direct} directly linked item(s)${c.flags ? `, ${c.flags} flag(s)` : ""}`).join("; ") +
    `. ${f.spe.layers[4].summary.contradictions} contradiction(s) found by the ledger's fixed rules.`]);
  ch.push(["7. The uncertainty", `${d.uncertainty.unquantified.length} effect(s) are named but not quantified (${d.uncertainty.unquantified.map((u) => u.name).join(", ")}); the sensitivities above bound what could have been detected.`]);
  const alt = f.info.hypothesis_space.flatMap((x) => x.explanations.filter((h) => !["V-INTRINSIC", "M-CATALOGUE"].includes(h.id) && h.overall !== "contradicted").map((h) => `${h.id} (${h.overall})`));
  ch.push(["8. Alternative explanations", alt.length ? `Not ruled out: ${alt.join(", ")}. ` + (pos.length ? "The positive outcome remains a candidate while these stand." : "") : "Every competing explanation was contradicted by a recorded test."]);
  ch.push(["9. Limitations", [...new Set(outs.flatMap((o) => o.limitations))].slice(0, 6).join(" ") + ` ${A.counts.critical} critical and ${A.counts.major} major open challenge(s) remain.`]);
  const top = f.info.candidates[0];
  ch.push(["10. The next research question", top ? `What would ${top.test} (${top.description}) say about ${top.bears_on.join(", ")}? (${top.feasibility}; INFO-1 rank 1)` : "No open test remains in the hypothesis space."]);
  const timeline = (s?.history || []).slice(-12);
  const md = [`# ${state.target?.target?.name || state.targetId}: investigation story`, "", syn ? "> SYNTHETIC TEST DATA — generated by code; not an astronomical result." : "", "",
    `Run ${f.content_hash}${s ? ` · session ${s.session_id} (${s.content_hash || "unsaved"})` : ""}. Generated by Skytrace from recorded values only.`, "",
    ...ch.flatMap(([h, t]) => [`## ${h}`, "", t, ""]), timeline.length ? "## Timeline" : "", ...timeline.map((h) => `- ${h.at} — ${h.summary}`)].join("\n");
  const exp = el("button", { class: "btn small", type: "button", id: "story-export" }, "Export story (Markdown)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-story-${f.content_hash.slice(0, 12)}.md`, md, "text/markdown")) { await S.log("story.export", "Discovery Story exported", null, { create: true }); toast("Story exported"); } });
  const toNb = el("button", { class: "btn small ghost", type: "button" }, "Copy into the notebook as a draft");
  toNb.addEventListener("click", async () => {
    const { insertDrafts } = await import("./notebook.js");
    await insertDrafts(ch.map(([h, t]) => ({ type: "paragraph", text: `${h}\n${t}`.slice(0, 5000) })));
    toast("Story added to the notebook as assistant drafts");
  });
  return el("div", { class: "story" }, el("div", { class: "card" }, el("p", { class: "muted" }, "Written from the recorded outcomes and their own statements; inconclusive results stay inconclusive. Hashes identify exactly what the story describes."),
    syn ? el("p", { class: "banner syn" }, "SYNTHETIC test data: nothing in this story is an astronomical result.") : null, el("div", { class: "controls" }, exp, toNb)),
    ...ch.map(([h, t]) => el("section", { class: "card story-ch" }, el("h3", {}, h), el("p", {}, t))),
    timeline.length ? el("div", { class: "card" }, el("h3", {}, "Investigation timeline (this session)"), el("ol", { class: "plain small" }, ...timeline.map((h) => el("li", {}, `${h.at.slice(0, 16).replace("T", " ")} — ${h.summary}`)))) : null);
}

export { emit, getFrontier };
