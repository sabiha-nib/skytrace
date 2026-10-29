"""Bounded diagnostics: which capabilities this environment actually has.

  python scripts/diagnose_environment.py          # writes data/environment_report.json

For each external service it records, separately: DNS resolution (direct), whether an
HTTPS proxy is configured, the proxy's answer to CONNECT, the TLS handshake, and the
HTTP status of one small documented request. Failures are classified as
dns_failure, proxy_refused (with the proxy's status line), tcp_failure, tls_failure,
timeout, http_<status>, auth_required, malformed_response or ok. Nothing is retried
beyond one attempt per probe; every probe has a 10-20 s timeout. No credentials are
printed (the Meta probe reports only whether a key is set and the HTTP status).
"""

from __future__ import annotations

import base64
import importlib
import json
import os
import platform
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PROBES = [
    ("IRSA SIA (SPHEREx)", "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+127.69444+-39.1776+0.001&RESPONSEFORMAT=votable&MAXREC=1"),
    ("IRSA TAP", "https://irsa.ipac.caltech.edu/TAP/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=SELECT+TOP+1+planeid+FROM+spherex.plane"),
    ("SIMBAD TAP", "https://simbad.cds.unistra.fr/simbad/sim-tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=SELECT+TOP+1+main_id+FROM+basic"),
    ("Gaia archive TAP", "https://gea.esac.esa.int/tap-server/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=SELECT+TOP+1+source_id+FROM+gaiadr3.gaia_source"),
    ("Meta Model API", "https://api.meta.ai/v1/models"),
    ("PyPI (astropy)", "https://pypi.org/simple/astropy/"),
    ("PyPI files", "https://files.pythonhosted.org/"),
    ("npm registry", "https://registry.npmjs.org/"),
    ("GitHub", "https://github.com/"),
]


def proxy_url() -> str | None:
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")


def dns(host: str) -> dict:
    t0 = time.time()
    try:
        addrs = sorted({a[4][0] for a in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
        return {"ok": True, "addresses": addrs[:4], "seconds": round(time.time() - t0, 2)}
    except socket.gaierror as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}", "seconds": round(time.time() - t0, 2)}


def connect_via_proxy(host: str, timeout=12) -> dict:
    """Open a CONNECT tunnel through the configured proxy and report the proxy's status line."""
    p = urlparse(proxy_url())
    t0 = time.time()
    try:
        s = socket.create_connection((p.hostname, p.port or 80), timeout=timeout)
    except OSError as e:
        return {"stage": "proxy_tcp", "ok": False, "error": str(e)}
    try:
        req = f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n"
        if p.username:
            tok = base64.b64encode(f"{p.username}:{p.password or ''}".encode()).decode()
            req += f"Proxy-Authorization: Basic {tok}\r\n"
        s.sendall((req + "\r\n").encode())
        s.settimeout(timeout)
        head = b""
        while b"\r\n\r\n" not in head and len(head) < 8192:
            chunk = s.recv(1024)
            if not chunk:
                break
            head += chunk
        status = head.split(b"\r\n", 1)[0].decode(errors="replace")
        ok = " 200" in status
        out = {"stage": "proxy_connect", "ok": ok, "proxy_status": status, "seconds": round(time.time() - t0, 2)}
        if ok:
            ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE"))
            try:
                with ctx.wrap_socket(s, server_hostname=host) as t:
                    out["tls"] = {"ok": True, "version": t.version()}
            except ssl.SSLError as e:
                out["tls"] = {"ok": False, "error": str(e)}
        return out
    except socket.timeout:
        return {"stage": "proxy_connect", "ok": False, "error": "timeout"}
    finally:
        try:
            s.close()
        except OSError:
            pass


def http(url: str, headers=None, timeout=(10, 20)) -> dict:
    import requests
    t0 = time.time()
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout, stream=True)
        body = r.raw.read(400, decode_content=True) if r.raw else b""
        r.close()
        return {"status": r.status_code, "content_type": r.headers.get("content-type"), "bytes_sampled": len(body),
                "head": body[:120].decode(errors="replace"), "seconds": round(time.time() - t0, 2)}
    except requests.exceptions.ProxyError as e:
        return {"error": "ProxyError", "detail": str(e)[-160:], "seconds": round(time.time() - t0, 2)}
    except requests.exceptions.SSLError as e:
        return {"error": "SSLError", "detail": str(e)[-160:]}
    except requests.exceptions.ConnectTimeout:
        return {"error": "ConnectTimeout"}
    except requests.exceptions.ReadTimeout:
        return {"error": "ReadTimeout"}
    except requests.exceptions.ConnectionError as e:
        return {"error": "ConnectionError", "detail": str(e)[-160:]}


def classify(d: dict, h: dict, c: dict | None) -> str:
    if c is not None and c.get("ok") is False and c.get("proxy_status"):
        return "proxy_refused"
    if c is None and not d["ok"]:
        return "dns_failure"
    if h.get("error") == "SSLError":
        return "tls_failure"
    if h.get("error") in ("ConnectTimeout", "ReadTimeout"):
        return "timeout"
    if h.get("error") == "ProxyError":
        return "proxy_refused"
    if h.get("error") == "ConnectionError":
        return "dns_failure" if not d["ok"] else "tcp_failure"
    st = h.get("status")
    if st in (401, 403) and "api.meta.ai" in h.get("_url", ""):
        return "auth_required"
    if st == 200:
        return "ok"
    return f"http_{st}"


def main() -> int:
    from skytrace.provenance import utc_now_iso
    rep = {"run_at": utc_now_iso(), "python": platform.python_version(), "platform": platform.platform(),
           "proxy_configured": bool(proxy_url()), "offline_flag": os.environ.get("OFFLINE", "0"), "services": [], "packages": {}}
    meta_key = os.environ.get("META_API_KEY") or os.environ.get("MODEL_API_KEY")
    rep["meta_key_configured"] = bool(meta_key)
    for name, url in PROBES:
        host = urlparse(url).hostname
        d = dns(host)
        c = connect_via_proxy(host) if proxy_url() else None
        hdr = {"Authorization": f"Bearer {meta_key}"} if (meta_key and "api.meta.ai" in url) else {}
        h = http(url, hdr)
        h["_url"] = url
        verdict = classify(d, h, c)
        h.pop("_url")
        rep["services"].append({"service": name, "host": host, "url": url, "verdict": verdict, "dns_direct": d,
                                "proxy_connect": c, "http": h})
        print(f"{verdict:<16} {name:<22} dns={'ok' if d['ok'] else 'fail'} "
              f"proxy={(c or {}).get('proxy_status', 'n/a')!s:<45} http={h.get('status', h.get('error'))}")
    for mod in ("astropy", "numpy", "scipy", "starlette", "uvicorn", "playwright", "requests", "pydantic"):
        try:
            m = importlib.import_module(mod)
            rep["packages"][mod] = getattr(m, "__version__", "installed")
        except ImportError:
            rep["packages"][mod] = None
    pip = subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "-d", "/dev/null", "--timeout", "8",
                          "--retries", "0", "astropy==7.0.1"], capture_output=True, text=True, timeout=60)
    rep["pip_download_astropy"] = {"returncode": pip.returncode, "tail": (pip.stdout + pip.stderr).strip().splitlines()[-2:]}
    print("pip download astropy:", "ok" if pip.returncode == 0 else rep["pip_download_astropy"]["tail"][-1][:120])
    out = ROOT / "data" / "environment_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
