// Skytrace application shell: target loading, workspace switching, events, URL state.

import { api, STATIC } from "./api.js";
import { deriveModel, emit, emptyContext, on, sanitizeContext, readHash, state, writeHash } from "./state.js";
import { renderRuler } from "./ruler.js";
import { loadSelected, renderExplorer, stepSelection } from "./explorer.js";
import { renderTime, stop as stopBlink, toggleBlink } from "./timemachine.js";
import { renderLab, setLabTab } from "./lab.js";
import { focusGraph, renderGraph } from "./graph.js";
import { renderRecords } from "./records.js";
import { ask, bindCopilot, refreshCopilot, resetCopilot } from "./copilot.js";
import { renderDiscovery } from "./discovery.js";
import { renderArena } from "./arena.js";
import { bindPalette, closeHelp, closePalette, observationCommands, openHelp, openPalette } from "./palette.js";
import { renderCommand } from "./commandcenter.js";
import { renderPlanner, setPlannerQuestion } from "./plannerui.js";
import { renderExperiments, setTargetLoader } from "./experimentsui.js";
import { renderQuality, setQualityTab } from "./qualityui.js";
import { renderRadar } from "./radarui.js";
import { renderNotebook } from "./notebook.js";
import { renderLedger, setLedgerTab } from "./ledgerui.js";
import { openSequence } from "./timemachine.js";
import * as S from "./session.js";
import { bindSessions, closeSessions, openSessions, renderSessionBox } from "./sessionsui.js";
import { setHooks } from "./executor.js";
import { renderHorizon } from "./horizonui.js";
import { renderCounterfactual } from "./counterfactualui.js";
import { renderSynthetic } from "./synthobsui.js";
import { renderAdversarial, setAdversarialTab } from "./adversarialui.js";
import { renderAutopilot } from "./autopilotui.js";
import { renderAtlas } from "./atlasui.js";
import { renderKnowledge } from "./knowledgeui.js";
import { renderReview, setReviewTab } from "./reviewui.js";
import { renderReasoning, setReasoningTab } from "./reasoningui.js";
import { renderCompiler, setCompilerTab } from "./compilerui.js";
import { renderClaims, setClaimsTab } from "./claimsui.js";
import { renderDebugger, setDebuggerTab } from "./debuggerui.js";
import { renderModels } from "./modelsui.js";
import { renderUflow } from "./uflowui.js";
import { renderFuture } from "./futureui.js";
import { renderDecide, setDecideTab } from "./decideui.js";
import { renderNegative } from "./negativeui.js";
import { renderIntegrity } from "./integrityui.js";
import { BLIND_ALLOWED, blindActive, renderProtocol } from "./protocolui.js";
import { renderArgue } from "./argueui.js";
import { renderIntel, setIntelPanel } from "./intelui.js";
import { $, $$, el, fmtDate, toast } from "./util.js";

const RENDER = { command: renderCommand, discovery: renderDiscovery, explorer: renderExplorer, time: renderTime, lab: renderLab, arena: renderArena,
                 graph: renderLedger, records: renderRecords, planner: renderPlanner, experiments: renderExperiments, quality: renderQuality,
                 radar: renderRadar, notebook: renderNotebook, horizon: renderHorizon, counterfactual: renderCounterfactual, synthetic: renderSynthetic,
                 adversarial: renderAdversarial, autopilot: renderAutopilot, atlas: renderAtlas, knowledge: renderKnowledge, review: renderReview,
                 reasoning: renderReasoning, compiler: renderCompiler, claims: renderClaims, debugger: renderDebugger, models: renderModels, uflow: renderUflow,
                 future: renderFuture, decide: renderDecide, negative: renderNegative, integrity: renderIntegrity, protocol: renderProtocol, argue: renderArgue, intel: renderIntel };
