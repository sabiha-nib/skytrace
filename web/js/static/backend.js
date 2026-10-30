// Static preview backend: answers the same API calls as the Python server, from files that the real server
// produced at build time (scripts/build_static.py). Nothing here measures or decides anything new:
//   * targets, images, investigation records, evidence graphs, reports, stability results and copilot answers
//     are the server's own responses, saved verbatim;
//   * pair comparison (JS port of view.pair_comparison, parity-tested) and display registration run in the browser;
//   * anything that needs the server (arbitrary parameters, questions about named observations, replay by
//     re-execution) is refused with an explanation, never imitated.
// Saved investigations live in this browser's storage only, and the interface says so.

import { pairComparison } from "./compare.js";
import { registerPair } from "./register.js";
import { verifyRecordText } from "./hash.js";
import { plan as planLocal } from "../planner.js";
import { validate as validateWorkflowLocal } from "../workflows.js";
import { finalize, logEvent, newSession, nowIso, verify as verifySession, validate as validateSession } from "../sessioncore.js";

const BASE = "data/";
const cache = new Map();
const runsByTarget = new Map();     // tid -> [{iid, label, params, default, content_hash}]
const runTarget = new Map();        // iid -> tid
const records = new Map();          // iid -> parsed record
const imagesByTarget = new Map();   // tid -> promise of {key: image payload}
const STORE_KEY = "skytrace.preview.records.v1";
const SESSION_KEY = "skytrace.preview.sessions.v1";
let memorySessions = null;
let memoryStore = null;             // used when browser storage is unavailable

export class PreviewLimit extends Error {}

async function getText(path) {
  if (cache.has(path)) return cache.get(path);
  const p = fetch(BASE + path).then(async (r) => {
    if (!r.ok) throw new Error(r.status === 404 ? "not included in this preview" : `${r.status} ${r.statusText}`);
    return r.text();
  });
  cache.set(path, p);
  try { return await p; } catch (e) { cache.delete(path); throw e; }
}
const getJSON = async (path) => JSON.parse(await getText(path));

async function runs(tid) {
  if (!runsByTarget.has(tid)) {
    const r = await getJSON(`t/${tid}/runs.json`);
    r.forEach((x) => runTarget.set(x.iid, tid));
    runsByTarget.set(tid, r);
  }
  return runsByTarget.get(tid);
}

async function record(iid) {
  if (!records.has(iid)) {
    const tid = runTarget.get(iid);
    if (!tid) throw new Error("unknown investigation in this preview");
    records.set(iid, await getJSON(`t/${tid}/run/${iid}/record.json`));
  }
  return records.get(iid);
}

async function summary(iid) {
  const tid = runTarget.get(iid);
  const meta = await getJSON(`t/${tid}/run/${iid}/meta.json`);
  return { ...meta, record: await record(iid) };
}

const near = (a, b) => (typeof a === "number" && typeof b === "number" ? Math.abs(a - b) < 1e-9 : JSON.stringify(a) === JSON.stringify(b));

function matchRun(list, params) {
  const keys = Object.keys(params || {});
  if (!keys.length) return list.find((r) => r.default);
  return list.find((r) => keys.every((k) => near(params[k], r.params[k] ?? r.defaults?.[k])));
}

function measurementsOf(rec) {
  const m = {};
  for (const e of rec.events) if (e.step === "measure" && e.data && "key" in e.data) m[e.data.key] = e.data;
  return m;
}

// Scenario keys for the recorded Phase 7 results (the same canonical text build_static.py uses).
export function cfKey(sc) { return canonKey({ kind: sc.kind, change: sc.change }); }
export function synKey(sc) { return canonKey({ seed: sc.seed, pm_mas_yr: sc.pm_mas_yr, passes: sc.passes, target_flux_scale: sc.target_flux_scale ?? null }); }
function canonKey(o) {
  const enc = (v) => Array.isArray(v) ? "[" + v.map(enc).join(",") + "]" : v && typeof v === "object"
    ? "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + enc(v[k])).join(",") + "}" : JSON.stringify(v);
  return enc(o);
}

