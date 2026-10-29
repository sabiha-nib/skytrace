"""Read-only, schema-validated tools the copilot may call.

They read one finished investigation (plus its bundle's discovery records and
manifest) through view.InvestigationView. None of them fetch data, modify
files, run code or reach the network. Arguments are validated with pydantic
(unknown fields rejected, bounded sizes); outputs are size-bounded and every
call is recorded in a ToolSession so the guard can check citations.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..view import InvestigationView, evidence_graph

MAX_OUTPUT_CHARS = 14000
KEY = Field(..., min_length=3, max_length=96, pattern=r"^[A-Za-z0-9_:.\-]+$", description="Observation key, e.g. QR3:2025W21_1A_0012_1:D2")


CONTRACT = "TOOLS-2"
ERROR_CODES = ("unknown_tool", "invalid_arguments", "not_found", "not_compatible", "output_too_large", "budget_exhausted")


class ToolError(ValueError):
    def __init__(self, message: str, code: str = "not_found"):
        super().__init__(message)
        self.code = code


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_Args):
    pass


class ListObsArgs(_Args):
    status: Literal["any", "included", "excluded", "measured_ok", "rejected"] = "any"
    detector: int | None = Field(None, ge=1, le=6)
    limit: int = Field(20, ge=1, le=50)
    offset: int = Field(0, ge=0, le=5000)


class KeyArgs(_Args):
    key: str = KEY


class OptKeyArgs(_Args):
    key: str | None = Field(None, min_length=3, max_length=96, pattern=r"^[A-Za-z0-9_:.\-]+$")
    limit: int = Field(10, ge=1, le=50)


class PairArgs(_Args):
    key_a: str = KEY
    key_b: str = KEY


class CompatArgs(_Args):
    key_a: str = KEY
    key_b: str | None = Field(None, min_length=3, max_length=96, pattern=r"^[A-Za-z0-9_:.\-]+$")


class GraphArgs(_Args):
    focus: str | None = Field(None, max_length=200, description="node id, e.g. claim:motion or meas:<key>")


class ClaimArgs(_Args):
    claim: str = Field(..., min_length=3, max_length=600)
    evidence_ids: list[str] = Field(..., min_length=1, max_length=8)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    output: dict            # the tool's result payload (or {"error": ...})
    ok: bool
    seconds: float
    error_code: str = ""
    envelope: dict = field(default_factory=dict)   # what the model receives (TOOLS-2 contract)


@dataclass
class ToolSession:
    view: InvestigationView
    target_id: str
    calls: list[ToolCall] = field(default_factory=list)
    availability: dict = field(default_factory=dict)   # {"server": bool, "network": bool | None}

    def outputs(self) -> dict[str, dict]:
        return {c.id: c.output for c in self.calls if c.ok}

    def executed_names(self) -> set[str]:
        return {c.name for c in self.calls if c.ok}


def _short_meas(m: dict | None) -> dict | None:
    if not m:
        return None
    c, p = m.get("centroid") or {}, m.get("photometry") or {}
    return {"quality": m.get("quality"), "quality_code": m.get("quality_code"), "astro_code": m.get("astro_code"),
            "release": m.get("release"), "wavelength_um": m.get("wavelength_um"), "bandwidth_um": m.get("bandwidth_um"),
            "flux_ujy": p.get("flux_ujy"), "flux_err_ujy": p.get("flux_err_ujy"), "snr": p.get("snr"),
            "photometry_status": p.get("status"), "centroid_x": c.get("x"), "centroid_y": c.get("y"),
            "centroid_sigma_px": c.get("sigma_x"), "centroid_converged": c.get("converged"),
            "plate_refs": (m.get("plate") or {}).get("n_refs"), "plate_rms_mas": (m.get("plate") or {}).get("rms_mas")}


def t_list(s: ToolSession, a: ListObsArgs) -> dict:
    rows = []
    for o in s.view.observations():
        m = s.view.measurements.get(o["key"])
        me = s.view.measure_events.get(o["key"])
        st = me["status"] if me else None
        ok = {"any": True, "included": o.get("included"), "excluded": not o.get("included"),
              "measured_ok": st == "ok", "rejected": st in ("rejected", "failed") or not o.get("included")}[a.status]
        if not ok or (a.detector and o.get("detector") != a.detector):
            continue
        rows.append({"key": o["key"], "release": o["release"], "detector": o["detector"], "t_mid_iso": o.get("t_mid_iso"),
                     "image_wavelength_range_um": [o.get("em_min_um"), o.get("em_max_um")], "included": o.get("included"),
                     "exclusion_reason": o.get("exclusion_reason"), "measurement_status": st,
                     "wavelength_at_target_um": (m or {}).get("wavelength_um"), "quality": (m or {}).get("quality")
                     or (me["detail"] if me else None),
                     "quality_code": ((me or {}).get("data") or {}).get("quality_code"),
                     "astro_code": ((me or {}).get("data") or {}).get("astro_code")})
    return {"n_matching": len(rows), "offset": a.offset, "rows": rows[a.offset:a.offset + a.limit],
            "synthetic": s.view.is_synthetic()}


def t_meta(s: ToolSession, a: KeyArgs) -> dict:
    o = s.view.observation(a.key)
    if not o:
        raise ToolError(f"unknown observation {a.key!r}")
    fe = s.view.file_entry(o.get("file"))
    insp = s.view.inspection.get(f"{o['release']}:D{o['detector']}")
    if insp is None:
        ie = next((e for e in s.view.events if e["step"] == "inspect" and e["data"].get("key", "").startswith(o["release"])
                   and f"D{o['detector']}" in e["detail"]), None)
        insp = ie["data"] if ie else None
    return {"observation": {k: o.get(k) for k in ("key", "release", "obs_id", "detector", "t_min_mjd", "t_max_mjd", "t_mid_mjd",
                                                   "t_mid_iso", "em_min_um", "em_max_um", "access_url", "cutout_url",
                                                   "included", "exclusion_reason", "file")},
            "file": {"sha256": fe["sha256"], "bytes": fe["bytes"], "provenance": fe.get("provenance")} if fe else None,
            "product_inspection": {k: insp.get(k) for k in ("reader", "extensions", "image_shape", "image_bunit",
                                                            "pixel_scale_arcsec", "synthetic", "warnings")} if insp else None}


def t_compat(s: ToolSession, a: CompatArgs) -> dict:
    if a.key_b:
        r = s.view.pair_comparison(a.key_a, a.key_b)
        if "error" in r:
            raise ToolError(r["error"], "not_compatible")
        return {k: r[k] for k in ("a", "b", "compatible_for_photometry", "reason", "rule", "delta_lambda_um", "tolerance_um",
                                  "wavelength_a_um", "wavelength_b_um", "delta_t_days", "t_a_iso", "t_b_iso")}
    if a.key_a not in s.view.measurements:
        raise ToolError(f"no logged measurement for {a.key_a!r}")
    partners = [d for d in s.view.accepted_pairs() if a.key_a in (d["a"], d["b"])]
    pe = s.view.first("pairs")
    return {"key": a.key_a, "wavelength_um": s.view.measurements[a.key_a].get("wavelength_um"),
            "detector": s.view.measurements[a.key_a].get("detector"),
            "compatible_partners": [{"key": d["b"] if d["a"] == a.key_a else d["a"], "delta_lambda_um": d["delta_lambda_um"],
                                     "delta_t_days": d["delta_t_days"]} for d in partners][:30],
            "n_compatible_partners": len(partners),
            "investigation_rejection_reasons": pe["data"].get("rejection_reasons") if pe else None,
            "rule": (pe["data"].get("rule", "WLMATCH-1") if pe else "WLMATCH-2") +
                    ": same detector, usable photometry, |Δλ| + margin <= tolerance x bandwidth"
                    + (", same release" if pe and pe["data"].get("same_release") else "")}


def t_quality(s: ToolSession, a: KeyArgs) -> dict:
    me = s.view.measure_events.get(a.key)
    if not me:
        o = s.view.observation(a.key)
        if o and not o.get("included"):
            return {"key": a.key, "included": False, "exclusion_reason": o.get("exclusion_reason")}
        raise ToolError(f"no measurement logged for {a.key!r}")
    m = me["data"]
    plate = m.get("plate") or {}
    return {"key": a.key, "status": me["status"], "detail": me["detail"], "quality": m.get("quality"),
            "flags_in_aperture": m.get("flag_summary"), "notes": m.get("notes"),
            "photometry_status": (m.get("photometry") or {}).get("status"),
            "centroid": {k: (m.get("centroid") or {}).get(k) for k in ("converged", "reduced_chi2", "fwhm_x", "fwhm_y", "n_masked", "message")},
            "plate": {k: plate.get(k) for k in ("n_refs", "n_candidates", "rms_mas", "ref_rejections", "rejected_refs", "failed", "method")}}


def t_meas(s: ToolSession, a: OptKeyArgs) -> dict:
    if a.key:
        m = s.view.measurements.get(a.key)
        if not m:
            raise ToolError(f"no measurement logged for {a.key!r}")
        return {"key": a.key, "t_mid_iso": m.get("t_mid_iso"), "detector": m.get("detector"), **_short_meas(m),
                "target_position_mas": m.get("target_xi_eta_mas"), "units": {"flux": "µJy (aperture, not aperture-corrected)",
                                                                              "position": "mas on the tangent plane"}}
    rows = [{"key": k, "t_mid_iso": m.get("t_mid_iso"), "detector": m.get("detector"), **_short_meas(m)}
            for k, m in s.view.measurements.items()]
    return {"n": len(rows), "rows": rows[: a.limit], "units": {"flux": "µJy (aperture, not aperture-corrected)"}}


def t_compare(s: ToolSession, a: PairArgs) -> dict:
    r = s.view.pair_comparison(a.key_a, a.key_b)
    if "error" in r:
        raise ToolError(r["error"], "not_compatible")
    return r


def t_astro(s: ToolSession, _: NoArgs) -> dict:
    ast = s.view.astrometry()
    out = next((o for o in s.view.outcomes() if o["question"] == "motion"), None)
    if not ast:
        e = s.view.first("astrometry")
        return {"available": False, "reason": e["detail"] if e else "no astrometry step logged", "outcome": out}
    rej = [ser["key"] for ser in ast["series"] if not ser.get("used_in_fit", True)]
    rms = sorted(ser["plate_rms_mas"] for ser in ast["series"])
    return {"available": True, "fit": ast["fit"], "catalogue": ast["catalogue"], "comparison": ast["comparison"],
            "median_plate_rms_mas": rms[len(rms) // 2] if rms else None, "n_exposures": len(ast["series"]),
            "rejected_epochs": rej, "parallax_systematic_bound_mas": ast.get("parallax_systematic_bound_mas"),
            "fit_kind": ast.get("fit_kind", "exposure"), "n_visits": len(ast.get("epochs") or []) or None,
            "parallax": ast.get("parallax"),
            "exposure_fit_crosscheck": ({k: ast["exposure_fit"][k] for k in ("pm_xi_mas_yr", "pm_eta_mas_yr", "sig_xi", "sig_eta", "n_epochs")}
                                        if ast.get("exposure_fit") and ast.get("fit_kind") == "epoch" else None),
            "outcome": out}


def t_graph(s: ToolSession, a: GraphArgs) -> dict:
    g = evidence_graph(s.view, s.target_id)
    out = {"counts": g["counts"], "n_edges": len(g["edges"])}
    if a.focus:
        nb = [e for e in g["edges"] if a.focus in (e["source"], e["target"])]
        if not nb and not any(n["id"] == a.focus for n in g["nodes"]):
            raise ToolError(f"unknown node {a.focus!r}")
        out["focus"] = a.focus
        out["edges"] = nb[:40]
    else:
        out["claims"] = [n for n in g["nodes"] if n["kind"] == "claim"]
    return out


def t_caps(s: ToolSession, _: NoArgs) -> dict:
    from ..capabilities import registry
    reg = registry(s.availability)
    return {"version": reg["version"], "synthetic": s.view.is_synthetic(),
            "capabilities": [{k: c[k] for k in ("id", "name", "methods", "outputs", "limitations", "execution", "available",
                                                  "availability_note")} for c in reg["capabilities"]]}


def t_prov(s: ToolSession, _: NoArgs) -> dict:
    seen, sources = set(), []
    for e in s.view.events:
        for p in e["provenance"]:
            k = (p["source"], p.get("release"), p.get("origin"))
            if k not in seen:
                seen.add(k)
                sources.append({"source": p["source"], "release": p.get("release"), "dataset_id": p.get("dataset_id"),
                                "origin": p.get("origin"), "retrieved_at": p.get("retrieved_at")})
    return {"parameters": s.view.r["parameters"], "software": s.view.r.get("software"),
            "content_hash": s.view.r.get("content_hash"), "data_origins": s.view.data_origins(),
            "synthetic": s.view.is_synthetic(), "sources": sources[:20]}


def t_summary(s: ToolSession, _: NoArgs) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for e in s.view.events:
        counts.setdefault(e["step"], {}).setdefault(e["status"], 0)
        counts[e["step"]][e["status"]] += 1
    pe = s.view.first("pairs")
    pairs = None
    if pe:
        acc = len(pe["data"].get("accepted", []))
        rr = pe["data"].get("rejection_reasons", {})
        pairs = {"accepted": acc, "considered": acc + sum(rr.values()), "rejection_reasons": rr,
                 "rule": pe["data"].get("rule", "WLMATCH-1")}
    return {"target": s.view.r["target"], "synthetic": s.view.is_synthetic(), "data_origins": s.view.data_origins(),
            "wavelength_pairs": pairs,
            "outcomes": [{k: o[k] for k in ("question", "category", "statement", "evidence", "criteria", "limitations")}
                         for o in s.view.outcomes()], "step_status_counts": counts}


def t_validate(s: ToolSession, a: ClaimArgs) -> dict:
    from . import guard
    outs = s.outputs()
    missing = [i for i in a.evidence_ids if i not in outs]
    payload = json.dumps({"answer": a.claim, "claims": [], "limitations": ["(validation request)"]})
    res = guard.check(payload, {i: outs[i] for i in a.evidence_ids if i in outs}, s.executed_names(),
                      s.view.data_origins())
    return {"claim": a.claim, "supported": res.ok and not missing,
            "problems": ([f"evidence id {m} was not produced in this session" for m in missing] + [p["detail"] for p in res.problems])}


TOOLS: dict[str, tuple[type[_Args], Callable[[ToolSession, Any], dict], str]] = {
    "list_target_observations": (ListObsArgs, t_list, "List the target's archive images with inclusion, measurement status and wavelength at the target."),
    "get_observation_metadata": (KeyArgs, t_meta, "Archive metadata, file checksum, provenance and product structure for one observation."),
    "get_wavelength_compatibility": (CompatArgs, t_compat, "Whether two observations can be compared photometrically (rule WLMATCH-2), or the compatible partners of one."),
    "inspect_image_quality": (KeyArgs, t_quality, "Quality flags, fit diagnostics, plate-solution details and rejection reasons for one observation."),
    "get_source_measurements": (OptKeyArgs, t_meas, "Measured centroid, flux, S/N and wavelength for one observation, or a list."),
    "compare_observation_epochs": (PairArgs, t_compare, "Compare two observations: wavelength compatibility, flux difference (only if compatible) and position difference."),
    "get_astrometric_validation": (NoArgs, t_astro, "Fitted proper motion, comparison with the catalogue, registration scatter and the motion outcome."),
    "get_evidence_graph": (GraphArgs, t_graph, "Evidence graph counts and claims, or the edges around one node."),
    "get_analysis_provenance": (NoArgs, t_prov, "Parameters, software versions, content hash, data origins and sources of the investigation."),
    "generate_investigation_summary": (NoArgs, t_summary, "The deterministic outcomes (motion, variability, data quality) with evidence, criteria and limitations."),
    "list_capabilities": (NoArgs, t_caps, "What SKYTRACE can actually do: registered capabilities with methods, outputs, limitations and whether each runs here."),
    "validate_claim_provenance": (ClaimArgs, t_validate, "Check a draft claim against evidence ids from earlier tool calls in this session."),
}


def tool_specs() -> list[dict]:
    """OpenAI-compatible function definitions."""
    return [{"type": "function", "function": {"name": n, "description": d, "parameters": m.model_json_schema()}}
            for n, (m, _, d) in TOOLS.items()]


def call_tool(session: ToolSession, name: str, raw_args: str | dict | None, call_id: str | None = None) -> ToolCall:
    cid = call_id or f"t{len(session.calls) + 1}"
    t0 = time.time()
    try:
        if name not in TOOLS:
            raise ToolError(f"unknown tool {name!r}", "unknown_tool")
        model, fn, _ = TOOLS[name]
        try:
            args = model.model_validate_json(raw_args) if isinstance(raw_args, str) else model.model_validate(raw_args or {})
        except ValidationError as e:
            raise ToolError(f"invalid arguments for {name}: {e.errors(include_url=False)}", "invalid_arguments") from e
        out = fn(session, args)
        text = json.dumps(out, default=str)
        if len(text) > MAX_OUTPUT_CHARS:
            raise ToolError(f"output exceeded {MAX_OUTPUT_CHARS} characters; narrow the request (limit/offset/key)",
                            "output_too_large")
        call = ToolCall(cid, name, args.model_dump(), out, True, time.time() - t0)
    except ToolError as e:
        call = ToolCall(cid, name, raw_args if isinstance(raw_args, dict) else {"raw": str(raw_args)[:300]},
                        {"error": str(e)}, False, time.time() - t0, e.code)
    call.envelope = envelope(session, call)
    session.calls.append(call)
    return call


def envelope(session: ToolSession, call: ToolCall) -> dict:
    """Uniform result wrapper (TOOLS-2). Every field is derived from the record, never from the model."""
    v = session.view
    return {"contract": CONTRACT, "tool": call.name, "call_id": call.id, "ok": call.ok,
            "result": call.output if call.ok else None,
            "error": None if call.ok else {"code": call.error_code, "message": call.output.get("error")},
            "evidence_id": call.id if call.ok else None,
            "data_status": "synthetic" if v.is_synthetic() else "archive",
            "data_origins": sorted(v.data_origins()),
            "record": {"content_hash": v.r.get("content_hash"),
                       "analysis_version": v.r.get("parameters", {}).get("analysis_version")},
            "cache": "none: reads a finished, hashed investigation record; deterministic for the same record"}
