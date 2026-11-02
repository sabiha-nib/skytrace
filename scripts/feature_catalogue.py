"""Feature catalogue: every concept considered for Skytrace, its status, scores, tier, dependencies and verification.

    python scripts/feature_catalogue.py          # writes docs/feature_catalogue.json and docs/FEATURE_CATALOGUE.md

Counts in the Markdown are computed from the data below, never typed. tests/unit/test_feature_catalogue.py checks that
the catalogue is well formed, that every cited verification file exists, and that every concept marked as implemented
cites a verification.

Status   E = existing before 0.5 · N = new in 0.5 · P = deferred (planned, not built) · X = out of scope (not advisable or
         not possible with this data/environment).
Scores   1–5 on seven dimensions, in this order:
         S scientific value · U user value · D differentiation · F feasibility now · R data readiness (are the needed data
         available here) · V verifiability (can it be tested deterministically) · K integrity safety (5 = little risk of
         misleading a user).
Tier     computed from the scores. value = mean(S, U, D); practicality = mean(F, R, V, K).
         A: value ≥ 4 and practicality ≥ 4 · B: value ≥ 3 and practicality ≥ 3.5 · C: value ≥ 2.5 · D: otherwise, and always
         for out-of-scope concepts. A tier is a priority signal, not a claim that something is built: see the status.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ["scientific value", "user value", "differentiation", "feasibility now", "data readiness", "verifiability",
              "integrity safety"]
STATUS = {"E": "existing (≤ 0.4)", "N": "new in 0.5", "P": "deferred", "X": "out of scope"}

T_API, T_E2E, T_DISC, T_STAT = "tests/integration/test_api.py", "tests/e2e/test_controls.py", "tests/unit/test_discovery.py", "tests/unit/test_static_preview.py"
T_MEAS, T_ASSESS, T_AI, T_TOOLS = "tests/unit/test_measurement.py", "tests/unit/test_assess2.py", "tests/unit/test_report_ai.py", "tests/unit/test_tool_contracts.py"
T_ROB, T_CAL, T_WL, T_FITS = "tests/robustness/test_robustness.py", "tests/unit/test_calibration_v2.py", "tests/unit/test_wavelength_flags.py", "tests/unit/test_fits_wcs.py"
T_ACQ, T_ARCH, T_PROV, T_OFF = "tests/unit/test_acquire.py", "tests/unit/test_archive.py", "tests/unit/test_provenance_check.py", "tests/unit/test_offline_workflow.py"
T_EPH, T_COORD, T_LIVE, T_APP = "tests/unit/test_ephemeris.py", "tests/unit/test_coords.py", "tests/live/test_live_archive.py", "tests/e2e/test_app.py"
T_FC = "tests/unit/test_feature_catalogue.py"

# (concept, status, scores "SUDFRVK", dependencies, verification)
C = {
 "Data acquisition and archives": [
  ("SPHEREx QR3 spectral images via documented IRSA interfaces (QR2 fallback, never QR1)", "E", "5545155", "network access to IRSA", T_ACQ),
  ("SIMBAD target resolution with stored response", "E", "3433255", "network", T_ACQ),
  ("Gaia DR3 reference stars and target astrometry", "E", "5435155", "network", T_ACQ),
  ("Environment diagnosis of every external service (verdict per service)", "E", "3445555", "none", "scripts/diagnose_environment.py"),
  ("Acquisition retries with bounded back-off and a cache", "E", "2324244", "network", T_ACQ),
  ("Live acquisition of the five challenge targets", "P", "5545144", "network access to IRSA, SIMBAD, Gaia (blocked here)", T_LIVE),
  ("Cutout service instead of full Level-2 images", "P", "3434143", "documented IRSA cutout endpoint; network", "—"),
  ("Background prefetch of neighbouring epochs", "P", "2323133", "network; storage budget", "—"),
  ("Automatic acquisition of new data releases", "P", "3423133", "release announcements; network", "—"),
  ("Scraping undocumented archive pages", "X", "1111111", "—", "—"),
 ],
 "Data bundles and provenance": [
  ("Verified data bundles with manifest and SHA-256 per file", "E", "4435555", "none", T_ARCH),
  ("Source-label contract (archive, cache, synthetic) on every record", "E", "4445555", "none", T_PROV),
  ("Synthetic fixtures with known injected answers, labelled SYNTHETIC", "E", "4445555", "none", "tests/synthetic.py"),
  ("Provenance check PROVCHECK-1 (hashes, origins, codes, re-run determinism)", "E", "4445555", "server", T_PROV),
  ("Bundle verification script", "E", "3435555", "none", "scripts/verify_data_bundle.py"),
  ("Evidence inventory per investigation (DISC-1 stage A)", "N", "4545555", "record, bundle manifest", T_DISC),
  ("Unknown fields left empty and counted, never guessed", "N", "4445555", "none", T_DISC),
  ("Dataset DOI and release on every observation", "E", "3435455", "archive metadata", T_ACQ),
  ("Signed bundles (cryptographic signature of the manifest)", "P", "2324143", "key management", "—"),
  ("Bundle diff between two acquisitions", "P", "3334344", "two bundles of one target", "—"),
 ],
 "Image access, FITS and WCS": [
  ("Native FITS reader with validated header parsing", "E", "3435555", "none", T_FITS),
  ("Gnomonic WCS with SIP distortion, validated against the reference implementation", "E", "4435455", "astropy for the external check (not installed here)", "tests/unit/test_fits_wcs_external.py"),
  ("Spectral WCS: wavelength at any pixel from the LVF solution", "E", "5545455", "Level-2 spectral WCS", T_WL),
  ("Flag-bit policy applied before measurement (FLAGPOL-1)", "E", "4435555", "none", T_WL),
  ("Image stamps served at native resolution with no resampling", "E", "3435555", "none", T_API),
  ("Variance plane propagated into photometric errors", "E", "4435555", "none", T_MEAS),
  ("PSF model per detector position from the archive PSF cubes", "P", "4432134", "PSF products; network", "—"),
  ("Zodiacal-light model subtraction", "P", "3322133", "external model; validation data", "—"),
  ("Full-frame mosaic of all epochs", "P", "2333143", "network; storage", "—"),
  ("Deep co-added image per detector", "P", "3332143", "registration of many epochs", "—"),
 ],
 "Sky Explorer": [
  ("Image viewer with stretch, black and white points, zoom and pan", "E", "2435555", "none", T_E2E),
  ("Overlays: catalogue position, centroid, reference stars, rejected pixels", "E", "4535555", "measurement records", T_E2E),
  ("Observation table with detector and status filters", "E", "2435555", "none", T_E2E),
  ("Keyboard stepping between observations", "E", "1424555", "none", T_E2E),
  ("Pixel read-out with value and approximate sky coordinates (linearised WCS)", "E", "3435555", "WCS", T_APP),
  ("Per-observation provenance panel (file, checksum, DOI)", "E", "4435555", "bundle", T_E2E),
  ("Command-palette jump to any observation", "N", "1324555", "palette", T_E2E),
  ("All-sky context map of where the target lies", "P", "1333244", "sky survey tiles (external)", "—"),
  ("Colour composite from several detectors", "X", "1221223", "mixing wavelengths misleads brightness comparison", "—"),
  ("AI-enhanced (super-resolved) images", "X", "1111511", "fabricates detail", "—"),
 ],
 "Time Machine": [
  ("Blink, fade, side-by-side and difference views of two epochs", "E", "3535555", "registration", T_E2E),
  ("Wavelength-compatibility banner per pair (WLMATCH-2)", "E", "5545555", "spectral WCS", T_E2E),
  ("Partner list with the reason each pair is not comparable", "E", "4535555", "WLMATCH-2", T_E2E),
  ("Plate-solution registration onto a common grid", "E", "4435455", "reference stars", T_STAT),
  ("Registration diagnostics: per-plate scale, rotation, residuals; relative rotation, scale and shift (REGDIAG-1)", "N", "4445555", "plate solutions", T_DISC),
  ("Pair comparison computed in the browser by a parity-tested port", "E", "3445555", "record", T_STAT),
  ("Same display scale toggle for honest visual comparison", "E", "3435555", "none", T_E2E),
  ("Ask the copilot about a specific pair", "E", "3434455", "server copilot", T_E2E),
  ("Animated multi-epoch sequence (more than two epochs)", "P", "2433444", "registration of all epochs", "—"),
  ("Motion vector overlay from the fitted proper motion", "P", "3434455", "motion fit", "—"),
  ("Interpolated in-between frames", "X", "1221112", "invents observations", "—"),
 ],
 "Wavelength and spectral analysis": [
  ("Wavelength ruler: every observation by wavelength and time (signature view)", "E", "4545555", "spectral WCS", T_APP),
  ("Wavelength-matched pairing with logged rejections (WLMATCH-2)", "E", "5545555", "spectral WCS", T_WL),
  ("Per-target spectrum from all included measurements", "E", "4435455", "photometry", T_APP),
  ("Narrow-band masking near spectral features (NBMASK-1)", "E", "3335455", "line list", T_WL),
  ("Spectral slope test across adjacent channels for wavelength-tolerance effects", "P", "4433244", "matched-channel photometry", "—"),
  ("Spectral template comparison (stellar types)", "P", "3332233", "template library; validation", "—"),
  ("102-band spectrum assembly per epoch", "P", "4442234", "full spectral coverage per epoch", "—"),
  ("Spectral change detection between epochs", "P", "4441134", "repeated full spectra (not in the fixtures)", "—"),
  ("Chemical composition claims from SPHEREx photometry", "X", "2221111", "not supported by the data", "—"),
  ("Redshift estimation", "X", "1211211", "out of the project's question", "—"),
 ],
 "Photometry and brightness change": [
  ("Aperture photometry with local background (APPHOT-1)", "E", "4435555", "none", T_MEAS),
  ("Pair difference with propagated errors (PAIRDIFF-1)", "E", "4435555", "WLMATCH-2", T_MEAS),
  ("Reference-calibrated pair difference (PAIRDIFF-2)", "E", "5545555", "≥ 3 matched reference stars", T_CAL),
  ("Error-scale calibration check from constant references (CALCHECK-1)", "E", "5545555", "reference stars", T_CAL),
  ("5σ sensitivity statement: smallest detectable change", "E", "5545555", "noise model", T_ASSESS),
  ("Detection threshold |z| ≥ 5 with z described as a significance, never a probability", "E", "4445555", "none", T_ASSESS),
  ("Variance decomposition of every z denominator (UNC-1)", "N", "4545555", "logged inputs", T_DISC),
  ("Recompute check: logged z versus z recomputed from logged inputs", "N", "4445555", "logged inputs", T_DISC),
  ("PSF-fitting photometry", "P", "4432134", "PSF model", "—"),
  ("Light-curve period search", "P", "3431133", "dense time sampling (not available)", "—"),
  ("Variability classification (e.g. star type)", "X", "2321111", "far beyond the evidence", "—"),
 ],
 "Astrometry and motion": [
  ("Gaussian centroids (CENTROID-G2D-1)", "E", "4435555", "none", T_MEAS),
  ("Per-exposure plate solutions with leave-one-out residuals (PLATE-LOO-1)", "E", "5435555", "reference stars", T_MEAS),
  ("Reference selection with RUWE and quality cuts (REFSEL-2)", "E", "4435555", "Gaia", T_MEAS),
  ("Parallax and aberration handling before the fit (EPHEM-AA-LP-1)", "E", "5435555", "ephemeris", T_EPH),
  ("Epoch-averaged linear motion fit (LINFIT-EPOCH-1) with per-exposure cross-check (LINFIT-LOO-1)", "E", "5545555", "≥ 2 epochs", T_MEAS),
  ("Comparison with the catalogue proper motion (z per axis)", "E", "5445555", "catalogue astrometry", T_ASSESS),
  ("Registration-limit test: is the motion larger than the registration error? (HYPO-1 T-REG)", "N", "5545555", "plate residuals", T_DISC),
  ("Parallax-bound test: can parallax alone explain the shift? (HYPO-1 T-PLX)", "N", "4445555", "parallax", T_DISC),
  ("Chromatic centroid offsets per detector", "P", "4432234", "per-detector motion fits", "—"),
  ("Orbit fitting for moving solar-system objects", "X", "3321122", "different science case", "—"),
  ("Planet X candidate search", "X", "3411111", "would invite unsupported discovery claims", "—"),
 ],
 "Calibration and quality control": [
  ("Exposure-level quality flags and rejection reasons", "E", "4435555", "none", T_MEAS),
  ("Data-quality outcome: how much is usable and why", "E", "4535555", "ASSESS-2", T_ASSESS),
  ("Robustness tests with injected gain changes and outliers", "E", "4335555", "synthetic", T_ROB),
  ("Calibration audit document", "E", "3325555", "none", "docs/CALIBRATION_AUDIT.md"),
  ("Calibration-change hypothesis tested by the reference ratio (T-REFRATIO)", "N", "5545555", "matched references", T_DISC),
  ("Error-model hypothesis tested by the calibration check (T-CALCHECK)", "N", "4445555", "CALCHECK-1", T_DISC),
  ("Cross-detector flux consistency check", "P", "4433344", "overlapping wavelengths", "—"),
  ("Persistence and saturation detection", "P", "3332134", "detector models", "—"),
  ("Automatic exclusion tuned by machine learning", "X", "1212111", "opaque, unverifiable", "—"),
  ("Manual exclusion with a logged reason", "P", "3424444", "record schema change", "—"),
 ],
 "Outcome assessment": [
  ("Deterministic outcome categories per question (ASSESS-2)", "E", "5545555", "measurements", T_ASSESS),
  ("Criteria shown with each outcome", "E", "4535555", "ASSESS-2", T_E2E),
  ("Failed fit never reported as no motion", "E", "5445555", "ASSESS-2", T_ASSESS),
  ("Absence of a detection reported with the sensitivity, not as proof", "E", "5445555", "ASSESS-2", T_ASSESS),
  ("Limitations attached to each outcome", "E", "4535555", "ASSESS-2", T_ASSESS),
  ("Stability check: outcomes under five parameter perturbations (STAB-1)", "E", "5545555", "server", T_ROB),
  ("Outcome comparison between two saved investigations", "N", "3435555", "vault", T_E2E),
  ("Outcome confidence as a probability", "X", "1111111", "no calibrated probability model exists", "—"),
  ("Expert-tunable thresholds in the interface", "P", "3323342", "risk of threshold shopping", "—"),
  ("Outcome history across data releases", "P", "4432133", "several releases", "—"),
 ],
 "Discovery Engine": [
  ("Engine stages A–G (inventory, question, plan, execution, review, next steps, record)", "N", "4555555", "record", T_DISC),
  ("Registered research questions with requirements (answerable / with limits / not answerable)", "N", "5555555", "capability registry", T_DISC),
  ("Unanswerable questions stated with the reason (cause, discovery, distance)", "N", "5545555", "none", T_DISC),
  ("Test plan per question: inputs, method, preconditions, assumptions, outputs, validation, limitations", "N", "4545555", "capability registry", T_DISC),
  ("Execution links to where each test runs", "N", "3435555", "interface", T_E2E),
  ("Evidence review linking outcomes, hypotheses and uncertainty", "N", "4535555", "DISC-1", T_E2E),
  ("Rule-based next steps with what they can and cannot establish", "N", "5555555", "registry, availability", T_DISC),
  ("Next steps that need unavailable services say so", "N", "4445555", "availability", T_DISC),
  ("Research question kept with the saved investigation", "N", "3435555", "vault", T_E2E),
  ("Automatic multi-target survey mode", "P", "4332133", "many acquired targets", "—"),
  ("Expected-information-gain ranking of next steps", "X", "3322121", "would need a probability model we do not have", "—"),
 ],
 "Hypothesis testing": [
  ("Hypothesis Arena: competing explanations × recorded tests matrix (HYPO-1)", "N", "5555555", "record", T_DISC),
  ("Six test statuses with stated rules; no probabilities", "N", "5545555", "none", T_DISC),
  ("Published overall rule, identical in Python and the browser", "N", "4445555", "rules.js parity", T_STAT),
  ("Explanations without an implemented test shown as not tested", "N", "4545555", "none", T_DISC),
  ("User-written hypotheses labelled as interpretations, attached to recorded tests", "N", "3535555", "context", T_E2E),
  ("Undo after removing a hypothesis", "N", "1424555", "none", T_E2E),
  ("Known-answer tests: gain-change fixture makes the calibration hypothesis consistent", "N", "4335555", "synthetic", T_DISC),
  ("Neighbour-blend test (T-NEIGHBOUR)", "P", "4432234", "deeper catalogue of neighbours", "—"),
  ("Spectral-slope test (T-SLOPE)", "P", "4433244", "matched-channel photometry", "—"),
  ("Bayesian model comparison", "X", "3322121", "no defensible priors or likelihoods for these data", "—"),
  ("Model-generated hypotheses entered into the matrix", "X", "2321122", "unverifiable; the model never measures", "—"),
 ],
 "Uncertainty and sensitivity": [
  ("Motion uncertainty components: fit σ, per-exposure cross-check, catalogue error", "N", "5545555", "record", T_DISC),
  ("Parallax residual shown as a bound, never as a σ", "N", "4445555", "parallax", T_DISC),
  ("Brightness z denominator shares: exposure A, exposure B, calibration", "N", "4545555", "logged inputs", T_DISC),
  ("Sensitivity to analysis choices kept separate from statistical uncertainty", "N", "5545555", "STAB-1", T_E2E),
  ("Named list of effects no method quantifies", "N", "5545555", "none", T_DISC),
  ("Within-visit scatter floor reported as a count of affected visits", "N", "3335555", "LINFIT-EPOCH-1", T_DISC),
  ("Bootstrap confidence intervals", "P", "4333344", "enough epochs for resampling", "—"),
  ("Systematic-error budget per detector", "P", "4432233", "calibration studies", "—"),
  ("Error bars on screen without a stated source", "X", "1211111", "unverifiable", "—"),
  ("Monte-Carlo propagation through the whole pipeline", "P", "4332343", "compute budget", "—"),
 ],
 "Evidence graph and traceability": [
  ("Graph of sources, target, observations, measurements, comparisons, claims, methods, limitations", "E", "5555555", "record", T_E2E),
  ("Claim tracing back to observations with typed steps", "E", "5555555", "graph", T_E2E),
  ("Observation nodes with file, checksum and archive identifier", "E", "4435555", "bundle", T_AI),
  ("Method nodes from recorded method versions", "E", "4435555", "record parameters", T_AI),
  ("Competing explanations as graph nodes with their recorded tests", "N", "4545555", "HYPO-1", T_DISC),
  ("Keyboard-operable graph nodes", "E", "2425555", "none", T_E2E),
  ("Evidence graph export (JSON)", "N", "3435555", "studio", T_E2E),
  ("Graph diff between two investigations", "P", "3434344", "two graphs", "—"),
  ("Force-directed free layout", "X", "1222532", "hides the evidence order", "—"),
  ("Graph query language", "P", "2323443", "users who need it", "—"),
 ],
 "Copilot and the evidence guard": [
  ("Meta model copilot through read-only tools", "E", "4545245", "META_API_KEY (not configured here)", T_AI),
  ("Local deterministic assistant when no key or offline", "E", "3445555", "none", T_AI),
  ("Twelve read-only tools, including the capability registry", "N", "4435555", "registry", T_TOOLS),
  ("Capability questions answered from the registry", "N", "3435555", "list_capabilities", T_DISC),
  ("Answer layout: Answer · Evidence · Method · Limitations · Next step", "N", "4535555", "answer schema", T_E2E),
  ("Evidence chips linking claims to tool outputs", "E", "4535555", "tool calls", T_E2E),
  ("Conversation saved with the investigation", "E", "3435555", "vault", T_E2E),
  ("Meta smoke test script", "E", "3425255", "key", "scripts/meta_smoke_test.py"),
  ("Streaming answers", "P", "1424344", "model API streaming", "—"),
  ("Copilot that runs new measurements", "X", "2221111", "the model never measures (rule)", "—"),
  ("Voice interface", "X", "1221333", "outside the brief", "—"),
  ("GUARD-3: every number in an answer must match a tool output", "E", "5555555", "tool outputs", T_AI),
  ("Withheld drafts shown with the guard's reasons", "E", "4545555", "guard", T_AI),
  ("Claims typed as evidence, interpretation or speculation", "E", "4535555", "schema", T_AI),
  ("Discovery wording blocked for candidates", "E", "5445555", "guard", T_AI),
  ("Tool contract tests", "E", "3335555", "none", T_TOOLS),
  ("Local answers pass the same guard", "N", "3435555", "guard", T_DISC),
  ("Prompt-injection screening of imported text", "P", "3433343", "imported notes reach the model", "—"),
  ("Red-team evaluation set for the model", "P", "4433143", "model access", "—"),
  ("Model output cached as evidence", "X", "1111111", "a model answer is never evidence", "—"),
  ("Free web search by the copilot", "X", "2321122", "unverifiable sources; network", "—"),
 ],
 "Investigation vault and records": [
  ("Save, reopen, delete investigations with two-step delete", "E", "3535555", "server or browser storage", T_E2E),
  ("Export and import records with content-hash verification", "E", "4535555", "hash", T_E2E),
  ("Import preview before anything is stored", "N", "3535555", "hash.js", T_E2E),
  ("Search across name, target, notes, tags and hash", "N", "2535555", "none", T_E2E),
  ("Tags and tag filter", "N", "2435555", "none", T_E2E),
  ("Rename and retag in place", "N", "1435555", "PATCH /api/records", T_API),
  ("Duplicate a saved investigation", "N", "1435555", "clone endpoint", T_API),
  ("Compare two saved investigations (parameters, outcomes, context)", "N", "3535555", "records", T_E2E),
  ("Saved context (research question, user hypotheses) treated as untrusted", "N", "3445555", "sanitiser", T_E2E),
  ("Shared team vault", "P", "2423233", "accounts, permissions", "—"),
  ("Cloud sync of records", "X", "1322232", "would send records off the machine", "—"),
 ],
 "Reports, figures and export": [
  ("Markdown report with methods, limitations and provenance", "E", "4535555", "record", T_E2E),
  ("Report Studio: report, record, graph, discovery report, package in one place", "N", "3535555", "server or precomputed files", T_E2E),
  ("Figure export as standalone SVG with target, hash, methods and synthetic label", "N", "3535555", "charts", T_E2E),
  ("Reproducibility package (deterministic ZIP with SHA256SUMS) (PKG-1)", "N", "5545555", "record, bundle manifest", T_DISC),
  ("Viewer downloads through the host's download capability", "E", "2435555", "host", T_E2E),
  ("PDF report", "P", "2433353", "PDF renderer", "—"),
  ("Citation (BibTeX) for datasets and methods", "P", "3434454", "DOIs", "—"),
  ("Publication-ready figure styling presets", "P", "2333454", "none", "—"),
  ("Automatic paper drafting", "X", "1321121", "invites unsupported claims", "—"),
  ("Slides from an investigation", "P", "1333454", "export format", "—"),
 ],
 "Reproducibility and replay": [
  ("Content hash of every investigation record", "E", "5545555", "stable JSON", T_STAT),
  ("Replay: re-execute a saved investigation and compare hashes", "E", "5545555", "server, bundle", T_API),
  ("Browser check against precomputed runs in the static preview", "E", "3435555", "precomputed runs", T_E2E),
  ("Content hash recomputed in the browser exactly as Python", "E", "4445555", "hash.js parity", T_STAT),
  ("Software versions recorded with every result", "E", "4435555", "none", T_API),
  ("Package verification instructions (sha256sum -c)", "N", "3435555", "PKG-1", T_DISC),
  ("Container image for exact environment replay", "P", "3423343", "container registry", "—"),
  ("Cross-platform determinism test (macOS/Linux)", "P", "3323343", "second platform", "—"),
  ("Replay across data releases with a difference report", "P", "4432133", "several releases", "—"),
  ("Blockchain notarisation of records", "X", "1121211", "adds nothing a hash does not", "—"),
 ],
 "Interaction and navigation": [
  ("Workspaces with back/forward history and deep links", "E", "2435555", "none", T_E2E),
  ("Discovery loop bar (Explore → … → Share)", "N", "2535555", "none", T_E2E),
  ("Command palette (Ctrl/⌘+K, /) with fuzzy search", "N", "1535555", "none", T_E2E),
  ("Keyboard shortcuts (Alt+1…7, ?, Esc, arrows, Space)", "N", "1435555", "none", T_E2E),
  ("Glossary and shortcut reference dialog", "N", "2535555", "none", T_E2E),
  ("Three levels of detail: Explore, Investigate, Research", "N", "3535555", "none", T_E2E),
  ("Persistent investigation context across workspaces", "N", "3535555", "state", T_E2E),
  ("Guided tour for first-time users", "P", "1423444", "content", "—"),
  ("Undo for every action", "P", "1423343", "action log", "—"),
  ("Multi-window layouts", "X", "1221333", "complexity", "—"),
 ],
 "Accessibility": [
  ("Semantic landmarks, labelled controls, keyboard operation", "E", "2435555", "none", T_E2E),
  ("Modal dialogs with focus trap and focus return", "N", "1435555", "none", T_E2E),
  ("Status announced with aria-live regions", "E", "1435555", "none", T_APP),
  ("Reduced-motion support", "E", "1435555", "none", "web/css/app.css"),
  ("Colour never the only carrier of meaning (status text on every chip)", "N", "2435555", "none", T_E2E),
  ("Responsive layouts at tablet and phone widths without horizontal scroll", "N", "2435555", "none", T_E2E),
  ("Screen-reader audit with assistive technology", "P", "1423343", "AT testing", "—"),
  ("Light theme", "P", "1424454", "design tokens", "—"),
  ("Sonification of light curves", "P", "1332343", "audio design", "—"),
  ("Localisation", "P", "1424444", "translations", "—"),
 ],
 "Visual design and visualization": [
  ("Midnight observatory theme with data-bearing detector colours", "E", "1435555", "none", "web/css/app.css"),
  ("Proper-motion and brightness charts from recorded values", "E", "4535555", "record", T_APP),
  ("Uncertainty component chart (σ bars, bounds as ticks)", "N", "3535555", "UNC-1", T_E2E),
  ("Variance-share bars per pair", "N", "3535555", "UNC-1", T_E2E),
  ("Evidence matrix with status chips", "N", "4535555", "HYPO-1", T_E2E),
  ("Synthetic-data label on every view and export", "E", "4445555", "none", T_E2E),
  ("Animated star field background", "X", "1211514", "decorative; distracts from data", "—"),
  ("3D sky globe", "P", "1332343", "rendering library", "—"),
  ("Fake live counters or activity indicators", "X", "1111111", "misleading (rule)", "—"),
  ("Interactive chart brushing and linked selection", "P", "2433454", "chart layer", "—"),
 ],
 "Offline operation and static preview": [
  ("OFFLINE=1 forbids all network use", "E", "4445555", "none", T_OFF),
  ("Static preview recorded from the real server at build time", "E", "3545555", "build script", T_STAT),
  ("Precomputed discovery reports, packages and capability registry in the preview", "N", "3535555", "build script", T_E2E),
  ("Preview capability registry says what runs where (browser port, precomputed, server only)", "N", "3445555", "build script", T_E2E),
  ("Parameter sets not precomputed are refused, not imitated", "E", "4445555", "PreviewLimit", T_E2E),
  ("Browser storage for preview records, with fallback to memory", "E", "2435555", "none", T_E2E),
  ("Offline map tiles", "X", "1211222", "no map in the product", "—"),
  ("Service worker for installable offline app", "P", "1333443", "packaging", "—"),
  ("In-browser Python (WebAssembly) re-execution", "P", "3322343", "large runtime", "—"),
  ("Pretending to re-execute in the preview", "X", "1111111", "dishonest (rule)", "—"),
 ],
 "Testing, quality gates and performance": [
  ("Unit, integration and robustness test suites", "E", "4435555", "none", "scripts/verify.py"),
  ("End-to-end control tests in server and static modes", "E", "3435555", "Playwright", T_E2E),
  ("JavaScript/Python parity tests (hash, pair comparison, overall rule, intent routing)", "N", "4445555", "node", T_STAT),
  ("Feature-catalogue consistency test", "N", "2335555", "this script", T_FC),
  ("Gate report with PASS / FAIL / BLOCKED / NOT RUN", "E", "4435555", "none", "docs/TEST_REPORT.md"),
  ("Page-load and analysis timing measurements", "N", "2335455", "Playwright", "docs/TEST_REPORT.md"),
  ("No external requests during use (asserted)", "E", "3445555", "none", T_E2E),
  ("Visual regression snapshots", "P", "1333443", "baseline images", "—"),
  ("Load testing with many simultaneous users", "X", "1222443", "single-user tool", "—"),
  ("Fuzzing of the record importer", "P", "2333543", "fuzzer", "—"),
 ],
 "Security, privacy and governance": [
  ("Keys only from the environment; never in code, logs, records or the browser", "E", "4445555", "none", T_AI),
  ("Strict content security policy, no external scripts", "E", "3445555", "none", T_API),
  ("Imported records verified and size-bounded; context sanitised", "N", "3445555", "none", T_E2E),
  ("Request size limits and parameter bounds on the server", "E", "3445555", "none", T_API),
  ("No telemetry", "E", "3445555", "none", T_E2E),
  ("Path-safe record identifiers", "E", "2435555", "none", T_API),
  ("Authentication for multi-user deployment", "P", "1323343", "deployment need", "—"),
  ("Dependency vulnerability scanning", "P", "2334443", "package index access (blocked here)", "—"),
  ("Usage analytics", "X", "1211331", "privacy; not needed", "—"),
  ("Storing model conversations on a third-party service", "X", "1211321", "privacy", "—"),
 ],
 "Documentation and learning": [
  ("Scientific methods document with versioned method IDs", "E", "5535555", "none", "docs/SCIENTIFIC_METHODS.md"),
  ("Limitations document", "E", "4535555", "none", "docs/LIMITATIONS.md"),
  ("Requirement traceability matrix", "E", "3435555", "none", "docs/REQUIREMENT_TRACEABILITY.md"),
  ("Capability registry as machine-readable documentation (CAPREG-1)", "N", "4545555", "registry", T_DISC),
  ("In-app glossary of every scientific term used", "N", "3535555", "none", T_E2E),
  ("Explanations of 'other possible causes' beside each outcome", "E", "4535555", "none", T_APP),
  ("Feature catalogue with scores, tiers and verification", "N", "2335555", "this script", T_FC),
  ("Interactive tutorial target with known answers", "P", "3533444", "synthetic fixture", "—"),
  ("Video walkthrough", "P", "1423454", "recording", "—"),
  ("Educator lesson plans", "P", "2422454", "curriculum partner", "—"),
 ],
}


def tier(status: str, scores: str) -> str:
    if status == "X":
        return "D"
    v = [int(c) for c in scores]
    value, practical = sum(v[:3]) / 3, sum(v[3:]) / 4
    return "A" if value >= 4 and practical >= 4 else "B" if value >= 3 and practical >= 3.5 else "C" if value >= 2.5 else "D"


def build() -> dict:
    items = []
    for i, (domain, rows) in enumerate(C.items(), 1):
        for j, (name, st, sc, deps, ver) in enumerate(rows, 1):
            items.append({"id": f"F{i:02d}.{j:02d}", "domain": domain, "concept": name, "status": STATUS[st], "status_code": st,
                          "scores": dict(zip(DIMENSIONS, (int(c) for c in sc))), "mean": round(sum(int(c) for c in sc) / 7, 2),
                          "tier": tier(st, sc), "dependencies": deps, "verification": ver})
    counts = {"concepts": len(items), "domains": len(C),
              "by_status": dict(Counter(x["status"] for x in items)), "by_tier": dict(sorted(Counter(x["tier"] for x in items).items())),
              "implemented": sum(x["status_code"] in "EN" for x in items)}
    return {"schema": "skytrace.feature_catalogue/1", "dimensions": DIMENSIONS, "statuses": STATUS, "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    out = ["# Skytrace feature catalogue", "",
           "Generated by `python scripts/feature_catalogue.py` from the data in that script; counts are computed. "
           "Checked by `tests/unit/test_feature_catalogue.py` (well formed; every cited verification file exists; every implemented "
           "concept cites one).", "",
           "Note: the Phase 5 brief asked for at least 250 concepts across 25 domains, scored 1–5 on seven dimensions with tiers A–D. "
           "The domain list and the seven dimensions below are this project's own breakdown; they were written for this catalogue "
           "rather than copied from the brief.", "",
           "This is the Phase 5 (0.5) catalogue. Later phases have their own, each deduplicated against the earlier ones: "
           "[PHASE6_CATALOGUE.md](PHASE6_CATALOGUE.md) (0.6), [PHASE7_CATALOGUE.md](PHASE7_CATALOGUE.md) (0.7), "
           "[PHASE8_CATALOGUE.md](PHASE8_CATALOGUE.md) (0.8, the epistemic layer) and [PHASE9_CATALOGUE.md](PHASE9_CATALOGUE.md) "
           "(0.9, the scientific intelligence layer: 600 concepts in 50 domains, a roadmap with categories A–D).", "",
           f"**{c['concepts']} concepts in {c['domains']} domains.** Status: " +
           ", ".join(f"{v} {k}" for k, v in c["by_status"].items()) + ". Tiers: " + ", ".join(f"{k} {v}" for k, v in c["by_tier"].items()) + ".", "",
           "Scores (1–5): " + ", ".join(f"**{l}** {d}" for l, d in zip("SUDFRVK", cat["dimensions"])) + " (5 = little risk of misleading).",
           "Tier: value = mean(S, U, D), practicality = mean(F, R, V, K). A: value ≥ 4 and practicality ≥ 4 · B: value ≥ 3 and "
           "practicality ≥ 3.5 · C: value ≥ 2.5 · D: otherwise, and always for out-of-scope concepts. A tier is a priority signal; "
           "the status says whether something is built.", "",
           "| Domain | Concepts | Existing | New in 0.5 | Deferred | Out of scope |", "|---|---:|---:|---:|---:|---:|"]
    for d in C:
        xs = [x for x in cat["items"] if x["domain"] == d]
        n = Counter(x["status_code"] for x in xs)
        out.append(f"| {d} | {len(xs)} | {n['E']} | {n['N']} | {n['P']} | {n['X']} |")
    out.append("")
    letters = "S U D F R V K".split()
    for d in C:
        out += [f"## {d}", "", "| ID | Concept | Status | " + " | ".join(letters) + " | Tier | Depends on | Verified by |",
                "|---|---|---|" + "---:|" * 7 + "---|---|---|"]
        for x in (x for x in cat["items"] if x["domain"] == d):
            s = list(x["scores"].values())
            out.append(f"| {x['id']} | {x['concept']} | {x['status']} | " + " | ".join(map(str, s)) +
                       f" | {x['tier']} | {x['dependencies']} | {x['verification'] if x['verification'] == '—' else '`' + x['verification'] + '`'} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "feature_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "FEATURE_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
