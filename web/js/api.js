// Thin client for the SKYTRACE API. Every error surfaces the server's message.

async function req(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const type = r.headers.get("content-type") || "";
  const body = type.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error((body && body.error) || `${r.status} ${r.statusText}`);
  return body;
}

export const api = {
  status: () => req("/api/status"),
  targets: () => req("/api/targets"),
  target: (tid) => req(`/api/targets/${encodeURIComponent(tid)}`),
  image: (tid, key) => req(`/api/targets/${encodeURIComponent(tid)}/observations/${encodeURIComponent(key)}/image`),
  pair: (tid, a, b, inv) => req(`/api/targets/${encodeURIComponent(tid)}/pair-image?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&inv=${encodeURIComponent(inv || "")}`),
  analyze: (tid, params = {}) => req(`/api/targets/${encodeURIComponent(tid)}/analyze`, { method: "POST", body: JSON.stringify({ params }) }),
  stability: (tid, params = {}) => req(`/api/targets/${encodeURIComponent(tid)}/stability`, { method: "POST", body: JSON.stringify({ params }) }),
  investigation: (iid) => req(`/api/investigations/${iid}`),
  graph: (iid) => req(`/api/investigations/${iid}/graph`),
  report: (iid) => req(`/api/investigations/${iid}/report.md`),
  ask: (iid, question, history) => req(`/api/investigations/${iid}/ask`, { method: "POST", body: JSON.stringify({ question, history }) }),
  records: () => req("/api/records"),
  saveRecord: (body) => req("/api/records", { method: "POST", body: JSON.stringify(body) }),
  record: (rid) => req(`/api/records/${rid}`),
  replay: (rid) => req(`/api/records/${rid}/replay`, { method: "POST", body: "{}" }),
  deleteRecord: (rid) => req(`/api/records/${rid}`, { method: "DELETE" }),
};
