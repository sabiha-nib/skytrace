// Research Protocol (PROTOCOL-1) and Blind Analysis (BLINDLAB-1).
// A protocol records the question, hypotheses, inputs, methods, exclusions, parameters, evaluation criteria (your expected
// outcome per question), robustness plans and limitations. Locking it stores a content hash and the time, and whether any
// result had already been visible — a protocol locked after results were visible is labelled as such and is never called
// a pre-analysis plan. Amendments are appended with a reason, never overwritten. This is a local record, not a registry
// submission (not preregistration).
// Blind analysis hides outcome categories, significances and the motion fit everywhere in the interface until a documented
// unblinding. It prevents accidental disclosure while you work; it is not access control (the record is in this browser).

import { emit, state } from "./state.js";
import { digest } from "./canon.js";
import * as S from "./session.js";
import { download, el, renderToken, toast, $, clear } from "./util.js";
import { kv, outcomePill, table } from "./epiui.js";

export const BLIND_ALLOWED = ["protocol", "explorer", "quality", "notebook"];
export const HIDDEN_FIELDS = ["outcome categories and statements (assessment)", "pair significances z and z_cal", "motion fit and its significance",
  "everything derived from them (hypotheses, ledger, boundary, story, copilot answers)"];
const QUESTIONS = ["data_quality", "motion", "variability"];
const CATS = { data_quality: ["usable", "partially_usable", "instrumental", "insufficient_data"],
  motion: ["motion_detected", "motion_inconsistent", "no_motion_at_sensitivity", "registration_limited", "measurement_failed", "insufficient_data"],
  variability: ["variability_candidate", "no_variability_at_sensitivity", "spectral_difference_only", "calibration_limited", "insufficient_data"] };
const PARAMS = ["aperture_radius_px", "fit_half_size_px", "wavelength_tolerance_channels", "epoch_gap_days", "epoch_clip_sigma", "apply_parallax"];

export const blindActive = () => !!state.session?.blind?.active;
const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
const body0 = (p) => { const { locked, amendments, ...rest } = p; return rest; };   // the locked content excludes the lock and amendments

async function hiddenDigest() {
  if (!state.inv) return null;
  const a = state.inv.record.events.find((e) => e.step === "assess")?.data?.outcomes || [];
  const v = state.inv.record.events.find((e) => e.step === "variability")?.data?.pairs || [];
  const f = state.inv.record.events.find((e) => e.step === "astrometry")?.data?.fit || null;
  return digest({ run: state.inv.record.content_hash, outcomes: a.map((o) => [o.question, o.category]), z: v.map((p) => [p.a, p.b, p.z]), fit: f ? [f.pm_xi_mas_yr, f.pm_eta_mas_yr] : null });
}

export async function renderProtocol() {
  const live = renderToken("protocol");
  const body = $("#protocol-body");
  clear(body);
  const p = state.session?.protocol || null;
  if (!live()) return;
  body.append(protocolCard(p), await blindCard(p));
  if (p) body.append(comparison(p));
}

function field(id, label, value, multiline) {
  const inp = multiline ? el("textarea", { id, rows: "2", "aria-label": label }, value || "") : el("input", { type: "text", id, value: value || "", "aria-label": label });
  return [el("label", { for: id }, label), inp];
}

