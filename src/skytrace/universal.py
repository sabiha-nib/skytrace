"""Phase 10 signature systems: readers of a finished investigation record and the reports already computed from it.

  WORLD-1     world model: typed relationships between the investigation's objects, each with an explicit basis (the rule
              and the recorded field it comes from), and a structured query over them. No physical relationship is inferred.
  CONV-1      discovery convergence: how many lines of evidence support an outcome *independently*. Lines that share an
              exposure, a reference-star set, a method or a data bundle are grouped; repeated use of the same data is never
              counted as independent confirmation.
  LEAD-1      contradictions as research leads: disagreements between methods, fits or tests, each with the possible kinds
              of resolution. A detected contradiction is a lead, not a paradox.
  NEGX-1      negative space in nine distinctions (measured absence, non-detection, missing measurement, unavailable
              dataset, failed method, insufficient sensitivity, unexplored region, unresolved explanation, unknown quantity),
              each saying what it does not mean. A non-detection never proves that something does not exist.
  MODAL-1     multimodal representation: every recorded measurement in one shape (modality, quantity, unit, time, wavelength,
              detector, value, error, source) and the rules for which cross-modal comparisons are compatible.
  OPP-2       research opportunities with ten fields and a novelty scope that never exceeds what Skytrace can know: new to
              this investigation, new to this collection, underexplored in indexed sources (not evaluated: no literature
              index is connected) or independently verified (not evaluated: only an outside reproduction can say).
  KCOMP-1     the knowledge compiler's stage statuses: Passed / Passed with warnings / Incomplete / Failed / Not evaluated.
  EXTSRC-1    external monitoring sources and their connection state; nothing is shown as an update unless a connector
              actually returned it (in this build none is connected).
  AGENTS-1    role agents: five rule sets that read the same record and argue from it. They share one model of the data,
              the same record and the same assumptions, so their agreement is not independent confirmation.
  EXPLAIN-1   eight explanation layers per outcome, as keyed messages with parameters, so the same values are explained in
              every interface language.
  TIMES-1     the discovery timeline with observation, processing, publication and event times kept apart.
  DIRECT-1    the investigation director's proposed plan: ordered registered steps with reasons; nothing runs without approval.

Deterministic; no network, no model calls; no probabilities and no scores.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from . import sigintel

DISTINCTIONS = ["measured absence", "non-detection", "missing measurement", "unavailable dataset", "failed method",
                "insufficient sensitivity", "unexplored region", "unresolved explanation", "unknown quantity"]
DOES_NOT_MEAN = {
    "measured absence": "not proof that the effect is absent: changes below the stated sensitivity are not excluded",
    "non-detection": "not proof that the source does not exist or emit at this wavelength",
    "missing measurement": "nothing about the source: the measurement was not made",
    "unavailable dataset": "nothing about the source: the data were not available to this investigation",
    "failed method": "nothing about the source: the method did not produce a result",
    "insufficient sensitivity": "not a null result: the data cannot answer the question at the needed level",
    "unexplored region": "not that nothing is there: nobody looked with these data",
    "unresolved explanation": "not that the explanations are equally likely: the tests did not decide between them",
    "unknown quantity": "not zero: the quantity is not known",
}
LEAD_NOTE = "A detected contradiction is a research lead, not a paradox: each lists the kinds of resolution still open."
NEG_NOTE = "A non-detection is not proof that an object or phenomenon does not exist."
WORLD_NOTE = "Every relationship names the rule and the recorded field it comes from. No physical relationship between objects is inferred."
OPP_NOTE = "Novelty is stated only within what Skytrace holds. Absence from this collection never makes a question globally novel."
KCOMP_MEANING = "Passing compilation means the defined checks were satisfied. It does not prove that a scientific conclusion is true."
EXT_NOTE = "No monitoring runs and no update is shown: a source would appear as connected only after a connector returns real data, with its retrieval time."
EXPLAIN_NOTE = "Layer wording is translated; the values and the statements recorded by the engines are shown unchanged."
TIMES_NOTE = "Observation, processing, publication and event times are kept on separate lanes and are never merged."
MODAL_RULES = [
    {"a": "photometry", "b": "photometry", "compatible": "only when wavelength-matched on one detector (WLMATCH-2)", "comparison": "flux difference with significance"},
    {"a": "photometry", "b": "spectrum", "compatible": "only at a common wavelength and time; a spectrum point is a photometric measurement placed by wavelength",
     "comparison": "the same measurement seen two ways — not independent"},
    {"a": "photometry", "b": "astrometry", "compatible": "time alignment only: values in µJy and mas are never compared",
     "comparison": "whether changes are co-temporal"},
    {"a": "astrometry", "b": "astrometry", "compatible": "same reference frame (Gaia) and epoch convention", "comparison": "motion fit"},
    {"a": "image", "b": "image", "compatible": "registered by plate solutions; same display scale; wavelength-matched for brightness",
     "comparison": "visual inspection — never physical similarity"},
]
CONV_RULES = ["two lines are independent only if they share no exposure",
              "lines that share a reference-star set share their calibration",
              "runs of the same data bundle never confirm one another",
              "one method applied many times is one method"]
DIRECTOR_RULES = ["steps are ordered by a fixed rule: data quality, leads, opportunities, methods, explanations, compilation, handoff",
                  "every step needs your approval; executing a step opens its recorded result",
                  "the director never acquires data, never changes a record and never publishes"]
LANE_MEANING = {'observation': 'when the telescope took each exposure (mid-exposure time from the file)',
                'processing': 'when this analysis was computed',
                'publication': 'when the data were released or retrieved from the archive',
                'event': 'when a physical change happened in the source'}
EVENT_STATE = "not determined: observation times bound when a change was seen, not when it happened"
COMPILER_STATUSES = ["Passed", "Passed with warnings", "Incomplete", "Failed", "Not evaluated"]
NOVELTY_SCOPES = ["new to this investigation", "new to this collection", "underexplored in indexed sources", "independently verified"]
SOURCES = [
    {"id": "irsa-spherex", "name": "IRSA SPHEREx archive (new quick releases)", "kind": "archive", "provider": "NASA/IPAC IRSA"},
    {"id": "gaia-alerts", "name": "Gaia Science Alerts", "kind": "transient alerts", "provider": "ESA / Gaia alerts team"},
    {"id": "tns", "name": "Transient Name Server", "kind": "transient reports", "provider": "IAU TNS"},
    {"id": "atel", "name": "The Astronomer's Telegram", "kind": "rapid communications", "provider": "ATel"},
    {"id": "arxiv", "name": "arXiv astro-ph listings", "kind": "preprints", "provider": "arXiv"},
    {"id": "ads", "name": "NASA ADS literature index", "kind": "literature index", "provider": "NASA ADS (requires an API token)"},
]
ROLES = [
    {"id": "observer", "name": "Observer", "reads": "what was observed and measured"},
    {"id": "skeptic", "name": "Skeptic", "reads": "contradictions, shared dependencies and limitations"},
    {"id": "methodologist", "name": "Methodologist", "reads": "method applicability and assumption checks"},
    {"id": "statistician", "name": "Statistician", "reads": "significances, sensitivities and noise checks"},
    {"id": "archivist", "name": "Archivist", "reads": "provenance, data origin and reproducibility"},
]
AGENT_CAVEAT = ("The five role agents are rule sets that read the same record with the same software. They share one model of the data, "
                "the same data and the same assumptions: their agreement is not independent confirmation, and no agent is a person.")


def _f(x, nd=6):
    return sigintel._f(x, nd)


def _events(rec, step, status=None):
    return [e for e in rec["events"] if e["step"] == step and (status is None or e["status"] == status)]


def _data(rec, step):
    ev = next(iter(_events(rec, step, "ok")), None) or next(iter(_events(rec, step)), None)
    return (ev or {}).get("data") or {}


def _outcomes(rec):
    return _data(rec, "assess").get("outcomes") or []


def _mjd_iso(m):
    if m is None:
        return None
    return (datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=float(m))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _synthetic(rec):
    return any(p.get("origin") == "synthetic" for e in rec["events"] for p in e.get("provenance") or [])


# ------------------------------------------------------------------ CONV-1
def convergence(rec: dict, sibling_hashes: list[str] | None = None) -> dict:
    var = _data(rec, "variability")
    pairs = var.get("pairs") or []
    sig = [p for p in pairs if abs(((p.get("differential") or {}).get("z_cal") or 0.0)) >= 5 and (p.get("differential") or {}).get("calibrated")]
    # union-find over shared exposures
    parent = list(range(len(sig)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(sig)):
        for j in range(i + 1, len(sig)):
            if {sig[i]["a"], sig[i]["b"]} & {sig[j]["a"], sig[j]["b"]}:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(sig)):
        groups.setdefault(find(i), []).append(i)
    glist = []
    for idx in groups.values():
        exps = sorted({x for i in idx for x in (sig[i]["a"], sig[i]["b"])})
        refs = sorted({r for i in idx for r in (sig[i].get("differential") or {}).get("ref_ids") or []})
        glist.append({"pairs": [f"{sig[i]['a']}|{sig[i]['b']}" for i in idx], "exposures": exps, "reference_stars": refs})
    glist.sort(key=lambda g: (-len(g["pairs"]), g["pairs"][0]))
    shared_refs = set.intersection(*[set(g["reference_stars"]) for g in glist]) if len(glist) > 1 else set()
    lines = []
    lines.append({"outcome": "variability", "lines": len(sig), "independent_by_exposure": len(glist),
                  "groups": glist, "shared_reference_stars": sorted(shared_refs),
                  "method_dependence": "every line uses APPHOT-1 photometry and PAIRDIFF-2 calibration: one method, not independent methods",
                  "reading": (f"{len(sig)} significant calibrated pair(s) form {len(glist)} group(s) that share no exposure"
                              + (f"; the groups share {len(shared_refs)} reference star(s), so their calibration is not independent" if shared_refs else "")
                              if sig else "no significant calibrated pair: nothing converges")})
    astro = _data(rec, "astrometry")
    if astro.get("fit"):
        ep = astro.get("epochs") or []
        lines.append({"outcome": "motion", "lines": 1, "independent_by_exposure": 1, "groups": [],
                      "shared_reference_stars": [],
                      "method_dependence": "one linear fit over visit means; the exposure-level fit (LINFIT-LOO-1) uses the same exposures and is a cross-check, not a second line",
                      "reading": f"one motion fit from {len(ep)} visit mean(s); every visit uses the same Gaia reference catalogue"})
    sib = sorted(set(sibling_hashes or []) - {rec.get("content_hash")})
    return {"method": "CONV-1", "outcomes": lines,
            "repeated_data": {"sibling_runs": len(sib),
                              "reading": (f"{len(sib)} other run(s) of this target reuse the same data bundle with different parameters: "
                                          "agreement between them shows stability under those choices, not independent confirmation") if sib else
                              "no other run of this target is held"},
            "rules": CONV_RULES}


# ------------------------------------------------------------------ LEAD-1
def leads(rec: dict, hypotheses: dict | None = None) -> dict:
    out = []
    var = _data(rec, "variability")
    for p in var.get("pairs") or []:
        d = p.get("differential") or {}
        if not d.get("calibrated") or d.get("z_cal") is None or p.get("z") is None:
            continue
        raw, cal = abs(p["z"]) >= 5, abs(d["z_cal"]) >= 5
        if raw != cal:
            out.append({"id": f"L-PAIR-{len(out) + 1}", "kind": "method disagreement",
                        "statement": f"PAIRDIFF-1 |z| = {abs(p['z']):.2f} and PAIRDIFF-2 |z_cal| = {abs(d['z_cal']):.2f} disagree about a ≥ 5 difference",
                        "evidence": [f"pair:{p['a']}|{p['b']}"],
                        "resolutions": ["exposure-level calibration change (the calibrated value is the one the assessment uses)",
                                        "reference-star selection", "a real change masked or mimicked by calibration"],
                        "status": "research lead", "rule": "raw and reference-calibrated significances fall on opposite sides of 5"})
    a = _data(rec, "astrometry")
    ef, pf = a.get("exposure_fit") or {}, a.get("fit") or {}
    for ax, k in (("ξ", "xi"), ("η", "eta")):
        if ef.get(f"pm_{k}_mas_yr") is None or pf.get(f"pm_{k}_mas_yr") is None:
            continue
        d = ef[f"pm_{k}_mas_yr"] - pf[f"pm_{k}_mas_yr"]
        s = math.hypot(ef.get(f"sig_{k}") or 0, pf.get(f"sig_{k}") or 0)
        if s > 0 and abs(d) > 3 * s:
            out.append({"id": f"L-FIT-{ax}", "kind": "fit disagreement",
                        "statement": f"exposure-level and visit-level proper motion differ by {d:.1f} mas/yr on {ax} (> 3σ combined)",
                        "evidence": ["$.events[astrometry].exposure_fit", "$.events[astrometry].fit"],
                        "resolutions": ["correlated errors within visits", "an outlying exposure", "non-linear motion"],
                        "status": "research lead", "rule": "|Δpm| > 3 √(σ₁² + σ₂²)"})
    comp = a.get("comparison") or {}
    if comp and comp.get("consistent_within_3sigma") is False:
        out.append({"id": "L-CAT", "kind": "catalogue disagreement", "statement": "the measured proper motion differs from the catalogue value by more than 3σ",
                    "evidence": ["$.events[astrometry].comparison"], "resolutions": ["catalogue error", "measurement systematics", "a change in the source"],
                    "status": "research lead", "rule": "|measured − catalogue| > 3σ on an axis"})
    for q in (hypotheses or {}).get("questions") or []:
        for h in q.get("hypotheses") or []:
            st = {t.get("status") for t in h.get("tests") or []}
            if "consistent" in st and "contradicted" in st:
                out.append({"id": f"L-HYP-{h['id']}", "kind": "test disagreement",
                            "statement": f"hypothesis {h['id']} has both consistent and contradicting tests",
                            "evidence": [f"hypothesis:{h['id']}"], "resolutions": ["one test's assumptions do not hold", "the hypothesis is incomplete"],
                            "status": "research lead", "rule": "a hypothesis with tests in both states"})
    return {"method": "LEAD-1", "leads": out, "note": LEAD_NOTE}


# ------------------------------------------------------------------ NEGX-1
_NEG_MAP = {("unavailable data", "data unavailable"): "unavailable dataset", ("unavailable data", "no data"): "missing measurement",
            ("missing measurement", None): "missing measurement", ("failed analysis", None): "failed method",
            ("unsupported method", None): "failed method", ("known limitation", None): "insufficient sensitivity",
            ("inconclusive test", None): "unresolved explanation", ("unresolved contradiction", None): "unresolved explanation",
            ("invalid comparison", None): "missing measurement", ("unsuccessful reproduction", None): "failed method",
            ("abandoned hypothesis", None): "unresolved explanation"}


def negative_space(rec: dict, neg: dict | None = None, hypotheses: dict | None = None, network: bool | None = None) -> dict:
    items = []

    def add(dist, statement, evidence, source):
        items.append({"distinction": dist, "statement": statement, "evidence": evidence, "source": source, "does_not_mean": DOES_NOT_MEAN[dist]})
    for o in _outcomes(rec):
        cat = o.get("category") or ""
        if cat.startswith("no_") or "not_detected" in cat:
            add("measured absence", o.get("statement") or cat, [f"outcome:{o.get('question')}"], "ASSESS-2")
        if cat in ("insufficient_data", "not_answerable"):
            add("insufficient sensitivity", o.get("statement") or cat, [f"outcome:{o.get('question')}"], "ASSESS-2")
    for ev in _events(rec, "measure"):
        ph = (ev.get("data") or {}).get("photometry") or {}
        snr = ph.get("snr")
        if snr is not None and snr < 5:
            add("non-detection", f"S/N = {snr:.1f} < 5 in {ev['data'].get('obs_id')}", [ev["data"].get("obs_id")], "APPHOT-1")
        elif ev["status"] in ("rejected", "failed"):
            add("missing measurement", f"{ev['data'].get('obs_id')}: {ev.get('detail') or ev['status']}", [ev["data"].get("obs_id")], "measure")
    for e in (neg or {}).get("entries") or []:
        dist = _NEG_MAP.get((e.get("category"), e.get("distinction"))) or _NEG_MAP.get((e.get("category"), None))
        if dist:
            add(dist, f"{e.get('attempted')}: {e.get('happened')}", e.get("inputs") or [e.get("source")], e.get("id"))
    if network is not True and not any(p.get("origin") == "archive" for x in rec["events"] for p in x.get("provenance") or []):
        add("unavailable dataset", "real SPHEREx archive data for this target were not acquired in this environment (the archive was not reachable)",
            ["environment"], "availability")
    for q in (hypotheses or {}).get("questions") or []:
        for h in q.get("hypotheses") or []:
            if h.get("overall") in ("inconclusive", "untested"):
                add("unresolved explanation", f"{h['id']}: {h.get('statement')} ({h.get('overall')})", [f"hypothesis:{h['id']}"], "HYPO-1")
    # unexplored regions: wavelength coverage and time gaps
    meas = [e["data"] for e in _events(rec, "measure", "ok") if (e.get("data") or {}).get("wavelength_um") is not None]
    if meas:
        wl = sorted(m["wavelength_um"] for m in meas)
        gaps = [(a, b) for a, b in zip([0.75] + wl, wl + [5.0]) if b - a > 0.25]
        for a, b in gaps[:6]:
            add("unexplored region", f"no measurement between {a:.2f} and {b:.2f} µm", ["coverage"], "MODAL-1")
        t = sorted(m["mjd"] for m in meas)
        big = [(a, b) for a, b in zip(t, t[1:]) if b - a > 60]
        for a, b in big[:6]:
            add("unexplored region", f"no observation for {b - a:.0f} d between MJD {a:.1f} and {b:.1f}", ["sampling"], "SIGNAL-1")
    ast = _data(rec, "astrometry")
    par = ast.get("parallax") or {}
    if not par.get("parallax_mas"):
        add("unknown quantity", "the source's parallax is not measured here; the catalogue value is used for the correction", ["$.events[astrometry].parallax"], "EPHEM-AA-LP-1")
    add("unknown quantity", "the time at which any physical change happened is not determined; only the observation times are known", ["timeline"], "TIMES-1")
    counts = {d: sum(1 for x in items if x["distinction"] == d) for d in DISTINCTIONS}
    return {"method": "NEGX-1", "distinctions": DISTINCTIONS, "does_not_mean": DOES_NOT_MEAN, "counts": counts, "items": items,
            "note": NEG_NOTE}


# ------------------------------------------------------------------ MODAL-1
def multimodal(rec: dict) -> dict:
    rows = []
    for m in (e["data"] for e in _events(rec, "measure", "ok")):
        ph = m.get("photometry") or {}
        if ph.get("status") == "ok":
            rows.append({"modality": "photometry", "quantity": "flux density", "unit": "µJy", "time_mjd": m.get("mjd"), "wavelength_um": m.get("wavelength_um"),
                         "detector": m.get("detector"), "value": ph.get("flux_ujy"), "error": ph.get("flux_err_ujy"), "source": m.get("obs_id"), "method": ph.get("method")})
        xe = m.get("target_xi_eta_mas")
        if isinstance(xe, (list, tuple)) and len(xe) == 2 and None not in xe:
            rows.append({"modality": "astrometry", "quantity": "tangent-plane offset (ξ, η)", "unit": "mas", "time_mjd": m.get("mjd"),
                         "wavelength_um": m.get("wavelength_um"), "detector": m.get("detector"), "value": list(xe), "error": None, "source": m.get("obs_id"),
                         "method": "PLATE-LOO-1"})
    for p in _data(rec, "spectrum").get("points") or []:
        if p.get("usable"):
            rows.append({"modality": "spectrum", "quantity": "flux density at wavelength", "unit": "µJy", "time_mjd": p.get("mjd"), "wavelength_um": p.get("wavelength_um"),
                         "detector": p.get("detector"), "value": p.get("flux_ujy"), "error": p.get("flux_err_ujy"), "source": p.get("key"), "method": "SPECTRUM"})
    n_img = len(_events(rec, "inspect"))
    mods = {}
    for r in rows:
        mods.setdefault(r["modality"], 0)
        mods[r["modality"]] += 1
    mods["image"] = n_img
    return {"method": "MODAL-1", "counts": mods, "fields": ["modality", "quantity", "unit", "time_mjd", "wavelength_um", "detector", "value", "error", "source", "method"],
            "rows": rows[:400], "n_rows": len(rows), "compatibility": MODAL_RULES}


# ------------------------------------------------------------------ WORLD-1
def world(rec: dict, hypotheses: dict | None = None) -> dict:
    tgt = rec.get("target") or "target"
    nodes, edges = {}, []

    def node(i, kind, label):
        nodes.setdefault(i, {"id": i, "kind": kind, "label": label})
        return i

    def edge(a, rel, b, rule, field):
        edges.append({"from": a, "rel": rel, "to": b, "basis": {"rule": rule, "field": field}})
    T = node(f"target:{tgt}", "target", tgt)
    for m in (e["data"] for e in _events(rec, "measure")):
        o = node(f"observation:{m.get('obs_id')}", "observation", m.get("obs_id"))
        d = node(f"detector:D{m.get('detector')}", "detector", f"D{m.get('detector')}")
        edge(o, "observes", T, "the exposure covers the target position", "$.events[measure].obs_id")
        edge(o, "taken with", d, "detector recorded in the file header", "$.events[measure].detector")
        if (m.get("photometry") or {}).get("status") == "ok":
            ms = node(f"measurement:flux:{m.get('obs_id')}", "measurement", f"flux {m.get('obs_id')}")
            edge(ms, "measured in", o, "APPHOT-1 aperture photometry", "$.events[measure].photometry")
    for p in _data(rec, "variability").get("pairs") or []:
        edge(f"observation:{p['a']}", "compared with", f"observation:{p['b']}", "WLMATCH-2 wavelength-matched pair (PAIRDIFF-1/2)", "$.events[variability].pairs")
    for o in _outcomes(rec):
        oc = node(f"outcome:{o.get('question')}", "outcome", f"{o.get('question')}: {o.get('category')}")
        edge(oc, "about", T, "ASSESS-2 outcome for the target", "$.events[assess].outcomes")
        for mth in (["PAIRDIFF-2", "CALCHECK-1"] if o.get("question") == "variability" else ["LINFIT-LOO-1", "PLATE-LOO-1"] if o.get("question") == "motion" else ["DQ"]):
            m_ = node(f"method:{mth}", "method", mth)
            edge(oc, "decided with", m_, "method recorded with the outcome's evidence", "$.events[assess].outcomes")
    for q in (hypotheses or {}).get("questions") or []:
        for h in q.get("hypotheses") or []:
            hn = node(f"hypothesis:{h['id']}", "hypothesis", h["id"])
            ov = h.get("overall") or ""
            rel = "consistent so far with" if ov.startswith("consistent") else "contradicted by" if ov == "contradicted" else "not decided by"
            edge(hn, rel, f"outcome:{q.get('question')}", f"HYPO-1 overall status: {ov or 'not recorded'}", "DISC-1 hypotheses")
    return {"method": "WORLD-1", "nodes": list(nodes.values()), "edges": edges, "relations": sorted({e["rel"] for e in edges}),
            "kinds": sorted({n["kind"] for n in nodes.values()}),
            "note": WORLD_NOTE}


def world_query(w: dict, q: dict) -> list[dict]:
    """Structured query: {"from_kind", "rel", "to_kind", "text"} (each optional); exact matching, never semantic."""
    kinds = {n["id"]: n["kind"] for n in w["nodes"]}
    labels = {n["id"]: (n.get("label") or "") for n in w["nodes"]}
    txt = (q.get("text") or "").strip().lower()
    out = []
    for e in w["edges"]:
        if q.get("rel") and e["rel"] != q["rel"]:
            continue
        if q.get("from_kind") and kinds.get(e["from"], e["from"].split(":")[0]) != q["from_kind"]:
            continue
        if q.get("to_kind") and kinds.get(e["to"], e["to"].split(":")[0]) != q["to_kind"]:
            continue
        if txt and txt not in (labels.get(e["from"], e["from"]) + " " + labels.get(e["to"], e["to"])).lower():
            continue
        out.append(e)
    return out


# ------------------------------------------------------------------ OPP-2
def opportunities(radar: dict | None, other_signals: set[str] | None = None) -> dict:
    items = []
    other = other_signals or set()
    for it in (radar or {}).get("items") or []:
        sig = it.get("signal")
        scope = "new to this collection" if sig not in other else "new to this investigation"
        items.append({"id": it.get("id"), "question": it.get("proposal"), "motivation": it.get("why"), "evidence": it.get("evidence") or [],
                      "data_needed": it.get("data_needed"), "method": it.get("action"), "expected_output": it.get("run_note"),
                      "cannot_establish": it.get("cannot_establish"), "feasibility": "can run now" if it.get("can_run_now") else "blocked",
                      "dependencies": it.get("refs") or [], "rank_reason": it.get("rank_reason"),
                      "novelty": {"scope": scope, "rule": ("no other investigation held here produced this kind of signal" if scope == "new to this collection"
                                                           else "another investigation held here produced the same kind of signal"),
                                  "underexplored_in_indexed_sources": "not evaluated — no literature index is connected",
                                  "independently_verified": "not evaluated — only an outside reproduction can establish it"}})
    return {"method": "OPP-2", "fields": ["question", "motivation", "evidence", "data_needed", "method", "expected_output", "cannot_establish",
                                          "feasibility", "dependencies", "novelty"],
            "scopes": NOVELTY_SCOPES, "items": items,
            "note": OPP_NOTE}


# ------------------------------------------------------------------ KCOMP-1
def compiler_statuses(comp: dict | None) -> dict:
    stages = []
    for s in (comp or {}).get("stages") or []:
        c = s.get("counts") or {}
        n = sum(c.get(k, 0) for k in ("pass", "warning", "fail"))
        review = any(ch.get("review") for ch in (comp or {}).get("checks") or [] if ch.get("stage") == s["id"])
        if n == 0:
            st = "Not evaluated"
        elif c.get("fail"):
            st = "Failed"
        elif review and not c.get("pass"):
            st = "Incomplete"
        elif c.get("warning"):
            st = "Passed with warnings"
        else:
            st = "Passed"
        stages.append({"id": s["id"], "name": s.get("name"), "status": st, "counts": c})
    return {"method": "KCOMP-1", "statuses": COMPILER_STATUSES, "stages": stages,
            "rule": "no check executed → Not evaluated; any failed check → Failed; only checks that ask for review → Incomplete; any warning → Passed with warnings; otherwise Passed",
            "meaning": KCOMP_MEANING}


# ------------------------------------------------------------------ EXTSRC-1
def external_sources(network: bool | None) -> dict:
    return {"method": "EXTSRC-1",
            "sources": [{**s, "state": "not connected", "updates": [],
                         "why": ("this environment cannot reach external services" if network is not True else "no connector is implemented for this source in this release")}
                        for s in SOURCES],
            "note": EXT_NOTE}


# ------------------------------------------------------------------ AGENTS-1
def agents(rec: dict, conv: dict, ld: dict, neg: dict, sig: dict) -> dict:
    o = {x.get("question"): x for x in _outcomes(rec)}
    syn = _synthetic(rec)
    rounds = []
    for q in ("variability", "motion"):
        if q not in o:
            continue
        oc = o[q]
        cv = next((c for c in conv["outcomes"] if c["outcome"] == q), None)
        msgs = [{"agent": "observer", "kind": "claim", "text": f"The recorded {q} outcome is {oc.get('category')}.", "cites": [f"outcome:{q}"]}]
        if cv:
            msgs.append({"agent": "skeptic", "kind": "challenge", "text": cv["reading"] + ". " + cv["method_dependence"] + ".", "cites": ["CONV-1"]})
        lq = [l for l in ld["leads"] if (q == "variability" and l["kind"] == "method disagreement") or (q == "motion" and l["kind"] in ("fit disagreement", "catalogue disagreement"))]
        if lq:
            msgs.append({"agent": "skeptic", "kind": "challenge", "text": f"{len(lq)} research lead(s) remain open: " + "; ".join(l["statement"] for l in lq[:3]) + ".",
                         "cites": [l["id"] for l in lq[:3]]})
        sel = [s for s in sig["series"] if (q == "variability" and s.get("unit") == "µJy") or (q == "motion" and s.get("unit") == "mas")]
        if sel:
            na = sorted({x["method"] for s in sel for x in s["analysis"]["selection"] if not x["applicable"]})
            msgs.append({"agent": "methodologist", "kind": "qualification",
                         "text": f"With {max(s['n'] for s in sel)} point(s) per series, these methods do not apply: {', '.join(na) or 'none'}.", "cites": ["SIGNAL-1"]})
            bic = [s["analysis"].get("model_comparison", {}).get("reading") for s in sel[:1]]
            msgs.append({"agent": "statistician", "kind": "qualification", "text": (bic[0] or "") + ".", "cites": ["SIGNAL-1"]})
        for lim in (oc.get("limitations") or [])[:2]:
            msgs.append({"agent": "skeptic", "kind": "limitation", "text": lim, "cites": [f"outcome:{q}"]})
        msgs.append({"agent": "archivist", "kind": "provenance",
                     "text": ("The data are SYNTHETIC test data: nothing here is an astronomical result." if syn else "The data come from the recorded archive files with checksums."),
                     "cites": ["provenance"]})
        open_ = bool(lq) or bool(cv and cv["outcome"] == "variability" and cv["lines"] and cv["independent_by_exposure"] < 2)
        rounds.append({"question": q, "messages": msgs,
                       "close": ("open: the challenges above are not resolved by the record" if open_ else "no challenge left unanswered by the record"),
                       "close_rule": "a round stays open while a research lead is open or fewer than two exposure-independent lines support a positive outcome"})
    return {"method": "AGENTS-1", "roles": ROLES, "rounds": rounds, "caveat": AGENT_CAVEAT}


# ------------------------------------------------------------------ EXPLAIN-1
LAYERS = ["observed", "measured", "method", "compared", "result", "certainty", "alternatives", "limits"]


def explain(rec: dict, hypotheses: dict | None = None) -> dict:
    meas = [e["data"] for e in _events(rec, "measure")]
    ok = [m for m in meas if m.get("mjd") is not None]
    dets = sorted({m["detector"] for m in ok})
    t0, t1 = (min(m["mjd"] for m in ok), max(m["mjd"] for m in ok)) if ok else (None, None)
    pairs = _data(rec, "variability").get("pairs") or []
    ast = _data(rec, "astrometry")
    nref = _data(rec, "references").get("n")
    out = []
    hyp = {q.get("question"): q for q in (hypotheses or {}).get("questions") or []}
    for o in _outcomes(rec):
        q = o.get("question")
        ev = o.get("evidence") or {}
        L = [{"layer": "observed", "key": "explain.observed",
              "params": {"n": len(ok), "target": rec.get("target"), "detectors": ", ".join(f"D{d}" for d in dets), "t0": _mjd_iso(t0)[:10] if t0 else "—",
                         "t1": _mjd_iso(t1)[:10] if t1 else "—"}}]
        if q == "variability":
            L.append({"layer": "measured", "key": "explain.measured.variability", "params": {"n": len(pairs)}})
            L.append({"layer": "method", "key": "explain.method", "params": {"methods": "APPHOT-1, WLMATCH-2, PAIRDIFF-1, PAIRDIFF-2, CALCHECK-1, ASSESS-2"}})
            L.append({"layer": "compared", "key": "explain.compared.variability", "params": {"n": len(pairs)}})
        elif q == "motion":
            L.append({"layer": "measured", "key": "explain.measured.motion", "params": {"refs": nref if nref is not None else "—", "epochs": len(ast.get("epochs") or [])}})
            L.append({"layer": "method", "key": "explain.method", "params": {"methods": "PLATE-LOO-1, EPHEM-AA-LP-1, LINFIT-EPOCH-1, LINFIT-LOO-1, ASSESS-2"}})
            L.append({"layer": "compared", "key": "explain.compared.motion", "params": {"baseline": _f(ev.get("baseline_yr"), 3) if ev.get("baseline_yr") is not None else "—"}})
        else:
            L.append({"layer": "measured", "key": "explain.measured.quality", "params": {"n": len(meas)}})
            L.append({"layer": "method", "key": "explain.method", "params": {"methods": "DQ-1, ASSESS-2"}})
            L.append({"layer": "compared", "key": "explain.compared.quality", "params": {}})
        L.append({"layer": "result", "key": "explain.result", "params": {"category": o.get("category")}, "recorded": [o.get("statement") or ""]})
        sens = o.get("sensitivity") or {}
        L.append({"layer": "certainty", "key": "explain.certainty", "params": {"n": len(sens)},
                  "recorded": [f"{k} = {v}" for k, v in sens.items() if not isinstance(v, (dict, list))][:6] + (o.get("criteria") or [])[:4]})
        hs = (hyp.get(q) or {}).get("hypotheses") or []
        L.append({"layer": "alternatives", "key": "explain.alternatives", "params": {"n": len(hs)},
                  "recorded": [f"{h['id']} — {h.get('overall')}: {h.get('statement')}" for h in hs]})
        L.append({"layer": "limits", "key": "explain.limits", "params": {}, "recorded": o.get("limitations") or []})
        out.append({"question": q, "category": o.get("category"), "layers": L})
    return {"method": "EXPLAIN-1", "layers": LAYERS, "outcomes": out,
            "note": EXPLAIN_NOTE}


# ------------------------------------------------------------------ TIMES-1
def timeline(rec: dict) -> dict:
    obs = sorted({(e["data"].get("mjd"), e["data"].get("obs_id")) for e in _events(rec, "measure") if (e.get("data") or {}).get("mjd") is not None})
    prov = [p for e in rec["events"] for p in e.get("provenance") or []]
    retrieved = sorted({p.get("retrieved_at") for p in prov if p.get("retrieved_at")})
    releases = sorted({p.get("release") for p in prov if p.get("release")})
    return {"method": "TIMES-1",
            "lanes": [
                {"lane": "observation", "meaning": LANE_MEANING["observation"],
                 "items": [{"time": _mjd_iso(m), "mjd": m, "ref": o} for m, o in obs]},
                {"lane": "processing", "meaning": LANE_MEANING["processing"],
                 "items": [{"time": rec.get("created_at"), "ref": "investigation record"}]},
                {"lane": "publication", "meaning": LANE_MEANING["publication"],
                 "items": [{"time": r, "ref": "retrieved"} for r in retrieved] + [{"time": None, "ref": f"release {r} (release date not recorded)"} for r in releases]},
                {"lane": "event", "meaning": LANE_MEANING["event"],
                 "items": [], "state": EVENT_STATE},
            ],
            "note": TIMES_NOTE}


# ------------------------------------------------------------------ DIRECT-1
def director_plan(rec: dict, ld: dict, neg: dict, sig: dict, opp: dict) -> dict:
    steps = []

    def step(sid, action, ws, reason, kind="open"):
        steps.append({"id": sid, "action": action, "workspace": ws, "reason": reason, "kind": kind, "requires_approval": True})
    o = {x.get("question"): x for x in _outcomes(rec)}
    dq = o.get("data_quality")
    if dq and dq.get("category") != "usable":
        step("D1", "Review data quality", "quality", f"data quality outcome is {dq.get('category')}")
    if ld["leads"]:
        step("D2", "Examine research leads", "world", f"{len(ld['leads'])} contradiction(s) recorded as research leads")
    can = [i for i in opp["items"] if i["feasibility"] == "can run now"]
    if can:
        step("D3", "Inspect the highest-ranked opportunity", "radar", f"{can[0]['question']} ({can[0]['rank_reason']})")
    if any(not x["applicable"] for s in sig["series"] for x in s["analysis"]["selection"]):
        step("D4", "Check which signal methods apply", "signal", "several time-series methods are not applicable to series this short")
    if neg["counts"].get("unresolved explanation"):
        step("D5", "Review unresolved explanations", "arena", f"{neg['counts']['unresolved explanation']} explanation(s) unresolved")
    step("D6", "Compile and review", "compiler", "structural checks before writing conclusions")
    step("D7", "Prepare a handoff", "gateway", "record what is established, open and unknown for the next researcher")
    return {"method": "DIRECT-1", "steps": steps,
            "rules": DIRECTOR_RULES}


# ------------------------------------------------------------------ the report
def report(rec: dict, hypotheses: dict | None = None, neg: dict | None = None, comp: dict | None = None, radar: dict | None = None,
           network: bool | None = None, sibling_hashes: list[str] | None = None, other_signals: set[str] | None = None) -> dict:
    sig = sigintel.workbench(rec)
    conv = convergence(rec, sibling_hashes)
    ld = leads(rec, hypotheses)
    ng = negative_space(rec, neg, hypotheses, network)
    opp = opportunities(radar, other_signals)
    return {"content_hash": rec.get("content_hash"), "synthetic": _synthetic(rec),
            "signal": sig, "convergence": conv, "leads": ld, "negative": ng, "multimodal": multimodal(rec), "world": world(rec, hypotheses),
            "opportunities": opp, "compiler": compiler_statuses(comp), "sources": external_sources(network),
            "agents": agents(rec, conv, ld, ng, sig), "explain": explain(rec, hypotheses), "timeline": timeline(rec),
            "director": director_plan(rec, ld, ng, sig, opp), "market": market()}


# ------------------------------------------------------------------ EXPMKT-1: the experiment marketplace (a catalogue, not a store)
MARKET = [
    {"id": "exp:negative_control", "name": "Negative control", "kind": "experiment template", "action": "experiments",
     "validation": "known answer on synthetic fixtures", "evidence": "tests/unit/test_research_os.py::test_experiment_validation_and_negative_control"},
    {"id": "exp:method_comparison", "name": "Method comparison (motion)", "kind": "experiment template", "action": "experiments",
     "validation": "known answer on synthetic fixtures", "evidence": "tests/unit/test_research_os.py::test_experiment_validation_and_negative_control"},
    {"id": "exp:reproducibility", "name": "Reproducibility (two executions)", "kind": "experiment template", "action": "experiments",
     "validation": "known answer on synthetic fixtures", "evidence": "tests/integration/test_api.py::test_phase6_research_planner_sessions_experiments_connectors"},
    {"id": "exp:parameter", "name": "Parameter experiment", "kind": "experiment template", "action": "experiments", "validation": "unvalidated", "evidence": None},
    {"id": "exp:sensitivity", "name": "Sensitivity (STAB-1 set)", "kind": "experiment template", "action": "experiments", "validation": "unvalidated", "evidence": None},
    {"id": "exp:robustness", "name": "Robustness", "kind": "experiment template", "action": "experiments", "validation": "unvalidated", "evidence": None},
    {"id": "sig:lomb_scargle", "name": "Lomb–Scargle periodogram", "kind": "signal method", "action": "signal",
     "validation": "known answer on synthetic signals", "evidence": "tests/unit/test_phase10.py::test_signal_methods_known_answers"},
    {"id": "sig:robust_regression", "name": "Theil–Sen trend", "kind": "signal method", "action": "signal",
     "validation": "known answer on synthetic signals", "evidence": "tests/unit/test_phase10.py::test_signal_methods_known_answers"},
    {"id": "sig:change_point", "name": "Single change point", "kind": "signal method", "action": "signal",
     "validation": "known answer on synthetic signals", "evidence": "tests/unit/test_phase10.py::test_signal_methods_known_answers"},
    {"id": "sig:dcf", "name": "Discrete correlation function", "kind": "signal method", "action": "signal",
     "validation": "known answer on synthetic signals", "evidence": "tests/unit/test_phase10.py::test_signal_methods_known_answers"},
    {"id": "sig:model_comparison", "name": "Model comparison (BIC with assumption checks)", "kind": "signal method", "action": "signal",
     "validation": "known answer on synthetic signals", "evidence": "tests/unit/test_phase10.py::test_bic_only_when_assumptions_hold"},
    {"id": "sig:wavelet", "name": "Haar wavelet decomposition", "kind": "signal method", "action": "signal", "validation": "unvalidated", "evidence": None},
]


def market() -> dict:
    items = [{**m, "recommended": m["validation"] != "unvalidated",
              "status": ("validated against a known answer on synthetic data — not on real observations" if m["validation"] != "unvalidated"
                         else "available, not recommended: no known-answer test")} for m in MARKET]
    return {"method": "EXPMKT-1", "items": items,
            "rule": "an item is shown as recommended only when a named test checks it against a known answer; nothing is installed, bought or downloaded"}
