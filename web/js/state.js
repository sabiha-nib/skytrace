// Application state, derived views of the investigation record, and URL syncing.

import { api } from "./api.js";

const listeners = new Map();

export const state = {
  status: null,
  targets: [],
  targetId: null,
  target: null,          // bundle detail (null when no data)
  inv: null,             // {investigation_id, record, ...}
  prevInv: null,         // previous run of the same target, for sensitivity comparison
  model: null,           // derived from inv.record
  selectedKey: null,
  partnerKey: null,
  ws: "explorer",
  transcript: [],
  context: emptyContext(),  // the user's investigation context: research question and own hypotheses (saved with records)
  discovery: null,          // {iid, data}: DISC-1 report for the current investigation
  stability: null,          // {target, result}: last STAB-1 result
  level: "investigate",     // explore | investigate | research (views of the same state)
};

export function emptyContext() { return { question: null, question_text: "", hypotheses: [] }; }

/** Context from a saved or imported record is untrusted: keep only the known fields, as plain bounded strings. */
export function sanitizeContext(c) {
  const out = emptyContext();
  if (!c || typeof c !== "object") return out;
  const str = (x, n) => (typeof x === "string" ? x.slice(0, n) : "");
  if (typeof c.question === "string" && /^Q-[A-Z]{2,10}$/.test(c.question)) out.question = c.question;
  out.question_text = str(c.question_text, 500);
  if (Array.isArray(c.hypotheses)) {
    out.hypotheses = c.hypotheses.filter((h) => h && typeof h === "object" && typeof h.statement === "string" && h.statement.trim()).slice(0, 50).map((h, i) => ({
      id: str(h.id, 40) || `U${i}`, statement: str(h.statement, 1000), kind: "interpretation", created_at: str(h.created_at, 40),
      tests: Array.isArray(h.tests) ? h.tests.filter((t) => typeof t === "string").map((t) => t.slice(0, 60)).slice(0, 30) : [] }));
  }
  return out;
}

/** DISC-1 report for the current investigation (fetched once per investigation). */
export async function getDiscovery() {
  if (!state.inv) return null;
  const iid = state.inv.investigation_id;
  if (state.discovery?.iid !== iid) state.discovery = { iid, data: await api.discovery(iid) };
  return state.discovery.data;
}

export function on(evt, fn) { (listeners.get(evt) || listeners.set(evt, []).get(evt)).push(fn); }
export function emit(evt, payload) { (listeners.get(evt) || []).forEach((fn) => fn(payload)); }

export function deriveModel(record) {
  const m = { measurements: {}, events: record.events, byStep: {}, outcomes: [], accepted: [], flux: [], acceptedSet: new Set(),
              astrometry: null, spectrum: [], synthetic: record.parameters.bundle_kind === "synthetic", record };
  record.events.forEach((e, i) => {
    (m.byStep[e.step] ||= []).push({ ...e, index: i });
    if (e.step === "measure" && e.data && e.data.key) m.measurements[e.data.key] = { ...e.data, status: e.status, detail: e.detail, index: i };
  });
  const first = (s) => (m.byStep[s] || [])[0];
  m.outcomes = first("assess")?.data?.outcomes || [];
  m.accepted = first("pairs")?.data?.accepted || [];
  m.accepted.forEach((p) => { m.acceptedSet.add(p.a + "|" + p.b); m.acceptedSet.add(p.b + "|" + p.a); });
  m.flux = first("variability")?.data?.pairs || [];
  const a = first("astrometry");
  m.astrometry = a && a.status === "ok" ? a.data : null;
  m.astrometryEvent = a || null;
  m.spectrum = first("spectrum")?.data?.points || [];
  m.pairRejections = first("pairs")?.data?.rejection_reasons || {};
  m.tolerance = record.parameters.wavelength_tolerance_channels;
  m.marginUm = record.parameters.wavelength_margin_um ?? 0;
  m.sameRelease = record.parameters.photometry_same_release ?? false;
  m.pairRule = first("pairs")?.data?.rule || "WLMATCH-1";
  m.calcheck = first("variability")?.data?.calibration_check || null;
  return m;
}

export function compatible(model, a, b) {
  return model ? model.acceptedSet.has(a + "|" + b) : false;
}

// Client-side mirror of the wavelength-match rule (WLMATCH-2; WLMATCH-1 for older records), used only to
// explain to the user why a pair is unavailable. The server's decision (accepted pairs in the record) is authoritative.
export function compatibilityReason(model, a, b) {
  const ma = model?.measurements[a], mb = model?.measurements[b];
  if (!ma || !mb) return "no measurement for one of the observations";
  if (ma.detector !== mb.detector) return `different detectors (D${ma.detector} vs D${mb.detector})`;
  const qa = ma.quality_code ?? (ma.quality === "ok" ? "ok" : ma.quality), qb = mb.quality_code ?? (mb.quality === "ok" ? "ok" : mb.quality);
  if (qa !== "ok") return `${a} unusable for photometry: ${qa}`;
  if (qb !== "ok") return `${b} unusable for photometry: ${qb}`;
  if (model.sameRelease && ma.release !== mb.release) return `different releases (${ma.release} vs ${mb.release}): calibrations may differ`;
  if (ma.wavelength_um == null || mb.wavelength_um == null) return "wavelength unknown";
  const dl = Math.abs(ma.wavelength_um - mb.wavelength_um);
  const tol = model.tolerance * Math.min(ma.bandwidth_um, mb.bandwidth_um);
  if (dl > tol) return `wavelength mismatch: |Δλ| = ${dl.toFixed(4)} µm > ${tol.toFixed(4)} µm`;
  if (dl + model.marginUm > tol) return `wavelength match ambiguous: |Δλ| = ${dl.toFixed(4)} µm is within the ${(model.marginUm * 1000).toFixed(1)} nm accuracy margin of ${tol.toFixed(4)} µm`;
  return `|Δλ| = ${dl.toFixed(4)} µm ≤ ${tol.toFixed(4)} µm`;
}

// URL state. Workspace and target changes push a history entry (so browser back/forward move between them);
// selection changes within a workspace replace the current entry.
export function writeHash(push = false) {
  const p = new URLSearchParams();
  if (state.targetId) p.set("target", state.targetId);
  if (state.selectedKey) p.set("obs", state.selectedKey);
  if (state.partnerKey && state.ws === "time") p.set("b", state.partnerKey);
  const h = `#/${state.ws}?${p.toString()}`;
  if (location.hash === h) return;
  const prev = readHash();
  if (push && (prev.ws !== state.ws || prev.target !== state.targetId)) history.pushState(null, "", h);
  else history.replaceState(null, "", h);
}

export function readHash() {
  const m = location.hash.match(/^#\/(\w+)\??(.*)$/);
  if (!m) return {};
  const p = new URLSearchParams(m[2]);
  return { ws: m[1], target: p.get("target"), obs: p.get("obs"), b: p.get("b") };
}
