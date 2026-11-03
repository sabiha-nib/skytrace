// HANDOFF-1: the discovery handoff protocol (skytrace.handoff/1). Port of src/skytrace/handoff.py (parity-tested).
// A handoff describes recorded work; importing one is never a reproduction and implies no live collaboration.

import { digest } from "./canon.js";

export const SCHEMA = "skytrace.handoff/1";
export const VERSIONS = ["1.0"];
const LANGS = ["en", "bn", "hi", "es", "fr", "de"];
export const NOTE = "This handoff describes recorded work. It implies no live collaboration; importing it is not a reproduction, and a "
  + "reproduction shows that a calculation repeats, not that its conclusion is true.";
const REQUIRED = { schema: "string", version: "string", created_at: "string", generator: "object", language: "object", investigation: "object",
  established: "list", open: "list", unknown: "list", evidence_needed: "list", provenance: "list", limitations: "list", reproduction: "object", note: "string", digest: "string" };
const HEX64 = /^[0-9a-f]{64}$/;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const MAX = 200;
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const typeOk = (v, t) => (t === "object" ? isObj(v) : t === "list" ? Array.isArray(v) : typeof v === t);

export async function build(rec, uni, lang, meta, createdAt, version) {
  const outs = rec.events.filter((e) => e.step === "assess");
  const outcomes = outs.length ? ((outs[0].data || {}).outcomes || []) : [];
  const prov = [], seen = new Set();
  for (const e of rec.events) for (const p of e.provenance || []) {
    const k = `${p.source}\u0000${p.content_sha256}`;
    if (seen.has(k)) continue;
    seen.add(k);
    prov.push({ source: p.source || "", origin: p.origin || "", release: p.release || "", retrieved_at: p.retrieved_at || "", content_sha256: p.content_sha256 || "" });
  }
  const synthetic = prov.some((p) => p.origin === "synthetic");
  const neg = uni.negative || {};
  const lims = [...new Set(outcomes.flatMap((o) => o.limitations || []))].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const doc = {
    schema: SCHEMA, version: VERSIONS[VERSIONS.length - 1], created_at: createdAt,
    generator: { software: "skytrace", version },
    language: { interface: LANGS.includes(lang) ? lang : "en", content: "en",
      translation: { status: meta.status || "source language", translator: meta.translator || "", reviewed: !!meta.reviewed } },
    investigation: { target: rec.target || "", content_hash: rec.content_hash || "", synthetic, record_schema: rec.schema || "" },
    established: outcomes.map((o) => ({ question: o.question || "", category: o.category || "", statement: o.statement || "", rule: "ASSESS-2" })).slice(0, MAX),
    open: [...(uni.leads?.leads || []).map((l) => ({ id: l.id, kind: l.kind, statement: l.statement })),
      ...(neg.items || []).map((x, i) => [x, i]).filter(([x]) => x.distinction === "unresolved explanation")
        .map(([x, i]) => ({ id: `NEG-${i}`, kind: "unresolved explanation", statement: x.statement }))].slice(0, MAX),
    unknown: (neg.items || []).filter((x) => ["unknown quantity", "unexplored region", "insufficient sensitivity", "unavailable dataset"].includes(x.distinction))
      .map((x) => ({ distinction: x.distinction, statement: x.statement, does_not_mean: x.does_not_mean })).slice(0, MAX),
    evidence_needed: (uni.opportunities?.items || []).map((i) => ({ question: i.question || "", data_needed: i.data_needed || "", novelty_scope: i.novelty.scope })).slice(0, MAX),
    provenance: prov.slice(0, MAX),
    limitations: lims.slice(0, MAX),
    reproduction: { content_hash: rec.content_hash || "", parameters: rec.parameters || {},
      instruction: "re-run the analysis on the same data bundle with these parameters; an identical content hash means an identical result" },
    note: NOTE,
  };
  doc.digest = await digest(doc);
  return doc;
}

export async function validate(doc) {
  const errs = [];
  if (!isObj(doc)) return ["the handoff must be a JSON object"];
  if (doc.schema !== SCHEMA) return [`schema must be ${SCHEMA}`];
  if (!VERSIONS.includes(doc.version)) errs.push(`unknown version ${JSON.stringify(doc.version ?? null)}; this release reads ${VERSIONS.join(", ")}`);
  for (const [k, t] of Object.entries(REQUIRED)) {
    if (!(k in doc)) errs.push(`$.${k}: missing`);
    else if (!typeOk(doc[k], t)) errs.push(`$.${k}: must be ${t === "object" ? "an object" : t === "list" ? "a list" : "a string"}`);
  }
  if (errs.length) return errs;
  const extra = Object.keys(doc).filter((k) => !(k in REQUIRED)).sort();
  if (extra.length) errs.push("unknown field(s): " + extra.join(", "));
  if (!ISO.test(doc.created_at)) errs.push("$.created_at: must be an ISO 8601 time with a zone");
  const lg = doc.language;
  if (!LANGS.includes(lg.interface)) errs.push(`$.language.interface: must be one of ${LANGS.join(", ")}`);
  if (lg.content !== "en") errs.push("$.language.content: the scientific content is recorded in English (en)");
  if (!isObj(lg.translation) || typeof lg.translation.reviewed !== "boolean") errs.push("$.language.translation: must state the translation status and whether it was reviewed");
  const inv = doc.investigation;
  if (!HEX64.test(String(inv.content_hash || ""))) errs.push("$.investigation.content_hash: must be 64 hexadecimal digits");
  if (typeof inv.synthetic !== "boolean") errs.push("$.investigation.synthetic: must be true or false");
  else if (doc.provenance.some((p) => isObj(p) && p.origin === "synthetic") && !inv.synthetic)
    errs.push("$.investigation.synthetic: the provenance lists synthetic data, so the handoff must be labelled synthetic");
  for (const k of ["established", "open", "unknown", "evidence_needed", "provenance", "limitations"]) {
    if (doc[k].length > MAX) errs.push(`$.${k}: more than ${MAX} items`);
    if (doc[k].some((x) => !(isObj(x) || typeof x === "string"))) errs.push(`$.${k}: items must be objects or strings`);
  }
  if (doc.reproduction.content_hash !== inv.content_hash) errs.push("$.reproduction.content_hash: must equal the investigation's content hash");
  if (!errs.length) {
    const body = { ...doc };
    delete body.digest;
    let d;
    try { d = await digest(body); } catch (e) { return [`not canonicalisable: ${e.message}`]; }
    if (d !== doc.digest) errs.push("$.digest: does not match the document's content (edited or incomplete)");
  }
  return errs;
}
