// Multilingual Research: cross-language search (XSEARCH-1), the scientific terminology base (TERM-1), explanations of every
// outcome in eight layers (EXPLAIN-1), the translation quality observatory (I18N-Q1) and reports in six languages.
// Translations are machine-made and unreviewed, and every view says so; values and recorded engine text are never translated.

import { emit, state } from "./state.js";
import { $, $$, clear, el, renderToken, toast } from "./util.js";
import { kv, table, tabs } from "./epiui.js";
import { getLang, getMeta, languages, missingSeen, t as tk } from "./i18n.js";
import { chooseLanguage } from "./settingsui.js";
import { index as xIndex, LABEL as XLABEL, search as xSearch } from "./xsearch.js";
import { getUniversal } from "./universalui.js";

const base = new URL("../i18n/", import.meta.url);
let terms = null, quality = null, idx = null, tab = "search", q = "", ctx = "all";

export async function getTerms() {
  if (!terms) { const r = await fetch(new URL("terms.json", base)); if (!r.ok) throw new Error(`terms.json: HTTP ${r.status}`); terms = await r.json(); idx = xIndex(terms); }
  return terms;
}
async function getQuality() {
  if (!quality) { const r = await fetch(new URL("quality.json", base)); if (!r.ok) throw new Error(`quality.json: HTTP ${r.status}`); quality = await r.json(); }
  return quality;
}
export function setLanguagesTab(t) { tab = t; }

/** Palette documents: the terminology base as searchable entries (used by the command palette too). */
export async function termDocs() {
  const T = await getTerms();
  return T.terms.map((x) => ({ id: `term:${x.id}`, text: ["en", "bn", "hi", "es", "fr", "de"].map((l) => [x[l]?.term, ...(x[l]?.synonyms || [])].join(" ")).join(" "), term: x }));
}
export const xsearch = async (query, docs) => xSearch(query, docs, await getTerms(), getLang(), idx);

export async function renderLanguages() {
  const live = renderToken("languages");
  const body = clear($("#languages-body"));
  const m = getMeta();
  const langs = languages();
  body.append(el("section", { class: "card", id: "lang-current" }, el("h3", {}, "Interface language"),
    el("div", { class: "set-langs", role: "radiogroup", "aria-label": "Interface language" }, ...langs.map((l) => {
      const b = el("button", { type: "button", role: "radio", class: `set-lang${l.code === getLang() ? " current" : ""}`, "aria-checked": String(l.code === getLang()), lang: l.code, translate: "no", "data-lang": l.code },
        el("span", { class: "set-native" }, l.name), el("span", { class: "faint small" }, l.english));
      b.addEventListener("click", async () => { await chooseLanguage(l.code); renderLanguages(); });
      return b;
    })),
    m.lang === "en" ? el("p", { class: "muted small" }, "English is the source language of the interface.")
      : el("p", { class: "banner warn small" }, el("strong", {}, "Machine translation. "), "This interface translation was written by an AI model and has not been reviewed by a native speaker. ",
        "Numbers, units, identifiers, method names and the text recorded by the scientific engines are not translated; they are shown exactly as computed.")),
  tabs("Multilingual research", [["search", "Cross-language search"], ["terms", "Terminology"], ["explain", "Explanations"], ["quality", "Translation quality"]], tab, "data-lang-tab", (t) => { tab = t; renderLanguages(); }));
  const out = el("div", { id: "lang-out" });
  body.append(out);
  try {
    if (tab === "search") await searchPanel(out);
    else if (tab === "terms") await termsPanel(out);
    else if (tab === "explain") await explainPanel(out, live);
    else await qualityPanel(out);
  } catch (e) { out.append(el("p", { class: "empty" }, e.message)); }
}

