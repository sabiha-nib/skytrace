"""MEMORY-1: research memory across investigations.

Built from every investigation Skytrace holds (runs in this server process, saved records; in the static preview, the runs
recorded at build time) and their epistemic reports (EPI-1, KBOUND-1, NEG-1, QFORGE-1, HYPO-1). Session-held memory (your
hypotheses and their wordings, decisions, reproductions, negative entries) is added in the browser by `intelcore.js`.

Memory items: observation summaries, conclusions, explanations (viable or rejected by rule), failures and inconclusive results,
unresolved questions, and the assumptions conclusions rest on. Every item names the record (content hash) and the field it
came from, the concepts it concerns, and a memory status:

  M1 verified      a recorded count, measurement summary or recorded failure (EPI-1 status measured or derived) from a record
                   whose content hash recomputes
  M2 provisional   a conclusion that is model-dependent, assumption-dependent or unresolved (KBOUND-1 region other than
                   'established'), and every explanation or question
  M3 assumption    an analysis choice or method premise a conclusion rests on
  M4 outdated      superseded: a later record of the same target answered the same question with a newer analysis version
                   or a different method version
  M5 unverifiable  the record's content hash does not recompute
  M6 an explanation or hypothesis is never 'verified': 'consistent' means still viable; 'contradicted' means rejected by a
     stated HYPO-1 rule, not disproved

Concepts come from structured fields (question, hypothesis id, refusal code, NEG-1 category), never from free text. Recall maps a
query to concepts through a fixed vocabulary (CONCEPTS) and ranks items by the number of matched concepts, then recency. It is
not semantic search, and it says which term matched which concept. Failure warnings match a planned action against earlier
failures of the same target and question, or with a shared concept, and quote the earlier reason.
"""

from __future__ import annotations

import re

from . import counterfactual as cf

METHOD = "MEMORY-1"
STATUSES = ["verified", "provisional", "assumption", "outdated", "unverifiable"]
STATUS_RULES = {"M1": "a recorded count, measurement summary or recorded failure from a record whose content hash recomputes is 'verified'",
                "M2": "a conclusion that is not established, and every explanation or question, is 'provisional'",
                "M3": "an analysis choice or method premise is an 'assumption'",
                "M4": "an item superseded by a later record of the same target (newer analysis version or other method version for that question) is 'outdated'",
                "M5": "an item from a record whose content hash does not recompute is 'unverifiable'",
                "M6": "an explanation is never 'verified'; 'consistent' means still viable, 'contradicted' means rejected by a stated rule"}
KINDS = ["observation", "conclusion", "explanation", "failure", "question", "assumption"]
CONCEPTS = {
    "variability": ("Brightness change", ["brightness", "variability", "variable", "dimming", "dims", "dimmed", "brightening", "flux change", "light curve", "photometric change", "fading"]),
    "motion": ("Proper motion", ["proper motion", "motion", "moving", "moves", "astrometric", "position change", "astrometry", "drift"]),
    "data_quality": ("Data quality", ["data quality", "quality", "usable", "unusable", "flags", "flagged"]),
    "calibration": ("Calibration", ["calibration", "calibrated", "reference ratio", "zero point", "calcheck", "error scale"]),
    "error_model": ("Error model", ["error model", "underestimated", "uncertainty", "uncertainties", "noise", "scatter"]),
    "wavelength": ("Wavelength matching", ["wavelength", "spectral", "channel", "matched pair", "wlmatch", "colour", "color"]),
    "blending": ("Blending and neighbours", ["blend", "blending", "blended", "neighbour", "neighbor", "contamination", "crowding"]),
    "registration": ("Registration", ["registration", "alignment", "plate solution", "astrometric solution", "wcs"]),
    "parallax": ("Parallax", ["parallax", "distance"]),
    "reference_stars": ("Reference stars", ["reference star", "reference stars", "references", "comparison stars", "gaia"]),
    "chromatic": ("Chromatic offsets", ["chromatic", "per-detector", "detector-dependent"]),
    "detector": ("Detector effects", ["detector", "edge", "pixel", "instrumental", "artefact", "artifact", "psf"]),
    "sample_size": ("Too few measurements", ["too few", "sample size", "few visits", "few epochs", "insufficient", "not enough"]),
    "cause": ("Physical cause", ["cause", "physical", "mechanism", "why"]),
    "discovery": ("Discovery claims", ["discovery", "new object", "novel"]),
    "archive": ("Archive access", ["archive", "irsa", "simbad", "network", "unavailable", "download"]),
}
HYP_CONCEPT = {"V-INTRINSIC": "variability", "V-CALIB": "calibration", "V-ERRMODEL": "error_model", "V-WAVELENGTH": "wavelength", "V-BLEND": "blending",
               "M-CATALOGUE": "motion", "M-STATIC": "motion", "M-REGISTRATION": "registration", "M-PARALLAX": "parallax", "M-REFS": "reference_stars",
               "M-CHROMATIC": "chromatic"}
