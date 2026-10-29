// Discovery Lab: outcomes, the evidence behind them, alternative explanations, sensitivity re-runs, and the report.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { scatter } from "./charts.js";
import { $, DET_COLORS, categoryLabel, clear, detSwatch, download, el, fmt, fmtDate, questionLabel, shortKey, toast } from "./util.js";

let tab = "outcomes";

// Guidance on competing explanations. These are standard considerations for each outcome, not results.
const EXPLANATIONS = {
  variability_candidate: [
    ["Intrinsic variability of the source", "The same change should appear in other wavelength-matched pairs and other detectors at similar dates."],
    ["Residual wavelength difference within tolerance", "Check |Δλ| of the significant pairs; a steep spectrum turns small Δλ into flux changes."],
    ["PSF or sensitivity variation across the detector", "Compare pairs where the target fell at similar detector positions; inspect fit χ²."],
    ["Unresolved neighbour or blend", "Look for catalogue sources within a few pixels; check whether the centroid shifts with the flux."],
    ["Calibration drift between epochs", "Reference stars measured the same way should not show the same change."],
  ],
  motion_inconsistent: [
    ["Parallax not modelled", "The residual pattern would follow the observer's yearly motion, bounded by the catalogue parallax."],
    ["Blending with a neighbour", "Check exposures where catalogue sources fall near the target's path."],
    ["Chromatic centroid shifts", "Fit each detector separately; a wavelength-dependent offset points to chromatic effects."],
    ["Catalogue proper motion error", "Compare the catalogue uncertainty and quality indicators (e.g. RUWE)."],
  ],
  registration_limited: [
    ["Too few or poorly placed reference stars", "Inspect plate residuals and the number of references per exposure."],
    ["Short baseline", "The expected shift between epochs may be smaller than the registration scatter; more epochs are needed."],
  ],
  motion_detected: [["Agreement with the catalogue", "Expected for a known high-proper-motion star; this validates the measurement chain, it is not a new finding."]],
  spectral_difference_only: [["Source spectrum sampled at different wavelengths", "This is the expected effect of the linear variable filters; it is not a change over time."]],
  insufficient_evidence: [["Not enough usable data", "More epochs, a matched-wavelength revisit, or different detectors would be needed."]],
  instrumental: [["Flagged or unusable pixels", "Inspect the quality flags and fit diagnostics of the rejected exposures."]],
  partially_usable: [["Some exposures rejected", "Check whether rejections cluster in one detector or date; they are listed in the measurements table."]],
  no_significant_change: [["Change below sensitivity", "A smaller change could be present; the stated uncertainties set the limit."]],
};

export function renderLab() {
  const body = $("#lab-body");
  clear(body);
  if (!state.target) { body.append(el("p", { class: "empty" }, "This target has no stored observations yet.")); return; }
  if (!state.model) {
    body.append(el("div", { class: "empty" }, el("h3", {}, "No analysis yet"), el("p", {}, "Run the analysis to measure every observation and assess motion and brightness changes."),
      el("button", { class: "btn primary", onclick: () => emit("run") }, "Run analysis")));
    return;
  }
  const tabs = [["outcomes", "Outcomes"], ["motion", "Motion"], ["variability", "Brightness"], ["spectrum", "Spectrum"], ["measurements", "Measurements"], ["rerun", "Re-run & compare"]];
  const bar = el("div", { class: "tabs", role: "tablist" }, ...tabs.map(([id, label]) => {
    const b = el("button", { role: "tab", "aria-selected": tab === id ? "true" : "false" }, label);
    b.addEventListener("click", () => { tab = id; renderLab(); });
    return b;
  }));
  const panel = el("div", { role: "tabpanel" });
  body.append(bar, panel);
  ({ outcomes, motion, variability, spectrum, measurements, rerun })[tab](panel);
}

