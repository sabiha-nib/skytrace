"""Discovery engine (DISC-1): what this investigation can and cannot establish, and what to do next.

Stages, each computed only from the investigation record, the bundle's discovery index and manifest, and the
capability registry:

  A  inventory      every evidence item with its identifier, type, source, provenance, epoch, channel, integrity
                    information, quality status and method versions. Unknown fields stay null and are counted.
  B  questions      a fixed set of research questions, each mapped to registered capabilities, with whether this
                    investigation can answer it; questions it cannot answer say why and what would be needed.
  C  test plans     for each question: required and available inputs, method, preconditions, assumptions,
                    expected outputs, limitations and validation checks.
  D  execution      done by the existing pipeline (analysis, STAB-1, PROVCHECK-1); the plan points to it.
  E  review         the ASSESS-2 outcome, HYPO-1 tests and UNC-1 decomposition (separate modules).
  F  next steps     rule-based recommendations, each with why, data required, what it can and cannot establish,
                    and whether it runs locally or needs an unavailable service. No confidence gain is promised.
"""

from __future__ import annotations

from . import capabilities, hypotheses, uncertainty

METHOD = "DISC-1"
NA = "not applicable"     # a field that does not apply to this kind of item (distinct from unknown = null)


def _first(record, step):
    return next((e for e in record["events"] if e["step"] == step), None)


# ---------------------------------------------------------------------------- A. inventory
def inventory(record: dict, discovery: dict, manifest: dict) -> dict:
    files = {f["path"]: f for f in manifest.get("files", [])}
    meas = {e["data"]["key"]: e for e in record["events"] if e["step"] == "measure" and "key" in e["data"]}
    items, unknown = [], 0

    def item(**kw):
        nonlocal unknown
        unknown += sum(1 for k, v in kw.items() if v is None and k not in ("limitations", "wavelength_um", "release", "file"))
        items.append(kw)

    t = _first(record, "target")
    ast = (t or {}).get("data", {}).get("astrometry", {})
    tprov = ((t or {}).get("provenance") or [{}])[0]
    item(id=f"target:{record.get('target')}", type="catalogue astrometry", source=ast.get("source"),
         origin=tprov.get("origin"), epoch=ast.get("ref_epoch"), channel=NA,
         sha256=tprov.get("content_sha256") or None, quality=NA, methods=NA,
         fields={k: ast.get(k) for k in ("ra", "dec", "pmra", "pmdec", "parallax")},
         limitations=["identity and astrometry as recorded by the catalogue; not measured here"])
    r = _first(record, "references")
    rd = (r or {}).get("data", {})
    rprov = ((r or {}).get("provenance") or [{}])[0]
    item(id="references", type="reference-star catalogue", source=rd.get("catalogue"), origin=rprov.get("origin"),
         epoch="per star (catalogue reference epoch)", channel=NA, sha256=rprov.get("content_sha256") or None,
         quality=f"{rd.get('n')} of {rd.get('n_catalogue')} kept by {(rd.get('selection') or {}).get('method')}" if rd else None,
         methods=[(rd.get("selection") or {}).get("method")] if rd else None, fields={}, limitations=[])
    for o in sorted(discovery.get("observations", []), key=lambda o: (o.get("t_mid_mjd") or 0, o.get("detector") or 0)):
        me = meas.get(o["key"])
        md = (me or {}).get("data", {})
        fe = files.get(o.get("file") or "")
        prov = (fe or {}).get("provenance") or {}
        status = (None if not o.get("included") else
                  f"photometry {md.get('quality_code')}, astrometry {md.get('astro_code')}" if md.get("quality_code")
                  else (me or {}).get("status"))
        lims = []
        if not o.get("included"):
            lims.append(f"excluded at selection: {o.get('exclusion_reason')}")
        if o.get("included") and not me:
            lims.append("not measured in this run (detector filter or limit)")
        item(id=o["key"], type="image (Level-2 spectral image)" if o.get("file") else "archive search result (no file stored)",
             source=(prov.get("source") + (f" {prov.get('release')}" if prov.get("release") else "")) if prov.get("source") else None,
             origin=prov.get("origin"), epoch=o.get("t_mid_iso"), channel=f"D{o['detector']}" if o.get("detector") else None,
             wavelength_um=md.get("wavelength_um"), release=o.get("release"), file=o.get("file"),
             sha256=(fe or {}).get("sha256"), quality=status if o.get("included") else NA,
             methods="see the analysis run" if me else NA, included=bool(o.get("included")),
             fields={}, limitations=lims)
    params = record.get("parameters", {})
    item(id=f"run:{record.get('content_hash', '')[:16]}", type="analysis run", source="skytrace " + str((record.get("software") or {}).get("skytrace")),
         origin="computed", epoch=record.get("created_at"), channel=NA, sha256=record.get("content_hash"),
         quality=NA, methods=params.get("methods"), fields={k: params.get(k) for k in ("analysis_version", "bundle", "bundle_kind")},
         limitations=[])
    obs = [i for i in items if "included" in i]
    incl = [i for i in obs if i.get("included")]
    visits = sorted({(i["epoch"] or "")[:10] for i in incl})
    return {"items": items, "summary": {
        "n_items": len(items), "n_observations": len(obs), "n_images": sum(1 for i in obs if i.get("file")), "n_included": len(incl), "n_excluded": len(obs) - len(incl),
        "detectors": sorted({i["channel"] for i in incl if i["channel"]}), "releases": sorted({i["release"] for i in incl if i.get("release")}),
        "dates": visits, "origins": sorted({i["origin"] for i in items if i.get("origin")}), "unknown_fields": unknown,
        "synthetic": params.get("bundle_kind") == "synthetic"}}


