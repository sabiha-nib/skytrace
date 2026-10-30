// The active Research Session (SESSION-1): one persistent, integrity-checked context shared by every workspace.
// It holds the user's question, the analysis runs used (by content hash), hypotheses, notebook, annotations, plans,
// experiments, missions, examined pairs and an append-only activity history. Every change is one function call here,
// logged as an event and saved (server: data/sessions/; static preview: this browser's storage). The backend validates
// the session against the shared schema and recomputes its content hash; the browser never stores an unvalidated copy.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { logEvent, nowIso, rid } from "./sessioncore.js";
import { toast } from "./util.js";

const ACTIVE_KEY = "skytrace.session.active";
let saving = null, pending = null;

function remember(sid) { try { localStorage.setItem(ACTIVE_KEY, sid); } catch { /* per-viewer convenience */ } }
function remembered() { try { return localStorage.getItem(ACTIVE_KEY); } catch { return null; } }

/** Load the remembered session, if it still exists. Never creates one. */
export async function restoreSession() {
  const sid = remembered();
  if (!sid) return null;
  try { state.session = stripV(await api.session(sid)); } catch { state.session = null; }
  syncContextFromSession();
  emit("session-changed");
  return state.session;
}

const stripV = (s) => { const { _verification, ...rest } = s; return rest; };

/** The active session, creating one for the current target the first time something needs recording. */
export async function ensureSession() {
  if (state.session) return state.session;
  const t = state.targets.find((x) => x.target_id === state.targetId);
  state.session = await api.createSession(`${t?.name || "Research"} — ${new Date().toISOString().slice(0, 10)}`, state.targetId || null);
  remember(state.session.session_id);
  emit("session-changed");
  if (state.inv) await attachRun(state.inv, "current analysis");
  return state.session;
}

export async function openSession(sid) {
  state.session = stripV(await api.session(sid));
  remember(sid);
  syncContextFromSession();
  emit("session-changed");
  return state.session;
}

export async function newSession(name) {
  state.session = await api.createSession(name, state.targetId || null);
  remember(state.session.session_id);
  syncContextFromSession();
  emit("session-changed");
  return state.session;
}

export function closeSession() {
  state.session = null;
  try { localStorage.removeItem(ACTIVE_KEY); } catch { /* ignore */ }
  emit("session-changed");
}

/** Apply a change and log it. `fn(session)` returns the changed session (or mutates a copy it was given). */
export async function update(kind, summary, fn = (s) => s, ref = null) {
  const s0 = await ensureSession();
  let s = structuredClone(s0);
  s = fn(s) || s;
  s = logEvent(s, kind, summary, ref);
  state.session = s;
  emit("session-changed");
  scheduleSave();
  return s;
}

/** Log an event without other changes (e.g. a workspace or pair was viewed). Only when a session exists already,
 *  except for `create` events that should start one. */
export async function log(kind, summary, ref = null, { create = false } = {}) {
  if (!state.session && !create) return null;
  const last = state.session?.history?.[state.session.history.length - 1];
  if (last && last.kind === kind && last.ref === (ref === null ? null : String(ref).slice(0, 300))) return state.session;   // no repeated views
  return update(kind, summary, (s) => s, ref);
}

function scheduleSave() {
  pending = state.session;
  if (saving) return;
  saving = (async () => {
    while (pending) {
      const s = pending;
      pending = null;
      try {
        const stored = await api.saveSession(s);
        if (!pending) state.session = stored;           // keep the backend's content hash
        emit("session-saved", stored);
      } catch (e) { toast(`The session could not be saved: ${e.message}`, 7000); }
    }
    saving = null;
  })();
}

export async function flush() { while (saving) await saving; }

// ------------------------------------------------------------------ the Phase 5 context is a view of the session
export function syncContextFromSession() {
  const s = state.session;
  if (!s) return;
  state.context = { question: s.question.id, question_text: s.question.text, hypotheses: structuredClone(s.hypotheses) };
}

export async function syncSessionFromContext() {
  const c = state.context;
  const s = state.session;
  if (s && s.question.text === c.question_text && JSON.stringify(s.hypotheses) === JSON.stringify(c.hypotheses)) return;
  const prev = s?.hypotheses || [];
  await update("context.update", "Research question or hypotheses changed", (x) => {
    x.question = { id: c.question || null, text: (c.question_text || "").slice(0, 500) };
    x.hypotheses = c.hypotheses.map((h) => {
      const old = prev.find((p) => p.id === h.id);
      const versions = old && old.statement !== h.statement ? [...(old.versions || []), { at: nowIso(), text: old.statement }].slice(-20) : (old?.versions || h.versions);
      return { id: h.id, statement: h.statement, tests: h.tests, kind: "interpretation", created_at: h.created_at || nowIso(), ...(versions ? { versions } : {}) };
    });
    return x;
  });
}

/** Attach the current analysis run to the session (by content hash) and make it active. */
export async function attachRun(inv, label = "analysis") {
  if (!inv) return;
  const h = inv.record.content_hash;
  const params = Object.fromEntries(Object.entries(inv.record.parameters || {}).filter(([k, v]) =>
    ["number", "boolean"].includes(typeof v) && /^[a-z_]{1,40}$/.test(k) && k !== "max_observations").slice(0, 20));
  const s = state.session;
  if (s && s.active_hash === h && s.runs.some((r) => r.content_hash === h)) return;
  await update("run.attach", `Analysis run ${h.slice(0, 12)} attached (${label})`, (x) => {
    if (!x.runs.some((r) => r.content_hash === h))
      x.runs = [...x.runs, { investigation_id: inv.investigation_id, content_hash: h, label: label.slice(0, 120), attached_at: nowIso(), params }].slice(-50);
    x.active_hash = h;
    if (!x.target_id) x.target_id = state.targetId;
    return x;
  }, h);
}

export const newId = (p = "x") => `${p}${rid(4)}`;
