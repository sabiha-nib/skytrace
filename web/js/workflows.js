// WF-1 validation in the browser: identical rules to src/skytrace/workflows.py (parity-tested). The schema and the
// action table come from the specs document; nothing here defines what an action does.

import { check } from "./schema.js";

export function validate(spec, w) {
  if (!w || typeof w !== "object" || Array.isArray(w)) return ["$: a workflow must be an object"];
  const errs = check(spec.workflow_schema, w);
  if (errs.length) return errs;
  if (!w.targets.length) errs.push("$.targets: at least one target");
  if (new Set(w.targets).size !== w.targets.length) errs.push("$.targets: targets must be distinct");
  if (!w.steps.length) errs.push("$.steps: at least one step");
  const ids = w.steps.map((s) => s.id);
  if (new Set(ids).size !== ids.length) errs.push("$.steps: step ids must be distinct");
  w.steps.forEach((s, i) => {
    const bad = s.depends.filter((d) => !ids.slice(0, i).includes(d));
    if (bad.length) errs.push(`$.steps[${i}]: depends on steps that do not precede it: ${bad.join(", ")}`);
    errs.push(...check(spec.action_inputs[s.action], s.inputs ?? {}, `$.steps[${i}].inputs`));
  });
  if (w.targets.length * w.steps.length > spec.workflow_limits.max_executions)
    errs.push(`$: ${w.targets.length} targets × ${w.steps.length} steps exceeds ${spec.workflow_limits.max_executions} executions`);
  return errs;
}