function protocolCard(p) {
  const locked = !!p?.locked;
  const v = p || { question: state.session?.question?.text || "", primary_hypothesis: "", inputs: state.targetId ? [`target ${state.targetId}`, "detectors D1–D6"] : [], alternatives: [], methods: ["WLMATCH-2", "PAIRDIFF-1", "PAIRDIFF-2", "CALCHECK-1", "LINFIT-EPOCH-1", "ASSESS-2"],
    exclusion: ["exposures refused by the flag policy (FLAGPOL-1)", "pairs rejected by WLMATCH-2"], parameters: {}, evaluation: {}, robustness: ["stability check (STAB-1)"], limitations: [] };
  const f = {};
  const grid = el("div", { class: "proto-grid" });
  for (const [k, label, multi] of [["question", "Research question", true], ["primary_hypothesis", "Primary hypothesis", true]]) {
    const [l, i] = field(`pr-${k}`, label, v[k], multi); f[k] = i; grid.append(l, i);
  }
  for (const [k, label] of [["inputs", "Selected inputs (one per line: target, detectors, release…)"], ["alternatives", "Alternative hypotheses (one per line)"], ["methods", "Planned methods (one per line)"], ["exclusion", "Exclusion criteria (one per line)"],
    ["robustness", "Planned robustness tests (one per line)"], ["limitations", "Known limitations (one per line)"]]) {
    const [l, i] = field(`pr-${k}`, label, (v[k] || []).join("\n"), true); f[k] = i; grid.append(l, i);
  }
  const params = el("div", { class: "controls" }, ...PARAMS.map((k) => {
    const i = el("input", { type: "text", id: `pr-param-${k}`, value: v.parameters?.[k] ?? "", "aria-label": `planned ${k}`, size: "6" });
    f[`param:${k}`] = i; return el("label", { class: "small" }, `${k} `, i);
  }));
  const evals = el("div", { class: "controls" }, ...QUESTIONS.map((q) => {
    const s = el("select", { id: `pr-eval-${q}`, "aria-label": `expected ${q} outcome` }, el("option", { value: "" }, "no prediction"), ...CATS[q].map((c) => el("option", { value: c, selected: v.evaluation?.[q] === c || null }, c)));
    f[`eval:${q}`] = s; return el("label", { class: "small" }, `${q}: `, s);
  }));
  if (locked) Object.values(f).forEach((i) => i.setAttribute("disabled", ""));
  const read = () => ({ schema: "skytrace.protocol/1", created_at: p?.created_at || nowIso(), question: f.question.value.slice(0, 500), primary_hypothesis: f.primary_hypothesis.value.slice(0, 500),
    inputs: lines(f.inputs), alternatives: lines(f.alternatives), methods: lines(f.methods), exclusion: lines(f.exclusion), robustness: lines(f.robustness), limitations: lines(f.limitations),
    parameters: Object.fromEntries(PARAMS.map((k) => [k, parse(f[`param:${k}`].value)]).filter(([, x]) => x !== null)),
    evaluation: Object.fromEntries(QUESTIONS.map((q) => [q, f[`eval:${q}`].value]).filter(([, x]) => x)) });
  const save = el("button", { class: "btn", type: "button", id: "pr-save", disabled: locked || null }, "Save draft");
  save.addEventListener("click", async () => {
    await S.update("protocol.save", "Protocol draft saved", (s) => { s.protocol = { ...read(), locked: null, amendments: [] }; return s; });
    toast("Draft saved (not locked)"); renderProtocol();
  });
  const lock = el("button", { class: "btn primary", type: "button", id: "pr-lock", disabled: locked || null }, "Lock the protocol");
  lock.addEventListener("click", async () => {
    const draft = read();
    if (!draft.question || !draft.primary_hypothesis) { toast("State the question and the primary hypothesis first"); return; }
    if (!lock.dataset.armed) { lock.dataset.armed = "1"; lock.textContent = "Confirm: lock (changes afterwards become amendments)"; return; }
    const visible = !!state.inv && !blindActive();
    const h = await digest(draft);
    await S.update("protocol.lock", `Protocol locked (${h.slice(0, 12)}…)${visible ? " after results were visible" : ""}`, (s) => {
      s.protocol = { ...draft, locked: { at: nowIso(), hash: h, results_visible: visible }, amendments: [] }; return s;
    }, h);
    toast(visible ? "Locked — labelled as locked after results were visible" : "Locked before any result was visible"); renderProtocol();
  });
  const amend = locked ? amendForm(p) : null;
  const exp = el("button", { class: "btn small", type: "button", id: "pr-export", disabled: !p || null }, "Export protocol (JSON)");
  exp.addEventListener("click", async () => { if (await download("skytrace-protocol.json", JSON.stringify(p, null, 1), "application/json")) toast("Protocol exported"); });
  const status = !p ? el("p", { class: "muted" }, "No protocol yet. Write one before analysing to separate planned choices from choices made after seeing results.")
    : locked ? el("p", { id: "pr-status" }, el("span", { class: `pill ${p.locked.results_visible ? "out-warn" : "out-ok"}` }, p.locked.results_visible ? "locked after results were visible" : "locked before results were visible"),
      ` ${p.locked.at} · hash `, el("span", { class: "mono" }, p.locked.hash.slice(0, 16) + "…"), ` · ${p.amendments.length} amendment(s)`)
      : el("p", { id: "pr-status" }, el("span", { class: "pill" }, "draft"), " not locked");
  return el("div", { class: "card" }, el("h3", {}, "Research protocol"), el("p", { class: "faint small" }, "A local record of planned choices. It is not a registry submission and not a formal preregistration."),
    status, grid, el("h4", {}, "Planned parameters"), params, el("h4", {}, "Evaluation criteria — your expected outcome per question"), evals,
    el("div", { class: "controls" }, save, lock, exp), amend);
}

