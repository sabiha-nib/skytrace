// Job file: {spec, planner_cases: [[question, facts]], missions: [...], sessions: [...], workflows: [...]}.
// Prints the browser implementations' plans, mission evaluations and workflow validations.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
const planner = await import(pathToFileURL(root + "/web/js/planner.js").href);
const missions = await import(pathToFileURL(root + "/web/js/missions.js").href);
const workflows = await import(pathToFileURL(root + "/web/js/workflows.js").href);
process.stdout.write(JSON.stringify({
  plans: job.planner_cases.map(([q, f]) => planner.plan(job.spec.planner, q, f)),
  missions: job.sessions.map((s) => missions.evaluate(job.spec.missions, s)),
  workflows: job.workflows.map((w) => workflows.validate(job.spec, w)),
}));
