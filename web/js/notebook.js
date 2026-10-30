// Research Notebook (NOTE-1): structured blocks stored in the research session. Text blocks are the user's own words;
// reference blocks name an observation, measurement, claim, explanation, experiment, figure, run or dataset by
// identifier, and their values are read from the record when shown — never typed in. Assistant drafts stay labelled
// until the user accepts them. Edits keep up to 20 earlier versions. Export: Markdown, or a session package (session,
// notebook, the investigation's reproducibility package and checksums) built as a deterministic zip.

import { api } from "./api.js";
import { emit, getDiscovery, getResearch, getSpecs, state } from "./state.js";
import * as S from "./session.js";
import { nowIso } from "./sessioncore.js";
import { buildFigure, figureCard, figureList } from "./figurestudio.js";
import { zipStore } from "./zipstore.js";
import { dumps } from "./canon.js";
import { categoryLabel, clear, download, el, fmtDate, questionLabel, renderToken, shortKey, toast, $ } from "./util.js";

const TEXT_TYPES = ["heading", "paragraph", "question", "conclusion", "warning"];
const REF_TYPES = { observation: "observation", measurement: "measurement", evidence: "claim", hypothesis: "hypothesis", experiment: "experiment",
                    figure: "figure", parameters: "run", citation: "dataset" };
const TYPE_LABEL = { heading: "Heading", paragraph: "Paragraph", question: "Question", conclusion: "Conclusion", warning: "Warning", observation: "Observation reference",
                     measurement: "Measurement reference", evidence: "Evidence link (claim)", hypothesis: "Explanation (HYPO-1)", experiment: "Experiment result",
                     figure: "Figure", parameters: "Parameter record (run)", citation: "Source citation" };
let query = "", undo = null, ctx = null;

async function context() {
  const [spec, r, d] = await Promise.all([getSpecs(), state.inv ? getResearch() : null, state.inv ? getDiscovery() : null]);
  return { spec, r, d };
}

function refOptions(type, c) {
  const s = state.session;
  if (type === "observation" || type === "measurement") return (c.r?.compat.observations || []).map((o) => [o.key, `${shortKey(o.key)} · D${o.detector} · ${fmtDate(o.t_mid_iso)}`]);
  if (type === "evidence") return (c.r?.ledger.claims || []).map((x) => [x.id, `${questionLabel(x.question)}: ${categoryLabel(x.category)}`]);
  if (type === "hypothesis") return (c.d?.hypotheses.questions || []).flatMap((q) => q.hypotheses.map((h) => [h.id, `${h.id}: ${h.statement}`]))
    .concat((s?.hypotheses || []).map((h) => [`user:${h.id}`, `yours: ${h.statement}`]));
  if (type === "experiment") return (s?.experiments || []).map((e) => [e.id, `${e.template} · ${fmtDate(e.created_at)}`]);
  if (type === "figure") return figureList(c.r).map((f) => [f.id, f.label]);
  if (type === "parameters") return (s?.runs || []).map((x) => [x.content_hash, `${x.content_hash.slice(0, 12)}… · ${x.label}`]);
  if (type === "citation") return c.spec.citations.map((x) => [x.id, x.text]);
  return [];
}

