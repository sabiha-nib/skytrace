"""Investigation blindness detector (BLIND-1): which parts of an investigation have not been examined.

Coverage is reported over a fixed, explicitly defined set of checks (CHECKS). Each check has one state —
examined, partially examined, not examined, not applicable, unknown — decided by its stated rule. There is no percentage
and no claim that an investigation is complete: the list says what was looked at, against what definition.

The server decides the record-dependent checks; three checks depend on what you did in the session (visits inspected by
eye, causal language in your notes, a sensitivity run) and are completed in the browser by `overlayBlindspots`
(epistemiccore.js, parity-tested).
"""

from __future__ import annotations

METHOD = "BLIND-1"
STATES = ["examined", "partially examined", "not examined", "not applicable", "unknown"]
CHECKS = [
    ("epochs", "Observation epochs inspected", "every visit has at least one compared pair you inspected by eye (session); visits without any are not examined"),
    ("unused", "Unused measurements", "every usable measurement enters a comparison or the motion fit; usable measurements used by neither are blind spots"),
    ("metadata", "Missing metadata", "no inventory field is unknown (DISC-1 counts unknown fields)"),
    ("assumptions", "Unverified assumptions", "every assumption a method can test was tested (SCI-COMP A4)"),
    ("hypotheses", "Unexplored alternative hypotheses", "every competing explanation has at least one evaluated test (HYPO-1)"),
    ("comparisons", "Incompatible comparison pairs", "every candidate pair was decided by WLMATCH-2 with a logged reason (decided pairs count as examined)"),
    ("systematics", "Unexamined systematic effects", "every effect UNC-1 lists as unquantified has been quantified"),
    ("provenance", "Missing provenance", "every measurement traces to a hashed manifest file (SCI-COMP V2)"),
    ("language", "Unsupported causal language", "none of your notebook text asserts causation or discovery (session)"),
    ("boundaries", "Untested boundary conditions", "the outcomes were re-derived under perturbed analysis settings (a stability run or threshold scenarios in the session)"),
    ("quality", "Unresolved data-quality concerns", "no DQ-1 check is invalid or incompatible"),
]


