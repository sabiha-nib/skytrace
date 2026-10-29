// Research copilot panel. The server runs the tool loop and the evidence guard; this panel shows
// exactly what happened: which tools ran, what they returned, what was claimed, and what was withheld.

import { api } from "./api.js";
import { emit, state } from "./state.js";
import { $, clear, el, questionLabel } from "./util.js";

const KEY_RE = /\b(?:QR\d|SYNTHETIC):[A-Za-z0-9_]+:D[1-6]\b/g;

export function resetCopilot() {
  state.transcript = [];
  clear($("#thread"));
  refreshCopilot();
}

export function refreshCopilot() {
  const ready = !!state.inv;
  $("#ask-input").disabled = !ready;
  $("#ask-btn").disabled = !ready;
  const st = state.status?.meta;
  $("#copilot-status").textContent = !ready ? "Run an analysis to ask questions about its evidence."
    : st?.configured ? `Answers come from Meta ${st.model} through read-only tools, checked by the evidence guard.`
    : "No Meta API key is configured (or offline mode is on): a local deterministic assistant answers from the same tools, without a language model.";
  const sug = $("#suggestions");
  clear(sug);
  if (!ready) return;
  for (const q of suggestions()) sug.append(el("button", { class: "chip", type: "button", onclick: () => ask(q) }, q));
}

function suggestions() {
  const out = [];
  const cats = Object.fromEntries((state.model?.outcomes || []).map((o) => [o.question, o.category]));
  if (cats.variability === "variability_candidate") out.push("Which observations support the variability candidate?");
  else out.push("What changed between these observations?");
  if (cats.motion === "motion_detected" || cats.motion === "motion_inconsistent") out.push("How does the result compare with the Gaia reference?");
  out.push("Could the apparent motion be caused by alignment errors?", "Why was an observation excluded?", "What should I investigate next?");
  return out.slice(0, 4);
}

function linkify(text) {
  const frag = document.createDocumentFragment();
  let last = 0;
  for (const m of text.matchAll(KEY_RE)) {
    frag.append(text.slice(last, m.index));
    const b = el("button", { class: "obs-link", type: "button", title: "Open this observation" }, m[0]);
    b.addEventListener("click", () => emit("goto", { ws: "explorer", key: m[0] }));
    frag.append(b);
    last = m.index + m[0].length;
  }
  frag.append(text.slice(last));
  return frag;
}

export async function ask(question) {
  if (!state.inv || !question.trim()) return;
  const thread = $("#thread");
  thread.append(el("div", { class: "msg user" }, question));
  const pending = el("div", { class: "msg bot" }, el("p", { class: "busy" }, el("span", { class: "spinner" }), "Looking up the evidence…"));
  thread.append(pending);
  thread.scrollTop = thread.scrollHeight;
  $("#ask-input").value = "";
  const history = state.transcript.slice(-6).map((t) => ({ role: t.role, content: t.content }));
  try {
    const r = await api.ask(state.inv.investigation_id, question, history);
    pending.replaceWith(renderAnswer(r));
    state.transcript.push({ role: "user", content: question }, { role: "assistant", content: r.answer?.answer || "(no answer)", mode: r.mode, ok: r.ok,
                            tools: r.tool_calls.map((c) => c.name), withheld: r.withheld.length });
  } catch (e) {
    pending.replaceWith(el("div", { class: "msg bot" }, el("p", { class: "withheld" }, `The copilot could not answer: ${e.message}`)));
  }
  thread.scrollTop = thread.scrollHeight;
}

function renderAnswer(r) {
  const meta = r.mode === "meta";
  const box = el("div", { class: "msg bot" + (meta ? " meta" : "") });
  box.append(el("div", { class: "mode" }, meta ? `Meta ${r.model} · checked by the evidence guard` : "Local assistant · no language model"));
  if (!r.answer) {
    box.append(el("p", { class: "withheld" }, "No answer could be shown: " + r.problems.join("; ")));
    return box;
  }
  box.append(el("div", { class: "answer" }, linkify(r.answer.answer)));
  const outputs = Object.fromEntries(r.tool_calls.map((c) => [c.id, c]));
  if (r.answer.claims?.length) {
    box.append(el("ul", { class: "claims", "aria-label": "Claims" }, ...r.answer.claims.map((c) => el("li", {},
      el("span", { class: "kind " + (c.kind || "measurement") }, c.kind === "interpretation" ? "interpretation" : c.kind === "speculation" ? "speculation" : "evidence"),
      c.text, c.value != null ? `: ${typeof c.value === "number" ? +c.value.toPrecision(6) : c.value} ${c.unit || ""}` : "",
      ...[].concat(c.evidence || []).map((id) => {
        const b = el("button", { class: "ev-chip", type: "button", title: "Show the tool output this claim cites" }, outputs[id]?.name || id);
        b.addEventListener("click", () => { const d = box.querySelector(`[data-tool="${id}"]`); if (d) { d.open = true; d.scrollIntoView({ block: "nearest" }); } });
        return b;
      })))));
  }
  if (r.answer.limitations?.length) box.append(el("ul", { class: "limits", "aria-label": "Limitations" }, ...r.answer.limitations.map((l) => el("li", {}, l))));
  const follow = [...(r.answer.follow_up_questions || []), ...(r.answer.suggested_next_steps || [])];
  if (follow.length) box.append(el("div", { class: "chips" }, ...follow.slice(0, 4).map((q) => el("button", { class: "chip", type: "button", onclick: () => ask(q) }, q))));
  const tools = el("details", {}, el("summary", {}, `Tool activity (${r.tool_calls.length})`),
    ...r.tool_calls.map((c) => el("details", { dataset: { tool: c.id } },
      el("summary", {}, el("span", { class: "tool-row" }, el("code", {}, c.name), el("span", { class: c.ok ? "faint" : "bad" }, c.ok ? JSON.stringify(c.arguments) : "error"))),
      el("pre", { class: "json" }, JSON.stringify(c.output, null, 1)))));
  box.append(tools);
  if (r.withheld?.length) box.append(el("details", {}, el("summary", { class: "withheld" }, `${r.withheld.length} model draft(s) withheld by the evidence guard`),
    ...r.withheld.map((w) => el("ul", { class: "limits" }, ...w.problems.map((p) => el("li", {}, `${p.code}: ${p.detail}`))))));
  if (r.problems?.length) box.append(el("p", { class: "faint" }, r.problems.join(" ")));
  return box;
}

export function bindCopilot() {
  $("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); ask($("#ask-input").value); });
  $("#ask-input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask($("#ask-input").value); } });
}

export { questionLabel };
