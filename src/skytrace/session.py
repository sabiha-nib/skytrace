"""Research Session (SESSION-1): the persistent, integrity-checked context of one investigation.

A session holds what the user decided and wrote, and references to what the pipeline computed — never copies of
computed results that could drift from their source. It contains the research question, the target, the analysis runs
it used (investigation id + content hash + parameters), user hypotheses with version history, notebook blocks,
annotations, investigation plans and their execution records, experiments, missions, examined observation pairs and an
append-only activity history.

Integrity: `content_hash` = SHA-256 of the SKY-CANON-1 text of the session without `content_hash`. The browser computes
the same hash (`web/js/session.js`, parity-tested), so a session can move between the server and the static preview.
A session whose stated hash does not recompute is refused on import. Unknown schema versions are refused with an
explicit message; v0.5 saved investigations convert with `from_saved_record` (nothing in them is discarded).

Validation uses SCHEMA-1 (`schema.py`); the same schema document is served to the browser.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from . import canon
from .schema import A, BOOL, HEX64, ID, INT, ISO, NUM, O, OPT, S, check

METHOD = "SESSION-1"
SCHEMA_ID = "skytrace.research_session/1"
MAX_BYTES = 1_000_000

BLOCK_TYPES = ["heading", "paragraph", "observation", "measurement", "evidence", "hypothesis", "experiment", "figure",
               "warning", "parameters", "citation", "question", "conclusion"]
REF_KINDS = ["observation", "measurement", "claim", "graph_node", "hypothesis", "user_hypothesis", "experiment",
             "figure", "run", "dataset", "pair", "test", "challenge", "scenario", "opportunity", "twin",
             "node", "argument", "negative", "review_item", "check", "entity", "memory", "capsule"]
STEP_STATUS = ["suggested", "ready", "running", "completed", "blocked", "failed", "needs_review"]

_REF = O({"kind": (S(enum=REF_KINDS), True), "id": (S(300, 1), True)})
_VERSION = O({"at": (ISO, True), "text": (S(5000), True)})
_SCALAR = {"t": "any", "of": [S(2000), {"t": "num"}, BOOL, {"t": "null"}]}

SESSION_SCHEMA = O({
    "schema": ({"t": "const", "v": SCHEMA_ID}, True),
    "session_id": (S(12, 12, r"^[a-z0-9]{12}$"), True),
    "name": (S(120, 1), True),
    "created_at": (ISO, True),
    "modified_at": (ISO, True),
    "target_id": (OPT(S(64, 1, r"^[A-Za-z0-9_.-]{1,64}$")), True),
    "question": (O({"id": (OPT(S(20, 3, r"^Q-[A-Z]{2,16}$")), True), "text": (S(500), True)}), True),
    "runs": (A(O({"investigation_id": (S(64, 1, r"^[A-Za-z0-9_-]{1,64}$"), True), "content_hash": (HEX64, True),
                  "label": (S(120), True), "attached_at": (ISO, True),
                  "params": ({"t": "map", "keys": r"^[a-z_]{1,40}$", "max": 20,
                              "values": {"t": "any", "of": [{"t": "num"}, BOOL]}}, True)}), 50), True),
    "active_hash": (OPT(HEX64), True),
    "hypotheses": (A(O({"id": (ID, True), "statement": (S(1000, 1), True), "tests": (A(S(60, 1), 30), True),
                        "kind": ({"t": "const", "v": "interpretation"}, True), "created_at": (S(40), True),
                        "versions": (A(_VERSION, 20), False)}), 50), True),
    "notebook": (A(O({"id": (ID, True), "type": (S(enum=BLOCK_TYPES), True), "text": (S(5000), False),
                      "ref": (_REF, False), "level": (INT(1, 3), False), "author": (S(enum=["user", "assistant-draft"]), True),
                      "created_at": (ISO, True), "modified_at": (ISO, True), "versions": (A(_VERSION, 20), False)}), 300), True),
    "annotations": (A(O({"id": (ID, True), "target": (_REF, True), "text": (S(2000, 1), True), "created_at": (ISO, True)}), 200), True),
    "plans": (A(O({"id": (ID, True), "question": (S(500), True), "created_at": (ISO, True), "revision": (INT(1, 1000), True),
                   "intent": ({"t": "json", "max_bytes": 4000, "depth": 4}, True),
                   "steps": (A(O({"id": (ID, True), "capability": (S(40, 1), True), "status": (S(enum=STEP_STATUS), True),
                                  "depends": (A(ID, 20), True), "title": (S(200), True),
                                  "result": ({"t": "map", "keys": r"^[a-z_]{1,40}$", "max": 30, "values": _SCALAR}, False),
                                  "error": (S(1000), False), "started_at": (ISO, False), "finished_at": (ISO, False),
                                  "inputs": ({"t": "json", "max_bytes": 2000, "depth": 3}, False), "note": (S(500), False),
                                  "optional": (BOOL, False)}), 20), True),
                   "confirmed": (BOOL, True)}), 30), True),
    "experiments": (A(O({"id": (ID, True), "template": (S(40, 1), True), "created_at": (ISO, True),
                         "status": (S(enum=["defined", "completed", "failed", "refused"]), True),
                         "config": ({"t": "json", "max_bytes": 10000, "depth": 5}, True),
                         "result": ({"t": "json", "max_bytes": 40000, "depth": 6}, False)}), 30), True),
    "missions": (A(O({"template_id": (S(40, 1), True), "started_at": (ISO, True),
                      "status": (S(enum=["active", "completed", "abandoned"]), True),
                      "reviews": (A(O({"task_id": (S(40, 1), True), "note": (S(1000), True), "at": (ISO, True)}), 50), True)}), 20), True),
    "workflows": (A({"t": "json", "max_bytes": 10000, "depth": 5}, 20), False),
    # v0.7 (optional, so 0.6 sessions stay valid): counterfactual scenarios (CF-1 results, compacted), synthetic scenarios
    # (SYNOBS-1 summaries), causal diagrams (user-proposed edges with their labels) and autopilot runs (permission level, steps)
    "scenarios": (A({"t": "json", "max_bytes": 20000, "depth": 6}, 40), False),
    "synthetic": (A({"t": "json", "max_bytes": 12000, "depth": 6}, 30), False),
    "causal": (A({"t": "json", "max_bytes": 6000, "depth": 5}, 30), False),
    "autopilot": (A({"t": "json", "max_bytes": 12000, "depth": 6}, 20), False),
    # v0.8 (optional): negative-knowledge entries you record, human review comments and responses, the research protocol
    # (pre-analysis plan, lock and amendments), the blind-analysis state, structured arguments, and debugging sessions
    "negative": (A({"t": "json", "max_bytes": 4000, "depth": 4}, 200), False),
    "reviews": (A({"t": "json", "max_bytes": 4000, "depth": 4}, 200), False),
    "protocol": ({"t": "json", "max_bytes": 40000, "depth": 6}, False),
    "blind": ({"t": "json", "max_bytes": 6000, "depth": 4}, False),
    "arguments": (A({"t": "json", "max_bytes": 12000, "depth": 6}, 30), False),
    "debug": (A({"t": "json", "max_bytes": 4000, "depth": 4}, 50), False),
    # v0.9 (optional): challenge-ledger statuses you set (ADV-1: acknowledged with a note, or resolved with a reference to a
    # recorded item), the investigation's completion (GATE-1 outcome when you marked it complete), frozen time capsules
    # (CAPSULE-1 digests of what was known), autonomous research-cycle runs (permission level, every step) and handoffs
    "challenges": (A({"t": "json", "max_bytes": 3000, "depth": 3}, 300), False),
    "completion": ({"t": "json", "max_bytes": 6000, "depth": 4}, False),
    "capsules": (A({"t": "json", "max_bytes": 20000, "depth": 6}, 20), False),
    "cycles": (A({"t": "json", "max_bytes": 12000, "depth": 6}, 20), False),
    "examined": (A(S(200, 1), 500), True),
    "history": (A(O({"seq": (INT(1, 10 ** 9), True), "at": (ISO, True), "kind": (S(40, 1, r"^[a-z_.]{1,40}$"), True),
                     "summary": (S(300), True), "ref": (OPT(S(300)), True), "h": (HEX64, False)}), 2000), True),
    "content_hash": (HEX64, False),
})

_ = NUM  # re-exported constructor kept for schema extensions


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new(name: str, target_id: str | None = None, at: str | None = None) -> dict:
    t = at or now()
    s = {"schema": SCHEMA_ID, "session_id": secrets.token_hex(6), "name": (name or "Research session").strip()[:120] or "Research session",
         "created_at": t, "modified_at": t, "target_id": target_id, "question": {"id": None, "text": ""}, "runs": [],
         "active_hash": None, "hypotheses": [], "notebook": [], "annotations": [], "plans": [], "experiments": [],
         "missions": [], "workflows": [], "examined": [],
         "history": [{"seq": 1, "at": t, "kind": "session.create", "summary": f"Session created{' for ' + target_id if target_id else ''}", "ref": None}]}
    return finalize(s)


def body_hash(s: dict) -> str:
    return canon.digest({k: v for k, v in s.items() if k != "content_hash"})


GENESIS = "0" * 64


def chain_hash(prev: str, entry: dict) -> str:
    """Evidence-vault link (VAULT-1): SHA-256 of the previous link + the entry's canonical text. Mirrored in sessioncore.js."""
    import hashlib
    body = canon.dumps({k: entry[k] for k in ("seq", "at", "kind", "summary", "ref")})
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def chain_fill(history: list) -> list:
    """Give every entry without a link its link, in order. Existing links are never recomputed (an edited entry stays broken)."""
    out, prev = [], None
    for i, e in enumerate(history):
        if "h" not in e:
            e = {**e, "h": chain_hash(prev if prev is not None else GENESIS, e)}
        out.append(e)
        prev = e["h"]
    return out


