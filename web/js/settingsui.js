// Settings: interface language, numerals and level of detail. The language is kept in this browser (so it survives page
// navigation and restarts), written into the open research session's preferences, and recorded in exported reports.
// Changing language never changes a number, an identifier or a scientific result.

import { $, clear, el } from "./util.js";
import { state } from "./state.js";
import * as S from "./session.js";
import { getDigits, getLang, getMeta, languages, onLangChange, setDigits, setLang } from "./i18n.js";

let opener = null, levelSetter = null;
export function setLevelHook(fn) { levelSetter = fn; }

const LEVELS = [["explore", "Explorer", "Plain-language view: outcomes, images and comparisons"],
                ["investigate", "Researcher", "Adds evidence, criteria, measurements, hypotheses and parameters"],
                ["research", "Advanced", "Adds identifiers, hashes, raw values, methods and diagnostics"]];

export async function chooseLanguage(code) {
  await setLang(code);
  const sel = $("#lang-select");
  if (sel) sel.value = code;
  if (state.session) {
    const prefs = state.session.preferences || {};
    if (prefs.language !== code) await S.update("preferences.language", `Interface language: ${code}`, (s) => { s.preferences = { ...(s.preferences || {}), language: code, digits: getDigits() }; return s; });
  }
}

function statusLine() {
  const m = getMeta();
  if (m.lang === "en") return el("p", { class: "muted small" }, "English is the source language of the interface.");
  return el("p", { class: "banner warn small", id: "set-mt" }, el("strong", {}, "Machine translation. "),
    "This interface translation was written by an AI model and has not been reviewed by a native speaker. ",
    "Numbers, units, identifiers, method names and the text recorded by the scientific engines are not translated; they are shown exactly as computed.");
}

export function renderSettings() {
  const body = $("#settings-body");
  // re-rendering replaces the controls: keep keyboard focus on the control that was in use (by id or data attribute)
  const a = document.activeElement;
  const keep = a && body.contains(a) ? (a.id ? `#${a.id}` : a.dataset.lang ? `[data-lang="${a.dataset.lang}"]` : a.dataset.setLevel ? `[data-set-level="${a.dataset.setLevel}"]` : null) : null;
  queueMicrotask(() => { if (keep) body.querySelector(keep)?.focus(); });
  clear(body);
  const cur = getLang();
  const langs = el("div", { class: "set-langs", role: "radiogroup", "aria-labelledby": "set-lang-h" }, ...languages().map((l) => {
    const b = el("button", { type: "button", role: "radio", class: `set-lang${l.code === cur ? " current" : ""}`, "aria-checked": String(l.code === cur),
      "data-lang": l.code, lang: l.code, translate: "no" }, el("span", { class: "set-native" }, l.name), el("span", { class: "faint small" }, l.english));
    b.addEventListener("click", async () => { await chooseLanguage(l.code); renderSettings(); });
    return b;
  }));
  const dig = el("select", { id: "set-digits" }, el("option", { value: "locale" }, "The language's own digits"), el("option", { value: "latn" }, "Western digits (0–9)"));
  dig.value = getDigits();
  dig.addEventListener("change", async () => { await setDigits(dig.value); renderSettings(); });
  const lv = el("div", { class: "segmented", role: "group", "aria-label": "Interface level" }, ...LEVELS.map(([id, name, why]) => {
    const b = el("button", { type: "button", "data-set-level": id, title: why, "aria-pressed": String(state.level === id) }, name);
    b.addEventListener("click", () => { levelSetter?.(id); renderSettings(); });
    return b;
  }));
  body.append(
    el("h3", { id: "set-lang-h" }, "Interface language"), langs, statusLine(),
    el("label", { for: "set-digits" }, "Numerals"), dig,
    el("p", { class: "faint small" }, "Decimal and grouping separators always follow the language; values and their precision are unchanged."),
    el("h3", {}, "Interface level"), lv,
    el("p", { class: "faint small" }, "Explorer, Researcher and Advanced show the same investigation with more or less detail. Switching never changes a result or loses your work."),
    el("h3", {}, "Where the language is kept"),
    el("ul", { class: "small" }, el("li", {}, "in this browser, so it survives navigation and restarts;"),
      el("li", {}, "in the open research session's preferences, so a session exported or reopened elsewhere carries it;"),
      el("li", {}, "in every report you generate, as language and translation metadata.")));
}

export function openSettings() {
  opener = document.activeElement;
  renderSettings();
  $("#settings").hidden = false;
  $("#settings-close").focus();
}
export function closeSettings() { $("#settings").hidden = true; opener?.focus?.(); }

export function bindSettings() {
  $("#settings-btn").addEventListener("click", openSettings);
  $("#settings-close").addEventListener("click", closeSettings);
  $("#settings").addEventListener("click", (e) => { if (e.target.id === "settings") closeSettings(); });
  $("#settings").addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); closeSettings(); } });
  const sel = $("#lang-select");
  sel.value = getLang();
  sel.addEventListener("change", () => chooseLanguage(sel.value));
  onLangChange((code) => { sel.value = code; });
}
