// Minimal SVG scatter/line charts with error bars. Every mark is drawn from a data value.

import { el, fmt } from "./util.js";

function ticks(lo, hi, n = 5) {
  const span = hi - lo || 1;
  const step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const err = (span / n) / step;
  const s = step * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const out = [];
  for (let v = Math.ceil(lo / s) * s; v <= hi + 1e-9; v += s) out.push(+v.toPrecision(12));
  return out;
}

export function scatter({ width = 640, height = 260, xLabel = "", yLabel = "", series = [], hlines = [], xfmt = (v) => fmt(v, 2), yfmt = (v) => fmt(v, 0), title = "" }) {
  const m = { l: 62, r: 14, t: 12, b: 38 };
  const pts = series.flatMap((s) => s.points || []);
  const lines = series.flatMap((s) => s.line || []);
  const xs = [...pts.map((p) => p.x), ...lines.map((p) => p[0])];
  const ys = [...pts.flatMap((p) => [p.y - (p.ey || 0), p.y + (p.ey || 0)]), ...lines.map((p) => p[1]), ...hlines.map((h) => h.y)].filter(Number.isFinite);
  const svg = el("svg", { class: "chart", viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": title || `${yLabel} versus ${xLabel}` });
  if (!xs.length || !ys.length) { svg.append(el("text", { x: width / 2, y: height / 2, "text-anchor": "middle" }, "No data to plot")); return svg; }
  let [x0, x1] = [Math.min(...xs), Math.max(...xs)], [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const px = (x1 - x0) * 0.06 || 1, py = (y1 - y0) * 0.08 || 1;
  x0 -= px; x1 += px; y0 -= py; y1 += py;
  const X = (v) => m.l + (v - x0) / (x1 - x0) * (width - m.l - m.r);
  const Y = (v) => height - m.b - (v - y0) / (y1 - y0) * (height - m.t - m.b);
  const g = el("g", { class: "grid" });
  for (const t of ticks(y0, y1)) g.append(el("line", { x1: m.l, x2: width - m.r, y1: Y(t), y2: Y(t) }), el("text", { x: m.l - 6, y: Y(t) + 4, "text-anchor": "end" }, yfmt(t)));
  for (const t of ticks(x0, x1)) g.append(el("text", { x: X(t), y: height - m.b + 15, "text-anchor": "middle" }, xfmt(t)));
  svg.append(g, el("line", { class: "axis-line", x1: m.l, x2: width - m.r, y1: height - m.b, y2: height - m.b }),
    el("text", { x: (m.l + width - m.r) / 2, y: height - 6, "text-anchor": "middle" }, xLabel),
    el("text", { x: 14, y: (m.t + height - m.b) / 2, "text-anchor": "middle", transform: `rotate(-90 14 ${(m.t + height - m.b) / 2})` }, yLabel));
  for (const h of hlines) svg.append(el("line", { class: h.class || "thresh", x1: m.l, x2: width - m.r, y1: Y(h.y), y2: Y(h.y) }),
    h.label ? el("text", { x: width - m.r - 4, y: Y(h.y) - 4, "text-anchor": "end" }, h.label) : null);
  for (const s of series) {
    if (s.line && s.line.length > 1) svg.append(el("polyline", { class: s.lineClass || "cat-line", points: s.line.map((p) => `${X(p[0])},${Y(p[1])}`).join(" ") }));
    for (const p of s.points || []) {
      const col = p.color || s.color || "#dde5f3";
      const gg = el("g", { class: "pt", tabindex: p.onClick ? "0" : null });
      if (p.ey) { const l = el("line", { x1: X(p.x), x2: X(p.x), y1: Y(p.y - p.ey), y2: Y(p.y + p.ey) }); l.style.stroke = col; l.style.strokeOpacity = ".7"; gg.append(l); }
      const c = el("circle", { cx: X(p.x), cy: Y(p.y), r: p.r || 3.4 });
      c.style.fill = p.hollow ? "none" : col; c.style.stroke = col; c.style.strokeWidth = "1.4";
      gg.append(c, el("title", {}, p.title || `${xfmt(p.x)}, ${yfmt(p.y)}`));
      if (p.onClick) { gg.addEventListener("click", p.onClick); gg.addEventListener("keydown", (e) => { if (e.key === "Enter") p.onClick(); }); }
      svg.append(gg);
    }
  }
  return svg;
}