const WS_LABEL = { command: "Command Center", explorer: "Sky Explorer", time: "Time Machine", quality: "Data Quality Observatory", planner: "Investigation Planner",
                   discovery: "Discovery Engine", lab: "Discovery Lab", arena: "Hypothesis Arena", experiments: "Experiment Studio", graph: "Evidence Ledger",
                   radar: "Discovery Radar", notebook: "Research Notebook", records: "Vault & Reports", horizon: "Discovery Horizon",
                   counterfactual: "Counterfactual Lab", synthetic: "Synthetic Observatory", adversarial: "Adversarial Science Lab", autopilot: "Research Autopilot",
                   atlas: "Cosmic Atlas", knowledge: "Knowledge Atlas", review: "Review Room & Discovery Story", reasoning: "Reasoning Graph & Lineage-X",
                   compiler: "Scientific Compiler & Method Genome", claims: "Claims: Boundary, Stress Test & Blindspots", debugger: "Scientific Debugger",
                   models: "Model Arena", uflow: "Uncertainty Flow", future: "FutureLab", decide: "Questions & Next Steps", negative: "Negative Space",
                   integrity: "Integrity Firewall", protocol: "Protocol & Blind Analysis", argue: "Reasoning Lab", intel: "Scientific Intelligence" };
const LEVELS = ["explore", "investigate", "research"];
const minLevel = (ws) => document.querySelector(`.nav button[data-ws=${ws}]`)?.dataset.minLevel || "explore";
const visibleWs = () => $$(".nav button[data-ws]").map((b) => b.dataset.ws).filter((ws) => LEVELS.indexOf(minLevel(ws)) <= LEVELS.indexOf(state.level));
const LOGGED = { arena: "arena.view", radar: null, quality: null, graph: null, planner: "planner.view", notebook: "notebook.view", experiments: "experiments.view",
                 counterfactual: "counterfactual.view", adversarial: "adversarial.view", review: "review.view", synthetic: "synthetic.view", autopilot: "autopilot.view",
                 compiler: "compiler.view", claims: "claims.view", debugger: "debugger.view", reasoning: "reasoning.view", intel: "intel.view" };

/** Render a workspace, unless a blind analysis is active and the workspace would show hidden results (BLINDLAB-1). The cover
 *  is drawn over the section; the workspace's own renderer is not called, so nothing hidden is computed or drawn. */
function renderWs(ws) {
  const sec = $(`#ws-${ws}`);
  sec?.querySelector(".blind-cover")?.remove();
  sec?.classList.remove("blinded");
  if (blindActive() && !BLIND_ALLOWED.includes(ws)) {
    sec?.classList.add("blinded");
    sec?.prepend(el("div", { class: "blind-cover card", role: "status" }, el("h3", {}, "Hidden by the blind analysis"),
      el("p", {}, `${WS_LABEL[ws]} would show outcomes, significances or results derived from them, which are hidden until you unblind.`),
      el("p", { class: "muted" }, `Open while blind: ${BLIND_ALLOWED.map((w) => WS_LABEL[w]).join(", ")}.`),
      el("button", { class: "btn", type: "button", onclick: () => setWorkspace("protocol") }, "Go to Protocol & Blind Analysis")));
    return;
  }
  RENDER[ws]();
}

// The discovery loop. Each step names where it happens; "Explain" opens the copilot.
const LOOP = [["Explore", "command"], ["Observe", "explorer"], ["Compare", "time"], ["Detect", "lab"], ["Test", "arena"],
              ["Explain", "copilot"], ["Verify", "graph"], ["Preserve", "notebook"], ["Share", "records"]];