/** Resolve a reference block to what it shows now, or why it cannot. Returns {ok, node, md}. */
function resolve(b, c) {
  const id = b.ref?.id;
  const s = state.session;
  const miss = (why) => ({ ok: false, node: el("p", { class: "status-rejected" }, `Unresolved reference ${id}: ${why}`), md: `> Unresolved reference ${id}: ${why}` });
  if (!id) return miss("no target chosen");
  if (b.type === "observation") {
    const o = c.r?.compat.observations.find((x) => x.key === id);
    if (!o) return miss("not in the current run");
    const t = `${o.key} · D${o.detector} · ${o.t_mid_iso} · λ ${o.wavelength_um?.toFixed(4) ?? "not recorded"} µm · file ${o.file} (SHA-256 ${o.sha256?.slice(0, 12) ?? "not recorded"}…)`;
    return { ok: true, node: el("p", { class: "mono wrap" }, t), md: `- Observation: ${t}` };
  }
  if (b.type === "measurement") {
    const m = state.model?.measurements[id];
    if (!m) return miss("no measurement in the current run");
    const ph = m.photometry || {}, ce = m.centroid || {};
    const t = `${id}: flux ${ph.status === "ok" ? `${ph.flux_ujy.toFixed(0)} ± ${ph.flux_err_ujy.toFixed(0)} µJy (${ph.method})` : `not measured (${ph.status || "no photometry"})`}; centroid ${ce.converged ? `x ${ce.x.toFixed(2)} ± ${ce.sigma_x.toFixed(2)}, y ${ce.y.toFixed(2)} ± ${ce.sigma_y.toFixed(2)} px (${ce.method})` : "not converged"}; quality ${m.quality}`;
    return { ok: true, node: el("p", { class: "wrap" }, t), md: `- Measurement (recorded): ${t}` };
  }
  if (b.type === "evidence") {
    const x = c.r?.ledger.claims.find((y) => y.id === id);
    if (!x) return miss("claim not in the current run");
    const t = `${questionLabel(x.question)}: ${categoryLabel(x.category)} — ${x.statement} [support: ${x.support.comparisons} comparisons, ${x.support.observations} observations, detectors ${x.support.detectors.join(" ") || "—"}${x.flags.length ? "; " + x.flags.join("; ") : ""}]`;
    return { ok: true, node: el("p", {}, t), md: `- Claim (recorded, LEDGER-1): ${t}` };
  }
  if (b.type === "hypothesis") {
    if (id.startsWith("user:")) {
      const h = (s?.hypotheses || []).find((y) => `user:${y.id}` === id);
      return h ? { ok: true, node: el("p", {}, el("span", { class: "kind interpretation" }, "your interpretation"), ` ${h.statement}`), md: `- Your interpretation: ${h.statement}` } : miss("hypothesis no longer in the session");
    }
    const h = (c.d?.hypotheses.questions || []).flatMap((q) => q.hypotheses).find((y) => y.id === id);
    if (!h) return miss("explanation not in the current run");
    const t = `${h.id}: ${h.statement} — overall ${h.overall} (${h.tests.map((x) => `${x.id} ${x.status.replace("_", " ")}`).join("; ")})`;
    return { ok: true, node: el("p", {}, t), md: `- Explanation (HYPO-1 rule result): ${t}` };
  }
  if (b.type === "experiment") {
    const e = (s?.experiments || []).find((y) => y.id === id);
    if (!e) return miss("experiment not in the session");
    const ev = e.result?.evaluation || {};
    const t = `${e.template} (${fmtDate(e.created_at)}): ${ev.passed === true ? "criterion met" : ev.passed === false ? "criterion not met" : "no evaluation"} — ${e.result?.criterion || ""}${e.result?.recorded_at_build ? " (recorded when the preview was built)" : ""}`;
    return { ok: true, node: el("p", {}, t), md: `- Experiment (EXP-1): ${t}` };
  }
  if (b.type === "figure") {
    try {
      const f = buildFigure(id, c.r);
      return { ok: true, node: figureCard(f), md: `- Figure ${f.id}: ${f.title}. ${f.summary} Data: ${f.source}. Method: ${f.method}. Limitations: ${f.limitations.join("; ")}.` };
    } catch (e) { return miss(e.message); }
  }
  if (b.type === "parameters") {
    const run = (s?.runs || []).find((y) => y.content_hash === id);
    if (!run) return miss("run not in the session");
    const t = `run ${id.slice(0, 16)}…: ` + Object.entries(run.params).map(([k, v]) => `${k}=${v}`).join(", ");
    return { ok: true, node: el("p", { class: "mono wrap" }, t), md: `- Parameters: ${t}` };
  }
  if (b.type === "citation") {
    const x = c.spec.citations.find((y) => y.id === id);
    if (!x) return miss("not a dataset this software uses");
    const t = `${x.text}${x.doi ? `, doi:${x.doi}` : ""}`;
    return { ok: true, node: el("p", {}, t), md: `- Source: ${t}` };
  }
  return miss("unknown block type");
}

