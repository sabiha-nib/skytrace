import { pathToFileURL } from "node:url";
const { overallStatus, STATUSES } = await import(pathToFileURL(process.argv[2]).href);
const out = [];
const n = STATUSES.length;
for (let len = 1; len <= 3; len++) {
  const idx = Array(len).fill(0);
  for (;;) {
    const combo = idx.map((i) => STATUSES[i]);
    out.push([combo, overallStatus(combo)]);
    let k = len - 1;
    while (k >= 0 && ++idx[k] === n) { idx[k] = 0; k--; }
    if (k < 0) break;
  }
}
process.stdout.write(JSON.stringify(out));
