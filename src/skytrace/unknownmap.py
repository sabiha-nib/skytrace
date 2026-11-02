"""UNKNOWN-1: the unknown universe — a map of the research frontier of one target, region by region.

The map does not describe astronomy. It describes what the investigations of one target, as recorded, establish and leave open.
Eight regions, each with a defined meaning and a rule that places items in it; every item names its basis (the module and
the record field or graph object it came from):

  established       U1  a claim in KBOUND-1's region 'established'
  supported         U2  a claim in 'supported under assumptions', with the assumptions it rests on
  weak              U3  a competing explanation (HYPO-1) that is still viable (consistent so far or inconclusive), and every
                        claim in 'unresolved'
  unresolved        U4  a question QFORGE-1 cannot answer directly, every KBOUND-1 item 'outside the evidence', and every
                        competing explanation no test has evaluated (HYPO-1 'untested')
  missing           U5  observations or measurements that were refused or are absent (NEG-1 missing measurement, invalid
                        comparison and unavailable data entries; visits BLIND-1 marks as not examined)
  unexplored        U6  documented parameter ranges (CAPREG) that no recorded run of the target sampled: the recorded values
                        of each parameter split its range into sampled points and unsampled intervals
  unavailable       U7  inputs the analysis needed but could not obtain (DISC-1 inventory unknowns, HYPO-1 tests with
                        'evidence_unavailable', services refused in the environment report)
  unmeasured        U8  quantities no method here quantifies (UNC-1 'unquantified', UFLOW-1 'not propagated')

An item may sit in one region only; the regions are listed in the order above and the first rule that applies wins. Counts
describe these records, not the sky; an empty region means no recorded item met its rule, not that nothing is unknown there.
"""

from __future__ import annotations

from . import scicomp

METHOD = "UNKNOWN-1"
REGIONS = [("established", "Established knowledge", "U1"), ("supported", "Evidence-supported possibilities", "U2"),
           ("weak", "Weakly supported hypotheses", "U3"), ("unresolved", "Unresolved questions", "U4"),
           ("missing", "Missing observations", "U5"), ("unexplored", "Unexplored parameter regions", "U6"),
           ("unavailable", "Unavailable data", "U7"), ("unmeasured", "Unknown or unmeasured quantities", "U8")]
RULES = {"U1": "a claim in KBOUND-1's region 'established'",
         "U2": "a claim in KBOUND-1's region 'supported under assumptions'",
         "U3": "a competing explanation that is still viable (HYPO-1 'consistent so far' or 'inconclusive'), or a claim in 'unresolved'",
         "U4": "a question QFORGE-1 cannot answer directly, a KBOUND-1 item 'outside the evidence', or an explanation no test has evaluated (HYPO-1 'untested')",
         "U5": "a refused or absent observation or measurement (NEG-1 missing measurement, invalid comparison, unavailable data; visits not examined)",
         "U6": "part of a documented parameter range that no recorded run of this target sampled",
         "U7": "an input the analysis needed but could not obtain (inventory unknowns, tests with evidence unavailable, refused services)",
         "U8": "a quantity no method here quantifies (UNC-1 unquantified, UFLOW-1 not propagated)"}
VIABLE = ("consistent so far", "inconclusive")


def _item(region, iid, label, basis, ref, **extra):
    return {"region": region, "id": iid, "label": str(label)[:300], "basis": basis, "ref": ref, **extra}


