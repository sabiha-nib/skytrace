// Reasoning Lab (ARG-1): structured scientific arguments. An argument has a claim, supporting and contradicting evidence
// (references to objects of the reasoning graph), assumptions, an inference rule, limitations, alternative interpretations
// and open questions. Arguments can be branched, compared, challenged step by step and exported as a map.
// Two separate verdicts are shown: whether the argument is well-formed (every step has premises, every reference resolves)
// and what empirical status its evidence has (from EPI-1). A well-formed argument can rest on false premises.

import { state } from "./state.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, outcomePill, statusPill, syntheticNote, table } from "./epiui.js";

export const RULES = ["threshold rule (a stated criterion applied to recorded values)", "elimination (alternatives contradicted by tests)", "inference to the best explanation",
  "consistency check (agreement with an external value)", "analogy with a known case"];
let sel = null, cmpWith = null;

export function assess(arg, graph) {
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]));
  const refs = [...arg.support, ...arg.contra, ...arg.assumptions.filter((a) => a.ref).map((a) => a.ref)];
  const unresolved = refs.filter((r) => !nodes.has(r));
  const problems = [];
  if (!arg.claim.trim()) problems.push("no claim");
  if (!arg.support.length) problems.push("no supporting evidence (the claim has no premise)");
  if (!arg.rule) problems.push("no inference rule");
  if (unresolved.length) problems.push(`${unresolved.length} reference(s) do not resolve: ${unresolved.slice(0, 3).join(", ")}`);
  const st = arg.support.filter((r) => nodes.has(r)).map((r) => nodes.get(r).status);
  const weakest = ["unsupported", "unknown", "hypothesized", "assumed", "user-authored", "simulated", "model-dependent", "derived", "measured", "directly recorded"].find((s) => st.includes(s));
  return { well_formed: !problems.length, problems, support_statuses: st, weakest_support: weakest || null, contradicting: arg.contra.length,
    empirical: !arg.support.length ? "unsupported" : arg.contra.length ? "contested by recorded evidence" : `rests on ${weakest} evidence`,
    note: "Well-formed means the structure is complete; it says nothing about whether the premises are true." };
}

export async function renderArgue() {
  const live = renderToken("argue");
  const body = $("#argue-body");
  clear(body);
  if (!state.inv) { needRun(body, "Arguments cite objects of a recorded analysis."); return; }
  const d = await loadEpistemic(body, "argue");
  if (!d || !live()) return;
  const args = state.session?.arguments || [];
  if (!sel || !args.find((a) => a.id === sel)) sel = args[args.length - 1]?.id || null;
  const list = el("ul", { class: "plain", id: "arg-list" }, ...args.map((a) => {
    const b = el("button", { type: "button", class: `linkish${a.id === sel ? " current" : ""}`, "data-arg": a.id }, `${a.title || a.claim.slice(0, 60)}${a.parent ? " (branch)" : ""}`);
    b.addEventListener("click", () => { sel = a.id; renderArgue(); });
    return el("li", {}, b);
  }));
  body.append(syntheticNote(d), el("div", { class: "card" }, el("p", { class: "muted" }, "Build an inspectable argument from the recorded evidence. Logical validity and empirical truth are judged separately: a well-formed argument can still depend on a false assumption or thin evidence."),
    args.length ? list : el("p", { class: "faint" }, "No argument yet."), newForm(d)));
  const a = args.find((x) => x.id === sel);
  if (a) body.append(argView(a, d, args));
}

function newForm(d) {
  const claimSel = el("select", { id: "arg-claim-ref", "aria-label": "Start from a recorded claim" }, el("option", { value: "" }, "— start from a recorded claim (optional) —"),
    ...d.graph.nodes.filter((n) => n.kind === "claim").map((n) => el("option", { value: n.id }, n.label.slice(0, 90))));
  const claim = el("input", { type: "text", id: "arg-claim", placeholder: "Claim", "aria-label": "Claim" });
  claimSel.addEventListener("change", () => { const n = d.graph.nodes.find((x) => x.id === claimSel.value); if (n) claim.value = n.label; });
  const go = el("button", { class: "btn primary", type: "button", id: "arg-new" }, "Create argument");
  go.addEventListener("click", async () => {
    if (!claim.value.trim()) { toast("State the claim"); return; }
    const id = S.newId("arg");
    await S.update("argument.create", `Argument created: ${claim.value}`.slice(0, 280), (s) => {
      s.arguments = [...(s.arguments || []), { id, title: claim.value.slice(0, 80), claim: claim.value.slice(0, 500), claim_ref: claimSel.value || null, support: [], contra: [],
        assumptions: [], rule: "", limitations: [], alternatives: [], questions: [], disputes: [], parent: null, created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }].slice(-30);
      return s;
    }, id);
    sel = id; renderArgue();
  });
  return el("div", { class: "controls" }, claimSel, claim, go);
}

