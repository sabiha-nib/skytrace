// The one place that executes registered actions (capabilities.ACTIONS) for the planner, missions, workflows and
// the Discovery Radar. Each action calls exactly one existing interface entry point — nothing is simulated — and
// returns a small result summary (scalars only, stored in the session) or throws with the reason.
//   status "completed": the action ran and returned a result
//   status "needs_review": the action opened something for a human judgement (e.g. inspecting a pair)
// Static preview: actions marked "unavailable" are refused; "precomputed" ones serve the build's results.

import { api, STATIC } from "./api.js";
import { emit, getDiscovery, getResearch, state } from "./state.js";
import * as S from "./session.js";

let hooks = { runAnalysis: null, loadTarget: null };
export function setHooks(h) { hooks = { ...hooks, ...h }; }

async function sha256hex(buf) {
  const h = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(h), (b) => b.toString(16).padStart(2, "0")).join("");
}

function needRun() { if (!state.inv) throw new Error("no analysis run is loaded"); }

const ACTIONS = {
  async run_analysis(inputs) {
    if (!state.target) throw new Error("the target has no stored observations");
    await hooks.runAnalysis(inputs.params || {}, { quiet: true });
    needRun();
    const m = state.model;
    return { status: "completed", result: { content_hash: state.inv.record.content_hash, n_events: state.inv.record.events.length,
      ...Object.fromEntries(m.outcomes.map((o) => [o.question, o.category])) } };
  },
  async run_stability() {
    needRun();
    const r = await api.stability(state.targetId, {});
    state.stability = { target: state.targetId, result: r };
    await S.log("stability.run", `STAB-1 for ${state.targetId}: ` + Object.entries(r.stable).map(([q, ok]) => `${q} ${ok ? "stable" : "fragile"}`).join(", "), null, { create: true });
    return { status: "completed", result: Object.fromEntries(Object.entries(r.stable).map(([q, ok]) => [`${q}_stable`, ok])) };
  },
  async compare_pair(inputs) {
    needRun();
    const p = await api.pair(state.targetId, inputs.a, inputs.b, state.inv.investigation_id);
    const c = p.comparison || {};
    return { status: "completed", result: { compatible: !!c.compatible_for_photometry, reason: String(c.reason || "").slice(0, 300),
      z: c.flux?.z ?? null, delta_t_days: c.delta_t_days ?? null, registration_available: !!c.registration?.available } };
  },
  async inspect_pair(inputs) {
    needRun();
    emit("goto", { ws: "time", key: inputs.a, partner: inputs.b });
    return { status: "needs_review", result: { opened: `${inputs.a} | ${inputs.b}` } };
  },
  async build_sequences() {
    needRun();
    const r = await getResearch();
    return { status: "completed", result: { n_sequences: r.compat.sequences.length, max_visits: Math.max(0, ...r.compat.sequences.map((s) => s.n_visits)),
      n_duplicates: r.compat.duplicates.length } };
  },
  async evaluate_hypotheses() {
    needRun();
    const d = await getDiscovery();
    const all = d.hypotheses.questions.flatMap((q) => q.hypotheses);
    const n = (st) => all.filter((h) => h.overall === st).length;
    return { status: "completed", result: { explanations: all.length, contradicted: n("contradicted"), consistent_so_far: n("consistent so far"),
      inconclusive: n("inconclusive"), untested: n("untested") } };
  },
  async decompose_uncertainty() {
    needRun();
    const d = await getDiscovery();
    const u = d.uncertainty;
    return { status: "completed", result: { motion_available: !!u.motion.available, pairs_decomposed: u.variability.available ? u.variability.pairs.length : 0,
      recompute_mismatches: u.variability.available ? u.variability.pairs.filter((p) => p.consistent_with_log === false).length : 0, unquantified_effects: u.unquantified.length } };
  },
  async check_quality() {
    needRun();
    const q = (await getResearch()).quality;
    return { status: "completed", result: Object.fromEntries(Object.entries(q.summary).map(([k, v]) => [`checks_${k}`, v])) };
  },
  async inspect_ledger() {
    needRun();
    const L = (await getResearch()).ledger;
    return { status: "completed", result: { claims: L.claims.length, contradictions: L.contradictions.length,
      completeness_gaps: L.completeness.gaps.filter((g) => !g.expected).length } };
  },
  async scan_radar() {
    needRun();
    const R = (await getResearch()).radar;
    return { status: "completed", result: { opportunities: R.items.length, runnable_now: R.items.filter((x) => x.can_run_now).length } };
  },
  async verify_provenance(inputs) {
    needRun();
    if (STATIC) throw new Error("needs the full application (python run.py)");
    const r = await api.provenance(state.inv.investigation_id, inputs.rerun !== false);
    await S.log("provenance.run", `PROVCHECK-1: ${r.checks.filter((c) => c.ok).length}/${r.checks.length} checks passed`, null, { create: true });
    return { status: "completed", result: { checks: r.checks.length, passed: r.checks.filter((c) => c.ok).length, all_passed: r.checks.every((c) => c.ok) } };
  },
  async run_experiment(inputs) {
    if (!state.target) throw new Error("the target has no stored observations");
    const r = await api.experiment(state.targetId, inputs);
    await recordExperiment(r);
    return { status: "completed", result: { template: r.template, passed: r.evaluation?.passed ?? null, analyses: r.n_analyses,
      recorded_at_build: !!r.recorded_at_build } };
  },
  async build_package() {
    needRun();
    const buf = await api.packageBytes(state.inv.investigation_id);
    return { status: "completed", result: { bytes: buf.byteLength, sha256: await sha256hex(buf) } };
  },
  async acquire_data() { throw new Error("acquisition needs network access to the archives, which is blocked here; run scripts/acquire_targets.py on a networked machine"); },
};

export async function recordExperiment(r) {
  await S.update(`experiment.${r.template}`, `${r.title}: ${r.evaluation?.passed === true ? "criterion met" : r.evaluation?.passed === false ? "criterion not met" : "no evaluation"}`,
    (s) => {
      const keep = { template: r.template, criterion: r.criterion, evaluation: r.evaluation, runs: r.runs.map((x) => ({ label: x.label, target: x.target, ok: x.ok,
        content_hash: x.content_hash ?? null, categories: x.categories ?? null, error: x.error ?? null })), recorded_at_build: !!r.recorded_at_build };
      let json = keep;
      if (JSON.stringify(json).length > 38000) json = { ...keep, evaluation: { passed: r.evaluation?.passed ?? null, detail: "evaluation too large to keep in the session" } };
      s.experiments = [...s.experiments, { id: S.newId("e"), template: r.template, created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
        status: r.status === "completed" ? "completed" : "refused", config: r.config || { template: r.template }, result: json }].slice(-30);
      return s;
    });
}

export async function execute(actionId, inputs = {}) {
  const fn = ACTIONS[actionId];
  if (!fn) throw new Error(`unknown action ${actionId}`);
  const spec = state.specs?.planner?.actions?.[actionId];
  if (STATIC && spec?.static === "unavailable") throw new Error("needs the full application (python run.py)");
  return fn(inputs);
}

export const ACTION_IDS = Object.keys(ACTIONS);
