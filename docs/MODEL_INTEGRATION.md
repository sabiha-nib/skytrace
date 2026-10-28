# Meta Model API integration

## Documented configuration (dev.meta.ai/docs, read 2026-10-29) — NOT yet verified by a live call

| Item | Value |
|---|---|
| Base URL | `https://api.meta.ai/v1` |
| Auth | `Authorization: Bearer $META_API_KEY` |
| Formats | Chat Completions, Responses, Messages (OpenAI/Anthropic SDK compatible) |
| Chosen model | `muse-spark-1.3` (standard mode): text/image/video/PDF input, tool calling, structured output, 1,048,576-token context; "recommended for new work" |
| Avoided | `*-contributor` models (may use request content to train Meta models); `muse-wonder-1.0` (preview) |
| Unknown | pricing, rate limits, account access, availability in the user's country |

## What the adapter uses
`POST /chat/completions` with `tools` (function schemas from pydantic) and, in the smoke test, `response_format={"type": "json_object"}`. `GET /models` to confirm the model is enabled for the key.

## Smoke test log

| Date | Result | Notes |
|---|---|---|
| 2026-10-29 | not run | development workspace has no route to api.meta.ai and no key is configured |

Run `python scripts/meta_smoke_test.py`; it writes `data/meta_smoke_test.json`. Copy the outcome into this table, including failures.