function argView(a, d, args) {
  const nodes = new Map(d.graph.nodes.map((n) => [n.id, n]));
  const A = assess(a, d.graph);
  const pick = (id, label, kinds) => el("select", { id, "aria-label": label }, el("option", { value: "" }, label),
    ...d.graph.nodes.filter((n) => kinds.includes(n.kind)).slice(0, 200).map((n) => el("option", { value: n.id }, `${n.kind}: ${n.label.slice(0, 80)}`)));
  const sup = pick("arg-add-support", "add supporting evidence…", ["measurement", "derived", "inference", "claim", "observation"]);
  const con = pick("arg-add-contra", "add contradicting evidence…", ["contradiction", "hypothesis", "inference", "derived", "limitation"]);
  const asm = pick("arg-add-asm", "add an assumption…", ["assumption", "model"]);
  const rule = el("select", { id: "arg-rule", "aria-label": "Inference rule" }, el("option", { value: "" }, "inference rule…"), ...RULES.map((r) => el("option", { value: r, selected: a.rule === r || null }, r)));
  const txt = (id, ph) => el("input", { type: "text", id, placeholder: ph, "aria-label": ph });
  const lim = txt("arg-add-lim", "add a limitation"), alt = txt("arg-add-alt", "add an alternative interpretation"), oq = txt("arg-add-q", "add an open question");
  const mut = async (kind, summary, fn) => { await S.update(kind, summary, (s) => { s.arguments = s.arguments.map((x) => (x.id === a.id ? fn(structuredClone(x)) : x)); return s; }, a.id); renderArgue(); };
  const addBtn = el("button", { class: "btn", type: "button", id: "arg-apply" }, "Add");
  addBtn.addEventListener("click", async () => {
    await mut("argument.edit", `Argument edited: ${a.title}`.slice(0, 280), (x) => {
      if (sup.value && !x.support.includes(sup.value)) x.support.push(sup.value);
      if (con.value && !x.contra.includes(con.value)) x.contra.push(con.value);
      if (asm.value && !x.assumptions.find((q) => q.ref === asm.value)) x.assumptions.push({ ref: asm.value, text: nodes.get(asm.value)?.label.slice(0, 200) || asm.value });
      if (rule.value) x.rule = rule.value;
      if (lim.value.trim()) x.limitations.push(lim.value.slice(0, 300));
      if (alt.value.trim()) x.alternatives.push(alt.value.slice(0, 300));
      if (oq.value.trim()) x.questions.push(oq.value.slice(0, 300));
      return x;
    });
  });
  const branch = el("button", { class: "btn small", type: "button", id: "arg-branch" }, "Branch this argument");
  branch.addEventListener("click", async () => {
    const id = S.newId("arg");
    await S.update("argument.branch", `Argument branched from ${a.title}`.slice(0, 280), (s) => {
      s.arguments = [...s.arguments, { ...structuredClone(a), id, parent: a.id, title: `${a.title} (branch)`.slice(0, 80), disputes: [] }].slice(-30); return s;
    }, id);
    sel = id; renderArgue();
  });
  const others = args.filter((x) => x.id !== a.id);
  const cmpSel = el("select", { id: "arg-compare", "aria-label": "Compare with" }, el("option", { value: "" }, "compare with…"), ...others.map((x) => el("option", { value: x.id, selected: x.id === cmpWith || null }, x.title)));
  cmpSel.addEventListener("change", () => { cmpWith = cmpSel.value || null; renderArgue(); });
  const disputeTarget = el("select", { id: "arg-dispute-step", "aria-label": "Step to challenge" }, ...["the inference rule", ...a.support.map((r) => `support: ${r}`), ...a.assumptions.map((x) => `assumption: ${x.ref}`)].map((t) => el("option", { value: t }, t.slice(0, 90))));
  const disputeText = txt("arg-dispute-text", "your challenge to this step");
  const dispute = el("button", { class: "btn small", type: "button", id: "arg-dispute" }, "Challenge step");
  dispute.addEventListener("click", async () => {
    if (!disputeText.value.trim()) { toast("Write the challenge"); return; }
    await mut("argument.dispute", `Challenge to “${a.title}”: ${disputeTarget.value}`.slice(0, 280), (x) => { x.disputes.push({ step: disputeTarget.value, text: disputeText.value.slice(0, 500), status: "open",
      at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") }); return x; });
  });
  const exp = el("button", { class: "btn small", type: "button", id: "arg-export" }, "Export argument map");
  exp.addEventListener("click", async () => {
    const md = [`# Argument: ${a.claim}`, "", `- Inference rule: ${a.rule || "—"}`, `- Well-formed: ${A.well_formed ? "yes" : "no — " + A.problems.join("; ")}`, `- Empirical standing: ${A.empirical}`, "",
      "## Supporting evidence", ...a.support.map((r) => `- ${r} — ${nodes.get(r)?.label || "unresolved"} [${nodes.get(r)?.status || "?"}]`), "", "## Contradicting evidence", ...a.contra.map((r) => `- ${r} — ${nodes.get(r)?.label || "unresolved"}`),
      "", "## Assumptions", ...a.assumptions.map((x) => `- ${x.text}`), "", "## Limitations", ...a.limitations.map((x) => `- ${x}`), "", "## Alternative interpretations", ...a.alternatives.map((x) => `- ${x}`),
      "", "## Open questions", ...a.questions.map((x) => `- ${x}`), "", "## Disputes", ...a.disputes.map((x) => `- [${x.status}] ${x.step}: ${x.text}`), "",
      `Synthetic test data: ${state.inv.record.parameters.bundle_kind === "synthetic" ? "yes" : "no"} · run ${state.inv.record.content_hash.slice(0, 12)} · ${A.note}`].join("\n");
    if (await download(`skytrace-argument-${a.id}.md`, md, "text/markdown")) toast("Argument map exported");
  });
  const sec = (title, items, render) => el("div", {}, el("h4", {}, title), items.length ? el("ul", { class: "plain small" }, ...items.map(render)) : el("p", { class: "faint small" }, "—"));
  return el("div", { class: "card", id: "arg-view" }, el("h3", {}, a.claim), a.parent ? el("p", { class: "faint small" }, `Branch of ${args.find((x) => x.id === a.parent)?.title || a.parent}`) : null,
    kv([["Well-formed (structure)", el("span", { id: "arg-valid" }, outcomePill(A.well_formed ? "pass" : "warning"), " ", A.well_formed ? "every step has premises and every reference resolves" : A.problems.join("; "))],
      ["Empirical standing (evidence)", el("span", { id: "arg-empirical" }, A.empirical)], ["Inference rule", a.rule || "—"]]),
    el("p", { class: "faint small" }, A.note),
    sec("Supporting evidence", a.support, (r) => el("li", {}, statusPill(nodes.get(r)?.status), " ", nodes.get(r)?.label || `${r} (unresolved)`)),
    sec("Contradicting evidence", a.contra, (r) => el("li", {}, statusPill(nodes.get(r)?.status), " ", nodes.get(r)?.label || r)),
    sec("Assumptions", a.assumptions, (x) => el("li", {}, x.text)), sec("Limitations", a.limitations, (x) => el("li", {}, x)),
    sec("Alternative interpretations", a.alternatives, (x) => el("li", {}, x)), sec("Open questions", a.questions, (x) => el("li", {}, x)),
    sec("Disputes", a.disputes, (x) => el("li", {}, el("span", { class: "pill" }, x.status), ` ${x.step}: ${x.text}`)),
    el("div", { class: "controls" }, sup, con, asm, rule), el("div", { class: "controls" }, lim, alt, oq, addBtn),
    el("div", { class: "controls" }, disputeTarget, disputeText, dispute), el("div", { class: "controls" }, branch, cmpSel, exp),
    cmpWith ? compare(a, args.find((x) => x.id === cmpWith), nodes) : null);
}

function compare(a, b, nodes) {
  if (!b) return null;
  const rows = ["support", "contra"].map((k) => el("tr", {}, el("th", { scope: "row" }, k), el("td", { class: "small" }, a[k].filter((x) => !b[k].includes(x)).join(", ") || "—"),
    el("td", { class: "small" }, a[k].filter((x) => b[k].includes(x)).join(", ") || "—"), el("td", { class: "small" }, b[k].filter((x) => !a[k].includes(x)).join(", ") || "—")));
  rows.push(el("tr", {}, el("th", { scope: "row" }, "rule"), el("td", {}, a.rule || "—"), el("td", {}, a.rule === b.rule ? "same" : ""), el("td", {}, b.rule || "—")));
  return el("div", { id: "arg-compare-out" }, el("h4", {}, `Compared with “${b.title}”`), table(["", "Only this argument", "Both", "Only the other"], rows));
}
