// Application state, derived views of the investigation record, and URL syncing.

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
};

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
  return m;
}

export function compatible(model, a, b) {
  return model ? model.acceptedSet.has(a + "|" + b) : false;
}

// Client-side mirror of WLMATCH-1, used only to explain to the user why a pair is unavailable.
// The server's decision (accepted pairs in the record) is authoritative.
export function compatibilityReason(model, a, b) {
  const ma = model?.measurements[a], mb = model?.measurements[b];
  if (!ma || !mb) return "no measurement for one of the observations";
  if (ma.detector !== mb.detector) return `different detectors (D${ma.detector} vs D${mb.detector})`;
  if (ma.quality !== "ok") return `${a} unusable: ${ma.quality}`;
  if (mb.quality !== "ok") return `${b} unusable: ${mb.quality}`;
  if (ma.wavelength_um == null || mb.wavelength_um == null) return "wavelength unknown";
  const dl = Math.abs(ma.wavelength_um - mb.wavelength_um);
  const tol = model.tolerance * Math.min(ma.bandwidth_um, mb.bandwidth_um);
  return dl > tol ? `wavelength mismatch: |Δλ| = ${dl.toFixed(4)} µm > ${tol.toFixed(4)} µm` : `|Δλ| = ${dl.toFixed(4)} µm ≤ ${tol.toFixed(4)} µm`;
}

export function writeHash() {
  const p = new URLSearchParams();
  if (state.targetId) p.set("target", state.targetId);
  if (state.selectedKey) p.set("obs", state.selectedKey);
  if (state.partnerKey && state.ws === "time") p.set("b", state.partnerKey);
  const h = `#/${state.ws}?${p.toString()}`;
  if (location.hash !== h) history.replaceState(null, "", h);
}

export function readHash() {
  const m = location.hash.match(/^#\/(\w+)\??(.*)$/);
  if (!m) return {};
  const p = new URLSearchParams(m[2]);
  return { ws: m[1], target: p.get("target"), obs: p.get("obs"), b: p.get("b") };
}