CODE_CONCEPT = [("blend", "blending"), ("neighbour", "blending"), ("edge", "detector"), ("flag", "detector"), ("wavelength", "wavelength"), ("channel", "wavelength"),
                ("calib", "calibration"), ("reference", "reference_stars"), ("too_few", "sample_size"), ("few", "sample_size"), ("environment:", "archive"),
                ("Q-CAUSE", "cause"), ("Q-DISCOVERY", "discovery"), ("Q-DIST", "parallax"), ("PAIRDIFF-2", "calibration"), ("CALCHECK", "error_model")]
QUESTION_OF_CAT = {"variability": "variability", "motion": "motion", "data_quality": "data_quality"}


def _concepts_for(*codes) -> list[str]:
    out = []
    for c in codes:
        if not c:
            continue
        c = str(c)
        if c in CONCEPTS:
            out.append(c)
        if c in HYP_CONCEPT:
            out.append(HYP_CONCEPT[c])
        for pat, con in CODE_CONCEPT:
            if pat in c:
                out.append(con)
    return sorted(set(out))


def _q_of(text: str) -> str | None:
    for q in ("variability", "motion", "data_quality"):
        if q in (text or ""):
            return q
    return None


STEP_Q = {"pairs": "variability", "variability": "variability", "spectral_context": "variability", "spectrum": "variability",
          "astrometry": "motion", "references": "motion", "select": "data_quality", "discover": "data_quality", "inspect": "data_quality",
          "measure": "data_quality"}


def _q_from_source(record: dict, src) -> str | None:
    """The question a recorded failure concerns, from where it is recorded: a HYPO-1 explanation id (V- brightness, M- motion),
    or the pipeline step of the cited record event. None when the source names no question."""
    s = str(src or "")
    m = re.match(r"HYPO-1:([VM])-", s)
    if m:
        return "variability" if m.group(1) == "V" else "motion"
    m = re.match(r"\$\.events\[(\d+)\]", s)
    if m and int(m.group(1)) < len(record.get("events", [])):
        return STEP_Q.get(record["events"][int(m.group(1))]["step"])
    m = re.match(r"\$\.events\[(\w+)\]", s)
    if m:
        return STEP_Q.get(m.group(1))
    return None


