// Investigation Vault and Report Studio.
// Vault: save (with tags, the research question and user hypotheses), search, filter by tag, rename, clone, compare
// two saved investigations, reopen, replay (reproducibility check), export, import (with a preview of what the file
// contains before anything is stored) and delete (two-step confirmation).
// With the server, records are JSON files in data/records/ and replay re-executes the analysis. In the static
// preview, records live in this browser's storage only, and "replay" compares the saved content hash with the result
// the Python pipeline produced for the preview (it cannot re-execute in the browser). Both say so.
// Report Studio: every export of the current investigation in one place; each file is produced by the pipeline
// (report, record, evidence graph, discovery report, reproducibility package), never assembled from screen text.

import { api } from "./api.js";
import { emit, sanitizeContext, state } from "./state.js";
import { verifyRecordText } from "./static/hash.js";
import { $, categoryLabel, clear, download, el, fmtDate, questionLabel, toast } from "./util.js";

let query = "", tagFilter = null, selected = new Set(), pendingImport = null, renaming = null;

function storageNote(kind) {
  if (!api.isStatic) return el("p", { class: "muted" }, "Records are saved on the Skytrace server (data/records/) and survive restarts.");
  return kind === "browser"
    ? el("p", { class: "muted", id: "storage-note" }, "Static preview: records are saved in this browser only (local storage). They are not shared and are lost if browser data is cleared. Export a record to keep it.")
    : el("p", { class: "muted", id: "storage-note" }, "Static preview: this browser does not allow storage here, so records last only until the page is closed. Export a record to keep it.");
}

const parseTags = (s) => [...new Set(String(s || "").split(",").map((t) => t.trim()).filter(Boolean))].slice(0, 20);

export async function renderRecords() {
  const body = $("#records-body");
  clear(body);
  body.append(saveCard(), studioCard(), importCard());
  const list = el("div", { class: "card", id: "vault" }, el("h3", {}, "Saved investigations"), el("p", { class: "busy" }, el("span", { class: "spinner" }), "Loading…"));
  body.append(list);
  let recs, storage;
  try { ({ records: recs, storage } = await api.records()); } catch (e) { list.replaceChildren(el("p", {}, e.message)); return; }
  renderVault(list, recs, storage);
}

// ------------------------------------------------------------------ save
function saveCard() {
  const name = el("input", { type: "text", id: "save-name", placeholder: "Name this investigation", "aria-label": "Investigation name", value: state.inv ? `${state.inv.record.target} — ${new Date().toISOString().slice(0, 10)}` : "" });
  const notes = el("textarea", { placeholder: "Notes (optional)", "aria-label": "Notes", rows: "2" });
  const tags = el("input", { type: "text", id: "save-tags", placeholder: "e.g. variability, follow-up", "aria-label": "Tags, separated by commas" });
  const save = el("button", { class: "btn primary", id: "save-record", disabled: !state.inv }, "Save investigation");
  save.addEventListener("click", async () => {
    try {
      const r = await api.saveRecord({ investigation_id: state.inv.investigation_id, name: name.value, notes: notes.value, transcript: state.transcript,
                                       tags: parseTags(tags.value), context: state.context });
      toast(`Saved “${r.name}”`); renderRecords();
    } catch (e) { toast(e.message); }
  });
  const ctx = state.context;
  return el("div", { class: "card" }, el("h3", {}, "Save the current investigation"),
    state.inv ? el("p", { class: "muted" }, `Saves the parameters, the data bundle checksum, every logged step and result (content hash ${state.inv.record.content_hash.slice(0, 12)}…), the copilot conversation (${state.transcript.length} messages), `
      + (ctx.question_text ? `your research question (“${ctx.question_text}”)` : "no research question") + ` and ${ctx.hypotheses.length} hypothesis(es) of your own.`)
              : el("p", { class: "muted" }, "Run an analysis first."),
    el("div", { class: "params" }, el("label", {}, "Name", name), el("label", {}, "Tags (comma-separated)", tags), el("label", { class: "wide" }, "Notes", notes)),
    el("div", { class: "controls" }, save));
}