def base(record: dict, disc: dict, compiled: dict, quality: dict | None, unc: dict | None) -> dict:
    ev = {}
    for i, e in enumerate(record["events"]):
        ev.setdefault(e["step"], []).append((i, e))
    checks = {c["id"]: c for c in compiled["checks"]}
    out = {}
    astro = ((ev.get("astrometry") or [(0, {"data": {}})])[0][1].get("data") or {})
    series = [s.get("key") for s in astro.get("series", [])]
    visits = [{"index": j, "t_mjd": e.get("t_mjd"), "members": [series[k] for k in e.get("members") or [] if isinstance(k, int) and k < len(series)]}
              for j, e in enumerate(astro.get("epochs", []))]
    pairs = ((ev.get("variability") or [(0, {"data": {}})])[0][1].get("data") or {}).get("pairs", [])
    out["epochs"] = {"state": "unknown", "detail": f"{len(visits)} visits; inspection is recorded in the session", "visits": visits,
                     "pairs": [f"{p['a']}|{p['b']}" for p in pairs]}
    usable = {(e.get("data") or {}).get("obs_id") for _, e in ev.get("measure", []) if e.get("status") == "ok"}
    in_pairs = {k for p in pairs for k in (p["a"], p["b"])}
    used_fit = {s.get("key") for s in astro.get("series", []) if s.get("used_in_fit", True)}
    unused = sorted(usable - in_pairs - used_fit)
    out["unused"] = {"state": "examined" if not unused else "partially examined",
                     "detail": f"{len(unused)} of {len(usable)} usable measurements enter neither a comparison nor the motion fit", "items": unused[:20]}
    inv = (disc.get("inventory") or {}).get("summary") or {}
    nu = inv.get("unknown_fields")
    out["metadata"] = {"state": "unknown" if nu is None else ("examined" if not nu else "partially examined"),
                       "detail": f"{nu} unknown inventory field value(s) — left empty, never filled" if nu is not None else "inventory summary not available"}
    a4 = checks.get("A4")
    out["assumptions"] = {"state": "examined" if a4 and a4["outcome"] == "pass" else ("partially examined" if a4 else "unknown"),
                          "detail": a4["detail"] if a4 else "no assumption check"}
    hyp = [h for q in (disc.get("hypotheses") or {}).get("questions", []) for h in q.get("hypotheses", [])]
    untested = [h["id"] for h in hyp if all(t["status"] in ("not_tested", "evidence_unavailable") for t in h.get("tests", []))]
    out["hypotheses"] = {"state": "examined" if not untested else ("not examined" if len(untested) == len(hyp) else "partially examined"),
                         "detail": f"{len(untested)} of {len(hyp)} explanations have no evaluated test", "items": untested}
    pr = ((ev.get("pairs") or [(0, {"data": {}})])[0][1].get("data") or {})
    n_rej = sum((pr.get("rejection_reasons") or {}).values())
    out["comparisons"] = {"state": "examined" if pr else "not applicable",
                          "detail": f"{len(pr.get('accepted', []))} accepted, {n_rej} rejected with a logged reason" if pr else "no pairing step"}
    unq = (unc or {}).get("unquantified") or []
    out["systematics"] = {"state": "not examined" if unq else "examined", "detail": f"{len(unq)} effect(s) not quantified by any method here",
                          "items": [u.get("effect") if isinstance(u, dict) else str(u) for u in unq][:10]}
    v2 = checks.get("V2")
    out["provenance"] = {"state": "examined" if v2 and v2["outcome"] == "pass" else ("not examined" if v2 else "unknown"), "detail": v2["detail"] if v2 else "no provenance check"}
    out["language"] = {"state": "unknown", "detail": "decided from your notebook in the browser"}
    out["boundaries"] = {"state": "unknown", "detail": "decided from the session (stability or threshold scenarios)"}
    dq = [c for c in (quality or {}).get("checks", []) if c["outcome"] in ("invalid", "incompatible")]
    out["quality"] = {"state": "unknown" if quality is None else ("examined" if not dq else "partially examined"),
                      "detail": (f"{len(dq)} check(s) unresolved: " + ", ".join(f"{c['id']} {c['outcome']}" for c in dq)) if dq else "no invalid or incompatible check"}
    rows = [{"id": cid, "name": name, "rule": rule, **out[cid]} for cid, name, rule in CHECKS]
    return {"method": METHOD, "states": STATES, "checks": rows, "counts": {s: sum(r["state"] == s for r in rows) for s in STATES},
            "note": "Coverage of these defined checks only. Examined does not mean correct, and a full set of examined checks does not make an investigation complete."}


def overlay(base: dict, session: dict | None, causal_words) -> dict:
    """The session-dependent checks (mirror of epistemiccore.overlayBlindspots; parity-tested)."""
    from .epistemic import asserted_words
    s = session or {}
    examined = set(s.get("examined") or [])
    rows = []
    for r in base["checks"]:
        if r["id"] == "epochs":
            visits = r.get("visits") or []
            seen = [any(p in examined and any(k in v["members"] for k in p.split("|")) for p in r.get("pairs") or []) for v in visits]
            n = sum(seen)
            state = "not applicable" if not visits else ("examined" if n == len(visits) else ("partially examined" if n else "not examined"))
            r = {**r, "state": state, "detail": f"{n} of {len(visits)} visits have a compared pair you inspected by eye"}
        elif r["id"] == "language":
            notes = [b for b in s.get("notebook") or [] if b.get("author") == "user"]
            if not notes:
                r = {**r, "state": "not applicable", "detail": "no notebook text of yours yet"}
            else:
                hits = [b for b in notes if asserted_words(b.get("text") or "", causal_words)]
                r = {**r, "state": "partially examined" if hits else "examined",
                     "detail": f"{len(hits)} of your note(s) assert causal or discovery language" if hits else f"{len(notes)} note(s) checked; none asserts causation or discovery",
                     "items": [b["id"] for b in hits]}
        elif r["id"] == "boundaries":
            scen = sum(1 for x in s.get("scenarios") or [] if isinstance(x, dict) and isinstance(x.get("scenario"), dict) and x["scenario"].get("kind") in ("threshold", "parameter", "error_scale"))
            stab = sum(1 for x in s.get("experiments") or [] if isinstance(x, dict) and x.get("template") in ("sensitivity", "robustness", "parameter") and x.get("status") == "completed")
            r = {**r, "state": "examined" if scen + stab else "not examined", "detail": f"{stab} completed sensitivity experiment(s), {scen} counterfactual scenario(s) in this session"}
        rows.append(r)
    return {**base, "checks": rows, "counts": {st: sum(x["state"] == st for x in rows) for st in base["states"]}}
