// Thin client for the SKYTRACE API. Every error surfaces the server's message.
// When the page is the static preview build (<meta name="skytrace-mode" content="static">), the same calls are
// answered from files the server produced at build time (see static/backend.js).

export const STATIC = document.querySelector('meta[name="skytrace-mode"]')?.content === "static";

async function req(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const type = r.headers.get("content-type") || "";
  const body = type.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error((body && body.error) || `${r.status} ${r.statusText}`);
  return body;
}

const serverApi = {
  isStatic: false,
  status: () => req("/api/status"),
  targets: () => req("/api/targets"),
  target: (tid) => req(`/api/targets/${encodeURIComponent(tid)}`),
  image: (tid, key) => req(`/api/targets/${encodeURIComponent(tid)}/observations/${encodeURIComponent(key)}/image`),
  pair: (tid, a, b, inv) => req(`/api/targets/${encodeURIComponent(tid)}/pair-image?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&inv=${encodeURIComponent(inv || "")}`),
  analyze: (tid, params = {}) => req(`/api/targets/${encodeURIComponent(tid)}/analyze`, { method: "POST", body: JSON.stringify({ params }) }),
  presetRuns: async () => null,
  stability: (tid, params = {}) => req(`/api/targets/${encodeURIComponent(tid)}/stability`, { method: "POST", body: JSON.stringify({ params }) }),
  investigation: (iid) => req(`/api/investigations/${iid}`),
  graph: (iid) => req(`/api/investigations/${iid}/graph`),
  report: (iid) => req(`/api/investigations/${iid}/report.md`),
  recordExportUrl: (iid) => `/api/investigations/${iid}/record.json`,
  recordText: async (iid) => {   // raw text, so numbers keep the exact form the content hash was computed on
    const r = await fetch(`/api/investigations/${iid}/record.json`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.text();
  },
  discovery: (iid) => req(`/api/investigations/${iid}/discovery`),
  capabilities: () => req("/api/capabilities"),
  packageBytes: async (iid) => {
    const r = await fetch(`/api/investigations/${iid}/package.zip`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.arrayBuffer();
  },
  updateRecord: (rid, body) => req(`/api/records/${rid}`, { method: "PATCH", body: JSON.stringify(body) }),
  cloneRecord: (rid) => req(`/api/records/${rid}/clone`, { method: "POST", body: "{}" }),
  ask: (iid, question, history) => req(`/api/investigations/${iid}/ask`, { method: "POST", body: JSON.stringify({ question, history }) }),
  records: () => req("/api/records"),
  saveRecord: (body) => req("/api/records", { method: "POST", body: JSON.stringify(body) }),
  record: (rid) => req(`/api/records/${rid}`),
  replay: (rid) => req(`/api/records/${rid}/replay`, { method: "POST", body: "{}" }),
  deleteRecord: (rid) => req(`/api/records/${rid}`, { method: "DELETE" }),
  // The record text is passed through unparsed so its numbers keep the exact form the content hash was computed on.
  importRecord: (text, name) => req("/api/records/import", { method: "POST", body: `{"name": ${JSON.stringify(name || "")}, "record": ${text}}` }),
  // ---- Phase 6
  specs: () => req("/api/specs"),
  research: (iid) => req(`/api/investigations/${iid}/research`),
  plan: (question, facts) => req("/api/plan", { method: "POST", body: JSON.stringify({ question, facts }) }),
  experiment: (tid, cfg) => req("/api/experiments", { method: "POST", body: JSON.stringify({ target_id: tid, ...cfg }) }),
  provenance: (iid, rerun = true) => req(`/api/investigations/${iid}/provenance`, { method: "POST", body: JSON.stringify({ rerun }) }),
  connectors: () => req("/api/connectors"),
  connectorPreview: (cid, params) => req(`/api/connectors/${cid}/preview`, { method: "POST", body: JSON.stringify({ params }) }),
  validateWorkflow: (workflow) => req("/api/workflows/validate", { method: "POST", body: JSON.stringify({ workflow }) }),
  sessions: () => req("/api/sessions"),
  createSession: (name, target_id) => req("/api/sessions", { method: "POST", body: JSON.stringify({ name, target_id }) }),
  session: (sid) => req(`/api/sessions/${sid}`),
  saveSession: (s) => req(`/api/sessions/${s.session_id}`, { method: "PUT", body: JSON.stringify({ session: s }) }),
  deleteSession: (sid) => req(`/api/sessions/${sid}`, { method: "DELETE" }),
  importSession: (s) => req("/api/sessions/import", { method: "POST", body: JSON.stringify({ session: s }) }),
  sessionFromRecord: (rid) => req(`/api/sessions/from-record/${rid}`, { method: "POST", body: "{}" }),
  // Phase 7
  frontier: (iid, stability) => req(`/api/investigations/${iid}/frontier`, { method: "POST", body: JSON.stringify(stability ? { stability } : {}) }),
  reproduce: (iid) => req(`/api/investigations/${iid}/reproduce`, { method: "POST", body: "{}" }),
  counterfactual: (tid, iid, scenario) => req("/api/counterfactuals", { method: "POST", body: JSON.stringify({ target_id: tid, baseline_investigation_id: iid, scenario }) }),
  synthetic: (scenario) => req("/api/synthetic", { method: "POST", body: JSON.stringify({ scenario }) }),
  design: (truth, schedules) => req("/api/observation-design", { method: "POST", body: JSON.stringify({ truth, schedules }) }),
  // Phase 8
  epistemic: (iid) => req(`/api/investigations/${iid}/epistemic`),
  reproduceX: (iid) => req(`/api/investigations/${iid}/reproduce-x`, { method: "POST", body: "{}" }),
  lineage: (iid, rid) => req(`/api/investigations/${iid}/lineage?result=${encodeURIComponent(rid)}`),
  simAudit: (scenario, seeds) => req("/api/simulation-audit", { method: "POST", body: JSON.stringify(seeds ? { scenario, seeds } : { scenario }) }),
};

export const api = STATIC ? (await import("./static/backend.js")).staticApi : serverApi;
