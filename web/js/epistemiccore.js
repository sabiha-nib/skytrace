// Phase 8 browser core: pure functions mirrored from the Python modules and parity-tested
// (tests/js/epistemic_parity.mjs ↔ tests/unit/test_epistemic.py):
//   trace            ← epistemic.trace          assertedWords  ← epistemic.asserted_words
//   diff             ← scidebug.diff            overlayBlindspots (session part of BLIND-1)
//   sigmaPm, pairPrecision ← futurelab           integrityCheck ← integrity.check
// They let the static preview trace claims, debug its recorded runs, check documents and plan scenarios without a server.

import { dumps } from "./canon.js";

// ------------------------------------------------------------------ reasoning graph
export function trace(graph, nodeId, direction = "back") {
  const ids = new Set(graph.nodes.map((n) => n.id));
  if (!ids.has(nodeId)) return { start: nodeId, direction, nodes: [], error: "unknown node" };
  const adj = new Map();
  for (const e of graph.edges) {
    const [a, b] = direction === "back" ? [e.target, e.source] : [e.source, e.target];
    if (!adj.has(a)) adj.set(a, []);
    adj.get(a).push(b);
  }
  const dist = new Map([[nodeId, 0]]);
  const q = [nodeId];
  while (q.length) {
    const x = q.shift();
    for (const y of [...(adj.get(x) || [])].sort(cmp)) {
      if (!dist.has(y)) { dist.set(y, dist.get(x) + 1); q.push(y); }
    }
  }
  const kinds = new Map(graph.nodes.map((n) => [n.id, n.kind]));
  const found = [...dist.entries()].filter(([i]) => i !== nodeId).map(([i, d]) => [d, i]).sort((a, b) => a[0] - b[0] || cmp(a[1], b[1]));
  const byKind = {};
  for (const [, i] of found) byKind[kinds.get(i)] = (byKind[kinds.get(i)] || 0) + 1;
  return { start: nodeId, direction, nodes: found.map(([d, i]) => ({ id: i, depth: d })), by_kind: byKind };
}

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// ------------------------------------------------------------------ wording
export const NEGATORS = ["not", "no", "never", "without", "nor", "cannot"];
const isAlnum = (c) => /[\p{L}\p{N}]/u.test(c);

export function assertedWords(text, words) {
  const low = (text || "").toLowerCase();
  const hits = new Set();
  for (const w of words) {
    let start = 0;
    for (;;) {
      const i = low.indexOf(w, start);
      if (i < 0) break;
      start = i + 1;
      const beforeOk = i === 0 || !isAlnum(low[i - 1]);
      const after = i + w.length;
      const afterOk = after >= low.length || !isAlnum(low[after]);
      if (!(beforeOk && afterOk)) continue;
      let clause = low.slice(0, i);
      const cut = Math.max(...[".", "!", "?", ";", ":"].map((c) => clause.lastIndexOf(c)));
      clause = clause.slice(cut + 1);
      const prev = [...clause].map((c) => (isAlnum(c) ? c : " ")).join("").split(/\s+/).filter(Boolean).slice(-4);
      if (!prev.some((t) => NEGATORS.includes(t))) { hits.add(w); break; }
    }
  }
  return [...hits].sort();
}

// ------------------------------------------------------------------ differential debugging (SCIDEBUG-1)
export const DEBUG_STAGES = [["ingestion", "Data ingestion", ["discover", "select"]], ["validation", "File validation", ["inspect"]],
  ["registration", "Registration (reference catalogue and per-exposure plate solutions)", ["references", "measure.plate"]],
  ["measurement", "Measurement", ["measure"]], ["matching", "Wavelength matching", ["pairs"]],
  ["statistics", "Statistical calculation", ["variability", "spectral_context", "spectrum", "astrometry"]], ["assessment", "Assessment", ["assess"]]];
export const REL_EQUIV = 1e-9;

function steps(record, names) {
  const out = [];
  (record.events || []).forEach((e, i) => {
    for (const n of names) {
      if (n === "measure.plate" && e.step === "measure") out.push([i, { step: "measure.plate", key: (e.data || {}).obs_id, data: (e.data || {}).plate ?? null }]);
      else if (e.step === n) out.push([i, e]);
    }
  });
  return out;
}