export async function renderNotebook() {
  const body = $("#notebook-body");
  const live = renderToken("notebook");
  const c = await context();
  if (!live()) return;
  ctx = c;
  clear(body);
  const s = state.session;
  const blocks = (s?.notebook || []).filter((b) => !query || JSON.stringify(b).toLowerCase().includes(query.toLowerCase()));
  const search = el("input", { type: "search", id: "nb-search", placeholder: "Search the notebook", "aria-label": "Search the notebook", value: query });
  search.addEventListener("input", () => { query = search.value; renderNotebook().then(() => { const x = $("#nb-search"); x?.focus(); if (x) x.selectionStart = x.selectionEnd = x.value.length; }); });
  const md = el("button", { class: "btn small", type: "button", id: "nb-export-md", disabled: !s?.notebook.length || null }, "Export notebook (Markdown)");
  md.addEventListener("click", async () => { if (await download(`skytrace-notebook-${s.session_id}.md`, markdown(), "text/markdown")) { await S.log("notebook.export", "Notebook exported (Markdown)"); toast("Notebook exported"); } });
  const pkg = el("button", { class: "btn small", type: "button", id: "nb-export-pkg", disabled: !s || null, title: s ? "" : "No session yet" }, "Export session package (ZIP)");
  pkg.addEventListener("click", () => exportPackage().catch((e) => toast(e.message, 6000)));
  body.append(el("div", { class: "card" }, el("div", { class: "controls nb-tools" }, search, md, pkg),
    el("p", { class: "faint" }, "Your text is labelled as yours; reference blocks show the recorded values they point to; drafts from the assistant stay labelled until you accept them.")));
  const list = el("ol", { class: "nb-blocks" });
  if (!s?.notebook.length) list.append(el("li", { class: "muted" }, s ? "No blocks yet." : "No research session yet: adding a block starts one."));
  for (const b of blocks) list.append(blockView(b));
  body.append(list, undoBox(), addBox());
}

function blockView(b) {
  const s = state.session;
  const i = s.notebook.findIndex((x) => x.id === b.id);
  const head = el("div", { class: "nb-head" }, el("span", { class: "nb-type" }, TYPE_LABEL[b.type] || b.type),
    el("span", { class: `kind ${b.author === "user" ? "interpretation" : "speculation"}` }, b.author === "user" ? (TEXT_TYPES.includes(b.type) ? "your text" : "your reference") : "assistant draft"),
    b.versions?.length ? el("span", { class: "faint" }, ` · edited ${b.versions.length}×`) : null, el("span", { class: "faint" }, ` · ${fmtDate(b.modified_at)}`));
  const li = el("li", { class: `nb-block nb-${b.type}`, "data-block": b.id }, head);
  if (TEXT_TYPES.includes(b.type)) {
    const ta = el("textarea", { rows: b.type === "heading" ? "1" : "3", "aria-label": `${TYPE_LABEL[b.type]} text` }, b.text || "");
    const save = el("button", { class: "btn small", type: "button" }, "Save");
    save.addEventListener("click", async () => {
      const v = ta.value;
      if (v === b.text) return;
      await S.update("note.edit", `Edited ${b.type} block`, (x) => {
        const blk = x.notebook.find((y) => y.id === b.id);
        blk.versions = [...(blk.versions || []), { at: blk.modified_at, text: blk.text || "" }].slice(-20);
        blk.text = v.slice(0, 5000); blk.modified_at = nowIso();
        return x;
      }, b.id);
      renderNotebook();
    });
    li.append(b.type === "heading" ? el("div", { class: "nb-heading-edit" }, ta) : ta, el("div", { class: "controls" }, save));
  } else {
    li.append(resolve(b, ctx).node);
  }
  if (b.versions?.length) li.append(el("details", {}, el("summary", {}, "Earlier versions"), el("ol", { class: "limits" }, ...b.versions.slice().reverse().map((v) => el("li", {}, `${fmtDate(v.at)}: ${v.text.slice(0, 300)}`)))));
  const ctl = el("div", { class: "controls nb-ctl" });
  if (b.author !== "user") {
    const acc = el("button", { class: "btn small", type: "button" }, "Accept draft as mine");
    acc.addEventListener("click", async () => { await S.update("note.accept", "Assistant draft accepted", (x) => { const blk = x.notebook.find((y) => y.id === b.id); blk.author = "user"; blk.modified_at = nowIso(); return x; }, b.id); renderNotebook(); });
    ctl.append(acc);
  }
  const up = el("button", { class: "btn small ghost", type: "button", "aria-label": "Move block up", disabled: i <= 0 || null }, "↑");
  const down = el("button", { class: "btn small ghost", type: "button", "aria-label": "Move block down", disabled: i >= s.notebook.length - 1 || null }, "↓");
  const move = (d) => S.update("note.move", "Block moved", (x) => { const k = x.notebook.findIndex((y) => y.id === b.id); const [blk] = x.notebook.splice(k, 1); x.notebook.splice(k + d, 0, blk); return x; }, b.id).then(renderNotebook);
  up.addEventListener("click", () => move(-1));
  down.addEventListener("click", () => move(1));
  const del = el("button", { class: "btn small ghost", type: "button", "aria-label": `Delete ${TYPE_LABEL[b.type]} block` }, "Delete");
  del.addEventListener("click", async () => {
    undo = { block: structuredClone(b), index: i };
    await S.update("note.delete", `Deleted ${b.type} block`, (x) => { x.notebook = x.notebook.filter((y) => y.id !== b.id); return x; }, b.id);
    renderNotebook();
    setTimeout(() => { if (undo?.block.id === b.id) { undo = null; $("#nb-undo")?.setAttribute("hidden", ""); } }, 8000);
  });
  ctl.append(up, down, del);
  li.append(ctl);
  return li;
}

