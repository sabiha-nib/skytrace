"""SCI-ENTITY-1: one envelope for every scientific object Skytrace knows about.

Phase 9 engines (research memory, discovery genome, unknown-universe map, integrity gate, multi-discovery network) do not read
records, graphs and sessions each in their own way. They read entities: the same object, wherever it came from, carries

    id          stable: "<type>:<local id>" (the local id is the EPI-1 node id, a session item id or a record field)
    type        one of TYPES (the 22 of the Phase 9 brief, plus four that EPI-1 already distinguishes)
    version     integer ≥ 1 (records are immutable: 1; a session hypothesis: number of recorded wordings; a method: its ID suffix)
    provenance  {source, ref, hash}: where it is recorded (a record event, a graph node, a session item, a registry entry), and the
                content hash of that record or session
    created_at  ISO 8601 time of the record, file or session item
    status      an EPI-1 epistemic status, or "hypothetical" (scenarios) or "not a statement" (instruments, datasets as containers,
                methods, transformations, provenance events)
    status_rule the rule that assigned the status (EPI-1 S1–S10, or E1–E6 below)

Entity rules (beyond EPI-1):
  E1  an investigation and its dataset take the status of their data (synthetic → simulated, archive → directly recorded)
  E2  instruments, methods, transformations and provenance events are 'not a statement'
  E3  counterfactual scenarios are 'hypothetical'
  E4  experiments, reproductions and rule-derived challenges are 'derived' (a computation or a rule applied to recorded values)
  E5  anything written in the session (hypotheses, causal proposals, decisions, negative entries) is 'user-authored'
  E6  a calibration estimate is 'derived'

validate() checks every field, and that the provenance reference resolves against the sources it was built from. Nothing here
computes science; it only names what exists.
"""

from __future__ import annotations

import re

from . import epistemic as epi

METHOD = "SCI-ENTITY-1"
TYPES = ["investigation", "observation", "dataset", "measurement", "instrument", "calibration", "transformation", "method", "model",
         "hypothesis", "evidence", "claim", "uncertainty", "assumption", "experiment", "counterfactual", "causal_relationship", "challenge",
         "reproduction", "research_decision", "conclusion", "provenance_event",
         # EPI-1 distinctions kept as their own types rather than folded into one of the above
         "derived_quantity", "inference", "limitation", "contradiction"]
STATUSES = list(epi.STATUSES) + ["hypothetical", "not a statement"]
SOURCES = ["record", "epistemic", "registry", "discovery", "frontier", "session"]
RULES = {"E1": "an investigation and its dataset take the status of their data (synthetic → simulated, archive → directly recorded)",
         "E2": "instruments, methods, transformations and provenance events are 'not a statement'",
         "E3": "counterfactual scenarios are 'hypothetical'",
         "E4": "experiments, reproductions and rule-derived challenges are 'derived'",
         "E5": "anything written in the session is 'user-authored'",
         "E6": "a calibration estimate is 'derived'"}
