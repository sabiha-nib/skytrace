# SKYTRACE — Phase 0 Reconnaissance Report

Date: 2026-10-29 (Asia/Dhaka) · Status: **superseded in part by `PHASE1_IMPLEMENTATION_PLAN.md`** — the project is now built for Meta, so the Space Apps rules, demo-length and pre-event-work items below (§2, K2, K3, decisions 2–3) no longer apply.

Labels used throughout: **[VERIFIED]** checked against an official source today · **[DOC-ONLY]** stated in official docs but not yet exercised by a live call · **[UNVERIFIED]** not yet checked · **[ASSUMPTION]** · **[PROPOSAL]**

---

## 1. Repository and environment audit

| Item | Finding |
|---|---|
| Existing SKYTRACE repo | None in the cloud workspace (`/home/claude` contains only dotfiles; not a git repo). No folder from your Mac is connected to this chat, and no obvious SKYTRACE folder appears in your home directory. **[VERIFIED]** |
| Existing CLAUDE.md / AGENTS.md / skills / tests | None found. Nothing to preserve or conflict with. |
| Python | 3.13.18; numpy 2.5.3, scipy 1.18.1, pydantic 2.13.5 present. astropy, photutils, pyvo, astroquery, fastapi, reproject **missing**. |
| Node | v22.23.4 |
| Network | **Blocking finding.** From this cloud workspace, IRSA (`irsa.ipac.caltech.edu`), the Meta Model API (`api.meta.ai`), PyPI and npm are all unreachable (proxy policy denial / DNS failure). Only GitHub answered. |
| Consequence | This workspace **cannot** install the astronomy stack, fetch a single SPHEREx file, or call a Meta model. Phase 1 (real data + real model call) must run somewhere with open network — realistically **Claude Code on your MacBook (macOS arm64)**. |

## 2. Verified challenge context

| Fact | Status | Source |
|---|---|---|
| Space Apps 2026 hackathon is **Nov 14–15, 2026**; full challenge statements released Oct 28; judging begins Nov 16 | [VERIFIED] (secondary source) | astrobiology.com announcement |
| "Planet X and SPHEREx" is a 2026 challenge | [VERIFIED] (URL exists) | spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ |
| Exact challenge text (targets, WISE 0855 coordinates, "further work" list) | **[UNVERIFIED]** — the official page blocks automated fetching. The spec's description is the only copy I have. | — |
| Demo limits | **2025 guide**: video ≤ **30 seconds** or ≤ 7 slides, English subtitles; exceeding limits = ineligible for Global Judging. 2026 guide not yet confirmed. | Space Apps Project Submission Guide (dated Oct 2025) |
| AI disclosure | 2025 guide: must state AI tools used and how; AI images/video need a visible watermark; no NASA branding in generated content. | same |
| Links | Demo and project links must open without login/permission. | same |
| Judging criteria (2025) | Impact, Creativity, Validity, Relevance, Presentation. | same |
| Prior-work rule | **[UNVERIFIED]** whether building the app *before* Nov 14 is allowed. Your spec's own acceptance criterion requires work "genuinely completed during the relevant challenge period." | — |
| Overlap with existing work | IRSA publishes a "SPHEREx Source Discovery Tool" demo notebook, and several public 2026 repos already target this challenge (e.g. moving-object finders validated against JPL). Originality must come from the method, not the concept. | IRSA tutorials; GitHub |

**Conflict with the spec:** Part XX plans a 3-minute demo. If the 2026 limit is still 30 s, a 3-minute video would make the project ineligible for Global Judging. Plan for a 30-second cut as the primary deliverable.

## 3. Verified SPHEREx data inventory