// ------------------------------------------------------------------ copilot (precomputed local-assistant answers)
// Same routing as src/skytrace/ai/local.py::_intent; the local assistant's answer depends only on the intent and on
// observation keys named in the question, so keyless questions get exactly the server's answer. The exception is the
// "plan" intent, whose plan depends on the question's wording: the copilot shows which question was recorded and
// offers to plan the exact question in the Planner (PLAN-1 runs in the browser).
const INTENTS = [["capabilities", /what can you|capabilit|which tools|what questions can|able to do|what can skytrace/],
  ["draft", /\bdraft\b|notebook|write (?:a|up|me) (?:a )?(?:note|summary|paragraph)/],
  ["plan", /\bplan\b|how (?:would|should|could|do) i (?:test|check|find out|establish)|what steps|step[- ]by[- ]step/],
  ["quality", /data quality|quality check|integrity|corrupt|data problem/],
  ["missing", /missing|what evidence|evidence gap|contradict|incomplete|ledger/],
  ["hypotheses", /hypothes|explanation|viable|alternative/], ["alignment", /align|registr|plate|astrometric frame/], ["compat", /compatib|wavelength|match/],
  ["excluded", /exclud|reject|why was|flag/], ["gaia", /gaia|catalog|proper motion|motion/],
  ["uncertainty", /uncertain|error bar|limitation|largest/], ["next", /next|should i|investigate|follow/],
  ["support", /support|which observations|evidence for/], ["changed", /chang|vary|variab|differ|bright|dim/]];
export function intentOf(q) {
  const ql = q.toLowerCase();
  for (const [name, re] of INTENTS) if (re.test(ql)) return name;
  return "summary";
}
const KEY_RE = /\b(?:QR\d|SYNTHETIC):[A-Za-z0-9_]+:D[1-6]\b/;

// ------------------------------------------------------------------ records in browser storage
function load() {
  if (memoryStore) return memoryStore;
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); } catch { memoryStore = []; return memoryStore; }
}
function store(list) {
  if (memoryStore) { memoryStore = list; return "memory"; }
  try { localStorage.setItem(STORE_KEY, JSON.stringify(list)); return "browser"; } catch { memoryStore = list; return "memory"; }
}
export function recordStorageKind() {
  if (memoryStore) return "memory";
  try { localStorage.setItem(STORE_KEY + ".probe", "1"); localStorage.removeItem(STORE_KEY + ".probe"); return "browser"; } catch { return "memory"; }
}
const rid = () => Array.from(crypto.getRandomValues(new Uint8Array(6)), (b) => b.toString(16).padStart(2, "0")).join("");

function cleanTags(tags) {
  return Array.isArray(tags) ? [...new Set(tags.filter((t) => typeof t === "string").map((t) => t.trim().slice(0, 40)).filter(Boolean))].sort().slice(0, 20) : [];
}
function cleanContext(ctx) {
  if (!ctx || typeof ctx !== "object") return {};
  const text = JSON.stringify(ctx);
  if (text.length > 50000) throw new Error("investigation context is larger than 50 kB");
  return JSON.parse(text);
}

async function saveFor(iid, name, notes, transcript, imported = false, extra = {}) {
  const rec = await record(iid);
  const list = load();
  const entry = { record_id: rid(), name: (name || "").trim().slice(0, 120) || `${rec.target} investigation`, notes: (notes || "").slice(0, 2000),
                  target_id: runTarget.get(iid), saved_at: new Date().toISOString(), content_hash: rec.content_hash,
                  bundle_kind: rec.parameters.bundle_kind, investigation_id: iid, parameters: rec.parameters, analysis_version: rec.parameters.analysis_version,
                  copilot_transcript: transcript || [], imported, last_replay: null,
                  tags: cleanTags(extra.tags), context: cleanContext(extra.context),
                  outcomes: (rec.events.find((e) => e.step === "assess")?.data?.outcomes || []).map((o) => ({ question: o.question, category: o.category })) };
  list.unshift(entry);
  const where = store(list);
  return { record_id: entry.record_id, name: entry.name, saved_at: entry.saved_at, stored_in: where };
}

