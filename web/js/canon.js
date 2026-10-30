// SKY-CANON-1 (see src/skytrace/canon.py): canonical JSON text shared by Python and the browser, so a research
// session hashes identically whichever side wrote it. Sorted ASCII keys, no whitespace, JSON.stringify string escapes,
// ECMAScript number spelling, integers within ±2^53, no NaN/Infinity, no lone surrogates. Parity-tested.

export const METHOD = "SKY-CANON-1";
const ASCII_KEY = /^[\x20-\x7e]{1,64}$/;
const LONE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

export class CanonError extends Error {}

function num(x) {
  if (!Number.isFinite(x)) throw new CanonError("NaN and infinities are not allowed");
  if (Number.isInteger(x) && Math.abs(x) > 2 ** 53) throw new CanonError(`integer ${x} is outside ±2^53`);
  return Object.is(x, -0) ? "0" : String(x);
}

function str(s) {
  if (LONE.test(s)) throw new CanonError("lone surrogate in string");
  return JSON.stringify(s);
}

export function dumps(v) {
  if (v === null) return "null";
  if (v === true) return "true";
  if (v === false) return "false";
  if (typeof v === "number") return num(v);
  if (typeof v === "string") return str(v);
  if (Array.isArray(v)) return "[" + v.map(dumps).join(",") + "]";
  if (typeof v === "object") {
    const keys = Object.keys(v);
    for (const k of keys) if (!ASCII_KEY.test(k)) throw new CanonError(`object key '${k}' is not 1–64 printable ASCII characters`);
    return "{" + keys.sort().map((k) => str(k) + ":" + dumps(v[k])).join(",") + "}";
  }
  throw new CanonError(`type ${typeof v} cannot be serialised`);
}

export async function digest(v) {
  const bytes = new TextEncoder().encode(dumps(v));
  const h = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(h), (b) => b.toString(16).padStart(2, "0")).join("");
}