function outcomes(p) {
  const m = state.model;
  const grid = el("div", { class: "outcomes" });
  for (const o of m.outcomes) {
    const ev = Object.entries(o.evidence).filter(([, v]) => typeof v !== "object" || v === null);
    grid.append(el("article", { class: `card outcome c-${o.category}` },
      el("h3", {}, questionLabel(o.question)), el("div", { class: "cat" }, categoryLabel(o.category)),
      el("p", {}, o.statement),
      el("dl", { class: "kv evidence" }, ...ev.slice(0, 8).flatMap(([k, v]) => [el("dt", {}, k.replaceAll("_", " ")), el("dd", {}, typeof v === "number" ? fmt(v, Math.abs(v) < 10 ? 2 : 0) : String(v))])),
      el("details", { class: "explanations" }, el("summary", {}, "Criteria"), el("ul", {}, ...o.criteria.map((c) => el("li", {}, c)))),
      el("details", { class: "explanations" }, el("summary", {}, "Limitations"), el("ul", {}, ...o.limitations.map((c) => el("li", {}, c)))),
      el("details", { class: "explanations" }, el("summary", {}, "Explanations to consider (guidance, not results)"),
        el("dl", {}, ...(EXPLANATIONS[o.category] || []).flatMap(([a, b]) => [el("dt", {}, a), el("dd", {}, b)]))),
      el("div", { class: "controls" },
        el("button", { class: "btn small", onclick: () => emit("goto", { ws: "graph", focus: "claim:" + o.question }) }, "Trace in Evidence Graph"),
        el("button", { class: "btn small", onclick: () => emit("ask", `Explain the ${questionLabel(o.question).toLowerCase()} outcome and its main uncertainty.`) }, "Ask the copilot"))));
  }
  p.append(grid, el("div", { class: "controls" },
    el("button", { class: "btn", onclick: async () => {
      try { download(`skytrace-${state.targetId}-${state.inv.investigation_id}.md`, await api.report(state.inv.investigation_id)); toast("Report downloaded"); }
      catch (e) { toast(e.message); } } }, "Download report (Markdown)"),
    el("span", { class: "muted" }, `Rules ${m.outcomes[0]?.rules || ""} · analysis ${m.record.parameters.analysis_version} · content hash ${m.record.content_hash.slice(0, 12)}…`)));
}