function amendForm(p) {
  const fieldSel = el("select", { id: "am-field", "aria-label": "Field to amend" }, ...["question", "primary_hypothesis", "inputs", "alternatives", "methods", "exclusion", "robustness", "limitations",
    ...PARAMS.map((k) => `parameters.${k}`), ...QUESTIONS.map((q) => `evaluation.${q}`)].map((x) => el("option", { value: x }, x)));
  const val = el("input", { type: "text", id: "am-value", placeholder: "New value", "aria-label": "New value" });
  const why = el("input", { type: "text", id: "am-reason", placeholder: "Reason for the amendment", "aria-label": "Reason" });
  const go = el("button", { class: "btn", type: "button", id: "am-add" }, "Append amendment");
  go.addEventListener("click", async () => {
    if (!why.value.trim()) { toast("Give the reason for the amendment"); return; }
    const visible = !!state.inv && !blindActive();
    const [top, sub] = fieldSel.value.split(".");
    const from = sub ? (p[top] || {})[sub] ?? null : p[top];
    await S.update("protocol.amend", `Protocol amended: ${fieldSel.value} (${visible ? "results visible" : "results hidden"})`, (s) => {
      s.protocol = { ...s.protocol, amendments: [...(s.protocol.amendments || []), { at: nowIso(), field: fieldSel.value, from, to: val.value.slice(0, 500), reason: why.value.slice(0, 500),
        results_visible: visible }] }; return s;
    });
    toast("Amendment appended; the locked text is unchanged"); renderProtocol();
  });
  return el("div", {}, el("h4", {}, "Amendments (append-only)"),
    p.amendments.length ? table(["When", "Field", "From", "To", "Reason", "Results visible"], p.amendments.map((a) => el("tr", {}, el("td", { class: "small" }, a.at), el("td", {}, a.field),
      el("td", { class: "small" }, JSON.stringify(a.from)), el("td", { class: "small" }, a.to), el("td", { class: "small" }, a.reason), el("td", {}, a.results_visible ? "yes (post-hoc)" : "no")))) : el("p", { class: "faint" }, "None."),
    el("div", { class: "controls" }, fieldSel, val, why, go));
}

