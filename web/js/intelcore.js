// Phase 9 browser core: pure functions mirrored from the Python modules and parity-tested
// (tests/js/intel_parity.mjs ↔ tests/unit/test_intelligence.py):
//   queryConcepts, recall, failureWarnings ← memory.query_concepts / recall / warnings
//   overlayLedger ← adversary.overlay          overlayGate ← gate.overlay
//   validateOracleSpec, oracleEvaluate ← oracle.validate_spec / evaluate_ctx
//   hypotheticalVisit ← whatif.hypothetical_visit (with whatif.refit)
//   reproValidate, reproCompare ← repronet.validate / compare
//   sessionEntities ← entities.session_entities   causalWarnings ← causal.warnings
// They let the static preview recall memory, examine challenges, mark the gate, plan observations, ask what-if questions and
// compare reproductions without a server. Nothing here calls a model or uses a probability.

import { digest } from "./canon.js";

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** Python's format(x, ".{p}g"). */
export function pyG(x, p = 6) {
  if (x === null || x === undefined) return "None";
  if (!Number.isFinite(x)) return Number.isNaN(x) ? "nan" : x > 0 ? "inf" : "-inf";
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  const e = Math.floor(Math.log10(Math.abs(Number(x.toPrecision(p)))));
  if (e < -4 || e >= p) {
    let [m, ex] = x.toExponential(p - 1).split("e");
    if (m.includes(".")) m = m.replace(/0+$/, "").replace(/\.$/, "");
    const n = Number(ex);
    return `${m}e${n < 0 ? "-" : "+"}${String(Math.abs(n)).padStart(2, "0")}`;
  }
  let s = x.toFixed(Math.max(0, p - 1 - e));
  if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
  return s;
}

/** Python's built-in sum() over floats (CPython ≥ 3.12 uses Neumaier's compensated summation), so totals agree bit for bit. */
export function pySum(xs) {
  let f = 0.0, c = 0.0;
  for (const x of xs) {
    const t = f + x;
    if (Math.abs(f) >= Math.abs(x)) c += (f - t) + x; else c += (x - t) + f;
    f = t;
  }
  return c !== 0 && Number.isFinite(c) ? f + c : f;
}

const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const n = s.length; return n % 2 ? s[(n - 1) / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2]); };