const isNum = (v) => typeof v === "number";
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

function brief(v) {
  if (typeof v === "string") return v.slice(0, 80);
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (isNum(v)) { try { return dumps(v); } catch { return String(v); } }
  if (Array.isArray(v)) return `[${v.length} items]`;
  return `{${Object.keys(v).length} keys}`;
}

function leaves(a, b, path, out, st) {
  if (isObj(a) && isObj(b)) {
    for (const k of [...new Set([...Object.keys(a), ...Object.keys(b)])].sort(cmp)) {
      if (!(k in a) || !(k in b)) {
        st.structural++;
        if (out.length < 20) out.push({ path: `${path}.${k}`, a: brief(a[k]), b: brief(b[k]), kind: "only in " + (!(k in a) ? "b" : "a") });
      } else leaves(a[k], b[k], `${path}.${k}`, out, st);
    }
    return;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) { st.structural++; if (out.length < 20) out.push({ path, a: `${a.length} items`, b: `${b.length} items`, kind: "length" }); }
    for (let j = 0; j < Math.min(a.length, b.length); j++) leaves(a[j], b[j], `${path}[${j}]`, out, st);
    return;
  }
  if (isNum(a) && isNum(b)) {
    if (a === b || (a !== a && b !== b)) return;
    const rel = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1e-300);
    st.numeric++;
    st.max_rel = Math.max(st.max_rel, rel);
    if (out.length < 20) out.push({ path, a, b, kind: "numeric", rel });
    return;
  }
  if (!sameScalar(a, b)) { st.other++; if (out.length < 20) out.push({ path, a: brief(a), b: brief(b), kind: "value" }); }
}

function sameScalar(a, b) {
  if (a === b) return true;
  if ((a === null || a === undefined) && (b === null || b === undefined)) return true;
  if (typeof a === "object" && typeof b === "object" && a && b) return JSON.stringify(a) === JSON.stringify(b);
  return false;
}

export function compareValues(a, b) {
  const out = [], st = { numeric: 0, structural: 0, other: 0, max_rel: 0 };
  leaves(a, b, "$", out, st);
  let kind;
  if (!(st.numeric || st.structural || st.other)) kind = "identical";
  else if (!st.structural && !st.other && st.max_rel <= REL_EQUIV) kind = "numerically equivalent";
  else kind = "different";
  return { kind, differences: out, ...st };
}

const ASSUMPTION_KEYS = ["aperture_radius_px", "fit_half_size_px", "wavelength_tolerance_channels", "wavelength_margin_um", "epoch_clip_sigma",
  "epoch_gap_days", "apply_parallax", "reference_quality_cut", "photometry_same_release", "detectors"];
const eqv = (x, y) => JSON.stringify(x ?? null) === JSON.stringify(y ?? null);

