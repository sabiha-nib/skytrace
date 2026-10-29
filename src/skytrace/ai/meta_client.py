"""Narrow adapter for the Meta Model API (OpenAI-compatible Chat Completions).

Documented at dev.meta.ai/docs (re-checked 2026-10-29): POST /v1/chat/completions
("the OpenAI-compatible messages-array endpoint") at https://api.meta.ai/v1,
Authorization: Bearer <key> (the docs name the variable MODEL_API_KEY; META_API_KEY
is also accepted here), OpenAI-style error envelope {"error": {"message", "type",
"param", "code"}}, per-team rate limits. Model muse-spark-1.3: tool calling and
structured output. None of this has been exercised by a live call from this
repository yet; scripts/meta_smoke_test.py does that and records the result.

Contributor-mode models ("*-contributor") may use request content to train
Meta models; this adapter refuses them unless explicitly allowed.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass


class MetaUnavailable(RuntimeError):
    """No key configured, offline mode, or the API could not be reached."""


class MetaAPIError(RuntimeError):
    def __init__(self, status: int, body: str):
        self.status, self.body = status, body[:2000]
        self.type = self.code = None
        msg = self.body
        try:
            err = json.loads(body).get("error", {})
            self.type, self.code = err.get("type"), err.get("code")
            msg = f"{err.get('type')}: {err.get('message')}"
        except (ValueError, AttributeError):
            pass
        super().__init__(f"Meta API HTTP {status}: {msg}")


@dataclass(frozen=True)
class MetaConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 60.0
    allow_contributor: bool = False

    @classmethod
    def from_env(cls) -> "MetaConfig":
        return cls(os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/"),
                   os.environ.get("META_API_KEY") or os.environ.get("MODEL_API_KEY", ""),
                   os.environ.get("META_MODEL", "muse-spark-1.3"),
                   float(os.environ.get("META_TIMEOUT_S", "60")))


class MetaClient:
    def __init__(self, cfg: MetaConfig | None = None, session=None, sleep=time.sleep):
        self.cfg = cfg or MetaConfig.from_env()
        self._session, self._sleep = session, sleep
        if os.environ.get("OFFLINE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            raise MetaUnavailable("OFFLINE=1: model calls disabled")
        if not self.cfg.api_key:
            raise MetaUnavailable("no API key configured (set META_API_KEY or MODEL_API_KEY)")
        if self.cfg.model.endswith("-contributor") and not self.cfg.allow_contributor:
            raise MetaUnavailable("contributor-mode models may train on request content; not allowed by default")

    def _post(self, path: str, payload: dict) -> dict:
        if self._session is None:
            import requests
            self._session = requests.Session()
        url = f"{self.cfg.base_url}/{path.lstrip('/')}"
        last = None
        for attempt in range(3):
            try:
                r = self._session.post(url, json=payload, timeout=self.cfg.timeout_s,
                                       headers={"Authorization": f"Bearer {self.cfg.api_key}",
                                                "Content-Type": "application/json"})
            except Exception as e:  # connection error / timeout
                last = MetaUnavailable(f"{type(e).__name__}: {str(e)[:200]}")
                if attempt < 2:
                    self._sleep(1.5 * (2 ** attempt))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = MetaAPIError(r.status_code, r.text)
                try:
                    wait = min(20.0, float(r.headers.get("Retry-After", "")))
                except (TypeError, ValueError):
                    wait = 1.5 * (2 ** attempt)
                if attempt < 2:
                    self._sleep(wait)
                continue
            if r.status_code != 200:
                raise MetaAPIError(r.status_code, r.text)
            try:
                return r.json()
            except ValueError as e:
                raise MetaAPIError(r.status_code, f"non-JSON body: {r.text[:200]}") from e
        raise last  # type: ignore[misc]

    def list_models(self) -> list[str]:
        if self._session is None:
            import requests
            self._session = requests.Session()
        r = self._session.get(f"{self.cfg.base_url}/models", timeout=self.cfg.timeout_s,
                              headers={"Authorization": f"Bearer {self.cfg.api_key}"})
        if r.status_code != 200:
            raise MetaAPIError(r.status_code, r.text)
        return [m.get("id") for m in r.json().get("data", [])]

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             response_format: dict | None = None, temperature: float = 0.0) -> dict:
        """One Chat Completions call. Returns the first choice's message dict plus usage."""
        payload: dict = {"model": self.cfg.model, "messages": messages, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        data = self._post("chat/completions", payload)
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise MetaAPIError(200, f"unexpected response shape: {json.dumps(data)[:500]}") from e
        return {"message": msg, "usage": data.get("usage"), "model": data.get("model"), "id": data.get("id"),
                "finish_reason": choice.get("finish_reason")}