async function blindCard(p) {
  const b = state.session?.blind;
  const est = el("button", { class: "btn primary", type: "button", id: "blind-start", disabled: b?.active || null }, "Establish a blind");
  est.addEventListener("click", async () => {
    if (!est.dataset.armed) { est.dataset.armed = "1"; est.textContent = "Confirm: hide outcomes everywhere until unblinding"; return; }
    const h = await hiddenDigest();
    await S.update("blind.establish", "Blind established" + (h ? ` (commitment ${h.slice(0, 12)}…)` : ""), (s) => {
      s.blind = { active: true, hidden: HIDDEN_FIELDS, configured_by: "this browser session (Skytrace has no user accounts)", established_at: nowIso(), commitment: h,
        run: state.inv?.record.content_hash || null, protocol_hash: s.protocol?.locked?.hash || null, unblinded_at: null }; return s;
    });
    emit("blind-changed"); toast("Blind established: outcomes are hidden"); renderProtocol();
  });
  const conf = el("input", { type: "text", id: "unblind-confirm", placeholder: "type UNBLIND", "aria-label": "Type UNBLIND to confirm" });
  const un = el("button", { class: "btn", type: "button", id: "blind-end", disabled: !b?.active || null }, "Unblind");
  un.addEventListener("click", async () => {
    if (!p?.locked) { toast("Lock the protocol before unblinding, so the planned criteria are fixed"); return; }
    if (conf.value.trim() !== "UNBLIND") { toast("Type UNBLIND to confirm"); conf.focus(); return; }
    const h = await hiddenDigest();
    await S.update("blind.unblind", `Unblinded against protocol ${p.locked.hash.slice(0, 12)}…` + (b.commitment && h !== b.commitment ? " (hidden content changed since the blind was established)" : ""), (s) => {
      s.blind = { ...s.blind, active: false, unblinded_at: nowIso(), unblind_protocol_hash: p.locked.hash, commitment_at_unblinding: h,
        commitment_matches: b.commitment ? h === b.commitment : null }; return s;
    });
    emit("blind-changed"); toast("Unblinded; compare the outcomes with your locked criteria below"); renderProtocol();
  });
  return el("div", { class: "card", id: "blind-card" }, el("h3", {}, "Blind analysis"),
    el("p", { class: "muted" }, "Optional. While a blind is active the interface hides outcome categories, significances and the motion fit everywhere — workspaces that would show them are covered, the copilot is paused and the wavelength ruler stops emphasising significant pairs. Use it to fix analysis choices and evaluation criteria before seeing outcomes. It is a workflow aid, not access control: the record is in this browser. Not every analysis benefits from blinding."),
    kv([["State", b?.active ? el("span", { class: "pill out-warn", id: "blind-state" }, "blind active") : el("span", { class: "pill", id: "blind-state" }, b?.unblinded_at ? "unblinded" : "no blind")],
      b ? ["Hidden", el("ul", { class: "plain small" }, ...b.hidden.map((x) => el("li", {}, x)))] : null, b ? ["Configured by", b.configured_by] : null,
      b ? ["Established", b.established_at] : null, b?.commitment ? ["Commitment (SHA-256 of the hidden values)", el("span", { class: "mono" }, b.commitment.slice(0, 24) + "…")] : null,
      b?.unblinded_at ? ["Unblinded", `${b.unblinded_at} against protocol ${String(b.unblind_protocol_hash).slice(0, 12)}…; commitment ${b.commitment_matches === null ? "not set" : b.commitment_matches ? "matches" : "DIFFERS"}`] : null,
      ["Allowed while blind", BLIND_ALLOWED.join(", ")]]),
    el("div", { class: "controls" }, est, conf, un));
}

function comparison(p) {
  if (blindActive()) return el("div", { class: "card" }, el("h3", {}, "Planned versus actual"), el("p", { class: "muted" }, "Hidden while the blind is active."));
  if (!state.inv) return el("div", { class: "card" }, el("h3", {}, "Planned versus actual"), el("p", { class: "muted" }, "Run the analysis to compare."));
  const rp = state.inv.record.parameters;
  const out = Object.fromEntries((state.inv.record.events.find((e) => e.step === "assess")?.data?.outcomes || []).map((o) => [o.question, o.category]));
  const am = new Set((p.amendments || []).map((a) => a.field));
  const rows = [
    ...PARAMS.filter((k) => k in (p.parameters || {})).map((k) => el("tr", {}, el("th", { scope: "row" }, k), el("td", {}, JSON.stringify(p.parameters[k])), el("td", {}, JSON.stringify(rp[k])),
      el("td", {}, outcomePill(JSON.stringify(p.parameters[k]) === JSON.stringify(rp[k]) ? "pass" : "warning"), am.has(`parameters.${k}`) ? " amended" : ""))),
    ...QUESTIONS.filter((q) => p.evaluation?.[q]).map((q) => el("tr", {}, el("th", { scope: "row" }, `expected ${q}`), el("td", {}, p.evaluation[q]), el("td", {}, out[q] || "—"),
      el("td", {}, outcomePill(p.evaluation[q] === out[q] ? "pass" : "warning"), p.evaluation[q] === out[q] ? " as expected" : " differs from expectation"))),
  ];
  return el("div", { class: "card", id: "pr-compare" }, el("h3", {}, "Planned versus actual"),
    el("p", { class: "muted" }, "Choices recorded in the protocol before results (or marked post-hoc when results were visible) compared with what the run used and found. A difference is information, not an error."),
    rows.length ? table(["Item", "Planned", "Actual", "Match"], rows, { id: "pr-compare-table" }) : el("p", { class: "faint" }, "The protocol states no parameters or expected outcomes to compare."));
}

const lines = (t) => t.value.split("\n").map((x) => x.trim()).filter(Boolean).slice(0, 30).map((x) => x.slice(0, 300));
function parse(x) {
  const t = String(x).trim();
  if (!t) return null;
  if (t === "true" || t === "false") return t === "true";
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}
