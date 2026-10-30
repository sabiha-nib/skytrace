import { writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const { zipStore } = await import(pathToFileURL(process.argv[2] + "/web/js/zipstore.js").href);
const files = [["pkg/a.txt", "hello µ 😀\n"], ["pkg/b.bin", new Uint8Array([0, 1, 2, 255, 254])], ["pkg/empty.txt", ""]];
writeFileSync(process.argv[3], zipStore(files));
writeFileSync(process.argv[4], zipStore(files));