export function diff(a, b) {
  const pa = a.parameters || {}, pb = b.parameters || {};
  const params = [...new Set([...Object.keys(pa), ...Object.keys(pb)])].sort(cmp).filter((k) => k !== "methods" && !eqv(pa[k], pb[k]))
    .map((k) => ({ key: k, a: pa[k] ?? null, b: pb[k] ?? null }));
  const ma = pa.methods || {}, mb = pb.methods || {};
  const methods = [...new Set([...Object.keys(ma), ...Object.keys(mb)])].sort(cmp).filter((k) => !eqv(ma[k], mb[k])).map((k) => ({ role: k, a: ma[k] ?? null, b: mb[k] ?? null }));
  const sa = a.software || {}, sb = b.software || {};
  const software = [...new Set([...Object.keys(sa), ...Object.keys(sb)])].sort(cmp).filter((k) => !eqv(sa[k], sb[k])).map((k) => ({ package: k, a: sa[k] ?? null, b: sb[k] ?? null }));
  const inputs = { bundle_a: pa.bundle ?? null, bundle_b: pb.bundle ?? null, manifest_a: pa.bundle_manifest_sha256 ?? null, manifest_b: pb.bundle_manifest_sha256 ?? null,
    same: (pa.bundle_manifest_sha256 ?? null) === (pb.bundle_manifest_sha256 ?? null) };
  const stages = []; let earliest = null;
  for (const [sid, name, st] of DEBUG_STAGES) {
    const ea = steps(a, st).map(([, e]) => e), eb = steps(b, st).map(([, e]) => e);
    if (!ea.length && !eb.length) continue;
    const pick = (e) => ({ step: e.step, status: e.status ?? null, data: e.data ?? null });
    const c = compareValues(ea.map(pick), eb.map(pick));
    stages.push({ id: sid, name, n_a: ea.length, n_b: eb.length, ...c });
    if (earliest === null && c.kind !== "identical") earliest = sid;
  }
  const assumptions = params.filter((p) => ASSUMPTION_KEYS.includes(p.key)).map((p) => ({ key: p.key, a: p.a, b: p.b }));
  const explanation = [];
  if (!inputs.same) explanation.push("the inputs differ (different bundle manifest)");
  if (params.length) explanation.push(`${params.length} parameter(s) differ: ` + params.slice(0, 6).map((p) => p.key).join(", "));
  if (methods.length) explanation.push(`${methods.length} method version(s) differ`);
  if (software.length) explanation.push("software versions differ: " + software.map((s) => `${s.package} ${s.a} → ${s.b}`).join(", "));
  if (earliest && !explanation.length) explanation.push("inputs, parameters, methods and software agree, so the difference arises from numerical behaviour or an unrecorded dependency");
  return { method: "SCIDEBUG-1", a: a.content_hash ?? null, b: b.content_hash ?? null, identical_hash: (a.content_hash ?? null) === (b.content_hash ?? null),
    inputs, parameters: params, assumptions, methods, software,
    metadata: ["schema", "target"].filter((k) => !eqv(a[k], b[k])).map((k) => ({ key: k, a: a[k] ?? null, b: b[k] ?? null })),
    stages, earliest_divergence: earliest, explanation };
}

// ------------------------------------------------------------------ blindspots (session part of BLIND-1)
export function overlayBlindspots(base, session, causalWords) {
  const s = session || {};
  const examined = new Set(s.examined || []);
  const rows = base.checks.map((r) => {
    if (r.id === "epochs") {
      const visits = r.visits || [];
      const seen = visits.map((v) => (r.pairs || []).some((p) => examined.has(p) && p.split("|").some((k) => v.members.includes(k))));
      const n = seen.filter(Boolean).length;
      const state = !visits.length ? "not applicable" : n === visits.length ? "examined" : n ? "partially examined" : "not examined";
      return { ...r, state, detail: `${n} of ${visits.length} visits have a compared pair you inspected by eye` };
    }
    if (r.id === "language") {
      const notes = (s.notebook || []).filter((b) => b.author === "user");
      if (!notes.length) return { ...r, state: "not applicable", detail: "no notebook text of yours yet" };
      const hits = notes.filter((b) => assertedWords(b.text || "", causalWords).length);
      return { ...r, state: hits.length ? "partially examined" : "examined",
        detail: hits.length ? `${hits.length} of your note(s) assert causal or discovery language` : `${notes.length} note(s) checked; none asserts causation or discovery`,
        items: hits.map((b) => b.id) };
    }
    if (r.id === "boundaries") {
      const scen = (s.scenarios || []).filter((x) => x && x.scenario && ["threshold", "parameter", "error_scale"].includes(x.scenario.kind)).length;
      const stab = (s.experiments || []).filter((x) => x && ["sensitivity", "robustness", "parameter"].includes(x.template) && x.status === "completed").length;
      return { ...r, state: scen + stab ? "examined" : "not examined", detail: `${stab} completed sensitivity experiment(s), ${scen} counterfactual scenario(s) in this session` };
    }
    return r;
  });
  const counts = {};
  for (const st of base.states) counts[st] = rows.filter((r) => r.state === st).length;
  return { ...base, checks: rows, counts };
}

