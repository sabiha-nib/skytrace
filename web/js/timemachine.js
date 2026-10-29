// Time Machine: compare observation A (selected) with observation B.
// Brightness comparisons are offered only for wavelength-matched pairs (WLMATCH-2, decided by the server's analysis).
// Blink and fade remain available for any pair because positions can be compared across wavelengths, but a
// persistent banner states when brightness differences are not evidence of change.

import { api } from "./api.js";
import { compatible, compatibilityReason, emit, state } from "./state.js";
import { ImageViewer, decodeFrame } from "./viewer.js";
import { markersFor, overlayControls, stretchControls } from "./explorer.js";
import { $, clear, detSwatch, el, fmt, fmtDate, shortKey } from "./util.js";

let viewer = null, viewerB = null;
let mode = "blink", timer = null, interval = 700, playing = true, pairData = null, tok = 0;

export function renderTime() {
  const body = $("#time-body");
  stop();
  clear(body);
  if (!state.target) { body.append(el("p", { class: "empty" }, "This target has no stored observations. See the Sky Explorer for how to acquire them.")); return; }
  if (!state.model) {
    body.append(el("div", { class: "empty" }, el("h3", {}, "Run the analysis first"),
      el("p", {}, "The Time Machine needs the wavelength at the target in every image to decide which pairs can be compared. Use Run analysis at the top.")));
    return;
  }
  if (!state.selectedKey) { body.append(el("p", { class: "empty" }, "Select an observation (in the Sky Explorer or on the wavelength ruler) to use as A.")); return; }
  if (!state.partnerKey || state.partnerKey === state.selectedKey) {
    // default B: the most distant wavelength-matched partner in time, so a change (if any) is most visible
    const m = state.model;
    const partners = m.accepted.filter((p) => p.a === state.selectedKey || p.b === state.selectedKey)
      .sort((x, y) => y.delta_t_days - x.delta_t_days);
    state.partnerKey = partners.length ? (partners[0].a === state.selectedKey ? partners[0].b : partners[0].a) : null;
  }
  const frames = el("div", { class: "tm-frames" + (mode === "side" ? " side" : "") });
  const hostA = el("div"); frames.append(hostA);
  viewer = new ImageViewer(hostA, { label: "Comparison view" });
  viewerB = null;
  if (mode === "side") { const hostB = el("div"); frames.append(hostB); viewerB = new ImageViewer(hostB, { label: "Observation B" }); }
  viewer.empty(state.partnerKey ? "Loading…" : "Choose observation B from the list.");
  const setStretch = (s) => { for (const v of [viewer, viewerB].filter(Boolean)) { Object.assign(v.opts.stretch, s); v._rescale(); v.render(); } };
  const shared = el("input", { type: "checkbox", checked: true });
  shared.addEventListener("change", () => { for (const v of [viewer, viewerB].filter(Boolean)) { v.opts.shared = shared.checked; v._rescale(); v.render(); } });
  const left = el("div", {}, el("div", { id: "tm-banner" }), frames, modeBar(),
    el("div", { class: "controls" }, ...stretchControls(() => viewer.opts.stretch, setStretch), el("label", { title: "Use A's black and white points for both images, so normalisation cannot create apparent changes" }, shared, "Same display scale for A and B")),
    el("div", { class: "controls" }, ...overlayControls(() => viewer)),
    el("div", { class: "card", id: "tm-details" }));
  body.append(el("div", { class: "tm-layout" }, left, partnerPanel()));
  if (state.partnerKey) loadPair();
}

function modeBar() {
  const m = state.model;
  const ok = state.partnerKey && compatible(m, state.selectedKey, state.partnerKey);
  const btn = (id, label, disabled, title) => {
    const b = el("button", { "aria-pressed": mode === id ? "true" : "false", disabled: disabled || null, title: title || "" }, label);
    b.addEventListener("click", () => { mode = id; renderTime(); });
    return b;
  };
  const speed = el("input", { type: "range", min: "250", max: "1600", step: "50", value: interval, "aria-label": "Blink interval" });
  speed.addEventListener("input", () => { interval = +speed.value; if (playing) start(); });
  const fade = el("input", { type: "range", min: "0", max: "1", step: "0.02", value: viewer?.opts.fade ?? 0.5, "aria-label": "Fade between A and B" });
  fade.addEventListener("input", () => { viewer.opts.fade = +fade.value; viewer.render(); });
  const play = el("button", { class: "btn small", "aria-pressed": playing ? "true" : "false" }, playing ? "Pause" : "Play");
  play.addEventListener("click", () => { playing = !playing; playing ? start() : stop(); play.textContent = playing ? "Pause" : "Play"; play.setAttribute("aria-pressed", String(playing)); });
  return el("div", { class: "controls" },
    el("div", { class: "segmented", role: "group", "aria-label": "Comparison mode" },
      btn("blink", "Blink"), btn("fade", "Fade"), btn("side", "Side by side"),
      btn("diff", "Difference", !ok, ok ? "B − A after subtracting each image's median" : "Only for wavelength-matched pairs: a difference between wavelengths shows the spectrum, not a change")),
    mode === "blink" ? [play, el("label", {}, "Interval", speed)] : null,
    mode === "fade" ? el("label", {}, "A", fade, "B") : null);
}

