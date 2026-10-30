// Research session switcher (nav) and the sessions dialog: open, create, rename, export, import (verified), delete.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import * as S from "./session.js";
import { finalize, logEvent, nowIso, rid } from "./sessioncore.js";
import { $, clear, download, el, fmtDate, toast } from "./util.js";

let opener = null;

export function renderSessionBox() {
  const box = $("#session-box");
  if (!box) return;
  const s = state.session;
  const b = el("button", { type: "button", class: "session-btn", id: "session-btn", "aria-haspopup": "dialog",
                           title: s ? `Session ${s.session_id} · content hash ${String(s.content_hash || "").slice(0, 12)}…` : "No research session yet" },
    el("span", { class: "session-label" }, "Session"), el("span", { class: "session-name" }, s ? s.name : "none yet"));
  b.addEventListener("click", openSessions);
  box.replaceChildren(b, s ? el("div", { class: "session-meta" }, `${s.runs.length} run(s) · ${s.notebook.length} note(s) · ${s.history.length} events`)
    : el("div", { class: "session-meta" }, "Starts when you set a question, write a note or start a plan"));
}

export function bindSessions() {
  $("#sessions-close").addEventListener("click", closeSessions);
  $("#sessions").addEventListener("mousedown", (e) => { if (e.target.id === "sessions") closeSessions(); });
  $("#sessions").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); closeSessions(); }
    if (e.key === "Tab") {
      const f = [...$("#sessions").querySelectorAll("button, input, label.btn, [href]")].filter((x) => !x.disabled && x.offsetParent);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
    }
  });
}

export async function openSessions() {
  opener = document.activeElement;
  $("#sessions").hidden = false;
  await renderSessionsBody();
  $("#sessions-close").focus();
}

export function closeSessions() {
  $("#sessions").hidden = true;
  opener?.focus?.();
}

