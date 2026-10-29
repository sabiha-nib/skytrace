# Release notes

## 0.5.0 — 2026-10-30 · the discovery environment

Skytrace now walks an investigation through one loop — explore, observe, compare, detect, test, explain, verify,
preserve, share — and says at each step what the data can and cannot establish. All new results are computed by
versioned, deterministic methods from the recorded investigation; none is a probability. The bundled data are still
synthetic, and real-data acquisition is still blocked in the build environment.

**New**
* **Discovery Engine** (DISC-1): evidence inventory with checksums and counted unknowns; research questions marked
  answerable, answerable with limits or not answerable (and why); a test plan for each; evidence review; rule-based
  next steps that state what each can and cannot establish and which unavailable service it needs.
* **Hypothesis Arena** (HYPO-1): 11 competing explanations × 12 recorded tests, six statuses, one published overall
  rule (identical in the browser, parity-tested). Your own hypotheses, labelled as interpretations, can cite recorded
  tests; removal can be undone.
* **Uncertainty Explorer** (UNC-1): components of the motion and brightness uncertainties, bounds kept as bounds, a
  recompute check of every calibrated z, parameter sensitivity kept separate, and the effects nothing here quantifies.
* **Registration diagnostics** (REGDIAG-1) in the Time Machine, computed in Python and in the browser.
* **Evidence Graph**: competing explanations appear as nodes linked to the claims they would explain.
* **Capability registry** (CAPREG-1): one list of what Skytrace can do and where; the copilot can answer from it.
* **Copilot answers** laid out as Answer · Evidence · Method · Limitations · Next step.
* **Report Studio**: report, record, evidence graph, discovery report and a deterministic reproducibility package
  (PKG-1, with SHA256SUMS); any chart exports as an SVG carrying its target, investigation hash and method versions.
* **Vault**: search, tags and tag filter, rename, duplicate, compare two investigations, import preview with a
  browser-side content-hash check before anything is stored.
* **Interaction**: discovery-loop bar, command palette (Ctrl/⌘+K or /), glossary and shortcuts (?), Alt+1…7, three
  levels of detail (Explore, Investigate, Research).
* **Feature catalogue**: 267 concepts in 25 domains, scored and tiered, generated from data with computed counts.

**Changed**
* Saved records store tags, the investigation context and an outcome summary; the server gains `PATCH /api/records/{id}`,
  `POST /api/records/{id}/clone`, `GET /api/capabilities`, `GET /api/investigations/{id}/discovery` and
  `GET /api/investigations/{id}/package.zip`.
* The faint text colour was raised to meet 4.5:1 contrast on every surface.
* `make_release.py` refuses to overwrite an existing version's artifacts and zips the static preview only when it was
  built from the release commit.

**Unchanged on purpose**: the analysis pipeline, its methods and the content hashes of the fixture investigations.

**Still blocked**: IRSA, SIMBAD, Gaia, the Meta Model API and package indexes are refused by this environment's
network policy. See [LIMITATIONS.md](LIMITATIONS.md).

## 0.4.0 — 2026-10-29 · previewable application

Static preview recorded from the real server, hosted preview, browser parity for pair comparison and content hashes,
verified record import/export, graph provenance, history navigation, every control tested in both modes.
[PHASE4_AUDIT.md](PHASE4_AUDIT.md)

## 0.3.0 — 2026-10-29 · validation

FITS/WCS validation against independent files, calibration audit, ASSESS-2, provenance verification, TOOLS-2 and
GUARD-3, robustness scenarios. [PHASE3_GATES.md](PHASE3_GATES.md)
