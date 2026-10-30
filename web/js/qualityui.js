// Data Quality Observatory: DQ-1 checks (no score), the COMPAT-1 compatibility matrix with reason codes, observation
// metadata with a two-observation difference inspector, coverage and SEQ-1 sequences, and the ACQ-2 archive
// connectors with validated request previews (server only; nothing is sent).

import { api, STATIC } from "./api.js";
import { emit, getResearch, state } from "./state.js";
import * as S from "./session.js";
import { clear, el, fmtDate, renderToken, shortKey, toast, $ } from "./util.js";

let tab = "checks", open = null, diffA = null, diffB = null;
const OUT_LABEL = { valid: "valid under the tested rules", invalid: "invalid", incompatible: "incompatible", not_available: "data not available", not_checked: "not checked" };
const CODE_SHORT = { accepted: "✓", wavelength_mismatch: "λ", different_detectors: "", different_release: "R", unusable_measurement: "U", not_measured: "–", self: "·" };

export function setQualityTab(t) { tab = t; }

export async function renderQuality() {
  const live = renderToken("quality");
  const body = $("#quality-body");
  clear(body);
  const tabs = [["checks", "Checks"], ["matrix", "Compatibility"], ["metadata", "Metadata"], ["coverage", "Coverage & sequences"], ["connectors", "Archive connectors"]];
  body.append(el("div", { class: "tabs", role: "tablist" }, ...tabs.map(([id, label]) => {
    const b = el("button", { role: "tab", "aria-selected": id === tab ? "true" : "false", "data-qtab": id }, label);
    b.addEventListener("click", () => { tab = id; renderQuality(); });
    return b;
  })));
  if (tab === "connectors") { const cp = await connectorsPanel(); if (live()) body.append(cp); return; }
  if (!state.inv) {
    body.append(el("div", { class: "empty" }, el("h3", {}, state.target ? "Run the analysis first" : "No stored observations for this target"),
      el("p", {}, "The checks read the recorded analysis and the bundle manifest."), state.target ? el("button", { class: "btn primary", onclick: () => emit("run") }, "Run analysis") : null));
    return;
  }
  const holder = el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the checks…");
  body.append(holder);
  let r;
  try { r = await getResearch(); } catch (e) { holder.replaceWith(el("p", { class: "empty" }, e.message)); return; }
  if (state.ws !== "quality" || !live()) return;
  holder.remove();
  S.log("quality.view", "Data Quality Observatory opened");
  if (tab === "checks") body.append(checksPanel(r.quality));
  if (tab === "matrix") body.append(matrixPanel(r.compat));
  if (tab === "metadata") body.append(metadataPanel(r.compat));
  if (tab === "coverage") body.append(coveragePanel(r.compat));
}

function checksPanel(q) {
  const wrap = el("div", {});
  wrap.append(el("div", { class: "card" }, el("h3", {}, `${q.method}: ${q.checks.length} checks`),
    el("p", { class: "muted" }, `${q.note}. ` + (q.files_checked_here ? "File hashes were recomputed from the stored files." : STATIC ? "File hashes were recomputed by the server when this preview was built." : "File hashes were not recomputed here.")),
    el("div", { class: "dq-legend" }, ...q.outcomes.map((o) => el("span", { class: `dq dq-${o}` }, OUT_LABEL[o])))));
  for (const c of q.checks) {
    const isOpen = open === c.id;
    const head = el("button", { type: "button", class: "dq-row", "aria-expanded": isOpen ? "true" : "false", "data-check": c.id },
      el("span", { class: `dq dq-${c.outcome}` }, OUT_LABEL[c.outcome]), el("strong", {}, `${c.id} · ${c.name}`),
      el("span", { class: "faint" }, Object.entries(c.counts).map(([k, n]) => `${n} ${OUT_LABEL[k]}`).join(" · ")));
    head.addEventListener("click", () => { open = isOpen ? null : c.id; renderQuality(); });
    const card = el("div", { class: "card dq-card" }, head);
    if (isOpen) {
      card.append(el("dl", { class: "kv compact" }, el("dt", {}, "Rule"), el("dd", {}, c.rule), el("dt", {}, "Scope"), el("dd", {}, c.scope),
        c.note ? [el("dt", {}, "Note"), el("dd", {}, c.note)] : null),
        el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Item"), el("th", { scope: "col" }, "Outcome"), el("th", { scope: "col" }, "Detail"))),
          el("tbody", {}, ...c.items.slice(0, 200).map((i) => el("tr", {}, el("td", { class: "mono wrap" }, i.id), el("td", {}, el("span", { class: `dq dq-${i.outcome}` }, OUT_LABEL[i.outcome])), el("td", { class: "wrap" }, i.detail)))))),
        c.items.length > 200 ? el("p", { class: "faint" }, `first 200 of ${c.items.length} items`) : null);
    }
    wrap.append(card);
  }
  return wrap;
}

