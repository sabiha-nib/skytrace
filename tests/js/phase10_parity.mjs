// Job file written by tests/unit/test_phase10.py. Prints the browser results (i18n.js translateText/t, xsearch.js, handoff.js)
// for the same inputs as the Python modules (skytrace.i18n, skytrace.xsearch, skytrace.handoff).
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { webcrypto } from "node:crypto";
if (!globalThis.crypto) globalThis.crypto = webcrypto;
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.location = { search: "", hash: "" };
globalThis.fetch = async (u) => { const p = new URL(u); const t = readFileSync(p, "utf8"); return { ok: true, json: async () => JSON.parse(t) }; };
const i18n = await import(pathToFileURL(root + "/web/js/i18n.js").href);
const xs = await import(pathToFileURL(root + "/web/js/xsearch.js").href);
const ho = await import(pathToFileURL(root + "/web/js/handoff.js").href);
const out = { translate: {}, keyed: {} };
for (const lang of job.langs) {
  await i18n.loadLanguage(lang);
  out.translate[lang] = job.texts.map((s) => i18n.translateText(s));
  out.keyed[lang] = job.keyed.map(([k, p]) => i18n.t(k, p));
}
const terms = JSON.parse(readFileSync(root + "/web/i18n/terms.json", "utf8"));
out.normalize = job.queries.map((q) => xs.normalize(q));
out.expand = job.queries.map((q) => xs.expand(q, terms));
out.search = job.queries.map((q) => xs.search(q, job.docs, terms, job.ui));
out.handoff = await ho.build(job.record, job.universal, job.hlang, job.meta, job.created_at, job.version);
out.validate = [];
for (const d of job.validate) out.validate.push(await ho.validate(d));
process.stdout.write(JSON.stringify(out));
