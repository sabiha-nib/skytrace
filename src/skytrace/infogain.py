"""Information analysis (INFO-1): which open test would best separate the competing explanations — qualitatively.

No probability model exists for the competing explanations in HYPO-1 (their statuses come from rules, and no prior
or likelihood is defined), so INFO-1 computes **no numerical information gain**. It ranks candidate tests by stated,
inspectable criteria instead:

  hypothesis space   the HYPO-1 explanations for each question (brightness change, motion)
  candidates         every test that is open (not tested, evidence unavailable, inconclusive, incompatible) in at least
                     one explanation that is not yet contradicted
  discrimination     a test discriminates between the explanations whose statuses it would decide; a test shared by
                     several viable explanations bears on all of them
  ranking (in order) 1. feasibility: can run now (a registered action) > needs new data > needs a method not implemented
                     2. number of viable explanations the test bears on (more first)
                     3. bears on the explanation the current claim relies on
                     4. test id (stable order)
  route              what resolving the test would take, from its status: evidence_unavailable → run the producing
                     analysis; inconclusive → more or better data (Observation Design Lab); not_tested → a new method;
                     incompatible → data of a different kind

The ranking says which test touches the most open alternatives with the least new work; it does not say how likely
any outcome is.
"""

from __future__ import annotations

METHOD = "INFO-1"
OPEN = ("not_tested", "evidence_unavailable", "inconclusive", "incompatible")
CLAIM_OWN = {"variability": "V-INTRINSIC", "motion": "M-CATALOGUE"}
ROUTE = {"evidence_unavailable": ("can run now", "run the analysis step that produces the missing input (re-run, stability or pair comparison)", "run_stability"),
         "inconclusive": ("needs new data", "more epochs, a longer baseline or matched pairs at the same wavelength (Observation Design Lab)", None),
         "not_tested": ("needs a new method", "a method Skytrace does not implement (named in the test's rule)", None),
         "incompatible": ("needs new data", "data of a different kind (e.g. matched-wavelength pairs, same release)", None)}
FEAS_ORDER = ["can run now", "needs new data", "needs a new method"]


def analyse(hyp: dict, server: bool = True) -> dict:
    rows, space = [], []
    for q in hyp["questions"]:
        viable = [h for h in q["hypotheses"] if h["overall"] != "contradicted"]
        space.append({"question": q["question"], "explanations": [{"id": h["id"], "statement": h["statement"], "overall": h["overall"]} for h in q["hypotheses"]],
                      "viable": [h["id"] for h in viable]})
        tests = {}
        for h in viable:
            for t in h["tests"]:
                if t["status"] in OPEN:
                    e = tests.setdefault(t["id"], {"test": t["id"], "question": q["question"], "description": t["description"], "rule": t["rule"],
                                                   "statuses": set(), "bears_on": []})
                    e["statuses"].add(t["status"])
                    e["bears_on"].append(h["id"])
        for e in tests.values():
            st = sorted(e["statuses"], key=lambda s: ["evidence_unavailable", "inconclusive", "incompatible", "not_tested"].index(s))[0]
            feas, route, action = ROUTE[st]
            if feas == "can run now" and not server:
                feas = "can run now"     # stability is precomputed in the preview; the planner says where it runs
            e.update({"status": st, "statuses": sorted(e["statuses"]), "feasibility": feas, "route": route, "action": action,
                      "n_viable": len(e["bears_on"]), "bears_on_claim": CLAIM_OWN.get(q["question"]) in e["bears_on"]})
            rows.append(e)
    rows.sort(key=lambda e: (FEAS_ORDER.index(e["feasibility"]), -e["n_viable"], not e["bears_on_claim"], e["test"]))
    for i, e in enumerate(rows, 1):
        e["rank"] = i
        e["why"] = (f"{e['feasibility']}; bears on {e['n_viable']} viable explanation(s) ({', '.join(e['bears_on'])})"
                    + ("; includes the explanation the claim relies on" if e["bears_on_claim"] else ""))
    return {"method": METHOD, "probability_model": None,
            "assumptions": ["HYPO-1 explanations are the hypothesis space; nothing outside it is ranked",
                            "a test is informative for every viable explanation it appears in",
                            "feasibility is decided by the test's status and the registered actions, not by expected outcomes"],
            "uncertainty_model": "none: no likelihoods are defined, so no expected information is computed",
            "ranking_rule": "feasibility, then number of viable explanations, then relevance to the claim, then test id",
            "hypothesis_space": space, "candidates": rows,
            "interpretation_limits": "A rank orders tests by how many open alternatives they touch for the least new work. It is not a "
                                     "probability, an expected information gain, or a prediction of the test's result."}
