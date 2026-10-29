// Saved investigations: save, reopen, replay (reproducibility check), export, import and delete.
// With the server, records are JSON files in data/records/ and replay re-executes the analysis.
// In the static preview, records live in this browser's storage only, and "replay" compares the saved content hash
// with the result the Python pipeline produced for the preview (it cannot re-execute in the browser). Both say so.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { $, clear, download, el, fmtDate, toast } from "./util.js";

function storageNote(kind) {
  if (!api.isStatic) return el("p", { class: "muted" }, "Records are saved on the Skytrace server (data/records/) and survive restarts.");
  return kind === "browser"
    ? el("p", { class: "muted", id: "storage-note" }, "Static preview: records are saved in this browser only (local storage). They are not shared and are lost if browser data is cleared. Export a record to keep it.")
    : el("p", { class: "muted", id: "storage-note" }, "Static preview: this browser does not allow storage here, so records last only until the page is closed. Export a record to keep it.");
}

export async function renderRecords() {
  const body = $("#records-body");
  clear(body);
  const name = el("input", { type: "text", placeholder: "Name this investigation", "aria-label": "Investigation name", value: state.inv ? `${state.inv.record.target} — ${new Date().toISOString().slice(0, 10)}` : "" });
  const notes = el("textarea", { placeholder: "Notes (optional)", "aria-label": "Notes", rows: "2" });
  const save = el("button", { class: "btn primary", disabled: !state.inv }, "Save investigation");
  save.addEventListener("click", async () => {
    try {
      const r = await api.saveRecord({ investigation_id: state.inv.investigation_id, name: name.value, notes: notes.value, transcript: state.transcript });
      toast(`Saved “${r.name}”`); renderRecords();
    } catch (e) { toast(e.message); }
  });
  const exp = el("button", { class: "btn", id: "export-record", disabled: !state.inv, title: "Download the investigation record (JSON) exactly as the pipeline wrote it" }, "Export record (JSON)");
  exp.addEventListener("click", async () => {
    try {
      const text = await api.recordText(state.inv.investigation_id);
      if (await download(`skytrace-${state.targetId}-${state.inv.investigation_id}.json`, text, "application/json")) toast("Record exported");
    } catch (e) { toast(e.message); }
  });
  body.append(el("div", { class: "card" }, el("h3", {}, "Save the current investigation"),
    state.inv ? el("p", { class: "muted" }, `Saves the parameters, the data bundle checksum, every logged step and result (content hash ${state.inv.record.content_hash.slice(0, 12)}…), and the copilot conversation (${state.transcript.length} messages).`)
              : el("p", { class: "muted" }, "Run an analysis first."),
    el("div", { class: "params" }, el("label", {}, "Name", name), el("label", {}, "Notes", notes)), el("div", { class: "controls" }, save, exp)));

  const file = el("input", { type: "file", accept: "application/json,.json", id: "import-file", class: "sr-only" });
  const pick = el("label", { class: "btn", for: "import-file" }, "Import record (JSON)…");
  file.addEventListener("change", async () => {
    const f = file.files[0];
    if (!f) return;
    try {
      const r = await api.importRecord(await f.text(), f.name.replace(/\.json$/i, ""));
      toast(r.matched_preview_run ? `Imported “${r.name}”: content hash verified; it is the preview run “${r.matched_preview_run}”`
                                  : `Imported “${r.name}”: content hash verified${r.same_bundle === false ? " (the data bundle has changed since)" : ""}`, 6000);
      renderRecords();
    } catch (e) { toast(`Import refused: ${e.message}`, 7000); }
    file.value = "";
  });
  body.append(el("div", { class: "card" }, el("h3", {}, "Import"),
    el("p", { class: "muted" }, api.isStatic
      ? "Reopen a record exported from this preview. Records from other runs need the full application, which verifies the content hash and can replay them."
      : "Import an exported record. Its content hash must recompute and its data bundle must be present on this machine; replay then re-executes it."),
    el("div", { class: "controls" }, file, pick)));

  const list = el("div", { class: "card" }, el("h3", {}, "Saved investigations"), el("p", { class: "busy" }, el("span", { class: "spinner" }), "Loading…"));
  body.append(list);
  let recs, storage;
  try { ({ records: recs, storage } = await api.records()); } catch (e) { list.replaceChildren(el("p", {}, e.message)); return; }
  if (!recs.length) { list.replaceChildren(el("h3", {}, "Saved investigations"), storageNote(storage), el("p", { class: "muted" }, "None yet.")); return; }
  const tbody = el("tbody");
  for (const r of recs) {
    const res = el("span", { class: "muted" }, r.last_replay ? replayText(r.last_replay) : "not replayed yet");
    const open = el("button", { class: "btn small" }, "Open");
    const replay = el("button", { class: "btn small", title: api.isStatic ? "Compares the saved content hash with the precomputed result (no re-execution in the browser)" : "Re-runs the analysis on the same data and compares content hashes" }, api.isStatic ? "Check" : "Replay");
    const del = el("button", { class: "btn small ghost", "aria-label": `Delete ${r.name}` }, "Delete");
    open.addEventListener("click", async () => {
      try { const d = await api.record(r.record_id); emit("open-record", d); } catch (e) { toast(e.message); }
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
    del.addEventListener("click", async () => {
      if (!confirmDelete(del)) return;
      try { await api.deleteRecord(r.record_id); toast("Deleted"); renderRecords(); } catch (e) { toast(e.message); }
    });
    tbody.append(el("tr", {}, el("td", {}, r.name, r.imported ? el("span", { class: "faint" }, " · imported") : null), el("td", {}, r.target_id), el("td", {}, r.bundle_kind || "—"), el("td", {}, fmtDate(r.saved_at)),
      el("td", { class: "mono" }, r.content_hash.slice(0, 12)), el("td", {}, res), el("td", { class: "row-actions" }, open, replay, del)));
  }
  list.replaceChildren(el("h3", {}, "Saved investigations"), storageNote(storage),
    el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Name", "Target", "Data", "Saved", "Content hash", "Reproducibility", ""].map((h) => el("th", { scope: "col" }, h)))), tbody)));
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