async function renderSessionsBody() {
  const body = $("#sessions-body");
  clear(body).append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Loading sessions…"));
  let list;
  try { list = await api.sessions(); } catch (e) { clear(body).append(el("p", {}, e.message)); return; }
  const name = el("input", { type: "text", id: "session-new-name", placeholder: "Name of the new session", "aria-label": "Name of the new session" });
  const create = el("button", { class: "btn primary small", type: "button", id: "session-new" }, "New session");
  create.addEventListener("click", async () => {
    try {
      await S.newSession(name.value.trim() || `Research — ${new Date().toISOString().slice(0, 10)}`);
      if (state.inv) await S.attachRun(state.inv, "current analysis");
      toast(`Session “${state.session.name}” started`); renderSessionsBody();
    } catch (e) { toast(e.message); }
  });
  const file = el("input", { type: "file", accept: "application/json,.json", id: "session-import-file", class: "sr-only" });
  const pick = el("label", { class: "btn small", for: "session-import-file" }, "Import session (JSON)…");
  file.addEventListener("change", async () => {
    const f = file.files[0];
    file.value = "";
    if (!f) return;
    if (f.size > 1_200_000) { toast("Import refused: larger than the session size limit", 6000); return; }
    let obj;
    try { obj = JSON.parse(await f.text()); } catch { toast("Import refused: the file is not JSON", 6000); return; }
    try {
      const r = await api.importSession(obj);
      toast(`Imported “${r.name}”${r.hash_verified ? ": content hash verified" : " (no hash was stated)"}`, 6000);
      await S.openSession(r.session_id); renderSessionsBody();
    } catch (e) { toast(`Import refused: ${e.message}`, 7000); }
  });
  const cur = state.session;
  const rename = el("input", { type: "text", value: cur?.name || "", "aria-label": "Rename the active session", disabled: !cur || null });
  const doRename = el("button", { class: "btn small", type: "button", disabled: !cur || null }, "Rename");
  doRename.addEventListener("click", async () => {
    const v = rename.value.trim();
    if (!v) { toast("A session needs a name"); return; }
    await S.update("session.rename", `Renamed to “${v.slice(0, 80)}”`, (s) => { s.name = v.slice(0, 120); return s; });
    renderSessionsBody();
  });
  const exp = el("button", { class: "btn small", type: "button", id: "session-export", disabled: !cur || null }, "Export session (JSON)");
  exp.addEventListener("click", async () => {
    await S.log("session.export", "Session exported (JSON)");
    await S.flush();
    if (await download(`skytrace-session-${state.session.session_id}.json`, JSON.stringify(state.session, null, 1), "application/json")) toast("Session exported");
  });
  // Branch: an independent copy under a new id, so an alternative line of work never alters the original. The copy
  // keeps the full history and records where it came from; it is saved through the same verified import path.
  const branch = el("button", { class: "btn small", type: "button", id: "session-branch", disabled: !cur || null,
                                title: "Copy the active session under a new id; the original stays unchanged" }, "Branch session");
  branch.addEventListener("click", async () => {
    try {
      await S.flush();
      const src = state.session;
      const b = await finalize(logEvent({ ...structuredClone(src), session_id: rid(6), name: `Branch of ${src.name}`.slice(0, 120), created_at: nowIso() },
        "session.branch", `Branched from session ${src.session_id} (content hash ${String(src.content_hash).slice(0, 12)}…)`, src.session_id));
      const r = await api.importSession(b);
      await S.openSession(r.session_id);
      toast(`Branched into “${r.name}”; the original session is unchanged`, 6000); renderSessionsBody();
    } catch (e) { toast(`Branch failed: ${e.message}`, 7000); }
  });
  const rows = list.sessions.map((x) => {
    const open = el("button", { class: "btn small", type: "button", disabled: x.session_id === cur?.session_id || null }, x.session_id === cur?.session_id ? "Active" : "Open");
    open.addEventListener("click", async () => { await S.openSession(x.session_id); toast(`Opened “${x.name}”`); renderSessionsBody(); });
    const del = el("button", { class: "btn small ghost", type: "button", "aria-label": `Delete session ${x.name}` }, "Delete");
    del.addEventListener("click", async () => {
      if (!del.dataset.armed) { del.dataset.armed = "1"; del.textContent = "Confirm delete"; setTimeout(() => { delete del.dataset.armed; del.textContent = "Delete"; }, 3000); return; }
      await api.deleteSession(x.session_id);
      if (cur?.session_id === x.session_id) S.closeSession();
      toast("Session deleted"); renderSessionsBody();
    });
    return el("tr", {}, el("td", {}, x.name, el("div", { class: "faint" }, x.question || "no question yet")), el("td", {}, x.target_id || "—"),
      el("td", {}, `${x.n_runs} · ${x.n_notes} · ${x.n_hypotheses}`), el("td", {}, fmtDate(x.modified_at)),
      el("td", { class: x.integrity === "ok" ? "status-ok" : "status-rejected" }, x.integrity === "ok" ? "hash verified" : x.integrity),
      el("td", { class: "row-actions" }, open, del));
  });
  clear(body).append(
    el("p", { class: "muted" }, list.storage === "server" ? "Sessions are stored on the Skytrace server (data/sessions/), validated and hash-checked on every save."
      : "Static preview: sessions are stored in this browser only. Export a session to keep it or move it to the full application."),
    el("div", { class: "controls" }, name, create, file, pick),
    cur ? el("div", { class: "controls" }, rename, doRename, exp, branch) : null,
    list.sessions.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Session", "Target", "Runs · notes · hypotheses", "Modified", "Integrity", ""].map((h) => el("th", { scope: "col" }, h)))), el("tbody", {}, ...rows)))
      : el("p", { class: "muted" }, "No sessions yet."),
    list.unreadable?.length ? el("p", { class: "status-rejected" }, `Unreadable session files (kept, not deleted): ${list.unreadable.join(", ")}`) : null);
  emit("session-changed");
}
