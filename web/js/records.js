// Saved investigations: save, reopen, replay (reproducibility check) and delete.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { $, clear, el, fmtDate, toast } from "./util.js";

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
  body.append(el("div", { class: "card" }, el("h3", {}, "Save the current investigation"),
    state.inv ? el("p", { class: "muted" }, `Saves the parameters, the data bundle checksum, every logged step and result, and the copilot conversation (${state.transcript.length} messages).`)
              : el("p", { class: "muted" }, "Run an analysis first."),
    el("div", { class: "params" }, el("label", {}, "Name", name), el("label", {}, "Notes", notes)), el("div", { class: "controls" }, save)));

  const list = el("div", { class: "card" }, el("h3", {}, "Saved investigations"), el("p", { class: "busy" }, el("span", { class: "spinner" }), "Loading…"));
  body.append(list);
  let recs;
  try { recs = (await api.records()).records; } catch (e) { list.replaceChildren(el("p", {}, e.message)); return; }
  if (!recs.length) { list.replaceChildren(el("h3", {}, "Saved investigations"), el("p", { class: "muted" }, "None yet.")); return; }
  const tbody = el("tbody");
  for (const r of recs) {
    const res = el("span", { class: "muted" }, r.last_replay ? (r.last_replay.reproduced ? "reproduced" : `not reproduced: ${r.last_replay.explanation}`) : "not replayed yet");
    const open = el("button", { class: "btn small" }, "Open");
    const replay = el("button", { class: "btn small" }, "Replay");
    const del = el("button", { class: "btn small ghost", "aria-label": `Delete ${r.name}` }, "Delete");
    open.addEventListener("click", async () => {
      try { const d = await api.record(r.record_id); emit("open-record", d); } catch (e) { toast(e.message); }
    });
    replay.addEventListener("click", async () => {
      replay.disabled = true; replay.textContent = "Replaying…";
      try {
        const x = await api.replay(r.record_id);
        res.textContent = x.reproduced ? "reproduced: identical content hash" : `not reproduced: ${x.explanation}`;
        res.className = x.reproduced ? "status-ok" : "status-rejected";
        toast(x.reproduced ? "Replay reproduced the saved result exactly" : "Replay differs: " + x.explanation);
      } catch (e) { res.textContent = e.message; }
      replay.disabled = false; replay.textContent = "Replay";
    });
    del.addEventListener("click", async () => {
      if (!confirmDelete(del)) return;
      try { await api.deleteRecord(r.record_id); toast("Deleted"); renderRecords(); } catch (e) { toast(e.message); }
    });
    tbody.append(el("tr", {}, el("td", {}, r.name), el("td", {}, r.target_id), el("td", {}, r.bundle_kind || "—"), el("td", {}, fmtDate(r.saved_at)),
      el("td", { class: "mono" }, r.content_hash.slice(0, 12)), el("td", {}, res), el("td", {}, open, " ", replay, " ", del)));
  }
  list.replaceChildren(el("h3", {}, "Saved investigations"),
    el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Name", "Target", "Data", "Saved", "Content hash", "Replay", ""].map((h) => el("th", { scope: "col" }, h)))), tbody)));
}

// Two-step delete without a modal dialog: the first click arms the button.
function confirmDelete(btn) {
  if (btn.dataset.armed) return true;
  btn.dataset.armed = "1"; btn.textContent = "Confirm delete";
  setTimeout(() => { delete btn.dataset.armed; btn.textContent = "Delete"; }, 3000);
  return false;
}
