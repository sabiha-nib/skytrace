"""MDNET-1: the multi-discovery network — stated relationships between investigations.

Nodes are investigations (records). An edge exists only when at least one rule below holds; every edge lists each rule
that holds, its basis (the recorded values compared) and its limitation. No relationship comes from a shared word or a
similarity score.

  N1 same target            both records analyse the same target; the edge lists the parameters that differ
  N2 conflicting conclusion same target and question, different outcome category (an analysis choice changed the answer)
  N3 shared anomaly         the same positive outcome category (variability_candidate, motion_detected, motion_inconsistent)
  N4 shared measurement     DGENOME-1: detectors overlap, wavelength coverage overlaps and baselines within a factor of 1.25
  N5 repeated weakness      the same CLAIMX-1 mode warns or fails for the same question in both
  N6 shared hypothesis      the same HYPO-1 explanation is viable (consistent so far or inconclusive) in both
  N7 reusable method        DGENOME-1: one record used a method the other did not, and the other recorded the inputs it needs
  N8 shared failure         the same NEG-1 refusal (category and quality code) occurs in both
  N9 related parameters     catalogue parallax or total proper motion within a factor of 1.25 (catalogue inputs, not results)

Limitations are stated per rule: sibling runs of one target share almost everything by construction (N1), and structural
matches (N3–N9) say the investigations share data, methods, weaknesses or inputs — not that the sources are physically related.
"""

from __future__ import annotations

import math

from . import dgenome

METHOD = "MDNET-1"
RULES = {"N1": ("same target", "sibling runs share data by construction; the parameter differences are what distinguish them"),
         "N2": ("conflicting conclusion", "the answer depends on an analysis choice; neither run is thereby wrong"),
         "N3": ("shared anomaly", "the same outcome category, reached by the same rules; not evidence of a common cause"),
         "N4": ("shared measurement characteristics", "similar sampling and coverage; not physical similarity"),
         "N5": ("repeated analytical weakness", "the same stress mode is weak in both; check whether one cause explains both"),
         "N6": ("shared viable explanation", "the same explanation remains open in both; it is not more likely for that"),
         "N7": ("reusable method", "the inputs exist; whether the method suits the other target is not checked"),
         "N8": ("shared failure", "the same refusal recurs; it may be a property of the data or of the method"),
         "N9": ("related catalogue parameters", "catalogue inputs within 25 %; not a measured result of either investigation")}
POSITIVE = {"variability_candidate", "motion_detected", "motion_inconsistent"}
VIABLE = ("consistent so far", "inconclusive")
FACTOR = 1.25


def _outs(rec):
    return {o["question"]: o for e in rec["events"] if e["step"] == "assess" for o in e["data"].get("outcomes", [])}


def _cat(rec):
    a = next((e for e in rec["events"] if e["step"] == "astrometry"), None)
    c = ((a or {}).get("data") or {}).get("catalogue") or {}
    pm = math.hypot(c["pmra"], c["pmdec"]) if isinstance(c.get("pmra"), (int, float)) and isinstance(c.get("pmdec"), (int, float)) else None
    return {"parallax": c.get("parallax"), "pm": pm}