# ---------------------------------------------------------------------------- B/C. questions and test plans
def _facts(record: dict) -> dict:
    outs = {o["question"]: o for o in ((_first(record, "assess") or {}).get("data") or {}).get("outcomes", [])}
    pairs = ((_first(record, "pairs") or {}).get("data") or {}).get("accepted", [])
    var = (_first(record, "variability") or {}).get("data") or {}
    calibrated = sum(1 for p in var.get("pairs", []) if (p.get("differential") or {}).get("calibrated"))
    a = _first(record, "astrometry")
    astro_n = sum(1 for e in record["events"] if e["step"] == "measure" and e["data"].get("astro_code") == "ok")
    measured = sum(1 for e in record["events"] if e["step"] == "measure" and "centroid" in e.get("data", {}))
    epochs = len(((a or {}).get("data") or {}).get("epochs") or [])
    return {"outcomes": outs, "n_pairs": len(pairs), "n_calibrated": calibrated, "calcheck": var.get("calibration_check") or {},
            "astro_n": astro_n, "epochs": epochs, "measured": measured, "motion_ok": bool(a and a["status"] == "ok"),
            "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic"}


QUESTIONS = [
    {"id": "Q-VAR", "text": "Did the target's brightness change between wavelength-matched observations?",
     "capabilities": ["wavelength_match", "brightness", "assessment"], "outcome": "variability",
     "requires": [("≥ 1 wavelength-matched pair with usable photometry", lambda f: f["n_pairs"] >= 1),
                  ("≥ 1 pair with ≥ 3 matched reference stars (calibrated comparison)", lambda f: f["n_calibrated"] >= 1)],
     "method": "WLMATCH-2 pairing, PAIRDIFF-1/2 comparison, CALCHECK-1 error scale, ASSESS-2 decision",
     "preconditions": ["same detector and release", "|Δλ| + 2 nm ≤ 0.5 × bandwidth"],
     "assumptions": ["constant reference stars", "per-pixel VARIANCE describes the noise up to the CALCHECK scale"],
     "outputs": ["category", "max |z| (calibrated)", "5σ sensitivity as a fractional change"],
     "validation": ["robustness tests with injected gain changes", "STAB-1 stability"]},
    {"id": "Q-MOT", "text": "Does the target move, and does its motion agree with the catalogue?",
     "capabilities": ["motion", "assessment"], "outcome": "motion",
     "requires": [("≥ 2 exposures with a usable target position and plate solution", lambda f: f["astro_n"] >= 2),
                  ("≥ 2 visits for the visit-averaged fit", lambda f: f["epochs"] >= 2)],
     "method": "REFSEL-2 references, PLATE-LOO-1 plates, EPHEM-AA-LP-1 parallax, LINFIT-EPOCH-1 fit, ASSESS-2 decision",
     "preconditions": ["Gaia-referenced plate per exposure", "catalogue proper motion available for comparison"],
     "assumptions": ["linear motion over the baseline", "parallax removed with the low-precision ephemeris"],
     "outputs": ["proper motion ± σ", "difference from catalogue (σ)", "5σ sensitivity"],
     "validation": ["injected-motion synthetic tests", "parallax robustness test", "STAB-1"]},
    {"id": "Q-COMPAT", "text": "Can two chosen observations be compared for brightness?",
     "capabilities": ["wavelength_match"], "outcome": None,
     "requires": [("≥ 2 measured observations with a wavelength at the target", lambda f: f["measured"] >= 2)],
     "method": "WLMATCH-2 on the two logged measurements (Time Machine)", "preconditions": [], "assumptions": [],
     "outputs": ["accepted / rejected with reason code"], "validation": ["Python/browser parity test"]},
    {"id": "Q-SENS", "text": "Which analysis choices change the result?", "capabilities": ["stability"], "outcome": None,
     "requires": [("a finished analysis", lambda f: bool(f["outcomes"]))],
     "method": "STAB-1: aperture ±0.5 px, tolerance 0.3, clip 3σ/6σ", "preconditions": [], "assumptions": [],
     "outputs": ["stable / fragile per outcome"], "validation": ["robustness suite"]},
    {"id": "Q-ALT", "text": "Which explanations remain viable?", "capabilities": ["hypotheses"], "outcome": None,
     "requires": [("a finished analysis", lambda f: bool(f["outcomes"]))],
     "method": "HYPO-1 rule-based tests on recorded values", "preconditions": [], "assumptions": ["the assessment's thresholds"],
     "outputs": ["evidence matrix"], "validation": ["unit tests of each rule"]},
    {"id": "Q-UNC", "text": "What are the uncertainties made of?", "capabilities": ["uncertainty"], "outcome": None,
     "requires": [("a motion fit or a matched pair", lambda f: f["motion_ok"] or f["n_pairs"] >= 1)],
     "method": "UNC-1 decomposition of logged σ terms", "preconditions": [], "assumptions": [],
     "outputs": ["σ components per quantity"], "validation": ["recomputed z equals logged z"]},
    {"id": "Q-QUAL", "text": "How much of the data is usable, and why were exposures rejected?",
     "capabilities": ["measure", "assessment"], "outcome": "data_quality",
     "requires": [("≥ 1 measured exposure", lambda f: f["measured"] >= 1)],
     "method": "status codes from measurement; ASSESS-2 data-quality outcome", "preconditions": [], "assumptions": [],
     "outputs": ["usable fraction", "reason codes"], "validation": ["status-code check in PROVCHECK-1"]},
    {"id": "Q-REPRO", "text": "Can this result be reproduced from the stored files?", "capabilities": ["provenance", "package"],
     "outcome": None, "requires": [("the bundle and the record", lambda f: True)],
     "method": "PROVCHECK-1 (hashes, origins, codes, re-run determinism)", "preconditions": ["server for the re-run"],
     "assumptions": [], "outputs": ["10 named checks"], "validation": ["tamper tests"]},
]
UNANSWERABLE = [
    {"id": "Q-CAUSE", "text": "What physically causes the change?",
     "why": "needs time-resolved spectra or data from other instruments and a physical model; SKYTRACE measures change, not cause",
     "needed": ["spectral time series", "astrophysical model fitting (not implemented)"]},
    {"id": "Q-DISCOVERY", "text": "Is this a new astronomical discovery?",
     "why": "no single analysis establishes a discovery; it needs real archive data, independent confirmation and expert review",
     "needed": ["real observations (blocked here)", "independent instruments or epochs", "peer review"]},
    {"id": "Q-DIST", "text": "How far away is the target?",
     "why": "no distance is measured; the catalogue parallax is quoted and used only to correct positions",
     "needed": ["a parallax fit over many epochs (not implemented)"]},
]