// ------------------------------------------------------------------ research memory (MEMORY-1)
const words = (s) => (String(s || "").toLowerCase().match(/[a-z0-9]+(?:[-'][a-z0-9]+)*/g) || []);

export function queryConcepts(query, concepts) {
  const q = " " + words(query).join(" ") + " ";
  const out = [];
  for (const [cid, c] of Object.entries(concepts)) {
    for (const term of [cid.replaceAll("_", " "), ...c.terms]) {
      const t = " " + words(term).join(" ") + " ";
      if (t.trim() && q.includes(t)) { out.push({ id: cid, label: c.label, via: term }); break; }
    }
  }
  return out;
}

export function recall(mem, query, limit = 30) {
  const cs = queryConcepts(query, mem.concepts);
  const ids = new Set(cs.map((c) => c.id));
  let scored = [];
  for (const x of mem.items) {
    const m = x.concepts.filter((c) => ids.has(c)).sort(cmp);
    if (m.length) scored.push([m.length, x.created_at || "", x.id, m]);
  }
  scored.sort((a, b) => b[0] - a[0] || cmp(b[1], a[1]) || cmp(a[2], b[2]));
  return { query, concepts: cs, results: scored.slice(0, limit).map((r) => ({ item: r[2], matched: r[3] })), n: scored.length,
    rule: "items sharing the most query concepts first, then the most recent; concepts come from the fixed vocabulary",
    note: cs.length ? null : "No concept recognised in the query." };
}

export function failureWarnings(mem, target, actions) {
  const out = [], seen = new Map();
  for (const a of actions) {
    for (const x of mem.items) {
      if (x.kind !== "failure" || (target && x.target !== target) || x.category === "known limitation" || String(x.source?.ref ?? "").startsWith("environment:")) continue;
      let rule = null;
      if (a.question && x.question === a.question) rule = "W1";
      else if ((a.concepts || []).some((c) => x.concepts.includes(c))) rule = "W2";
      if (!rule) continue;
      const key = JSON.stringify([a.id, x.statement]);
      if (seen.has(key)) { const w = seen.get(key); w.records.push(x.record); if (rule === "W1") w.rule = "W1"; continue; }
      const w = { action: a.id, action_label: a.label ?? null, memory: x.id, rule, target: x.target, record: x.record, records: [x.record],
        what_failed: x.statement, why: x.why ?? null, unblock: x.unblock ?? null };
      seen.set(key, w); out.push(w);
    }
  }
  out.sort((p, q) => cmp(p.rule, q.rule) || cmp(p.action, q.action) || cmp(p.what_failed, q.what_failed));
  return out;
}

// ------------------------------------------------------------------ challenge ledger and gate (ADV-1, GATE-1)
export const LEDGER_STATUSES = ["open", "acknowledged", "resolved"];

export function overlayLedger(led, session) {
  const marks = {};
  for (const m of (session || {}).challenges || []) {
    if (m && typeof m === "object" && !Array.isArray(m) && m.id && LEDGER_STATUSES.includes(m.status)) {
      if (m.status === "resolved" && !m.ref) continue;
      marks[m.id] = m;
    }
  }
  const out = { ...led, conclusions: [] };
  for (const c of led.conclusions) {
    const qs = c.questions.map((q) => ({ ...q, items: q.items.map((i) => (i.id in marks ? { ...i, status: marks[i.id].status, note: marks[i.id].note ?? null, resolved_by: marks[i.id].ref ?? null } : i)) }));
    const all = qs.flatMap((q) => q.items);
    out.conclusions.push({ ...c, questions: qs, by_status: Object.fromEntries(LEDGER_STATUSES.map((s) => [s, all.filter((i) => i.status === s).length])) });
  }
  return out;
}

const GATE_STATES = ["met", "not met", "needs your action"];
const GOOD_REPRO = ["exact reproduction", "numerically equivalent reproduction"];

function gateFinish(record, R, syn) {
  const ready = R.every((r) => r.state === "met");
  return { method: "GATE-1", record, requirements: R, states: GATE_STATES, outcome: ready ? "ready to mark complete" : "not ready", synthetic: syn,
    counts: Object.fromEntries(GATE_STATES.map((s) => [s, R.filter((r) => r.state === s).length])),
    meaning: "Ready means the conclusions are stated within the evidence, reproducible here, and disclose their uncertainty and limitations. It does not mean they are true."
      + (syn ? " On synthetic data, completion is a completed software test." : "") };
}

export function overlayGate(gate, ledOverlaid, session) {
  const s = session || {};
  const R = gate.requirements.map((r) => ({ ...r }));
  const by = Object.fromEntries(R.map((r) => [r.id, r]));
  if (by.G3.state !== "met") {
    const rx = (s.debug || []).filter((d) => d && typeof d === "object" && d.kind === "reproduction" && (d.content_hash || d.record) === gate.record);
    const good = rx.filter((d) => GOOD_REPRO.includes(d.verdict));
    if (good.length) Object.assign(by.G3, { state: "met", detail: `reproduction you ran: ${good[good.length - 1].verdict}` });
    else if (rx.length) Object.assign(by.G3, { state: "not met", detail: `reproduction you ran: ${rx[rx.length - 1].verdict ?? "None"}` });
  }
  const items = {};
  for (const c of ledOverlaid.conclusions) for (const q of c.questions) for (const i of q.items) items[i.id] = i;
  for (const [rid, pred] of [["G7", () => true], ["G6", (i) => i.question_id === "Q8"]]) {
    const r = by[rid];
    if (r.state === "needs your action") {
      const left = r.cites.filter((c) => c in items && pred(items[c]) && items[c].status === "open");
      if (!left.length) Object.assign(r, { state: "met", detail: r.detail + " — all examined in the session" });
      else Object.assign(r, { detail: `${left.length} challenge(s) still open` });
    }
  }
  return { ...gateFinish(gate.record, R, gate.synthetic), record: gate.record };
}

// ------------------------------------------------------------------ observation oracle (ORACLE-1)
const isNum = (x) => typeof x === "number" && Number.isFinite(x);

export function validateOracleSpec(spec, maxAdded = 20) {
  const errs = [];
  if (!spec || typeof spec !== "object" || Array.isArray(spec)) return ["the specification must be an object"];
  const q = spec.question;
  if (!["motion", "variability"].includes(q)) errs.push("question must be 'motion' or 'variability'");
  const cands = spec.candidates;
  if (!Array.isArray(cands) || cands.length < 1 || cands.length > 6) { errs.push("give 1–6 candidate observation sets"); return errs; }
  cands.forEach((c, i) => {
    if (!c || typeof c !== "object" || Array.isArray(c)) { errs.push(`candidate ${i + 1} must be an object`); return; }
    if (q === "motion") {
      const add = c.added_years_after_last ?? [];
      if (!Array.isArray(add) || add.length > maxAdded || add.some((x) => !isNum(x) || !(x > 0 && x <= 20))) errs.push(`candidate ${i + 1}: added_years_after_last must be ≤ ${maxAdded} values in (0, 20] years`);
      const f = c.error_factor ?? 1.0;
      if (!isNum(f) || !(f >= 0.1 && f <= 10)) errs.push(`candidate ${i + 1}: error_factor must be in [0.1, 10]`);
    } else {
      const e = c.fractional_error;
      if (!isNum(e) || !(e >= 1e-4 && e <= 1)) errs.push(`candidate ${i + 1}: fractional_error must be in [0.0001, 1]`);
    }
  });
  const h1 = spec.h1_value;
  if (h1 !== undefined && h1 !== null && (!isNum(h1) || h1 <= 0)) errs.push("h1_value must be positive (|μ| in mas/yr, or the fractional change f)");
  return errs;
}

function sigmaPm(times, sigmas) {
  if (times.length < 2) return null;
  const w = sigmas.map((s) => 1 / s ** 2);
  const sw = pySum(w), st = pySum(w.map((x, i) => x * times[i])), stt = pySum(w.map((x, i) => x * times[i] * times[i]));
  const det = sw * stt - st * st;
  return det > 0 ? Math.sqrt(sw / det) : null;
}

export function oracleEvaluate(ctx, spec, threshold = 5.0) {
  const q = spec.question;
  const rows = [];
  let assumptions = [];
  const warnings = [];
  if (q === "motion") {
    if (ctx.visits.length < 2 || !ctx.validated) return { method: "ORACLE-1", available: false, why: "the slope-error formula could not be validated against the recorded fit" };
    const mu = spec.h1_value || ctx.recorded_pm_mas_yr;
    if (!mu) return { method: "ORACLE-1", available: false, why: "give |μ| for H1: the record has no motion estimate" };
    const t = ctx.visits.map((v) => v.t_yr), s = ctx.visits.map((v) => v.sigma_mas);
    const med = median(s);
    [{ label: "recorded visits only", added_years_after_last: [] }, ...spec.candidates].forEach((c, i) => {
      const add = c.added_years_after_last ?? [];
      const k = c.error_factor ?? 1.0;
      const tt = [...t, ...add.map((x) => Math.max(...t) + x)];
      const ss = [...s, ...add.map(() => med * k)];
      const sp = sigmaPm(tt, ss);
      const S = sp ? mu / sp : null;
      rows.push({ id: i === 0 ? "recorded" : `c${i}`, label: c.label || `candidate ${i}`, added_visits: add.length, baseline_yr: Math.max(...tt) - Math.min(...tt),
        sigma_mu_mas_yr: sp, expected_significance: S, expected_delta_chi2: S !== null ? S * S + 1 : null, min_detectable_mu_mas_yr: sp ? threshold * sp : null,
        discriminates: S !== null && S >= threshold, hypothetical: i > 0 });
    });
    assumptions = [`H1: linear motion at |μ| = ${pyG(mu, 4)} mas/yr (${spec.h1_value ? "your value" : "the recorded estimate"})`,
      `an added visit has the median recorded per-visit error × factor (${pyG(med, 4)} mas × factor, worse axis)`,
      "independent Gaussian errors; no χ²ν inflation", "the worse axis is used for S (conservative)", "no telescope schedule, pointing or availability is implied"];
    if (!spec.h1_value && ctx.recorded_pm_mas_yr) warnings.push("H1 uses the recorded estimate of |μ|, which is itself uncertain; try a smaller |μ| to see what would still be detected");
  } else {
    const f = spec.h1_value || 0.05;
    const k = Math.max(1.0, ctx.error_scale);
    [{ label: "recorded precision", fractional_error: ctx.median_fractional_error }, ...spec.candidates].forEach((c, i) => {
      const e = c.fractional_error;
      if (!e) { rows.push({ id: "recorded", label: "recorded precision", available: false }); return; }
      const S = f / (Math.SQRT2 * e * k);
      rows.push({ id: i === 0 ? "recorded" : `c${i}`, label: c.label || `candidate ${i}`, fractional_error: e, expected_significance: S, expected_delta_chi2: S * S + 1,
        max_error_for_detection: f / (threshold * Math.SQRT2 * k), discriminates: S >= threshold, hypothetical: i > 0 });
    });
    assumptions = [`H1: a fractional change f = ${pyG(f)} between two epochs`, `the recorded CALCHECK error scale ${pyG(k, 4)} applies to new data`,
      "one wavelength-matched pair with equal fractional errors", "|z| ≥ 5 in one pair (ASSESS-2 also needs consistent pairs)", "no schedule is implied"];
    if (ctx.error_scale && ctx.error_scale > 1.5) warnings.push(`the recorded error scale ${pyG(ctx.error_scale, 3)} exceeds 1.5: the error model underestimates the scatter (ASL M1)`);
  }
  const ranked = rows.filter((r) => r.hypothetical && r.expected_significance !== null && r.expected_significance !== undefined)
    .sort((a, b) => b.expected_significance - a.expected_significance || (a.added_visits ?? 0) - (b.added_visits ?? 0) || cmp(a.id, b.id));
  return { method: "ORACLE-1", available: true, question: q, hypotheses: { H0: q === "motion" ? "static source" : "no brightness change", H1: assumptions[0] },
    rows, ranking: ranked.map((r) => r.id), ranking_rule: "largest expected significance first; ties by fewer added visits; this is an ordering under the stated model, not an optimum",
    assumptions, warnings, information_gain: null,
    information_gain_note: "not computed: bits of information need prior probabilities for H0 and H1, which the record does not contain",
    context: Object.fromEntries(Object.entries(ctx).filter(([k]) => k !== "validation")), hypothetical: true, note: "Hypothetical planning only. Nothing is scheduled; no instrument availability is implied." };
}

// ------------------------------------------------------------------ what-if: a hypothetical visit (WHATIF-1)
function wls(t, y, s) {
  const w = s.map((x) => 1 / x ** 2);
  const sw = pySum(w), st = pySum(w.map((x, i) => x * t[i])), sy = pySum(w.map((x, i) => x * y[i]));
  const stt = pySum(w.map((x, i) => x * t[i] * t[i])), sty = pySum(w.map((x, i) => x * t[i] * y[i]));
  const det = sw * stt - st * st;
  const b = (sw * sty - st * sy) / det, a = (sy - b * st) / sw;
  const chi2 = pySum(y.map((yi, i) => ((yi - (a + b * t[i])) / s[i]) ** 2));
  return { position: a, pm: b, sigma_pm: (sw / det) ** 0.5, chi2 };
}

export function motionRefit(t, xi, sxi, eta, seta) {
  const axes = {};
  for (const [ax, y, s] of [["xi", xi, sxi], ["eta", eta, seta]]) {
    const r = wls(t, y, s);
    const dof = y.length - 2;
    const rc = dof > 0 ? r.chi2 / dof : null;
    axes[ax] = { pm: r.pm, sigma: rc !== null ? r.sigma_pm * Math.sqrt(Math.max(1.0, rc)) : r.sigma_pm, reduced_chi2: rc };
  }
  const px = axes.xi.pm, pe = axes.eta.pm, sx = axes.xi.sigma, se = axes.eta.sigma;
  const pm = Math.hypot(px, pe);
  const sig = pm > 0 ? Math.hypot(sx * px, se * pe) / pm : Math.sqrt((sx ** 2 + se ** 2) / 2);
  return { axes, pm_mas_yr: pm, sigma_mas_yr: sig, snr: sig > 0 ? pm / sig : 0.0 };
}

export function hypotheticalVisit(ctx, dtYears, position = "static", errorFactor = 1.0, detect = 5.0) {
  if (!ctx.available || !ctx.validated) return { available: false, why: ctx.why || "the refit does not reproduce the recorded fit, so no what-if is computed" };
  if (!(dtYears > 0 && dtYears <= 20) || !(errorFactor >= 0.1 && errorFactor <= 10) || !["static", "track"].includes(position))
    return { available: false, why: "dt_years must be in (0, 20], error_factor in [0.1, 10], position 'static' or 'track'" };
  const v = ctx.visits;
  const t = v.map((x) => x.t_yr);
  const tn = Math.max(...t) + dtYears;
  const nv = {};
  for (const ax of ["xi", "eta"]) {
    const y = v.map((x) => x[`${ax}_mas`]), s = v.map((x) => x[`sig_${ax}_mas`]);
    if (position === "static") { const w = s.map((q) => 1 / q ** 2); nv[ax] = pySum(w.map((wi, i) => wi * y[i])) / pySum(w); }
    else { const r = wls(t, y, s); nv[ax] = r.position + r.pm * tn; }
    nv[`sig_${ax}`] = [...s].sort((a, b) => a - b)[Math.floor(s.length / 2)] * errorFactor;
  }
  const r = motionRefit([...t, tn], [...v.map((x) => x.xi_mas), nv.xi], [...v.map((x) => x.sig_xi_mas), nv.sig_xi], [...v.map((x) => x.eta_mas), nv.eta], [...v.map((x) => x.sig_eta_mas), nv.sig_eta]);
  const b = ctx.refit;
  return { available: true, hypothetical: true, visit: { t_yr: tn, position, ...nv },
    before: { pm_mas_yr: b.pm_mas_yr, sigma_mas_yr: b.sigma_mas_yr, snr: b.snr, detected: b.snr >= detect },
    after: { pm_mas_yr: r.pm_mas_yr, sigma_mas_yr: r.sigma_mas_yr, snr: r.snr, detected: r.snr >= detect, reduced_chi2: { xi: r.axes.xi.reduced_chi2, eta: r.axes.eta.reduced_chi2 } },
    rule: `detection |μ|/σ ≥ ${pyG(detect)} (ASSESS-2); only the fit significance is recomputed: ASSESS-2's catalogue and registration checks need fields a hypothetical visit does not have`,
    note: "Hypothetical: a visit that was not observed. It is never stored as an observation." };
}

// ------------------------------------------------------------------ reproduction network (REPRONET-1)
export const REPRO_SCHEMA = "skytrace.reproduction/1";
const REPRO_REQUIRED = ["schema", "record", "dataset", "software", "configuration", "methods", "stages", "outcomes", "environment", "limitations"];
const STAGE_ORDER = ["ingestion", "validation", "registration", "measurement", "matching", "statistics", "assessment"];
const eqJ = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

export async function reproValidate(m) {
  if (!m || typeof m !== "object" || Array.isArray(m)) return ["a manifest must be an object"];
  const errs = REPRO_REQUIRED.filter((k) => !(k in m)).map((k) => `missing field ${k}`);
  if (m.schema !== REPRO_SCHEMA) errs.push(`schema must be ${REPRO_SCHEMA}`);
  if (!errs.length) {
    const rest = Object.fromEntries(Object.entries(m).filter(([k]) => k !== "manifest_digest"));
    if ((await digest(rest)) !== m.manifest_digest) errs.push("manifest digest does not match its content (altered or incomplete)");
  }
  return errs;
}

function numClose(a, b, rel) {
  if (typeof a === "boolean" || typeof b === "boolean" || typeof a !== "number" || typeof b !== "number") return eqJ(a, b);
  return a === b || Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b), 1e-300);
}

export async function reproCompare(a, b, rel = 1e-9) {
  const cls = [], detail = [];
  const sa = Object.fromEntries(a.stages.map((s) => [s.id, s.digest])), sb = Object.fromEntries(b.stages.map((s) => [s.id, s.digest]));
  const keys = [...new Set([...Object.keys(sa), ...Object.keys(sb)])];
  const stageDiff = keys.filter((k) => sa[k] !== sb[k]).sort(cmp);
  const earliest = STAGE_ORDER.filter((k) => keys.includes(k)).find((k) => stageDiff.includes(k)) ?? null;
  const oq = [...new Set([...Object.keys(a.outcomes), ...Object.keys(b.outcomes)])];
  const oc = oq.filter((q) => (a.outcomes[q] || {}).category !== (b.outcomes[q] || {}).category).sort(cmp);
  if (!stageDiff.length && !oc.length) cls.push("exact match");
  else {
    const fa = Object.fromEntries(a.dataset.files.map((f) => [f.key, f.sha256])), fb = Object.fromEntries(b.dataset.files.map((f) => [f.key, f.sha256]));
    const fdiff = [...new Set([...Object.keys(fa), ...Object.keys(fb)])].filter((k) => fa[k] !== fb[k]).sort(cmp);
    if (a.dataset.manifest_sha256 !== b.dataset.manifest_sha256 || fdiff.length) {
      cls.push("different input data");
      detail.push(`input files differ: ${fdiff.length}` + (fdiff.length ? ` (e.g. ${fdiff[0]})` : ""));
    }
    const ca = a.configuration, cb = b.configuration;
    const pdiff = [...new Set([...Object.keys(ca), ...Object.keys(cb)])].filter((k) => k !== "bundle_manifest_sha256" && !eqJ(ca[k], cb[k])).sort(cmp);
    const mdiff = [...new Set([...Object.keys(a.methods), ...Object.keys(b.methods)])].filter((k) => !eqJ(a.methods[k], b.methods[k])).sort(cmp);
    if (pdiff.length || mdiff.length) { cls.push("methodological"); detail.push(pdiff.length ? "parameters differ: " + pdiff.join(", ") : "methods differ: " + mdiff.join(", ")); }
    const ea = a.environment || {}, eb = b.environment || {};
    const miss = [...new Set([...Object.keys(ea), ...Object.keys(eb)])].filter((k) => ((ea[k] ?? null) === null) !== ((eb[k] ?? null) === null)).sort(cmp);
    if (miss.length) { cls.push("missing dependency"); detail.push("present in one environment only: " + miss.join(", ")); }
    const close = Object.entries(a.outcomes).every(([q, o]) => Object.entries(o.metrics || {}).every(([k, v]) => numClose(v, ((b.outcomes[q] || {}).metrics || {})[k], rel)));
    if (!oc.length && close && !cls.includes("different input data") && !cls.includes("methodological")) { cls.push("numerical"); detail.push("outcome metrics agree within relative 1e-9"); }
    if (!cls.length) { cls.push("unexplained divergence"); detail.push("outputs differ with identical inputs, configuration, methods and dependencies"); }
  }
  const ea = a.environment || {}, eb = b.environment || {};
  const envDiff = [...new Set([...Object.keys(ea), ...Object.keys(eb)])].filter((k) => !eqJ(ea[k], eb[k])).sort(cmp);
  return { method: "REPRONET-1", a: a.record ?? null, b: b.record ?? null, status: cls[0], classes: cls, detail, stages_differing: stageDiff, earliest_divergence: earliest,
    outcomes_differing: oc, environment_differences: envDiff, valid_a: (await reproValidate(a)).length === 0, valid_b: (await reproValidate(b)).length === 0,
    note: "A match shows the calculation repeats. It does not show the result is scientifically valid." };
}

// ------------------------------------------------------------------ entities held in the session (SCI-ENTITY-1, rules E2–E5)
function env(etype, local, version, source, ref, createdAt, status, rule, label, h, data = {}) {
  return { id: `${etype}:${local}`, type: etype, version: Math.trunc(version), provenance: { source, ref, hash: h ?? null }, created_at: createdAt ?? null,
    status, status_rule: rule, label: String(label ?? "None").slice(0, 300), data: Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null && v !== undefined)) };
}

