// Pure Phase 7 rules that depend on the research session (applied in the browser to the server's session-free report),
// plus browser ports of TWIN-1 comparison and the angular separation used by the Cosmic Atlas. Every function here is
// parity-tested against its Python counterpart (tests/unit/test_frontier.py → tests/js/frontier_parity.mjs):
//   overlayHorizon      ≡ possibility.horizon(..., session, ..., has_stability)
//   overlayChallenges   ≡ adversarial.challenges(..., session=...)
//   overlayReview       ≡ review.review(..., session, plan_intent)
//   twinCompare         ≡ twin.compare
//   angularSeparationDeg ≡ coords-free Vincenty formula (tests compare with a Python implementation)

const FEAS = ["can run now", "needs the server", "needs new data", "needs a new method"];
const CATS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"];
const CAT_NAME = { C1: "Unexamined significant pairs", C2: "Unsupported or conflicting evidence", C3: "Incomplete candidate assessment",
  C4: "Unresolved hypotheses", C5: "Unexplored parameter space", C6: "Unexplored compatible epochs", C7: "Unvalidated analytical assumptions",
  C8: "Missing calibration metadata", C9: "Unused measurements", C10: "Incomplete provenance" };
const SEVERITY = ["critical", "major", "moderate", "note"];

export function overlayHorizon(h, session, hasStability, server) {
  const s = session || {};
  const examined = new Set(s.examined || []);
  const seqViewed = new Set((s.history || []).filter((x) => x.kind === "sequence.view").map((x) => x.ref));
  const scen = s.scenarios || [];
  const runnable = server ? "can run now" : "needs the server";
  let cards = h.cards.filter((c) => {
    if (c.category === "C1") return !examined.has((c.refs || []).slice(0, 2).join("|"));
    if (c.category === "C6") return !seqViewed.has(c.id.slice(2));
    return c.category !== "C5";
  }).map((c) => ({ ...c }));
  if (!hasStability || !scen.length) {
    cards.push({ id: "H-PARAMS", category: "C5", category_name: CAT_NAME.C5, question: "Do the outcomes depend on analysis choices or thresholds?",
      prompted_by: [...(!hasStability ? ["no STAB-1 result for this run"] : []), ...(!scen.length ? ["no CF-1 scenario in this session"] : [])],
      required_data: ["the bundle (re-run) or the record (re-assessment)"], available_data: ["the record and bundle"],
      method: "run_stability · CF-1 parameter/threshold/error-scale scenarios", limitations: ["only the stated changes are examined"],
      feasibility: !hasStability ? runnable : "can run now", expected_output: "which outcomes change under which stated change", refs: [] });
  }
  cards.sort((a, b) => FEAS.indexOf(a.feasibility) - FEAS.indexOf(b.feasibility) || CATS.indexOf(a.category) - CATS.indexOf(b.category) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  cards.forEach((c, i) => {
    c.rank = i + 1;
    c.priority_reason = `${c.feasibility}; category ${c.category} (${CAT_NAME[c.category]}) is position ${CATS.indexOf(c.category) + 1} of ${CATS.length} in the stated order`;
  });
  const counts = Object.fromEntries(CATS.map((k) => [k, cards.filter((c) => c.category === k).length]));
  const byFeas = Object.fromEntries(FEAS.map((f) => [f, cards.filter((c) => c.feasibility === f).length]));
  return { ...h, cards, counts, by_feasibility: byFeas, map: mapOf(cards) };
}

function mapOf(cards) {
  const nodes = new Map(), edges = [];
  for (const c of cards) {
    nodes.set(c.id, { id: c.id, kind: "question", label: c.question.slice(0, 90) });
    const m = "method:" + c.method.slice(0, 60);
    if (!nodes.has(m)) nodes.set(m, { id: m, kind: "method", label: c.method.slice(0, 60) });
    edges.push({ s: c.id, t: m, rel: "tested by" });
    for (const p of c.prompted_by.slice(0, 2)) {
      const e = "evidence:" + String(p).slice(0, 60);
      if (!nodes.has(e)) nodes.set(e, { id: e, kind: "evidence", label: String(p).slice(0, 60) });
      edges.push({ s: e, t: c.id, rel: "prompted" });
    }
    for (const r of c.required_data.slice(0, 1)) {
      const q = "requires:" + String(r).slice(0, 60);
      if (!nodes.has(q)) nodes.set(q, { id: q, kind: "required evidence", label: String(r).slice(0, 60) });
      edges.push({ s: c.id, t: q, rel: "needs" });
    }
  }
  return { nodes: [...nodes.values()], edges };
}

export function overlayChallenges(asl, session) {
  const s = session || {};
  const examined = new Set(s.examined || []);
  const notes = {};
  for (const a of s.annotations || []) if (a.target?.kind === "challenge") (notes[a.target.id] ||= []).push(a.text || "");
  const out = [];
  for (const c0 of asl.challenges) {
    let c = { ...c0 };
    if (c.id === "B-PAIRS") {
      const left = (c.pairs || []).filter((k) => { const [a, b] = k.split("|"); return !examined.has(`${a}|${b}`) && !examined.has(`${b}|${a}`); });
      if (!left.length) continue;
      c = { ...c, issue: `${left.length} significant pair(s) not yet inspected by eye in this session`, evidence: left.slice(0, 5).map((k) => k.replace("|", " → ")) };
    }
    if (notes[c.id] && c.status === "open") c = { ...c, status: "acknowledged", notes: notes[c.id] };
    out.push(c);
  }
  return { ...asl, challenges: out, counts: Object.fromEntries(SEVERITY.map((k) => [k, out.filter((c) => c.severity === k).length])) };
}

export function overlayReview(rv, session, planIntent, causalWords) {
  const s = session || {};
  const q = s.question?.text || "";
  const F = rv.findings.filter((f) => !(f.role === "methods" && (f.check === "The research question is stated" || f.check === "The question maps to registered methods"))
    && !(f.role === "interpretation" && f.check === "Notes avoid unsupported causal or discovery language"));
  const lead = [{ role: "methods", role_name: "Methods reviewer", check: "The research question is stated", outcome: q ? "met" : "not met", cites: ["session.question"],
    detail: q ? `“${q.slice(0, 160)}”` : "No research question in the session (Command Center → Research question)." }];
  if (q) {
    const ok = planIntent !== null && planIntent !== undefined && planIntent !== "unknown";
    lead.push({ role: "methods", role_name: "Methods reviewer", check: "The question maps to registered methods", outcome: ok ? "met" : "not met", cites: ["PLAN-1 intent"],
      detail: ok ? `intent: ${planIntent}` : "PLAN-1 could not map the question to registered actions." });
  }
  const texts = (s.notebook || []).filter((b) => b.author === "user").map((b) => b.text || "");
  const hits = [...new Set(texts.flatMap((t) => causalWords.filter((w) => t.toLowerCase().includes(w))))].sort();
  const causal = { role: "interpretation", role_name: "Interpretation reviewer", check: "Notes avoid unsupported causal or discovery language",
    outcome: hits.length ? "not met" : "met", cites: ["notebook (your text)", "REVIEW-1 word list"],
    detail: hits.length ? "found: " + hits.join(", ") : (texts.length ? "none of the listed words found" : "no notebook text yet") };
  const order = ["methods", "data", "evidence", "reproducibility", "interpretation"];
  const out = [];
  for (const r of order) {
    if (r === "methods") out.push(...lead);
    out.push(...F.filter((f) => f.role === r));
    if (r === "interpretation") out.push(causal);
  }
  const counts = Object.fromEntries(order.map((r) => [r, { met: 0, "not met": 0, "not checked": 0 }]));
  for (const f of out) counts[f.role][f.outcome] += 1;
  return { ...rv, findings: out, counts };
}

function leaves(v, path, out) {
  if (v && typeof v === "object" && !Array.isArray(v)) {
    const ks = Object.keys(v).sort();
    if (!ks.length) out.set(path, {});
    for (const k of ks) leaves(v[k], path ? `${path}.${k}` : k, out);
  } else if (Array.isArray(v)) {
    if (!v.length) out.set(path, []);
    v.forEach((x, i) => leaves(x, `${path}[${i}]`, out));
  } else out.set(path, v);
  return out;
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function twinCompare(a, b, sections) {
  if (a.kind !== b.kind) return { method: "TWIN-1", comparable: false, reason: `different kinds (${a.kind} vs ${b.kind})` };
  const differences = {};
  for (const s of sections) {
    const la = leaves(a.sections[s] || {}, "", new Map()), lb = leaves(b.sections[s] || {}, "", new Map());
    const keys = [...new Set([...la.keys(), ...lb.keys()])].sort();
    differences[s] = keys.filter((k) => !same(la.get(k), lb.get(k)) || la.has(k) !== lb.has(k))
      .map((k) => ({ path: k, a: la.has(k) ? la.get(k) : null, b: lb.has(k) ? lb.get(k) : null }));
  }
  return { method: "TWIN-1", comparable: true, kind: a.kind, a: a.id, b: b.id,
    identical: a.content_hash === b.content_hash || !Object.values(differences).some((d) => d.length), differences,
    counts: Object.fromEntries(Object.entries(differences).map(([k, v]) => [k, v.length])) };
}

/** Great-circle angular separation in degrees (Vincenty form, stable at all separations). */
export function angularSeparationDeg(ra1, dec1, ra2, dec2) {
  const r = Math.PI / 180;
  const [l1, b1, l2, b2] = [ra1 * r, dec1 * r, ra2 * r, dec2 * r];
  const dl = l2 - l1;
  const num = Math.hypot(Math.cos(b2) * Math.sin(dl), Math.cos(b1) * Math.sin(b2) - Math.sin(b1) * Math.cos(b2) * Math.cos(dl));
  const den = Math.sin(b1) * Math.sin(b2) + Math.cos(b1) * Math.cos(b2) * Math.cos(dl);
  return Math.atan2(num, den) / r;
}

// ICRS (J2000) → Galactic, with the standard rotation matrix (Hipparcos/ICRS definition of the galactic frame).
const G = [[-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
           [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
           [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669]];
export function icrsToGalactic(raDeg, decDeg) {
  const r = Math.PI / 180;
  const v = [Math.cos(decDeg * r) * Math.cos(raDeg * r), Math.cos(decDeg * r) * Math.sin(raDeg * r), Math.sin(decDeg * r)];
  const g = G.map((row) => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]);
  let l = Math.atan2(g[1], g[0]) / r;
  if (l < 0) l += 360;
  return [l, Math.asin(Math.max(-1, Math.min(1, g[2]))) / r];
}

/** "17h57m48.49847s" / "+04d41m36.1139s" (or decimal degrees) → degrees; null when not parseable. */
export function parseSexagesimal(s, isRa) {
  if (typeof s === "number") return s;
  if (typeof s !== "string") return null;
  const t = s.trim();
  if (/^[+-]?\d+(\.\d+)?$/.test(t)) return Number(t);
  const m = t.match(/^([+-]?)(\d+)[hd:\s]\s*(\d+)[m'′:\s]\s*([\d.]+)\s*[s"″]?$/);
  if (!m) return null;
  const v = Number(m[2]) + Number(m[3]) / 60 + Number(m[4]) / 3600;
  return (m[1] === "-" ? -1 : 1) * v * (isRa && /h/.test(t) ? 15 : 1);
}

/** TWIN-1 investigation twin, built in the browser from the session (port of twin.investigation; parity-tested). */
export async function investigationTwin(session, digest) {
  const s = session;
  const SECTIONS = ["inputs", "parameters", "methods", "measurements", "outputs", "assumptions", "provenance"];
  const sections = {
    inputs: { target_id: s.target_id ?? null, runs: (s.runs || []).map((r) => ({ content_hash: r.content_hash, label: r.label })) },
    parameters: { question: s.question?.text ?? null },
    outputs: { n_notes: (s.notebook || []).length, n_plans: (s.plans || []).length, n_experiments: (s.experiments || []).length, n_hypotheses: (s.hypotheses || []).length },
    assumptions: { hypotheses: (s.hypotheses || []).map((h) => h.statement).slice(0, 20) },
    provenance: { session_hash: s.content_hash ?? null, history_events: (s.history || []).length },
  };
  const derived = [...new Set([...(s.runs || []).map((r) => r.content_hash), ...(s.content_hash ? [s.content_hash] : [])])].sort();
  const body = { schema: "skytrace.twin/1", method: "TWIN-1", kind: "investigation", id: String(s.session_id), version: 1,
    semantics: "A computational record of what Skytrace knows and did, not a physical model of an astronomical object.",
    sections: Object.fromEntries(SECTIONS.map((k) => [k, sections[k] || {}])), derived_from: derived };
  return { ...body, content_hash: await digest(body) };
}
