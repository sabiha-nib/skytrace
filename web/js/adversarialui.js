// Adversarial Science Lab (ASL-1), information analysis (INFO-1) and the Causality Workbench.
// Challenges come from documented rules over the recorded analysis; "open" means not yet examined, not "wrong".
// The causality tab separates what the pipeline's data flow implies (dependency, not causation), what competing
// explanations assume, and what you propose — every relationship carries one of those labels.

import { emit, getFrontier, getSpecs, state } from "./state.js";
import { overlayChallenges } from "./frontiercore.js";
import * as S from "./session.js";
import { loadFrontier, needRun } from "./horizonui.js";
import { clear, download, el, renderToken, toast, $ } from "./util.js";

let tab = "challenges", sevFilter = "all";
export function setAdversarialTab(t) { tab = t; }

export async function renderAdversarial() {
  const live = renderToken("adversarial");
  const body = $("#adversarial-body");
  clear(body);
  if (!state.inv) { needRun(body, "The laboratory challenges the recorded analysis: run or load one first."); return; }
  const f = await loadFrontier(body, "adversarial");
  if (!f || !live()) return;
  const tabs = el("div", { class: "tabs", role: "tablist", "aria-label": "Adversarial Science Lab" }, ...[["challenges", "Challenges"], ["ranking", "Test ranking (INFO-1)"], ["causal", "Causality workbench"]].map(([k, t]) => {
    const b = el("button", { type: "button", role: "tab", "aria-selected": String(tab === k), "data-atab": k }, t);
    b.addEventListener("click", () => { tab = k; renderAdversarial(); });
    return b;
  }));
  body.append(tabs);
  if (tab === "challenges") body.append(challengesView(f));
  else if (tab === "ranking") body.append(rankingView(f.info));
  else body.append(await causalView(f));
}