| Fact | Status |
|---|---|
| **QR3 is the current release** (IRSA began releasing it Sept 2026), DOI `10.26131/IRSA662`. The spec's statement that QR2 is current is **stale**. | [VERIFIED] IRSA QR overview |
| QR2 = DOI `10.26131/IRSA652` (Oct 2025; superseded QR1). QR1 (`10.26131/IRSA629`) retired Feb 2026. QR2 headers corrected April 2026 (PSF extension). | [VERIFIED] |
| Only public product: Level 2 calibrated **Spectral Images**, 0.75–5.0 µm. **No SPHEREx source catalogue yet** (higher-level products planned). | [VERIFIED] |
| SIA2 endpoint `https://irsa.ipac.caltech.edu/SIA`, collections `spherex_qr3`, `spherex_qr3_deep`, `spherex_qr2`, `spherex_qr2_deep`. SIA lags ingestion by ~1 day. | [DOC-ONLY] |
| TAP `https://irsa.ipac.caltech.edu/TAP`, tables `spherex.artifact` ⨝ `spherex.plane`, filter `CONTAINS(POINT('ICRS',ra,dec), p.poly)`, band via `p.energy_bandpassname = 'SPHEREx-D1'…'D6'`, time `p.time_bounds_lower`. | [DOC-ONLY] IRSA cutouts tutorial |
| Cutouts: append `?center=RA,DECd&size=0.1` to an on-prem file URL. Example field returned 84 D2 images; parallel fetch ~0.5 min. | [DOC-ONLY] |
| astroquery: `Irsa.query_sia(pos=(coord, radius), collection='spherex_qr3')` | [DOC-ONLY] |
| File: one MEF **per detector per pointing** (6 per pointing), ~69 MB each, extensions `IMAGE` (MJy/sr, 2040², zodi *not* subtracted), `FLAGS`, `VARIANCE`, `ZODI`, `PSF` (121 zone PSFs, 10× oversampled), `WCS-WAVE`. | [DOC-ONLY] |
| Pixel scale **6.2″** (spec does not state it; one IRSA page's 0.615″ figure refers to the oversampled PSF grid). | [VERIFIED] spherex.caltech.edu instrument page |
| Six bands = six detectors: D1 0.75–1.09 µm (R≈39), D2 1.10–1.62 (41), D3 1.63–2.41 (41), D4 2.42–3.82 (35), D5 3.83–4.41 (112), D6 4.42–5.00 (128). | [DOC-ONLY] |
| Wavelength varies **across each image** (linear variable filter). `WCS-WAVE` gives ~1 nm accuracy "for visualization"; science-grade `CWAVE`/`CBAND` live in a separate Spectral WCS product. | [DOC-ONLY] |
| Flags include `MP_TRANSIENT` (bit 0), `MP_SOURCE` (bit 21), `MP_OVERFLOW`, `MP_NONLINEAR`, `MP_PERSIST`, `MP_HOT`, `MP_COLD`, `MP_OUTLIER`, `MP_MISSING_DATA`, etc. Full table: Explanatory Supplement Table 10. | [DOC-ONLY] |
| Public cloud mirror on AWS (bucket name not yet confirmed). | [DOC-ONLY] |

### The scientific fact that shapes the whole design

Because each detector sits behind a linear variable filter, **a star's measured wavelength depends on where it lands on the detector**. Two exposures of the same star on different dates usually sample *different wavelengths*. A brightness difference between them is therefore mostly spectral shape, not variability. SKYTRACE must compare epochs **only at matched wavelength** (same detector, central wavelength within a stated tolerance, e.g. ≤ ½ channel width), and must say so in the UI. Most naive "blink the two images" tools get this wrong; getting it right is SKYTRACE's strongest credibility point.

### Target feasibility (expected, to be tested — not results)

Proper motions below are approximate catalogue values from memory, **[UNVERIFIED]** until checked against SIMBAD/Gaia. Survey baseline ≈ May 2025 → present (~1.4 yr).

| Target | Expected behaviour | Expected shift at 6.2″/px | Main risk |
|---|---|---|---|
| Barnard's Star | ~10.4″/yr proper motion | ~2.3 px | Bright → possible `MP_OVERFLOW`/`MP_NONLINEAR`; needs sub-pixel centroiding, not visual blink |
| Epsilon Indi B (Ba/Bb, T dwarfs) | ~4.7″/yr | ~1 px | Unresolved binary; near bright Eps Indi A (~400″ away) |
| WISE 0855−0714 | ~8.1″/yr | ~1.8 px | Extremely faint below ~3 µm; may only be detectable in D5–D6, possibly not in single exposures |
| RW Aurigae | Irregular T Tauri variability (multi-band dimming episodes) | — | Needs wavelength-matched pairs; blended companion RW Aur B (~1.4″, unresolved) |
| R Draconis | Mira variable (~245-day period, large amplitude) | — | Very bright in IR → saturation flags likely |

**Validation hook:** fitting Barnard's Star's position vs time and comparing it to Gaia DR3's proper motion is an *external*, quantitative check of the pipeline. That is the single most defensible demo result available.

## 4. Verified Meta Model API inventory

| Fact | Status |
|---|---|
| Product: **Meta Model API**, docs at `dev.meta.ai/docs` (old `llama.developer.meta.com` redirects there; old Llama-API model IDs are stale) | [VERIFIED] |
| Base URL `https://api.meta.ai/v1`, Bearer auth (`MODEL_API_KEY`), OpenAI-compatible: Chat Completions, Responses, Messages formats | [DOC-ONLY] |
| `muse-spark-1.3` — text/image/video/PDF input, tool calling, structured output, 1M context; "recommended for new work" | [DOC-ONLY] |
| `muse-wonder-1.0` — same modalities, **preview** | [DOC-ONLY] |
| `*-contributor` variants are discounted but **may use your content to train Meta models** | [DOC-ONLY] — recommend **not** using |
| Pricing, rate limits, credits, account access, availability in Bangladesh (Geographic Use Policy) | **[UNVERIFIED]** — needs your account |

**Recommended first model: `muse-spark-1.3`** (standard mode) for tool-calling orchestration and explanation, pending a smoke test.

**Smoke-test plan** (run on your Mac, ~2 minutes): (1) `GET /v1/models` — confirm `muse-spark-1.3` is listed for your key; (2) one Chat Completion returning a fixed JSON schema; (3) one tool call with a dummy `get_observation_metadata` tool; (4) one image input (a PNG cutout) — record latency, token usage, cost, and errors in `docs/MODEL_INTEGRATION.md`.

## 5. Smallest scientifically defensible prototype [PROPOSAL]

One vertical slice that touches every Tier A requirement:

1. **Acquire** — TAP query + 0.1° cutouts (D1–D6, all epochs, QR3 with QR2 fallback per target) for Barnard's Star; provenance record per file (collection, DOI, `a.uri`, `time_bounds_lower`, retrieval time, cache status, SHA-256).
2. **Measure** (deterministic, tested) — per cutout: WCS position → pixel; source wavelength from `WCS-WAVE` at that pixel; PSF-weighted centroid and aperture flux with `VARIANCE`-based errors; flag bits in the aperture.
3. **Analyse** — (a) position vs time → fitted proper motion ± error, compared with Gaia DR3; (b) wavelength-matched flux pairs → variability significance; (c) spectrum points (λ, flux, σ, flags, observation ID).
4. **Show** — coordinate input with URL state, epoch timeline, blink / side-by-side / difference at matched wavelength, measured-position overlay, spectrum plot, provenance drawer, cached/live badge.
5. **Explain** — Meta copilot with 3 read-only tools (`get_candidate_evidence`, `get_observation_metadata`, `extract_spectrum`) and a provenance guard that rejects any number not present in tool output.
6. **Offline** — the full slice replays from committed fixtures with `OFFLINE=1`.

Then extend to the other four targets (coverage table first), then Discovery Lab features.

## 6. Architecture [PROPOSAL]

- **Backend:** Python 3.12/3.13, FastAPI, astropy, photutils, astroquery + pyvo, httpx (timeouts/retries), pydantic v2, SQLite for investigations. Deterministic compute in `src/compute/`, no network inside it.
- **Images:** server renders cutouts to PNG with selectable stretch (zscale/asinh, linear) and returns the WCS so the frontend can draw overlays. Raw FITS available for download. No map-tile stack (PMTiles/MapLibre) — unnecessary for 0.1° cutouts.
- **Frontend:** Vite + React + TypeScript; canvas viewer with pan/zoom; a lightweight scientific chart lib for spectra and astrometry. Aladin Lite considered only as an *online-only* context layer (its HiPS backgrounds need network).
- **Agent:** explicit loop, ≤ 6 tool calls, structured output `{claims:[{text, value, unit, evidence_ref}]}`, guard validates every `evidence_ref` and value before display. No code-execution tool.
- **MCP:** defer. A custom FastMCP server adds nothing for the demo that typed in-app tools don't; revisit only if time remains.
- **Not used:** Earthdata, GIBS, FIRMS, POWER, ASF, AppEEARS, SPICE (no astrophysical role here). Gaia DR3 (via astroquery) is the only supplementary catalogue proposed; Horizons only if a solar-system feature is added.

## 7. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| K1 | Cloud workspace has no network → can't build here | Certain | High | Build in Claude Code on your Mac |
| K2 | Pre-hackathon development may breach Space Apps rules | Unknown | **Disqualifying** | Check official rules/local lead before writing app code; if restricted, limit pre-work to research + design |
| K3 | 30-second demo limit vs planned 3-minute demo | Likely | High | 30 s cut is primary; longer version only as optional link if allowed |
| K4 | Bright targets flagged overflow/nonlinear | Likely | Medium | Report flags honestly; fall back to fainter bands or unsaturated companions; never silently use bad pixels |
| K5 | Sub-pixel motions (1–2.3 px) not visible by eye | Likely | Medium | Measure by centroid fit + Gaia comparison; visual blink with marker overlays |
| K6 | WISE 0855 undetected in single exposures | Plausible | Low | Document as a limitation; try D5–D6 stacking per epoch |
| K7 | Comparing different wavelengths mistaken for variability | High if ignored | High (validity) | Wavelength-matched comparison enforced in code and UI |
| K8 | Meta API unavailable/unaffordable for your account or region | Unknown | High (Tier A) | Smoke test first; app degrades gracefully with copilot off |
| K9 | QR3 still partially released for some fields | Plausible | Low | Query both collections per target; label release per file |
| K10 | Originality vs IRSA tool and other teams | Certain overlap | Medium | Differentiate on wavelength-matched evidence, external validation, provenance guard |
| K11 | Scope (spec is very large) vs solo dev, ~2 weeks | Certain | High | Vertical slice first; Tier C deferred explicitly |
| K12 | Fixture size / redistribution | Low | Low | ~0.1° cutouts are small; cite DOIs; confirm IRSA acknowledgement text |

## 8. Test strategy

- **Synthetic (labelled `SYNTHETIC`)**: injected PSF stars with known shift/flux → centroid bias, photometry, difference images, failure modes (misregistration, gradients, overflow, NaNs, normalization).
- **Real integration**: Barnard's Star proper motion vs Gaia DR3 within stated tolerance; WCS round-trip; wavelength lookup vs header.
- **Contract**: provenance present on every API response; offline mode makes zero network calls (socket-blocking test).
- **Agent**: guard rejects fabricated numbers (adversarial fixtures); tool-budget enforcement.
- **Frontend**: URL-state restore, every control wired (Playwright smoke).

## 9. Milestones

| M | Deliverable | Gate |
|---|---|---|
| M0 | Decisions below answered; repo created on your Mac | You approve |
| M1 | Data feasibility notebook: coverage/epoch/band table for all 5 targets (QR3+QR2) | Real query output committed |
| M2 | Meta smoke test recorded | Pass/fail documented |
| M3 | Compute core + synthetic tests + Barnard PM vs Gaia | Tests green; numbers in report |
| M4 | FastAPI + cache + fixtures + `OFFLINE=1` | Socket-blocked test passes |
| M5 | Explore + Time Machine UI | Full slice clickable offline |
| M6 | Spectrum inspector | Real spectrum with flags |
| M7 | Copilot + provenance guard | Adversarial tests pass |
| M8 | Discovery Lab subset (evidence graph, uncertainty explorer, failure lab) | Driven by stored records |
| M9 | Submission assets, public repo, 30 s video | Checklist against official 2026 rules |

## 10. Decisions needed from you

1. **Where to build.** Claude Code on your Mac (recommended). Tell me the folder name, or I can request access to a new folder.
2. **Rules check.** Can you confirm with your local event / the 2026 rules that development before Nov 14 is allowed, and the 2026 demo-length limit?
3. **Challenge text.** Please paste the official Planet X and SPHEREx statement — I couldn't fetch it.
4. **Meta account.** Do you have a Meta Model API key with pay-as-you-go access? OK to avoid `contributor` models?
5. **Release default.** QR3 by default with QR2 fallback — agree?