KIND_TYPE = {"source": "dataset", "observation": "observation", "measurement": "measurement", "transformation": "transformation",
             "method": "method", "model": "model", "assumption": "assumption", "uncertainty": "uncertainty", "inference": "inference",
             "hypothesis": "hypothesis", "claim": "claim", "limitation": "limitation", "contradiction": "contradiction", "conclusion": "conclusion"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def _derived_type(nid: str) -> str:
    if nid.startswith(("pair:", "fit:")):
        return "evidence"
    if nid.startswith("scale:"):
        return "calibration"
    return "derived_quantity"


def _method_version(mid: str) -> int:
    m = re.search(r"-(\d+)$", mid.split("/")[0])
    return int(m.group(1)) if m else 1


def env(etype, local, version, source, ref, created_at, status, rule, label, h=None, **data) -> dict:
    return {"id": f"{etype}:{local}", "type": etype, "version": int(version), "provenance": {"source": source, "ref": ref, "hash": h},
            "created_at": created_at, "status": status, "status_rule": rule, "label": str(label)[:300],
            "data": {k: v for k, v in data.items() if v is not None}}


def investigation_entities(record: dict, graph: dict, frontier: dict | None = None, session: dict | None = None) -> list[dict]:
    """Every entity of one investigation: the record, its reasoning graph (EPI-1), its rule-derived challenges (ASL-1, when the
    frontier report is given) and, when a session is given, the session's own objects."""
    h = record.get("content_hash")
    t = record.get("created_at")
    params = record.get("parameters", {})
    synthetic = params.get("bundle_kind") == "synthetic"
    dstat = ("simulated", "E1") if synthetic else ("directly recorded", "E1")
    out = [env("investigation", h[:16], 1, "record", "$", t, *dstat, f"investigation of {record.get('target')}",
               h, target=record.get("target"), bundle=params.get("bundle"), analysis_version=params.get("analysis_version")),
           env("dataset", f"bundle:{params.get('bundle')}", 1, "record", "$.parameters.bundle_manifest_sha256", t, *dstat,
               f"bundle {params.get('bundle')} ({params.get('bundle_kind')})", h, manifest_sha256=params.get("bundle_manifest_sha256"))]
    detectors = sorted({n.get("detector") for n in graph["nodes"] if n["kind"] == "observation" and n.get("detector") is not None})
    for d in detectors:
        out.append(env("instrument", f"SPHEREx-D{d}", 1, "record", "$.events[step=measure].data.detector", t, "not a statement", "E2",
                       f"SPHEREx detector D{d}", h))
    for n in graph["nodes"]:
        kind = n["kind"]
        etype = _derived_type(n["id"]) if kind == "derived" else KIND_TYPE[kind]
        if kind in ("method", "transformation"):
            status, rule = "not a statement", "E2"
        elif etype == "calibration":
            status, rule = "derived", "E6"
        else:
            status, rule = n.get("status"), n.get("status_rule")
        version = _method_version(n["id"][7:]) if kind == "method" else 1
        ref = f"$.events[{n['event']}]" if isinstance(n.get("event"), int) else f"graph:{n['id']}"
        src = "record" if ref.startswith("$") else "epistemic"
        created = n.get("retrieved_at") if kind == "source" and n.get("retrieved_at") else t
        out.append(env(etype, n["id"], version, src, ref, created, status, rule, n["label"], h, node=n["id"]))
    for c in (frontier or {}).get("asl", {}).get("challenges", []):
        out.append(env("challenge", c["id"], 1, "frontier", f"asl:{c['id']}", t, "derived", "E4", c.get("issue") or c["id"], h,
                       challenge_rule=c.get("rule"), severity=c.get("severity"), mode=c.get("mode")))
    if session:
        out += session_entities(session)
    return out


def session_entities(s: dict) -> list[dict]:
    """The session's own objects. Statuses follow E3–E5; versions count recorded wordings."""
    h = s.get("content_hash")
    out = []
    for x in s.get("hypotheses") or []:
        out.append(env("hypothesis", f"user:{x['id']}", 1 + len(x.get("versions") or []), "session", f"session:hypotheses/{x['id']}", x.get("created_at"),
                       "user-authored", "E5", x.get("statement"), h, tests=x.get("tests")))
    for x in s.get("experiments") or []:
        out.append(env("experiment", x["id"], 1, "session", f"session:experiments/{x['id']}", x.get("created_at"), "derived", "E4",
                       f"{x.get('template')} experiment ({x.get('status')})", h, template=x.get("template"), run_status=x.get("status")))
    for k, x in enumerate(s.get("scenarios") or []):
        sid = (x or {}).get("scenario_hash") or f"{k}"
        out.append(env("counterfactual", str(sid)[:16], 1, "session", f"session:scenarios/{k}", (x or {}).get("at") or s.get("created_at"),
                       "hypothetical", "E3", (x or {}).get("label") or "counterfactual scenario", h))
    for k, x in enumerate(s.get("causal") or []):
        out.append(env("causal_relationship", f"user:{k}", 1, "session", f"session:causal/{k}", (x or {}).get("at") or s.get("created_at"),
                       "user-authored", "E5", f"{(x or {}).get('from')} — {(x or {}).get('rel')} — {(x or {}).get('to')}", h))
    for k, x in enumerate(s.get("negative") or []):
        out.append(env("limitation", f"user:{(x or {}).get('id') or k}", 1, "session", f"session:negative/{k}", (x or {}).get("at") or s.get("created_at"),
                       "user-authored", "E5", (x or {}).get("attempted") or "negative-knowledge entry", h))
    for k, x in enumerate(s.get("debug") or []):
        if (x or {}).get("kind") == "reproduction":
            out.append(env("reproduction", f"{k}", 1, "session", f"session:debug/{k}", x.get("at") or s.get("created_at"), "derived", "E4",
                           f"reproduction: {x.get('verdict')}", h, verdict=x.get("verdict")))
    for e in s.get("history") or []:
        if e.get("kind") == "decision.record":
            out.append(env("research_decision", f"seq{e['seq']}", 1, "session", f"session:history/{e['seq']}", e.get("at"), "user-authored", "E5", e.get("summary"), h))
        out.append(env("provenance_event", f"seq{e['seq']}", 1, "session", f"session:history/{e['seq']}", e.get("at"), "not a statement", "E2",
                       f"{e.get('kind')}: {e.get('summary')}", h))
    return out


def resolver(record: dict, graph: dict, frontier: dict | None = None, session: dict | None = None):
    """A function that says whether a provenance reference points at something that exists."""
    n_ev = len(record.get("events", []))
    ids = {n["id"] for n in graph["nodes"]}
    asl = {c["id"] for c in (frontier or {}).get("asl", {}).get("challenges", [])}
    s = session or {}
    seqs = {str(e.get("seq")) for e in s.get("history") or []}

    def ok(ref: str) -> bool:
        m = re.fullmatch(r"\$\.events\[(\d+)\]", ref)
        if m:
            return int(m.group(1)) < n_ev
        if ref in ("$", "$.parameters.bundle_manifest_sha256", "$.events[step=measure].data.detector"):
            return True
        if ref.startswith("graph:"):
            return ref[6:] in ids
        if ref.startswith("asl:"):
            return ref[4:] in asl
        m = re.fullmatch(r"session:(\w+)/(.+)", ref)
        if m:
            field, key = m.groups()
            if field == "history":
                return key in seqs
            items = s.get(field) or []
            return any(str((x or {}).get("id")) == key for x in items) or (key.isdigit() and int(key) < len(items))
        return False
    return ok


def validate(entities: list[dict], resolves=None) -> list[str]:
    """Errors in a list of entities: unknown type or status, bad version or time, missing or unresolvable provenance, duplicates."""
    errs, seen = [], set()
    for x in entities:
        i = x.get("id")
        if not isinstance(i, str) or ":" not in i:
            errs.append(f"{i}: id must be '<type>:<local id>'")
            continue
        if i in seen:
            errs.append(f"{i}: duplicate id")
        seen.add(i)
        if x.get("type") not in TYPES or not i.startswith(x["type"] + ":"):
            errs.append(f"{i}: unknown type or id prefix {x.get('type')}")
        if not isinstance(x.get("version"), int) or x["version"] < 1:
            errs.append(f"{i}: version must be an integer ≥ 1")
        if x.get("status") not in STATUSES:
            errs.append(f"{i}: status {x.get('status')!r} is not an epistemic status")
        if not x.get("status_rule"):
            errs.append(f"{i}: no status rule")
        p = x.get("provenance") or {}
        if p.get("source") not in SOURCES or not p.get("ref"):
            errs.append(f"{i}: provenance needs a known source and a reference")
        elif resolves and not resolves(p["ref"]):
            errs.append(f"{i}: provenance reference {p['ref']} does not resolve")
        if not isinstance(x.get("created_at"), str) or not ISO.match(x["created_at"]):
            errs.append(f"{i}: created_at must be ISO 8601")
    return errs


def summary(entities: list[dict]) -> dict:
    by_type = {t: 0 for t in TYPES}
    by_status = {s: 0 for s in STATUSES}
    for x in entities:
        by_type[x["type"]] += 1
        by_status[x["status"]] += 1
    return {"method": METHOD, "n": len(entities), "by_type": by_type, "by_status": by_status, "rules": RULES,
            "note": "Every object Skytrace knows about, in one envelope with a stable id, a version, provenance, a creation time and an "
                    "epistemic status. Counts describe this investigation's record, not the sky."}