function challengesView(f) {
  const A = overlayChallenges(f.asl, state.session);
  const sev = ["all", ...A.challenges.map((c) => c.severity).filter((v, i, a) => a.indexOf(v) === i)];
  const exp = el("button", { class: "btn small", type: "button", id: "asl-export" }, "Export challenge report (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-challenges-${f.content_hash.slice(0, 12)}.json`, JSON.stringify(A, null, 1), "application/json")) toast("Challenge report exported"); });
  const list = A.challenges.filter((c) => sevFilter === "all" || c.severity === sevFilter);
  return el("div", {}, el("div", { class: "card" },
    el("p", { class: "muted" }, A.note),
    el("p", {}, ...Object.entries(A.counts).map(([k, v]) => el("span", { class: `pill sev-${k}` }, `${v} ${k}`))),
    el("details", {}, el("summary", {}, "Severity classes"), el("pre", { class: "wrap small" }, A.severity_rule)),
    el("div", { class: "controls" }, el("div", { class: "tagrow", "aria-label": "Filter by severity" }, ...sev.map((s) => {
      const b = el("button", { type: "button", class: "tag", "aria-pressed": sevFilter === s ? "true" : "false" }, s);
      b.addEventListener("click", () => { sevFilter = s; renderAdversarial(); });
      return b;
    })), exp)),
    el("ol", { class: "asl-list" }, ...list.map((c) => {
      const ack = el("button", { class: "btn small ghost", type: "button" }, c.status === "acknowledged" ? "Add another note" : "Acknowledge with a note");
      const ta = el("textarea", { rows: "2", "aria-label": `Your note on ${c.id}`, placeholder: "What did you check? (kept in the session)" });
      ack.addEventListener("click", async () => {
        const t = ta.value.trim();
        if (!t) { toast("Write what you checked first"); ta.focus(); return; }
        await S.update("challenge.note", `Note on challenge ${c.id}`, (s) => {
          s.annotations = [...s.annotations, { id: S.newId("a"), target: { kind: "challenge", id: c.id }, text: t.slice(0, 2000),
            created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-200);
          return s;
        }, c.id);
        toast("Noted; the challenge stays visible as acknowledged"); renderAdversarial();
      });
      return el("li", { class: `asl-item sev-${c.severity}`, "data-challenge": c.id },
        el("div", { class: "next-head" }, el("span", { class: `pill sev-${c.severity}` }, c.severity), el("span", { class: "pill" }, c.mode_name),
          el("strong", {}, c.issue), el("span", { class: `pill st-${c.status.replace(/ /g, "-")}` }, c.status)),
        el("dl", { class: "kv compact" }, el("dt", {}, "Evidence"), el("dd", { class: "wrap" }, c.evidence.join("; ") || "—"), el("dt", {}, "Rule"), el("dd", {}, c.rule),
          el("dt", {}, "Why it matters"), el("dd", {}, c.why), el("dt", {}, "Verification"), el("dd", {}, c.verification),
          c.notes ? el("dt", {}, "Your notes") : null, c.notes ? el("dd", {}, c.notes.join(" · ")) : null),
        el("div", { class: "controls" }, ta, ack));
    })));
}

function rankingView(I) {
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Which open test would best separate the competing explanations?"),
    el("p", { class: "muted" }, I.interpretation_limits),
    el("dl", { class: "kv compact" }, el("dt", {}, "Probability model"), el("dd", {}, I.probability_model === null ? "none — no numerical information gain is computed" : String(I.probability_model)),
      el("dt", {}, "Uncertainty model"), el("dd", {}, I.uncertainty_model), el("dt", {}, "Ranking rule"), el("dd", {}, I.ranking_rule),
      el("dt", {}, "Assumptions"), el("dd", {}, I.assumptions.join("; ")))),
    el("div", { class: "table-wrap card" }, el("table", { id: "info-table" }, el("thead", {}, el("tr", {}, ...["#", "Test", "Question", "Status", "Bears on (viable)", "Feasibility", "Route"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...I.candidates.map((c) => el("tr", {}, el("td", {}, String(c.rank)), el("td", {}, el("strong", {}, c.test), el("div", { class: "faint" }, c.description)), el("td", {}, c.question),
        el("td", {}, c.statuses.join(", ")), el("td", {}, c.bears_on.join(", ") + (c.bears_on_claim ? " (incl. the claim's own)" : "")), el("td", {}, c.feasibility), el("td", { class: "wrap" }, c.route)))))),
    el("div", { class: "card" }, el("h3", {}, "Hypothesis space"), ...I.hypothesis_space.map((q) => el("p", {}, el("strong", {}, q.question), ": ",
      q.explanations.map((h) => `${h.id} (${h.overall})`).join(" · ")))));
}

async function causalView(f) {
  const rec = state.inv.record;
  const ok = (st) => rec.events.some((e) => e.step === st && e.status === "ok");
  const flow = [["image files (SHA-256 in the manifest)", "per-exposure measurements", ok("measure") || rec.events.some((e) => e.step === "measure")],
    ["per-exposure measurements", "wavelength-matched comparisons (WLMATCH-2)", ok("pairs")], ["wavelength-matched comparisons", "brightness outcome (ASSESS-2)", ok("variability")],
    ["Gaia reference stars", "plate solutions", ok("astrometry") || ok("plate")], ["plate solutions + target positions", "motion fit", ok("astrometry")], ["motion fit", "motion outcome (ASSESS-2)", ok("astrometry")]];
  const disc = state.discovery?.data;
  const hyps = (f.info.hypothesis_space || []).flatMap((q) => q.explanations.map((h) => ({ ...h, question: q.question })));
  const user = state.session?.causal || [];
  const from = el("input", { type: "text", id: "causal-from", placeholder: "e.g. a calibration change in pass 3", "aria-label": "Proposed factor" });
  const rel = el("select", { id: "causal-rel", "aria-label": "Relationship you propose" }, ...["proposed cause of", "possible confounder of", "co-occurs with"].map((r) => el("option", { value: r }, r)));
  const to = el("input", { type: "text", id: "causal-to", placeholder: "e.g. the flux difference in D1", "aria-label": "Affected quantity" });
  const add = el("button", { class: "btn small", type: "button", id: "causal-add" }, "Add proposed relationship");
  add.addEventListener("click", async () => {
    const a = from.value.trim(), b = to.value.trim();
    if (!a || !b) { toast("Name both ends of the relationship"); return; }
    await S.update("causal.propose", `Proposed: ${a} — ${rel.value} — ${b}`.slice(0, 280), (s) => {
      s.causal = [...(s.causal || []), { id: S.newId("c"), from: a.slice(0, 200), to: b.slice(0, 200), relation: rel.value, label: "user-proposed",
        created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-30);
      return s;
    });
    renderAdversarial();
  });
  const words = (await getSpecs()).frontier.review_causal_words;
  const notes = (state.session?.notebook || []).filter((b) => b.author === "user" && words.some((w) => (b.text || "").toLowerCase().includes(w)));
  return el("div", {},
    el("div", { class: "card" }, el("h3", {}, "Model-derived dependencies"), el("p", { class: "muted" }, "How the pipeline's outputs depend on its inputs (data flow). A dependency is not a causal claim about the sky."),
      el("ul", { class: "causal-list" }, ...flow.map(([a, b, done]) => el("li", { class: done ? "" : "faint" }, a, el("span", { class: "rel dep" }, " ⟶ feeds "), b,
        el("span", { class: "pill" }, "model-derived"), done ? null : el("span", { class: "faint" }, " (not produced in this run)"))))),
    el("div", { class: "card" }, el("h3", {}, "Alternative causal structures (assumption-based)"),
      el("p", { class: "muted" }, "Each competing explanation proposes a different cause for the same values. Its status is a rule-based test result, not support for causation."),
      el("ul", { class: "causal-list" }, ...hyps.map((h) => el("li", {}, el("strong", {}, h.id), ": ", h.statement, el("span", { class: "pill" }, "assumption-based"), el("span", { class: "pill" }, h.overall))))),
    el("div", { class: "card" }, el("h3", {}, "Your proposed relationships"),
      el("p", { class: "muted" }, "Labelled user-proposed. Skytrace does not test causation; a proposal here is a hypothesis to examine, and no arrow implies that it holds."),
      el("div", { class: "controls" }, from, rel, to, add),
      user.length ? el("ul", { class: "causal-list", id: "causal-user" }, ...user.map((c) => el("li", {}, c.from, el("span", { class: "rel" }, ` — ${c.relation} — `), c.to, el("span", { class: "pill" }, c.label))))
        : el("p", { class: "faint" }, "None yet.")),
    el("div", { class: "card" }, el("h3", {}, "Causal claim warnings"),
      notes.length ? el("ul", { class: "limits" }, ...notes.map((b) => el("li", {}, `“${(b.text || "").slice(0, 160)}” — contains causal or discovery language (${words.filter((w) => (b.text || "").toLowerCase().includes(w)).join(", ")}). Correlation or temporal order alone does not establish a cause.`)))
        : el("p", { class: "muted" }, "None of your notebook text uses the listed causal or discovery words.")),
    disc ? null : null);
}

export { getFrontier, emit };
