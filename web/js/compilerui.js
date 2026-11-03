// Scientific Compiler (SCICOMP-1) and Method Genome (METHOD-DNA-1).
// The compiler's checks ran on the server against the recorded investigation; this view shows the ten stages, the overall
// outcome with its precedence rule, and every check with the objects it cites. Passing is not proof of a conclusion.

import { state } from "./state.js";
import { focusNode } from "./reasoningui.js";
import { emit } from "./state.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, loadEpistemic, needRun, outcomePill, syntheticNote, table, tabs } from "./epiui.js";
import { compilerStatuses } from "./universalui.js";

let tab = "compile", stageFilter = "all", outFilter = "all", methodSel = null, cmpA = "PAIRDIFF-1", cmpB = "PAIRDIFF-2";
export function setCompilerTab(t) { tab = t; }

export async function renderCompiler() {
  const live = renderToken("compiler");
  const body = $("#compiler-body");
  clear(body);
  if (!state.inv) { needRun(body, "The compiler checks a recorded analysis."); return; }
  const d = await loadEpistemic(body, "compiler");
  if (!d || !live()) return;
  body.append(syntheticNote(d), tabs("Compiler", [["compile", "Compilation"], ["genome", "Method genome"]], tab, "data-ctab", (k) => { tab = k; renderCompiler(); }));
  body.append(tab === "compile" ? compileView(d.compile) : genomeView(d.genome, d.method_graph));
  if (tab === "compile") compilerStatuses(body);
}