function undoBox() {
  const b = el("button", { class: "btn small", type: "button" }, "Undo");
  b.addEventListener("click", async () => {
    if (!undo) return;
    const u = undo; undo = null;
    await S.update("note.restore", "Deleted block restored", (x) => { x.notebook.splice(Math.min(u.index, x.notebook.length), 0, u.block); return x; }, u.block.id);
    renderNotebook();
  });
  return el("div", { class: "undo", id: "nb-undo", hidden: !undo || null, role: "status" }, "Block deleted. ", b);
}

function addBox() {
  const type = el("select", { id: "nb-type", "aria-label": "Block type" }, ...Object.entries(TYPE_LABEL).map(([k, v]) => el("option", { value: k }, v)));
  const holder = el("div", { class: "nb-add-fields" });
  const fill = () => {
    clear(holder);
    if (TEXT_TYPES.includes(type.value)) holder.append(el("textarea", { id: "nb-text", rows: "3", "aria-label": "Block text", placeholder: type.value === "conclusion" ? "Your conclusion, with its limits" : "Text" }));
    else {
      const opts = refOptions(type.value, ctx);
      holder.append(opts.length ? el("select", { id: "nb-ref", "aria-label": "Referenced item" }, ...opts.map(([v, l]) => el("option", { value: v }, l.slice(0, 140))))
        : el("p", { class: "muted", id: "nb-ref-empty" }, state.inv ? "Nothing of this kind to reference yet." : "Run the analysis first: references point into the recorded analysis."));
    }
  };
  type.addEventListener("change", fill);
  fill();
  const add = el("button", { class: "btn primary small", type: "button", id: "nb-add" }, "Add block");
  add.addEventListener("click", async () => {
    const t = type.value;
    const blk = { id: S.newId("n"), type: t, author: "user", created_at: nowIso(), modified_at: nowIso() };
    if (TEXT_TYPES.includes(t)) {
      const v = $("#nb-text").value.trim();
      if (!v) { toast("Write the text first"); return; }
      blk.text = v.slice(0, 5000);
      if (t === "heading") blk.level = 2;
    } else {
      const sel = $("#nb-ref");
      if (!sel) { toast("Nothing to reference"); return; }
      blk.ref = { kind: REF_TYPES[t] === "hypothesis" && sel.value.startsWith("user:") ? "user_hypothesis" : REF_TYPES[t], id: sel.value };
    }
    await S.update("note.add", `Added ${t} block`, (x) => { x.notebook = [...x.notebook, blk].slice(-300); return x; }, blk.id);
    if (state.inv) await S.attachRun(state.inv, "current analysis");
    renderNotebook();
  });
  return el("div", { class: "card nb-add" }, el("h3", {}, "Add a block"), el("div", { class: "controls" }, type), holder, el("div", { class: "controls" }, add));
}

