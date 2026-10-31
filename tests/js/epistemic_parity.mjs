// Job file: {trace_cases: [[graph, id, dir]], word_cases: [[text, words]], diff_cases: [[a, b]], blind_cases: [[base, session, words]],
//            sigma_cases: [[times, sigmas]], precision_cases: [[f, flux, scale]], integrity_cases: [[text, facts]], integrity_spec,
//            chain_cases: [history]}. Prints the browser implementations' results (web/js/epistemiccore.js, web/js/sessioncore.js).
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { webcrypto } from "node:crypto";
if (!globalThis.crypto) globalThis.crypto = webcrypto;
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
const f = await import(pathToFileURL(root + "/web/js/epistemiccore.js").href);
const sc = await import(pathToFileURL(root + "/web/js/sessioncore.js").href);
const chains = [];
for (const h of job.chain_cases) {
  const filled = await sc.chainFill(h);
  chains.push({ filled: filled.map((e) => e.h), verify: await sc.verifyChain(h) });
}
process.stdout.write(JSON.stringify({
  trace: job.trace_cases.map(([g, id, d]) => f.trace(g, id, d)),
  words: job.word_cases.map(([t, w]) => f.assertedWords(t, w)),
  diff: job.diff_cases.map(([a, b]) => f.diff(a, b)),
  blind: job.blind_cases.map(([b, s, w]) => f.overlayBlindspots(b, s, w)),
  sigma: job.sigma_cases.map(([t, s]) => f.sigmaPm(t, s)),
  precision: job.precision_cases.map(([a, b, c]) => f.pairPrecision(a, b, c)),
  integrity: job.integrity_cases.map(([t, facts]) => f.integrityCheck(t, facts, job.integrity_spec)),
  chains,
}));
