// Node helper for tests/unit/test_static_preview.py: computes pairComparison for the pairs listed in a JSON file.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const [, , inputPath, modulePath] = process.argv;
const { pairComparison } = await import(pathToFileURL(modulePath).href);
const inp = JSON.parse(readFileSync(inputPath, "utf8"));
const out = inp.pairs.map(([a, b]) => pairComparison(inp.measurements, inp.params, inp.flux_pairs, a, b));
process.stdout.write(JSON.stringify(out, (k, v) => (typeof v === "number" && !Number.isFinite(v) ? null : v)));
