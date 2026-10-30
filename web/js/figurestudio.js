// Scientific figures (FIG-2) drawn from recorded values only. Each figure states its title, units, axis labels, data
// source, method, limitations and a text summary (read by screen readers), and exports as a standalone SVG carrying its
// provenance and its settings (so it can be regenerated). Figure ids are stable references used by notebook blocks.
//   timeline            observations by date and detector (COMPAT-1)
//   flux:<sequence id>  aperture flux of a compatible sequence over time (APPHOT-1, 1σ errors)
//   zhist               distribution of the significance used for each matched pair (ASSESS-2 pair_significance)
//   positions           visit-averaged positions over time (LINFIT-EPOCH-1 inputs), ξ and η
//   quality             DQ-1 item outcomes per check
//   sensitivity         STAB-1 outcomes per perturbation (when the stability check has run)

import { state } from "./state.js";
import { el, fmtDate } from "./util.js";

const DET = ["#f3d27a", "#f0a35e", "#e07a5f", "#c5609a", "#8e6bd1", "#5c83d9"];
const DQC = { valid: "#6cc6a4", invalid: "#e06a6a", incompatible: "#e48b5c", not_available: "#7d8bb0", not_checked: "#a48cf2" };

export function figureList(research) {
  const out = [{ id: "timeline", label: "Observation timeline" }, { id: "zhist", label: "Pair significance distribution" },
               { id: "positions", label: "Visit-averaged positions" }, { id: "quality", label: "Data-quality outcomes" }];
  for (const s of research?.compat?.sequences || []) out.push({ id: `flux:${s.id}`, label: `Flux over time · ${s.id} (${s.n_frames} frames, ${s.n_visits} visits)` });
  out.push({ id: "sensitivity", label: "Sensitivity (STAB-1)" });
  return out;
}

