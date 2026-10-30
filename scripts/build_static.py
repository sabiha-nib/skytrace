"""Build the static, previewable copy of Skytrace (no server needed to view it).

    python scripts/build_static.py            # writes dist/preview/ (index.html, css/, js/, data/)
    python scripts/build_static.py --web-only # re-copy the interface files only, keeping the recorded data
    python -m http.server -d dist/preview 8700   # then open http://127.0.0.1:8700/

How it works: the real server is started (OFFLINE=1) and every response the interface needs for the bundled
targets is requested from it and saved verbatim: target lists, observation images, investigation records for the
default parameters and for each STAB-1 perturbation, evidence graphs, reports, the stability check and the local
assistant's answer for every question intent. The interface code is copied unchanged; `api.js` switches to the
static backend because index.html carries <meta name="skytrace-mode" content="static">. Nothing is computed by
this script itself, and nothing that needs the server is imitated in the preview (see web/js/static/backend.js).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skytrace import __version__, stability  # noqa: E402
from skytrace.ai.local import _intent  # noqa: E402

OUT = ROOT / "dist" / "preview"
NOPROXY = {"http": None, "https": None}
QUESTIONS = {   # one canonical question per local-assistant intent; the answer depends only on the intent
    "capabilities": "What can you do with this investigation?",
    "alignment": "Could the apparent motion be caused by alignment errors?",
    "compat": "Which observations are wavelength-compatible?",
    "excluded": "Why was an observation excluded?",
    "gaia": "How does the result compare with the Gaia reference?",
    "uncertainty": "What is the largest remaining uncertainty?",
    "next": "What should I investigate next?",
    "support": "Which observations support the outcome?",
    "changed": "What changed?",
    "summary": "Summarise this investigation.",
    "draft": "Draft a notebook note for this investigation.",
    "plan": "How would I test whether the source changed in brightness?",
    "quality": "Are there any data quality problems?",
    "missing": "Which evidence is still missing?",
    "hypotheses": "Which explanations remain viable?",
}


EXPERIMENTS = [{"template": "sensitivity"}, {"template": "reproducibility"}, {"template": "method_comparison"},
               {"template": "negative_control", "question": "variability"}, {"template": "negative_control", "question": "motion"},
               {"template": "robustness"}]


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def fname(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", key)


def write(rel: str, content) -> None:
    p = OUT / "data" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        p.write_text(json.dumps(content, separators=(",", ":")))
    else:
        p.write_text(content)


BROWSER_PORTS = {"wavelength_match", "registration"}     # web/js/static/compare.js and register.js, parity-tested


def preview_caps(reg: dict) -> dict:
    """The registry as the static preview sees it: server-side capabilities only have their precomputed results here.
    (The reproducibility package keeps the build server's registry: it describes the environment that produced it.)"""
    out = []
    for c in reg["capabilities"]:
        if c["execution"] == "server":
            c = {**c, "available": False, "availability_note": "needs the running Skytrace server; this static preview has its "
                 "precomputed results for the default parameters and the five stability perturbations only"}
        elif c["execution"] == "local":
            c = {**c, "availability_note": "computed in this browser by a parity-tested JavaScript port" if c["id"] in BROWSER_PORTS
                 else "precomputed by the Python pipeline when this preview was built (no re-execution in the browser)"}
        out.append(c)
    return {**reg, "capabilities": out, "preview": True}


def copy_web() -> None:
    for sub in ("css", "js"):
        if (OUT / sub).exists():
            shutil.rmtree(OUT / sub)
        shutil.copytree(ROOT / "web" / sub, OUT / sub)
    html = (ROOT / "web" / "index.html").read_text()
    html = html.replace('href="/static/css/app.css"', 'href="css/app.css"').replace('src="/static/js/main.js"', 'src="js/main.js"')
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n  <meta name="skytrace-mode" content="static">', 1)
    (OUT / "index.html").write_text(html)
    # artifact.html: the same page as body content, for hosts that wrap the page in their own document skeleton
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    keep = sorted((ln for ln in head.splitlines() if re.search(r"<title>|skytrace-mode|name=\"description\"|rel=\"stylesheet\"", ln)),
                  key=lambda ln: "<title>" not in ln)      # the host reads the <title> from the top of the file
    (OUT / "artifact.html").write_text("\n".join(ln.strip() for ln in keep) + "\n" + body.strip() + "\n")


def main() -> int:
    for intent, q in QUESTIONS.items():
        assert _intent(q) == intent, (intent, q)
    if "--web-only" in sys.argv:
        if not (OUT / "data").exists():
            print("no recorded data yet; run without --web-only first")
            return 1
        copy_web()
        st = json.loads((OUT / "data" / "status.json").read_text())
        write_manifest(st.get("commit", ""), st.get("built_at", ""))
        print(f"re-copied the interface into {OUT.relative_to(ROOT)} (data unchanged)")
        return 0
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy_web()
    port = free_port()
    rec_dir = tempfile.mkdtemp(prefix="skytrace-build-records-")
    env = {**os.environ, "OFFLINE": "1", "SKYTRACE_RECORDS_DIR": rec_dir, "SKYTRACE_SESSIONS_DIR": rec_dir + "/sessions",
           "META_API_KEY": "", "MODEL_API_KEY": ""}
    proc = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--port", str(port)], env=env, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                requests.get(base + "/api/status", timeout=1, proxies=NOPROXY)
                break
            except requests.RequestException:
                time.sleep(0.25)
        get = lambda path: requests.get(base + path, timeout=120, proxies=NOPROXY)
        post = lambda path, body: requests.post(base + path, json=body, timeout=600, proxies=NOPROXY)

        def ok(r):
            r.raise_for_status()
            return r

        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        status = ok(get("/api/status")).json()
        status.update({"static": True, "offline": True, "built_at": status["time"], "commit": commit,
                       "meta": {"configured": False, "key_present": False, "model": status["meta"]["model"], "smoke_test": None},
                       "static_note": "Static preview: every response was produced by the Skytrace server at build time; "
                                      "no server, archive or model is contacted while viewing."})
        write("status.json", status)
        targets = ok(get("/api/targets")).json()
        write("targets.json", targets)
        write("capabilities.json", preview_caps(ok(get("/api/capabilities")).json()))
        write("specs.json", ok(get("/api/specs")).json())
        con = ok(get("/api/connectors")).json()
        con["preview_note"] = "static preview: request previews and acquisition need the full application; verdicts are from the last environment diagnosis"
        write("connectors.json", con)

        n_files = 0
        for t in targets["targets"]:
            tid = t["target_id"]
            if not t.get("kind"):
                continue                      # challenge targets without data: the app shows their no-data state
            detail = ok(get(f"/api/targets/{tid}")).json()
            write(f"t/{tid}/target.json", detail)
            images = {}
            for o in detail["observations"]:
                if o.get("file"):
                    images[o["key"]] = ok(get(f"/api/targets/{tid}/observations/{o['key']}/image")).json()
                    n_files += 1
            write(f"t/{tid}/images.json", images)      # one file per target keeps the hosted preview under its file limit
            runs = []
            for label, params in [("Default parameters", {})] + stability.perturbations({}):
                s = ok(post(f"/api/targets/{tid}/analyze", {"params": params})).json()
                iid = s["investigation_id"]
                rec_text = ok(get(f"/api/investigations/{iid}/record.json")).text
                write(f"t/{tid}/run/{iid}/record.json", rec_text)
                write(f"t/{tid}/run/{iid}/meta.json", {k: v for k, v in s.items() if k != "record"})
                write(f"t/{tid}/run/{iid}/graph.json", ok(get(f"/api/investigations/{iid}/graph")).json())
                write(f"t/{tid}/run/{iid}/report.md", ok(get(f"/api/investigations/{iid}/report.md")).text)
                write(f"t/{tid}/run/{iid}/research.json", ok(get(f"/api/investigations/{iid}/research")).json())
                disc = ok(get(f"/api/investigations/{iid}/discovery")).json()
                disc["capabilities"] = preview_caps(disc["capabilities"])
                write(f"t/{tid}/run/{iid}/discovery.json", disc)
                pkg = ok(get(f"/api/investigations/{iid}/package.zip")).content   # hosts serve no .zip: carried as base64 JSON
                write(f"t/{tid}/run/{iid}/package.json", {"method": "PKG-1", "bytes": len(pkg), "sha256": hashlib.sha256(pkg).hexdigest(),
                                                          "base64": base64.b64encode(pkg).decode()})
                write(f"t/{tid}/run/{iid}/ask.json", {intent: {**ok(post(f"/api/investigations/{iid}/ask", {"question": q})).json(), "recorded_question": q}
                                                      for intent, q in QUESTIONS.items()})
                runs.append({"iid": iid, "label": label, "params": params, "default": not params,
                             "content_hash": s["record"]["content_hash"]})
                print(f"  {tid}: {label} -> {iid}")
            write(f"t/{tid}/runs.json", runs)
            write(f"t/{tid}/stability.json", ok(post(f"/api/targets/{tid}/stability", {"params": {}})).json())
            exps = {}
            for cfg in EXPERIMENTS:                     # the standard experiments, executed by the server at build time
                key = cfg["template"] + (f":{cfg['question']}" if "question" in cfg else "")
                exps[key] = ok(post("/api/experiments", {"target_id": tid, **cfg})).json()
                print(f"  {tid}: experiment {key} -> {exps[key]['evaluation'].get('passed')}")
            write(f"t/{tid}/experiments.json", exps)
    finally:
        proc.terminate()
        proc.wait(10)
        shutil.rmtree(rec_dir, ignore_errors=True)

    manifest = write_manifest(commit, status["built_at"])
    total = sum(f["bytes"] for f in manifest["files"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(manifest['files'])} files, {total / 1e6:.1f} MB ({n_files} observation images)")
    return 0


def write_manifest(data_commit: str, built_at: str) -> dict:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "PREVIEW_MANIFEST.json")
    manifest = {"skytrace": __version__, "data_commit": data_commit, "interface_commit": head, "data_built_at": built_at,
                "mode": "static preview",
                "data": "synthetic bundles only (fixtures/synthetic); no real archive data exists in this build",
                "files": [{"path": str(p.relative_to(OUT)), "bytes": p.stat().st_size,
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (OUT / "PREVIEW_MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
