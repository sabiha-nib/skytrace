// Reads a JSON job file {canon: [values], numbers: [floats], schema: spec, sessions: [objects]} and prints
// the browser implementation's canonical texts, hashes, schema errors and session verification results.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
const canon = await import(pathToFileURL(root + "/web/js/canon.js").href);
const schema = await import(pathToFileURL(root + "/web/js/schema.js").href);
const core = await import(pathToFileURL(root + "/web/js/sessioncore.js").href);
const tryc = (f) => { try { return f(); } catch (e) { return "ERR"; } };
const out = {
  canon: job.canon.map((v) => tryc(() => canon.dumps(v))),
  numbers: job.numbers.map((x) => tryc(() => canon.dumps(x))),
  hashes: await Promise.all(job.canon.map(async (v) => { try { return await canon.digest(v); } catch { return "ERR"; } })),
  checks: job.checks.map(([spec, v]) => schema.check(spec, v)),
  sessions: await Promise.all(job.sessions.map((s) => core.verify(job.session_schema, s))),
};
process.stdout.write(JSON.stringify(out));
