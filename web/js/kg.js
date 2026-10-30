// Scientific Knowledge Graph (KG-1): relationships between stored investigations (saved records and research
// sessions), targets, runs and method sets — only those stated by stored data under the documented rules below.
// No physical relationship between astronomical objects is ever inferred.
//   K1 investigates      a record or session names a target
//   K2 identical result  two records have the same content hash
//   K3 uses run          a session's runs include a saved record's content hash
//   K4 method set        records analysed with the same analysis version
//   K5 repeated issue    records whose data-quality outcome is the same non-clean category
// Computed in the browser from the vault and session lists (stored data); presentation only.

import { el } from "./util.js";

export const RULES = { K1: "investigates (record or session names the target)", K2: "identical result (same content hash)", K3: "uses run (session run = record content hash)",
                       K4: "same method set (analysis version)", K5: "repeated data-quality issue (same non-clean category)" };

export function build(records, sessions) {
  const nodes = new Map(), edges = [];
  const node = (id, kind, label) => { if (!nodes.has(id)) nodes.set(id, { id, kind, label }); return id; };
  for (const r of records) {
    const rid = node(`record:${r.record_id}`, "record", r.name);
    if (r.target_id) edges.push({ s: rid, t: node(`target:${r.target_id}`, "target", r.target_id), rule: "K1" });
    if (r.analysis_version) edges.push({ s: rid, t: node(`methods:${r.analysis_version}`, "method set", r.analysis_version), rule: "K4" });
    const dq = (r.outcomes || []).find((o) => o.question === "data_quality");
    if (dq && dq.category !== "usable") edges.push({ s: rid, t: node(`issue:${dq.category}`, "data-quality issue", dq.category.replaceAll("_", " ")), rule: "K5" });
  }
  for (let i = 0; i < records.length; i++)
    for (let j = i + 1; j < records.length; j++)
      if (records[i].content_hash && records[i].content_hash === records[j].content_hash)
        edges.push({ s: `record:${records[i].record_id}`, t: `record:${records[j].record_id}`, rule: "K2" });
  for (const s of sessions) {
    const sid = node(`session:${s.session_id}`, "session", s.name);
    if (s.target_id) edges.push({ s: sid, t: node(`target:${s.target_id}`, "target", s.target_id), rule: "K1" });
    for (const r of records) if ((s.run_hashes || []).includes(r.content_hash)) edges.push({ s: sid, t: `record:${r.record_id}`, rule: "K3" });
  }
  const issues = [...nodes.values()].filter((n) => n.kind === "data-quality issue").map((n) => ({ issue: n.label, n: edges.filter((e) => e.t === n.id).length })).filter((x) => x.n >= 2);
  return { method: "KG-1", nodes: [...nodes.values()], edges, rules: RULES, repeated_issues: issues };
}

export function view(g) {
  if (g.nodes.filter((n) => n.kind === "record" || n.kind === "session").length < 2)
    return el("p", { class: "muted" }, "Fewer than two stored investigations: there is nothing to relate yet. Save investigations or create sessions; relationships appear only where stored data state them (rules K1–K5). Persistence: records in data/records/, sessions in data/sessions/ (server) or this browser (preview).");
  const by = {};
  for (const e of g.edges) (by[e.rule] ||= []).push(e);
  const label = (id) => g.nodes.find((n) => n.id === id)?.label || id;
  return el("div", {}, el("p", { class: "muted" }, `${g.nodes.length} nodes, ${g.edges.length} relationships, each from a stated rule over stored data. No physical relationship between objects is inferred.`),
    ...Object.entries(g.rules).map(([k, v]) => el("details", { open: k !== "K1" || null }, el("summary", {}, `${k} · ${v} (${(by[k] || []).length})`),
      (by[k] || []).length ? el("ul", { class: "limits" }, ...by[k].slice(0, 100).map((e) => el("li", {}, `${label(e.s)} → ${label(e.t)}`))) : el("p", { class: "faint" }, "none"))),
    g.repeated_issues.length ? el("p", {}, "Repeated data-quality issues: " + g.repeated_issues.map((x) => `${x.issue} (${x.n} investigations)`).join("; ")) : null);
}
