# Environment report (Phase 3)

Produced by `python scripts/diagnose_environment.py` → `data/environment_report.json`
(run 2026-10-29T10:47:56Z, Python 3.13.18, Linux x86_64). Every probe is one bounded attempt; no
credentials are printed. Nothing was bypassed: proxy refusals are policy decisions and were not retried
through other routes.

## How failures are distinguished

For each service the script records separately: direct DNS resolution, whether an HTTPS proxy is
configured, the proxy's literal status line for `CONNECT host:443`, the TLS handshake, and the HTTP status
of one small documented request. Verdicts: `dns_failure`, `proxy_refused` (with status line), `tcp_failure`,
`tls_failure`, `timeout`, `http_<status>`, `auth_required`, `malformed_response`, `ok`.

## Results

| Service | Host | Direct DNS | Proxy CONNECT | Verdict |
|---|---|---|---|---|
| IRSA SIA (SPHEREx) | irsa.ipac.caltech.edu | fails | `HTTP/1.1 403 Forbidden` | **proxy_refused** |
| IRSA TAP | irsa.ipac.caltech.edu | fails | 403 | **proxy_refused** |
| SIMBAD TAP | simbad.cds.unistra.fr | fails | 403 | **proxy_refused** |
| Gaia archive TAP | gea.esac.esa.int | fails | 403 | **proxy_refused** |
| Meta Model API | api.meta.ai | fails | 403 | **proxy_refused** |
| PyPI | pypi.org | fails | 403 | **proxy_refused** (see below) |
| PyPI files | files.pythonhosted.org | fails | 403 | **proxy_refused** |
| npm registry | registry.npmjs.org | fails | 403 | **proxy_refused** |
| GitHub | github.com | fails | `200 Connection Established` | reachable (HTTP 400 to the bare probe, as expected) |

Also refused at CONNECT (checked during Phase 3 acquisition attempts): the SPHEREx S3 mirror
(`nasa-irsa-spherex.s3.us-east-1.amazonaws.com`), `registry.opendata.aws`, `storage.googleapis.com`,
`raw.githubusercontent.com`. `codeload.github.com` is reachable (used to fetch the astropy test files
for Gate C, with SHA-256 recorded).

The agent proxy's own status endpoint reports these as
`connect_rejected: gateway answered 403 to CONNECT (policy denial or upstream failure)`.

**Package installation.** `pip download astropy==7.0.1` fails with "No matching distribution". The
cause is specific: `pypi.org` and `files.pythonhosted.org` are listed in `NO_PROXY`, so pip connects
directly, and direct DNS resolution fails in this sandbox ("Name or service not known"). Through the
proxy the same hosts are refused with 403. Both routes are closed, so astropy cannot be installed here;
this is not a missing-package or version problem.

**Meta key.** No `META_API_KEY` / `MODEL_API_KEY` is set in this environment. None was requested in
conversation (by policy).

## Consequences

| Gate | Effect |
|---|---|
| B — real SPHEREx acquisition | blocked: IRSA, SIMBAD and Gaia unreachable |
| C — independent FITS/WCS validation | done with independent astropy test files (via codeload.github.com); comparison against astropy on real SPHEREx files blocked |
| F — live Meta test | blocked: api.meta.ai unreachable and no key |

## To unblock

Either run on a machine with normal internet access (all scripts are written for that; see README
"Getting real SPHEREx data"), or have an organisation admin add these hosts to the account's network
allowlist (claude.ai → Settings → Capabilities):

```
irsa.ipac.caltech.edu
simbad.cds.unistra.fr
gea.esac.esa.int
api.meta.ai
pypi.org
files.pythonhosted.org
nasa-irsa-spherex.s3.us-east-1.amazonaws.com   (optional: bulk SPHEREx downloads)
```

then set `META_API_KEY` in the environment (never in code) and run:

```
python scripts/diagnose_environment.py
pip install "astropy>=7"
python scripts/acquire_targets.py --all && python scripts/build_observation_index.py && python scripts/verify_data_bundle.py
python scripts/verify_provenance.py --all --rerun
python scripts/meta_smoke_test.py
pytest -m live tests/live
```
