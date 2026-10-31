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
  ["Research session", "Everything you do in one line of work — question, runs, notes, plans, experiments, missions — validated and hashed (SESSION-1). Export it to keep it; a branch is an independent copy."],
  ["Investigation plan (PLAN-1)", "Registered actions chosen by fixed rules for your question. Steps marked ‘confirm’ wait for you; ‘needs review’ steps wait for your written judgement."],
  ["Sequence (SEQ-1)", "Observations on one detector in which every pair is wavelength-matched. Playback shows only recorded frames; nothing is interpolated."],
  ["Data-quality outcomes (DQ-1)", "Each check reports invalid, incompatible, not available, not checked or valid under its stated rule. There is no overall score."],
  ["Evidence ledger (LEDGER-1)", "What each claim rests on, counted by kind, with contradictions found by four fixed rules. One linked item is never full support."],
  ["Research opportunity", "A Discovery Radar item: something worth examining, with why, the evidence, the data needed, and what it cannot establish. Not a detection."],
  ["Negative control", "The same analysis on a fixture where the effect is absent by construction; detecting it there would show a method problem."],
  ["Static preview", "A copy of the interface with results precomputed by the Python pipeline; nothing runs on a server while you browse."],
  ["Epistemic status", "How a statement was produced — directly recorded, measured, derived, model-dependent, assumed, hypothesized, simulated, user-authored, unsupported or unknown. Assigned by stated rules from the origin and method (EPI-1), never from wording; it is not a measure of truth."],
  ["Reasoning graph", "The investigation as connected objects: files, observations, measurements, derived quantities, inferences and claims, with the methods, assumptions and uncertainty that produced them (EPI-1). Trace a claim back or a file forward."],
  ["Scientific compilation", "Ten stages of structural and methodological checks on an investigation (SCICOMP-1). Passing means the investigation met these checks, not that its conclusions are true."],
  ["Knowledge boundary", "Where each claim stands: established by the recorded evidence, supported under stated assumptions, unresolved, or outside the evidence (KBOUND-1). Categories with rules, not confidence levels."],
  ["Negative knowledge", "What was attempted and could not be established — failed, refused, inconclusive or impossible work, kept on record with what would unblock it (NEG-1)."],
  ["Blind analysis", "Working with outcomes hidden until a documented unblinding, so analysis choices are fixed before results are seen (BLINDLAB-1). A workflow aid, not access control."],
  ["Locked protocol", "A research plan stored with a content hash and time; later changes are appended as amendments with reasons. Labelled when results were already visible. Not a formal preregistration."],
  ["Lineage", "The recorded path from an original file to a result: import, validation, transformations, measurement, analysis, assessment, claim, report (LINEAGE-1). Missing stages are shown as missing."],
  ["Reproduction verdict", "Exact (identical hash), numerically equivalent (within 1e-9 relative), with documented differences, failed, or blocked (REPROX-1). Importing a record is never a reproduction."],
  ["Evidence vault", "The session's append-only history with a hash chain linking every event, so an edited or removed event is detectable (VAULT-1). Not a signature."],
];
const SHORTCUTS = [
  ["Ctrl+K, ⌘K or /", "Search and commands"], ["?", "This reference"], ["Alt+1 … Alt+9", "Switch between the visible workspaces"],
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
export function glossaryEntries() { return GLOSSARY.map(([k, v]) => ({ term: k, text: v })); }

export function observationCommands(go) {
  return (state.target?.observations || []).filter((o) => o.included).slice(0, 200).map((o) => ({
    group: "Observation", label: `${shortKey(o.key)} · D${o.detector}`, hint: fmtDate(o.t_mid_iso), run: () => go(o.key) }));
}
