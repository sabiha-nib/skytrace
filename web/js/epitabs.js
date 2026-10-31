// Phase 8 tabs inside earlier workspaces:
//   Knowledge Atlas → Evidence vault (VAULT-1 hash chain over the session history, with appended corrections)
//   Synthetic Observatory → Simulation audit (SIMCHECK-1)
//   Review Room → Review board (REVIEWX-1, eight automated perspectives, with your comments and responses)

import { api, STATIC } from "./api.js";
import { getEpistemic, getSpecs, state } from "./state.js";
import { verifyChain } from "./sessioncore.js";
import * as S from "./session.js";
import { download, el, toast } from "./util.js";
import { kv, outcomePill, table } from "./epiui.js";

// ------------------------------------------------------------------ evidence vault
export async function vaultView(rerender) {
  const s = state.session;
  if (!s) return el("p", { class: "empty" }, "No session yet: the evidence vault is the session's append-only history.");
  const V = await verifyChain(s.history);
  const seq = el("select", { id: "vault-seq", "aria-label": "Entry to correct" }, ...s.history.slice(-200).map((h) => el("option", { value: String(h.seq) }, `#${h.seq} ${h.kind}: ${h.summary.slice(0, 60)}`)));
  const txt = el("input", { type: "text", id: "vault-correction", placeholder: "Correction (the original entry is kept)", "aria-label": "Correction" });
  const add = el("button", { class: "btn", type: "button", id: "vault-correct" }, "Append correction");
  add.addEventListener("click", async () => {
    if (!txt.value.trim()) { toast("Write the correction"); return; }
    await S.update("vault.correction", `Correction to #${seq.value}: ${txt.value}`.slice(0, 300), (x) => x, `seq:${seq.value}`);
    toast("Correction appended; the original entry is unchanged"); rerender();
  });
  const exp = el("button", { class: "btn small", type: "button", id: "vault-export" }, "Export event history (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-evidence-history.json", JSON.stringify({ method: "VAULT-1", verification: V, history: s.history }, null, 1), "application/json")) toast("History exported"); });
  const corrections = new Map(s.history.filter((h) => h.kind === "vault.correction").map((h) => [h.ref, h]));
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Evidence vault"),
    el("p", { class: "muted" }, "Every action in this session is an append-only event. Each event carries a link: the SHA-256 of the previous link and the event's text, so an edited or deleted event breaks the chain. Corrections are new events that point at the old one; nothing is rewritten. A hash chain is not a signature: someone who recomputes every later link can hide an edit."),
    kv([["Events", String(s.history.length)], ["Links verified", el("span", { id: "vault-verified" }, `${V.verified} of ${V.links}`)],
      ["Broken links", el("span", { id: "vault-broken" }, V.broken.length ? V.broken.join(", ") : "none")],
      ["Chain start", V.anchor ? `entry ${V.anchor} (older entries were trimmed, so its link cannot be checked)` : "the first entry (checked against the genesis value)"],
      ["Unchained (older format)", String(V.unchained)]]),
    el("div", { class: "controls" }, seq, txt, add, exp)),
    table(["#", "When", "Event", "Summary", "Link"], s.history.slice(-80).reverse().map((h) => el("tr", { class: V.broken.includes(h.seq) ? "flag" : "" }, el("td", {}, String(h.seq)),
      el("td", { class: "small" }, h.at), el("td", { class: "small" }, h.kind), el("td", { class: "small wrap" }, h.summary, corrections.get(`seq:${h.seq}`) ? el("div", { class: "faint" }, `corrected later (#${corrections.get(`seq:${h.seq}`).seq})`) : null),
      el("td", { class: "mono small" }, h.h ? h.h.slice(0, 10) + "…" : "—"))), { id: "vault-table" }));
}

// ------------------------------------------------------------------ simulation audit
let lastAudit = null;
export async function simAuditView() {
  const sp = (await getSpecs()).frontier.synthetic;
  const tpl = el("select", { id: "sa-template", "aria-label": "Template to audit" }, ...sp.templates.map((t, i) => el("option", { value: String(i) }, t.title)));
  const go = el("button", { class: "btn primary", type: "button", id: "sa-run" }, STATIC ? "Show the recorded audit" : "Audit with three seeds");
  const out = el("div", { id: "sa-out" }, lastAudit ? auditResult(lastAudit) : null);
  go.addEventListener("click", async () => {
    if (!STATIC && !go.dataset.armed) { go.dataset.armed = "1"; go.textContent = "Confirm: generates three scenarios and runs the analysis on each (~15 s)"; return; }
    out.replaceChildren(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Generating each seed and running the pipeline…"));
    try {
      lastAudit = await api.simAudit(sp.templates[Number(tpl.value)].scenario);
      await S.log("synthetic.audit", `Simulation audit: ${Object.entries(lastAudit.repeated_seed_test.stable).map(([q, v]) => `${q} ${v ? "stable" : "unstable"}`).join(", ")}`, null, { create: true });
      out.replaceChildren(auditResult(lastAudit));
    } catch (e) { out.replaceChildren(el("p", { class: "withheld" }, e.message)); }
    delete go.dataset.armed; go.textContent = STATIC ? "Show the recorded audit" : "Audit with three seeds";
  });
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Simulation audit"),
    el("p", { class: "muted" }, "What a scenario assumes, and whether its verdicts survive independent noise (different seeds). A synthetic benchmark tests the software against its own generator; it is not an observational validation dataset."),
    el("div", { class: "controls" }, tpl, go)), out);
}