// ------------------------------------------------------------------ report studio
function studioCard() {
  const inv = state.inv;
  const iid = inv?.investigation_id;
  const tid = state.targetId;
  const base = `skytrace-${tid}-${inv?.record.content_hash.slice(0, 12)}`;
  const item = (id, label, what, fn) => {
    const b = el("button", { class: "btn", type: "button", id, disabled: !inv }, label);
    b.addEventListener("click", async () => {
      b.disabled = true;
      try { if (await fn()) toast(`${label} saved`); } catch (e) { toast(`${label}: ${e.message}`, 6000); }
      b.disabled = false;
    });
    return el("li", {}, b, el("span", { class: "muted" }, what));
  };
  return el("section", { class: "card", id: "studio", "aria-labelledby": "studio-title" },
    el("h3", { id: "studio-title" }, "Report Studio"),
    inv ? el("p", { class: "muted" }, `Exports of investigation ${inv.record.content_hash.slice(0, 16)}… (${inv.record.target}${state.model?.synthetic ? ", synthetic test data" : ""}). Every file is written by the pipeline; the report carries its limitations and the synthetic label where it applies.`)
        : el("p", { class: "muted" }, "Run an analysis first."),
    el("ul", { class: "studio" },
      item("dl-report", "Report (Markdown)", "Findings, method versions, limitations, provenance.", async () => download(`${base}-report.md`, await api.report(iid), "text/markdown")),
      item("export-record", "Record (JSON)", "The investigation record exactly as written; its content hash can be re-verified.", async () => download(`${base}.json`, await api.recordText(iid), "application/json")),
      item("dl-graph", "Evidence graph (JSON)", "Every claim linked to its measurements, methods and files.", async () => download(`${base}-evidence-graph.json`, JSON.stringify(await api.graph(iid), null, 1), "application/json")),
      item("dl-discovery", "Discovery report (JSON)", "Inventory, questions, hypothesis tests, uncertainty components, next steps.", async () => download(`${base}-discovery.json`, JSON.stringify(await api.discovery(iid), null, 1), "application/json")),
      item("dl-package", "Reproducibility package (ZIP)", "All of the above with the capability registry, bundle manifest and SHA256SUMS.", async () => download(`${base}-package.zip`, await api.packageBytes(iid), "application/zip"))),
    el("p", { class: "faint" }, "Charts: use “Export figure (SVG)” under any chart in the Discovery Lab; each figure carries its target, investigation hash and method versions."));
}

// ------------------------------------------------------------------ import (preview, then confirm)
function importCard() {
  const file = el("input", { type: "file", accept: "application/json,.json", id: "import-file", class: "sr-only" });
  const pick = el("label", { class: "btn", for: "import-file" }, "Choose a record (JSON)…");
  const preview = el("div", { id: "import-preview", "aria-live": "polite" });
  file.addEventListener("change", async () => {
    const f = file.files[0];
    file.value = "";
    if (!f) return;
    if (f.size > 2_000_000) { toast("Import refused: the file is larger than 2 MB", 6000); return; }
    const text = await f.text();
    pendingImport = { text, name: f.name.replace(/\.json$/i, "") };
    showImportPreview(preview);
  });
  if (pendingImport) showImportPreview(preview);
  return el("div", { class: "card" }, el("h3", {}, "Import"),
    el("p", { class: "muted" }, api.isStatic
      ? "Reopen a record exported from this preview. Records from other runs need the full application, which verifies the content hash and can replay them."
      : "Import an exported record. Its content hash must recompute and its data bundle must be present on this machine; replay then re-executes it."),
    el("p", { class: "muted" }, "The file is read and checked first; nothing is stored until you confirm. Its contents are treated as untrusted."),
    el("div", { class: "controls" }, file, pick), preview);
}