function partnerPanel() {
  const m = state.model, A = state.selectedKey;
  const list = el("div", { class: "partner-list", role: "listbox", "aria-label": "Observation B" });
  const all = state.target.observations.filter((o) => o.included && o.key !== A);
  const groups = [["Same wavelength, same detector: brightness can be compared", all.filter((o) => compatible(m, A, o.key))],
                  ["Same detector, different wavelength", all.filter((o) => !compatible(m, A, o.key) && m.measurements[o.key]?.detector === m.measurements[A]?.detector)],
                  ["Other detectors", all.filter((o) => m.measurements[o.key] && m.measurements[o.key].detector !== m.measurements[A]?.detector)]];
  for (const [title, items] of groups) {
    list.append(el("h4", {}, `${title} (${items.length})`));
    for (const o of items) {
      const ok = compatible(m, A, o.key);
      const b = el("button", { class: "partner", role: "option", "aria-pressed": o.key === state.partnerKey ? "true" : "false" },
        detSwatch(o.detector), el("span", {}, fmtDate(o.t_mid_iso)),
        el("span", { class: "faint" }, m.measurements[o.key]?.wavelength_um != null ? `${fmt(m.measurements[o.key].wavelength_um, 3)} µm` : ""),
        ok ? null : el("span", { class: "why" }, "Brightness comparison unavailable: " + compatibilityReason(m, A, o.key)));
      b.addEventListener("click", () => { state.partnerKey = o.key; if (!ok && mode === "diff") mode = "blink"; emit("partner", o.key); });
      list.append(b);
    }
  }
  const mA = m.measurements[A];
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Observation A"),
    el("p", {}, detSwatch(mA?.detector), `${shortKey(A)} · ${fmtDate(mA?.t_mid_iso)} · ${mA?.wavelength_um != null ? fmt(mA.wavelength_um, 4) + " µm" : "λ unknown"}`),
    el("p", { class: "muted" }, "Change A by selecting another observation on the wavelength ruler.")),
    el("div", { class: "card" }, el("h3", {}, "Observation B"), list));
}

async function loadPair() {
  const t = ++tok;
  const A = state.selectedKey, B = state.partnerKey;
  try {
    pairData = await api.pair(state.targetId, A, B, state.inv?.investigation_id);
  } catch (e) { viewer.empty(`Could not load the pair: ${e.message}`); return; }
  if (t !== tok) return;
  const fa = decodeFrame(pairData.a), fb = decodeFrame(pairData.b);
  const mA = markersFor(A, pairData.a);
  const mB = [];
  if (pairData.b.predicted_target_xy) mB.push({ kind: "predictedB", x: pairData.b.predicted_target_xy[0], y: pairData.b.predicted_target_xy[1] });
  if (pairData.b.centroid_in_a) mB.push({ kind: "centroidB", x: pairData.b.centroid_in_a[0], y: pairData.b.centroid_in_a[1] });
  const cap = (p, lbl) => [`${lbl} · ${fmtDate(p.observation.t_mid_iso)} · D${p.observation.detector}`, p.wavelength_at_target_um != null ? `λ ${fmt(p.wavelength_at_target_um, 4)} µm` : "λ unknown"];
  if (mode === "side") {
    viewer.set({ frames: [fa], mode: "single", markers: [mA], captions: [cap(pairData.a, "A")] });
    viewerB.set({ frames: [fb], mode: "single", markers: [mB.map((x) => ({ ...x, kind: x.kind.replace("B", "") }))], captions: [cap(pairData.b, "B (on A's grid)")] });
  } else {
    // the difference caption must be in place before the first render (it was set afterwards and never shown)
    viewer.set({ frames: [fa, fb], mode: mode === "diff" ? "diff" : mode, index: 0, markers: [mA, mB],
      captions: mode === "diff" ? [["B − A (median-subtracted)", "warm: brighter in B · cool: fainter in B"]]
                                : [cap(pairData.a, "A"), cap(pairData.b, "B")] });
    if (mode === "blink" && playing) start();
  }
  renderBanner();
  renderDetails();
}

function renderBanner() {
  const c = pairData.comparison;
  const box = $("#tm-banner");
  if (!box || !c) return;
  box.replaceChildren(c.compatible_for_photometry
    ? el("div", { class: "banner ok" }, el("strong", {}, "Wavelength-matched pair."), el("p", {}, `${c.reason}. Brightness differences between these two images can be compared (rule ${c.rule}).`))
    : el("div", { class: "banner warn" }, el("strong", {}, "Not comparable for brightness."),
      el("p", {}, `${c.reason}. Brightness differences in this view reflect the source's spectrum and the detector, not a change over time. Positions can still be compared, with chromatic effects unmodelled.`)));
}

