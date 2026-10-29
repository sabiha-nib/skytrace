// Uncertainty Explorer (Discovery Lab tab). Shows what each recorded uncertainty is made of (UNC-1, computed by the
// Python pipeline), parameter sensitivity from STAB-1 kept separate, and the effects no method quantifies.
// Question answered: "how much of the stated uncertainty comes from where, and what is not in it?"

import { emit, getDiscovery, state } from "./state.js";
import { el, fmt, shortKey } from "./util.js";

const COLS = { east: "#5fd0e4", north: "#a48cf2" };

// Horizontal bars, one row per σ component, east and north side by side; bounds drawn as a tick, not a bar.
function sigmaChart(rows) {
  const plotted = rows.filter((r) => r.kind === "sigma" || r.kind === "bound");
  const vals = plotted.flatMap((r) => Object.values(r.values)).filter((v) => typeof v === "number" && Number.isFinite(v));
  const max = Math.max(...vals, 1e-9);
  const W = 640, rowH = 34, left = 250, right = 70, top = 10, H = top + plotted.length * rowH + 30;
  const X = (v) => left + (v / max) * (W - left - right);
  const svg = el("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Components of the motion uncertainty in mas/yr" });
  plotted.forEach((r, i) => {
    const y = top + i * rowH;
    svg.append(el("text", { x: left - 8, y: y + 15, "text-anchor": "end" }, r.component));
    if (r.kind === "bound") {
      const v = r.values.rate_bound;
      if (typeof v === "number") {
        svg.append(el("line", { x1: X(v), x2: X(v), y1: y + 4, y2: y + 24, class: "thresh" }),
                   el("text", { x: X(v) + 6, y: y + 18 }, `≤ ${fmt(v, 2)} (bound)`));
      } else svg.append(el("text", { x: left, y: y + 18 }, "not recorded"));
      return;
    }
    ["east", "north"].forEach((k, j) => {
      const v = r.values[k];
      if (typeof v !== "number") { svg.append(el("text", { x: left, y: y + 10 + j * 11 }, `${k}: not recorded`)); return; }
      const rect = el("rect", { x: left, y: y + 3 + j * 11, width: Math.max(1, X(v) - left), height: 9 });
      rect.style.fill = COLS[k];
      svg.append(rect, el("text", { x: X(v) + 6, y: y + 11 + j * 11 }, `${fmt(v, v < 10 ? 2 : 0)}`));
    });
  });
  svg.append(el("line", { class: "axis-line", x1: left, x2: W - right, y1: H - 24, y2: H - 24 }),
             el("text", { x: (left + W - right) / 2, y: H - 6, "text-anchor": "middle" }, "mas/yr (east and north components)"));
  return svg;
}

function shareBar(share) {
  if (!share) return el("span", { class: "faint" }, "—");
  const names = { exposure_a: "A", exposure_b: "B", exposure_b_scaled: "B", calibration_ratio: "calibration" };
  const colors = { exposure_a: "#5fd0e4", exposure_b: "#a48cf2", exposure_b_scaled: "#a48cf2", calibration_ratio: "#e6b450" };
  return el("div", { class: "sharebar", role: "img", "aria-label": Object.entries(share).map(([k, v]) => `${names[k]} ${fmt(100 * v, 0)}%`).join(", ") },
    ...Object.entries(share).map(([k, v]) => { const s = el("span", { title: `${names[k]}: ${fmt(100 * v, 1)}% of the variance` }); s.style.width = `${100 * v}%`; s.style.background = colors[k]; return s; }));
}

