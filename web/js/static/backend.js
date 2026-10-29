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

const BASE = "data/";
const cache = new Map();
const runsByTarget = new Map();     // tid -> [{iid, label, params, default, content_hash}]
const runTarget = new Map();        // iid -> tid
const records = new Map();          // iid -> parsed record
const imagesByTarget = new Map();   // tid -> promise of {key: image payload}
const STORE_KEY = "skytrace.preview.records.v1";
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

// ------------------------------------------------------------------ copilot (precomputed local-assistant answers)
// Same routing as src/skytrace/ai/local.py::_intent; the local assistant's answer depends only on the intent and on
// observation keys named in the question, so keyless questions get exactly the server's answer.
const INTENTS = [["alignment", /align|registr|plate|astrometric frame/], ["compat", /compatib|wavelength|match/],
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

async function saveFor(iid, name, notes, transcript, imported = false) {
  const rec = await record(iid);
  const list = load();
  const entry = { record_id: rid(), name: (name || "").trim().slice(0, 120) || `${rec.target} investigation`, notes: (notes || "").slice(0, 2000),
                  target_id: runTarget.get(iid), saved_at: new Date().toISOString(), content_hash: rec.content_hash,
                  bundle_kind: rec.parameters.bundle_kind, investigation_id: iid, analysis_version: rec.parameters.analysis_version,
                  copilot_transcript: transcript || [], imported, last_replay: null };
  list.unshift(entry);
  const where = store(list);
  return { record_id: entry.record_id, name: entry.name, saved_at: entry.saved_at, stored_in: where };
}

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
  recordExportUrl: (iid) => BASE + `t/${runTarget.get(iid)}/run/${iid}/record.json`,
  recordText: (iid) => getText(`t/${runTarget.get(iid)}/run/${iid}/record.json`),
  async ask(iid, question) {
    if (KEY_RE.test(question))
      throw new PreviewLimit("questions that name specific observations are answered by the local server's assistant; in this preview, use the Time Machine's comparison panel for a pair, or ask a general question.");
    return (await getJSON(`t/${runTarget.get(iid)}/run/${iid}/ask.json`))[intentOf(question)];
  },
  async records() { return { records: load(), storage: recordStorageKind() }; },
  async saveRecord(body) { return saveFor(body.investigation_id, body.name, body.notes, body.transcript); },
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
