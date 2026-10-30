// PLAN-1 in the browser: the same algorithm as src/skytrace/planner.py, driven by the same SPEC document (served by
// the server at /api/planner, or data/planner.json in the static preview). Parity-tested on a question corpus.
// Nothing here decides a scientific outcome: it only arranges registered actions and says what blocks them.

const uniq = (xs) => [...new Set(xs)];

export function parse(spec, question, targets = []) {
  const q = question || "";
  const ql = q.toLowerCase();
  let kind = "unknown", rule = null;
  for (const [k, pat] of spec.rules) if (new RegExp(pat).test(ql)) { kind = k; rule = pat; break; }
  const aspects = Object.entries(spec.aspects).filter(([, pat]) => new RegExp(pat).test(ql)).map(([a]) => a);
  if ((kind === "brightness" || kind === "motion") && aspects.length === 2) kind = "change";
  const all = (re, s) => [...s.matchAll(new RegExp(re, "g"))];
  const keys = uniq(all(spec.patterns.key, q).map((m) => m[0]));
  const dets = uniq(all(spec.patterns.detector, q).map((m) => +m[1])).sort((a, b) => a - b);
  const dates = uniq(all(spec.patterns.date, q).map((m) => m[0]));
  let target = null;
  for (const t of targets || []) if (t && ql.includes(t.toLowerCase())) { target = t; break; }
  return { kind, rule, aspects, pair_requested: new RegExp(spec.patterns.pair).test(ql) || keys.length >= 2,
           keys: keys.slice(0, 4), detectors: dets, dates: dates.slice(0, 4), target, text: q.slice(0, 500) };
}

function fact(facts, name, action) {
  if (name === "server_or_precomputed") return !!facts.server || ["precomputed", "browser"].includes(action.static);
  if (name === "has_pair") return !!facts.pair;
  return !!facts[name];
}

export function plan(spec, question, facts) {
  const intent = parse(spec, question, facts.targets);
  const kind = intent.kind;
  const out = { method: spec.method, question: intent.text, intent, steps: [], answerable: true, explanation: "", requires_confirmation: false };
  if (kind in spec.unanswerable_map) {
    const u = spec.unanswerable[spec.unanswerable_map[kind]];
    return { ...out, answerable: false, explanation: `Not answerable here: ${u.why}. Would need: ${u.needed.join("; ")}.` };
  }
  if (kind === "capabilities") return { ...out, explanation: "Ask the copilot or open the capability registry: this is a question about Skytrace, not about the data." };
  if (kind === "unknown") return { ...out, answerable: false, explanation: "The question did not match any planning rule. Try one of: " + spec.examples.join(" · ") };
  if (!facts.has_target_data) out.explanation = "The selected target has no stored observations, so no analysis can run.";
  const pair = intent.keys.length >= 2 ? intent.keys.slice(0, 2) : (facts.pair || null);
  const eff = { ...facts, pair };
  const produced = {}, statusOf = {};
  for (const [sid, aid, optional, deps, cond] of spec.templates[kind]) {
    if (cond === "pair" && !intent.pair_requested && !optional) continue;
    if (cond === "pair" && optional && !(intent.pair_requested || pair)) continue;
    const a = spec.actions[aid];
    const step = { id: sid, action: aid, capabilities: a.capabilities, title: a.title, depends: deps.filter((d) => d in statusOf),
                   confirm: a.confirm, cost: a.cost, optional, review: !!a.review, inputs: {}, note: "" };
    if ((aid === "compare_pair" || aid === "inspect_pair") && pair) step.inputs = { a: pair[0], b: pair[1] };
    if (aid === "run_experiment") step.inputs = { template: spec.experiment_template[kind] || "sensitivity" };
    const missing = a.preconditions.filter((f) => !(fact(eff, f, a) || f in produced));
    if (facts.static && a.static === "unavailable") missing.push("server");
    if (aid === "run_analysis" && facts.has_run) {
      step.status = "completed";
      step.note = `reusing the loaded analysis run ${String(facts.run_hash || "").slice(0, 12)}`;
    } else if (missing.length) {
      step.status = "blocked";
      step.note = "needs: " + uniq(missing).map((m) => spec.facts[m] || m).join("; ");
      if (missing.includes("has_pair")) step.note += " — select two observations in the Time Machine, or name them in the question";
    } else if (step.depends.some((d) => statusOf[d] === "blocked")) {
      step.status = "blocked";
      step.note = "waits for a blocked step: " + step.depends.filter((d) => statusOf[d] === "blocked").join(", ");
    } else step.status = optional ? "suggested" : "ready";
    for (const p of a.produces) if (["ready", "completed", "suggested"].includes(step.status)) produced[p] = sid;
    statusOf[sid] = step.status;
    out.steps.push(step);
  }
  out.requires_confirmation = out.steps.some((s) => s.confirm && (s.status === "ready" || s.status === "suggested"));
  if (!out.explanation) {
    const nb = out.steps.filter((s) => s.status === "blocked").length;
    out.explanation = `${out.steps.length} steps from the ${kind} template` + (nb ? `; ${nb} blocked` : "") +
      ". Steps marked ‘confirm’ re-execute analyses or take time and run only after you confirm.";
  }
  return out;
}