function matrixPanel(c) {
  const m = c.matrix;
  const n = m.keys.length;
  const cell = 9, L = 4, T = 4, W = L + n * cell + 4;
  const colors = { accepted: "#6cc6a4", wavelength_mismatch: "#e48b5c", different_detectors: "#1b2742", different_release: "#a48cf2", unusable_measurement: "#e06a6a", not_measured: "#6c7aa0", self: "#263454" };
  const svg = el("svg", { class: "chart matrix-svg", viewBox: `0 0 ${W} ${W}`, role: "img", "aria-label": `Compatibility matrix of ${n} observations; ${m.counts.accepted || 0} accepted pairs` });
  const info = el("div", { class: "card", id: "matrix-cell", "aria-live": "polite" }, el("h3", {}, "Select a cell"), el("p", { class: "muted" }, "Each cell is the WLMATCH-2 decision logged for that pair in this run."));
  m.cells.forEach((row, i) => row.forEach((code, j) => {
    const r = el("rect", { x: L + j * cell, y: T + i * cell, width: cell - 1, height: cell - 1, class: "mcell", tabindex: code === "self" || code === "different_detectors" ? null : "0" });
    r.style.fill = colors[code] || "#444";
    r.append(el("title", {}, `${m.keys[i]} × ${m.keys[j]}: ${code.replaceAll("_", " ")}`));
    const show = () => {
      const a = c.observations[i], b = c.observations[j];
      info.replaceChildren(el("h3", {}, `${shortKey(a.key)} × ${shortKey(b.key)}`), el("p", {}, el("strong", {}, code.replaceAll("_", " ")), " — ", m.codes[code] || ""),
        el("dl", { class: "kv compact" }, el("dt", {}, "Detectors"), el("dd", {}, `D${a.detector} · D${b.detector}`), el("dt", {}, "Wavelengths"),
          el("dd", {}, `${a.wavelength_um?.toFixed(4) ?? "—"} · ${b.wavelength_um?.toFixed(4) ?? "—"} µm`), el("dt", {}, "Dates"), el("dd", {}, `${fmtDate(a.t_mid_iso)} · ${fmtDate(b.t_mid_iso)}`)),
        code === "accepted" ? el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "time", key: a.key, partner: b.key }) }, "Open the pair in the Time Machine") : null,
        el("button", { class: "btn small ghost", type: "button", onclick: () => { diffA = a.key; diffB = b.key; tab = "metadata"; renderQuality(); } }, "Compare their metadata"));
    };
    r.addEventListener("click", show);
    r.addEventListener("keydown", (e) => { if (e.key === "Enter") show(); });
    svg.append(r);
  }));
  return el("div", { class: "grid-2" }, el("div", { class: "card" }, el("h3", {}, `${c.method}: ${n} measured observations`),
    el("p", { class: "muted" }, "Rows and columns are ordered by detector, then time. Compatibility is the recorded rule decision, never visual similarity."),
    svg, el("div", { class: "legend" }, ...Object.entries(m.counts).map(([k, v]) => { const i = el("i", { class: "swatch" }); i.style.background = colors[k]; return el("span", {}, i, `${k.replaceAll("_", " ")} (${v} pairs)`); }))), info);
}