def build(corpus: list[dict]) -> dict:
    """corpus: [{iid, record, epistemic, origin, saved}] — `epistemic` is the epistemic report of that record."""
    items, invs = [], []
    for c in corpus:
        rec, epi = c["record"], c["epistemic"]
        h = rec["content_hash"]
        ok = cf.record_hash(rec) == h
        p = rec.get("parameters", {})
        tgt = p.get("bundle") or rec.get("target")             # the target id (bundle); the display name is target_name
        t = rec.get("created_at")
        base = {"target": tgt, "target_name": rec.get("target"), "record": h, "iid": c.get("iid"), "origin": c.get("origin"), "created_at": t, "synthetic": p.get("bundle_kind") == "synthetic"}
        invs.append({**base, "name": (c.get("saved") or {}).get("name"), "analysis_version": p.get("analysis_version"), "methods": p.get("methods") or {},
                     "parameters": {k: v for k, v in p.items() if k not in ("methods", "bundle_manifest_sha256")}, "hash_ok": ok})

        def add(kind, local, statement, status, rule, ref, concepts, **extra):
            if not ok:
                status, rule = "unverifiable", "M5"
            items.append({"id": f"mem:{h[:12]}:{local}", "kind": kind, "statement": str(statement)[:400], "status": status, "status_rule": rule,
                          "source": {"record": h, "ref": ref}, "concepts": concepts, **base, **extra})
        obs = [n for n in epi["graph"]["nodes"] if n["kind"] == "observation" and not n.get("excluded")]
        meas = [n for n in epi["graph"]["nodes"] if n["kind"] == "measurement"]
        dets = sorted({n.get("detector") for n in obs if n.get("detector") is not None})
        mjd = sorted(n["mjd"] for n in obs if isinstance(n.get("mjd"), (int, float)))
        add("observation", "obs", f"{len(obs)} observations of {rec.get('target')} on detectors {', '.join('D%s' % d for d in dets)}"
            + (f", MJD {mjd[0]:.1f}–{mjd[-1]:.1f}" if mjd else "") + f"; {len(meas)} measured", "verified", "M1", "graph:observation+measurement",
            ["data_quality"], n_observations=len(obs), n_measured=len(meas))
        for b in epi["boundary"]["items"]:
            if b["kind"] == "claim":
                q = b["id"].split(":", 1)[1]
                est = b["region"] == "established"
                add("conclusion", b["id"], b["statement"], "verified" if est and b.get("status") in ("measured", "derived") else "provisional",
                    "M1" if est and b.get("status") in ("measured", "derived") else "M2", f"graph:{b['id']}", _concepts_for(q),
                    question=q, category=b["category"], region=b["region"], method_versions=_methods_for(p, q))
                for a in (b.get("assumptions") or [])[:8]:
                    add("assumption", f"{b['id']}:{a['id']}", f"{q} rests on {a['label']}", "assumption", "M3", f"graph:{a['id']}", _concepts_for(q), question=q)
        for qq in (c.get("hypotheses") or {}).get("questions", []):
            for hy in qq["hypotheses"]:
                st = hy.get("overall")
                add("explanation", f"hyp:{hy['id']}", hy["statement"], "provisional", "M6", f"HYPO-1:{hy['id']}", _concepts_for(hy["id"], qq["question"]),
                    question=qq["question"], hypothesis=hy["id"], hypothesis_status=st,
                    standing="rejected by rule" if st == "contradicted" else "still viable" if st in ("consistent", "inconclusive", "not_tested") else st)
        for k, n in enumerate(epi["negative"]["entries"]):
            q = _q_from_source(rec, n.get("source")) or _q_of(n.get("attempted", "") + " " + str(n.get("source")))
            add("failure", f"neg{k}", f"{n['attempted']}: {n.get('happened') or n.get('why')}", "verified" if n["category"] != "known limitation" else "provisional",
                "M1" if n["category"] != "known limitation" else "M2", n.get("source"),
                _concepts_for(n.get("source"), n.get("category"), q, *(n.get("inputs") or [])[:3]) or _concepts_for(q),
                question=q, category=n["category"], distinction=n["distinction"], why=n.get("why"), failure=n.get("failure"), unblock=n.get("unblock"))
        for qn in epi["questions"]["questions"]:
            if qn["category"] != "directly answerable":
                add("question", qn["id"], qn["question"], "provisional", "M2", qn.get("prompted_by"), _concepts_for(qn["id"], _q_of(qn["question"].lower()), *(qn.get("missing") or [])[:2]),
                    category=qn["category"], missing=qn.get("missing"))
    _mark_outdated(items, invs)
    counts = {s: sum(x["status"] == s for x in items) for s in STATUSES}
    return {"method": METHOD, "statuses": STATUSES, "status_rules": STATUS_RULES, "concepts": {k: {"label": v[0], "terms": v[1]} for k, v in CONCEPTS.items()},
            "investigations": invs, "items": items, "counts": counts, "by_kind": {k: sum(x["kind"] == k for x in items) for k in KINDS},
            "evolution": evolution(items, invs),
            "note": "Memory holds what earlier investigations recorded, with where each item came from. It never promotes an explanation to a fact: "
                    "an explanation stays provisional however often it was consistent. Recall uses a fixed concept vocabulary, not semantic search."}


def _methods_for(p: dict, q: str) -> dict:
    m = p.get("methods") or {}
    keys = {"variability": ("variability", "pairing", "calibration"), "motion": ("astrometry", "centroid", "references"), "data_quality": ("flags", "photometry")}
    return {k: v for k, v in m.items() if any(s in k for s in keys.get(q, ()))}


def _mark_outdated(items: list[dict], invs: list[dict]) -> None:
    """M4: an item from record R is outdated when a later record of the same target answered the same question with a newer
    analysis version or other method versions for that question."""
    by_target = {}
    for i in invs:
        by_target.setdefault(i["target"], []).append(i)
    newer = {}
    for tgt, rs in by_target.items():
        for r in rs:
            later = [x for x in rs if x["created_at"] > r["created_at"]]
            newer[r["record"]] = later
    for x in items:
        if x["kind"] not in ("conclusion", "assumption") or x["status"] == "unverifiable":
            continue
        own = next(i for i in invs if i["record"] == x["record"])
        q = x.get("question")
        for r in newer.get(x["record"], []):
            if (r["analysis_version"] or "") > (own["analysis_version"] or "") or _methods_for({"methods": r["methods"]}, q) != _methods_for({"methods": own["methods"]}, q):
                x["status"], x["status_rule"], x["superseded_by"] = "outdated", "M4", r["record"]
                break


