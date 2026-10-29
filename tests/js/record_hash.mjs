// Node helper: prints the verification result of web/js/static/hash.js for a record file.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const [, , file, mod] = process.argv;
const { verifyRecordText } = await import(pathToFileURL(mod).href);
process.stdout.write(JSON.stringify(await verifyRecordText(readFileSync(file, "utf8"))));