async function showImportPreview(box) {
  const { text, name } = pendingImport;
  let rec = null, problem = null, hash = null;
  try { rec = JSON.parse(text); } catch { problem = "the file is not JSON"; }
  if (rec && (typeof rec !== "object" || !rec.content_hash || !rec.parameters || !Array.isArray(rec.events))) problem = "not a Skytrace investigation record";
  if (!problem) { try { hash = await verifyRecordText(text); } catch (e) { problem = e.message; } }
  const cancel = el("button", { class: "btn small ghost", type: "button", id: "import-cancel" }, "Cancel");
  cancel.addEventListener("click", () => { pendingImport = null; box.replaceChildren(); });
  if (problem) {
    box.replaceChildren(el("div", { class: "import-preview bad" }, el("p", {}, el("strong", {}, "Cannot import: "), problem), el("div", { class: "controls" }, cancel)));
    return;
  }
  const outcomes = (rec.events.find((e) => e.step === "assess")?.data?.outcomes || []);
  const confirm = el("button", { class: "btn primary small", type: "button", id: "import-confirm", disabled: !hash.ok }, "Import");
  confirm.addEventListener("click", async () => {
    confirm.disabled = true;
    try {
      const r = await api.importRecord(text, name);
      toast(r.matched_preview_run ? `Imported “${r.name}”: content hash verified; it is the preview run “${r.matched_preview_run}”`
                                  : `Imported “${r.name}”: content hash verified${r.same_bundle === false ? " (the data bundle has changed since)" : ""}`, 6000);
      pendingImport = null; renderRecords();
    } catch (e) { toast(`Import refused: ${e.message}`, 7000); confirm.disabled = false; }
  });
  box.replaceChildren(el("div", { class: `import-preview ${hash.ok ? "" : "bad"}` },
    el("dl", { class: "kv compact" },
      el("dt", {}, "Target"), el("dd", {}, String(rec.target ?? "unknown")),
      el("dt", {}, "Data bundle"), el("dd", {}, `${rec.parameters.bundle ?? "unknown"} (${rec.parameters.bundle_kind ?? "unknown kind"})`),
      el("dt", {}, "Analysis"), el("dd", {}, String(rec.parameters.analysis_version ?? "unknown")),
      el("dt", {}, "Created"), el("dd", {}, rec.created_at ? fmtDate(rec.created_at) : "unknown"),
      el("dt", {}, "Logged steps"), el("dd", {}, String(rec.events.length)),
      el("dt", {}, "Outcomes"), el("dd", {}, outcomes.length ? outcomes.map((o) => `${questionLabel(o.question)}: ${categoryLabel(o.category)}`).join(" · ") : "none recorded"),
      el("dt", {}, "Content hash"), el("dd", { class: hash.ok ? "status-ok" : "status-rejected" },
        hash.ok ? `recomputed in this browser: matches (${hash.computed.slice(0, 16)}…)` : `does not match: stated ${String(hash.stated).slice(0, 16)}…, recomputed ${hash.computed.slice(0, 16)}…. The record was modified or is incomplete.`)),
    el("div", { class: "controls" }, confirm, cancel)));
}

// ------------------------------------------------------------------ vault list
function renderVault(list, recs, storage) {
  const allTags = [...new Set(recs.flatMap((r) => r.tags || []))].sort();
  if (tagFilter && !allTags.includes(tagFilter)) tagFilter = null;
  for (const id of [...selected]) if (!recs.some((r) => r.record_id === id)) selected.delete(id);
  const q = query.trim().toLowerCase();
  const shown = recs.filter((r) => (!tagFilter || (r.tags || []).includes(tagFilter)) &&
    (!q || [r.name, r.target_id, r.notes, ...(r.tags || []), r.content_hash].some((x) => String(x || "").toLowerCase().includes(q))));

  const search = el("input", { type: "search", id: "vault-search", placeholder: "Search name, target, notes, tags, hash", "aria-label": "Search saved investigations", value: query });
  search.addEventListener("input", () => { query = search.value; renderVault(list, recs, storage); $("#vault-search")?.focus(); const s = $("#vault-search"); if (s) s.selectionStart = s.selectionEnd = s.value.length; });
  const tagRow = allTags.length ? el("div", { class: "tagrow", role: "group", "aria-label": "Filter by tag" },
    ...[null, ...allTags].map((t) => {
      const b = el("button", { type: "button", class: "tag", "aria-pressed": tagFilter === t ? "true" : "false" }, t ?? "all");
      b.addEventListener("click", () => { tagFilter = t; renderVault(list, recs, storage); });
      return b;
    })) : null;
  const compare = el("button", { class: "btn small", type: "button", id: "vault-compare", disabled: selected.size !== 2 }, `Compare selected (${selected.size}/2)`);
  const cmpBox = el("div", { id: "vault-compare-box", "aria-live": "polite" });
  compare.addEventListener("click", () => compareRecords(cmpBox, [...selected]));

  if (!recs.length) { list.replaceChildren(el("h3", {}, "Saved investigations"), storageNote(storage), el("p", { class: "muted" }, "None yet.")); return; }
  const tbody = el("tbody");
  for (const r of shown) tbody.append(row(r, list, recs, storage));
  list.replaceChildren(el("h3", {}, "Saved investigations ", el("span", { class: "muted" }, `(${shown.length} of ${recs.length})`)), storageNote(storage),
    el("div", { class: "controls vault-tools" }, search, compare), tagRow,
    shown.length ? el("div", { class: "table-wrap" }, el("table", { class: "vault" }, el("thead", {}, el("tr", {},
      ...["", "Name", "Target", "Outcomes", "Saved", "Content hash", "Reproducibility", ""].map((h, i) => el("th", { scope: "col" }, i === 0 ? el("span", { class: "sr-only" }, "Select") : h)))), tbody))
      : el("p", { class: "muted" }, "No saved investigation matches."), cmpBox);
}