function motion(p) {
  const a = state.model.astrometry;
  if (!a) { p.append(el("p", { class: "empty" }, state.model.astrometryEvent?.detail || "No astrometry was possible.")); return; }
  const s = a.series, f = a.fit, cmp = a.comparison;
  const t0 = f.t_ref;
  const sel = (k) => () => emit("select", k);
  const mk = (getY, getE, getP) => [{
    points: s.map((d) => ({ x: d.t_jyear, y: getY(d) - getP(d) + 0, ey: getE(d), color: d.used_in_fit === false ? "#e48b5c" : DET_COLORS[state.model.measurements[d.key]?.detector],
      hollow: d.used_in_fit === false, title: `${d.key}\n${fmt(getY(d) - getP(d), 0)} ± ${fmt(getE(d), 0)} mas from the catalogue prediction${d.used_in_fit === false ? "\nrejected as an outlier" : ""}`, onClick: sel(d.key) })),
  }];
  p.append(
    el("div", { class: "card" }, el("h3", {}, "Proper motion"),
      el("dl", { class: "kv" },
        el("dt", {}, "Measured"), el("dd", {}, `${fmt(f.pm_xi_mas_yr, 0)} ± ${fmt(f.sig_xi, 0)} mas/yr (east), ${fmt(f.pm_eta_mas_yr, 0)} ± ${fmt(f.sig_eta, 0)} mas/yr (north)`),
        el("dt", {}, "Catalogue"), el("dd", {}, `${fmt(a.catalogue.pmra, 0)}, ${fmt(a.catalogue.pmdec, 0)} mas/yr · ${a.catalogue.source}`),
        el("dt", {}, "Difference"), el("dd", {}, `${fmt(cmp.z_pmra, 2)}σ and ${fmt(cmp.z_pmdec, 2)}σ (significance of the difference, not a probability)`),
        el("dt", {}, "Data"), el("dd", {}, `${f.n_epochs} exposures used over ${fmt(f.baseline_yr, 2)} yr; ${f.rejected.length} rejected as outliers; reduced χ² ${fmt(f.reduced_chi2, 2)}`),
        el("dt", {}, "Not modelled"), el("dd", {}, `parallax (up to ${fmt(a.parallax_systematic_bound_mas, 0)} mas), chromatic PSF/distortion`))),
    el("div", { class: "card" }, el("h3", {}, "East offset from the catalogue prediction ", el("span", { class: "muted" }, "(mas; 0 = catalogue motion exactly)")),
      scatter({ xLabel: "Epoch (Julian year)", yLabel: "Δξ (mas)", series: mk((d) => d.xi_mas, (d) => d.sig_xi_mas, (d) => d.pred_xi_mas), hlines: [{ y: 0, class: "cat-line", label: "catalogue" }], xfmt: (v) => fmt(v, 2) })),
    el("div", { class: "card" }, el("h3", {}, "North offset from the catalogue prediction ", el("span", { class: "muted" }, "(mas)")),
      scatter({ xLabel: "Epoch (Julian year)", yLabel: "Δη (mas)", series: mk((d) => d.eta_mas, (d) => d.sig_eta_mas, (d) => d.pred_eta_mas), hlines: [{ y: 0, class: "cat-line", label: "catalogue" }], xfmt: (v) => fmt(v, 2) })),
    el("div", { class: "card" }, el("h3", {}, "Registration scatter per exposure ", el("span", { class: "muted" }, "(plate-solution residual, mas per axis)")),
      scatter({ xLabel: "Epoch (Julian year)", yLabel: "residual (mas)", series: [{ points: s.map((d) => ({ x: d.t_jyear, y: d.plate_rms_mas, color: "#8fb3ff", title: `${d.key}: ${fmt(d.plate_rms_mas, 0)} mas, ${d.n_refs} reference stars`, onClick: sel(d.key) })) }], xfmt: (v) => fmt(v, 2) })));
  void t0;
}

function variability(p) {
  const m = state.model;
  const fp = [...m.flux].sort((a, b) => Math.abs(b.z) - Math.abs(a.z));
  const meas = m.measurements;
  p.append(el("div", { class: "card" }, el("h3", {}, "Wavelength-matched flux comparisons ", el("span", { class: "muted" }, `(${fp.length} pairs; |z| ≥ 5 is the candidate threshold)`)),
    scatter({ xLabel: "Days between the two observations", yLabel: "z (significance of the difference)", xfmt: (v) => fmt(v, 0), yfmt: (v) => fmt(v, 0),
      hlines: [{ y: 5, label: "+5" }, { y: -5, label: "−5" }],
      series: [{ points: fp.map((f) => ({ x: f.delta_t_days, y: f.z, color: DET_COLORS[meas[f.a]?.detector],
        title: `${f.a} → ${f.b}\n${fmt(f.flux_a_ujy, 0)} → ${fmt(f.flux_b_ujy, 0)} µJy, z = ${fmt(f.z, 1)}\n|Δλ| ${fmt(f.delta_lambda_um, 4)} µm`,
        onClick: () => { state.selectedKey = f.a; state.partnerKey = f.b; emit("goto", { ws: "time", key: f.a, partner: f.b }); } })) }] })),
    el("div", { class: "card" }, el("h3", {}, "Pairs, most significant first"),
      el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ...["Detector", "A", "B", "Δt (d)", "|Δλ| (µm)", "Flux A → B (µJy)", "z"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, ...fp.slice(0, 80).map((f) => {
          const tr = el("tr", { tabindex: "0" }, el("td", {}, detSwatch(meas[f.a]?.detector), `D${meas[f.a]?.detector}`),
            el("td", {}, fmtDate(meas[f.a]?.t_mid_iso)), el("td", {}, fmtDate(meas[f.b]?.t_mid_iso)), el("td", { class: "num" }, fmt(f.delta_t_days, 1)),
            el("td", { class: "num" }, fmt(f.delta_lambda_um, 4)), el("td", { class: "num" }, `${fmt(f.flux_a_ujy, 0)} → ${fmt(f.flux_b_ujy, 0)}`),
            el("td", { class: "num" }, fmt(f.z, 1)));
          tr.addEventListener("click", () => { state.selectedKey = f.a; state.partnerKey = f.b; emit("goto", { ws: "time", key: f.a, partner: f.b }); });
          return tr;
        }))))),
    el("p", { class: "muted" }, `Pairs not compared: ${Object.entries(m.pairRejections).map(([k, v]) => `${k} ${v}`).join(", ") || "none"}. Different-wavelength pairs are excluded because their flux differences mostly reflect the spectrum.`));
}

