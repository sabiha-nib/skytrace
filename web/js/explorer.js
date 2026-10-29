// Sky Explorer: one observation at a time, with its metadata, provenance and overlays.

import { api } from "./api.js";
import { state, emit } from "./state.js";
import { ImageViewer, decodeFrame } from "./viewer.js";
import { $, DET_COLORS, clear, detSwatch, el, fmt, fmtDate, shortKey, toast } from "./util.js";

let viewer = null;
let filters = { detector: "all", status: "all" };
let loadToken = 0;

export function markersFor(key, payload) {
  const m = state.model?.measurements[key];
  const out = [];
  if (payload?.predicted_target_xy) out.push({ kind: "predicted", x: payload.predicted_target_xy[0], y: payload.predicted_target_xy[1] });
  if (m?.centroid?.converged) out.push({ kind: "centroid", x: m.centroid.x, y: m.centroid.y });
  for (const r of m?.plate?.refs_xy || []) out.push({ kind: r.used ? "ref" : "ref-rejected", x: r.x, y: r.y });
  return out;
}

export function stretchControls(get, set) {
  const s = get();
  const fnSel = el("select", { "aria-label": "Display stretch" },
    ...["asinh", "linear", "sqrt", "log"].map((f) => el("option", { value: f, selected: s.fn === f }, f)));
  fnSel.addEventListener("change", () => set({ fn: fnSel.value }));
  const lo = el("input", { type: "range", min: "0", max: "20", step: "0.5", value: s.lo, "aria-label": "Black point percentile" });
  const hi = el("input", { type: "range", min: "90", max: "100", step: "0.1", value: s.hi, "aria-label": "White point percentile" });
  lo.addEventListener("input", () => set({ lo: +lo.value }));
  hi.addEventListener("input", () => set({ hi: +hi.value }));
  return [el("label", {}, "Stretch", fnSel), el("label", {}, "Black", lo), el("label", {}, "White", hi)];
}

export function overlayControls(viewerRef, extra = []) {
  const box = (key, label) => {
    const i = el("input", { type: "checkbox", checked: viewerRef().opts.overlays[key] });
    i.addEventListener("change", () => { viewerRef().opts.overlays[key] = i.checked; viewerRef().render(); });
    return el("label", {}, i, label);
  };
  return [box("predicted", "Catalogue position"), box("centroid", "Measured centroid"), box("refs", "Reference stars"), box("mask", "Rejected pixels"), ...extra];
}

function legend() {
  return el("div", { class: "legend" },
    el("span", {}, el("i"), "catalogue position at this epoch"),
    el("span", {}, el("i"), "measured centroid"), el("span", {}, el("i"), "reference star used"), el("span", {}, el("i"), "reference star rejected"));
}

function colourLegend(lg) {
  const cols = ["#e6b450", "#6cc6a4", "#8fb3ff", "#e48b5c"];
  [...lg.querySelectorAll("i")].forEach((i, k) => { i.style.borderColor = cols[k]; });
  return lg;
}

export function renderExplorer() {
  const body = $("#explorer-body");
  clear(body);
  const t = state.targets.find((x) => x.target_id === state.targetId);
  if (!t) { body.append(el("p", { class: "empty" }, "Choose a target.")); return; }
  if (!state.target) { body.append(noData(t)); return; }

  const left = el("div");
  const host = el("div");
  left.append(host);
  viewer = new ImageViewer(host, { label: "Selected observation" });
  viewer.empty("Select an observation from the table.");
  const setStretch = (s) => { Object.assign(viewer.opts.stretch, s); viewer._rescale(); viewer.render(); };
  left.append(el("div", { class: "controls" },
    ...stretchControls(() => viewer.opts.stretch, setStretch),
    el("button", { class: "btn small", onclick: () => viewer.zoomBy(1.4), "aria-label": "Zoom in" }, "+"),
    el("button", { class: "btn small", onclick: () => viewer.zoomBy(1 / 1.4), "aria-label": "Zoom out" }, "−"),
    el("button", { class: "btn small", onclick: () => viewer.resetView() }, "Reset view")),
    el("div", { class: "controls" }, ...overlayControls(() => viewer)), colourLegend(legend()),
    el("div", { class: "card", id: "obs-meta" }, el("p", { class: "muted" }, "Observation details appear here.")));

  const right = el("div");
  right.append(targetCard(t), obsTable());
  body.append(el("div", { class: "grid-2" }, left, right));
  if (state.selectedKey) loadSelected();
}