function auditResult(A) {
  if (A.status !== "completed") return el("p", { class: "withheld" }, (A.errors || []).join("; "));
  const R = A.repeated_seed_test;
  return el("div", { class: "card" }, el("h3", { id: "sa-verdict" }, "Repeated-seed test: " + Object.entries(R.stable).map(([q, v]) => `${q} ${v ? "stable" : "unstable"}`).join(", ")),
    A.recorded_at_build ? el("p", { class: "pill" }, "recorded when the preview was built") : null,
    table(["Seed", "Verdicts", "Refused exposures", "Record"], R.runs.map((r) => el("tr", {}, el("td", {}, String(r.seed)), el("td", {}, Object.entries(r.verdicts).map(([q, v]) => `${q}: ${v}`).join("; ")),
      el("td", {}, Object.entries(r.refused_exposures).map(([k, n]) => `${n} ${k}`).join(", ") || "none"), el("td", { class: "mono small" }, r.record_content_hash.slice(0, 12))))),
    kv([["Generator", `${A.generator} (${A.generator_version})`], ["Ground truth", JSON.stringify(A.ground_truth).slice(0, 300)], ["Noise assumptions", A.noise_assumptions.join("; ")],
      ["Physical assumptions", A.physical_assumptions.join("; ")], ["Simplifications", A.simplifications.join("; ")],
      ["Validity domain", Object.entries(A.validity_domain).map(([k, [lo, hi]]) => `${k} ${lo}–${hi}`).join("; ")], ["Expected limitations", A.expected_limitations.join("; ")],
      ["Kind", A.benchmark_kind], ["Rule", R.rule]]));
}

// ------------------------------------------------------------------ review board
export async function reviewBoardView(rerender) {
  const d = await getEpistemic();
  const RB = d.review;
  const comments = state.session?.reviews || [];
  const blocks = RB.perspectives.map((p) => el("details", { class: "card", "data-perspective": p.id, open: p.counts.fail || p.counts.warning ? "" : null },
    el("summary", {}, el("strong", {}, p.name), " ", ...Object.entries(p.counts).filter(([, n]) => n).map(([k, n]) => el("span", {}, outcomePill(k), ` ${n} `))),
    el("ul", { class: "plain" }, ...p.items.map((it) => {
      const mine = comments.filter((c) => c.item === it.id);
      const ta = el("input", { type: "text", "aria-label": `Comment on ${it.id}`, placeholder: "your review comment or response" });
      const kind = el("select", { "aria-label": "Comment kind" }, ...["comment", "response", "resolved"].map((k) => el("option", { value: k }, k)));
      const add = el("button", { class: "btn small ghost", type: "button" }, "Add");
      add.addEventListener("click", async () => {
        if (!ta.value.trim()) { toast("Write the comment"); return; }
        await S.update("review.comment", `Review ${kind.value} on ${it.id}`, (s) => {
          s.reviews = [...(s.reviews || []), { item: it.id, kind: kind.value, text: ta.value.slice(0, 1000), by: "you (no accounts)", at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-200);
          return s;
        }, it.id);
        rerender();
      });
      return el("li", { class: "rb-item", "data-rbitem": it.id }, el("div", { class: "next-head" }, outcomePill(it.outcome), el("strong", {}, it.source), el("span", { class: "small" }, it.rule)),
        el("p", { class: "small" }, it.detail), el("p", { class: "faint small mono" }, "Links: " + it.links.join(", ")),
        mine.length ? el("ul", { class: "plain small" }, ...mine.map((c) => el("li", {}, el("span", { class: "pill" }, c.kind), ` ${c.text} `, el("span", { class: "faint" }, c.at)))) : null,
        el("div", { class: "controls" }, kind, ta, add));
    }))));
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Review board"), el("p", { class: "muted" }, RB.note)), ...blocks);
}