def _near(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > 0 and b > 0 and max(a, b) / min(a, b) <= FACTOR


def node(c: dict) -> dict:
    rec = c["record"]
    p = rec.get("parameters", {})
    return {"id": rec["content_hash"][:16], "record": rec["content_hash"], "iid": c.get("iid"), "target": p.get("bundle") or rec.get("target"), "target_name": rec.get("target"), "created_at": rec.get("created_at"),
            "origin": c.get("origin"), "synthetic": p.get("bundle_kind") == "synthetic",
            "categories": {q: o.get("category") for q, o in _outs(rec).items()},
            "parameters": {k: v for k, v in p.items() if k not in ("methods", "bundle_manifest_sha256", "bundle", "bundle_kind")}}


def build(corpus: list[dict]) -> dict:
    """corpus: [{iid, record, epistemic, hypotheses, origin}]."""
    nodes = [node(c) for c in corpus]
    gen = [{g["question"]: g for g in dgenome.genomes(c["record"], c["epistemic"], c.get("hypotheses") or {})} for c in corpus]
    steps = [{e["step"] for e in c["record"]["events"]} for c in corpus]
    edges = []
    for i in range(len(corpus)):
        for j in range(i + 1, len(corpus)):
            A, B = corpus[i], corpus[j]
            ra, rb = A["record"], B["record"]
            oa, ob = _outs(ra), _outs(rb)
            rel = []

            def add(rule, basis, **extra):
                rel.append({"rule": rule, "name": RULES[rule][0], "basis": basis, "limitation": RULES[rule][1], **extra})
            same = nodes[i]["target"] == nodes[j]["target"]
            if same:
                pa, pb = nodes[i]["parameters"], nodes[j]["parameters"]
                diff = sorted(k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))
                add("N1", f"both analyse {ra.get('target')}" + (f"; parameters differ: {', '.join(diff)}" if diff else "; identical parameters"), differs=diff)
                for q in sorted(set(oa) & set(ob)):
                    if oa[q].get("category") != ob[q].get("category"):
                        add("N2", f"{q}: {oa[q]['category']} vs {ob[q]['category']}", question=q)
            for q in sorted(set(oa) & set(ob)):
                if oa[q].get("category") in POSITIVE and oa[q].get("category") == ob[q].get("category"):
                    add("N3", f"{q}: both {oa[q]['category']}", question=q)
            for q in ("variability", "motion"):
                ga, gb = gen[i].get(q), gen[j].get(q)
                if not (ga and gb and ga.get("available") and gb.get("available")):
                    continue
                cmp = dgenome.compare(ga, gb, steps[j], steps[i])
                sh = {s["field"]: s["match"] for s in cmp["shared_observational"]}
                if sh.get("detectors") and sh.get("wavelength coverage (µm)") and sh.get("baseline (days)"):
                    add("N4", f"{q}: detectors overlap, wavelength coverage overlaps, baselines {cmp['shared_observational'][2]['a']} vs "
                              f"{cmp['shared_observational'][2]['b']} days", question=q)
                if cmp["similar_weaknesses"]["both"]:
                    add("N5", f"{q}: CLAIMX-1 modes weak in both: {', '.join(cmp['similar_weaknesses']['both'])}", question=q)
                reuse = [r for r in cmp["reusable_methods"]["items"] if r["inputs_recorded_in_other"]]
                if reuse:
                    add("N7", f"{q}: " + "; ".join(f"{r['method']} (used in {'first' if r['from'] == 'a' else 'second'})" for r in reuse), question=q)
            ha = {h["id"]: h.get("overall") for qq in (A.get("hypotheses") or {}).get("questions", []) for h in qq["hypotheses"]}
            hb = {h["id"]: h.get("overall") for qq in (B.get("hypotheses") or {}).get("questions", []) for h in qq["hypotheses"]}
            shared_h = sorted(k for k in set(ha) & set(hb) if ha[k] in VIABLE and hb[k] in VIABLE)
            if shared_h:
                add("N6", "viable in both: " + ", ".join(shared_h), explanations=shared_h)
            fa = {(n["category"], n.get("failure") or n.get("source")) for n in A["epistemic"]["negative"]["entries"] if n["category"] not in ("known limitation", "unavailable data")}
            fb = {(n["category"], n.get("failure") or n.get("source")) for n in B["epistemic"]["negative"]["entries"] if n["category"] not in ("known limitation", "unavailable data")}
            sf = sorted(fa & fb, key=str)
            if sf:
                add("N8", f"{len(sf)} shared refusal(s): " + "; ".join(f"{c}: {f}" for c, f in sf[:4]), n=len(sf))
            if not same:
                ca, cb = _cat(ra), _cat(rb)
                near = [k for k in ("parallax", "pm") if _near(ca[k], cb[k])]
                if near:
                    add("N9", "catalogue " + ", ".join(f"{k} {ca[k]:.3g} vs {cb[k]:.3g}" for k in near))
            if rel:
                edges.append({"a": nodes[i]["id"], "b": nodes[j]["id"], "relationships": rel, "rules": sorted({r["rule"] for r in rel})})
    return {"method": METHOD, "nodes": nodes, "edges": edges, "rules": {k: {"name": v[0], "limitation": v[1]} for k, v in RULES.items()},
            "counts": {k: sum(k in e["rules"] for e in edges) for k in RULES},
            "note": "Every edge states which rules hold and what was compared. No edge comes from a shared word or a score, and structural "
                    "matches are not evidence that the sources are physically related."}