def build(record: dict, rep: dict, disc: dict, sibling_params: list[dict] | None = None, env_report: dict | None = None) -> dict:
    """rep: the epistemic report; disc: DISC-1 (with 'hypotheses', 'uncertainty', 'inventory'); sibling_params: the parameters
    of every recorded run of the same target (this one included); env_report: data/environment_report.json, when present."""
    items = []
    seen = set()

    def add(it):
        if it["id"] not in seen:
            seen.add(it["id"])
            items.append(it)

    bnd = rep["boundary"]["items"]
    region_of = {"established": "established", "supported under assumptions": "supported", "unresolved": "weak", "outside the evidence": "unresolved"}
    for b in bnd:
        if b["kind"] == "claim":
            add(_item(region_of[b["region"]], b["id"], b["statement"], f"KBOUND-1 {b['rule']}", f"graph:{b['id']}", why=b.get("why"),
                      assumptions=[a.get("label") for a in (b.get("assumptions") or [])][:6], could_change_it=(b.get("could_change_it") or [])[:4]))
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q["hypotheses"]:
            if h.get("overall") in VIABLE:
                open_tests = [t["id"] for t in h.get("tests", []) if t["status"] in ("untested", "inconclusive", "evidence_unavailable", "not_tested")]
                add(_item("weak", f"hyp:{h['id']}", h["statement"], f"HYPO-1 overall '{h['overall']}'", f"HYPO-1:{h['id']}", question=q["question"], open_tests=open_tests))
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q["hypotheses"]:
            if h.get("overall") == "untested":
                add(_item("unresolved", f"hyp:{h['id']}", h["statement"], "HYPO-1 overall 'untested'", f"HYPO-1:{h['id']}", question=q["question"],
                          open_tests=[t["id"] for t in h.get("tests", [])]))
    for b in bnd:
        if b["kind"] != "claim":
            add(_item("unresolved", b["id"], b["statement"], f"KBOUND-1 {b['rule']} ({b['region']})", f"graph:{b['id']}", why=b.get("why")))
    for qn in rep["questions"]["questions"]:
        pb = str(qn.get("prompted_by") or "")
        if any(f" {i} " in f" {pb} " or pb.endswith(f" {i}") for i in list(seen)):
            continue                                    # the same open question already placed from KBOUND-1 (one region, one entry)
        if qn["category"] != "directly answerable":
            add(_item("unresolved", qn["id"], qn["question"], f"QFORGE-1 '{qn['category']}'", qn.get("prompted_by"), missing=qn.get("missing")))
    for k, n in enumerate(rep["negative"]["entries"]):
        if n["category"] in ("missing measurement", "invalid comparison", "unavailable data"):
            add(_item("missing" if n["category"] != "unavailable data" or not str(n.get("source", "")).startswith("environment:") else "unavailable",
                      f"neg:{k}", f"{n['attempted']}: {n.get('happened') or n.get('why')}", f"NEG-1 {n['category']} ({n['distinction']})", n.get("source"),
                      n_inputs=n.get("n_inputs"), unblock=n.get("unblock")))
    for c in rep["blindspot"]["checks"]:
        if c["id"] == "epochs" and c["state"] in ("not examined", "partially examined"):
            add(_item("missing", "blind:epochs", c["detail"], f"BLIND-1 {c['state']}", "BLIND-1:epochs"))
    add_unexplored = _unexplored(record, sibling_params or [record.get("parameters", {})])
    for it in add_unexplored:
        add(it)
    inv = disc.get("inventory") or {}
    for it in inv.get("items") or []:
        for f, v in sorted((it.get("fields") or {}).items()):
            if v is None:
                add(_item("unavailable", f"inv:{it['id']}:{f}", f"{f} of {it['id']} is unknown (left empty, never filled)", "DISC-1 inventory unknown",
                          f"DISC-1:inventory/{it['id']}"))
    for q in (disc.get("hypotheses") or {}).get("questions", []):
        for h in q["hypotheses"]:
            for t in h.get("tests", []):
                if t["status"] == "evidence_unavailable":
                    add(_item("unavailable", f"test:{h['id']}:{t['id']}", f"{h['id']} {t['id']}: {t.get('detail') or t.get('description')}",
                              "HYPO-1 test with evidence unavailable", f"HYPO-1:{h['id']}/{t['id']}"))
    have_env = any(str(i.get("ref") or "").startswith("environment:") for i in items)
    for r in ([] if have_env else (env_report or {}).get("services", [])):
        v = str(r.get("verdict") or "")
        if v.startswith(("proxy_refused", "dns", "refused", "timeout", "connection")):
            add(_item("unavailable", f"env:{r.get('service')}", f"{r.get('service')} could not be reached ({v})", "environment report (diagnose_environment.py)",
                      "data/environment_report.json", run_at=(env_report or {}).get("run_at")))
    for k, row in enumerate((disc.get("uncertainty") or {}).get("unquantified", [])):
        lab = row if isinstance(row, str) else (row.get("effect") or row.get("component") or row.get("name") or str(row))
        add(_item("unmeasured", f"unc:{k}", lab, "UNC-1 unquantified", "UNC-1:unquantified"))
    for k, x in enumerate(rep["uflow"]["not_propagated"]):
        add(_item("unmeasured", f"uflow:{k}", f"{x['step']}: {x['what']}", "UFLOW-1 not propagated", f"UFLOW-1:{x['step']}"))
    regions = []
    for rid, name, rule in REGIONS:
        xs = [i for i in items if i["region"] == rid]
        regions.append({"id": rid, "name": name, "rule_id": rule, "rule": RULES[rule], "n": len(xs), "items": xs})
    return {"method": METHOD, "record": record.get("content_hash"), "target": record.get("target"),
            "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic", "regions": regions,
            "n_runs_considered": len(sibling_params or [1]),
            "note": "A map of what these records establish and leave open, not of astronomical knowledge. An empty region means no recorded "
                    "item met its rule, not that nothing is unknown there. Connections between regions are not inferences."}


def _unexplored(record: dict, params_list: list[dict]) -> list[dict]:
    out = []
    for k, (lo, hi) in scicomp.PARAM_RANGES.items():
        vals = sorted({p.get(k) for p in params_list if isinstance(p.get(k), (int, float)) and not isinstance(p.get(k), bool)})
        if not vals:
            continue
        gaps = []
        prev = lo
        for v in vals:
            if v > prev:
                gaps.append([prev, v])
            prev = max(prev, v)
        if prev < hi:
            gaps.append([prev, hi])
        span = hi - lo
        for g in gaps:
            if span and (g[1] - g[0]) / span >= 0.05:            # ignore slivers under 5 % of the documented range
                out.append(_item("unexplored", f"param:{k}:{g[0]:g}-{g[1]:g}", f"{k} between {g[0]:g} and {g[1]:g} was not sampled",
                                 f"CAPREG range {lo:g}–{hi:g}; sampled {', '.join(f'{v:g}' for v in vals)}", f"$.parameters.{k}",
                                 parameter=k, interval=g, sampled=vals, documented_range=[lo, hi]))
    return out