function row(r, list, recs, storage) {
  const res = el("span", { class: "muted" }, r.last_replay ? replayText(r.last_replay) : "not replayed yet");
  const sel = el("input", { type: "checkbox", "aria-label": `Select ${r.name} for comparison`, checked: selected.has(r.record_id) || null,
                            disabled: !selected.has(r.record_id) && selected.size >= 2 || null });
  sel.addEventListener("change", () => { sel.checked ? selected.add(r.record_id) : selected.delete(r.record_id); renderVault(list, recs, storage); });
  const open = el("button", { class: "btn small" }, "Open");
  const replay = el("button", { class: "btn small", title: api.isStatic ? "Compares the saved content hash with the precomputed result (no re-execution in the browser)" : "Re-runs the analysis on the same data and compares content hashes" }, api.isStatic ? "Check" : "Replay");
  const rename = el("button", { class: "btn small ghost", "aria-label": `Rename or retag ${r.name}` }, "Edit");
  const clone = el("button", { class: "btn small ghost", "aria-label": `Duplicate ${r.name}` }, "Duplicate");
  const del = el("button", { class: "btn small ghost", "aria-label": `Delete ${r.name}` }, "Delete");
  open.addEventListener("click", async () => {
    try { const d = await api.record(r.record_id); emit("open-record", { ...d, context: sanitizeContext(d.context) }); } catch (e) { toast(e.message); }
  });
  replay.addEventListener("click", async () => {
    const lbl = replay.textContent;
    replay.disabled = true; replay.textContent = api.isStatic ? "Checking…" : "Replaying…";
    try {
      const x = await api.replay(r.record_id);
      res.textContent = replayText(x);
      res.className = x.reproduced ? "status-ok" : "status-rejected";
      toast(x.reproduced ? (api.isStatic ? "Matches the precomputed result exactly" : "Replay reproduced the saved result exactly") : "Differs: " + x.explanation);
    } catch (e) { res.textContent = e.message; }
    replay.disabled = false; replay.textContent = lbl;
  });
  rename.addEventListener("click", () => { renaming = r.record_id; renderVault(list, recs, storage); $(`#rename-${r.record_id}`)?.focus(); });
  clone.addEventListener("click", async () => {
    try { const x = await api.cloneRecord(r.record_id); toast(`Duplicated as “${x.name}”`); renderRecords(); } catch (e) { toast(e.message); }
  });
  del.addEventListener("click", async () => {
    if (!confirmDelete(del)) return;
    try { await api.deleteRecord(r.record_id); selected.delete(r.record_id); toast("Deleted"); renderRecords(); } catch (e) { toast(e.message); }
  });
  const nameCell = renaming === r.record_id ? renameForm(r, list, recs, storage)
    : el("td", {}, r.name, r.imported ? el("span", { class: "faint" }, " · imported") : null,
        (r.tags || []).length ? el("div", { class: "tags" }, ...r.tags.map((t) => el("span", { class: "tag static" }, t))) : null,
        r.modified_at ? el("div", { class: "faint" }, `edited ${fmtDate(r.modified_at)}`) : null);
  return el("tr", {}, el("td", {}, sel), nameCell, el("td", {}, r.target_id, el("div", { class: "faint" }, r.bundle_kind || "")),
    el("td", {}, (r.outcomes || []).length ? r.outcomes.map((o) => `${questionLabel(o.question)}: ${categoryLabel(o.category)}`).join("; ") : el("span", { class: "faint" }, "not stored")),
    el("td", {}, fmtDate(r.saved_at)), el("td", { class: "mono" }, r.content_hash.slice(0, 12)), el("td", {}, res),
    el("td", { class: "row-actions" }, open, replay, rename, clone, del));
}

function renameForm(r, list, recs, storage) {
  const name = el("input", { type: "text", id: `rename-${r.record_id}`, value: r.name, "aria-label": "New name" });
  const tags = el("input", { type: "text", value: (r.tags || []).join(", "), "aria-label": "Tags, separated by commas" });
  const ok = el("button", { class: "btn small primary", type: "button" }, "Save");
  const cancel = el("button", { class: "btn small ghost", type: "button" }, "Cancel");
  const submit = async () => {
    try { await api.updateRecord(r.record_id, { name: name.value, tags: parseTags(tags.value) }); renaming = null; toast("Updated"); renderRecords(); }
    catch (e) { toast(e.message); name.focus(); }
  };
  ok.addEventListener("click", submit);
  cancel.addEventListener("click", () => { renaming = null; renderVault(list, recs, storage); });
  [name, tags].forEach((i) => i.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); if (e.key === "Escape") { e.stopPropagation(); cancel.click(); } }));
  return el("td", { class: "rename" }, el("label", {}, "Name", name), el("label", {}, "Tags", tags), el("div", { class: "controls" }, ok, cancel));
}