def questions(record: dict) -> list[dict]:
    f = _facts(record)
    out = []
    for q in QUESTIONS:
        req = [{"input": label, "available": bool(test(f))} for label, test in q["requires"]]
        missing = [r["input"] for r in req if not r["available"]]
        oc = f["outcomes"].get(q["outcome"]) if q["outcome"] else None
        status = ("answerable" if not missing else "answerable with limits" if any(r["available"] for r in req) else "not answerable")
        out.append({"id": q["id"], "text": q["text"], "status": status, "capabilities": q["capabilities"],
                    "plan": {"required_inputs": req, "missing_inputs": missing, "method": q["method"],
                             "preconditions": q["preconditions"], "assumptions": q["assumptions"],
                             "expected_outputs": q["outputs"], "validation": q["validation"],
                             "limitations": ["synthetic test data: no astronomical conclusion"] if f["synthetic"] else []},
                    "current_answer": {"category": oc["category"], "statement": oc["statement"]} if oc else None})
    for q in UNANSWERABLE:
        out.append({"id": q["id"], "text": q["text"], "status": "not answerable", "capabilities": [],
                    "plan": {"required_inputs": [], "missing_inputs": q["needed"], "method": None, "preconditions": [],
                             "assumptions": [], "expected_outputs": [], "validation": [], "limitations": [q["why"]]},
                    "current_answer": None, "why_not": q["why"]})
    return out