function metadataPanel(c) {
  const obs = c.observations;
  const opts = (sel) => obs.map((o) => el("option", { value: o.key, selected: o.key === sel || null }, `${shortKey(o.key)} · D${o.detector} · ${fmtDate(o.t_mid_iso)}`));
  diffA = diffA || obs[0]?.key; diffB = diffB || obs[1]?.key;
  const sa = el("select", { "aria-label": "First observation" }, ...opts(diffA)), sb = el("select", { "aria-label": "Second observation" }, ...opts(diffB));
  sa.addEventListener("change", () => { diffA = sa.value; renderQuality(); });
  sb.addEventListener("change", () => { diffB = sb.value; renderQuality(); });
  const a = obs.find((o) => o.key === diffA), b = obs.find((o) => o.key === diffB);
  const fields = [...c.metadata.fields, "visit", "origin", "quality", "status"];
  const diff = a && b ? el("table", {}, el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Field"), el("th", { scope: "col" }, shortKey(a.key)), el("th", { scope: "col" }, shortKey(b.key)))),
    el("tbody", {}, ...fields.map((f) => {
      const va = a[f], vb = b[f];
      const same = JSON.stringify(va) === JSON.stringify(vb);
      const fmtv = (v) => v === null || v === undefined || v === "" ? el("span", { class: "faint" }, "not recorded") : String(v);
      return el("tr", { class: same ? "" : "diff" }, el("th", { scope: "row" }, f), el("td", { class: "wrap" }, fmtv(va)), el("td", { class: "wrap" }, fmtv(vb)));
    }))) : el("p", {}, "Choose two observations.");
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Missing metadata"),
    el("p", { class: "muted" }, `${c.metadata.n_observations} included observations; missing values are left empty and counted, never filled.`),
    el("ul", { class: "plain" }, ...Object.entries(c.metadata.missing_counts).map(([k, n]) => el("li", {}, `${k}: missing in ${n}`))),
    c.synthetic ? el("p", { class: "faint" }, "Synthetic observations have no archive URL or dataset identifier by construction.") : null,
    c.duplicates.length ? el("p", { class: "status-rejected" }, `${c.duplicates.length} file(s) appear under more than one observation key.`) : el("p", { class: "faint" }, "No duplicate files (identical SHA-256 under different keys).")),
    el("div", { class: "card" }, el("h3", {}, "Metadata difference inspector"), el("div", { class: "controls" }, sa, sb), el("div", { class: "table-wrap compare-records" }, diff)));
}

function coveragePanel(c) {
  const per = c.coverage.per_detector;
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, "Coverage by detector"),
    el("p", { class: "muted" }, `${c.visit_rule}. Gaps of at least ${c.coverage.gap_threshold_days} days between visits are listed: nothing is known about the source during them.`),
    el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Detector", "Visits", "Exposures", "Gaps (days)"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...Object.entries(per).map(([d, v]) => el("tr", {}, el("td", {}, `D${d}`), el("td", {}, String(v.visits.length)),
        el("td", {}, String(v.visits.reduce((a, x) => a + x.n, 0))), el("td", {}, v.gaps.map((g) => g.days.toFixed(0)).join(", ") || "none"))))))),
    el("div", { class: "card" }, el("h3", {}, `${c.sequence_method}: ${c.sequences.length} compatible sequences`),
      el("p", { class: "muted" }, "Every pair of members is accepted by WLMATCH-2. Open a sequence in the Time Machine to step through its frames."),
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Sequence", "Detector", "Frames", "Visits", "Span", "Note", ""].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, ...c.sequences.map((s) => el("tr", {}, el("td", { class: "mono" }, s.id), el("td", {}, `D${s.detector}`), el("td", {}, String(s.n_frames)), el("td", {}, String(s.n_visits)),
          el("td", {}, `${s.span_days.toFixed(1)} d`), el("td", { class: "wrap faint" }, s.note),
          el("td", {}, el("button", { class: "btn small", type: "button", onclick: () => emit("open-sequence", s.id) }, "Open")))))))));
}