/** Insert drafts (e.g. from the copilot) as assistant-draft blocks. */
export async function insertDrafts(blocks) {
  await S.update("note.draft", `${blocks.length} draft block(s) from the assistant`, (x) => {
    x.notebook = [...x.notebook, ...blocks.map((b) => ({ id: S.newId("n"), author: "assistant-draft", created_at: nowIso(), modified_at: nowIso(), ...b }))].slice(-300);
    return x;
  });
}

function markdown() {
  const s = state.session;
  const L = [`# ${s.name}`, "", `Research session ${s.session_id} · exported ${nowIso()} · content hash ${s.content_hash || "(pending)"}`, ""];
  if (s.question.text) L.push(`**Research question:** ${s.question.text}`, "");
  if (state.model?.synthetic) L.push("> SYNTHETIC TEST DATA: generated by code; nothing here is an astronomical result.", "");
  L.push("Legend: *[you]* your text · *[recorded]* values read from the analysis record · *[draft]* assistant draft not yet accepted.", "");
  for (const b of s.notebook) {
    const who = b.author === "user" ? (TEXT_TYPES.includes(b.type) ? "[you]" : "[recorded]") : "[draft]";
    if (b.type === "heading") L.push(`## ${b.text} ${who}`, "");
    else if (TEXT_TYPES.includes(b.type)) L.push(`**${TYPE_LABEL[b.type]}** ${who}: ${b.text}`, "");
    else L.push(`${resolve(b, ctx).md} ${who}`, "");
  }
  return L.join("\n") + "\n";
}

async function exportPackage() {
  const s = state.session;
  if (!s) throw new Error("no session");
  await S.log("session.export", "Session package exported (ZIP)");
  await S.flush();
  const cur = state.session;
  const enc = new TextEncoder();
  const files = [["session.json", dumps(cur)], ["notebook.md", markdown()]];
  if (state.inv && cur.runs.some((r) => r.content_hash === state.inv.record.content_hash)) {
    try { files.push(["investigation-package.zip", new Uint8Array(await api.packageBytes(state.inv.investigation_id))]); } catch (e) { toast(`Package not included: ${e.message}`, 6000); }
  }
  const readme = [`# Skytrace session package — ${cur.name}`, "", "* session.json — the research session in SKY-CANON-1 form; its content_hash recomputes as SHA-256 of the text without the content_hash field",
    "* notebook.md — the notebook, with references resolved against the active analysis run at export time",
    files.length > 2 ? "* investigation-package.zip — the PKG-1 reproducibility package of the active run (record, reports, checksums)" : "* (no investigation package: the active run is not attached to this session)",
    "* SHA256SUMS — checksums of the files above (sha256sum -c SHA256SUMS)", ""].join("\n");
  files.splice(2, 0, ["README.md", readme]);
  const sums = [];
  for (const [n, d] of files) {
    const bytes = typeof d === "string" ? enc.encode(d) : d;
    const h = await crypto.subtle.digest("SHA-256", bytes);
    sums.push(`${Array.from(new Uint8Array(h), (x) => x.toString(16).padStart(2, "0")).join("")}  ${n}`);
  }
  files.push(["SHA256SUMS", sums.join("\n") + "\n"]);
  const dir = `skytrace-session-${cur.session_id}/`;
  const zip = zipStore(files.map(([n, d]) => [dir + n, d]));
  if (await download(`skytrace-session-${cur.session_id}.zip`, zip.buffer, "application/zip")) toast("Session package exported");
}

export { resolve as resolveBlock };
