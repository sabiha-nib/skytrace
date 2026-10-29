// Discovery Engine workspace (DISC-1). Everything shown is computed by the Python pipeline from the recorded
// investigation (src/skytrace/discovery.py); this module only lays it out and links each step to where it runs.
// Stages: A inventory · B question · C test plan · D execution (links to the pipeline) · E review · F next steps · G record.

import { emit, getDiscovery, state } from "./state.js";
import { $, categoryLabel, clear, el, fmtDate, questionLabel, shortKey } from "./util.js";

// Where each registered question is executed or reviewed in the interface.
const RUN = {
  "Q-VAR": ["Open the brightness comparison", () => emit("goto", { ws: "lab", tab: "variability" })],
  "Q-MOT": ["Open the motion fit", () => emit("goto", { ws: "lab", tab: "motion" })],
  "Q-COMPAT": ["Compare two observations", () => emit("goto", { ws: "time" })],
  "Q-SENS": ["Run the stability check", () => emit("goto-lab", "rerun-stability")],
  "Q-ALT": ["Open the Hypothesis Arena", () => emit("goto", { ws: "arena" })],
  "Q-UNC": ["Open the uncertainty decomposition", () => emit("goto", { ws: "lab", tab: "uncertainty" })],
  "Q-QUAL": ["Open the measurement table", () => emit("goto", { ws: "lab", tab: "measurements" })],
  "Q-REPRO": ["Open the reproducibility tools", () => emit("goto", { ws: "records" })],
};
const CAP_RUN = { stability: RUN["Q-SENS"], wavelength_match: RUN["Q-COMPAT"], brightness: RUN["Q-VAR"], motion: RUN["Q-MOT"],
                  uncertainty: RUN["Q-UNC"], provenance: RUN["Q-REPRO"] };
let showAll = false;

const statusClass = (s) => ({ answerable: "ok", "answerable with limits": "warn", "not answerable": "bad" })[s] || "";

export async function renderDiscovery() {
  const body = $("#discovery-body");
  clear(body);
  if (!state.target) {
    body.append(el("div", { class: "empty" }, el("h3", {}, "No stored observations for this target"),
      el("p", {}, "The engine works on an analysed investigation. Choose a synthetic test target, or acquire real data for this one (see the Sky Explorer for the command)."),
      el("p", { class: "muted" }, "Not answerable without data: every registered question needs at least one measured observation.")));
    return;
  }
  if (!state.inv) {
    body.append(el("div", { class: "empty" }, el("h3", {}, "Run the analysis first"), el("p", {}, "The engine reads the recorded analysis; it does not measure anything itself."),
      el("button", { class: "btn primary", onclick: () => emit("run") }, "Run analysis")));
    return;
  }
  body.append(el("p", { class: "busy" }, el("span", { class: "spinner" }), "Reading the investigation…"));
  let d;
  try { d = await getDiscovery(); } catch (e) { clear(body).append(el("p", { class: "empty" }, `The engine could not run: ${e.message}`)); return; }
  if (state.ws !== "discovery") return;
  clear(body);
  const stages = el("ol", { class: "stages", "aria-label": "Engine stages" }, ...d.stages.map((s) => el("li", {}, s)));
  body.append(el("div", { class: "card engine-head" }, el("div", {}, el("h3", {}, `${d.method} · investigation ${d.content_hash.slice(0, 12)}…`),
    d.synthetic ? el("p", { class: "syn-note" }, "Synthetic test data: the engine shows what the method can establish, not facts about the sky.") : null), stages));
  body.append(questionCard(d), reviewCard(), nextCard(d), inventoryCard(d), recordCard());
}

function questionCard(d) {
  const selId = state.context.question || "Q-VAR";
  const q = d.questions.find((x) => x.id === selId) || d.questions[0];
  const list = el("div", { class: "qlist", role: "radiogroup", "aria-label": "Research questions" }, ...d.questions.map((x) => {
    const b = el("button", { type: "button", role: "radio", "aria-checked": x.id === q.id ? "true" : "false", class: `qitem ${statusClass(x.status)}` },
      el("span", { class: "qstatus" }, x.status), el("span", {}, x.text));
    b.addEventListener("click", () => { state.context.question = x.id; state.context.question_text = x.text; emit("context-changed"); renderDiscovery(); });
    return b;
  }));
  const p = q.plan;
  const run = RUN[q.id];
  const plan = el("div", { class: "plan" },
    el("h4", {}, "Test plan"),
    el("dl", { class: "kv" },
      el("dt", {}, "Status"), el("dd", { class: `status-${statusClass(q.status)}` }, q.status),
      q.why_not ? [el("dt", {}, "Why not"), el("dd", {}, q.why_not)] : null,
      el("dt", {}, "Required inputs"), el("dd", {}, p.required_inputs.length ? el("ul", { class: "checks" }, ...p.required_inputs.map((r) =>
        el("li", { class: r.available ? "yes" : "no" }, `${r.available ? "available" : "missing"}: ${r.input}`))) : "—"),
      p.missing_inputs.length ? [el("dt", {}, "Missing"), el("dd", {}, p.missing_inputs.join("; "))] : null,
      p.method ? [el("dt", {}, "Method"), el("dd", {}, p.method)] : null,
      p.preconditions.length ? [el("dt", { class: "lvl-investigate" }, "Preconditions"), el("dd", { class: "lvl-investigate" }, p.preconditions.join("; "))] : null,
      p.assumptions.length ? [el("dt", { class: "lvl-investigate" }, "Assumptions"), el("dd", { class: "lvl-investigate" }, p.assumptions.join("; "))] : null,
      p.expected_outputs.length ? [el("dt", {}, "Outputs"), el("dd", {}, p.expected_outputs.join("; "))] : null,
      p.validation.length ? [el("dt", { class: "lvl-investigate" }, "Validated by"), el("dd", { class: "lvl-investigate" }, p.validation.join("; "))] : null,
      p.limitations.length ? [el("dt", {}, "Limitations"), el("dd", {}, p.limitations.join("; "))] : null,
      q.current_answer ? [el("dt", {}, "Current answer"), el("dd", {}, el("strong", {}, categoryLabel(q.current_answer.category)), " — ", q.current_answer.statement)] : null),
    run && q.status !== "not answerable" ? el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: run[1] }, run[0])) : null);
  return el("div", { class: "card" }, el("h3", {}, "B · Research question and C · test plan"),
    el("p", { class: "muted" }, "Each question maps to registered capabilities. Questions the data cannot answer say why and what would be needed."),
    el("div", { class: "qgrid" }, list, plan));
}

