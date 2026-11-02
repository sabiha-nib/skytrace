// Job file written by tests/unit/test_intelligence.py::test_browser_intelligence_functions_match_python. Prints the browser
// implementations' results (web/js/intelcore.js) for the same inputs as the Python modules.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { webcrypto } from "node:crypto";
if (!globalThis.crypto) globalThis.crypto = webcrypto;
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
const f = await import(pathToFileURL(root + "/web/js/intelcore.js").href);
const ledger = job.sessions.map((s) => f.overlayLedger(job.led, s));
const repro = [];
for (const [a, b] of job.repro_cases) repro.push(await f.reproCompare(a, b));
const rv = [];
for (const m of job.repro_validate) rv.push(await f.reproValidate(m));
process.stdout.write(JSON.stringify({
  concepts: job.queries.map((q) => f.queryConcepts(q, job.mem.concepts)),
  recall: job.queries.map((q) => f.recall(job.mem, q)),
  warnings: f.failureWarnings(job.mem, job.target, job.actions),
  ledger,
  gate: ledger.map((l, i) => f.overlayGate(job.gate, l, job.sessions[i])),
  oracle: job.specs.map(([c, s]) => f.oracleEvaluate(c, s)),
  bad_specs: job.bad_specs.map((s) => f.validateOracleSpec(s)),
  visits: job.visits.map(([i, dt, pos, k]) => f.hypotheticalVisit(job.mc[i], dt, pos, k)),
  repro, repro_validate: rv,
  sess_e: f.sessionEntities(job.sess_e),
  causal: job.csess.map((s) => f.causalWarnings(s, job.models, job.causal_words)),
  pyg: [...job.pyg.map((x) => f.pyG(x)), ...job.pyg.map((x) => f.pyG(x, 4)), ...job.pyg.map((x) => f.pyG(x, 3))],
}));