def verify_chain(history: list) -> dict:
    """{'links', 'verified', 'anchor', 'broken': [seq], 'unchained': n}. The first entry verifies against the genesis value
    unless older entries were trimmed (then it is an unverifiable anchor)."""
    broken, verified, anchor, unchained = [], 0, None, 0
    prev = None
    for i, e in enumerate(history):
        if "h" not in e:
            unchained += 1
            prev = None
            continue
        if prev is None:
            if i == 0 and e["seq"] == 1 and chain_hash(GENESIS, e) == e["h"]:
                verified += 1
            elif i == 0 or "h" not in history[i - 1]:
                anchor = anchor or e["seq"]
            else:
                broken.append(e["seq"])
        elif chain_hash(prev, e) == e["h"]:
            verified += 1
        else:
            broken.append(e["seq"])
        prev = e["h"]
    return {"method": "VAULT-1", "links": len(history) - unchained, "verified": verified, "anchor": anchor, "broken": broken, "unchained": unchained,
            "note": "A hash chain detects an edited or removed entry unless every later link and the session hash are recomputed too; it is not a signature."}


def finalize(s: dict) -> dict:
    s = dict(s)
    s["history"] = chain_fill(s.get("history", []))
    s["content_hash"] = body_hash(s)
    return s


def validate(s) -> list[str]:
    """Schema violations plus the cross-field rules (empty list = valid)."""
    if not isinstance(s, dict):
        return ["$: a session must be an object"]
    if s.get("schema") != SCHEMA_ID:
        got = s.get("schema")
        return [f"$.schema: {got!r} is not a supported session format (expected {SCHEMA_ID})"]
    errs = check(SESSION_SCHEMA, s)
    if errs:
        return errs
    try:
        size = len(canon.dumps(s).encode("utf-8"))
    except canon.CanonError as e:
        return [f"$: {e}"]
    if size > MAX_BYTES:
        return [f"$: session larger than {MAX_BYTES} bytes"]
    seqs = [h["seq"] for h in s["history"]]
    if seqs != sorted(seqs) or len(set(seqs)) != len(seqs):
        errs.append("$.history: sequence numbers must increase")
    hashes = {r["content_hash"] for r in s["runs"]}
    if s["active_hash"] is not None and s["active_hash"] not in hashes:
        errs.append("$.active_hash: not one of the session's runs")
    for p in s["plans"]:
        ids = [st["id"] for st in p["steps"]]
        for st in p["steps"]:
            missing = [d for d in st["depends"] if d not in ids[:ids.index(st["id"])]]
            if missing:
                errs.append(f"$.plans[{p['id']}].{st['id']}: depends on steps that do not precede it: {', '.join(missing)}")
    vc = verify_chain(s["history"])
    if vc["broken"]:
        errs.append(f"$.history: evidence-vault chain broken at entry {vc['broken'][0]} (an entry was edited or removed)")
    return errs


