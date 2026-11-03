// XSEARCH-1: cross-language search in labelled layers — exact text, terminology mapping (TERM-1), lexical words.
// Not semantic search. Port of src/skytrace/xsearch.py (parity-tested by tests/unit/test_i18n.py).

export const METHOD = "XSEARCH-1";
export const LABEL = "exact text, terminology mapping (TERM-1) and lexical matching — not semantic search";
const LANGS = ["en", "bn", "hi", "es", "fr", "de"];
const MIN_STEM = 5;

export function normalize(s) {
  let x = String(s || "").normalize("NFKC").toLowerCase();
  x = x.normalize("NFD").replace(/[̀-ͯ]/g, "").normalize("NFC");
  x = x.replace(/[^\p{L}\p{M}\p{N}]/gu, " ");
  return x.split(/\s+/).filter(Boolean).join(" ");
}

export function script(s) {
  const bn = /[ঀ-৿]/.test(s), hi = /[ऀ-ॿ]/.test(s), la = /[A-Za-zÀ-ɏ]/.test(s);
  const present = [["bn", bn], ["hi", hi], ["latin", la]].filter(([, v]) => v).map(([k]) => k);
  return present.length > 1 ? "mixed" : present[0] || "none";
}

export function index(terms) {
  const out = [];
  for (const t of terms?.terms || []) {
    for (const lang of LANGS) {
      const v = t[lang] || {};
      for (const [kind, form] of [["term", v.term], ...(v.synonyms || []).map((x) => ["synonym", x])]) {
        const n = normalize(form || "");
        if (n) out.push({ form: n, term: t.id, lang, kind });
      }
    }
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  out.sort((a, b) => b.form.length - a.form.length || cmp(a.form, b.form) || cmp(a.term, b.term) || cmp(a.lang, b.lang));
  return out;
}

function stemEq(a, b) {
  if (a === b) return true;
  const k = Math.min(a.length, b.length);
  return k >= MIN_STEM && a.slice(0, k) === b.slice(0, k);
}

export function expand(query, terms, idx = null) {
  idx = idx || index(terms);
  const q = normalize(query);
  const toks = q ? q.split(" ") : [];
  const used = toks.map(() => false);
  const padded = ` ${q} `;
  const matches = [], seen = new Set();
  for (const e of idx) {
    const key = `${e.term}\u0000${e.lang}\u0000${e.form}`;
    if (padded.includes(` ${e.form} `) && !seen.has(key)) {
      seen.add(key);
      matches.push({ term: e.term, lang: e.lang, form: e.form, kind: e.kind, how: "term" });
      const ft = e.form.split(" ");
      for (let i = 0; i <= toks.length - ft.length; i++) {
        if (ft.every((w, j) => toks[i + j] === w)) for (let j = i; j < i + ft.length; j++) used[j] = true;
      }
    }
  }
  toks.forEach((tk, i) => {
    if (used[i] || tk.length < MIN_STEM) return;
    for (const e of idx) {
      if (e.form.includes(" ") || !stemEq(tk, e.form)) continue;
      const key = `${e.term}\u0000${e.lang}\u0000${e.form}`;
      if (seen.has(key)) { used[i] = true; continue; }
      seen.add(key);
      matches.push({ term: e.term, lang: e.lang, form: e.form, kind: e.kind, how: "stem" });
      used[i] = true;
    }
  });
  const ids = [];
  for (const m of matches) if (!ids.includes(m.term)) ids.push(m.term);
  const byId = Object.fromEntries((terms?.terms || []).map((t) => [t.id, t]));
  return { method: METHOD, query, normalized: q, script: script(query), tokens: toks, matches, terms: ids,
    english: ids.filter((i) => byId[i]).map((i) => byId[i].en.term), residual: toks.filter((t, i) => !used[i]) };
}

function forms(term, ui) {
  const out = [normalize(term.en.term), ...(term.en.synonyms || []).map(normalize)];
  const v = term[ui];
  if (ui !== "en" && v) out.push(normalize(v.term || ""), ...(v.match || []).map(normalize));
  return out.filter(Boolean);
}

/** docs: [{id, text}] — text may include the item's interface-language label. */
export function search(query, docs, terms, ui = "en", idx = null, limit = 40) {
  const ex = expand(query, terms, idx);
  const q = ex.normalized;
  const byId = Object.fromEntries((terms?.terms || []).map((t) => [t.id, t]));
  const tf = ex.terms.filter((i) => byId[i]).map((i) => [i, forms(byId[i], ui)]);
  const res = [];
  docs.forEach((d, pos) => {
    const txt = ` ${normalize(d.text || "")} `;
    let layer = null, via = [];
    if (q && ((q.length >= 3 && txt.includes(q)) || txt.includes(` ${q} `))) { layer = 1; via = ["exact text"]; }
    const hit = tf.filter(([, fs]) => fs.some((f) => txt.includes(` ${f} `) || (f.length >= MIN_STEM && txt.includes(f)))).map(([i]) => i);
    if (layer === null && hit.length) { layer = 2; via = hit.map((i) => `terminology: ${byId[i].en.term}`); }
    if (layer === null) {
      const rest = ex.terms.length ? ex.residual : ex.tokens;
      const words = txt.trim().split(" ");
      if (rest.length && rest.every((r) => words.some((w) => stemEq(r, w) || (r.length >= 3 && w.startsWith(r))))) { layer = 3; via = ["words"]; }
    }
    if (layer !== null) res.push({ id: d.id, layer, n_terms: hit.length, via, pos });
  });
  res.sort((a, b) => a.layer - b.layer || (a.layer === 2 ? b.n_terms - a.n_terms : 0) || a.pos - b.pos);
  return { method: METHOD, label: LABEL, expansion: ex, results: res.slice(0, limit), n: res.length };
}