def evolution(items: list[dict], invs: list[dict]) -> list[dict]:
    """How each conclusion moved across the records of one target, in creation order, with what differed between them."""
    out = []
    targets = sorted({i["target"] for i in invs})
    for tgt in targets:
        rs = sorted([i for i in invs if i["target"] == tgt], key=lambda i: (i["created_at"], i["record"]))
        for q in ("data_quality", "motion", "variability"):
            steps, prev = [], None
            for r in rs:
                c = next((x for x in items if x["record"] == r["record"] and x["kind"] == "conclusion" and x.get("question") == q), None)
                if not c:
                    continue
                diff = []
                if prev:
                    diff = sorted(k for k in set(r["parameters"]) | set(prev["parameters"]) if k not in ("bundle", "bundle_kind") and r["parameters"].get(k) != prev["parameters"].get(k))
                prev_cat = steps[-1]["category"] if steps else None
                steps.append({"record": r["record"], "created_at": r["created_at"], "category": c["category"], "region": c["region"], "status": c["status"],
                              "changed": prev_cat is not None and prev_cat != c["category"], "differs_in": diff})
                prev = r
            if steps:
                out.append({"target": tgt, "question": q, "steps": steps, "n_changes": sum(s["changed"] for s in steps)})
    return out


_WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


def query_concepts(query: str) -> list[dict]:
    """Concepts named by a query: a vocabulary term (or the concept's own id) appearing as whole words."""
    q = " " + " ".join(_WORD.findall((query or "").lower())) + " "
    out = []
    for cid, (label, terms) in CONCEPTS.items():
        for term in [cid.replace("_", " ")] + terms:
            t = " " + " ".join(_WORD.findall(term.lower())) + " "
            if t.strip() and t in q:
                out.append({"id": cid, "label": label, "via": term})
                break
    return out


def recall(mem: dict, query: str, limit: int = 30) -> dict:
    cs = query_concepts(query)
    ids = {c["id"] for c in cs}
    scored = []
    for x in mem["items"]:
        m = sorted(ids & set(x["concepts"]))
        if m:
            scored.append((len(m), x["created_at"] or "", x["id"], m))
    scored.sort(key=lambda r: r[2])                       # deterministic tie-break by id
    scored.sort(key=lambda r: r[1], reverse=True)         # then most recent
    scored.sort(key=lambda r: r[0], reverse=True)         # most concepts first (stable sorts compose)
    return {"query": query, "concepts": cs, "results": [{"item": r[2], "matched": r[3]} for r in scored[:limit]], "n": len(scored),
            "rule": "items sharing the most query concepts first, then the most recent; concepts come from the fixed vocabulary",
            "note": "No concept recognised in the query." if not cs else None}


def warnings(mem: dict, target: str | None, actions: list[dict]) -> list[dict]:
    """Memory of failure. actions: [{id, label, question, concepts}]. W1 an earlier failure or inconclusive result for the same
    target and question; W2 an earlier failure for the same target sharing a concept with the action."""
    out, seen = [], {}
    for a in actions:
        for x in mem["items"]:
            if x["kind"] != "failure" or (target and x["target"] != target) or x.get("category") == "known limitation" \
                    or str(x.get("source", {}).get("ref", "")).startswith("environment:"):
                continue
            rule = None
            if a.get("question") and x.get("question") == a["question"]:
                rule = "W1"
            elif set(a.get("concepts") or []) & set(x["concepts"]):
                rule = "W2"
            if rule:
                key = (a["id"], x["statement"])
                if key in seen:                      # the same failure recorded by several runs: one warning, every record listed
                    seen[key]["records"].append(x["record"])
                    if rule == "W1":
                        seen[key]["rule"] = "W1"
                    continue
                w = {"action": a["id"], "action_label": a.get("label"), "memory": x["id"], "rule": rule, "target": x["target"], "record": x["record"],
                     "records": [x["record"]], "what_failed": x["statement"], "why": x.get("why"), "unblock": x.get("unblock")}
                seen[key] = w
                out.append(w)
    out.sort(key=lambda w: (w["rule"], w["action"], w["what_failed"]))
    return out