def verify(s: dict) -> dict:
    """{'valid', 'errors', 'hash_ok', 'stated', 'computed'} for an imported session."""
    errs = validate(s)
    if errs:
        return {"valid": False, "errors": errs, "hash_ok": None, "stated": s.get("content_hash") if isinstance(s, dict) else None, "computed": None}
    comp = body_hash(s)
    stated = s.get("content_hash")
    return {"valid": True, "errors": [], "hash_ok": stated == comp if stated else None, "stated": stated, "computed": comp}


def log(s: dict, kind: str, summary: str, ref: str | None = None, at: str | None = None) -> dict:
    s = dict(s)
    seq = (s["history"][-1]["seq"] + 1) if s["history"] else 1
    s["history"] = (s["history"] + [{"seq": seq, "at": at or now(), "kind": kind, "summary": summary[:300], "ref": ref}])[-2000:]
    return s


def from_saved_record(saved: dict, at: str | None = None) -> dict:
    """Convert a v0.5 saved investigation (record + context) into a session; the saved record itself is untouched."""
    t = at or now()
    rec = saved.get("investigation") or {}
    ctx = saved.get("context") or {}
    s = new(saved.get("name") or "Imported investigation", saved.get("target_id"), at=t)
    h = saved.get("content_hash") or rec.get("content_hash")
    iid = saved.get("investigation_id")
    if h and iid:
        s["runs"] = [{"investigation_id": iid, "content_hash": h, "label": "saved investigation", "attached_at": t,
                      "params": clean_params(saved.get("parameters") or rec.get("parameters") or {})}]
        s["active_hash"] = h
    if isinstance(ctx.get("question"), str):
        s["question"] = {"id": ctx["question"], "text": str(ctx.get("question_text") or "")[:500]}
    for x in (ctx.get("hypotheses") or [])[:50]:
        if isinstance(x, dict) and isinstance(x.get("statement"), str) and x["statement"].strip():
            s["hypotheses"].append({"id": str(x.get("id") or f"U{len(s['hypotheses'])}")[:40], "statement": x["statement"][:1000],
                                    "tests": [str(t)[:60] for t in x.get("tests", []) if isinstance(t, str)][:30],
                                    "kind": "interpretation", "created_at": str(x.get("created_at") or t)[:40]})
    s = log(s, "session.migrate", f"Converted from saved investigation “{saved.get('name', '')}” (v0.5 record)", saved.get("record_id"), at=t)
    return finalize(s)


def clean_params(p: dict) -> dict:
    """The analysis parameters a session keeps with a run: known names, numbers or booleans only."""
    from . import analysis
    return {k: v for k, v in (p or {}).items() if k in analysis.DEFAULTS and isinstance(v, (bool, int, float)) and v is not None}


def summary(s: dict) -> dict:
    return {"session_id": s["session_id"], "name": s["name"], "target_id": s["target_id"], "modified_at": s["modified_at"],
            "created_at": s["created_at"], "question": s["question"]["text"], "n_runs": len(s["runs"]),
            "n_notes": len(s["notebook"]), "n_hypotheses": len(s["hypotheses"]), "content_hash": s.get("content_hash"),
            "run_hashes": [r["content_hash"] for r in s["runs"]], "methods": sorted({h["kind"].split(".")[0] for h in s["history"]})}