function reviewCard() {
  const m = state.model;
  return el("div", { class: "card" }, el("h3", {}, "E · Evidence review"),
    el("p", { class: "muted" }, "The deterministic outcomes (ASSESS-2). A computation that ran is not a supported hypothesis: see the Hypothesis Arena for competing explanations and the Uncertainty tab for what the errors contain."),
    el("ul", { class: "review" }, ...m.outcomes.map((o) => el("li", {}, el("strong", {}, questionLabel(o.question)), ": ", categoryLabel(o.category), " — ", o.statement))),
    el("div", { class: "controls" },
      el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "arena" }) }, "Test explanations"),
      el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "lab", tab: "uncertainty" }) }, "Uncertainty decomposition"),
      el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "graph", focus: "claim:variability" }) }, "Trace in the Evidence Graph")));
}

function nextCard(d) {
  return el("div", { class: "card" }, el("h3", {}, "F · Next steps"),
    el("p", { class: "muted" }, "Rule-based recommendations from the outcomes, the inventory and the capability registry. None promises a specific gain in confidence."),
    el("ol", { class: "next" }, ...d.next_steps.map((s) => {
      const run = CAP_RUN[s.capability];
      return el("li", {},
        el("div", { class: "next-head" }, el("strong", {}, s.action),
          el("span", { class: `pill ${s.runs_locally ? "archive" : "none"}` }, s.runs_locally ? "runs here" : s.requires_unavailable_service ? `needs ${s.requires_unavailable_service}` : "needs the server")),
        el("p", {}, s.why),
        el("dl", { class: "kv compact" }, el("dt", {}, "Question"), el("dd", {}, s.question), el("dt", {}, "Data needed"), el("dd", {}, s.data_required),
          el("dt", {}, "Can establish"), el("dd", {}, s.can_establish), el("dt", {}, "Cannot establish"), el("dd", {}, s.cannot_establish)),
        run && !s.requires_unavailable_service ? el("button", { class: "btn small", type: "button", onclick: run[1] }, run[0]) : null);
    })));
}

function inventoryCard(d) {
  const inv = d.inventory, s = inv.summary;
  const rows = showAll ? inv.items : inv.items.slice(0, 14);
  const more = el("button", { class: "btn small ghost", type: "button" }, showAll ? "Show fewer" : `Show all ${inv.items.length}`);
  more.addEventListener("click", () => { showAll = !showAll; renderDiscovery(); });
  return el("div", { class: "card" }, el("h3", {}, "A · Evidence inventory"),
    el("p", { class: "muted" }, `${s.n_observations} archive records (${s.n_images} stored images): ${s.n_included} included, ${s.n_excluded} excluded · detectors ${s.detectors.join(" ")} · releases ${s.releases.join(", ") || "—"} · ${s.dates.length} observing dates · origins ${s.origins.join(", ")} · ${s.unknown_fields} unknown field(s) left empty, never guessed.`),
    el("div", { class: "table-wrap lvl-investigate" }, el("table", { class: "inventory" },
      el("thead", {}, el("tr", {}, ...["Identifier", "Type", "Source / origin", "Epoch", "Channel", "Quality", "SHA-256"].map((h, i) => el("th", { scope: "col", class: i === 6 ? "lvl-research" : null }, h)))),
      el("tbody", {}, ...rows.map((i) => el("tr", {},
        el("td", { class: "mono" }, i.id.startsWith("SYNTHETIC:") || /^QR\d:/.test(i.id) ? shortKey(i.id) : i.id),
        el("td", {}, i.type), el("td", {}, [i.source ?? "unknown", i.origin ? ` · ${i.origin}` : ""].join("")),
        el("td", {}, typeof i.epoch === "string" && i.epoch.includes("T") ? fmtDate(i.epoch) : i.epoch ?? "unknown"),
        el("td", {}, i.channel ?? "unknown"), el("td", {}, i.quality ?? "unknown", ...(i.limitations || []).map((l) => el("div", { class: "faint" }, l))),
        el("td", { class: "mono wrap lvl-research" }, i.sha256 ? i.sha256.slice(0, 16) + "…" : "unknown")))))),
    el("div", { class: "controls lvl-investigate" }, more));
}

function recordCard() {
  return el("div", { class: "card" }, el("h3", {}, "G · Reproducible record"),
    el("p", { class: "muted" }, `Investigation content hash ${state.inv.record.content_hash.slice(0, 16)}… Saving keeps the record, your question and your hypotheses together; the reproducibility package adds the inventory, test results and checksums.`),
    el("div", { class: "controls" }, el("button", { class: "btn small", type: "button", onclick: () => emit("goto", { ws: "records" }) }, "Save or export this investigation")));
}