export async function renderUncertainty(p) {
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Loading the decomposition…");
  p.append(holder);
  let d;
  try { d = await getDiscovery(); } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return; }
  const u = d.uncertainty;
  const parts = [el("p", { class: "muted" }, `${u.method}: components of the recorded uncertainties, taken from logged values. ${u.sensitivity_note}`)];
  // motion
  if (u.motion.available) {
    const rows = u.motion.rows;
    parts.push(el("div", { class: "card" }, el("h3", {}, "Motion uncertainty components ", el("span", { class: "muted" }, `(primary fit: ${u.motion.fit_kind} positions)`)),
      sigmaChart(rows),
      el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ...["Component", "Kind", "Value", "Source"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, ...rows.map((r) => el("tr", {}, el("td", {}, r.component), el("td", {}, r.kind === "bound" ? "bound (not a σ)" : r.kind),
          el("td", { class: "num" }, Object.entries(r.values).map(([k, v]) => `${k.replaceAll("_", " ")} ${typeof v === "number" ? fmt(v, Math.abs(v) < 10 ? 2 : 0) : v ?? "not recorded"}`).join(", ") + (r.unit && r.kind !== "count" ? ` ${r.unit}` : "")),
          el("td", { class: "muted" }, r.source || "", r.detail?.note ? ` · ${r.detail.note}` : ""))))))));
  } else parts.push(el("div", { class: "card" }, el("h3", {}, "Motion"), el("p", { class: "muted" }, `No motion uncertainty: ${u.motion.reason}`)));
  // brightness
  if (u.variability.available) {
    const cal = u.variability.calibration_check || {};
    parts.push(el("div", { class: "card" }, el("h3", {}, "Brightness comparison: what the z denominator is made of ", el("span", { class: "muted" }, `(${u.variability.pairs.length} largest of ${u.variability.n_pairs} matched pairs)`)),
      el("p", { class: "muted" }, cal.status === "insufficient" ? "The calibration check had too few reference stars; z values are not scaled."
        : `Calibration check: reference stars scatter ${fmt(cal.robust_scatter, 2)}× their errors; z used = calibrated z ÷ ${fmt(cal.error_scale, 2)}.`),
      el("div", { class: "table-wrap" }, el("table", { class: "lvl-investigate" },
        el("thead", {}, el("tr", {}, ...["Pair (A → B)", "z raw", "z calibrated", "z used", "σ total (µJy)", "Variance share", "Refs", "Check"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, ...u.variability.pairs.map((r) => el("tr", {},
          el("td", {}, `${shortKey(r.a)} → ${shortKey(r.b)}`), el("td", { class: "num" }, fmt(r.z_raw, 1)),
          el("td", { class: "num" }, r.calibrated ? fmt(r.z_calibrated, 1) : "not calibrated"), el("td", { class: "num" }, fmt(r.z_used, 1)),
          el("td", { class: "num" }, fmt(r.denominator_ujy, 0)), el("td", {}, shareBar(r.variance_share)), el("td", { class: "num" }, r.n_refs ?? "—"),
          el("td", { class: r.consistent_with_log === false ? "status-rejected" : "status-ok", title: "Recomputed from logged inputs and compared with the logged z" },
            r.calibrated ? (r.consistent_with_log ? "matches log" : "MISMATCH") : "—")))))),
      el("div", { class: "legend" }, ...[["#5fd0e4", "exposure A"], ["#a48cf2", "exposure B"], ["#e6b450", "calibration ratio"]].map(([c, t]) => { const i = el("i", { class: "swatch" }); i.style.background = c; return el("span", {}, i, t); }))));
  } else parts.push(el("div", { class: "card" }, el("h3", {}, "Brightness"), el("p", { class: "muted" }, u.variability.reason)));
  // sensitivity (separate)
  const st = state.stability?.target === state.targetId ? state.stability.result : null;
  parts.push(el("div", { class: "card" }, el("h3", {}, "Sensitivity to analysis choices ", el("span", { class: "muted" }, "(STAB-1; not a statistical uncertainty)")),
    st ? el("dl", { class: "kv" },
      el("dt", {}, "Proper motion across runs"), el("dd", {}, (() => { const v = [st.base, ...st.runs].map((r) => r.pm_measured_mas_yr).filter((x) => x != null);
        return v.length ? `${fmt(Math.min(...v), 0)} – ${fmt(Math.max(...v), 0)} mas/yr over ${v.length} runs` : "no motion measured"; })()),
      el("dt", {}, "Largest calibrated |z| across runs"), el("dd", {}, (() => { const v = [st.base, ...st.runs].map((r) => r.max_abs_z_calibrated).filter((x) => x != null);
        return v.length ? `${fmt(Math.min(...v), 1)} – ${fmt(Math.max(...v), 1)}` : "no calibrated pair"; })()),
      el("dt", {}, "Outcomes"), el("dd", {}, Object.entries(st.stable).map(([q, ok]) => `${q.replace("_", " ")}: ${ok ? "stable" : "fragile"}`).join(" · ")))
      : el("div", { class: "controls" }, el("p", { class: "muted" }, "Not run yet for this target."),
        el("button", { class: "btn small", type: "button", onclick: () => emit("goto-lab", "rerun-stability") }, "Run the stability check"))));
  parts.push(el("div", { class: "card" }, el("h3", {}, "Not quantified by any method here"),
    el("ul", { class: "limits" }, ...u.unquantified.map((x) => el("li", {}, el("strong", {}, x.name), `: ${x.why}`)))));
  holder.replaceWith(...parts);
  const { attachFigureExports } = await import("./figures.js");
  attachFigureExports(p);
}
