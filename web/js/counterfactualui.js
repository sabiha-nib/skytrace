// Counterfactual Universe Lab (CF-1): change one stated thing, see what changes. The baseline is the loaded run; the
// original is never altered (the server recomputes the baseline's hash and reports whether it is intact). Every
// value is labelled observed / derived / simulated / assumed / hypothetical. Scenarios are kept in the session.

import { api, STATIC } from "./api.js";
import { getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { needRun } from "./horizonui.js";
import { clear, download, el, renderToken, toast, $ } from "./util.js";

let last = null, busy = false;

const fmtv = (v) => v === null || v === undefined ? "—" : typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toPrecision(4)) : String(v);

export async function renderCounterfactual() {
  const live = renderToken("counterfactual");
  const body = $("#counterfactual-body");
  clear(body);
  if (!state.inv) { needRun(body, "A counterfactual varies a recorded analysis: run or load one first."); return; }
  const sp = (await getSpecs()).frontier.counterfactual;
  if (!live()) return;
  const kind = el("select", { id: "cf-kind", "aria-label": "Scenario kind" }, ...sp.kinds.map((k) => el("option", { value: k }, `${k} — ${sp.labels[k]}`)));
  const inputs = el("div", { class: "controls", id: "cf-inputs" });
  const draw = () => {
    clear(inputs);
    const k = kind.value;
    if (k === "parameter") {
      const names = [...Object.keys(sp.param_bounds), ...sp.param_booleans];
      const p = el("select", { id: "cf-param", "aria-label": "Parameter" }, ...names.map((n) => el("option", { value: n }, n)));
      const v = el("input", { id: "cf-value", type: "text", "aria-label": "New value", placeholder: "value" });
      const hint = el("span", { class: "faint" });
      const upd = () => { const n = p.value; hint.textContent = sp.param_bounds[n] ? `allowed ${sp.param_bounds[n][0]}–${sp.param_bounds[n][1]}` : "true or false"; };
      p.addEventListener("change", upd); upd();
      inputs.append(p, v, hint);
    } else if (k === "exclusion") {
      inputs.append(el("span", { class: "faint" }, "Exclude detectors:"), ...[1, 2, 3, 4, 5, 6].map((d) => el("label", { class: "chk" }, el("input", { type: "checkbox", value: String(d), class: "cf-det" }), ` D${d}`)),
        state.selectedKey ? el("label", { class: "chk" }, el("input", { type: "checkbox", id: "cf-sel" }), ` the selected observation (${state.selectedKey})`) : null);
    } else if (k === "threshold") {
      const t = el("select", { id: "cf-thr", "aria-label": "Threshold" }, ...Object.entries(sp.threshold_bounds).map(([n, [lo, hi]]) => el("option", { value: n }, `${n} (${lo}–${hi})`)));
      inputs.append(t, el("input", { id: "cf-value", type: "number", step: "0.5", value: "8", "aria-label": "New threshold" }));
    } else if (k === "error_scale") {
      inputs.append(el("span", { class: "faint" }, "multiply every photometric uncertainty by"), el("input", { id: "cf-value", type: "number", step: "0.25", min: "1.25", max: String(sp.error_scale_bounds[1]), value: "2", "aria-label": "Error factor" }));
    } else inputs.append(el("span", { class: "faint" }, "Decide brightness with PAIRDIFF-1 alone (ignore the reference-star calibration)."));
  };
  kind.addEventListener("change", draw); draw();
  const run = el("button", { class: "btn primary", type: "button", id: "cf-run" }, "Run scenario");
  run.addEventListener("click", async () => {
    let spec;
    try { spec = build(kind.value, sp); } catch (e) { toast(e.message, 6000); return; }
    const rerun = ["parameter", "exclusion"].includes(spec.kind);
    if (rerun && !run.dataset.armed && !STATIC) { run.dataset.armed = "1"; run.textContent = "Confirm: re-runs the pipeline (~5–10 s)"; return; }
    delete run.dataset.armed; run.textContent = "Run scenario";
    await execute(spec);
  });
  const presets = el("div", { class: "tagrow", "aria-label": "Prepared scenarios" }, ...sp.presets.map((p) => {
    const b = el("button", { type: "button", class: "tag cf-preset" }, p.label);
    b.addEventListener("click", () => execute({ kind: p.kind, change: p.change, label: p.label }));
    return b;
  }));
  body.append(el("div", { class: "card" }, el("h3", {}, "Scenario"),
    el("p", { class: "muted" }, `Baseline: the loaded run ${state.inv.record.content_hash.slice(0, 12)}… (${state.targetId}). The original is never modified; a scenario is not an observation.` +
      (STATIC ? " Static preview: the prepared scenarios below were computed by the server when the preview was built (against the default run)." : "")),
    el("div", { class: "controls" }, kind), inputs, el("div", { class: "controls" }, run), el("h4", {}, "Prepared scenarios"), presets),
    el("div", { id: "cf-result" }), lineage());
  if (last && last.scenario?.baseline_hash === state.inv.record.content_hash) $("#cf-result").append(resultView(last));
}

