// Small helpers that add notebook blocks from other workspaces (figure studio, copilot drafts).
import * as S from "./session.js";
import { nowIso } from "./sessioncore.js";
import { state } from "./state.js";

export async function insertFigure(id) {
  await S.update("note.add", `Added figure block ${id}`, (x) => {
    x.notebook = [...x.notebook, { id: S.newId("n"), type: "figure", ref: { kind: "figure", id }, author: "user", created_at: nowIso(), modified_at: nowIso() }].slice(-300);
    return x;
  }, id);
  if (state.inv) await S.attachRun(state.inv, "current analysis");
}
