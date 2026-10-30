// Cosmic Atlas: where the targets are on the sky, how far apart they appear, and what is known about their distances.
// Angular separations are computed; physical distances are shown only when a parallax is recorded (and then labelled
// "inferred from parallax"); no three-dimensional relationship is derived from sky positions alone.

import { api } from "./api.js";
import { state } from "./state.js";
import { angularSeparationDeg, icrsToGalactic, parseSexagesimal } from "./frontiercore.js";
import { clear, download, el, renderToken, toast, $ } from "./util.js";

let detailCache = new Map();

async function coordsOf(t) {
  if (t.n_observations || t.kind === "synthetic" || t.verified) {
    if (!detailCache.has(t.target_id)) detailCache.set(t.target_id, await api.target(t.target_id).catch(() => null));
    const d = detailCache.get(t.target_id);
    const a = d?.target?.astrometry;
    if (a && Number.isFinite(a.ra) && Number.isFinite(a.dec)) {
      const synth = d.target.kind === "synthetic";
      return { ra: a.ra, dec: a.dec, source: synth ? "generator input (synthetic)" : (a.source || "bundle target.json"), synthetic: synth, parallax: a.parallax || null, detail: d };
    }
  }
  const h = t.hint || {};
  const ra = parseSexagesimal(h.ra, true), dec = parseSexagesimal(h.dec, false);
  if (ra !== null && dec !== null) return { ra, dec, source: `secondary source, unverified (${h.source || "hint"})`, synthetic: false, parallax: null };
  return { ra: null, dec: null, source: h.note || "no coordinates recorded", synthetic: false, parallax: null };
}