function spectrum(p) {
  const pts = state.model.spectrum;
  const mjds = [...new Set(pts.map((d) => Math.round(d.mjd / 30)))].sort();
  p.append(el("div", { class: "card" }, el("h3", {}, "Aperture flux versus wavelength ", el("span", { class: "muted" }, "(each point is one exposure)")),
    scatter({ xLabel: "Wavelength at the target (µm)", yLabel: "Aperture flux (µJy)", xfmt: (v) => fmt(v, 1),
      series: [{ points: pts.map((d) => ({ x: d.wavelength_um, y: d.status === "ok" ? d.flux_ujy : 0, ey: d.status === "ok" ? d.flux_err_ujy : 0,
        color: DET_COLORS[d.detector], hollow: d.status !== "ok", title: `${d.key}\n${fmtDate(state.model.measurements[d.key]?.t_mid_iso)}\n${d.status === "ok" ? fmt(d.flux_ujy, 0) + " ± " + fmt(d.flux_err_ujy, 0) + " µJy" : "not measured: " + d.status}`,
        onClick: () => emit("select", d.key) })) }] }),
    el("p", { class: "muted" }, `Points come from ${mjds.length} visit groups. A variable source mixes brightness from different dates into one spectrum. Fluxes are not aperture-corrected, so the shape across detectors is approximate. Hollow points at zero were not measured.`)));
}

function measurements(p) {
  const rows = Object.values(state.model.measurements).sort((a, b) => a.mjd - b.mjd || a.detector - b.detector);
  p.append(el("div", { class: "table-wrap" }, el("table", {},
    el("thead", {}, el("tr", {}, ...["Date", "Det", "λ (µm)", "Flux (µJy)", "S/N", "Centroid σ (px)", "Plate refs", "Residual (mas)", "Status"].map((h) => el("th", { scope: "col" }, h)))),
    el("tbody", {}, ...rows.map((m) => {
      const ph = m.photometry || {}, c = m.centroid || {}, pl = m.plate || {};
      const tr = el("tr", { tabindex: "0", title: (m.notes || []).join("; ") },
        el("td", {}, fmtDate(m.t_mid_iso)), el("td", {}, detSwatch(m.detector), m.detector), el("td", { class: "num" }, fmt(m.wavelength_um, 4)),
        el("td", { class: "num" }, ph.status === "ok" ? `${fmt(ph.flux_ujy, 0)} ± ${fmt(ph.flux_err_ujy, 0)}` : "—"), el("td", { class: "num" }, ph.status === "ok" ? fmt(ph.snr, 0) : "—"),
        el("td", { class: "num" }, c.converged ? fmt(c.sigma_x, 3) : "—"), el("td", { class: "num" }, pl.n_refs ?? "—"), el("td", { class: "num" }, pl.n_refs ? fmt(pl.rms_mas, 0) : "—"),
        el("td", { class: m.status === "ok" ? "status-ok" : "status-rejected" }, m.quality));
      tr.addEventListener("click", () => emit("goto", { ws: "explorer", key: m.key }));
      return tr;
    })))));
}