function build(kind, sp) {
  if (kind === "parameter") {
    const n = $("#cf-param").value, raw = $("#cf-value").value.trim();
    const v = sp.param_booleans.includes(n) ? (raw === "true" ? true : raw === "false" ? false : null) : Number(raw);
    if (v === null || (typeof v === "number" && !Number.isFinite(v)) || raw === "") throw new Error("Enter a value for the parameter");
    return { kind, change: { [n]: v } };
  }
  if (kind === "exclusion") {
    const dets = [...document.querySelectorAll(".cf-det:checked")].map((x) => Number(x.value));
    const keys = $("#cf-sel")?.checked ? [state.selectedKey] : [];
    if (!dets.length && !keys.length) throw new Error("Choose something to exclude");
    return { kind, change: { ...(dets.length ? { detectors: dets } : {}), ...(keys.length ? { keys } : {}) } };
  }
  if (kind === "threshold") return { kind, change: { [$("#cf-thr").value]: Number($("#cf-value").value) } };
  if (kind === "error_scale") return { kind, change: { photometric_error_factor: Number($("#cf-value").value) } };
  return { kind, change: { variability_method: "PAIRDIFF-1" } };
}

async function execute(spec) {
  if (busy) return;
  busy = true;
  const out = $("#cf-result");
  clear(out).append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Running the scenario against the baseline…"));
  try {
    const r = await api.counterfactual(state.targetId, state.inv.investigation_id, spec);
    last = r;
    await S.update("scenario.run", `Counterfactual (${r.scenario.kind}): ${spec.label || JSON.stringify(r.scenario.change)} — ` +
      (r.comparison.some((x) => x.changed && x.metric.startsWith("category.")) ? "an outcome changed" : "no outcome changed"), (s) => {
      const keep = { scenario: r.scenario, scenario_hash: r.scenario_hash, value_label: r.value_label, baseline_hash: r.baseline.content_hash,
        counterfactual_hash: r.counterfactual.content_hash, categories: r.counterfactual.categories, changed: r.comparison.filter((x) => x.changed).map((x) => x.metric),
        recorded_at_build: !!r.recorded_at_build };
      s.scenarios = [...(s.scenarios || []).filter((x) => x.scenario_hash !== r.scenario_hash), keep].slice(-40);
      return s;
    }, r.scenario_hash.slice(0, 16));
    clear(out).append(resultView(r));
    $("#cf-lineage")?.replaceWith(lineage());
  } catch (e) { clear(out).append(el("p", { class: "withheld" }, e.message)); }
  busy = false;
}

function resultView(r) {
  const exp = el("button", { class: "btn small", type: "button", id: "cf-export" }, "Export comparison (JSON)");
  exp.addEventListener("click", async () => { if (await download(`skytrace-counterfactual-${r.scenario_hash.slice(0, 12)}.json`, JSON.stringify(r, null, 1), "application/json")) toast("Comparison exported"); });
  const rows = r.comparison;
  return el("div", { class: "card cf-result" }, el("h3", {}, `Result · ${r.scenario.kind}`),
    el("p", {}, el("span", { class: "pill sim" }, r.value_label), r.recorded_at_build ? el("span", { class: "pill" }, "recorded when the preview was built") : null,
      el("span", { class: `pill ${r.baseline.intact ? "archive" : "none"}` }, r.baseline.intact ? "baseline intact (hash recomputed)" : "baseline hash mismatch")),
    el("ul", { class: "plain" }, ...r.explanation.map((x) => el("li", {}, x))),
    el("div", { class: "table-wrap" }, el("table", { class: "cf-table" }, el("thead", {}, el("tr", {}, ...["Output", "Baseline (derived from observations)", `Scenario (${r.value_label.split(" ")[0]})`, ""].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...rows.map((x) => el("tr", { class: x.changed ? "changed" : "" }, el("th", { scope: "row" }, x.metric), el("td", {}, fmtv(x.baseline)), el("td", {}, fmtv(x.counterfactual)),
        el("td", {}, x.changed ? "changed" : "same")))))),
    r.notes.length ? el("ul", { class: "limits" }, ...r.notes.map((n) => el("li", {}, n))) : null,
    el("p", { class: "faint" }, r.caveat),
    el("dl", { class: "kv compact" }, el("dt", {}, "Baseline"), el("dd", { class: "mono" }, r.baseline.content_hash), el("dt", {}, "Scenario"), el("dd", { class: "mono" }, r.scenario_hash),
      el("dt", {}, "Change"), el("dd", { class: "mono" }, JSON.stringify(r.scenario.change)),
      el("dt", {}, "Labels"), el("dd", {}, Object.entries(r.legend).map(([k, v]) => `${k}: ${v}`).join(" · "))),
    el("div", { class: "controls" }, exp));
}

function lineage() {
  const sc = (state.session?.scenarios || []).filter((x) => x.scenario?.target_id === state.targetId);
  return el("div", { class: "card", id: "cf-lineage" }, el("h3", {}, "Scenarios in this session"),
    sc.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["Scenario", "Kind", "Baseline", "Outcomes", "Changed"].map((h) => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...sc.slice().reverse().map((x) => el("tr", {}, el("td", { class: "mono" }, x.scenario_hash.slice(0, 12)), el("td", {}, `${x.scenario.kind} ${JSON.stringify(x.scenario.change)}`),
        el("td", { class: "mono" }, x.baseline_hash.slice(0, 12)), el("td", {}, Object.entries(x.categories || {}).map(([q, c]) => `${q}: ${c}`).join("; ")),
        el("td", {}, x.changed.filter((m) => m.startsWith("category.")).join(", ") || "no outcome"))))))
      : el("p", { class: "muted" }, "No scenario yet. Each scenario you run is kept here with the baseline it varied."));
}