// ------------------------------------------------------------------ FutureLab (FUTURE-1)
export function sigmaPm(times, sigmas) {
  if (times.length < 2) return null;
  const w = sigmas.map((s) => 1 / s ** 2);
  const sw = w.reduce((p, x) => p + x, 0);
  const st = w.reduce((p, x, i) => p + x * times[i], 0);
  const stt = w.reduce((p, x, i) => p + x * times[i] * times[i], 0);
  const det = sw * stt - st * st;
  return det > 0 ? Math.sqrt(sw / det) : null;
}

export function pairPrecision(fraction, flux, scale = 1) { return fraction * flux / (5 * Math.SQRT2 * Math.max(1, scale)); }

// ------------------------------------------------------------------ integrity firewall (INTEG-1)
const NUM_RE = () => /(?<![A-Za-z0-9_\-.:])-?\d+(?:\.\d+)?(?:[eE]-?\d+)?(?![A-Za-z0-9_]|\.\d)/g;
const SYN_RE = /(?<![a-z0-9:_\-])(synthetic|generated|simulated)(?![a-z0-9:_\-])/;
const METHOD_RE = () => /\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*-\d+\b/g;
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const roundSig = (x) => Number(x.toPrecision(10));

function bisectLeft(a, x) { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] < x) lo = m + 1; else hi = m; } return lo; }

function grounded(tok, nums, pct) {
  let x = Number(tok);
  if (Number.isNaN(x)) return true;
  const dec = tok.includes(".") ? tok.split(".")[1].split(/[eE]/)[0].length : 0;
  const sig = tok.replace(/^-/, "").split(/[eE]/)[0].replace(".", "").replace(/^0+/, "").length;
  let half;
  if (sig > 10) { x = roundSig(x); half = Math.abs(x) * 5e-10; }
  else half = !tok.toLowerCase().includes("e") ? 0.5 * 10 ** (-dec) : Math.abs(x) * 1e-6;
  for (const target of pct ? [x, x / 100] : [x]) {
    const h = pct && target !== x ? half / 100 : half;
    const lo = target - h - 1e-12 * Math.abs(target), hi = target + h + 1e-12 * Math.abs(target);
    let i = bisectLeft(nums, lo);
    if (i < nums.length && nums[i] <= hi) return true;
    i = bisectLeft(nums, -hi);
    if (i < nums.length && nums[i] <= -lo) return true;
  }
  return false;
}

