"""Bounded, cache-aware HTTP retrieval with honest source labels.

Order of attempts:
  OFFLINE=1 : cache -> fixture -> OfflineError   (no socket is ever opened)
  online    : live -> cache -> fixture -> FetchError

Every result carries a Provenance record. A cached copy keeps the retrieval
time of the original live request and is labelled origin="cache"; it is
never relabelled as live.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlencode

from ..provenance import Provenance, sha256_bytes, stable_hash, utc_now_iso

TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}
MAX_RETRY_AFTER_S = 60.0   # a Retry-After hint is honoured up to this many seconds
DEFAULT_MAX_BYTES = 256 * 1024 * 1024  # bounded downloads; a full SPHEREx MEF is ~70 MB


class OfflineError(RuntimeError):
    """OFFLINE=1 and no cached copy or fixture exists for the request."""


def _proxy_refused(e: Exception) -> bool:
    """True if a requests ProxyError carries the proxy's 403/407 answer to CONNECT."""
    text = repr(e)
    return "ProxyError" in type(e).__name__ + text and ("403" in text or "407" in text)


class FetchError(RuntimeError):
    def __init__(self, url: str, reason: str, attempts: list[str]):
        self.url, self.reason, self.attempts = url, reason, attempts
        super().__init__(f"{reason} for {url}; attempts: {'; '.join(attempts)}")


def offline_enabled() -> bool:
    return os.environ.get("OFFLINE", "0").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FetchResult:
    content: bytes
    provenance: Provenance
    path: Path | None = None   # where the bytes are stored locally


def full_url(url: str, params: Mapping[str, str] | None) -> str:
    if not params:
        return url
    return f"{url}{'&' if '?' in url else '?'}{urlencode(sorted(params.items()))}"