function frame(W, H, aria) { return el("svg", { class: "chart figure-svg", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": aria }); }
function axes(svg, { W, H, L, R, T, B }, xl, yl) {
  svg.append(el("line", { class: "axis-line", x1: L, x2: W - R, y1: H - B, y2: H - B }), el("line", { class: "axis-line", x1: L, x2: L, y1: T, y2: H - B }),
             el("text", { x: (L + W - R) / 2, y: H - 6, "text-anchor": "middle" }, xl),
             el("text", { x: 12, y: (T + H - B) / 2, transform: `rotate(-90 12 ${(T + H - B) / 2})`, "text-anchor": "middle" }, yl));
}
const ticks = (lo, hi, n = 5) => Array.from({ length: n }, (_, i) => lo + (i * (hi - lo)) / (n - 1));
const f2 = (x, d = 2) => (Math.abs(x) >= 1000 ? x.toFixed(0) : x.toFixed(d));

export function buildFigure(id, research, cfg = {}) {
  const W = 640, H = 340, P = { W, H, L: 70, R: 20, T: 20, B: 46 };
  const X0 = P.L, X1 = W - P.R, Y0 = H - P.B, Y1 = P.T;
  const sx = (v, lo, hi) => X0 + ((v - lo) / (hi - lo || 1)) * (X1 - X0), sy = (v, lo, hi) => Y0 - ((v - lo) / (hi - lo || 1)) * (Y0 - Y1);
  let f;
  if (id === "timeline") {
    const obs = research.compat.observations.filter((o) => o.t_mid_mjd != null);
    const t0 = Math.min(...obs.map((o) => o.t_mid_mjd)), t1 = Math.max(...obs.map((o) => o.t_mid_mjd));
    const svg = frame(W, H, `Timeline of ${obs.length} observations by detector`);
    axes(svg, P, cfg.xlabel || "MJD (days)", cfg.ylabel || "detector");
    for (let d = 1; d <= 6; d++) svg.append(el("text", { x: X0 - 8, y: sy(d, 0.5, 6.5) + 4, "text-anchor": "end" }, `D${d}`));
    for (const t of ticks(t0, t1)) svg.append(el("text", { x: sx(t, t0, t1), y: Y0 + 16, "text-anchor": "middle" }, t.toFixed(0)));
    for (const o of obs) { const c = el("circle", { cx: sx(o.t_mid_mjd, t0, t1), cy: sy(o.detector, 0.5, 6.5), r: 4 }); c.style.fill = DET[o.detector - 1]; c.append(el("title", {}, `${o.key} ${o.t_mid_iso}`)); svg.append(c); }
    f = { svg, title: "Observation timeline", units: "time: MJD; detector index", source: `${obs.length} included observations (bundle discovery index)`, method: "COMPAT-1 observation table",
          limitations: ["shows when observations exist, not what they measured"], summary: `${obs.length} observations from ${fmtDate(obs.map((o) => o.t_mid_iso).sort()[0])} to ${fmtDate(obs.map((o) => o.t_mid_iso).sort().pop())} on detectors ${[...new Set(obs.map((o) => o.detector))].join(", ")}.` };
  } else if (id.startsWith("flux:")) {
    const seq = research.compat.sequences.find((s) => s.id === id.slice(5));
    if (!seq) throw new Error("this sequence is not in the current run");
    const pts = seq.members.map((k) => ({ k, o: research.compat.observations.find((x) => x.key === k), m: state.model?.measurements[k] }))
      .filter((p) => p.m?.photometry?.status === "ok");
    if (!pts.length) throw new Error("no usable photometry in this sequence");
    const t = pts.map((p) => p.o.t_mid_mjd), y = pts.map((p) => p.m.photometry.flux_ujy), e = pts.map((p) => p.m.photometry.flux_err_ujy);
    const t0 = Math.min(...t) - 5, t1 = Math.max(...t) + 5, y0 = Math.min(...y.map((v, i) => v - 2 * e[i])), y1 = Math.max(...y.map((v, i) => v + 2 * e[i]));
    const svg = frame(W, H, `Aperture flux of ${pts.length} exposures of sequence ${seq.id}`);
    axes(svg, P, cfg.xlabel || "MJD (days)", cfg.ylabel || "aperture flux (µJy)");
    for (const v of ticks(y0, y1)) svg.append(el("text", { x: X0 - 6, y: sy(v, y0, y1) + 4, "text-anchor": "end" }, v.toFixed(0)));
    for (const v of ticks(t0, t1)) svg.append(el("text", { x: sx(v, t0, t1), y: Y0 + 16, "text-anchor": "middle" }, v.toFixed(0)));
    pts.forEach((p, i) => {
      const x = sx(t[i], t0, t1);
      svg.append(el("line", { class: "errbar", x1: x, x2: x, y1: sy(y[i] - e[i], y0, y1), y2: sy(y[i] + e[i], y0, y1) }));
      const c = el("circle", { cx: x, cy: sy(y[i], y0, y1), r: 4 }); c.style.fill = DET[seq.detector - 1]; c.append(el("title", {}, `${p.k}: ${y[i].toFixed(0)} ± ${e[i].toFixed(0)} µJy`)); svg.append(c);
    });
    f = { svg, title: `Flux over time — ${seq.id}`, units: "µJy; MJD", source: `${pts.length} exposures: ${seq.members.join(", ")}`, method: "APPHOT-1 aperture photometry; members compatible under WLMATCH-2 (SEQ-1)",
          limitations: ["error bars are 1σ as recorded, before the CALCHECK error scale", "no line is drawn between visits: nothing was observed between them", seq.note],
          summary: `${pts.length} exposures in ${seq.n_visits} visits; flux from ${Math.min(...y).toFixed(0)} to ${Math.max(...y).toFixed(0)} µJy.` };
  } else if (id === "zhist") {
    const z = research.significance.pairs.map((p) => p.z_used).filter((v) => typeof v === "number");
    if (!z.length) throw new Error("no compared pairs");
    const lo = Math.floor(Math.min(...z, -research.significance.threshold - 1)), hi = Math.ceil(Math.max(...z, research.significance.threshold + 1));
    const nb = Math.min(30, Math.max(8, hi - lo)), bw = (hi - lo) / nb, cnt = Array(nb).fill(0);
    z.forEach((v) => { cnt[Math.min(nb - 1, Math.floor((v - lo) / bw))]++; });
    const cmax = Math.max(...cnt);
    const svg = frame(W, H, `Histogram of ${z.length} pair significances`);
    axes(svg, P, cfg.xlabel || "significance z (difference ÷ uncertainty)", cfg.ylabel || "number of pairs");
    cnt.forEach((c, i) => { const x = sx(lo + i * bw, lo, hi), w = sx(lo + (i + 1) * bw, lo, hi) - x; const r = el("rect", { x: x + 0.5, y: sy(c, 0, cmax), width: Math.max(1, w - 1), height: Y0 - sy(c, 0, cmax), class: "bar" }); r.append(el("title", {}, `${c} pair(s) in [${(lo + i * bw).toFixed(1)}, ${(lo + (i + 1) * bw).toFixed(1)})`)); svg.append(r); });
    for (const th of [-research.significance.threshold, research.significance.threshold]) svg.append(el("line", { class: "thresh", x1: sx(th, lo, hi), x2: sx(th, lo, hi), y1: Y1, y2: Y0 }));
    for (const v of ticks(lo, hi)) svg.append(el("text", { x: sx(v, lo, hi), y: Y0 + 16, "text-anchor": "middle" }, v.toFixed(0)));
    for (const v of ticks(0, cmax, 3)) svg.append(el("text", { x: X0 - 6, y: sy(v, 0, cmax) + 4, "text-anchor": "end" }, v.toFixed(0)));
    const n5 = z.filter((v) => Math.abs(v) >= research.significance.threshold).length;
    f = { svg, title: "Distribution of pair significances", units: "dimensionless (z); count", source: `${z.length} wavelength-matched pairs of this run`, method: research.significance.method,
          limitations: ["z is a significance under the stated errors, not a probability", "pairs share exposures, so they are not independent", `dashed lines: the ±${research.significance.threshold} detection threshold`],
          summary: `${z.length} pairs; ${n5} at or beyond |z| = ${research.significance.threshold}.` };
  } else if (id === "positions") {
    const ep = state.model?.astrometry?.epochs || state.model?.byStep?.astrometry?.[0]?.data?.epochs;
    if (!ep?.length) throw new Error("no visit-averaged positions in this run");
    const t = ep.map((e) => e.t_mjd);
    const vals = ep.flatMap((e) => [e.xi_mas - e.sig_xi_mas, e.xi_mas + e.sig_xi_mas, e.eta_mas - e.sig_eta_mas, e.eta_mas + e.sig_eta_mas]);
    const t0 = Math.min(...t) - 10, t1 = Math.max(...t) + 10, y0 = Math.min(...vals), y1 = Math.max(...vals);
    const svg = frame(W, H, `Visit-averaged positions of ${ep.length} visits`);
    axes(svg, P, cfg.xlabel || "MJD (days)", cfg.ylabel || "offset from the catalogue position (mas)");
    for (const v of ticks(y0, y1)) svg.append(el("text", { x: X0 - 6, y: sy(v, y0, y1) + 4, "text-anchor": "end" }, f2(v, 0)));
    for (const v of ticks(t0, t1)) svg.append(el("text", { x: sx(v, t0, t1), y: Y0 + 16, "text-anchor": "middle" }, v.toFixed(0)));
    ep.forEach((e, i) => {
      [["xi_mas", "sig_xi_mas", "#5fd0e4", -3, "circle"], ["eta_mas", "sig_eta_mas", "#a48cf2", 3, "rect"]].forEach(([k, s, col, dx, shape]) => {
        const x = sx(t[i], t0, t1) + dx;
        svg.append(el("line", { class: "errbar", x1: x, x2: x, y1: sy(e[k] - e[s], y0, y1), y2: sy(e[k] + e[s], y0, y1) }));
        const m = shape === "circle" ? el("circle", { cx: x, cy: sy(e[k], y0, y1), r: 4 }) : el("rect", { x: x - 3.5, y: sy(e[k], y0, y1) - 3.5, width: 7, height: 7 });
        m.style.fill = col; m.append(el("title", {}, `${k === "xi_mas" ? "ξ" : "η"} ${e[k].toFixed(0)} ± ${e[s].toFixed(0)} mas`)); svg.append(m);
      });
    });
    svg.append(el("text", { x: X1 - 120, y: Y1 + 12 }, "● ξ (east)   ■ η (north)"));
    f = { svg, title: "Visit-averaged positions", units: "mas; MJD", source: `${ep.length} visits (astrometry step of this run)`, method: "LINFIT-EPOCH-1 inputs: Gaia-referenced positions averaged per visit (EPHEM-AA-LP-1 applied)",
          limitations: ["offsets are relative to the propagated catalogue position", "empirical scatter used where larger than the formal error"],
          summary: `${ep.length} visits; ξ and η offsets with 1σ errors.` };
  } else if (id === "quality") {
    const q = research.quality, rows = q.checks;
    const H2 = 40 + rows.length * 22, svg = frame(W, H2, `Item outcomes for ${rows.length} data-quality checks`);
    rows.forEach((c, i) => {
      const y = 20 + i * 22, tot = Object.values(c.counts).reduce((a, b) => a + b, 0);
      svg.append(el("text", { x: 150, y: y + 12, "text-anchor": "end" }, c.id));
      let x = 160;
      for (const o of q.outcomes) {
        const n = c.counts[o] || 0;
        if (!n) continue;
        const w = (n / tot) * (W - 180);
        const r = el("rect", { x, y, width: Math.max(1, w), height: 15 }); r.style.fill = DQC[o]; r.append(el("title", {}, `${c.id}: ${n} item(s) ${o.replace("_", " ")}`)); svg.append(r);
        x += w;
      }
    });
    f = { svg, title: "Data-quality item outcomes", units: "fraction of each check's items", source: `${rows.length} DQ-1 checks of this run`, method: "DQ-1",
          limitations: ["bars show item shares within each check; checks are not comparable to each other and are not combined into a score"],
          summary: rows.map((c) => `${c.id}: ${c.outcome.replace("_", " ")}`).join("; ") + "." };
  } else if (id === "sensitivity") {
    const st = state.stability?.target === state.targetId ? state.stability.result : null;
    if (!st) throw new Error("the stability check has not been run for this target");
    const runs = [st.base, ...st.runs].map((r, i) => ({ label: i ? r.label : "baseline", pm: r.pm_measured_mas_yr, s: r.pm_sigma_mas_yr }));
    const ok = runs.filter((r) => typeof r.pm === "number");
    if (!ok.length) throw new Error("no motion measured in the stability runs");
    const vals = ok.flatMap((r) => [r.pm - (r.s || 0), r.pm + (r.s || 0)]), y0 = Math.min(0, ...vals), y1 = Math.max(...vals);
    const svg = frame(W, H, `Measured proper motion under ${runs.length} parameter settings`);
    axes(svg, P, cfg.xlabel || "analysis setting", cfg.ylabel || "measured proper motion (mas/yr)");
    for (const v of ticks(y0, y1)) svg.append(el("text", { x: X0 - 6, y: sy(v, y0, y1) + 4, "text-anchor": "end" }, v.toFixed(0)));
    ok.forEach((r, i) => {
      const x = X0 + ((i + 0.5) / ok.length) * (X1 - X0);
      svg.append(el("line", { class: "errbar", x1: x, x2: x, y1: sy(r.pm - (r.s || 0), y0, y1), y2: sy(r.pm + (r.s || 0), y0, y1) }));
      const c = el("circle", { cx: x, cy: sy(r.pm, y0, y1), r: 4 }); c.style.fill = "#5fd0e4"; svg.append(c);
      svg.append(el("text", { x, y: Y0 + 14, "text-anchor": "middle", class: "small" }, r.label.slice(0, 16)));
    });
    f = { svg, title: "Sensitivity of the measured motion (STAB-1)", units: "mas/yr", source: `${ok.length} runs: baseline and the fixed perturbations`, method: "STAB-1",
          limitations: ["parameter sensitivity, not statistical uncertainty", "error bars are each run's own 1σ"],
          summary: `measured proper motion from ${Math.min(...ok.map((r) => r.pm)).toFixed(0)} to ${Math.max(...ok.map((r) => r.pm)).toFixed(0)} mas/yr across ${ok.length} runs.` };
  } else throw new Error(`unknown figure ${id}`);
  if (cfg.title) f.title = cfg.title;
  if (cfg.annotation) f.svg.append(el("text", { x: X0 + 8, y: Y1 + 14, class: "annotation" }, cfg.annotation.slice(0, 120)));
  f.id = id; f.settings = { id, ...cfg };
  f.svg.setAttribute("aria-label", `${f.title}. ${f.summary}`);
  return f;
}

/** A figure card: the chart, its provenance lines and an accessible summary. */
export function figureCard(f, extra = null) {
  return el("figure", { class: "fig-card" }, el("h4", {}, f.title), f.svg,
    el("figcaption", {}, el("p", {}, f.summary), el("dl", { class: "kv compact" }, el("dt", {}, "Units"), el("dd", {}, f.units), el("dt", {}, "Data"), el("dd", { class: "wrap" }, f.source),
      el("dt", {}, "Method"), el("dd", {}, f.method), el("dt", {}, "Limitations"), el("dd", {}, f.limitations.join("; ")))), extra);
}
