// Prints the static preview's intent for each question given as JSON on argv[3] (backend.js path on argv[2]).
import { pathToFileURL } from "node:url";
globalThis.document ??= { querySelector: () => null, baseURI: "file:///" };
globalThis.location ??= { href: "file:///" };
const { intentOf } = await import(pathToFileURL(process.argv[2]).href);
process.stdout.write(JSON.stringify(JSON.parse(process.argv[3]).map((q) => intentOf(q))));