function renderDetails() {
  const c = pairData.comparison, box = $("#tm-details");
  if (!box) return;
  const kids = [el("h3", {}, "Comparison"), el("dl", { class: "kv" },
    el("dt", {}, "Time between"), el("dd", {}, c ? `${fmt(c.delta_t_days, 2)} days` : "—"),
    el("dt", {}, "Wavelengths"), el("dd", {}, c ? `${fmt(c.wavelength_a_um, 4)} and ${fmt(c.wavelength_b_um, 4)} µm (|Δλ| ${fmt(c.delta_lambda_um, 4)}, tolerance ${fmt(c.tolerance_um, 4)})` : "—"),
    el("dt", {}, "Registration"), el("dd", {}, pairData.registration),
    el("dt", {}, "Flux"), el("dd", {}, c?.flux ? `${fmt(c.flux.flux_a_ujy, 0)} → ${fmt(c.flux.flux_b_ujy, 0)} µJy; difference ${fmt(c.flux.delta_ujy, 0)} ± ${fmt(c.flux.sigma_ujy, 0)} (z = ${fmt(c.flux.z, 1)}, a significance, not a probability)` : (c?.flux_note || "—")),
    el("dt", {}, "Position change"), el("dd", {}, c?.position ? `Δξ ${fmt(c.position.d_xi_mas, 0)} ± ${fmt(c.position.sigma_xi_mas, 0)} mas, Δη ${fmt(c.position.d_eta_mas, 0)} ± ${fmt(c.position.sigma_eta_mas, 0)} mas` : "not available (no plate solution for one of the images)"),
    el("dt", {}, "Note"), el("dd", { class: "muted" }, pairData.note))];
  kids.push(registrationCard(c?.registration));
  kids.push(el("div", { class: "legend" }, ...[["#e6b450", "A: catalogue position"], ["#6cc6a4", "A: measured centroid"], ["#d97fb6", "B: catalogue position / centroid"]].map(([c2, t]) => {
    const i = el("i"); i.style.borderColor = c2; return el("span", {}, i, t);
  }), (() => { const i = el("i", { class: "swatch" }); i.style.background = "rgb(70,20,30)"; return el("span", {}, i, "no data: outside B's footprint after registration, or a missing value"); })()));
  kids.push(el("div", { class: "controls" },
    api.isStatic
      ? el("button", { class: "btn small", disabled: true, title: "Questions about named observations need the local server's assistant" }, "Ask the copilot about this pair")
      : el("button", { class: "btn small", onclick: () => emit("ask", `Compare ${state.selectedKey} and ${state.partnerKey}: are they measured at compatible wavelengths, and what changed?`) }, "Ask the copilot about this pair"),
    api.isStatic ? el("span", { class: "faint" }, "Not available in the static preview: questions about named observations are answered by the local server's assistant. The comparison above is computed from the record.") : null));
  box.replaceChildren(...kids);
}

function start() {
  stop();
  if (mode !== "blink" || !viewer) return;
  timer = setInterval(() => { viewer.opts.index = (viewer.opts.index + 1) % 2; viewer.render(); }, interval);
}
export function stop() { if (timer) clearInterval(timer); timer = null; }

export function toggleBlink() {
  if (mode !== "blink") return;
  playing = !playing; playing ? start() : stop();
  renderTime();
}

// REGDIAG-1: the geometry behind the registration, from each exposure's Gaia-referenced plate solution.
function registrationCard(g) {
  if (!g) return null;
  if (!g.available) return el("div", { class: "regdiag", id: "tm-regdiag" }, el("h4", {}, "Registration diagnostics"), el("p", { class: "muted" }, `Not available: ${g.reason}.`));
  const r = g.relative;
  const plate = (p) => `${fmt(p.scale_x_arcsec_px, 3)} × ${fmt(p.scale_y_arcsec_px, 3)} ″/px, x-axis at ${fmt(p.x_axis_angle_deg, 2)}°, ${p.n_refs ?? "?"} reference stars, residual RMS ${fmt(p.rms_mas, 0)} mas`;
  return el("div", { class: "regdiag", id: "tm-regdiag" }, el("h4", {}, "Registration diagnostics ", el("span", { class: "muted" }, `(${g.method})`)),
    el("dl", { class: "kv compact" },
      el("dt", {}, "Plate A"), el("dd", {}, plate(g.a)),
      el("dt", {}, "Plate B"), el("dd", {}, plate(g.b)),
      el("dt", {}, "B relative to A"), el("dd", {}, `rotation ${fmt(r.rotation_deg, 3)}°, scale ratio ${fmt(r.scale_ratio, 5)}`),
      el("dt", {}, "Target pixel"), el("dd", {}, `(${fmt(r.target_pixel_in_a[0], 1)}, ${fmt(r.target_pixel_in_a[1], 1)}) in A ↦ (${fmt(r.same_sky_point_in_b[0], 1)}, ${fmt(r.same_sky_point_in_b[1], 1)}) in B; shift (${fmt(r.shift_px[0], 1)}, ${fmt(r.shift_px[1], 1)}) px`)),
    el("p", { class: "faint" }, `${g.note}. A residual RMS comparable to the motion over the baseline would make a position change ambiguous; the Hypothesis Arena tests this (T-REG).`));
}