function rerun(p) {
  const cur = state.model.record.parameters;
  const fields = [["aperture_radius_px", "Aperture radius (px)", 1, 5, 0.25], ["fit_half_size_px", "Fit box half-size (px)", 3, 8, 1],
                  ["wavelength_tolerance_channels", "Wavelength tolerance (× bandwidth)", 0.1, 1, 0.05], ["epoch_clip_sigma", "Epoch outlier clip (σ)", 2, 10, 0.5]];
  const inputs = {};
  const dets = el("div", { class: "controls" }, el("span", {}, "Detectors"), ...[1, 2, 3, 4, 5, 6].map((d) => {
    const i = el("input", { type: "checkbox", checked: (cur.detectors || []).includes(d), value: d });
    inputs["det" + d] = i; return el("label", {}, i, `D${d}`);
  }));
  const form = el("div", { class: "params" }, ...fields.map(([k, label, lo, hi, step]) => {
    const i = el("input", { type: "number", min: lo, max: hi, step, value: cur[k] });
    inputs[k] = i; return el("label", {}, label, i);
  }));
  const go = el("button", { class: "btn primary" }, "Re-run analysis");
  go.addEventListener("click", () => {
    const params = Object.fromEntries(fields.map(([k]) => [k, +inputs[k].value]));
    params.detectors = [1, 2, 3, 4, 5, 6].filter((d) => inputs["det" + d].checked);
    emit("run", params);
  });
  p.append(el("div", { class: "card" }, el("h3", {}, "Parameters"), el("p", { class: "muted" }, "Changing a parameter re-runs the deterministic analysis on the same verified files. The previous run is kept below for comparison, so you can see how sensitive each outcome is."),
    form, dets, el("div", { class: "controls" }, go)));
  const prev = state.prevInv;
  if (!prev) { p.append(el("p", { class: "muted" }, "Re-run with different parameters to compare outcomes here.")); return; }
  const pm = prev.model, cm = state.model;
  const keys = [...new Set([...Object.keys(prev.record.parameters), ...Object.keys(cur)])].filter((k) => !["bundle_manifest_sha256", "bundle", "bundle_kind", "analysis_version"].includes(k));
  const prow = (k) => {
    const a = JSON.stringify(prev.record.parameters[k]), b = JSON.stringify(cur[k]);
    return el("tr", {}, el("td", {}, k), el("td", {}, a ?? "—"), el("td", { class: a !== b ? "changed" : "" }, b ?? "—"));
  };
  const orow = (q) => {
    const a = pm.outcomes.find((o) => o.question === q), b = cm.outcomes.find((o) => o.question === q);
    return el("tr", {}, el("td", {}, questionLabel(q)), el("td", {}, categoryLabel(a?.category)), el("td", { class: a?.category !== b?.category ? "changed" : "" }, categoryLabel(b?.category)));
  };
  const nrow = (label, f) => { const a = f(pm), b = f(cm); return el("tr", {}, el("td", {}, label), el("td", {}, a), el("td", { class: a !== b ? "changed" : "" }, b)); };
  p.append(el("div", { class: "card" }, el("h3", {}, "Previous run versus this run"),
    el("table", { class: "diff-table" }, el("thead", {}, el("tr", {}, el("th", {}, ""), el("th", {}, "Previous"), el("th", {}, "This run"))),
      el("tbody", {}, ...keys.map(prow), ...["data_quality", "motion", "variability"].map(orow),
        nrow("Matched pairs", (x) => String(x.accepted.length)),
        nrow("Pairs with |z| ≥ 5", (x) => String(x.flux.filter((f) => Math.abs(f.z) >= 5).length)),
        nrow("Measured pm (mas/yr)", (x) => x.astrometry ? `${fmt(x.astrometry.fit.pm_xi_mas_yr, 0)}, ${fmt(x.astrometry.fit.pm_eta_mas_yr, 0)}` : "—"),
        nrow("Content hash", (x) => x.record.content_hash.slice(0, 12))))));
}
