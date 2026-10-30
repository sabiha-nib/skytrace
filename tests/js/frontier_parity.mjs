// Job file: {horizon_cases: [[horizon, session, has_stability, server]], asl_cases: [[asl, session]],
//            review_cases: [[review, session, intent, words]], twin_cases: [[a, b, sections]], sep_cases: [[ra1, dec1, ra2, dec2]]}.
// Prints the browser implementations' results (web/js/frontiercore.js).
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const root = process.argv[2];
const job = JSON.parse(readFileSync(process.argv[3], "utf8"));
const f = await import(pathToFileURL(root + "/web/js/frontiercore.js").href);
process.stdout.write(JSON.stringify({
  horizon: job.horizon_cases.map(([h, s, st, sv]) => f.overlayHorizon(h, s, st, sv)),
  asl: job.asl_cases.map(([a, s]) => f.overlayChallenges(a, s)),
  review: job.review_cases.map(([r, s, i, w]) => f.overlayReview(r, s, i, w)),
  twins: job.twin_cases.map(([a, b, secs]) => f.twinCompare(a, b, secs)),
  sep: job.sep_cases.map(([a, b, c, d]) => f.angularSeparationDeg(a, b, c, d)),
}));