export async function renderAtlas() {
  const live = renderToken("atlas");
  const body = $("#atlas-body");
  clear(body).append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading target coordinates…"));
  const rows = [];
  for (const t of state.targets) rows.push({ t, c: await coordsOf(t) });
  if (!live()) return;
  clear(body);
  const placed = rows.filter((r) => r.c.ra !== null);
  const W = 900, H = 450, X = (ra) => W - (ra / 360) * W, Y = (dec) => H / 2 - (dec / 90) * (H / 2);
  const svg = el("svg", { class: "atlas-map", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Sky map (equatorial, RA increasing to the left): ${placed.length} of ${rows.length} targets have coordinates` });
  for (let ra = 0; ra <= 360; ra += 30) svg.append(el("line", { x1: X(ra), y1: 0, x2: X(ra), y2: H, class: "grid" }), el("text", { x: X(ra) + 2, y: H - 4, class: "axis-l" }, `${ra}°`));
  for (let dec = -60; dec <= 60; dec += 30) svg.append(el("line", { x1: 0, y1: Y(dec), x2: W, y2: Y(dec), class: dec === 0 ? "grid eq" : "grid" }), el("text", { x: 4, y: Y(dec) - 3, class: "axis-l" }, `${dec}°`));
  for (const r of placed) {
    const g = el("g", { class: `atlas-pt${r.c.synthetic ? " syn" : ""}${r.t.target_id === state.targetId ? " current" : ""}`, tabindex: "0", role: "button", "aria-label": `${r.t.name}: RA ${r.c.ra.toFixed(3)}°, Dec ${r.c.dec.toFixed(3)}° (${r.c.source})` },
      el("circle", { cx: X(r.c.ra), cy: Y(r.c.dec), r: r.t.target_id === state.targetId ? 7 : 5 }), el("text", { x: X(r.c.ra) + 8, y: Y(r.c.dec) + 4 }, r.t.name));
    const go = () => { const sel = $("#target-select"); if (sel && sel.value !== r.t.target_id) { sel.value = r.t.target_id; sel.dispatchEvent(new Event("change")); } };
    g.addEventListener("click", go); g.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    svg.append(g);
  }
  const fmt = (x, d = 3) => x === null ? "—" : x.toFixed(d);
  const table = el("table", { id: "atlas-table" }, el("thead", {}, el("tr", {}, ...["Target", "RA (°)", "Dec (°)", "Galactic l, b (°)", "Coordinate source", "Distance"].map((h) => el("th", { scope: "col" }, h)))),
    el("tbody", {}, ...rows.map((r) => {
      const gal = r.c.ra !== null ? icrsToGalactic(r.c.ra, r.c.dec) : null;
      const dist = r.c.parallax && r.c.parallax > 0 ? `${(1000 / r.c.parallax).toFixed(2)} pc — inferred from parallax ${r.c.parallax} mas` : "unknown (no parallax recorded)";
      return el("tr", { class: r.t.target_id === state.targetId ? "current" : "" }, el("th", { scope: "row" }, r.t.name), el("td", {}, fmt(r.c.ra, 4)), el("td", {}, fmt(r.c.dec, 4)),
        el("td", {}, gal ? `${gal[0].toFixed(3)}, ${gal[1].toFixed(3)}` : "—"), el("td", { class: "wrap" }, r.c.source), el("td", {}, dist));
    })));
  const sepRows = [];
  for (let i = 0; i < placed.length; i++) for (let j = i + 1; j < placed.length; j++) {
    const a = placed[i], b = placed[j];
    sepRows.push([a.t.name, b.t.name, angularSeparationDeg(a.c.ra, a.c.dec, b.c.ra, b.c.dec)]);
  }
  const exp = el("button", { class: "btn small", type: "button", id: "atlas-export" }, "Export atlas (JSON)");
  exp.addEventListener("click", async () => {
    const data = { method: "Cosmic Atlas (angular separation: Vincenty formula; galactic: ICRS rotation)", targets: rows.map((r) => ({ target_id: r.t.target_id, name: r.t.name, ra_deg: r.c.ra, dec_deg: r.c.dec,
      coordinate_source: r.c.source, parallax_mas: r.c.parallax })), separations_deg: sepRows.map(([a, b, s]) => ({ a, b, angular_separation_deg: s })),
      note: "Angular separations only; no physical separation is computed without distances." };
    if (await download("skytrace-atlas.json", JSON.stringify(data, null, 1), "application/json")) toast("Atlas exported");
  });
  body.append(el("div", { class: "card" }, el("h3", {}, "Targets on the sky"), el("div", { class: "hz-scroll" }, svg),
    el("p", { class: "muted" }, "Equatorial coordinates, plate carrée, RA increasing to the left. Synthetic targets are drawn hollow and are not real objects. Coordinates marked “secondary source, unverified” come from the target list's hints, not from a resolved catalogue query (blocked here)."),
    el("div", { class: "controls" }, exp)),
    el("div", { class: "card table-wrap" }, el("h3", {}, "Coordinates, frames and distances"), table),
    el("div", { class: "card table-wrap" }, el("h3", {}, "Angular separations"),
      el("p", { class: "muted" }, "Angle between two directions on the sky. Without distances this says nothing about how far apart the objects are in space; no projected or physical separation is computed."),
      sepRows.length ? el("table", { id: "atlas-sep" }, el("thead", {}, el("tr", {}, ...["Target", "Target", "Angular separation"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, ...sepRows.map(([a, b, s]) => el("tr", {}, el("td", {}, a), el("td", {}, b), el("td", {}, `${s.toFixed(4)}°`))))) : el("p", { class: "faint" }, "Fewer than two targets have coordinates.")),
    fieldView(rows.find((r) => r.t.target_id === state.targetId)));
}

function fieldView(r) {
  if (!r?.c.detail?.references?.stars?.length) return el("div", { class: "card" }, el("h3", {}, "Field"), el("p", { class: "muted" }, "Select a target with a stored bundle to see its field (target and Gaia reference stars)."));
  const stars = r.c.detail.references.stars, ra0 = r.c.ra, dec0 = r.c.dec, cosd = Math.cos(dec0 * Math.PI / 180);
  const pts = stars.map((s) => [(s.ra - ra0) * cosd * 3600, (s.dec - dec0) * 3600]);
  const R = Math.max(60, ...pts.map(([x, y]) => Math.max(Math.abs(x), Math.abs(y)))) * 1.1, S = 360;
  const P = ([x, y]) => [S / 2 - (x / R) * (S / 2), S / 2 - (y / R) * (S / 2)];
  const svg = el("svg", { class: "atlas-field", viewBox: `0 0 ${S} ${S}`, role: "img", "aria-label": `Field of ${r.t.name}: target and ${stars.length} reference stars within ${(R / 3600).toFixed(3)}°` });
  svg.append(el("rect", { x: 0, y: 0, width: S, height: S, class: "field-bg" }));
  for (const p of pts) { const [x, y] = P(p); svg.append(el("circle", { cx: x, cy: y, r: 3, class: "ref" })); }
  svg.append(el("circle", { cx: S / 2, cy: S / 2, r: 6, class: "tgt" }));
  return el("div", { class: "card" }, el("h3", {}, `Field of ${r.t.name}`), svg,
    el("p", { class: "muted" }, `Tangent-plane offsets (east to the left, north up) of the target and ${stars.length} reference stars from references.json; half-width ${(R / 3600).toFixed(3)}°.${r.c.synthetic ? " Synthetic field." : ""}`));
}
