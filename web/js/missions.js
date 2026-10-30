// MISSION-1 evaluation in the browser: identical to src/skytrace/missions.py (parity-tested). Mission templates come
// from the server or the static preview's specs; completion is read from the session, never self-declared.

export function taskDone(task, ms, s) {
  const c = task.criterion;
  const since = ms.started_at || "";
  if ("event" in c) return (s.history || []).filter((h) => c.event.includes(h.kind) && h.at >= since).length >= (c.min ?? 1);
  if ("question" in c) return !!((s.question || {}).text || "").trim();
  if ("runs" in c) return (s.runs || []).length >= c.runs;
  if ("notebook" in c) return (s.notebook || []).filter((b) => c.notebook.includes(b.type)).length >= (c.min ?? 1);
  if ("hypotheses_with_tests" in c) return (s.hypotheses || []).filter((h) => h.tests && h.tests.length).length >= c.hypotheses_with_tests;
  if ("review" in c) return (ms.reviews || []).some((r) => r.task_id === task.id && r.note.trim());
  return false;
}

export function evaluate(missions, s) {
  const by = Object.fromEntries(missions.map((m) => [m.id, m]));
  return (s.missions || []).map((ms) => {
    const m = by[ms.template_id];
    if (!m) return { template_id: ms.template_id, known: false, tasks: [], complete: false };
    const tasks = m.tasks.map((t) => ({ id: t.id, title: t.title, done: taskDone(t, ms, s) }));
    return { template_id: m.id, known: true, tasks, complete: tasks.every((t) => t.done), n_done: tasks.filter((t) => t.done).length, n_tasks: tasks.length };
  });
}
