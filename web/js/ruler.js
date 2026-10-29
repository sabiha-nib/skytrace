// The wavelength ruler: every observation of the target placed by wavelength (x) and date (y).
// Wavelength-matched pairs appear as vertical links: the only pairs whose brightness may be compared.

import { DET_BANDS, DET_COLORS, clear, el, fmt, fmtDate } from "./util.js";
import { state, emit } from "./state.js";

const LMIN = 0.70, LMAX = 5.05;

export function renderRuler() {
  const svg = document.getElementById("ruler-svg");
  clear(svg);
  const W = svg.clientWidth || 900, H = svg.clientHeight || 118;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const padL = 60, padR = 12, top = 26, bottom = 20;
  // log-ish wavelength axis gives the short-wavelength detectors room
  const xs = (l) => padL + (Math.log(l) - Math.log(LMIN)) / (Math.log(LMAX) - Math.log(LMIN)) * (W - padL - padR);
  for (const [d, [lo, hi]] of Object.entries(DET_BANDS)) {
    const r = el("rect", { x: xs(lo), y: top - 12, width: xs(hi) - xs(lo), height: 5, rx: 1.5 });
    r.style.fill = DET_COLORS[d];
    svg.append(r, el("text", { class: "band-label", x: (xs(lo) + xs(hi)) / 2, y: top - 15, "text-anchor": "middle" }, `D${d}`));
  }
  const axis = el("g", { class: "axis" });
  axis.append(el("line", { x1: padL, x2: W - padR, y1: H - bottom, y2: H - bottom }));
  for (const l of [0.75, 1, 1.5, 2, 3, 4, 5]) {
    axis.append(el("line", { x1: xs(l), x2: xs(l), y1: H - bottom, y2: H - bottom + 4 }),
                el("text", { x: xs(l), y: H - 5, "text-anchor": "middle" }, l === 5 ? "5 µm" : String(l)));
  }
  svg.append(axis);

  const m = state.model;
  const obs = state.target ? state.target.observations.filter((o) => o.included) : [];
  if (!obs.length) {
    svg.append(el("text", { class: "empty", x: padL + 8, y: (top + H - bottom) / 2 + 4 },
      state.targetId ? "No observations stored for this target yet." : "Choose a target."));
    return;
  }
  const times = obs.map((o) => o.t_mid_mjd).filter(Number.isFinite);
  const t0 = Math.min(...times), t1 = Math.max(...times);
  const ys = (t) => top + 4 + (t1 > t0 ? (t - t0) / (t1 - t0) : 0.5) * (H - bottom - top - 10);
  axis.append(el("text", { x: padL - 6, y: ys(t0) + 3, "text-anchor": "end" }, fmtDate(obs[0].t_mid_iso).slice(0, 7)),
              el("text", { x: padL - 6, y: ys(t1) + 3, "text-anchor": "end" }, fmtDate(obs[obs.length - 1].t_mid_iso).slice(0, 7)));

  const pos = (o) => {
    const mm = m?.measurements[o.key];
    const lam = mm?.wavelength_um ?? (o.em_min_um != null ? (o.em_min_um + o.em_max_um) / 2 : null);
    return lam == null ? null : [xs(lam), ys(o.t_mid_mjd), lam, !!mm?.wavelength_um];
  };
  if (m) {
    const strong = new Set();
    for (const f of m.flux) if (Math.abs(f.z) >= 5) strong.add(f.a + "|" + f.b);
    for (const p of m.accepted) {
      const oa = obs.find((o) => o.key === p.a), ob = obs.find((o) => o.key === p.b);
      const pa = oa && pos(oa), pb = ob && pos(ob);
      if (pa && pb) svg.append(el("line", { class: "pair-link" + (strong.has(p.a + "|" + p.b) ? " strong" : ""), x1: pa[0], y1: pa[1], x2: pb[0], y2: pb[1] }));
    }
  }
  const partners = new Set(m && state.selectedKey ? m.accepted.filter((p) => p.a === state.selectedKey || p.b === state.selectedKey)
    .map((p) => (p.a === state.selectedKey ? p.b : p.a)) : []);
  for (const o of obs) {
    const p = pos(o);
    if (!p) continue;
    const mm = m?.measurements[o.key];
    const cls = ["obs-dot", mm && mm.status !== "ok" ? "rejected" : "", o.key === state.selectedKey ? "selected" : "",
                 partners.has(o.key) ? "partner" : ""].join(" ");
    const c = el("circle", { class: cls, cx: p[0], cy: p[1], r: o.key === state.selectedKey ? 5 : 3.6, tabindex: "-1" },
      el("title", {}, `${o.key}\n${fmtDate(o.t_mid_iso)}\n${p[3] ? "λ at target " + fmt(p[2], 4) + " µm" : "image band centre (run the analysis for λ at the target)"}${mm ? "\n" + (mm.quality || "") : ""}`));
    c.style.fill = DET_COLORS[o.detector];
    c.addEventListener("click", () => emit("select", o.key));
    svg.append(c);
  }
  document.getElementById("ruler-caption").textContent = m
    ? `${m.accepted.length} wavelength-matched pairs (vertical links). Bold links differ in brightness by |z| ≥ 5. Faded dots were rejected. Click a dot to select it.`
    : "Before analysis, dots sit at each image's band centre. Run the analysis to place them at the wavelength measured at the target.";
}