export function sessionEntities(s) {
  const h = s.content_hash ?? null;
  const out = [];
  for (const x of s.hypotheses || []) out.push(env("hypothesis", `user:${x.id}`, 1 + (x.versions || []).length, "session", `session:hypotheses/${x.id}`, x.created_at, "user-authored", "E5", x.statement, h, { tests: x.tests }));
  for (const x of s.experiments || []) out.push(env("experiment", x.id, 1, "session", `session:experiments/${x.id}`, x.created_at, "derived", "E4", `${x.template ?? "None"} experiment (${x.status ?? "None"})`, h, { template: x.template, run_status: x.status }));
  (s.scenarios || []).forEach((x, k) => {
    const sid = (x || {}).scenario_hash || `${k}`;
    out.push(env("counterfactual", String(sid).slice(0, 16), 1, "session", `session:scenarios/${k}`, (x || {}).at || s.created_at, "hypothetical", "E3", (x || {}).label || "counterfactual scenario", h));
  });
  (s.causal || []).forEach((x, k) => out.push(env("causal_relationship", `user:${k}`, 1, "session", `session:causal/${k}`, (x || {}).at || s.created_at, "user-authored", "E5",
    `${(x || {}).from ?? "None"} — ${(x || {}).rel ?? "None"} — ${(x || {}).to ?? "None"}`, h)));
  (s.negative || []).forEach((x, k) => out.push(env("limitation", `user:${(x || {}).id || k}`, 1, "session", `session:negative/${k}`, (x || {}).at || s.created_at, "user-authored", "E5",
    (x || {}).attempted || "negative-knowledge entry", h)));
  (s.debug || []).forEach((x, k) => {
    if ((x || {}).kind === "reproduction") out.push(env("reproduction", `${k}`, 1, "session", `session:debug/${k}`, x.at || s.created_at, "derived", "E4", `reproduction: ${x.verdict ?? "None"}`, h, { verdict: x.verdict }));
  });
  for (const e of s.history || []) {
    if (e.kind === "decision.record") out.push(env("research_decision", `seq${e.seq}`, 1, "session", `session:history/${e.seq}`, e.at, "user-authored", "E5", e.summary, h));
    out.push(env("provenance_event", `seq${e.seq}`, 1, "session", `session:history/${e.seq}`, e.at, "not a statement", "E2", `${e.kind}: ${e.summary}`, h));
  }
  return out;
}

// ------------------------------------------------------------------ causal proposals (CAUSAL-1)
export function causalWarnings(session, models, causalWords) {
  const out = [];
  const byCause = {};
  for (const m of models) if (m.cause) (byCause[m.cause] ||= []).push(m);
  ((session || {}).causal || []).forEach((p, k) => {
    if (!p || typeof p !== "object" || Array.isArray(p)) return;
    const rel = String(p.rel || "").toLowerCase();
    if (!causalWords.some((w) => rel.includes(w)) && !["causal", "cause"].includes(rel)) return;
    const ms = byCause[String(p.from || "")] || [];
    const met = [...new Set(ms.flatMap((m) => Object.entries(m.criteria).filter(([, v]) => v).map(([c]) => c)))].sort(cmp);
    out.push({ index: k, proposal: `${p.from ?? "None"} — ${p.rel ?? "None"} — ${p.to ?? "None"}`, criteria_met: met,
      warning: "user-proposed causal claim; " + (met.length === 1 && met[0] === "C1" ? "the matching model meets correlation only" : !ms.length ? "no model in the lab has this cause"
        : `the matching model meets ${met.join(", ") || "no criterion"}`) + "; experimental support (C5) is not possible with archival data" });
  });
  return out;
}
