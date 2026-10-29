// Recompute a Skytrace record's content hash in the browser (static preview), exactly as Python does:
//   sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)), body = record minus
//   created_at, software and content_hash.
// JSON.parse would lose the exact number spelling Python hashed ("1.0", "1e-05"), so the record *text* is
// tokenised and re-serialised with sorted keys, keeping every number and string token verbatim. This is valid
// for records written by Python's json module (the server's export and the preview's files), whose tokens are
// already in Python's canonical form. Parity with Python is tested (tests/unit/test_static_preview.py).

function parse(text) {
  let i = 0;
  const ws = () => { while (i < text.length && " \t\n\r".includes(text[i])) i++; };
  const value = () => {
    ws();
    const c = text[i];
    if (c === "{") {
      i++; const entries = []; ws();
      if (text[i] === "}") { i++; return { t: "o", entries }; }
      for (;;) {
        ws(); const kTok = str(); ws();
        if (text[i++] !== ":") throw new Error("bad JSON: expected ':'");
        entries.push([JSON.parse(kTok), kTok, value()]); ws();
        const d = text[i++];
        if (d === "}") return { t: "o", entries };
        if (d !== ",") throw new Error("bad JSON: expected ',' or '}'");
      }
    }
    if (c === "[") {
      i++; const items = []; ws();
      if (text[i] === "]") { i++; return { t: "a", items }; }
      for (;;) {
        items.push(value()); ws();
        const d = text[i++];
        if (d === "]") return { t: "a", items };
        if (d !== ",") throw new Error("bad JSON: expected ',' or ']'");
      }
    }
    if (c === '"') return { t: "s", raw: str() };
    const m = /^(?:-?(?:\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?|true|false|null|NaN|-?Infinity)/.exec(text.slice(i, i + 40));
    if (!m) throw new Error(`bad JSON at ${i}`);
    i += m[0].length;
    return { t: "v", raw: m[0] };
  };
  const str = () => {
    const s = i;
    if (text[i] !== '"') throw new Error("bad JSON: expected string");
    i++;
    while (text[i] !== '"') { if (text[i] === "\\") i++; i++; if (i >= text.length) throw new Error("bad JSON: open string"); }
    i++;
    return text.slice(s, i);
  };
  const v = value(); ws();
  if (i !== text.length) throw new Error("bad JSON: trailing data");
  return v;
}

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);   // code-unit order, as Python sorts str keys (BMP)

function emit(n) {
  if (n.t === "o") return "{" + [...n.entries].sort((a, b) => cmp(a[0], b[0])).map(([, k, v]) => k + ":" + emit(v)).join(",") + "}";
  if (n.t === "a") return "[" + n.items.map(emit).join(",") + "]";
  return n.raw;
}

async function sha256hex(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Returns {ok, stated, computed}. Throws on malformed JSON. */
export async function verifyRecordText(text) {
  const root = parse(text);
  if (root.t !== "o") throw new Error("not a JSON object");
  const stated = root.entries.find(([k]) => k === "content_hash");
  const body = { t: "o", entries: root.entries.filter(([k]) => !["created_at", "software", "content_hash"].includes(k)) };
  const computed = await sha256hex(emit(body));
  const statedHash = stated ? JSON.parse(stated[2].raw) : null;
  return { ok: computed === statedHash, stated: statedHash, computed };
}