function noData(t) {
  const hint = t.hint || {};
  const rows = Object.entries(hint).filter(([k]) => k !== "source");
  return el("div", { class: "empty" },
    el("h3", {}, `No SPHEREx data stored for ${t.name} yet`),
    el("p", {}, "This build has no archive bundle for this target. The development environment could not reach the IRSA archive, so no real observations were downloaded. Nothing is shown in their place."),
    el("p", {}, "On a machine with internet access, acquire and verify the real data with:"),
    el("div", { class: "copy-cmd" }, el("code", {}, t.acquire_command),
      el("button", { class: "btn small", onclick: () => navigator.clipboard?.writeText(t.acquire_command).then(() => toast("Command copied")) }, "Copy")),
    el("p", {}, "Then restart Skytrace; the target will appear with its observations."),
    t.role ? el("p", {}, el("strong", {}, "Planned use: "), t.role) : null,
    rows.length ? el("div", { class: "card" }, el("h3", {}, "Planning hints ", el("span", { class: "muted" }, "(secondary source, unverified; not used in any measurement)")),
      el("dl", { class: "kv" }, ...rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, String(v))])),
      hint.source ? el("p", { class: "faint" }, hint.source) : null) : null,
    el("p", {}, "To explore the full workflow now, choose one of the synthetic test targets (SYN-…). They are generated by code and clearly marked."));
}

function targetCard(t) {
  const a = state.target.target.astrometry || {};
  const id = state.target.target.identity || {};
  const v = state.target.verification;
  return el("div", { class: "card" },
    el("h3", {}, state.target.target.name, " ", el("span", { class: "muted" }, state.target.kind === "synthetic" ? "· synthetic test target" : "· archive data")),
    el("dl", { class: "kv" },
      el("dt", {}, "Identity"), el("dd", {}, id.main_id || id.description || "—"),
      el("dt", {}, "Astrometry"), el("dd", {}, `${a.source || "—"} (epoch ${a.ref_epoch ?? "—"})`),
      el("dt", {}, "Position"), el("dd", {}, `RA ${fmt(a.ra, 5)}°, Dec ${fmt(a.dec, 5)}° (ICRS)`),
      el("dt", {}, "Proper motion"), el("dd", {}, `${fmt(a.pmra, 1)}, ${fmt(a.pmdec, 1)} mas/yr`),
      el("dt", {}, "Images"), el("dd", {}, `${t.n_included} included of ${t.n_observations} found · detectors ${(t.detectors || []).map((d) => "D" + d).join(" ")}`),
      el("dt", {}, "Time span"), el("dd", {}, t.time_span_iso ? `${fmtDate(t.time_span_iso[0])} → ${fmtDate(t.time_span_iso[1])}` : "—"),
      el("dt", {}, "Bundle"), el("dd", {}, v.ok ? `verified: ${v.n_files} files, ${(v.total_bytes / 1e6).toFixed(1)} MB, all checksums match` : "verification failed")));
}

function obsTable() {
  const wrap = el("div", { class: "card" });
  const detSel = el("select", { "aria-label": "Filter by detector" }, el("option", { value: "all" }, "All detectors"),
    ...[1, 2, 3, 4, 5, 6].map((d) => el("option", { value: d, selected: String(filters.detector) === String(d) }, `D${d}`)));
  const stSel = el("select", { "aria-label": "Filter by status" },
    ...[["all", "All"], ["ok", "Measured"], ["rejected", "Rejected"], ["excluded", "Excluded at selection"]].map(([v, l]) =>
      el("option", { value: v, selected: filters.status === v }, l)));
  detSel.addEventListener("change", () => { filters.detector = detSel.value; fill(); });
  stSel.addEventListener("change", () => { filters.status = stSel.value; fill(); });
  const tbody = el("tbody");
  wrap.append(el("h3", {}, "Observations"), el("div", { class: "filters" }, detSel, stSel, el("span", { id: "obs-count" })),
    el("div", { class: "table-wrap" }, el("table", { "aria-label": "Observations" },
      el("thead", {}, el("tr", {}, ...["Date (UTC)", "Detector", "λ at target (µm)", "Status", "Observation"].map((h) => el("th", { scope: "col" }, h)))),
      tbody)));
  function fill() {
    clear(tbody);
    const m = state.model;
    const rows = state.target.observations.filter((o) => {
      const mm = m?.measurements[o.key];
      const st = !o.included ? "excluded" : mm ? (mm.status === "ok" ? "ok" : "rejected") : "ok";
      return (filters.detector === "all" || String(o.detector) === String(filters.detector)) && (filters.status === "all" || filters.status === st);
    });
    $("#obs-count", wrap).textContent = `${rows.length} shown`;
    for (const o of rows) {
      const mm = m?.measurements[o.key];
      const st = !o.included ? ["excluded", "excluded"] : mm ? [mm.status, mm.status === "ok" ? "measured" : "rejected"] : ["", m ? "not measured" : "not analysed"];
      const tr = el("tr", { "aria-selected": o.key === state.selectedKey ? "true" : "false", tabindex: "0", dataset: { key: o.key } },
        el("td", {}, fmtDate(o.t_mid_iso)), el("td", {}, detSwatch(o.detector), `D${o.detector}`),
        el("td", { class: "num" }, mm?.wavelength_um != null ? fmt(mm.wavelength_um, 4) : "—"),
        el("td", { class: `status-${st[0]}`, title: !o.included ? o.exclusion_reason : mm?.quality || "" }, st[1]),
        el("td", { class: "faint" }, shortKey(o.key)));
      const pick = () => { if (o.included) emit("select", o.key); else toast(`Excluded at selection: ${o.exclusion_reason}`); };
      tr.addEventListener("click", pick);
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter") pick(); });
      tbody.append(tr);
    }
  }
  fill();
  return wrap;
}

