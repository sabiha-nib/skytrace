// Command palette (Ctrl/⌘+K or /) and the glossary/shortcut reference (?). Both are modal dialogs with focus kept
// inside and returned to the opener on close. Commands only call existing actions; nothing here computes results.

import { state } from "./state.js";
import { $, clear, el, fmtDate, shortKey } from "./util.js";

let commands = [], shown = [], active = 0, opener = null, build = () => [];

export function bindPalette(buildCommands) {
  build = buildCommands;
  const input = $("#palette-input");
  input.addEventListener("input", () => { active = 0; renderList(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(shown.length - 1, active + 1); renderList(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(0, active - 1); renderList(); }
    else if (e.key === "Enter") { e.preventDefault(); run(shown[active]); }
    else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
    else if (e.key === "Tab") e.preventDefault();          // focus stays in the dialog
  });
  $("#palette").addEventListener("mousedown", (e) => { if (e.target.id === "palette") closePalette(); });
  $("#help").addEventListener("mousedown", (e) => { if (e.target.id === "help") closeHelp(); });
  $("#help-close").addEventListener("click", closeHelp);
  $("#help").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); closeHelp(); }
    if (e.key === "Tab") {   // keep focus inside the dialog
      const f = [...$("#help").querySelectorAll("button, [href], input, summary")];
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
    }
  });
}

export function openPalette() {
  opener = document.activeElement;
  commands = build();
  $("#palette").hidden = false;
  const input = $("#palette-input");
  input.value = ""; active = 0; renderList();
  input.focus();
}

export function closePalette() {
  $("#palette").hidden = true;
  opener?.focus?.();
}

function score(c, q) {
  if (!q) return 1;
  const hay = (c.label + " " + (c.hint || "") + " " + (c.group || "")).toLowerCase();
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.every((w) => hay.includes(w))) return 0;
  return c.label.toLowerCase().startsWith(words[0]) ? 3 : hay.includes(q.toLowerCase()) ? 2 : 1;
}

function renderList() {
  const q = $("#palette-input").value.trim();
  shown = commands.map((c) => [score(c, q), c]).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]).map(([, c]) => c).slice(0, 40);
  const list = $("#palette-list");
  clear(list);
  if (!shown.length) { list.append(el("li", { class: "empty-row" }, "No matches")); return; }
  shown.forEach((c, i) => {
    const li = el("li", { role: "option", id: `pal-${i}`, "aria-selected": i === active ? "true" : "false", "aria-disabled": c.disabled ? "true" : null },
      el("span", { class: "pal-group" }, c.group), el("span", { class: "pal-label" }, c.label), c.hint ? el("span", { class: "pal-hint" }, c.hint) : null);
    li.addEventListener("mousedown", (e) => { e.preventDefault(); run(c); });
    list.append(li);
  });
  $("#palette-input").setAttribute("aria-activedescendant", `pal-${active}`);
  list.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
}

function run(c) {
  if (!c || c.disabled) return;
  closePalette();
  c.run();
}

// ------------------------------------------------------------------ help
const GLOSSARY = [
  ["Proper motion", "The apparent motion of a star across the sky, in milliarcseconds per year (mas/yr). Measured here from positions in several visits, referenced to Gaia stars."],
  ["Parallax", "The yearly apparent shift caused by Earth's orbit. Removed before the motion fit (EPHEM-AA-LP-1); what remains is bounded, not measured."],
  ["Wavelength-matched pair", "Two exposures from the same detector and release whose wavelengths at the target agree within half a channel minus a 2 nm margin (WLMATCH-2). Only these are compared for brightness."],
  ["z", "Difference divided by its stated uncertainty: a significance, not a probability. |z| ≥ 5 is the detection threshold used here."],
  ["σ (sigma)", "One standard deviation of a measurement's stated uncertainty."],
  ["5σ sensitivity", "The smallest change this data set would detect at |z| ≥ 5. Changes below it are not excluded."],
  ["Reference-calibrated (PAIRDIFF-2)", "The target's flux ratio divided by the median ratio of constant reference stars measured in the same two exposures, which removes exposure-level calibration changes."],
  ["Calibration check (CALCHECK-1)", "How much constant reference stars scatter relative to their stated errors. Above 1.5 the errors are scaled up."],
  ["Plate solution", "The mapping from image pixels to sky positions fitted to Gaia reference stars in each exposure (PLATE-LOO-1)."],
  ["Registration", "Placing two images on a common pixel grid using their plate solutions. Geometric only; it says nothing about brightness calibration."],
  ["RUWE", "Gaia's renormalised unit weight error. Reference stars above 1.4 are excluded (REFSEL-2)."],
  ["Visit / epoch", "Exposures taken within a few days of each other. Their positions are averaged before the motion fit (LINFIT-EPOCH-1)."],
  ["Detector D1–D6", "SPHEREx's six detectors, covering 0.75–5.0 µm. Each sits behind a linear variable filter, so wavelength depends on position."],
  ["Stability check (STAB-1)", "The analysis re-run under five small parameter changes. It shows sensitivity to choices, not statistical uncertainty."],
  ["Hypothesis statuses", "Consistent, contradicted, inconclusive, not tested, evidence unavailable, incompatible: each from a stated rule over recorded values (HYPO-1)."],
  ["Content hash", "SHA-256 of an investigation record's content. An identical hash after a re-run means an identical result."],
  ["Provenance", "Where each file came from, when, and its checksum. Every result links back to it."],
  ["Synthetic data", "Generated by code to test the pipeline (SYN-… targets). Never an astronomical observation."],
  ["Static preview", "A copy of the interface with results precomputed by the Python pipeline; nothing runs on a server while you browse."],
];
const SHORTCUTS = [
  ["Ctrl+K, ⌘K or /", "Search and commands"], ["?", "This reference"], ["Alt+1 … Alt+7", "Switch workspace"],
  ["← →", "Previous / next observation (Sky Explorer)"], ["Space", "Play / pause blink (Time Machine)"],
  ["Enter", "Open the focused graph node or table row"], ["Esc", "Close a dialog or the copilot overlay"],
];

export function openHelp() {
  opener = document.activeElement;
  const body = $("#help-body");
  clear(body);
  body.append(el("h3", {}, "Keyboard"),
    el("dl", { class: "kv shortcuts" }, ...SHORTCUTS.flatMap(([k, v]) => [el("dt", {}, el("kbd", {}, k)), el("dd", {}, v)])),
    el("h3", {}, "Glossary"),
    el("dl", { class: "glossary" }, ...GLOSSARY.flatMap(([k, v]) => [el("dt", { id: "g-" + k.toLowerCase().replace(/[^a-z0-9]+/g, "-") }, k), el("dd", {}, v)])),
    el("p", { class: "faint" }, state.status?.static ? "Static preview build." : `Skytrace ${state.status?.version || ""}.`));
  $("#help").hidden = false;
  $("#help-close").focus();
}

export function closeHelp() {
  $("#help").hidden = true;
  opener?.focus?.();
}

export function glossaryTerms() { return GLOSSARY.map(([k]) => k); }

export function observationCommands(go) {
  return (state.target?.observations || []).filter((o) => o.included).slice(0, 200).map((o) => ({
    group: "Observation", label: `${shortKey(o.key)} · D${o.detector}`, hint: fmtDate(o.t_mid_iso), run: () => go(o.key) }));
}
