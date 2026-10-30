// SCHEMA-1 interpreter (see src/skytrace/schema.py). The schema documents come from the server (/api/schemas) or the
// static preview (data/schemas.json); this file only interprets them, with the same messages and order as Python.

import { CanonError, dumps } from "./canon.js";

function depth(v, d = 0) {
  if (v && typeof v === "object") {
    const xs = Array.isArray(v) ? v : Object.values(v);
    return xs.length ? Math.max(...xs.map((x) => depth(x, d + 1))) : d + 1;
  }
  return d;
}
const repr = (v) => (typeof v === "string" ? `'${v}'` : JSON.stringify(v));
const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export function check(spec, v, path = "$") {
  const t = spec.t;
  if (t === "any") return spec.of.some((s) => !check(s, v, path).length) ? [] : [`${path}: matches none of the allowed forms`];
  if (t === "const") return v === spec.v ? [] : [`${path}: must be ${repr(spec.v)}`];
  if (t === "null") return v === null ? [] : [`${path}: must be null`];
  if (t === "bool") return typeof v === "boolean" ? [] : [`${path}: must be true or false`];
  if (t === "num" || t === "int") {
    if (!isNum(v)) return [`${path}: must be a finite number`];
    if (t === "int" && !Number.isInteger(v)) return [`${path}: must be an integer`];
    if ("min" in spec && v < spec.min) return [`${path}: must be ≥ ${spec.min}`];
    if ("max" in spec && v > spec.max) return [`${path}: must be ≤ ${spec.max}`];
    return [];
  }
  if (t === "str") {
    if (typeof v !== "string") return [`${path}: must be text`];
    if (v.length < (spec.min || 0)) return [`${path}: must have at least ${spec.min || 0} characters`];
    if ("max" in spec && v.length > spec.max) return [`${path}: must have at most ${spec.max} characters`];
    if (spec.enum && !spec.enum.includes(v)) return [`${path}: must be one of ${spec.enum.join(", ")}`];
    if (spec.re && !new RegExp(spec.re).test(v)) return [`${path}: has an invalid format`];
    return [];
  }
  if (t === "arr") {
    if (!Array.isArray(v)) return [`${path}: must be a list`];
    if ("max" in spec && v.length > spec.max) return [`${path}: must have at most ${spec.max} items`];
    return v.flatMap((x, i) => check(spec.items, x, `${path}[${i}]`));
  }
  const isObj = v !== null && typeof v === "object" && !Array.isArray(v);
  if (t === "map") {
    if (!isObj) return [`${path}: must be an object`];
    const keys = Object.keys(v).sort();
    if ("max" in spec && keys.length > spec.max) return [`${path}: must have at most ${spec.max} entries`];
    return keys.flatMap((k) => (new RegExp(spec.keys).test(k) ? check(spec.values, v[k], `${path}.${k}`) : [`${path}: key ${repr(k)} has an invalid format`]));
  }
  if (t === "obj") {
    if (!isObj) return [`${path}: must be an object`];
    const out = [];
    for (const k of Object.keys(v).sort()) if (!(k in spec.f) && !spec.extra) out.push(`${path}: unknown field ${repr(k)}`);
    for (const k of Object.keys(spec.f).sort()) {
      const [s, req] = spec.f[k];
      if (k in v) out.push(...check(s, v[k], `${path}.${k}`));
      else if (req) out.push(`${path}: missing field ${repr(k)}`);
    }
    return out;
  }
  if (t === "json") {
    let text;
    try { text = dumps(v); } catch (e) { if (e instanceof CanonError) return [`${path}: ${e.message}`]; throw e; }
    const max = spec.max_bytes ?? 20000, dmax = spec.depth ?? 6;
    if (new TextEncoder().encode(text).length > max) return [`${path}: larger than ${max} bytes`];
    if (depth(v) > dmax) return [`${path}: nested deeper than ${dmax} levels`];
    return [];
  }
  throw new Error(`unknown schema type ${t}`);
}