// ------------------------------------------------------------------ cross-language search
async function searchPanel(out) {
  const T = await getTerms();
  const docs = [...(await termDocs()), ...$$(".nav button[data-ws]").map((b) => ({ id: `ws:${b.dataset.ws}`, text: `${b.dataset.wsEn || b.textContent} ${b.textContent}`, ws: b.dataset.ws, label: b.textContent }))];
  const input = el("input", { type: "search", id: "xs-input", value: q, placeholder: "Search in any of the six languages", "aria-label": "Search in any of the six languages" });
  const res = el("div", { id: "xs-results", "aria-live": "polite" });
  const draw = () => {
    q = input.value;
    clear(res);
    if (!q.trim()) {
      const by = Object.fromEntries(T.terms.map((x) => [x.id, x]));
      const sample = [["proper-motion", "bn"], ["parallax", "hi"], ["proper-motion", "es"], ["calibration", "fr"], ["proper-motion", "de"], ["wavelength", "en"]]
        .filter(([id, l]) => by[id]?.[l]).map(([id, l]) => by[id][l].term);
      res.append(el("p", { class: "muted small" }, "Try:", " ", el("span", { translate: "no" }, sample.join(" · "))));
      return;
    }
    const r = xSearch(q, docs, T, getLang(), idx);
    const ex = r.expansion;
    res.append(el("p", { class: "small", id: "xs-method" }, el("strong", {}, "Method: "), r.label),
      kv([["Script", ex.script], ["Normalised query", ex.normalized], ["Terms recognised", ex.matches.length ? ex.matches.map((x) => `${x.form} (${x.lang}, ${x.how}) → ${T.terms.find((t) => t.id === x.term).en.term}`).join("; ") : "none"],
        ["Words matched as text", ex.residual.join(", ") || "—"]]),
      el("p", { class: "muted small", id: "xs-count" }, `${r.n} result(s)`),
      table(["Result", "Layer", "Why it matched"], r.results.map((x) => {
        const d = docs.find((y) => y.id === x.id);
        const label = d.term ? el("span", {}, el("strong", { lang: "en", translate: "no" }, d.term.en.term), " · ", el("span", { lang: getLang(), translate: "no" }, d.term[getLang()]?.term || d.term.en.term))
          : el("button", { class: "linkish", type: "button", onclick: () => emit("goto", { ws: d.ws }) }, d.label);
        return el("tr", { "data-xs": x.id }, el("td", {}, label), el("td", {}, ["", "exact text", "terminology", "words"][x.layer]), el("td", { class: "small" }, x.via.join("; ")));
      }), { id: "xs-table" }));
  };
  input.addEventListener("input", draw);
  out.append(el("section", { class: "card" }, el("h3", {}, "Cross-language search (XSEARCH-1)"),
    el("p", { class: "muted" }, "Type in Bangla, Hindi, Spanish, French, German or English. Matching is in three labelled layers: exact text, the scientific terminology base, and words. It is not semantic search: a word that is not in the terminology base is matched only as text."),
    input, res));
  draw();
  input.focus();
}

// ------------------------------------------------------------------ terminology
async function termsPanel(out) {
  const T = await getTerms();
  const L = ["en", "bn", "hi", "es", "fr", "de"], cur = getLang();
  const contexts = [...new Set(T.terms.map((x) => x.context))].sort();
  const sel = el("select", { id: "term-ctx", "aria-label": "Context" }, el("option", { value: "all" }, "all contexts"), ...contexts.map((c) => el("option", { value: c, selected: c === ctx || null }, c)));
  const holder = el("div");
  const draw = () => {
    const list = T.terms.filter((x) => ctx === "all" || x.context === ctx);
    clear(holder).append(el("div", { class: "table-wrap" }, el("table", { id: "term-table", translate: "no" },
      el("thead", {}, el("tr", {}, ...["Context", "Units", ...languages().map((l) => l.name)].map((h, i) => el("th", { scope: "col", lang: i >= 2 ? L[i - 2] : null }, h)))),
      el("tbody", {}, ...list.map((x) => el("tr", { "data-term": x.id }, el("td", { class: "small" }, x.context), el("td", { class: "mono small" }, x.units || "—"),
        ...L.map((l) => el("td", { lang: l }, el("strong", {}, x[l].term), x[l].pronunciation ? el("div", { class: "faint small", lang: "en" }, `/${x[l].pronunciation}/`) : null,
          (x[l].synonyms || []).length ? el("div", { class: "faint small" }, x[l].synonyms.join(", ")) : null))))))),
    el("h4", {}, "Definitions"), el("dl", { class: "terms-defs" }, ...list.flatMap((x) => [el("dt", { lang: cur, translate: "no" }, `${x[cur]?.term || x.en.term}`, cur !== "en" ? el("span", { class: "faint", lang: "en" }, ` · ${x.en.term}`) : null),
      el("dd", { lang: cur, translate: "no" }, x[cur]?.definition || x.en.definition)])));
  };
  sel.addEventListener("change", () => { ctx = sel.value; draw(); });
  out.append(el("section", { class: "card" }, el("h3", {}, `Scientific terminology (${T.n} terms, TERM-1)`),
    el("p", { class: "banner warn small" }, T.status, ". ", T.pronunciation, "."),
    el("p", { class: "muted small" }, "Canonical English with the term used by each interface translation, accepted synonyms, the context it belongs to and its units. Method identifiers, units and symbols are never translated."),
    el("div", { class: "controls" }, sel), holder));
  draw();
}

// ------------------------------------------------------------------ explanations (EXPLAIN-1)
const LAYER_TITLE = { observed: "1 · What was observed", measured: "2 · What was measured", method: "3 · How", compared: "4 · What was compared", result: "5 · What the result is",
  certainty: "6 · How certain", alternatives: "7 · What else could explain it", limits: "8 · What it does not mean" };
