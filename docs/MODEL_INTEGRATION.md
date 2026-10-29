# Meta Model API integration

## Configuration as documented (dev.meta.ai/docs, read 2026-10-29), not yet confirmed by a live call

| Item | Value | Source |
|---|---|---|
| Endpoint | `POST https://api.meta.ai/v1/chat/completions` ("the OpenAI-compatible messages-array endpoint") | API reference overview |
| Auth | `Authorization: Bearer <key>`; the docs name the variable `MODEL_API_KEY` (Skytrace also accepts `META_API_KEY`) | API reference overview |
| Errors | `{"error": {"message", "type", "param", "code"}}` | API reference overview |
| Rate limits | per team; values on the pricing page (not read) | API reference overview |
| Model | `muse-spark-1.3`, standard mode: text/image/video/PDF input, tool calling, structured output, 1,048,576-token context, "recommended for new work" | Models page |
| Refused by default | `*-contributor` models (may use request content to train Meta models) | Models page |
| Not checked | exact request fields beyond the OpenAI-compatible core, `max_tokens` naming, reasoning-effort options, rate-limit headers, data-retention policy | the detailed schema pages were not read |

## How Skytrace uses it

- **Adapter** (`src/skytrace/ai/meta_client.py`): configuration from the environment, 60 s timeout, up to 3 attempts for connection errors and 429/5xx (honouring `Retry-After`, capped at 20 s), parsing of the error envelope, `finish_reason` recorded. `OFFLINE=1` or a missing key raise `MetaUnavailable` before any request.
- **Loop** (`src/skytrace/ai/copilot.py`): system rules + a compact context (target, synthetic flag, data origins, outcome categories) + 11 tool schemas. At most 8 tool calls, 10 model rounds and 150 s. Each tool call is validated, executed and recorded.
- **What the model sees:** only tool outputs, which are summaries of logged measurements, never FITS files or pixel arrays. Outputs are capped at 14,000 characters each.
- **Guard** (`src/skytrace/ai/guard.py`, GUARD-2): see [ARCHITECTURE.md](ARCHITECTURE.md). Failing answers get one repair round. After a second failure the draft is withheld (kept in the audit record) and the local assistant's grounded answer is shown with the reasons.
- **Honest labelling:** the response's `mode` is `meta` only if a Meta model produced the shown answer. The interface shows "Meta muse-spark-1.3 · checked by the evidence guard" or "Local assistant · no language model".
- **Secrets:** the key is read from the environment on the server. It is not sent to the browser, not logged, not stored in records, and `scripts/verify.py` scans tracked files for keys.

## Smoke test

```bash
export META_API_KEY=...      # or put it in .env
python scripts/meta_smoke_test.py
```

The test runs: list models → plain completion → JSON-object response → one tool call. It writes `data/meta_smoke_test.json`, and the app's header shows whether it passed.

| Date | Result | Notes |
|---|---|---|
| 2026-10-29 | not run | no route from the build environment to api.meta.ai (proxy `connect_rejected`) and no key configured |

## What is verified without the API

`tests/unit/test_report_ai.py` drives the full loop with a scripted client. The loop calls tools and a grounded answer passes. An answer with an invented number is withheld twice and replaced. The tool budget is enforced. A 429 error falls back to the local assistant. Contributor models and offline mode are refused. The error envelope is parsed.