export function integrityCheck(text, f, spec) {
  const low = text.toLowerCase();
  const R = [];
  const add = (cid, ok, detail, items = []) => {
    const c = spec.checks.find((x) => x[0] === cid);
    R.push({ id: cid, name: c[2], rule: c[3], severity: c[1], ok, detail, items: items.slice(0, 15) });
  };
  if (f.synthetic) { const ok = SYN_RE.test(low); add("I1", ok, ok ? "the text discloses synthetic data" : "the record is synthetic but the text never says so"); }
  else add("I1", true, "the record is not synthetic");
  const nums = f.numbers || [];
  const bad = [];
  for (const m of text.matchAll(NUM_RE())) {
    const tok = m[0], x = Number(tok);
    if (Number.isNaN(x)) continue;
    if (!tok.includes(".") && !tok.toLowerCase().includes("e") && (Math.abs(x) <= 10 || (Math.abs(x) >= 1900 && Math.abs(x) <= 2100))) continue;
    const pct = text.slice(m.index + tok.length, m.index + tok.length + 1) === "%";
    if (!grounded(tok, nums, pct)) bad.push(tok);
  }
  const uniq = [...new Set(bad)];
  add("I2", !bad.length, bad.length ? `${bad.length} number(s) not found in the record` : "every number checked is in the record", uniq);
  const h = f.content_hash || "";
  const cited = !!h && [64, 16, 12].some((k) => low.includes(h.slice(0, k)));
  add("I3", cited, cited ? "the run's content hash is cited" : `cite the run (content hash ${h.slice(0, 12)}…) so the text can be traced`);
  const wrong = [];
  for (const [phrase, q, cat] of spec.phrases) {
    const rec = (f.categories || {})[q];
    if (assertedWords(low, [phrase]).length && rec !== undefined && rec !== null && rec !== cat) wrong.push(`“${phrase}” but the recorded ${q} outcome is ${rec}`);
  }
  add("I4", !wrong.length, wrong.length ? wrong.join("; ") : "no asserted outcome contradicts the record", wrong);
  const prose = text.replace(/```[\s\S]*?```/g, (m) => " ".repeat(m.length));
  const nounit = [];
  for (const m of prose.matchAll(NUM_RE())) {
    const tok = m[0];
    if (!tok.includes(".")) continue;
    const end = m.index + tok.length;
    const after = prose.slice(end, end + 14).toLowerCase().replace(/^[ ±]+/, "");
    const before = prose.slice(Math.max(0, m.index - 12), m.index).toLowerCase().replaceAll("|", " ").replaceAll("/", " ");
    const bt = before.replace(/\s+$/, "");
    if (spec.units.some((u) => after.startsWith(u.trim())) || spec.dimless.some((d) => new RegExp("(^|[^a-z_])" + esc(d) + "\\s*[=:≈≥≤<>]?\\s*[-−]?$").test(bt))) continue;
    if (/^\s*(±|\+\/-)/.test(prose.slice(end, end + 4)) || ["×", ")"].some((c) => prose.slice(end, end + 2).trim().startsWith(c))) continue;
    nounit.push(tok);
  }
  add("I5", !nounit.length, nounit.length ? `${nounit.length} decimal number(s) without a unit` : "decimal numbers carry units or are named dimensionless quantities", nounit);
  const pw = assertedWords(low, spec.prob_words);
  add("I6", !pw.length, pw.length ? `asserts: ${pw.join(", ")}` : "no probability language asserted", pw);
  const sim = ["counterfactual", "scenario"].some((w) => low.includes(w));
  const lab = ["hypothetical", "not an observation"].some((w) => low.includes(w));
  add("I7", !sim || lab, lab || !sim ? "scenario results are labelled" : "counterfactual or scenario results are mentioned without 'hypothetical' or 'not an observation'");
  add("I8", low.includes("limitation"), low.includes("limitation") ? "limitations are mentioned" : "the text never mentions its limitations");
  add("I9", !!f.hash_ok, f.hash_ok ? "the record's hash recomputes" : "the record's hash does not recompute");
  const acc = new Set(f.accepted_pairs || []), keys = f.obs_keys || [];
  const badp = [];
  for (const s of text.split(/(?<=[.!?])\s+|\n+/).filter((x) => x && x.trim())) {
    const found = [...new Set(keys.filter((k) => s.includes(k)))].sort((x, y) => s.indexOf(x) - s.indexOf(y));
    if (found.length >= 2 && /↔|→|\svs\.?\s|\sand\s/.test(s)) {
      for (let i = 0; i < found.length - 1; i++) {
        const a = found[i], b = found[i + 1];
        if (!acc.has(`${a}|${b}`) && !acc.has(`${b}|${a}`)) badp.push(`${a} / ${b}`);
      }
    }
  }
  add("I10", !badp.length, badp.length ? `${badp.length} compared pair(s) not accepted by WLMATCH-2` : "every compared pair named is an accepted pair", badp);
  const known = new Set(f.methods || []);
  const unk = [...new Set([...text.matchAll(METHOD_RE())].map((m) => m[0]))].sort(cmp)
    .filter((m) => !known.has(m) && ![...known].some((k) => m === k.split("/")[0])).filter((m) => !/^(SYN|SYNTHETIC|D|Q|T|H|NX|QF|N)-/.test(m));
  add("I11", !unk.length, unk.length ? `unregistered method identifier(s): ${unk.join(", ")}` : "every method identifier is registered", unk);
  const ow = assertedWords(low, spec.overstate);
  add("I12", !ow.length, ow.length ? `asserts: ${ow.join(", ")}` : "no overstated wording asserted", ow);
  const high = R.filter((r) => !r.ok && r.severity === "high"), warn = R.filter((r) => !r.ok && r.severity === "warning");
  return { method: "INTEG-1", outcome: high.length ? "needs attention" : warn.length ? "ready with warnings" : "ready", checks: R, n_high: high.length, n_warning: warn.length,
    note: "Advice only: the export is never blocked and the text is never changed." };
}