function renderLoop() {
  const nav = $("#loop");
  nav.replaceChildren(el("span", { class: "loop-label" }, "Discovery loop"), ...LOOP.map(([label, ws], i) => {
    const current = ws === state.ws || (ws === "copilot" && $("#app").classList.contains("copilot-open-narrow"));
    const b = el("button", { type: "button", class: "loop-step", "aria-current": current ? "step" : null,
                             title: ws === "copilot" ? "Ask the research copilot" : `Go to ${WS_LABEL[ws]}` },
      el("span", { class: "n" }, String(i + 1)), label);
    b.addEventListener("click", () => {
      if (ws === "copilot") { setCopilotOpen(true); if (!$("#copilot").offsetParent) toast("The copilot is in the panel on the right."); return; }
      if (label === "Observe") { setWorkspace("explorer"); setTimeout(() => $("#explorer-body table")?.scrollIntoView({ block: "start" }), 50); return; }
      if (label === "Share") { setWorkspace("records"); setTimeout(() => $("#studio")?.scrollIntoView({ block: "start" }), 50); return; }
      setWorkspace(ws);
    });
    return b;
  }));
}

function setLevel(level, persist = true) {
  if (!["explore", "investigate", "research"].includes(level)) level = "investigate";
  state.level = level;
  document.body.dataset.level = level;
  $$(".level-switch button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.level === level)));
  if (persist) { try { localStorage.setItem("skytrace.level", level); } catch { /* per-viewer convenience only */ } }
}

function setWorkspace(ws, { push = true } = {}) {
  if (!RENDER[ws]) ws = "command";
  const need = minLevel(ws);
  if (LEVELS.indexOf(need) > LEVELS.indexOf(state.level)) {
    setLevel(need);
    toast(`Switched to the ${need[0].toUpperCase() + need.slice(1)} level to open the ${WS_LABEL[ws]}.`);
  }
  if (LOGGED[ws]) S.log(LOGGED[ws], `${WS_LABEL[ws]} opened`);
  if (state.ws === "time" && ws !== "time") stopBlink();
  state.ws = ws;
  $$(".nav button").forEach((b) => b.setAttribute("aria-current", b.dataset.ws === ws ? "page" : "false"));
  $$(".workspace").forEach((s) => s.classList.toggle("active", s.id === `ws-${ws}`));
  $(`.nav button[data-ws=${ws}]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  renderWs(ws);
  renderLoop();
  writeHash(push);
}

function renderHeader() {
  const t = state.targets.find((x) => x.target_id === state.targetId);
  const pill = $("#data-pill");
  if (!t) { pill.className = "pill none"; pill.textContent = "No target"; }
  else if (t.kind === "synthetic") { pill.className = "pill syn"; pill.textContent = "Synthetic test data"; }
  else if (t.kind === "archive") {
    const rel = [...new Set((state.target?.observations || []).map((o) => o.release))].join(", ");
    pill.className = "pill archive"; pill.textContent = `Archive data${rel ? " · " + rel : ""}`;
  } else { pill.className = "pill none"; pill.textContent = "No data yet"; }
  const s = state.status;
  $("#offline-pill").hidden = !s?.offline || STATIC;
  $("#preview-pill").hidden = !STATIC;
  const mp = $("#model-pill");
  if (s?.meta?.configured) {
    mp.textContent = `Copilot: Meta ${s.meta.model}`;
    mp.title = s.meta.smoke_test ? `Smoke test ${s.meta.smoke_test.all_passed ? "passed" : "failed"} at ${s.meta.smoke_test.run_at}` : "Not yet smoke-tested (python scripts/meta_smoke_test.py)";
  } else {
    mp.textContent = "Copilot: local assistant";
    mp.title = STATIC ? "Static preview: answers are the local assistant's, recorded at build time; no model is called"
      : s?.offline ? "Offline mode: no model calls are made" : "No Meta API key configured; answers come from the deterministic local assistant";
  }
  $("#run-btn").disabled = !state.target;
  $("#run-btn").textContent = state.inv ? "Re-run analysis" : "Run analysis";
  const gb = $("#global-banner");
  gb.replaceChildren();
  if (t?.kind === "synthetic") gb.append(el("div", { class: "banner syn" }, el("strong", {}, "Synthetic test data."),
    el("p", {}, "This target and its images were generated by code to exercise the pipeline end to end. Nothing here is an astronomical observation or result.")));
  else if (t?.kind === "archive" && !t.verified) gb.append(el("div", { class: "banner warn" }, el("strong", {}, "This data bundle failed verification."),
    el("p", {}, (t.problems || []).join("; "))));
  $("#nav-foot").replaceChildren(el("div", {}, `Skytrace ${s?.version || ""}${STATIC ? ` · preview ${s?.commit || ""}` : ""}`),
    el("div", {}, `FITS reader: ${s?.astropy ? "astropy" : "native"}`),
    el("div", {}, STATIC ? `Built ${fmtDate(s?.built_at)}` : s?.offline ? "Offline mode" : "No archive calls from the app"));
}

async function loadTarget(tid, { keepSelection = null, push = true } = {}) {
  if (state.targetId !== tid) state.context = state.session ? state.context : emptyContext();   // a session's context spans its targets
  state.discovery = null; state.research = null; state.frontier = null; state.epistemic = null; state.intelligence = null; state.corpus = null;
  state.targetId = tid;
  state.target = null; state.inv = null; state.model = null; state.prevInv = null; state.selectedKey = null; state.partnerKey = null;
  resetCopilot();
  const t = state.targets.find((x) => x.target_id === tid);
  if (t?.kind) {
    try { state.target = await api.target(tid); } catch (e) { toast(e.message); }
  }
  if (state.target) {
    const inc = state.target.observations.filter((o) => o.included);
    state.selectedKey = keepSelection && inc.some((o) => o.key === keepSelection) ? keepSelection : inc[0]?.key || null;
  }
  $("#target-select").value = tid;
  renderHeader(); renderRuler(); refreshCopilot();
  renderWs(state.ws);
  writeHash(push);
  // The preview's default analysis is already computed, so open each target in its working state.
  if (STATIC && state.target) await runAnalysis(undefined, { quiet: true });
}

async function runAnalysis(params, { quiet = false } = {}) {
  if (!state.target) return;
  const btn = $("#run-btn");
  btn.disabled = true; btn.replaceChildren(el("span", { class: "spinner" }), "Analysing…");
  try {
    const prev = state.inv ? { record: state.inv.record, model: state.model } : null;
    const r = await api.analyze(state.targetId, params || {});
    state.prevInv = prev;
    state.inv = r; state.model = deriveModel(r.record); state.discovery = null; state.research = null; state.frontier = null; state.epistemic = null; state.intelligence = null; state.corpus = null;
    if (state.session) S.attachRun(r, Object.keys(params || {}).length ? "re-run with changed parameters" : "analysis");
    const o = state.model.outcomes.map((x) => `${x.question.replace("_", " ")}: ${x.category.replaceAll("_", " ")}`).join(" · ");
    if (!quiet) toast(`Analysis complete. ${o}`, 5000);
    if (prev) $("#thread").append(el("p", { class: "faint" }, "New analysis run; later answers refer to it."));
  } catch (e) { toast(STATIC ? e.message : `Analysis failed: ${e.message}`, 7000); }
  renderHeader(); renderRuler(); refreshCopilot();
  renderWs(state.ws);
}

// On narrow screens the copilot is an overlay panel: Escape or Close dismisses it and focus returns to the toggle.
function setCopilotOpen(open, focus = true) {
  $("#app").classList.toggle("copilot-open-narrow", open);
  $("#copilot-toggle").setAttribute("aria-expanded", String(open));
  renderLoop();
  if (!focus) return;
  if (open) $("#ask-input").disabled ? $("#copilot-close").focus() : $("#ask-input").focus();
  else if (getComputedStyle($("#copilot-toggle")).display !== "none") $("#copilot-toggle").focus();
}

function bind() {
  $$(".nav button").forEach((b) => b.addEventListener("click", () => setWorkspace(b.dataset.ws)));
  $("#target-select").addEventListener("change", (e) => loadTarget(e.target.value));
  window.addEventListener("popstate", async () => {   // browser back/forward
    const h = readHash();
    if (h.target && h.target !== state.targetId && state.targets.some((t) => t.target_id === h.target))
      await loadTarget(h.target, { keepSelection: h.obs, push: false });
    else if (h.obs && h.obs !== state.selectedKey) state.selectedKey = h.obs;
    if (h.b) state.partnerKey = h.b;
    setWorkspace(RENDER[h.ws] ? h.ws : "command", { push: false });
    renderRuler();
  });
  $("#run-btn").addEventListener("click", () => runAnalysis());
  $("#copilot-toggle").addEventListener("click", () => setCopilotOpen(!$("#app").classList.contains("copilot-open-narrow")));
  $("#copilot-close").addEventListener("click", () => setCopilotOpen(false));
  on("select", (key) => {
    state.selectedKey = key;
    if (state.partnerKey === key) state.partnerKey = null;
    renderRuler();
    if (state.ws === "explorer") loadSelected();
    else if (state.ws === "time") renderTime();
    writeHash();
  });
  on("partner", () => { renderRuler(); renderTime(); writeHash(); });
  on("goto-lab", (tab) => { setLabTab(tab === "rerun-stability" ? "rerun" : tab, { stability: tab === "rerun-stability" }); setWorkspace("lab"); });
  on("goto", ({ ws, key, partner, focus, tab, question, qtab }) => {
    if (key) state.selectedKey = key;
    if (partner) state.partnerKey = partner;
    if (focus) { focusGraph(focus); if (ws === "graph" && !tab) setLedgerTab("graph"); }
    if (tab && ws === "lab") setLabTab(tab);
    if (tab && ws === "graph") setLedgerTab(tab === "ledger" ? "claims" : tab);
    if (tab && ws === "adversarial") setAdversarialTab(tab);
    if (tab && ws === "review") setReviewTab(tab);
    if (tab && ws === "reasoning") setReasoningTab(tab);
    if (tab && ws === "compiler") setCompilerTab(tab);
    if (tab && ws === "claims") setClaimsTab(tab);
    if (tab && ws === "debugger") setDebuggerTab(tab);
    if (tab && ws === "decide") setDecideTab(tab);
    if (tab && ws === "intel") setIntelPanel(tab);
    if (qtab) setQualityTab(qtab);
    if (question) setPlannerQuestion(question);
    renderRuler();
    setWorkspace(ws);
  });
  on("run", (params) => runAnalysis(params));
  on("blind-changed", () => { $("#app").classList.toggle("blind-mode", blindActive()); renderRuler(); });
  on("open-sequence", (id) => { openSequence(id); setWorkspace("time"); });
  on("pair-viewed", async ({ a, b, compatible }) => {
    if (!state.session) return;
    const key = `${a}|${b}`;
    await S.update(compatible ? "pair.view_matched" : "pair.view", `Compared ${a} with ${b}${compatible ? " (wavelength-matched)" : ""}`,
      (x) => { if (!x.examined.includes(key)) x.examined = [...x.examined, key].slice(-500); return x; }, key);
  });
  on("sequence-viewed", (id) => S.log("sequence.view", `Sequence ${id} opened`, id));
  on("session-changed", () => {
    renderSessionBox();
    if (state.ws === "command") renderCommand();
    if ($("#app").classList.contains("blind-mode") !== blindActive()) { $("#app").classList.toggle("blind-mode", blindActive()); renderRuler(); if (!BLIND_ALLOWED.includes(state.ws)) renderWs(state.ws); }
  });
  on("ask", (q) => { setCopilotOpen(true, false); ask(q); });
  on("open-record", async (d) => {
    if (!d.bundle_available) { toast("The data bundle for this record is not available on this machine."); return; }
    if (state.targetId !== d.target_id) await loadTarget(d.target_id);
    try {
      const r = await api.investigation(d.investigation_id);
      state.inv = r; state.model = deriveModel(r.record); state.discovery = null; state.research = null; state.frontier = null; state.epistemic = null; state.intelligence = null; state.corpus = null;
      state.context = sanitizeContext(d.context);   // restored as saved (untrusted, so only known fields); nothing is filled in
      resetCopilot();
      $("#thread").append(el("p", { class: "faint" }, `Reopened “${d.name}”, saved ${d.saved_at}. Earlier conversation:`));
      for (const m of d.copilot_transcript || []) $("#thread").append(el("div", { class: m.role === "user" ? "msg user" : "msg bot" },
        m.role === "user" ? m.content : [el("div", { class: "mode" }, m.mode === "meta" ? "Meta (saved)" : "Local assistant (saved)"), el("div", { class: "answer" }, m.content)]));
      state.transcript = d.copilot_transcript || [];
      renderHeader(); renderRuler(); refreshCopilot();
      toast(`Reopened “${d.name}”`);
      setWorkspace("lab");
    } catch (e) { toast(e.message); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("#palette").hidden ? openPalette() : closePalette(); return; }
    if (!$("#sessions").hidden) { if (e.key === "Escape") { e.preventDefault(); closeSessions(); } return; }
    if (!$("#palette").hidden || !$("#help").hidden) return;
    if (e.key === "Escape" && $("#app").classList.contains("copilot-open-narrow")) { setCopilotOpen(false); return; }
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (e.altKey && /^[1-9]$/.test(e.key)) { const v = visibleWs(); if (v[+e.key - 1]) { e.preventDefault(); setWorkspace(v[+e.key - 1]); } return; }
    if (e.key === "/" ) { e.preventDefault(); openPalette(); return; }
    if (e.key === "?") { e.preventDefault(); openHelp(); return; }
    if (state.ws === "explorer" && (e.key === "ArrowRight" || e.key === "ArrowLeft")) { e.preventDefault(); stepSelection(e.key === "ArrowRight" ? 1 : -1); }
    if (state.ws === "time" && e.key === " ") { e.preventDefault(); toggleBlink(); }
  });
  new ResizeObserver(() => renderRuler()).observe($("#ruler-svg"));
  bindCopilot();
  $$(".level-switch button").forEach((b) => b.addEventListener("click", () => { setLevel(b.dataset.level); renderWs(state.ws); }));
  $("#palette-btn").addEventListener("click", openPalette);
  $("#help-btn").addEventListener("click", openHelp);
  bindPalette(paletteCommands);
  on("context-changed", () => { renderLoop(); S.syncSessionFromContext(); });
}

function paletteCommands() {
  const vis = visibleWs();
  const cmds = Object.keys(WS_LABEL).map((ws) => ({ group: "Workspace", label: WS_LABEL[ws], hint: vis.includes(ws) && vis.indexOf(ws) < 9 ? `Alt+${vis.indexOf(ws) + 1}` : `${minLevel(ws)} level`, run: () => setWorkspace(ws) }));
  for (const t of state.targets) cmds.push({ group: "Target", label: t.name, hint: t.kind === "synthetic" ? "synthetic" : t.kind ? "archive" : "no data yet",
                                              run: () => loadTarget(t.target_id) });
  cmds.push(...observationCommands((key) => { state.selectedKey = key; setWorkspace("explorer"); }));
  const inv = !!state.inv;
  cmds.push(
    { group: "Action", label: state.inv ? "Re-run analysis" : "Run analysis", disabled: !state.target, run: () => runAnalysis() },
    { group: "Action", label: "Check stability", hint: "STAB-1", disabled: !inv, run: () => emit("goto-lab", "rerun-stability") },
    { group: "Action", label: "Uncertainty decomposition", hint: "UNC-1", disabled: !inv, run: () => emit("goto-lab", "uncertainty") },
    { group: "Action", label: "Test hypotheses", hint: "HYPO-1", disabled: !inv, run: () => setWorkspace("arena") },
    { group: "Action", label: "Reproducibility package and reports", disabled: !inv, run: () => { setWorkspace("records"); setTimeout(() => $("#studio")?.scrollIntoView(), 50); } },
    { group: "Action", label: "Ask the copilot", run: () => { setCopilotOpen(true); $("#ask-input").focus(); } },
    ...["explore", "investigate", "research"].map((l) => ({ group: "View", label: `Level: ${l[0].toUpperCase() + l.slice(1)}`,
      run: () => { setLevel(l); renderWs(state.ws); } })),
    { group: "Help", label: "Glossary and keyboard shortcuts", hint: "?", run: openHelp },
    { group: "Session", label: "Research sessions…", hint: state.session ? state.session.name : "none yet", run: openSessions },
    { group: "Session", label: "Plan an investigation", hint: "PLAN-1", run: () => setWorkspace("planner") },
    { group: "Session", label: "Add a notebook block", run: () => { setWorkspace("notebook"); setTimeout(() => $("#nb-type")?.focus(), 50); } },
    { group: "Action", label: "Data-quality checks", hint: "DQ-1", disabled: !inv, run: () => { setQualityTab("checks"); setWorkspace("quality"); } },
    { group: "Action", label: "Compatibility matrix", hint: "COMPAT-1", disabled: !inv, run: () => { setQualityTab("matrix"); setWorkspace("quality"); } },
    { group: "Action", label: "Multi-epoch sequences", hint: "SEQ-1", disabled: !inv, run: () => { setQualityTab("coverage"); setWorkspace("quality"); } },
    { group: "Action", label: "Contradiction inspector", hint: "LEDGER-1", disabled: !inv, run: () => { setLedgerTab("contradictions"); setWorkspace("graph"); } },
    { group: "Action", label: "Research opportunities", hint: "RADAR-1", disabled: !inv, run: () => setWorkspace("radar") },
    { group: "Action", label: "Run an experiment", hint: "EXP-1", disabled: !state.target, run: () => setWorkspace("experiments") },
    { group: "Action", label: "Archive connectors", hint: "ACQ-2", run: () => { setQualityTab("connectors"); setWorkspace("quality"); } });
  return cmds;
}

async function init() {
  let lvl = "investigate";
  try { lvl = localStorage.getItem("skytrace.level") || lvl; } catch { /* storage may be unavailable */ }
  setLevel(lvl, false);
  bind();
  bindSessions();
  setHooks({ runAnalysis, loadTarget: (tid) => loadTarget(tid) });
  setTargetLoader(async (tid) => { if (tid !== state.targetId) await loadTarget(tid); if (!state.inv && state.target) await runAnalysis(undefined, { quiet: true }); });
  try {
    [state.status, { targets: state.targets }] = await Promise.all([api.status(), api.targets()]);
  } catch (e) {
    $("#main").prepend(el("div", { class: "banner warn" }, el("strong", {}, STATIC ? "The preview's data files could not be loaded." : "Cannot reach the Skytrace server."), el("p", {}, e.message)));
    return;
  }
  if (STATIC) $("#preview-note").hidden = false;
  await S.restoreSession();
  renderSessionBox();
  const sel = $("#target-select");
  const real = state.targets.filter((t) => t.real_target), syn = state.targets.filter((t) => !t.real_target);
  sel.append(el("optgroup", { label: "Challenge targets (archive data)" }, ...real.map((t) => el("option", { value: t.target_id }, `${t.name}${t.kind ? "" : " — no data yet"}`))),
             el("optgroup", { label: "Synthetic test targets" }, ...syn.map((t) => el("option", { value: t.target_id }, `${t.name} (synthetic)`))));
  const h = readHash();
  const withData = state.targets.find((t) => t.kind === "archive" && t.verified) || state.targets.find((t) => t.kind);
  const tid = state.targets.some((t) => t.target_id === h.target) ? h.target : withData?.target_id || state.targets[0]?.target_id;
  state.ws = RENDER[h.ws] ? h.ws : "command";
  setWorkspace(state.ws, { push: false });
  await loadTarget(tid, { keepSelection: h.obs, push: false });
  if (h.b) state.partnerKey = h.b;
  renderWs(state.ws);
  renderLoop();
}

init();
