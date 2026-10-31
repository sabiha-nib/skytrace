// SESSION-1 in the browser: validation and integrity, identical to src/skytrace/session.py (parity-tested).
// The schema document itself is loaded from the server or the static preview; nothing here redefines it.

import { CanonError, digest, dumps } from "./canon.js";
import { check } from "./schema.js";

export const SCHEMA_ID = "skytrace.research_session/1";
export const MAX_BYTES = 1000000;

export async function bodyHash(s) {
  const b = { ...s };
  delete b.content_hash;
  return digest(b);
}

export const GENESIS = "0".repeat(64);

async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Evidence-vault link (VAULT-1), mirrored from session.chain_hash: SHA-256(previous link + canonical entry). */
export async function chainHash(prev, e) {
  return sha256hex(prev + dumps({ seq: e.seq, at: e.at, kind: e.kind, summary: e.summary, ref: e.ref }));
}

/** Fill missing links in order; existing links are never recomputed, so an edited entry stays detectably broken. */
export async function chainFill(history) {
  const out = [];
  let prev = null;
  for (const e of history || []) {
    const x = "h" in e ? e : { ...e, h: await chainHash(prev === null ? GENESIS : prev, e) };
    out.push(x);
    prev = x.h;
  }
  return out;
}

export async function verifyChain(history) {
  const broken = []; let verified = 0, anchor = null, unchained = 0, prev = null;
  for (let i = 0; i < history.length; i++) {
    const e = history[i];
    if (!("h" in e)) { unchained++; prev = null; continue; }
    if (prev === null) {
      if (i === 0 && e.seq === 1 && (await chainHash(GENESIS, e)) === e.h) verified++;
      else if (i === 0 || !("h" in history[i - 1])) anchor = anchor ?? e.seq;
      else broken.push(e.seq);
    } else if ((await chainHash(prev, e)) === e.h) verified++;
    else broken.push(e.seq);
    prev = e.h;
  }
  return { method: "VAULT-1", links: history.length - unchained, verified, anchor, broken, unchained,
    note: "A hash chain detects an edited or removed entry unless every later link and the session hash are recomputed too; it is not a signature." };
}

export async function finalize(s) {
  const out = { ...s };
  delete out.content_hash;
  out.history = await chainFill(out.history);
  out.content_hash = await bodyHash(out);
  return out;
}

export function validate(schema, s) {
  if (!s || typeof s !== "object" || Array.isArray(s)) return ["$: a session must be an object"];
  if (s.schema !== SCHEMA_ID) return [`$.schema: ${s.schema === undefined ? "None" : `'${s.schema}'`} is not a supported session format (expected ${SCHEMA_ID})`];
  const errs = check(schema, s);
  if (errs.length) return errs;
  let size;
  try { size = new TextEncoder().encode(dumps(s)).length; } catch (e) { if (e instanceof CanonError) return [`$: ${e.message}`]; throw e; }
  if (size > MAX_BYTES) return [`$: session larger than ${MAX_BYTES} bytes`];
  const seqs = s.history.map((h) => h.seq);
  if (seqs.some((x, i) => i && x <= seqs[i - 1])) errs.push("$.history: sequence numbers must increase");
  const hashes = new Set(s.runs.map((r) => r.content_hash));
  if (s.active_hash !== null && !hashes.has(s.active_hash)) errs.push("$.active_hash: not one of the session's runs");
  for (const p of s.plans) {
    const ids = p.steps.map((st) => st.id);
    for (const st of p.steps) {
      const before = ids.slice(0, ids.indexOf(st.id));
      const missing = st.depends.filter((d) => !before.includes(d));
      if (missing.length) errs.push(`$.plans[${p.id}].${st.id}: depends on steps that do not precede it: ${missing.join(", ")}`);
    }
  }
  errs.crossField = true;      // reached the cross-field rules: verify() adds the evidence-vault chain check (async)
  return errs;
}

export async function verify(schema, s) {
  const errors = validate(schema, s);
  if (errors.crossField) {
    const vc = await verifyChain(s.history);
    if (vc.broken.length) errors.push(`$.history: evidence-vault chain broken at entry ${vc.broken[0]} (an entry was edited or removed)`);
  }
  if (errors.length) return { valid: false, errors, hash_ok: null, stated: s?.content_hash ?? null, computed: null };
  const computed = await bodyHash(s);
  const stated = s.content_hash;
  return { valid: true, errors: [], hash_ok: stated ? stated === computed : null, stated: stated ?? null, computed };
}

export function nowIso() { return new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"); }

export function logEvent(s, kind, summary, ref = null) {
  const seq = s.history.length ? s.history[s.history.length - 1].seq + 1 : 1;
  return { ...s, modified_at: nowIso(), history: [...s.history, { seq, at: nowIso(), kind, summary: String(summary).slice(0, 300), ref: ref === null ? null : String(ref).slice(0, 300) }].slice(-2000) };
}

export function rid(n = 6) { return Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, "0")).join(""); }

export async function newSession(name, targetId = null) {
  const t = nowIso();
  return finalize({ schema: SCHEMA_ID, session_id: rid(6), name: (name || "Research session").trim().slice(0, 120) || "Research session",
    created_at: t, modified_at: t, target_id: targetId, question: { id: null, text: "" }, runs: [], active_hash: null, hypotheses: [],
    notebook: [], annotations: [], plans: [], experiments: [], missions: [], workflows: [], examined: [],
    history: [{ seq: 1, at: t, kind: "session.create", summary: `Session created${targetId ? " for " + targetId : ""}`, ref: null }] });
}