export async function loadSelected() {
  if (!viewer || !state.selectedKey || !state.target) return;
  const key = state.selectedKey;
  const tok = ++loadToken;
  document.querySelectorAll("#explorer-body tbody tr").forEach((tr) => tr.setAttribute("aria-selected", tr.dataset.key === key ? "true" : "false"));
  try {
    const p = await api.image(state.targetId, key);
    if (tok !== loadToken) return;
    const f = decodeFrame(p);
    const o = p.observation;
    viewer.set({ frames: [f], mode: "single", markers: [markersFor(key, p)],
      captions: [[`${fmtDate(o.t_mid_iso)} · D${o.detector}`, p.wavelength_at_target_um != null ? `λ ${fmt(p.wavelength_at_target_um, 4)} µm` : "λ unknown"]] });
    renderMeta(p);
  } catch (e) {
    viewer.empty(`Could not load this image: ${e.message}`);
  }
}

function renderMeta(p) {
  const box = $("#obs-meta");
  if (!box) return;
  const o = p.observation, m = state.model?.measurements[o.key], prov = p.file.provenance || {};
  const phot = m?.photometry, c = m?.centroid, plate = m?.plate;
  box.replaceChildren(
    el("h3", {}, shortKey(o.key), " ", el("span", { class: "muted" }, `· ${o.release}`)),
    el("dl", { class: "kv" },
      el("dt", {}, "Observed"), el("dd", {}, `${fmtDate(o.t_mid_iso)} UTC (MJD ${fmt(o.t_mid_mjd, 4)})`),
      el("dt", {}, "Detector"), el("dd", {}, `D${o.detector}, image band ${fmt(o.em_min_um, 2)}–${fmt(o.em_max_um, 2)} µm`),
      el("dt", {}, "At the target"), el("dd", {}, p.wavelength_at_target_um != null ? `λ ${fmt(p.wavelength_at_target_um, 4)} µm, bandwidth ${fmt(p.bandwidth_at_target_um, 4)} µm` : "wavelength unavailable"),
      el("dt", {}, "Image"), el("dd", {}, `${p.width} × ${p.height} px, ${fmt(p.pixel_scale_arcsec[0], 2)}″/px, ${p.bunit || "units not stated"}; read with ${p.reader}`),
      el("dt", {}, "Flag bits"), el("dd", {}, p.flag_bits.origin === "header" ? "from the file header" : "from IRSA documentation only (undocumented bits not applied)"),
      m ? [el("dt", {}, "Measurement"), el("dd", { class: m.status === "ok" ? "status-ok" : "status-rejected" }, m.quality)] : [el("dt", {}, "Measurement"), el("dd", { class: "muted" }, "run the analysis")],
      phot ? [el("dt", {}, "Aperture flux"), el("dd", {}, phot.status === "ok" ? `${fmt(phot.flux_ujy, 0)} ± ${fmt(phot.flux_err_ujy, 0)} µJy (S/N ${fmt(phot.snr, 0)}; not aperture-corrected)` : `not measured: ${phot.detail}`)] : null,
      c ? [el("dt", {}, "Centroid"), el("dd", {}, c.converged ? `x ${fmt(c.x, 3)} ± ${fmt(c.sigma_x, 3)}, y ${fmt(c.y, 3)} ± ${fmt(c.sigma_y, 3)} px (χ²ν ${fmt(c.reduced_chi2, 2)})` : `not usable: ${c.message}`)] : null,
      plate ? [el("dt", {}, "Plate solution"), el("dd", {}, plate.n_refs ? `${plate.n_refs} reference stars, residual ${fmt(plate.rms_mas, 0)} mas per axis` : `failed: ${plate.failed || "no references"}`)] : null,
      (m?.notes || []).length ? [el("dt", {}, "Notes"), el("dd", {}, m.notes.join("; "))] : null,
      el("dt", {}, "Source"), el("dd", {}, `${prov.source || "—"} [${prov.origin || "?"}] ${prov.release || ""} ${prov.dataset_id || ""}`),
      el("dt", {}, "Retrieved"), el("dd", {}, prov.retrieved_at || "—"),
      el("dt", {}, "File"), el("dd", { class: "mono" }, `${p.file.path}\nsha256 ${p.file.sha256?.slice(0, 16)}…`),
      o.access_url ? [el("dt", {}, "Archive URL"), el("dd", { class: "mono" }, o.access_url)] : null),
    el("div", { class: "controls" },
      el("button", { class: "btn small", onclick: () => emit("goto", { ws: "time", key: o.key }) }, "Compare in Time Machine"),
      m ? el("button", { class: "btn small", onclick: () => emit("goto", { ws: "graph", focus: "meas:" + o.key }) }, "Show in Evidence Graph") : null));
}

export function stepSelection(dir) {
  if (!state.target) return;
  const inc = state.target.observations.filter((o) => o.included);
  const i = inc.findIndex((o) => o.key === state.selectedKey);
  const n = inc[Math.max(0, Math.min(inc.length - 1, i + dir))];
  if (n) emit("select", n.key);
}

export { DET_COLORS };