function compileView(C) {
  const head = el("div", { class: `card compile-head out-${C.outcome.replace(/\s+/g, "-")}`, id: "compile-outcome" },
    el("p", { class: "eyebrow" }, "Compilation outcome"), el("h3", {}, C.outcome),
    el("p", { class: "muted" }, C.meaning), el("details", { class: "small" }, el("summary", {}, "Outcome rule"), el("p", {}, C.outcome_rule)));
  const pipeline = el("ol", { class: "compile-stages", "aria-label": "Compilation stages" }, ...C.stages.map((s, i) => {
    const worst = s.counts.fail ? "fail" : s.counts.warning ? "warning" : s.counts.pass ? "pass" : "not applicable";
    const b = el("button", { type: "button", class: `stage-btn s-${worst}`, "data-stage": s.id, "aria-pressed": String(stageFilter === s.id) },
      el("span", { class: "stage-n" }, String(i + 1)), el("span", {}, s.name), el("span", { class: "faint small" }, `${s.counts.pass}✓ ${s.counts.warning}! ${s.counts.fail}✗`));
    b.addEventListener("click", () => { stageFilter = stageFilter === s.id ? "all" : s.id; renderCompiler(); });
    return el("li", {}, b);
  }), el("li", {}, el("span", { class: "stage-btn s-report" }, el("span", { class: "stage-n" }, "10"), el("span", {}, "Compilation report"), el("span", { class: "faint small" }, C.outcome))));
  const outs = el("div", { class: "tagrow", "aria-label": "Filter by outcome" }, ...["all", "fail", "warning", "pass", "not applicable"].map((o) => {
    const b = el("button", { type: "button", class: "tag", "aria-pressed": String(outFilter === o), "data-out": o }, o);
    b.addEventListener("click", () => { outFilter = o; renderCompiler(); });
    return b;
  }));
  const list = C.checks.filter((c) => (stageFilter === "all" || c.stage === stageFilter) && (outFilter === "all" || c.outcome === outFilter));
  const exp = el("button", { class: "btn small", type: "button", id: "compile-export" }, "Export compilation report (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-compilation-${C.content_hash.slice(0, 12)}.json`, JSON.stringify(C, null, 1), "application/json")) toast("Compilation report exported"); });
  return el("div", {}, head, el("div", { class: "card" }, pipeline, el("div", { class: "controls" }, outs, exp)),
    el("ol", { class: "check-list", id: "compile-checks" }, ...list.map((c) => el("li", { class: `check o-${c.outcome.replace(/\s+/g, "-")}`, "data-check": c.id },
      el("div", { class: "next-head" }, outcomePill(c.outcome), el("strong", {}, `${c.id} · ${c.rule}`), c.review ? el("span", { class: "pill out-warn" }, "asks for review") : null),
      el("p", {}, c.detail),
      c.cites.length ? el("p", { class: "small" }, "Cites: ", ...c.cites.map((x) => cite(x))) : null))),
    list.length ? null : el("p", { class: "empty" }, "No check matches the filter."));
}

function cite(x) {
  if (/^(claim|pair|meas|pos|file|fit|epoch|inf|hyp|method|asm|param|unc|con|scale|tf):/.test(x)) {
    const b = el("button", { type: "button", class: "linkish mono small" }, x.length > 60 ? x.slice(0, 60) + "…" : x);
    b.addEventListener("click", () => { focusNode(x); emit("goto", { ws: "reasoning" }); });
    return el("span", {}, b, " ");
  }
  return el("span", { class: "mono small" }, x + " ");
}

function genomeView(G, MG) {
  const methods = G.methods;
  if (!methodSel || !methods.find((m) => m.id === methodSel)) methodSel = methods.find((m) => m.used_in_run)?.id || methods[0].id;
  const m = methods.find((x) => x.id === methodSel);
  const list = table(["Method", "Family", "Used here", "Known-answer tests", "Output status", "Docs"], methods.map((x) => {
    const b = el("button", { type: "button", class: "linkish", "data-method": x.id }, x.id);
    b.addEventListener("click", () => { methodSel = x.id; renderCompiler(); });
    return el("tr", { class: x.id === methodSel ? "sel" : "" }, el("th", { scope: "row" }, b), el("td", {}, x.family), el("td", {}, x.used_in_run ? "yes" : "—"),
      el("td", {}, `${x.health.n_defined} defined`), el("td", {}, x.output_status), el("td", {}, x.health.documentation_missing.length ? `missing ${x.health.documentation_missing.length}` : "complete"));
  }), { id: "genome-table" });
  const io = (xs) => el("ul", { class: "plain" }, ...xs.map((i) => el("li", {}, `${i.name} `, el("span", { class: "faint" }, `[${i.unit}]`))));
  const detail = el("div", { class: "card", id: "method-detail" }, el("h3", {}, m.id), el("p", {}, m.purpose), kv([["Inputs", io(m.inputs)], ["Outputs", io(m.outputs)],
    ["Assumptions", el("ul", { class: "plain" }, ...m.assumptions.map((a) => el("li", {}, a)))], ["Parameters", m.parameters.join(", ") || "none"],
    ["Mathematics", m.math], ["Depends on", m.dependencies.join(", ") || "none"], ["Applicable", m.applicable.join("; ")], ["Not supported", m.unsupported.join("; ")],
    ["Limitations", m.limitations.join("; ")], ["Uncertainty", m.uncertainty_propagation], ["Validation data", m.validation_data.join("; ")],
    ["Known-answer tests", el("ul", { class: "plain mono small" }, ...m.health.known_answer_tests.map((t) => el("li", {}, `${t.defined ? "✓" : "✗"} ${t.test}`)))],
    ["Versions", m.versions.map((v) => `${v.id}: ${v.change}`).join(" → ")], ["Implementation", el("span", { class: "mono" }, m.module)],
    ["Reproducibility", m.health.reproducibility], ["Dependencies here", Object.entries(m.health.dependencies_available).map(([k, v]) => `${k} ${v ? "available" : "missing"}`).join(", ")]]),
    el("p", { class: "faint small" }, m.health.note));
  const sa = el("select", { id: "cmp-a", "aria-label": "Method A" }, ...methods.map((x) => el("option", { value: x.id, selected: x.id === cmpA || null }, x.id)));
  const sb = el("select", { id: "cmp-b", "aria-label": "Method B" }, ...methods.map((x) => el("option", { value: x.id, selected: x.id === cmpB || null }, x.id)));
  const cmpOut = el("div", { id: "cmp-out" }, compareMethods(methods, cmpA, cmpB));
  sa.addEventListener("change", () => { cmpA = sa.value; cmpOut.replaceChildren(compareMethods(methods, cmpA, cmpB)); });
  sb.addEventListener("change", () => { cmpB = sb.value; cmpOut.replaceChildren(compareMethods(methods, cmpA, cmpB)); });
  const deps = el("ul", { class: "plain small", id: "method-deps" }, ...MG.nodes.map((n) => {
    const inn = MG.edges.filter((e) => e.target === n.id).map((e) => e.source);
    return el("li", {}, el("strong", {}, n.id), inn.length ? ` ← ${inn.join(", ")}` : el("span", { class: "faint" }, " (no method dependency)"));
  }));
  return el("div", {}, el("div", { class: "card" }, el("p", { class: "muted" }, "Every analysis method as a versioned object. Health is reported as facts — defined tests, determinism coverage, dependencies, documentation — never as a score. Test coverage is software evidence, not scientific validity."), list),
    detail, el("div", { class: "card" }, el("h3", {}, "Compare two methods"), el("div", { class: "controls" }, sa, sb), cmpOut),
    el("div", { class: "card" }, el("h3", {}, "Method dependencies"), deps));
}

function compareMethods(methods, a, b) {
  const A = methods.find((x) => x.id === a), B = methods.find((x) => x.id === b);
  const ta = new Set(A.outputs.map((o) => o.type)), tb = new Set(B.outputs.map((o) => o.type));
  const shared = [...ta].filter((t) => tb.has(t));
  const fmtList = (xs) => xs.map((x) => (typeof x === "object" ? `${x.name} [${x.unit}]` : String(x)));
  const rows = ["inputs", "outputs", "assumptions", "parameters", "limitations", "validation_data"].map((f) => {
    const la = fmtList(A[f]), lb = fmtList(B[f]);
    return el("tr", {}, el("th", { scope: "row" }, f), el("td", {}, la.filter((x) => !lb.includes(x)).join("; ") || "—"), el("td", {}, la.filter((x) => lb.includes(x)).join("; ") || "—"),
      el("td", {}, lb.filter((x) => !la.includes(x)).join("; ") || "—"));
  });
  rows.push(el("tr", {}, el("th", { scope: "row" }, "validation status"), el("td", {}, `${A.health.n_defined} tests`), el("td", {}, ""), el("td", {}, `${B.health.n_defined} tests`)));
  return el("div", {}, el("p", {}, shared.length ? `Compatible: both produce ${shared.join(", ")}.` : "Not compatible: they produce different kinds of quantity.",
    el("span", { class: "faint" }, " Compatible does not mean either is better.")), table(["Field", `Only ${a}`, "Both", `Only ${b}`], rows, { id: "cmp-table" }));
}