async function explainPanel(out, live) {
  if (!state.inv) { out.append(el("p", { class: "empty" }, "Run an analysis first.")); return; }
  const u = await getUniversal();
  if (!live()) return;
  const ex = u.explain;
  out.append(el("p", { class: "muted" }, "Every outcome explained in eight layers, in the interface language. The wording is translated; the values come from the record, and the statements the engines recorded are shown unchanged in English, marked as such."),
    ...ex.outcomes.map((o) => el("section", { class: "card", "data-explain": o.question }, el("h3", {}, `${o.question}: ${o.category}`),
      ...o.layers.map((L) => el("div", { class: "explain-layer", "data-layer": L.layer }, el("h4", {}, LAYER_TITLE[L.layer]), el("p", { "data-i18n-skip": "" }, tk(L.key, L.params)),
        (L.recorded || []).length ? el("ul", { class: "recorded small", lang: "en", translate: "no", title: "Recorded by the engine, in English" }, ...L.recorded.map((r) => el("li", {}, r))) : null)))),
    el("p", { class: "faint small" }, ex.note));
}

// ------------------------------------------------------------------ translation quality observatory (I18N-Q1)
function overflowCheck() {
  const sel = "button, .nav-h, th, label, .pill, .tabs [role=tab], h1, h2, h3, h4, .kv dt, select";
  const out = [];
  for (const e of $$(sel)) {
    if (!e.offsetParent) continue;
    const cs = getComputedStyle(e);
    if (cs.overflowX === "auto" || cs.overflowX === "scroll") continue;
    if (e.classList.contains("sr-only") || cs.clip !== "auto" || cs.textOverflow === "ellipsis") continue;   // visually hidden for screen readers / truncated on purpose
    if (e.scrollWidth > e.clientWidth + 1) out.push(e);
  }
  return out;
}

async function qualityPanel(out) {
  const Q = await getQuality();
  const L = Object.keys(Q.languages);
  const row = (label, f) => el("tr", {}, el("th", { scope: "row" }, label), ...L.map((l) => el("td", {}, String(f(Q.languages[l])))));
  const miss = missingSeen();
  const ov = el("div", { id: "overflow-out" });
  const chk = el("button", { class: "btn small", type: "button", id: "overflow-check" }, "Check this page for clipped text");
  chk.addEventListener("click", () => {
    const hits = overflowCheck();
    clear(ov).append(el("p", { class: hits.length ? "banner warn small" : "banner ok small", id: "overflow-result" }, hits.length ? `${hits.length} element(s) wider than their box in ${getLang()}` : `No clipped text found among the visible labels, buttons and headings (${getLang()}).`),
      hits.length ? el("ul", { class: "small" }, ...hits.slice(0, 20).map((e) => el("li", {}, `${e.tagName.toLowerCase()}: “${e.textContent.trim().slice(0, 60)}”`))) : "");
    toast("Checked");
  });
  out.append(el("section", { class: "card", id: "tq" }, el("h3", {}, "Translation quality observatory (I18N-Q1)"),
    el("p", { class: "muted" }, `Counts, not percentages. ${Q.n_messages} interface messages, ${Q.n_keyed} keyed messages and ${Q.n_terms} terms, checked for every language when the files were built.`),
    el("div", { class: "table-wrap" }, el("table", { id: "tq-table" }, el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Check"), ...L.map((l) => el("th", { scope: "col", lang: l, translate: "no" }, Q.languages[l].name)))),
      el("tbody", {},
        row("Messages translated", (v) => `${v.translated} of ${Q.n_messages}`), row("Keyed messages translated", (v) => `${v.keyed_translated} of ${Q.n_keyed}`),
        row("Placeholder mismatches", (v) => v.placeholder_mismatches.length), row("Unicode problems", (v) => v.unicode_problems.length), row("Not in NFC form", (v) => v.not_nfc.length),
        row("Numbers changed", (v) => v.numbers_changed.length), row("Identifiers changed", (v) => v.identifiers_changed.length),
        row("Terminology consistent / inconsistent", (v) => `${v.terminology.consistent} / ${v.terminology.inconsistent}`),
        row("Kept identical (words)", (v) => v.identical_words), row("Text expansion (median, max)", (v) => `${v.expansion.median_ratio} · ${v.expansion.max_ratio}`),
        row("Version", (v) => v.version), row("Status", (v) => v.status), row("Reviewed by a native speaker", (v) => (v.reviewed ? "yes" : "no"))))),
    el("p", { class: "faint small" }, "“Kept identical” lists messages left in English on purpose (names, shared words, symbols); the build report lists them for review."),
    el("h4", {}, "In this browser"),
    kv([["Interface language", getLang()], ["Catalogue messages shown without a translation so far", miss.length]]),
    miss.length ? el("ul", { class: "small", id: "tq-missing" }, ...miss.slice(0, 20).map((s) => el("li", { lang: "en" }, s))) : null,
    el("div", { class: "controls" }, chk), ov,
    el("p", { class: "faint small" }, "Visual checks of every language at desktop, tablet and phone widths are recorded with the release (docs/I18N.md).")));
}