# ---------------------------------------------------------------------------- F. next steps
def next_steps(record: dict, hyp: dict, availability: dict) -> list[dict]:
    f = _facts(record)
    oc = {k: v["category"] for k, v in f["outcomes"].items()}
    net = availability.get("network")
    server = availability.get("server")
    out = []

    def rec(action, why, question, data, can, cannot, capability, local):
        needs = None if local else ("network access to the archives" if capability == "archive" else "the Skytrace server")
        out.append({"action": action, "why": why, "question": question, "data_required": data, "can_establish": can,
                    "cannot_establish": cannot, "capability": capability, "runs_locally": local,
                    "requires_unavailable_service": (needs if (capability == "archive" and net is False) or
                                                     (not local and capability != "archive" and server is False) else None)})

    if f["synthetic"]:
        rec("Acquire real SPHEREx observations for a challenge target", "every result here comes from synthetic test data",
            "any", "archive bundle (scripts/acquire_targets.py)", "a real-data version of every analysis",
            "nothing until the data exist", "archive", False)
    rec("Run the stability check", "shows whether each outcome survives small parameter changes", "Q-SENS",
        "this investigation", "whether outcomes are fragile", "statistical uncertainty", "stability", False)
    if oc.get("variability") == "variability_candidate":
        dets = next((t for q in hyp["questions"] if q["question"] == "variability" for h in q["hypotheses"]
                     for t in h["tests"] if t["id"] == "T-REPEAT"), {})
        if dets.get("status") != "consistent":
            rec("Look for the change on a second detector", "a change seen on one detector cannot rule out a detector-specific effect",
                "Q-VAR", "matched pairs on another detector at the same dates", "whether the change repeats independently",
                "the physical cause", "archive", False)
        rec("Inspect the significant pairs in the Time Machine", "check registration, flags and neighbours by eye", "Q-VAR",
            "the significant pairs", "visible artifacts", "a measurement", "wavelength_match", True)
    if oc.get("variability") in ("calibration_limited",):
        rec("Check reference-star counts per pair", "the difference could not be separated from a calibration change", "Q-VAR",
            "matched reference stars (≥ 3 per pair)", "whether calibration explains it", "variability by itself", "brightness", True)
    if oc.get("variability") in ("insufficient_evidence", "spectral_difference_only"):
        rec("Acquire a revisit at a matched wavelength", "no wavelength-matched pair tests variability", "Q-VAR",
            "same-detector exposures at the same wavelength", "a variability test", "the cause", "archive", False)
    if oc.get("motion") in ("insufficient_evidence", "measurement_failed") or f["epochs"] < 2:
        rec("Acquire more visits", "the motion needs at least two visits with plate solutions", "Q-MOT",
            "exposures on more dates", "a motion measurement", "the cause of any motion", "archive", False)
    if oc.get("motion") in ("registration_limited", "motion_inconsistent"):
        rec("Inspect plate residuals and reference stars", "registration or references may limit the motion", "Q-MOT",
            "plate solutions per exposure", "whether registration explains the result", "the true motion", "motion", True)
    if (f["calcheck"] or {}).get("status") == "underestimated":
        rec("Review the error model", f"reference stars scatter {f['calcheck'].get('robust_scatter', 0):.2f}× their stated errors", "Q-UNC",
            "reference-star comparisons", "how optimistic the stated errors are", "the cause of the excess scatter", "uncertainty", True)
    rec("Verify provenance and re-run", "confirms every number traces to unchanged files and the result reproduces", "Q-REPRO",
        "the bundle and this record", "integrity and determinism", "scientific validity", "provenance", False)
    return out


def report(record: dict, discovery: dict, manifest: dict, availability: dict | None = None) -> dict:
    av = availability or {}
    hyp = hypotheses.evaluate(record)
    return {"method": METHOD, "content_hash": record.get("content_hash"), "synthetic": record.get("parameters", {}).get("bundle_kind") == "synthetic",
            "inventory": inventory(record, discovery, manifest), "questions": questions(record),
            "hypotheses": hyp, "uncertainty": uncertainty.decompose(record),
            "next_steps": next_steps(record, hyp, av), "capabilities": capabilities.registry(av),
            "stages": ["A inventory", "B questions", "C test plans", "D execution (pipeline)", "E review", "F next steps", "G record"]}