async function connectorsPanel() {
  let reg;
  try { reg = await api.connectors(); } catch (e) { return el("p", { class: "empty" }, e.message); }
  const lc = reg.lifecycle;
  const cards = reg.connectors.map((c) => {
    const fields = Object.entries(c.params.f);
    const inputs = fields.map(([k, [spec]]) => spec.enum ? el("label", {}, k, el("select", { name: k }, ...spec.enum.map((v) => el("option", { value: v }, v))))
      : el("label", {}, k, el("input", { type: spec.t === "num" ? "number" : "text", name: k, step: "any", placeholder: spec.t === "num" ? `${spec.min} … ${spec.max}` : "" })));
    const out = el("div", { class: "conn-out", "aria-live": "polite" });
    const pv = el("button", { class: "btn small", type: "button", disabled: STATIC || null, title: STATIC ? "Previews are built by the server's acquisition code (python run.py)" : "" }, "Validate and preview the request");
    pv.addEventListener("click", async () => {
      const params = {};
      for (const [k, [spec]] of fields) {
        const v = form.querySelector(`[name="${k}"]`).value;
        params[k] = spec.t === "num" ? (v === "" ? null : Number(v)) : v;
      }
      try {
        const r = await api.connectorPreview(c.id, params);
        out.replaceChildren(r.ok ? el("div", {}, el("p", { class: "status-ok" }, "Valid. Not sent."), el("pre", { class: "json" }, JSON.stringify(r.request, null, 1)), el("p", { class: "faint" }, r.note))
          : el("ul", { class: "limits" }, ...r.errors.map((x) => el("li", { class: "status-rejected" }, x))));
      } catch (e) { toast(e.message); }
    });
    const form = el("div", { class: "params" }, ...inputs);
    return el("div", { class: "card", "data-connector": c.id }, el("h3", {}, `${c.service} `, el("span", { class: `pill ${c.usable_now ? "archive" : "offline"}` }, c.usable_now ? "reachable at last diagnosis" : "not usable now")),
      el("dl", { class: "kv compact" }, el("dt", {}, "Endpoint"), el("dd", { class: "mono wrap" }, c.endpoint), el("dt", {}, "Documented by"), el("dd", {}, c.documented_by),
        el("dt", {}, "Provides"), el("dd", {}, c.provides), el("dt", {}, "Response"), el("dd", {}, c.response), el("dt", {}, "Status"), el("dd", {}, c.usable_note)),
      form, el("div", { class: "controls" }, pv, STATIC ? el("span", { class: "faint" }, "Static preview: previews need the full application.") : null), out);
  });
  return el("div", {}, el("div", { class: "card" }, el("h3", {}, `${reg.method}: request lifecycle`),
    el("p", { class: "muted" }, `Last environment diagnosis: ${reg.diagnosed_at ? fmtDate(reg.diagnosed_at) : "never"}${reg.offline ? " · OFFLINE=1" : ""}. A preview validates the parameters and shows the exact request; it does not search.`),
    el("dl", { class: "kv compact" }, el("dt", {}, "Timeouts"), el("dd", {}, `connect ${lc.timeouts_s.connect} s, read ${lc.timeouts_s.read} s`), el("dt", {}, "Retries"), el("dd", {}, `${lc.retries}, back-off ${lc.backoff}`),
      el("dt", {}, "Rate limits"), el("dd", {}, `Retry-After ${lc.retry_after}; transient statuses ${lc.transient_status.join(", ")}`), el("dt", {}, "Size cap"), el("dd", {}, `${(lc.max_bytes / 1048576).toFixed(0)} MiB`),
      el("dt", {}, "Proxy refusal"), el("dd", {}, lc.proxy_refusal), el("dt", {}, "Offline"), el("dd", {}, lc.offline), el("dt", {}, "Provenance"), el("dd", {}, lc.provenance),
      el("dt", {}, "Integrity"), el("dd", {}, lc.integrity))), ...cards);
}