class Fetcher:
    def __init__(self, cache_dir: str | Path, *, offline: bool | None = None,
                 timeout: tuple[float, float] = (10.0, 120.0), retries: int = 3,
                 backoff_s: float = 2.0, max_bytes: int = DEFAULT_MAX_BYTES,
                 session=None, sleep: Callable[[float], None] = time.sleep):
        self.cache_dir = Path(cache_dir)
        self.offline = offline_enabled() if offline is None else offline
        self.timeout, self.retries, self.backoff_s = timeout, retries, backoff_s
        self.max_bytes, self._session, self._sleep = max_bytes, session, sleep

    # -- cache layout: <cache>/<kind>/<release>/<key[:2]>/<key>.{bin,json}
    def _paths(self, kind: str, release: str, key: str) -> tuple[Path, Path]:
        d = self.cache_dir / kind / (release or "unversioned") / key[:2]
        return d / f"{key}.bin", d / f"{key}.json"

    def read_cache(self, kind: str, release: str, url: str) -> FetchResult | None:
        key = stable_hash(url)
        data_p, meta_p = self._paths(kind, release, key)
        if not (data_p.exists() and meta_p.exists()):
            return None
        content = data_p.read_bytes()
        prov = Provenance.from_dict(json.loads(meta_p.read_text()))
        if prov.content_sha256 and prov.content_sha256 != sha256_bytes(content):
            return None  # corrupted entry: treat as absent rather than serve it
        return FetchResult(content, prov.with_origin("cache"), data_p)

    def _write_cache(self, kind: str, release: str, url: str, content: bytes, prov: Provenance) -> Path:
        key = stable_hash(url)
        data_p, meta_p = self._paths(kind, release, key)
        data_p.parent.mkdir(parents=True, exist_ok=True)
        for p, blob in ((data_p, content), (meta_p, json.dumps(prov.to_dict(), indent=2).encode())):
            tmp = p.with_suffix(p.suffix + ".part")
            tmp.write_bytes(blob)
            os.replace(tmp, p)  # atomic on POSIX
        return data_p

    def _live(self, url: str) -> bytes:
        session = self._session
        if session is None:
            import requests  # imported lazily so offline runs never load the HTTP stack
            session = self._session = requests.Session()
        resp = session.get(url, timeout=self.timeout, stream=True)
        try:
            if resp.status_code != 200:
                ra = None
                try:
                    ra = float((getattr(resp, "headers", None) or {}).get("Retry-After"))
                except (TypeError, ValueError):
                    ra = None          # absent, or an HTTP date (not parsed): fall back to exponential back-off
                raise _HTTPStatus(resp.status_code, ra)
            chunks, total = [], 0
            for chunk in resp.iter_content(chunk_size=1 << 16):
                total += len(chunk)
                if total > self.max_bytes:
                    raise FetchError(url, f"response exceeds {self.max_bytes} bytes", [])
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            resp.close()

    def get(self, url: str, params: Mapping[str, str] | None = None, *, source: str,
            kind: str = "metadata", release: str = "", dataset_id: str = "",
            validate: Callable[[bytes], None] | None = None,
            fixture: str | Path | None = None, use_cache: bool = True) -> FetchResult:
        url = full_url(url, params)
        attempts: list[str] = []

        if not self.offline:
            for i in range(self.retries):
                delay = self.backoff_s * (2 ** i)
                try:
                    content = self._live(url)
                    if validate:
                        validate(content)
                    prov = Provenance(source=source, source_url=url, retrieved_at=utc_now_iso(),
                                      origin="live", dataset_id=dataset_id, release=release,
                                      content_sha256=sha256_bytes(content))
                    path = self._write_cache(kind, release, url, content, prov)
                    return FetchResult(content, prov, path)
                except _HTTPStatus as e:
                    attempts.append(f"live#{i + 1}: HTTP {e.status}" + (f" (Retry-After {e.retry_after:g} s)" if e.retry_after is not None else ""))
                    if e.status not in TRANSIENT_STATUS:
                        break
                    if e.retry_after is not None and e.retry_after >= 0:
                        delay = min(MAX_RETRY_AFTER_S, e.retry_after)   # honour the server's rate-limit hint, bounded
                except FetchError as e:
                    attempts.append(f"live#{i + 1}: {e.reason}")
                    break
                except ValueError as e:  # failed validation: not retryable
                    attempts.append(f"live#{i + 1}: invalid response ({e})")
                    break
                except Exception as e:  # connection errors, timeouts
                    if _proxy_refused(e):   # policy denial by the egress proxy: never retried or routed around
                        attempts.append(f"live#{i + 1}: proxy_refused (proxy answered 403 to CONNECT; host not allowed)")
                        break
                    attempts.append(f"live#{i + 1}: {type(e).__name__}: {_short(e)}")
                if i + 1 < self.retries:
                    self._sleep(delay)
        else:
            attempts.append("live: skipped (OFFLINE=1)")

        if use_cache:
            cached = self.read_cache(kind, release, url)
            if cached:
                note = "served from cache after live failure: " + "; ".join(attempts) if not self.offline else "served from cache (OFFLINE=1)"
                return FetchResult(cached.content, _note(cached.provenance, note), cached.path)
            attempts.append("cache: miss")

        if fixture is not None:
            fp = Path(fixture)
            meta_p = fp.with_suffix(fp.suffix + ".provenance.json")
            if fp.exists() and meta_p.exists():
                prov = Provenance.from_dict(json.loads(meta_p.read_text())).with_origin("fixture")
                return FetchResult(fp.read_bytes(), prov, fp)
            attempts.append(f"fixture: missing {fp.name} or its provenance sidecar")

        if self.offline:
            raise OfflineError(f"OFFLINE=1 and no cached copy or fixture for {url} ({'; '.join(attempts)})")
        raise FetchError(url, "data unavailable", attempts)


class _HTTPStatus(Exception):
    def __init__(self, status: int, retry_after: float | None = None):
        self.status, self.retry_after = status, retry_after


def _note(p: Provenance, note: str) -> Provenance:
    d = p.to_dict()
    d["notes"] = (d.get("notes", "") + " | " if d.get("notes") else "") + note
    return Provenance.from_dict(d)


def _short(e: Exception, n: int = 160) -> str:
    """Compact error text: the URL is already in FetchError, so drop repeated URL noise."""
    msg = str(e)
    if "Caused by" in msg:
        msg = msg[msg.index("Caused by"):]
    return msg[:n]
