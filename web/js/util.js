// Small DOM and formatting helpers. No external libraries: the app must run offline.

export function el(tag, attrs = {}, ...children) {
  const isSvg = ["svg", "g", "path", "line", "circle", "rect", "text", "polyline", "title", "defs", "marker", "tspan"].includes(tag);
  const n = isSvg ? document.createElementNS("http://www.w3.org/2000/svg", tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (k === "class") n.setAttribute("class", v);
    else if (k === "dataset") Object.assign(n.dataset, v);
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return n;
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

export function fmt(x, nd = 2) {
  if (x === null || x === undefined || (typeof x === "number" && !Number.isFinite(x))) return "—";
  if (typeof x !== "number") return String(x);
  if (Number.isInteger(x) && Math.abs(x) < 1e15) nd = 0;
  return x.toLocaleString("en-US", { minimumFractionDigits: nd, maximumFractionDigits: nd });
}

export const fmtInt = (x) => fmt(x, 0);

export function fmtDate(iso) {
  if (!iso) return "—";
  return iso.slice(0, 10) + (iso.length > 10 ? " " + iso.slice(11, 16) : "");
}

export function shortKey(key) {
  if (!key) return "";
  const p = key.split(":");
  return p.length === 3 ? `${p[1]} ${p[2]}` : key;
}

export const DET_COLORS = { 1: "#f3d27a", 2: "#f0a35e", 3: "#e07a5f", 4: "#c5609a", 5: "#8e6bd1", 6: "#5c83d9" };
export const DET_BANDS = { 1: [0.75, 1.09], 2: [1.10, 1.62], 3: [1.63, 2.41], 4: [2.42, 3.82], 5: [3.83, 4.41], 6: [4.42, 5.00] };

export function detSwatch(d) { const s = el("span", { class: "det" }); s.style.background = DET_COLORS[d] || "#888"; return s; }

let toastTimer;
export function toast(msg, ms = 3200) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, ms);
}

export function categoryLabel(c) {
  return ({
    motion_detected: "Motion detected", motion_inconsistent: "Motion disagrees with catalogue", registration_limited: "Limited by registration",
    variability_candidate: "Variability candidate", spectral_difference_only: "Spectral differences only", instrumental: "Mostly unusable data",
    partially_usable: "Some exposures rejected", insufficient_evidence: "Insufficient evidence", no_significant_change: "No significant change",
    no_motion_at_sensitivity: "No motion at this sensitivity", no_variability_at_sensitivity: "No change at this sensitivity",
    measurement_failed: "Measurement failed", calibration_limited: "Limited by calibration", all_usable: "All exposures usable",
  })[c] || c;
}

export function questionLabel(q) {
  return ({ motion: "Motion", variability: "Brightness change", data_quality: "Data quality" })[q] || q;
}

export function b64ToFloat32(b64) {
  const bin = atob(b64); const buf = new ArrayBuffer(bin.length); const u8 = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Float32Array(buf);
}
export function b64ToUint8(b64) {
  const bin = atob(b64); const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}

// Offer a file to save. Inside a claude.ai artifact viewer, page-started downloads are blocked, so the viewer's
// `downloads` capability is used (the viewer confirms the save). Elsewhere (the local app, a plain browser) a Blob
// link is used. Resolves true when the file was handed over, false (with a message) otherwise.
export async function download(name, text, type = "text/markdown") {
  if (window.claude?.use) {
    let dl = null;
    try { dl = await window.claude.use("downloads"); } catch { dl = null; }
    if (!dl) { toast("Saving files is not available in this view."); return false; }
    try { await dl.save({ filename: name, data: text }); return true; }
    catch (e) { toast(e?.code === "declined" ? "Not saved." : `Could not save the file (${e?.code || "unavailable"}).`); return false; }
  }
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  document.body.append(a); a.click(); a.remove();
  return true;
}

// Copy text; where the clipboard is refused, select the text so the viewer can copy it themselves.
export async function copyText(text, selectEl) {
  try { await navigator.clipboard.writeText(text); toast("Copied"); }
  catch {
    if (selectEl) { const r = document.createRange(); r.selectNodeContents(selectEl); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }
    toast("Copy was blocked here; the text is selected so you can copy it.");
  }
}