// ------------------------------------------------------------------ compare two saved investigations
async function compareRecords(box, ids) {
  box.replaceChildren(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Comparing…"));
  let a, b;
  try { [a, b] = await Promise.all(ids.map((id) => api.record(id))); } catch (e) { box.replaceChildren(el("p", {}, e.message)); return; }
  const same = a.content_hash === b.content_hash;
  const pa = a.parameters || null, pb = b.parameters || null;
  const keys = pa && pb ? [...new Set([...Object.keys(pa), ...Object.keys(pb)])].filter((k) => !["methods"].includes(k)).sort() : [];
  const diffs = keys.filter((k) => JSON.stringify(pa[k]) !== JSON.stringify(pb[k]));
  const outc = (d) => Object.fromEntries((d.outcomes || []).map((o) => [o.question, o.category]));
  const oa = outc(a), ob = outc(b);
  const qs = [...new Set([...Object.keys(oa), ...Object.keys(ob)])];
  const ca = sanitizeContext(a.context), cb = sanitizeContext(b.context);
  const fmtv = (v) => v === undefined ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v);
  box.replaceChildren(el("div", { class: "compare-records" },
    el("h4", {}, `“${a.name}” vs “${b.name}”`),
    el("p", { class: same ? "status-ok" : "" }, same ? "Identical content hash: the two saved investigations contain the same analysis result. Differences below, if any, are in your notes, tags or context."
      : `Different content hashes (${a.content_hash.slice(0, 12)}… vs ${b.content_hash.slice(0, 12)}…).`),
    el("div", { class: "table-wrap" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, ""), el("th", { scope: "col" }, a.name), el("th", { scope: "col" }, b.name))),
      el("tbody", {},
        el("tr", {}, el("th", { scope: "row" }, "Target"), el("td", {}, a.target_id), el("td", {}, b.target_id)),
        el("tr", {}, el("th", { scope: "row" }, "Analysis version"), el("td", {}, fmtv(a.analysis_version)), el("td", {}, fmtv(b.analysis_version))),
        ...qs.map((q) => el("tr", { class: oa[q] !== ob[q] ? "diff" : "" }, el("th", { scope: "row" }, questionLabel(q)), el("td", {}, oa[q] ? categoryLabel(oa[q]) : "—"), el("td", {}, ob[q] ? categoryLabel(ob[q]) : "—"))),
        ...(pa && pb ? diffs.map((k) => el("tr", { class: "diff" }, el("th", { scope: "row" }, k), el("td", { class: "mono wrap" }, fmtv(pa[k])), el("td", { class: "mono wrap" }, fmtv(pb[k]))))
                     : [el("tr", {}, el("th", { scope: "row" }, "Parameters"), el("td", { colspan: "2" }, "Not stored with one of these records (saved by an earlier version); compare the content hashes instead.")) ]),
        el("tr", {}, el("th", { scope: "row" }, "Research question"), el("td", {}, ca.question_text || "—"), el("td", {}, cb.question_text || "—")),
        el("tr", {}, el("th", { scope: "row" }, "Your hypotheses"), el("td", {}, String(ca.hypotheses.length)), el("td", {}, String(cb.hypotheses.length))),
        el("tr", {}, el("th", { scope: "row" }, "Tags"), el("td", {}, (a.tags || []).join(", ") || "—"), el("td", {}, (b.tags || []).join(", ") || "—"))))),
    pa && pb && !diffs.length && !same ? el("p", { class: "muted" }, "Same parameters but different results: the data bundle or software differs (see each record's software versions).") : null,
    pa && pb && diffs.length ? el("p", { class: "muted" }, `${diffs.length} parameter(s) differ (highlighted). Outcome rows that differ are highlighted too.`) : null));
}

function replayText(x) {
  if (x.executed === false) return x.reproduced ? "matches the precomputed result (identical content hash; not re-executed)" : `no match: ${x.explanation}`;
  return x.reproduced ? "reproduced: identical content hash" : `not reproduced: ${x.explanation}`;
}

// Two-step delete without a modal dialog: the first click arms the button.
function confirmDelete(btn) {
  if (btn.dataset.armed) return true;
  btn.dataset.armed = "1"; btn.textContent = "Confirm delete";
  setTimeout(() => { delete btn.dataset.armed; btn.textContent = "Delete"; }, 3000);
  return false;
}
