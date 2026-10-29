# Copilot tools and the evidence guard (TOOLS-2, GUARD-3)

Source: `src/skytrace/ai/tools.py`, `src/skytrace/ai/guard.py`, `src/skytrace/ai/copilot.py`.
Tests: `tests/unit/test_tool_contracts.py`, `tests/unit/test_report_ai.py`.

## Contract

All 11 tools are **read-only**: they read one finished, hashed investigation record and its bundle's
discovery index, manifest and inspection data. They never fetch data, write files, run code or
reach the network (`test_tools_have_no_side_effects` checks file modification times; the envelope
test runs with sockets disabled).

Arguments are validated with pydantic: unknown fields are rejected, strings and lists are length-bounded,
observation keys must match `^[A-Za-z0-9_:.\-]+$`.

Every call returns the same envelope to the model:

```json
{"contract": "TOOLS-2", "tool": "...", "call_id": "c3", "ok": true,
 "result": { ... } | null,
 "error": null | {"code": "...", "message": "..."},
 "evidence_id": "c3" | null,
 "data_status": "synthetic" | "archive",
 "data_origins": ["synthetic"] | ["live", "cache"],
 "record": {"content_hash": "...", "analysis_version": "skytrace-analysis/2"},
 "cache": "none: reads a finished, hashed investigation record; deterministic for the same record"}
```

* `evidence_id` is what claims must cite. Failed calls have no evidence id and can never be cited.
* `data_status` comes from the record, not the model, so the model cannot relabel synthetic data.
* Output larger than 14,000 characters is refused (`output_too_large`), never silently cut.

Error codes: `unknown_tool`, `invalid_arguments`, `not_found`, `not_compatible`, `output_too_large`,
`budget_exhausted` (more than 8 tool calls in one answer).

## Tools

| Tool | Arguments (* required; bounds) | Returns (in `result`) |
|---|---|---|
| `list_target_observations` | status ∈ {any, included, excluded, measured_ok, rejected}; detector 1–6; limit 1–50 (20); offset 0–5000 | archive images with inclusion, measurement status/codes, wavelength at target |
| `get_observation_metadata` | key* (3–96 chars) | archive metadata, file SHA-256, provenance, product structure |
| `get_wavelength_compatibility` | key_a*; key_b | WLMATCH decision with `reason_code`, or the compatible partners of one key |
| `inspect_image_quality` | key* | flags, fit diagnostics, plate solution, quality/astrometry codes |
| `get_source_measurements` | key; limit 1–50 (10) | centroid, flux ± error, S/N, wavelength |
| `compare_observation_epochs` | key_a*, key_b* | compatibility; PAIRDIFF-1 flux difference and the logged PAIRDIFF-2 calibration (only if compatible); position difference |
| `get_astrometric_validation` | — | primary fit (epoch or exposure), per-exposure cross-check, catalogue comparison, parallax treatment, registration scatter, motion outcome |
| `get_evidence_graph` | focus (≤ 200 chars) | graph counts and claims, or edges around one node |
| `get_analysis_provenance` | — | parameters, method versions, software, content hash, data origins, sources |
| `generate_investigation_summary` | — | the three ASSESS-2 outcomes with evidence, criteria, limitations; pair rejection codes |
| `validate_claim_provenance` | claim* (3–600 chars); evidence_ids* (1–8) | whether a draft claim passes the guard against the cited outputs |

## Guard (GUARD-3)

The model must reply with a JSON object (`answer`, `claims[]` with `value`, `unit`, `uncertainty`,
`evidence`, plus `limitations`). Every answer is checked before the user sees it; a failing answer
gets one repair round, then is withheld and the deterministic local answer is shown instead, with the
withheld draft and its problems kept in the audit trail.

| Code | Check |
|---|---|
| structure | valid JSON with the required fields |
| citation | each claim cites evidence ids from this session; claim values occur in the cited output |
| number | every number in the answer occurs in the evidence (rounding-aware) |
| date | ISO dates and MJDs occur in the evidence |
| wavelength | µm/nm values match wavelength fields in the evidence |
| identifier | observation keys, archive observation ids and Gaia source ids occur in the evidence *(new)* |
| uncertainty | a measured value in mas/yr, mas, µJy, mJy or % is given with its uncertainty, in the sentence or in the claim *(new)*; bounds, thresholds and catalogue values are exempt |
| tool | tools named in the answer were executed |
| causal | causal statements are hedged or grounded in the evidence's own words |
| attribution | catalogues and missions named occur in the evidence |
| certainty | no unhedged discovery, proof or certainty claims; *discussing* whether something could be a discovery is allowed |
| probability | significances are not presented as probabilities |
| limitations | at least one limitation |
| synthetic | synthetic evidence is called synthetic and never described as real; archive data never called synthetic |

The guard is a filter on stated facts, not a judge of reasoning. It cannot detect a correct number
used in a misleading sentence; that limitation is stated in `docs/AI_USE.md`.

## Live model status

The live Meta Model API test is **blocked** in this environment: `api.meta.ai` is refused by the
egress proxy (HTTP 403 at CONNECT; see `docs/ENVIRONMENT_REPORT.md`). All copilot tests use a
scripted stand-in (`FakeClient` in `tests/unit/test_report_ai.py`) and are labelled as such; no
scripted response is reported as a model response anywhere in this repository.