// ------------------------------------------------------------------ research sessions in browser storage
function loadSessions() {
  if (memorySessions) return memorySessions;
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "[]"); } catch { memorySessions = []; return memorySessions; }
}
function storeSessions(list) {
  if (memorySessions) { memorySessions = list; return "memory"; }
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(list)); return "browser"; } catch { memorySessions = list; return "memory"; }
}
async function putSession(s) {
  const spec = await getJSON("specs.json");
  const errs = validateSession(spec.session_schema, s);
  if (errs.length) throw new Error("invalid session: " + errs.slice(0, 5).join("; "));
  const f = await finalize(s);
  const list = loadSessions().filter((x) => x.session_id !== f.session_id);
  list.unshift(f);
  storeSessions(list);
  return f;
}
const sessionSummary = (s) => ({ session_id: s.session_id, name: s.name, target_id: s.target_id, modified_at: s.modified_at, created_at: s.created_at,
  question: s.question.text, n_runs: s.runs.length, n_notes: s.notebook.length, n_hypotheses: s.hypotheses.length, content_hash: s.content_hash,
  run_hashes: s.runs.map((r) => r.content_hash), methods: [...new Set(s.history.map((h) => h.kind.split(".")[0]))].sort() });

export const staticApi = {
  isStatic: true,
  status: () => getJSON("status.json"),
  targets: () => getJSON("targets.json"),
  target: (tid) => getJSON(`t/${tid}/target.json`),
  async image(tid, key) {
    if (!imagesByTarget.has(tid)) imagesByTarget.set(tid, getJSON(`t/${tid}/images.json`));
    const all = await imagesByTarget.get(tid);
    if (!all[key]) throw new Error(`${key} has no stored image in this preview`);
    return all[key];
  },
  async pair(tid, a, b, iid) {
    const [pa, pb] = await Promise.all([staticApi.image(tid, a), staticApi.image(tid, b)]);
    let ma = null, mb = null, comparison = null;
    if (iid && runTarget.has(iid)) {
      const rec = await record(iid);
      const meas = measurementsOf(rec);
      ma = meas[a]; mb = meas[b];
      const vp = rec.events.find((e) => e.step === "variability");
      comparison = pairComparison(meas, rec.parameters, vp?.data?.pairs || [], a, b);
    }
    return registerPair(pa, pb, ma, mb, comparison);
  },
  async analyze(tid, params = {}) {
    const list = await runs(tid);
    const r = matchRun(list, params);
    if (!r) throw new PreviewLimit("This preview contains precomputed runs only (the default parameters and the five stability perturbations). Other parameters need the local server: python run.py");
    return summary(r.iid);
  },
  presetRuns: (tid) => runs(tid),
  async stability(tid, params = {}) {
    const list = await runs(tid);
    const r = matchRun(list, params);
    if (!r?.default) throw new PreviewLimit("The stability check is precomputed for the default parameters only in this preview.");
    return getJSON(`t/${tid}/stability.json`);
  },
  investigation: (iid) => summary(iid),
  graph: (iid) => getJSON(`t/${runTarget.get(iid)}/run/${iid}/graph.json`),
  report: (iid) => getText(`t/${runTarget.get(iid)}/run/${iid}/report.md`),
  discovery: (iid) => getJSON(`t/${runTarget.get(iid)}/run/${iid}/discovery.json`),
  capabilities: () => getJSON("capabilities.json"),
  // The package zip built by the server at build time, carried as base64 (static hosts may not serve .zip files);
  // its SHA-256 is checked before it is offered, so the bytes are exactly the server's.
  packageBytes: async (iid) => {
    const p = await getJSON(`t/${runTarget.get(iid)}/run/${iid}/package.json`);
    const bin = Uint8Array.from(atob(p.base64), (c) => c.charCodeAt(0));
    const hex = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bin)), (b) => b.toString(16).padStart(2, "0")).join("");
    if (bin.length !== p.bytes || hex !== p.sha256) throw new Error("the stored package does not match its checksum");
    return bin.buffer;
  },
  async updateRecord(id, body) {
    const list = load(), d = list.find((r) => r.record_id === id);
    if (!d) throw new Error("unknown record");
    if ("name" in body) { const n = String(body.name || "").trim().slice(0, 120); if (!n) throw new Error("name must not be empty"); d.name = n; }
    if ("notes" in body) d.notes = String(body.notes || "").slice(0, 2000);
    if ("tags" in body) d.tags = cleanTags(body.tags);
    if ("context" in body) d.context = cleanContext(body.context);
    d.modified_at = new Date().toISOString();
    store(list);
    return { record_id: id, name: d.name, notes: d.notes, tags: d.tags, modified_at: d.modified_at };
  },
  async cloneRecord(id) {
    const d = load().find((r) => r.record_id === id);
    if (!d) throw new Error("unknown record");
    const out = await saveFor(d.investigation_id, `Copy of ${d.name}`.slice(0, 120), d.notes, d.copilot_transcript, false,
                              { tags: d.tags, context: d.context });
    return { ...out, cloned_from: id };
  },
  recordExportUrl: (iid) => BASE + `t/${runTarget.get(iid)}/run/${iid}/record.json`,
  recordText: (iid) => getText(`t/${runTarget.get(iid)}/run/${iid}/record.json`),
  async ask(iid, question) {
    if (KEY_RE.test(question))
      throw new PreviewLimit("questions that name specific observations are answered by the local server's assistant; in this preview, use the Time Machine's comparison panel for a pair, or ask a general question.");
    return (await getJSON(`t/${runTarget.get(iid)}/run/${iid}/ask.json`))[intentOf(question)];
  },
  async records() { return { records: load(), storage: recordStorageKind() }; },
  async saveRecord(body) { return saveFor(body.investigation_id, body.name, body.notes, body.transcript, false, body); },
  async record(id) {
    const d = load().find((r) => r.record_id === id);
    if (!d) throw new Error("unknown record");
    return { ...d, bundle_available: runTarget.has(d.investigation_id) || !!(await runs(d.target_id)).find((r) => r.iid === d.investigation_id) };
  },
  async replay(id) {
    const list = load(), d = list.find((r) => r.record_id === id);
    if (!d) throw new Error("unknown record");
    const r = (await runs(d.target_id)).find((x) => x.content_hash === d.content_hash);
    const res = { reproduced: !!r, saved_content_hash: d.content_hash, replay_content_hash: r?.content_hash || null,
                  replayed_at: new Date().toISOString(), executed: false,
                  explanation: r ? "identical to the result the Python pipeline produced for this preview (compared, not re-executed in the browser)"
                                 : "no precomputed run in this preview has this content hash" };
    d.last_replay = res; store(list);
    return res;
  },
  async deleteRecord(id) { store(load().filter((r) => r.record_id !== id)); return { deleted: id }; },
  // ---- Phase 6 (precomputed by the server at build time, or computed by parity-tested browser ports)
  specs: () => getJSON("specs.json"),
  research: (iid) => getJSON(`t/${runTarget.get(iid)}/run/${iid}/research.json`),
  async plan(question, facts) {
    const spec = await getJSON("specs.json");
    return planLocal(spec.planner, question, { ...facts, server: false, static: true, network: false });
  },
  async experiment(tid, cfg) {
    if (cfg.configs) throw new PreviewLimit("custom parameter sets need the local server (python run.py); this preview has the standard experiments precomputed.");
    const all = await getJSON(`t/${tid}/experiments.json`);
    const key = cfg.template + (cfg.question ? `:${cfg.question}` : "");
    if (!all[key]) throw new PreviewLimit(`the ${cfg.template} experiment is not precomputed in this preview`);
    return { ...all[key], recorded_at_build: true };
  },
  // Phase 7: recorded by the server at build time
  frontier: (iid) => getJSON(`t/${runTarget.get(iid)}/run/${iid}/frontier.json`),
  async reproduce(iid) {
    const r = await getJSON(`t/${runTarget.get(iid)}/run/${iid}/reproduce.json`).catch(() => null);
    if (!r) throw new PreviewLimit("the re-execution audit is recorded for the default run only in this preview; run python run.py for others.");
    return { ...r, recorded_at_build: true };
  },
  async counterfactual(tid, iid, scenario) {
    const runsList = await runs(tid);
    if (!runsList.find((x) => x.iid === iid)?.default) throw new PreviewLimit("counterfactuals are precomputed against the default run only in this preview.");
    const all = await getJSON(`t/${tid}/counterfactuals.json`);
    const hit = all.find((x) => x.key === cfKey(scenario));
    if (!hit) throw new PreviewLimit("this scenario is not precomputed in the preview; choose one of the listed scenarios or run python run.py.");
    return { ...hit.result, recorded_at_build: true };
  },
  async synthetic(scenario) {
    const all = await getJSON("synthetic.json");
    const hit = all.find((x) => x.key === synKey(scenario));
    if (!hit) throw new PreviewLimit("only the template scenarios are precomputed in the preview; custom scenarios generate files and need python run.py.");
    return { ...hit.result, recorded_at_build: true };
  },
  async design() {
    const d = await getJSON("design.json");
    return { ...d, recorded_at_build: true };
  },
  async provenance() { throw new PreviewLimit("provenance verification re-reads the stored files and re-runs the analysis: it needs the local server (python run.py)."); },
  connectors: () => getJSON("connectors.json"),
  async connectorPreview() { throw new PreviewLimit("request previews are built by the server's acquisition code; run python run.py to preview a query."); },
  async validateWorkflow(workflow) {
    const spec = await getJSON("specs.json");
    const errors = validateWorkflowLocal(spec, workflow);
    return { valid: !errors.length, errors };
  },
  async sessions() {
    const spec = await getJSON("specs.json");
    const out = [];
    for (const s of loadSessions()) {
      const v = await verifySession(spec.session_schema, s);
      out.push({ ...sessionSummary(s), integrity: v.hash_ok ? "ok" : !v.valid ? "invalid" : "hash mismatch" });
    }
    return { sessions: out, unreadable: [], storage: memorySessions ? "memory" : "browser" };
  },
  async createSession(name, tid) { return putSession(await newSession(name, tid ?? null)); },
  async session(sid) {
    const s = loadSessions().find((x) => x.session_id === sid);
    if (!s) throw new Error("unknown session");
    const spec = await getJSON("specs.json");
    return { ...s, _verification: await verifySession(spec.session_schema, s) };
  },
  async saveSession(s) {
    const { _verification, ...rest } = s;
    return putSession(rest);
  },
  async deleteSession(sid) { storeSessions(loadSessions().filter((x) => x.session_id !== sid)); return { deleted: sid }; },
  async importSession(s) {
    const spec = await getJSON("specs.json");
    const v = await verifySession(spec.session_schema, s);
    if (!v.valid) throw new Error("not a valid research session: " + v.errors.slice(0, 5).join("; "));
    if (v.hash_ok === false) throw new Error("the session's content hash does not match: it was modified or is incomplete");
    let x = { ...s };
    if (loadSessions().some((y) => y.session_id === x.session_id)) x.session_id = (await newSession("x")).session_id;
    x = logEvent(x, "session.import", v.hash_ok ? "Imported (content hash verified)" : "Imported (no hash was stated)");
    return { ...(await putSession(x)), hash_verified: !!v.hash_ok };
  },
  async sessionFromRecord(rid) {
    const d = load().find((r) => r.record_id === rid);
    if (!d) throw new Error("unknown record");
    const t = nowIso();
    let s = await newSession(d.name || "Imported investigation", d.target_id);
    s.runs = [{ investigation_id: d.investigation_id, content_hash: d.content_hash, label: "saved investigation", attached_at: t,
                params: Object.fromEntries(Object.entries(d.parameters || {}).filter(([k, v]) => ["number", "boolean"].includes(typeof v) && /^[a-z_]{1,40}$/.test(k))) }];
    s.active_hash = d.content_hash;
    const c = d.context || {};
    if (typeof c.question === "string") s.question = { id: c.question, text: String(c.question_text || "").slice(0, 500) };
    s.hypotheses = (c.hypotheses || []).filter((h) => h && typeof h.statement === "string" && h.statement.trim()).slice(0, 50)
      .map((h, i) => ({ id: String(h.id || `U${i}`).slice(0, 40), statement: h.statement.slice(0, 1000), tests: (h.tests || []).filter((x) => typeof x === "string").slice(0, 30), kind: "interpretation", created_at: String(h.created_at || t).slice(0, 40) }));
    s = logEvent(s, "session.migrate", `Converted from saved investigation “${d.name || ""}” (v0.5 record)`, rid);
    return putSession(s);
  },
  async importRecord(text, name) {
    let rec;
    try { rec = JSON.parse(text); } catch { throw new Error("the file is not JSON"); }
    if (!rec || typeof rec !== "object" || !rec.content_hash || !rec.parameters || !Array.isArray(rec.events))
      throw new Error("not a Skytrace investigation record");
    const v = await verifyRecordText(text);      // recomputed in the browser exactly as Python's stable_hash
    if (!v.ok) throw new Error("the content hash does not match the record: it was modified or is incomplete");
    const tid = rec.parameters.bundle;
    const list = tid ? await runs(tid).catch(() => []) : [];
    const r = list.find((x) => x.content_hash === rec.content_hash);
    if (!r) throw new PreviewLimit("the record is intact, but it is not one of this preview's precomputed runs; open it with the full application (python run.py), which can also replay it.");
    return { ...(await saveFor(r.iid, name || `Imported ${rec.target}`, "", [], true)), content_hash_verified: true, matched_preview_run: r.label };
  },
};
