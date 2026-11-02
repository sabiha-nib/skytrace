"""Phase 9 capability catalogue: 600 scientific-intelligence capabilities in 50 research domains — a research roadmap, not a
build list. Each concept records its name, research problem, proposed capability, scientific value, required data,
dependencies, implementation complexity, validation strategy, scientific risks and current status.

    python scripts/phase9_catalogue.py      # writes docs/phase9_catalogue.json and docs/PHASE9_CATALOGUE.md

Category  A implemented and tested (evidence and a verifying test are cited; both must exist) ·
          B implementable now with the available infrastructure (not built; nothing claims it) ·
          C requires additional datasets, integrations or infrastructure (named in 'required data') ·
          D speculative or outside the current scope.
Rows      grouped under "# <domain>" lines; name | research problem | proposed capability | required data | complexity (L/M/H) | category | evidence (";"-separated;
          py:x = src/skytrace/x.py, js:x = web/js/x.js) | verifying test (I: test_intelligence, E: test_epistemic, C: e2e test_controls,
          F: test_frontier, R: test_research_os, D: test_discovery, O: test_offline_workflow, S: test_research_session, A: test_api,
          M: test_measurement, W2: test_calibration_v2, G: test_fits_wcs, CO: test_coords, EP: test_ephemeris, AS: test_assess2,
          AR: test_archive, X: test_accessibility, P: test_static_preview, CP: test_copilot2) | validation (optional) | risk (optional)
Scientific value, default validation and risks and the domain's dependencies are stated per domain; a row may override them.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORY = {"A": "implemented and tested", "B": "implementable now", "C": "requires additional data or infrastructure", "D": "speculative or out of scope"}
COMPLEXITY = {"L": "low", "M": "medium", "H": "high"}
TESTS = {"I": "tests/unit/test_intelligence.py", "E": "tests/unit/test_epistemic.py", "C": "tests/e2e/test_controls.py", "F": "tests/unit/test_frontier.py",
         "R": "tests/unit/test_research_os.py", "D": "tests/unit/test_discovery.py", "O": "tests/unit/test_offline_workflow.py", "S": "tests/unit/test_research_session.py",
         "A": "tests/integration/test_api.py", "M": "tests/unit/test_measurement.py", "W2": "tests/unit/test_calibration_v2.py", "G": "tests/unit/test_fits_wcs.py",
         "CO": "tests/unit/test_coords.py", "EP": "tests/unit/test_ephemeris.py", "AS": "tests/unit/test_assess2.py", "AR": "tests/unit/test_archive.py",
         "X": "tests/unit/test_accessibility.py", "P": "tests/unit/test_static_preview.py", "CP": "tests/unit/test_copilot2.py"}
DEFAULT_VALIDATION = {"A": "the cited known-answer, rule or browser test", "B": "known-answer tests on the synthetic fixtures with documented ground truth before release",
                      "C": "validation on real archive data once acquired, cross-checked against an independent tool or catalogue",
                      "D": "not defined: a validation strategy would be part of bringing the concept into scope"}

# (domain, scientific value, typical risk, dependencies)
DOMAINS = [
    ("Computational astrophysics", "physical models tested against measurements", "a model that fits is mistaken for the mechanism", "physical models; validated numerics"),
    ("Observational astronomy", "every result traced to what was observed", "selection effects mistaken for properties of the sky", "archive access; observation metadata"),
    ("Exoplanet research", "planetary signals separated from stellar and instrumental ones", "systematics mimic transits or wobbles", "dense time series; stellar parameters"),
    ("Stellar physics", "measurements interpreted with stellar models", "model degeneracies hide in fits", "stellar atmosphere and evolution models"),
    ("Cosmology", "large-scale inferences with honest error budgets", "out of scope for repeated single-target observations", "survey-scale data; cosmological codes"),
    ("Solar physics", "solar-system and solar context of observations", "contamination from moving or bright solar-system objects", "ephemerides; solar data"),
    ("Time-domain astronomy", "change over time measured, not assumed", "sparse sampling produces spurious periods or trends", "multi-epoch photometry and astrometry"),
    ("Spectroscopy", "spectral features measured with their wavelength solution", "wavelength mismatch read as a spectral change", "spectral WCS; wavelength-matched data"),
    ("Photometry", "fluxes and their errors from stated methods", "calibration drift read as variability", "images, variance planes, reference stars"),
    ("Astrometry", "positions and motions with registration diagnostics", "registration error read as proper motion", "plate solutions; reference catalogues"),
    ("Signal processing", "signals separated from noise by stated filters", "filtering creates features", "time series; noise models"),
    ("Statistical inference", "conclusions bounded by stated statistics", "p-hacking and post-hoc thresholds", "recorded statistics; error models"),
    ("Bayesian methods", "posterior statements where priors are defensible", "priors chosen to give the answer", "explicit priors; likelihood models"),
    ("Scientific machine learning", "learned components with stated validity", "a model learns the artefacts", "labelled training data; held-out validation"),
    ("Anomaly detection", "unusual results found and then explained", "every outlier called a discovery", "baselines of normal behaviour"),
    ("Causal inference", "causal language earned by design", "correlation reported as causation", "documented causal assumptions; interventions"),
    ("Information theory", "test selection reasoned without invented numbers", "information gains computed from made-up priors", "probability models where defensible"),
    ("Experimental design", "the next measurement chosen for what it separates", "designs optimised for a favoured hypothesis", "measurement models; feasibility"),
    ("Uncertainty quantification", "every number with where its error comes from", "unquantified effects silently dropped", "error models; calibration checks"),
    ("Data provenance", "every value traced to a file and a method", "provenance gaps hidden by summaries", "checksums; event logs"),
    ("Scientific visualization", "figures that carry their provenance and units", "visual impressions replace measurements", "recorded values; figure metadata"),
    ("Instrument calibration", "instrument effects measured and corrected openly", "calibration assumptions untested", "calibration products; reference stars"),
    ("Simulation science", "simulations that state what they assume", "simulations confused with observations", "generators with ground truth"),
    ("Reproducibility", "results that repeat, with the differences explained", "execution success read as validity", "manifests; environments"),
    ("Research automation", "routine steps automated within permissions", "automation acting beyond what was approved", "registered actions; audit logs"),
    ("Scientific knowledge graphs", "findings connected by stated relations", "links inferred from shared words", "structured records"),
    ("Research collaboration", "work handed on with what is open", "implying live collaboration that does not exist", "exports; handoff formats"),
    ("Open science", "work others can inspect and re-run", "sharing data without its provenance", "open formats; licences"),
    ("Scientific software verification", "software checked against known answers", "test coverage confused with validity", "test suites; known answers"),
    ("Multimodal scientific data", "images, tables, spectra and text kept in step", "joining data that do not describe the same thing", "multiple data products"),
    ("Research memory", "earlier work recalled with its standing", "old hypotheses turned into facts", "saved investigations"),
    ("Discovery genomics", "how a result developed, field by field", "structural similarity read as physical similarity", "records; reasoning graphs"),
    ("Research frontier mapping", "what is known and unknown, by rule", "a map implying completeness", "boundaries; negative knowledge"),
    ("Counterfactual reasoning", "what would change under a stated change", "hypothetical results stored as observations", "re-assessment methods"),
    ("Adversarial review", "objections raised by rules, tracked to resolution", "manufactured objections", "rule sets; challenge ledgers"),
    ("Bounded autonomy", "autonomous steps that stay within permissions", "silent changes to data or claims", "registered actions; permission levels"),
    ("Cross-investigation intelligence", "patterns across investigations with their basis", "superficial similarity reported as a relation", "a corpus of investigations"),
    ("Integrity and completion", "completion only when requirements are met", "a gate read as proof of truth", "compilers; firewalls; reproductions"),
    ("Epistemic modelling", "every object with an origin-based status", "statuses assigned from wording", "reasoning graphs"),
    ("Hypothesis management", "hypotheses tracked through their tests", "hypotheses ranked by invented likelihoods", "hypothesis registries"),
    ("Evidence negotiation and decisions", "decisions with their reasons and alternatives", "optimality claimed without a model", "decision records"),
    ("Observation planning", "hypothetical plans with stated models", "plans presented as scheduled observations", "measurement models; instrument parameters"),
    ("Archive and data access", "data acquired with verification and provenance", "unverified downloads used in analysis", "archive services; network access"),
    ("Data quality", "quality judged by explicit rules", "quality scores hiding the reasons", "flags; metadata"),
    ("Sensitivity and robustness", "dependence on choices made visible", "fragile results reported as robust", "re-analysis methods"),
    ("Human–AI research interaction", "a model that explains without deciding", "model output taken as computation", "tool contracts; guards"),
    ("Accessibility and research experience", "the instrument usable by everyone", "information conveyed by colour or motion alone", "accessible components"),
    ("Security and trust", "imports and credentials handled safely", "untrusted input executed or keys exposed", "validation; sandboxing"),
    ("Performance and scale", "responsive analysis as data grow", "speed bought by dropping checks", "caching; measurement"),
    ("Education and training", "methods learned with their limits", "training content overstating certainty", "worked examples; synthetic data"),
]

ROWS = """
# Computational astrophysics
Synthetic image generator with ground truth|pipelines need inputs whose answer is known|Gaussian-PSF images with seeded noise, motion and variability|none (generated)|M|A|py:synthetic;py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
Repeated-seed simulation audit|one generated scenario may pass by luck|re-generate with independent seeds and report verdict stability|generated scenarios|L|A|py:simcheck|E:test_simulation_audit_refuses_invalid_scenarios
Counterfactual re-assessment engine|analysts need to see what a choice changes|re-assess recorded inputs under one stated change, baseline untouched|recorded investigation|M|A|py:counterfactual;py:whatif|F:test_reassessment_without_change_reproduces_the_record
PSF-model photometry|aperture photometry is noisy for faint, crowded targets|fit a PSF model per exposure with residual diagnostics|SPHEREx PSF models per detector and wavelength|H|C
Blend deconvolution|neighbours contaminate fluxes and centroids|joint fit of target and catalogued neighbours|deep catalogue; PSF models|H|C
Light-curve model library|pairwise comparisons cannot describe periodic or secular change|registered light-curve models with nested comparison|dense multi-epoch photometry|M|C
N-body ephemerides for nearby systems|binaries and companions move non-linearly|orbit fits for resolved companions|astrometric time series over an orbit|H|D
Radiative-transfer comparison|spectral changes need physical interpretation|compare measured spectra with model grids|spectral model grids; flux-calibrated spectra|H|D
Error propagation by automatic differentiation|hand-propagated errors miss terms|propagate covariances through the measurement chain|existing pipeline|H|B
Monte Carlo error validation|analytic errors may be optimistic|re-measure synthetic images many times and compare scatter with stated errors|generated images|M|B
Pipeline determinism check|non-deterministic code breaks reproduction|re-execute and compare content hashes|recorded investigation|L|A|py:reprox;py:provenance_check|E:test_reproduction_verdicts
Numerical stability tests|ill-conditioned fits give silent garbage|condition numbers and perturbation tests on every fit|existing fits|M|B
# Observational astronomy
Visit-level observation inventory|analysts must know what exists before measuring|every image covering the target with inclusion and exclusion reasons|archive discovery or bundle|M|A|py:discovery|D:test_inventory_traces_to_manifest_and_counts_unknowns
Exposure exclusion with reasons|silently dropped data bias results|record every refused exposure with its code|bundle images|L|A|py:analysis;py:negspace|E:test_negative_knowledge_registry_records_what_failed
Observation-footprint maps|coverage on the sky is hard to judge from tables|draw each exposure footprint around the target|WCS of every image|M|B
Observing-condition metadata|conditions explain outliers|zodiacal background, detector temperature and pointing per exposure|SPHEREx housekeeping metadata|M|C
Cross-survey identification|one survey's view is incomplete|match to Gaia, WISE and 2MASS sources with stated radii|external catalogues; network access|M|C
Field-star context|the target's neighbourhood affects measurements|list catalogued neighbours with separations and magnitudes|Gaia neighbourhood query|L|C
Visit compatibility matrix|not every pair of visits can be compared|pairwise compatibility with reasons|recorded investigation|M|A|py:compat|R:test_matrix_is_the_logged_decisions
Multi-epoch sequences without interpolation|sequences invite interpolation|group compatible epochs into sequences, never filling gaps|recorded investigation|M|A|py:compat|R:test_sequences_are_cliques_of_accepted_pairs_and_say_how_many_visits
Exposure-level quality flags|bad pixels corrupt measurements|apply documented flag bits only, report the rest as unresolved|FLAGS planes|L|A|py:analysis|M:test_photometry_flagged_returns_nan
Observation-gap analysis|gaps hide variability on some timescales|report the timescales the sampling cannot see|visit times|L|A|py:compat|C:test_s3_quality_matrix_metadata_sequences
Proposal-ready target summaries|observing proposals need concise evidence|export the observation inventory, outcomes and open questions|recorded investigation|L|B
Telescope scheduling integration|observations are planned elsewhere|submit planned observations to an observatory|authorised observatory interface|H|D
# Exoplanet research
Transit search in SPHEREx photometry|transits are short and need dense sampling|box-least-squares search with false-alarm levels|dense photometric time series (SPHEREx cadence is too sparse)|M|C
Stellar-activity indicators|activity mimics planetary signals|spectral activity indices per epoch|spectra covering activity lines|M|C
Host-star parameter retrieval|planet properties depend on the host|retrieve Teff, radius and mass with their errors|Gaia and spectroscopic catalogues|M|C
Transit-depth chromaticity|atmospheres change depth with wavelength|compare transit depths across SPHEREx channels|transit-covering exposures|H|C
Astrometric planet detection|wobbles reveal companions|fit reflex motion in residuals|μas astrometry over years|H|D
Contamination dilution correction|neighbours dilute transit depths|estimate flux fraction of neighbours in the aperture|neighbour catalogue; PSF|M|C
Known-planet ephemeris cross-check|observations may catch known transits|predict transit windows of catalogued planets at visit times|planet ephemeris catalogue|L|C
Phase-curve fitting|thermal emission varies with orbital phase|fit phase curves with stated models|phase-resolved photometry|H|D
Exoplanet false-positive rules|eclipsing binaries mimic planets|rule-based vetting of candidate signals|candidate light curves; centroids|M|C
Radial-velocity cross-reference|RV detections constrain masses|list RV-detected companions|RV archives|L|C
Habitability inference|habitability is a model chain|stated model chain with every assumption|planet and star parameters|H|D
Planet-candidate genome|candidates develop through tests|discovery genome specialised to transit candidates|candidate investigations|M|B
# Stellar physics
Spectral-type cross-check|wrong spectral types distort colours|compare SPHEREx spectra with type templates|template library|M|C
Stellar variability classification|variables have types|rule-based classes from amplitude, timescale and colour|multi-epoch photometry|M|C
Brown-dwarf colour sequences|cool objects are identified by colours|place targets on infrared colour sequences|SPHEREx spectra; reference sequences|M|C
Ice and dust absorption features|young stars show ice bands|measure band depths with continuum models|flux-calibrated spectra|H|C
Flare detection|flares are brief outbursts|single-exposure outlier tests against within-visit scatter|within-visit exposures|M|B
Rotation periods|spots modulate brightness|periodograms with window functions|dense photometry|M|C
Evolutionary-track placement|positions on tracks give ages|interpolate tracks with errors|luminosity, Teff; track grids|M|C
Binary-star astrometric acceleration|unresolved binaries accelerate|fit quadratic motion terms with model comparison|long astrometric baselines|M|C
Parallax measurement|distance needs parallax|fit parallax jointly with motion|well-sampled parallax ellipse|M|C
Parallax correction with a stated bound|uncorrected parallax biases motion|apply catalogue parallax with a residual bound|catalogue parallax|L|A|py:science/ephemeris|EP:test_parallax_ellipse_amplitude_and_phase
Stellar population membership|cluster membership depends on motion|compare motion with cluster centroid motions|cluster catalogues|M|C
Chemical abundance from spectra|abundances need high resolution|not achievable at SPHEREx resolution|high-resolution spectra|H|D
# Cosmology
Large-scale structure statistics|cosmology needs many objects|two-point statistics of galaxies|survey-scale catalogues|H|D
Redshift estimation from SPHEREx spectra|SPHEREx measures galaxy redshifts|template-fit redshifts with uncertainties|galaxy spectra; templates|H|D
Inflationary non-Gaussianity|SPHEREx's cosmology goal|not in scope for single-target investigations|full-sky survey data|H|D
Cosmic infrared background fluctuations|background fluctuations encode history|power spectra of background maps|deep maps|H|D
Galaxy photometric-redshift validation|photo-z errors propagate to cosmology|compare with spectroscopic redshifts|spec-z catalogues|H|D
Lensing magnification check|lensing changes fluxes|lens-model lookups for background sources|lens catalogues|M|D
Cosmological parameter inference|parameters need likelihoods|out of scope|cosmological likelihoods|H|D
Extragalactic transient context|transients need host context|host-galaxy lookups|galaxy catalogues|M|C
Survey selection-function modelling|surveys miss objects systematically|model completeness versus magnitude|injection-recovery over the survey|H|D
Foreground subtraction for maps|foregrounds hide signals|component separation|multi-band maps|H|D
Dust-map extinction correction|extinction reddens fluxes|look up E(B−V) along the line of sight|dust maps|L|C
Distance-ladder cross-checks|distances are chained|propagate ladder uncertainties|ladder calibrators|H|D
# Solar physics
Heliocentric-to-barycentric correction|observer motion biases timing and positions|apply barycentric corrections with stated precision|precise ephemerides|M|B
Annual parallax ephemeris|parallax depends on observer position|low-precision analytic Earth ephemeris with a stated bound|visit times|L|A|py:science/ephemeris|EP:test_observer_is_opposite_the_sun_and_one_au
Solar-system object contamination|asteroids pass through apertures|flag known minor bodies near the target at each visit|minor-planet ephemerides; network|M|C
Zodiacal-light background modelling|zodiacal light dominates the background|model background versus ecliptic latitude and season|zodiacal models; housekeeping|M|C
Solar-elongation constraints|observability depends on elongation|report elongation per visit|ephemerides|L|B
Stray-light diagnostics|bright sources scatter light|flag exposures near bright solar-system bodies|ephemerides; stray-light models|M|C
Space-weather effects on detectors|particle hits create artefacts|cosmic-ray hit statistics per exposure|detector housekeeping|M|C
Solar-analog spectral comparison|solar analogs anchor calibration|compare targets with solar spectra|solar reference spectra|M|C
Moving-object linking|faint movers appear in several exposures|link detections into tracks|source lists per exposure|H|D
Cometary activity detection|comets brighten and extend|extended-emission tests|images of the comet|H|D
Solar-cycle context|activity cycles affect backgrounds|annotate visits with solar-cycle phase|solar indices|L|C
Planetary-defence alerts|near-Earth objects need alerts|out of scope|alert streams|H|D
# Time-domain astronomy
Matched-pair flux comparison|fluxes at different wavelengths are not comparable|compare only wavelength-matched pairs, logging every rejection|bundle measurements|M|A|py:science/wavelength;py:analysis|W2:test_pair_codes_structured
Reference-calibrated variability (PAIRDIFF-2)|zero-point drifts mimic variability|ratio to constant reference stars before testing change|reference-star photometry|M|A|py:analysis|W2:test_pairdiff2_removes_calibration_offset
Error-model check on constant stars (CALCHECK-1)|stated errors may be too small|robust scatter of normalised reference differences|reference-star pairs|L|A|py:analysis|W2:test_robust_scatter
Hypothetical-visit what-if for motion|would one more visit change the conclusion?|validated refit with a hypothetical visit, labelled hypothetical|recorded visits|M|A|py:whatif;js:intelcore|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Structure-function analysis|variability amplitude depends on timescale|structure functions with error bars|multi-epoch photometry|M|B
Change-point detection|steps in a light curve need locating|Bayesian blocks with stated priors|dense photometry|M|C
Alert-stream cross-match|other surveys see transients|cross-match targets with alert brokers|broker access; network|M|C
Long-term trend detection|secular trends need long baselines|weighted linear trends with model comparison|years of photometry|M|C
Cadence-aware detectability|sampling limits what can be detected|report the smallest change each timescale could reveal|visit times; errors|M|B
Light-curve classifier|many variables have known shapes|rule-based classes from features|dense light curves|M|C
Time-delay estimation|lensed or reverberating sources lag|cross-correlation with uncertainty|paired dense light curves|H|D
Temporal association inspection|trends with time are often mistaken for causes|per-detector Pearson r against visit time, descriptive only|recorded measurements|L|A|py:causal|I:test_causal_confounders_and_criteria_never_claim_causation
# Spectroscopy
Wavelength at the target from the spectral WCS|each pixel samples a different wavelength|evaluate the -TAB spectral WCS at the target|SPHEREx images|M|A|py:wcs;py:fitsio|G:test_tab_lookup_with_cutout_offset
Low-resolution spectrum assembly|SPHEREx builds spectra from many exposures|assemble per-wavelength fluxes with mixed-epoch labels|bundle measurements|M|A|py:analysis|O:test_expected_outcomes_on_synthetic_truth
Spectral slope test for wavelength explanations|a residual wavelength offset changes flux on a slope|predict the flux change from the local slope|well-sampled spectrum|M|B
Continuum fitting|features need a continuum|polynomial or spline continuum with stated degree|spectra|M|B
Line and band measurement|ice and molecular bands carry physics|band depths with continuum uncertainty|flux-calibrated spectra|M|C
Spectral variability tests|spectral shape may change|compare matched spectra between epochs|matched multi-epoch spectra|H|C
Template cross-correlation|types and redshifts from templates|cross-correlate with template libraries|templates|M|C
Spectro-photometric calibration check|spectral and broadband fluxes should agree|compare synthesized photometry with catalogues|external photometry|M|C
Channel-matching diagnostics|channel tolerance decides pairings|report pairs near the tolerance edge|bundle measurements|L|B
Chromatic PSF effects|PSF width changes with wavelength|wavelength-dependent PSF corrections|PSF models|H|C
Spectral energy distribution fitting|SEDs constrain physics|fit SED models with priors stated|multi-band photometry; models|H|D
Spectral provenance per point|each spectral point needs its exposure|link every point to file and channel|bundle measurements|L|A|py:lineage|E:test_lineage_refers_only_to_recorded_stages
# Photometry
Aperture photometry with variance propagation|fluxes need errors from variance planes|aperture sums with propagated variance|images and variance planes|M|A|py:science/photometry|M:test_photometry_recovers_flux_and_errors
Sky annulus background|backgrounds must be subtracted|annulus median background with error|images|L|A|py:science/photometry|M:test_photometry_no_sky_and_off_image
Unit conversion MJy/sr to µJy|surface brightness must become flux|pixel solid-angle conversion recorded in the lineage|WCS pixel scale|L|A|py:lineage;py:analysis|E:test_lineage_refers_only_to_recorded_stages
Uncertainty budget with variance shares|users need to know which error dominates|measured, estimated and unquantified terms with shares where they add in quadrature|recorded pair terms|L|A|py:budget;py:uncertainty|I:test_instrumental_check_and_budget
Aperture-correction modelling|finite apertures lose flux|curve-of-growth corrections per detector|PSF models|M|C
Forced photometry at catalogue positions|centroid errors bias fluxes|measure at fixed catalogue positions|propagated catalogue positions|M|B
Photometric zero-point tracking|zero points drift between exposures|trend zero points from reference stars over time|reference-star photometry|M|B
Saturation and non-linearity flags|bright targets saturate|flag pixels near full well|detector characterisation|M|C
Colour-term corrections|colour affects calibration|derive colour terms from references|reference colours|M|C
Difference-image photometry|crowded fields need difference imaging|PSF-matched difference images|PSF models; good registration|H|C
Photometric sensitivity statement|absence of change must be bounded|minimum detectable fractional change at threshold|recorded errors|L|A|py:science/assess|AS:test_variability_outcomes
Photometric outlier rejection with reasons|outliers distort statistics|reject with stated rules and keep a record|measurements|L|B
# Astrometry
Gaussian centroiding with calibrated errors|positions need errors|2-D Gaussian fits with error calibration|images|M|A|py:science/centroid|M:test_centroid_uncertainty_is_calibrated
Per-exposure plate solutions|positions need a reference frame|fit plate transforms to reference stars with outlier rejection|reference catalogue|M|A|py:science/astrometry|M:test_plate_solution_recovers_transform_and_rejects_outlier
Visit-averaged motion fit|exposures within a visit are correlated|fit visit means with an empirical error floor|plate-solved positions|M|A|py:science/astrometry|W2:test_epoch_fit_does_not_shrink_correlated_errors
Registration diagnostics|registration residuals limit motion detection|plate RMS against expected shifts|plate solutions|L|A|py:view|D:test_registration_known_answer
Catalogue-consistency test|measured motion should agree with Gaia|per-axis consistency in σ including catalogue errors|Gaia motion|L|A|py:science/assess|AS:test_motion_outcomes
Model arena for motion|static or moving?|static versus linear models per axis with χ², AIC and leave-one-out|visit positions|M|A|py:modelarena|E:test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit
Per-detector motion fits|chromatic offsets differ by detector|fit motion per detector and compare|enough visits per detector|M|B
Quadratic motion terms|acceleration reveals companions|nested quadratic fits with model comparison|long baselines|M|C
Absolute astrometry against Gaia frame|relative motion lacks an absolute zero point|tie to Gaia frame with frame-rotation terms|Gaia references|M|C
Distortion-map validation|SIP distortion may be imperfect|compare distortion residuals across the field|many reference stars|M|C
Astrometric excess-noise statistic|unmodelled motion leaves excess scatter|excess-noise estimate per target|visit residuals|L|B
Proper-motion sensitivity statement|non-detections need bounds|minimum detectable motion at threshold over the baseline|recorded fit|L|A|py:science/assess|AS:test_every_outcome_documents_itself
# Signal processing
Periodogram with window function|sampling creates aliases|Lomb–Scargle with window and false-alarm levels|time series|M|B
Wavelet decomposition|signals live on several scales|wavelet power with significance|dense time series|M|C
Robust scatter estimators|outliers inflate standard deviations|MAD-based scatter|any residuals|L|A|py:analysis|W2:test_robust_scatter
Matched filtering for transients|known shapes are found by matched filters|matched-filter search with injection tests|dense photometry|M|C
Detrending with stated models|systematics need removal|co-trending against housekeeping with model comparison|housekeeping metadata|H|C
Noise-model characterisation|white noise is often assumed|autocorrelation and red-noise tests on residuals|dense residuals|M|C
Image-plane filtering diagnostics|filters can create features|record every filter applied to an image|image processing steps|L|B
Spectral leakage control|windowing distorts spectra|tapering with stated windows|time series|L|C
Injection–recovery of signals|detectability must be measured|inject known signals into real data and recover|real images|M|C
Pixel-level systematics decomposition|pixel response varies|PCA of pixel time series|pixel cubes|H|C
Signal-to-noise maps|where is the signal significant?|per-pixel S/N maps from variance|variance planes|L|B
Cross-correlation of detectors|common-mode noise across detectors|correlate residuals between detectors|multi-detector residuals|M|B
# Statistical inference
Rule-based assessment with stated thresholds|conclusions need explicit criteria|fixed, documented thresholds and outcome categories|recorded measurements|M|A|py:science/assess|AS:test_every_outcome_documents_itself
Threshold sensitivity re-assessment|thresholds may be arbitrary|re-assess at stricter and looser thresholds|recorded inputs|L|A|py:fingerprint;py:counterfactual|I:test_fingerprint_recomputes_and_never_scores
Nested-model comparison criteria|model choice needs criteria|χ², Δχ², AIC without p-values|fits|L|A|py:modelarena|E:test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit
Multiple-testing accounting|many pairs inflate false positives|report the number of tests behind every significant result|recorded pair counts|L|B
False-discovery rate control|many comparisons need FDR control|Benjamini–Hochberg on per-pair significances where independence holds|pair statistics|M|B|||independence between pairs sharing exposures is not guaranteed
Bootstrap confidence intervals|analytic intervals may be wrong|bootstrap over visits|enough visits|M|B
Leave-one-visit-out influence|single visits may drive fits|refit without each visit and report shifts in σ|visit positions|L|A|py:fingerprint;py:modelarena|I:test_fingerprint_recomputes_and_never_scores
Heteroscedastic error models|errors vary with flux|fit error models against flux|reference-star residuals|M|B
Pre-analysis plans with locks|post-hoc choices bias results|lockable protocol with amendments, never called preregistration|session|M|A|js:protocolui|C:test_e8_protocol_and_blind_analysis
Blind analysis|seeing results biases choices|hide outcome-bearing views until unblinding|session|M|A|js:protocolui;js:main|C:test_e8_protocol_and_blind_analysis
Power analysis before observing|will a planned dataset detect the effect?|expected significance under H1 for planned data|measurement model|L|A|py:oracle;js:intelcore|I:test_oracle_known_answers_and_refusals
Effect-size reporting|significance hides magnitude|report effect sizes with intervals alongside z|recorded statistics|L|B
# Bayesian methods
Posterior proper motion with stated priors|priors should be explicit|Gaussian posterior for motion with a stated prior|motion fit; prior from catalogue|M|B|||a catalogue prior can dominate a weak measurement
Hierarchical models across targets|targets share population properties|hierarchical fits with partial pooling|many targets|H|C
Model evidence comparison|Bayes factors compare models|nested sampling evidences|likelihood models; priors|H|C
Prior sensitivity analysis|conclusions may hinge on priors|re-run with alternative priors and report changes|explicit priors|M|B
Bayesian change-point models|steps need posterior locations|change-point posterior|dense photometry|M|C
Expected information gain with defensible priors|test selection in bits needs probabilities|expected KL divergence where priors are documented|prior probabilities for hypotheses|M|C|||no defensible prior exists in the current records
Posterior predictive checks|models must reproduce the data|simulate data from the posterior and compare|posterior samples|M|C
Probabilistic hypothesis statuses|users ask how likely each explanation is|deliberately not provided: statuses are rules|none|L|D|||would invent likelihoods
Bayesian blocks for light curves|optimal segmentation needs priors|blocks with stated prior on changes|time series|M|C
Calibrated probability reporting|probabilities must be calibrated|reliability diagrams for any probabilistic output|labelled outcomes|M|D
Gaussian-process light-curve models|correlated variability needs flexible models|GP fits with stated kernels|dense photometry|H|C
Approximate Bayesian computation|simulators without likelihoods|ABC against the synthetic generator|generator; summary statistics|H|D
# Scientific machine learning
Learned PSF models|analytic PSFs are approximate|PSF models learned from field stars with held-out validation|many field stars per detector|H|C
Artefact classifiers|artefacts need recognising|classifiers trained on labelled artefacts|labelled exposures|H|C|||a classifier learns the labelling habits
Learned photometric redshifts|galaxy redshifts|out of scope for this instrument|training sets|H|D
Semantic recall with embeddings|keyword recall misses synonyms|embedding-based recall with source attribution|a reachable embedding model|M|C|||similarity in embedding space is not scientific relation
Learned anomaly scores|unusual results need flagging|isolation-forest scores with held-out validation|baselines of normal investigations|M|C
Model cards for every learned component|learned components need documentation|model cards with data, metrics and limits|any learned model|L|B
Explainable feature attributions|learned outputs need reasons|attribution maps for classifiers|learned models|M|D
Active-learning labelling loop|labels are expensive|propose examples for human labelling|label interface|M|D
Surrogate models for slow pipelines|re-running is slow|learned surrogates validated against the pipeline|many pipeline runs|H|D
Physics-informed fitting|learned models ignore physics|constrained models respecting known physics|training data|H|D
Learned error-model correction|errors may be systematically wrong|regress residuals on metadata|reference-star residuals|M|C
LLM explanation behind a guard|models may overstate|tool-grounded explanations checked by an evidence guard|tool outputs|M|A|py:ai/guard;py:ai/copilot|CP:test_phase6_intents_pass_the_guard
# Anomaly detection
Rule-based anomaly flags|unusual results need flagging by rule|outcome categories and challenge rules raise anomalies|recorded investigation|L|A|py:adversarial;py:adversary|I:test_adversary_raises_only_rule_backed_challenges
Instrumental reality check|apparent signals may be instrumental|per-question checks of every known instrumental explanation|recorded investigation|M|A|py:instcheck|I:test_instrumental_check_and_budget
Detector-dependence test|a signal on one detector is suspect|count significant calibrated pairs per detector|matched pairs|L|A|py:instcheck|I:test_instrumental_check_and_budget
Population-relative anomaly|is this target unusual among similar ones?|compare with distributions of other targets|many investigations of similar targets|M|C
Anomaly genome|anomalies develop through tests|discovery genome for every candidate, null results included|recorded investigation|M|A|py:dgenome|I:test_genomes_have_every_field_and_cite_real_objects
Outlier provenance drill-down|outliers need tracing|trace an outlier to file and method in one step|reasoning graph|L|A|py:epistemic;js:reasoningui|C:test_e1_reasoning_graph_and_lineage
Anomaly persistence across runs|a real anomaly survives re-analysis|check the category across sibling runs|several runs of a target|L|A|py:memory|I:test_memory_marks_superseded_conclusions_outdated
Novelty against catalogues|known variables are not new|cross-match with variable-star catalogues|variable-star catalogues; network|M|C
Discovery-claim guard|candidates are not discoveries|wording checks in reports, notes and copilot answers|text|L|A|py:integrity;py:ai/guard|E:test_integrity_firewall_flags_problems_without_rewriting
Anomaly triage queue|many anomalies compete for attention|queue ordered by stated rules|anomaly list|L|B
Synthetic anomaly injection|detectors must be tested|inject anomalies into synthetic data and recover|generator|M|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
Unsupervised clustering of light curves|groups may reveal classes|clustering with stability checks|many light curves|H|D
# Causal inference
Documented causal graph of the measurement process|causal claims need assumptions|a directed graph stated as an assumption, not learned|none|M|A|py:causal|I:test_causal_confounders_and_criteria_never_claim_causation
Confounder identification|common causes mislead|common ancestors of cause and effect in the graph|causal graph|L|A|py:causal|I:test_causal_confounders_and_criteria_never_claim_causation
Five-level causal standing|correlation, timing, mechanism, hypothesis and experiment differ|separate criteria C1–C5 per model, never one verdict|recorded investigation|L|A|py:causal;js:intelui2|C:test_i3_adversary_and_causality
Causal-language warnings|notes slip into causal wording|flag user proposals that use causal language and say what they rest on|session|L|A|py:causal;js:intelcore|I:test_browser_intelligence_functions_match_python
Re-analysis interventions|archival data allow no sky interventions|map each model to a re-analysis that removes its cause|counterfactual scenarios|L|A|py:causal;py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Back-door adjustment estimates|effects need adjustment for confounders|adjusted effect estimates when the graph licenses them|measured confounders|M|B|||the graph is an assumption; estimates inherit it
Instrumental-variable designs|unmeasured confounding|IV estimates with stated instruments|valid instruments (rare in archival data)|H|D
Causal discovery from data|learn graphs from data|deliberately not done: the graph is documented, not learned|none|H|D|||learned graphs from tiny samples are unreliable
Granger-style temporal tests|precedence hints at causation|lagged regression with stated limits|long dense series|M|C
Interventional experiments on instruments|calibration can be tested by intervention|out of scope: needs instrument access|instrument operations|H|D
Counterfactual causal queries|what if the cause were absent?|structural counterfactuals under the documented graph|structural equations|H|D
Mediation analysis|effects travel through mediators|direct and indirect effects under the graph|structural model|H|D
# Information theory
Information analysis without probabilities|test ranking is asked for without probabilities|order tests by feasibility and explanations they bear on|hypothesis tests|L|A|py:infogain|F:test_information_analysis_has_no_probabilities
Expected discrimination (Δχ²) of planned data|which data would separate hypotheses?|expected significance and Δχ² under a stated model|measurement model|L|A|py:oracle|I:test_oracle_known_answers_and_refusals
Fisher-information planning|parameter precision from designs|Fisher matrices for motion and parallax|visit design|M|B
Mutual information between tests and hypotheses|information in bits|requires prior probabilities; reported as not computed|priors|M|C
Entropy of the hypothesis set|uncertainty over explanations|requires probabilities; not computed|priors|M|D
Minimum-description-length model choice|model complexity penalties|MDL comparison alongside AIC|fits|M|B
Information content of each visit|which visits matter most?|leave-one-out change in σ per visit|visit positions|L|A|py:whatif;py:fingerprint|I:test_fingerprint_recomputes_and_never_scores
Redundancy between observations|duplicate data add little|flag duplicate exposures|compatibility matrix|L|A|py:compat|R:test_matrix_is_the_logged_decisions
Compression-based anomaly measures|anomalies are less compressible|compression ratios as descriptive features|time series|M|D
Value-of-information decisions|act on expected value|requires utilities and probabilities|utilities; priors|H|D
Divergence between model predictions|how different are two fitted models' predictions?|KL divergence between Gaussian predictive distributions of two fitted models, reported as descriptive|model fits with errors|L|B
Information budget of a dataset|which data product constrains a parameter most?|Fisher information per data product for motion and flux|recorded measurements|M|B
# Experimental design
Hypothetical schedule comparison|which schedule detects more?|compare schedules on the same truth and seed|generator|M|A|py:synthobs|F:test_observation_design_compares_schedules
Candidate observation sets|plans need comparing|evaluate up to six candidate sets with a stated ranking rule|recorded visits|L|A|py:oracle;js:intelui2|C:test_i4_whatif_and_oracle
Evidence negotiation tables|two explanations need distinguishing evidence|tests unique to each viable explanation|hypothesis tests|L|A|py:oracle|I:test_oracle_known_answers_and_refusals
Feasibility constraints|plans must be possible|check inputs are physical and bounded|plan inputs|L|A|py:oracle|I:test_oracle_known_answers_and_refusals
Sequential design|each result changes the next choice|re-plan after each new visit|incoming data|M|C
Optimal design under a model|best design for a parameter|D-optimal visit times for motion and parallax|measurement model|M|B|||optimal only under the stated model
Negative-control experiments|pipelines must not find signals in noise|run on constant sources and expect no change|synthetic or constant targets|L|A|py:experiments|R:test_experiment_validation_and_negative_control
Robustness experiments|results may depend on settings|parameter sweeps with stated criteria|re-analysis|L|A|py:experiments|R:test_experiment_validation_and_negative_control
Injection-recovery completeness curves|detection efficiency versus amplitude|inject and recover over a grid|real images|H|C
Planning reports|plans need records|export plans with assumptions|plans|L|A|py:synthobs|F:test_observation_design_compares_schedules
Experiment specification validation|ill-formed experiments waste effort|validate parameters, variants and criteria before any run|experiment specifications|L|A|py:experiments|R:test_experiment_validation_and_negative_control
Stage ablation design|which stage drives a conclusion?|re-run with one stage replaced by its documented alternative|re-analysis|M|B
# Uncertainty quantification
Per-pair error decomposition|which term dominates a pair's error?|recompute the PAIRDIFF-2 denominator from logged inputs|recorded pairs|L|A|py:uncertainty|D:test_uncertainty_recomputes_logged_values_exactly
Uncertainty flow graph|where does uncertainty travel?|nodes from variance to outputs, with what is not propagated|recorded investigation|M|A|py:uflow|E:test_uncertainty_flow_only_uses_represented_categories_and_lists_omissions
Measured, estimated and unquantified classes|users conflate kinds of uncertainty|classify every term|recorded terms|L|A|py:budget|I:test_instrumental_check_and_budget
Unquantified-effect registry|unknown effects must stay visible|list effects no method quantifies|method documentation|L|A|py:uncertainty;py:budget|I:test_instrumental_check_and_budget
Systematic-error bounds|bounds are not σ|carry bounds separately from statistical errors|bound derivations|L|A|py:uncertainty|D:test_uncertainty_recomputes_logged_values_exactly
Covariance propagation|correlated errors matter|full covariance through the fit|covariances|M|B
Calibration-uncertainty propagation|calibration errors are shared|propagate zero-point errors as correlated terms|calibration products|M|C
Error scaling from constant stars|stated errors may be off|scale by the CALCHECK factor and report it|reference stars|L|A|py:analysis|W2:test_robust_scatter
Uncertainty in derived quantities|derived values need errors|propagate to every derived quantity|derivations|M|B
Coverage tests of intervals|stated intervals should cover truth|coverage on synthetic truth|generator|M|B
Total error budget including systematics|users want one number|deliberately withheld while effects are unquantified|all effects quantified|M|D|||a total would hide unquantified effects
Uncertainty-aware figures|figures hide errors|error bars and bounds styled apart|figure metadata|L|A|js:figurestudio|C:test_s10_figure_studio
# Data provenance
SHA-256 manifests for every input|inputs must be identifiable|checksum every bundle file|bundle files|L|A|py:bundle|O:test_full_workflow_without_network
Event-level investigation records|results need their steps|log every step with status and provenance|pipeline|M|A|py:report;py:analysis|O:test_expected_outcomes_on_synthetic_truth
Content-hashed records|records must be tamper-evident|canonical content hash over the record|record|L|A|py:provenance;py:counterfactual|E:test_reproduction_verdicts
Lineage of a result through nine stages|users ask where a number came from|stage-by-stage lineage with fingerprints|record; manifest|M|A|py:lineage|E:test_lineage_refers_only_to_recorded_stages
Shared entity envelope|engines read objects differently|one envelope with id, version, provenance, time and status|records; sessions|M|A|py:entities;js:intelcore|I:test_entities_have_ids_versions_provenance_and_statuses
Provenance resolution checks|references can dangle|validate that every provenance reference resolves|entities|L|A|py:entities|I:test_entities_have_ids_versions_provenance_and_statuses
Hash-chained session history|edits to history must be detectable|SHA-256 chain over history entries|session|L|A|py:session;js:sessioncore|E:test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid
W3C PROV export|provenance should travel in a standard|PROV-JSON export of entities and activities|entities|M|B
Archive DOI citations|data need citations|cite dataset DOIs in reports|release metadata|L|A|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors
Signed records|hash chains are not signatures|digital signatures with managed keys|key management|M|C|||a signature proves who signed, not that content is right
Provenance-gap reports|gaps hide in summaries|list values lacking file provenance|record|L|A|py:blindspot|E:test_blindspot_coverage_is_over_defined_checks_only
Time-stamped capsules|what was known when?|frozen capsule with digest of record, gate, unknowns|investigation; session|L|A|js:intelui|C:test_i6_memory_reproduction_and_preservation
# Scientific visualization
Figures with provenance|figures lose their sources|figure exports carry target, hash and methods|recorded values|L|A|js:figurestudio|C:test_s10_figure_studio
Reasoning graph visualisation|reasoning is hard to see|layered graph with trace and status pills|reasoning graph|M|A|js:reasoningui|C:test_e1_reasoning_graph_and_lineage
Unknown-universe map|what is unknown is invisible|eight rule-defined regions drawn as frontier bands|intelligence report|M|A|js:intelui;py:unknownmap|C:test_i2_unknown_universe_and_network
Causal graph view|assumptions should be visible|layered causal graph highlighting cause, effect and confounders|causal lab|M|A|js:intelui2|C:test_i3_adversary_and_causality
Relationship network view|connections between investigations|network with rule-filtered edges and stated bases|corpus|M|A|js:intelui|C:test_i2_unknown_universe_and_network
Data-kind legend|real, synthetic, simulated and hypothetical values look alike|six labelled kinds on every intelligence view|labels|L|A|js:intelbits|C:test_i1_command_center_genome_and_fingerprint
Wavelength–time ruler|matched pairs are hard to find|ruler showing every observation by wavelength and date|measurements|M|A|js:ruler|C:test_b_explorer_controls
Interactive light curves|users explore time series|zoomable light curves with error bars|photometry|M|B
3-D sky views|depth from 2-D positions is invented|deliberately not drawn without distances|parallaxes|M|D|||would imply depth not measured
Colour-blind-safe palettes|colour alone misleads some users|palettes checked for colour-vision deficiencies|palette|L|B
Animated blink comparisons|changes are seen by blinking|blink and fade only for compatible pairs|images|M|A|js:timemachine|C:test_b_explorer_controls
Figure accessibility text|figures need text equivalents|accessible names and summaries for every figure|figures|L|A|js:figurestudio|C:test_y_accessible_names
# Instrument calibration
Reference-star calibration ratios|zero points vary by exposure|ratios to constant references|reference stars|M|A|py:analysis|W2:test_pairdiff2_needs_three_matched_refs
Reference-star selection with quality cuts|bad references corrupt calibration|Gaia-based cuts with counts recorded|Gaia references|M|A|py:analysis|W2:test_refsel2_cuts_and_counts
Calibration-change explanation tests|calibration may cause apparent change|HYPO-1 calibration test on reference ratios|reference ratios|L|A|py:hypotheses|D:test_hypotheses_known_answers
Flat-field residual maps|flats are imperfect|residual maps from dithered stars|many dithered exposures|H|C
Detector non-linearity correction|response is non-linear near saturation|apply characterised non-linearity|detector characterisation|M|C
Persistence flags|bright sources leave persistence|flag exposures after bright-source visits|exposure sequence metadata|M|C
Absolute flux calibration check|absolute scale may drift|compare standards with catalogues|spectrophotometric standards|M|C
Spectral-response validation|channel response curves matter|compare with lab response|instrument response files|M|C
Calibration-epoch annotations|calibration versions change|record calibration release per exposure|release metadata|L|A|py:archive/acquire|AR:test_releases_are_cached_separately
Quality-rule registry|quality judgements need rules|eleven explicit data-quality rules|metadata|L|A|py:quality|R:test_quality_outcomes_and_injected_defects
Instrument-model registry|instrument assumptions are scattered|one registry of instrument parameters with sources|instrument documentation|L|B
Cross-detector calibration|detectors differ|inter-detector offsets from overlap regions|overlapping coverage|M|C
# Simulation science
Labelled synthetic bundles|synthetic data must never pass as real|SYNTHETIC = T, origin synthetic, watermarks, verifier refusals|generator|L|A|py:synthetic;py:bundle|O:test_full_workflow_without_network
Byte-reproducible scenarios|simulations must repeat|fixed stamps and seeds give identical bytes|generator|L|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
Validity domains of simulations|simulations hold within bounds|state bounds and refuse outside them|generator|L|A|py:simcheck;py:synthobs|E:test_simulation_audit_refuses_invalid_scenarios
Simulation assumptions registry|what a simulation assumes is hidden|list noise, physics and simplifications|generator|L|A|py:simcheck|E:test_simulation_audit_refuses_invalid_scenarios
Realistic PSF simulation|Gaussian PSFs are too simple|simulate with SPHEREx PSF models|PSF models|H|C
Background and zodiacal simulation|constant skies are unrealistic|simulate structured backgrounds|zodiacal models|M|C
Simulation-based calibration|inference must recover truth|SBC rank statistics|many simulations|H|C
Sim-to-real gap analysis|simulations differ from reality|compare simulated and real statistics|real data|M|C
Scenario twins|scenarios need records|hashed computational records of scenarios|scenarios|L|A|py:twin|F:test_twins_integrity_and_comparison
Synthetic catalogue of variable populations|tests need populations|simulate populations with known statistics|generator|M|B
Failure-case templates|pipelines must fail gracefully|deliberate blend failure case|generator|L|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
Simulation provenance chains|simulated values need lineage|record generator, seed and truth with every output|generator|L|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
# Reproducibility
Independent reproduction with five verdicts|execution success is not reproduction|re-execute and compare every stage|recorded investigation|M|A|py:reprox|E:test_reproduction_verdicts
Reproduction manifests|reproduction needs a travelling record|manifest with data hashes, software, configuration, stages and limitations|recorded investigation|M|A|py:repronet|I:test_reproduction_manifests_validate_and_comparison_classes
Reproduction comparison classes|differences need classifying|exact, input, methodological, dependency, numerical, unexplained|two manifests|M|A|py:repronet;js:intelcore|I:test_reproduction_manifests_validate_and_comparison_classes
Differential debugging|where do two runs diverge?|earliest divergent stage between runs|two records|M|A|py:scidebug|E:test_differential_debugging_finds_the_earliest_divergence
Reproducibility package|others need files to re-run|deterministic zip with SHA256SUMS|record; files|M|A|py:package|D:test_package_is_deterministic_and_self_verifying
Container images|environments drift|published container with pinned versions|container registry|M|C
Cross-platform reproduction|floating point differs across platforms|run on several platforms and classify differences|other machines|M|C
Reproduction registry|who reproduced what?|registry of reproduction attempts with verdicts|shared service|M|C
Dependency lock files|versions drift|lock every dependency with hashes|package index (refused here)|L|C
Replication with independent data|same data are not replication|replicate with independent observations|new observations|H|C
Reproduction status separate from validity|reproduction is read as validity|every result says repeating is not validity|reports|L|A|py:repronet;py:reprox|I:test_reproduction_manifests_validate_and_comparison_classes
Reproduction of synthetic scenarios|scenario results must repeat|same scenario and seed give the same record hash|generator|L|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer
# Research automation
Registered-action executor|automation must call known actions|one executor for every registered action|capability registry|M|A|js:executor;py:capabilities|F:test_executor_implements_every_registered_action
Research cycle with stated rules|what to do next is ad hoc|propose registered actions for open items by rules A1–A6|intelligence report|M|A|py:autonomy|I:test_research_cycle_proposes_registered_actions_by_rule_and_levels_bound_execution
Planner from questions|questions need plans|rule-based plans of registered actions|planner rules|M|A|py:planner|R:test_planner_known_plans
Workflow validation|imported workflows may be unsafe|validate and never auto-run|workflows|L|A|py:workflows|R:test_workflow_validation
Batch runs over targets|many targets need the same steps|validated multi-target workflows|bundles|M|A|py:workflows|R:test_workflow_validation
Scheduled re-analysis|new data should trigger re-analysis|scheduled runs when bundles change|scheduler; new data|M|C
Model-proposed plans behind validation|a language model could propose plans|validate model plans like any plan|a reachable model|M|C
Plan execution through the executor|plans need running|execute a plan's registered actions in order and record each result|plans|M|A|js:executor;py:planner|C:test_s2_planner_plans_runs_and_persists
Radar of next items|what needs attention next is unclear|radar items explained and ordered by a stated rule|record|L|A|py:radar|R:test_radar_items_are_explained_and_ranked_by_the_stated_rule
Automatic duplicate-file detection|duplicate files inflate samples|identical SHA-256 under different names reported on load|bundles|L|A|py:compat|R:test_duplicate_files_are_detected
Bounded retries honouring Retry-After|automated requests must back off|bounded retries that honour Retry-After and never retry policy refusals|network|L|A|py:archive/net;py:connectors|R:test_retry_after_is_honoured_and_bounded
Research autopilot with authorization|objectives need turning into steps|autopilot proposes registered steps; plan level cannot run; local execution needs authorization|registry|M|A|js:autopilotui|C:test_t5_research_autopilot
# Scientific knowledge graphs
Typed reasoning graph|findings need structure|fifteen object kinds with data edges|record|M|A|py:epistemic|E:test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses
Knowledge graph of investigations|records relate to each other|links between saved records from stored facts|saved records|M|A|js:kg|C:test_p_vault_and_studio
Multi-discovery relationships by rule|similar investigations need finding|nine stated relationship rules with basis and limitation|corpus|M|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Concept vocabulary|recall by keyword misses concepts|fixed concept vocabulary mapping terms to concepts|records|L|A|py:memory|I:test_recall_uses_the_concept_vocabulary_and_failure_warnings_quote_reasons
Knowledge package export|knowledge should travel|entity export with schema and digest|entities|L|A|js:intelui|C:test_i6_memory_reproduction_and_preservation
External ontology alignment|terms differ between projects|map concepts to the IVOA UCD vocabulary|UCD vocabulary|M|B
Literature linking|findings relate to papers|link targets to ADS bibliographies|ADS access; network|M|C
SPARQL endpoint|graphs need querying|serve the entity graph through SPARQL|graph store|M|D
Graph diff between versions|knowledge changes|diff entity sets between runs|entity sets|L|B
Relationship-confidence statements|relations have limits|every relation states its limitation|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Semantic search across investigations|users search by meaning|exact search plus concept recall; embeddings blocked|corpus|M|A|js:knowledgeui;py:memory|I:test_recall_uses_the_concept_vocabulary_and_failure_warnings_quote_reasons
Cross-target graph analytics|global patterns|centrality and clustering of the relationship graph|large corpora|M|D
# Research collaboration
Structured handoffs|work changes hands|handoff with open questions, required evidence and reproduction steps|investigation|L|A|js:intelui|C:test_i6_memory_reproduction_and_preservation
Review comments and responses|review needs records|comments, responses and resolutions per item|session|L|A|js:epitabs|C:test_e9_reasoning_lab_and_phase8_tabs
Session export and import|sessions travel|validated, hashed session files|session|L|A|py:session|S:test_session_rules
Branching sessions|alternatives need exploring|branch a session with its history|session|L|A|js:sessionsui|C:test_s9_sessions_dialog_export_import
Live multi-user editing|teams edit together|not implemented: single-user product|accounts; sync service|H|D|||implying collaboration that does not exist
Reviewer identities and assignments|reviews need reviewers|accounts and assignments|identity service|M|D
Conflict detection for concurrent saves|two tabs overwrite each other|detect conflicting session versions|versioned storage|M|B
Shared annotation layers|annotations from many people|layered annotations with authors|accounts|M|D
Discussion threads on claims|claims attract discussion|threads anchored to entities|accounts; storage|M|D
Read-only shared previews|stakeholders need to look|static preview of recorded results|static build|L|A|scripts/build_static.py|C:test_a_load_and_run
Handoff acceptance records|handoffs need acknowledgement|record who accepted a handoff|accounts|L|D
Team dashboards|teams track many investigations|command centre across investigations|corpus|M|B
# Open science
Open, documented formats|closed formats lock data|JSON records with schemas|records|L|A|py:schema;py:session|S:test_browser_matches_python
Static preview without servers|sharing should not need infrastructure|static build answering from recorded files|static build|M|A|scripts/build_static.py|C:test_a_load_and_run
Dataset DOIs in every report|data need credit|DOI per dataset release|release metadata|L|A|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors
Open licences for outputs|reuse needs licences|licence metadata on exports|licence choice|L|B
Machine-readable methods|methods should be parseable|method genome in JSON|methods|L|A|py:methodgenome|E:test_method_genome_is_complete_and_its_tests_exist
FAIR metadata checklist|findable, accessible, interoperable, reusable|checklist over exports|exports|L|B
Public reproduction challenges|others should try to reproduce|publish manifests for challenge|hosting|M|C
Negative results preserved|failures disappear|negative-knowledge registry|records; session|L|A|py:negspace|E:test_negative_knowledge_registry_records_what_failed
Zenodo deposition|archiving needs a repository|deposit packages with DOIs|Zenodo access; network|M|C
Open peer-review packages|reviews should be open|export review boards with links|review data|L|A|js:reviewui|C:test_t8_review_room_repro_story
VOTable export|astronomers use VO formats|export measurements as VOTable|measurements|M|B
Citation files|software needs citing|CITATION.cff for releases|metadata|L|B
# Scientific software verification
Known-answer method tests|software must reproduce known answers|tests per method with generated truth|generator|M|A|py:methodgenome|E:test_method_genome_is_complete_and_its_tests_exist
Python–browser parity tests|two implementations can diverge|run both on the same inputs and compare|both implementations|M|A|tests/js/intel_parity.mjs;js:intelcore|I:test_browser_intelligence_functions_match_python
FITS/WCS validation against astropy files|a native reader may be wrong|compare with independent test files|astropy test files|M|A|py:fitsio;py:wcs|G:test_reads_hand_built_file_per_standard
Mutation testing|tests may not detect bugs|mutate code and check tests fail|test suite|M|B
Property-based testing|edge cases escape examples|generated inputs with invariants|a property-testing library (not installed)|M|C
Scientific compiler|investigations have structural errors|ten-stage checks with one precedence rule|record|M|A|py:scicomp|E:test_compiler_runs_every_stage_and_states_the_precedence_rule
Injected-defect tests|checks must catch defects|inject unit, provenance and wording defects|records|L|A|py:scicomp|E:test_compiler_detects_injected_defects
Test coverage separate from validity|coverage is mistaken for correctness|every method view says tests are not validity|method genome|L|A|py:methodgenome|E:test_method_genome_is_complete_and_its_tests_exist
Continuous integration|tests should run on every change|CI pipeline|CI service|L|C
Fuzzing of parsers|parsers meet hostile input|fuzz FITS and JSON parsers|fuzzer|M|B
Tests of the release gate script|verify.py runs the gates but nothing tests verify.py itself|a unit test that the gate script reports a failing gate|scripts|L|B
Static type checking|types catch errors|type-check the Python package|type checker|L|B
# Multimodal scientific data
Images, tables and spectra in one view|data products are scattered|explorer linking images, measurements and spectra|bundle|M|A|js:explorer|C:test_b_explorer_controls
Copilot over tools|text and data meet in answers|answers grounded in tool outputs|tools|M|A|py:ai/copilot;py:ai/tools|CP:test_plan_tool_executes_nothing_and_uses_registered_actions
Notebook referencing recorded values|notes drift from data|notebook blocks that reference recorded values|session|M|A|js:notebook|C:test_s10_figure_studio
Spectral and photometric joint views|spectra and light curves inform each other|linked spectral and temporal views|measurements|M|B
Multi-instrument fusion|other instruments add information|fuse SPHEREx with WISE or Gaia time series|external data|H|C
Radio and X-ray counterparts|multiwavelength context|cross-match with radio and X-ray catalogues|external catalogues|M|C
Image–text alignment|captions drift from images|figures carry their provenance text|figures|L|A|js:figurestudio|C:test_s10_figure_studio
Audio sonification|another sense for data|sonify light curves|photometry|M|D
Joint likelihoods across modalities|combined fits|joint photometric–astrometric models|models|H|D
Cross-modal consistency checks|products may disagree|compare spectral and broadband fluxes|both products|M|C
Image behind a selected observation|measurements lose their pixels|show the image and measurement of a selected observation together|bundle images|L|A|js:explorer|C:test_b_explorer_controls
Per-epoch spectral cubes|SPHEREx spectra mix epochs|assemble spectra per epoch with epoch labels|dense per-epoch wavelength coverage|M|C
# Research memory
Remembered investigations|earlier work is forgotten|corpus memory over runs and saved records|corpus|M|A|py:memory;py:server/intelligence|I:test_memory_statuses_never_promote_explanations_and_flag_tampering
Memory statuses|old results need standing|verified, provisional, assumption, outdated, unverifiable by rules|corpus|L|A|py:memory|I:test_memory_statuses_never_promote_explanations_and_flag_tampering
Never promoting explanations|old hypotheses become facts|explanations stay provisional however often consistent|corpus|L|A|py:memory|I:test_memory_statuses_never_promote_explanations_and_flag_tampering
Outdated knowledge detection|superseded results linger|mark items superseded by a newer analysis version|corpus|L|A|py:memory|I:test_memory_marks_superseded_conclusions_outdated
Memory of failure|failed approaches are repeated|warn with the earlier reason before repeating|corpus|L|A|py:memory;js:intelcore|I:test_recall_uses_the_concept_vocabulary_and_failure_warnings_quote_reasons
Knowledge evolution tables|conclusions change over runs|how each conclusion moved and what differed|corpus|L|A|py:memory|I:test_memory_marks_superseded_conclusions_outdated
Hypothesis evolution timelines|hypotheses rise and fall|HYPO-1 status per remembered run|corpus|L|A|js:intelui|C:test_i6_memory_reproduction_and_preservation
Session-held memory|your own work is memory too|session entities with versions|session|L|A|js:intelcore;py:entities|I:test_session_entities_follow_rules_and_count_versions
Tamper detection in memory|edited records should not be trusted|unverifiable status when hashes fail|corpus|L|A|py:memory|I:test_memory_statuses_never_promote_explanations_and_flag_tampering
Memory across machines|memory is local|sync memory through a shared store|shared storage|M|C
Forgetting policies|memory grows forever|retention rules with records of what was dropped|policy|L|B
Memory provenance browser|where did a memory come from?|open the source record of any memory item|corpus|L|B
# Discovery genomics
Thirteen-field discovery genome|discoveries develop opaquely|genome built for every question, null results included|record|M|A|py:dgenome|I:test_genomes_have_every_field_and_cite_real_objects
Genome citations|fields need sources|every field cites graph objects or record paths|record|L|A|py:dgenome|I:test_genomes_have_every_field_and_cite_real_objects
Genome comparison by rule|similar discoveries need comparing|shared characteristics, interpretations, weaknesses, uncertainty, methods|two genomes|M|A|py:dgenome|I:test_genome_comparison_is_structural_and_unscored
No similarity score|scores imply physical similarity|structural comparison only|two genomes|L|A|py:dgenome|I:test_genome_comparison_is_structural_and_unscored
Reusable-method detection|methods could transfer|methods one genome used whose inputs the other recorded|two genomes|L|A|py:dgenome|I:test_genome_comparison_is_structural_and_unscored
Genome export|genomes should travel|JSON export with fingerprint and budget|genome|L|A|js:intelui|C:test_i1_command_center_genome_and_fingerprint
Sensitivity fingerprint|discoveries depend on choices|six recomputed dimensions per question|record|M|A|py:fingerprint|I:test_fingerprint_recomputes_and_never_scores
Genome versioning|genomes change between runs|version genomes per run|records|L|B
Genome libraries of known phenomena|compare with known classes|reference genomes for known variable types|real reference investigations|M|C
Genome clustering|groups of similar discoveries|clustering with stated features and stability|many genomes|M|D
Genome-based alerts|new runs resemble old discoveries|alert on rule-based resemblance|corpus|L|B
Genome diff view|what changed between two runs' genomes?|field-by-field diff|two genomes|L|B
# Research frontier mapping
Eight-region frontier map|unknowns are invisible|established to unmeasured regions with rules U1–U8|intelligence report|M|A|py:unknownmap|I:test_unknown_map_regions_have_rules_and_every_item_a_basis
Unexplored parameter regions|parameter space is sampled sparsely|intervals of documented ranges no run sampled|sibling runs|L|A|py:unknownmap|I:test_unknown_map_regions_have_rules_and_every_item_a_basis
One region per item|items double-count|first matching rule wins|intelligence report|L|A|py:unknownmap|I:test_unknown_map_regions_have_rules_and_every_item_a_basis
Map navigation to evidence|regions need drill-down|open graph objects from map items|reasoning graph|L|A|js:intelui|C:test_i2_unknown_universe_and_network
Knowledge boundary regions|claims sit somewhere|four regions with rules B1–B4|record|L|A|py:claims|E:test_knowledge_boundary_rules
Blindspot coverage|parts go unexamined|eleven defined checks without percentages|record; session|L|A|py:blindspot|E:test_blindspot_coverage_is_over_defined_checks_only
Frontier across targets|frontier over many targets|aggregate maps across a corpus|corpus|M|B
Frontier change over time|frontiers move|compare maps between runs|runs|L|B
Unavailable-data catalogue|blocked inputs are forgotten|list inputs that could not be obtained|environment report; inventory|L|A|py:unknownmap|I:test_unknown_map_regions_have_rules_and_every_item_a_basis
Opportunity map|possible research is unclear|opportunities from rules with feasibility|record|M|A|py:possibility|F:test_possibility_layers_and_horizon_cards
Completeness percentages|users want one number|deliberately not computed|none|L|D|||implies knowledge of the unknown
Sky-wide knowledge map|map all of astronomy|out of scope|everything|H|D
# Counterfactual reasoning
Six what-if questions|what-ifs are ad hoc|six brief questions answered only where a method exists|record|M|A|py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
No-valid-method refusals|approximations sneak in|refuse with reasons where no method exists|record|L|A|py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Changed and stable conclusions|users want to know what changed|list conclusions that changed and stayed|scenario results|L|A|py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Baseline isolation|scenarios corrupt originals|baseline recomputed and hash-checked; record untouched|record|L|A|py:counterfactual;py:whatif|F:test_counterfactuals_are_isolated_and_labelled
Prepared scenario library|users need starting points|nine prepared counterfactuals|record|L|A|py:counterfactual|C:test_t2_counterfactual_lab
Recorded what-ifs|what-ifs vanish|record hypothetical scenarios in the session|session|L|A|js:intelui2|C:test_i4_whatif_and_oracle
Background-model alternatives|background may be wrong|alternative background estimators with known-answer tests|method development|M|B
Combined scenarios|changes interact|scenarios with several stated changes|re-analysis|M|B|||interactions make attribution harder
Counterfactual twins|scenarios need records|scenario twins with baseline hashes|scenarios|L|A|py:twin|F:test_twins_integrity_and_comparison
Contradicting brightness pair|what if a new pair showed no change?|requires synthesising pair inputs; refused|hypothetical exposures|M|D
Scenario sensitivity maps|how far can a setting move?|sweep a setting and map category changes|re-analysis|M|B
Counterfactual narratives|scenarios need explanation|plain-language explanation of each change|scenario results|L|A|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled
# Adversarial review
Challenge ledger by eight questions|objections are scattered|ledger organised by the brief's eight questions|record|M|A|py:adversary|I:test_adversary_raises_only_rule_backed_challenges
Rule-backed objections only|manufactured objections waste time|every entry names its rule|record|L|A|py:adversary|I:test_adversary_raises_only_rule_backed_challenges
Resolution with references|objections dismissed without evidence|resolved only with a recorded item|session|L|A|py:adversary;js:intelcore|I:test_adversary_raises_only_rule_backed_challenges
Severity classes per rule|severity is arbitrary|fixed severity per rule|rules|L|A|py:adversarial|F:test_adversarial_rules_and_statuses
Follow-up tests|objections need next steps|follow-up test per question|ledger|L|A|py:adversary|I:test_adversary_raises_only_rule_backed_challenges
Review board perspectives|reviews need structure|eight automated perspectives linked to evidence|record|M|A|py:reviewx|E:test_review_board_links_every_item
Claim stress tests|claims have weak points|ten modes with documented rules|record|M|A|py:claims|E:test_claim_stress_modes_and_results
Red-team prompts for reports|reports overstate|integrity firewall checks|text|L|A|py:integrity|E:test_integrity_firewall_flags_problems_without_rewriting
External reviewer workflows|human reviewers need tasks|assign challenges to reviewers|accounts|M|D
Challenge statistics across investigations|recurring weaknesses|aggregate challenge rules across a corpus|corpus|L|B
Adversarial synthetic tests|can the adversary catch planted flaws?|plant flaws in synthetic records and expect challenges|generator|M|B
Debate transcripts between agents|simulated debates|deliberately not simulated|a verified model provider|H|D|||simulated agent conversations
# Bounded autonomy
Three autonomy levels|autonomy needs bounds|advisory, supervised and restricted automation|capability registry|L|A|py:capabilities;js:intelui2|C:test_i5_research_cycle_permissions_and_gate
Predefined auditable workflow|restricted automation needs a fixed list|one authorization runs a listed workflow|registered actions|L|A|py:capabilities;js:intelui2|C:test_i5_research_cycle_permissions_and_gate
Autonomous action audit log|automated steps must be traceable|every step with level, approval and timestamps in the session|session|L|A|js:intelui2|C:test_i5_research_cycle_permissions_and_gate
Autonomous data acquisition|acquisition could be automated|deliberately excluded: no level grants network|network; authorisation|M|D|||silent external access
Autonomous publication|automation could publish|deliberately excluded|none|L|D|||unreviewed claims leave the lab
Permission classes per action|actions differ in what they can touch|every registered action declares a permission class|capability registry|L|A|py:capabilities|F:test_registry_permissions_cover_every_action
Supervised per-step approval|each automated step needs consent|supervised level runs a step only when you approve it|registry; session|L|A|js:intelui2|C:test_i5_research_cycle_permissions_and_gate
Precondition checks before execution|actions can run on missing inputs|registered preconditions and dependencies per action|registry|L|A|py:capabilities;js:executor|R:test_registry_actions_and_capabilities_are_consistent
Confirmation before costly runs|costly runs surprise users|experiment and workflow runs need a confirming second click|registry|L|A|js:experimentsui;js:workflows|C:test_s8_experiments_and_workflows
Stop control for running automation|automation must be stoppable|stop a restricted workflow between steps|interface|L|B
Step and runtime limits per authorization|automation can run long|cap on steps and runtime for each authorization|registry|L|B
Stop at first failure|failed steps could be retried silently|halt the workflow at the first failure and report it|session|L|B
# Cross-investigation intelligence
Corpus of investigations|cross-investigation reasoning needs a corpus|corpus of recorded runs and saved records, cached by their hashes|saved records|M|A|py:server/intelligence|A:test_phase9_intelligence_corpus_oracle_whatif_reproduction
Same-target relations across runs|repeated runs of a target diverge|N1 links sibling runs and names the parameters that differ|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Conflicting conclusions between runs|two runs disagree|N2 flags different categories for the same question|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Shared failures across targets|the same refusal recurs|N8 links investigations with shared refusal codes|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Repeated analytical weaknesses|the same weak point recurs|N5 links investigations weak in the same stress mode|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Precomputed cross-target genome comparisons|comparisons are slow to make on demand|genome comparisons for corpus pairs|corpus|M|A|py:server/intelligence;py:dgenome|A:test_phase9_intelligence_corpus_oracle_whatif_reproduction
Rule filter on the relationship network|many edges obscure each rule|filter the network by rule|corpus|L|A|js:intelui|C:test_i2_unknown_universe_and_network
Outcome distributions across the corpus|how common is each outcome?|counts of outcome categories per question across investigations|corpus|L|B
Method-transfer suggestions|a method that worked elsewhere may apply|suggest N7 reusable methods as next steps for the receiving investigation|corpus|L|B
Links to other instruments' investigations|other instruments see the same targets|relations to investigations from other pipelines|other instrument pipelines|H|C
Keyword relations|shared words suggest links|deliberately refused: shared words are not scientific relations|none|L|D|||superficial similarity reported as a relation
Shared corpus across users|corpora are local to one machine|shared corpus with provenance per contribution|shared storage; accounts|M|C
# Integrity and completion
Gate before completion|investigations are called done too early|eight requirements before marking complete|record; session|M|A|py:gate;js:intelcore|I:test_gate_requirements_and_session_overlay
Completion is not truth|completion read as correctness|every gate says ready is not true|gate|L|A|py:gate|I:test_gate_requirements_and_session_overlay
Research debt detector|shortcuts accumulate|debt items from compiler, stress, genome and budget|record|L|A|py:gate|I:test_gate_requirements_and_session_overlay
Integrity firewall|texts overstate before export|twelve export-readiness checks, never blocking|text|M|A|py:integrity|E:test_integrity_firewall_flags_problems_without_rewriting
Completion records|completion needs a record|completion with requirement states in the session|session|L|A|js:intelui|C:test_i5_research_cycle_permissions_and_gate
Debt repayment tracking|debt needs paying down|track debt items closed over time|sessions|L|B
Gate profiles per project|projects need different gates|configurable requirement sets with stated rules|configuration|M|B|||weakened gates may pass weak work
Gate certificates|completion should be shareable|signed completion certificates|key management|M|C
Pre-export integrity on every export|exports bypass checks|run the firewall on every export|exports|L|B
Completion audit trail|completion decisions need audit|hash-chained completion events|session|L|A|py:session|E:test_evidence_vault_chain_detects_edits_and_keeps_old_sessions_valid
Retraction workflow|errors found after completion|retract with reasons, keep the record|session|L|B
Independent gate review|gates can be gamed|second reviewer confirms the gate|accounts|M|D
# Epistemic modelling
Origin-based statuses|statuses assigned by wording|ten statuses from origin and method by rules S1–S10|record|M|A|py:epistemic|E:test_epistemic_objects_have_stable_ids_known_kinds_and_grounded_statuses
Negation-aware wording checks|negated claims trip filters|negation within four words in the same sentence|text|L|A|py:epistemic|E:test_asserted_words_ignore_negated_uses
Backward and forward traces|what does a claim rest on?|breadth-first traces over data edges|reasoning graph|L|A|py:epistemic|E:test_claim_lineage_traces_back_to_files_methods_assumptions_and_forward_to_claims
Entity status rules E1–E6|non-graph objects need statuses|rules for investigations, scenarios, session items|entities|L|A|py:entities|I:test_entities_have_ids_versions_provenance_and_statuses
Argument maps|arguments need structure|validity separate from empirical standing|session|M|A|js:argueui|C:test_e9_reasoning_lab_and_phase8_tabs
Status history per object|statuses change|status history across runs|corpus|L|B
Epistemic diffs between runs|what changed in what is known?|diff statuses between runs|two graphs|L|B
Formal logic verification|arguments could be checked formally|proof-assistant encoding of arguments|formal logic tooling|H|D
Uncertainty-aware statuses|statuses ignore error size|combine status with sensitivity|records|M|B|||conflating kinds of uncertainty
Epistemic export standards|statuses should interoperate|map statuses to a published vocabulary|vocabulary|M|C
Status explanations for novices|statuses are jargon|plain-language glossary entries|glossary|L|A|js:palette|C:test_k_palette_help_shortcuts
Status-based filtering everywhere|users want only verified items|filter any list by status|lists|L|B
# Hypothesis management
Competing explanations with rule statuses|alternatives are forgotten|HYPO-1 explanations with tests and statuses|record|M|A|py:hypotheses|D:test_hypotheses_known_answers
User hypotheses with versions|hypotheses get reworded|versions kept and hashed|session|L|A|py:session|S:test_version_histories_are_kept_bounded_and_hashed
Hypothesis arena|hypotheses need comparing|side-by-side test matrix|record|M|A|js:arena|C:test_m_hypothesis_arena
Hypotheses never get probabilities|users want likelihoods|statuses are rules; no probabilities|record|L|A|py:hypotheses|D:test_hypotheses_never_produce_probabilities_and_use_known_statuses
Hypothesis evolution across runs|hypotheses change across runs|timeline per explanation|corpus|L|A|js:intelui|C:test_i6_memory_reproduction_and_preservation
Supersession links|hypotheses replace each other|explicit superseded-by links|session|L|B
Hypothesis-specific tests registry|tests are hard-coded|registry of tests with inputs and rules|hypotheses|M|B
Hypothesis import from literature|papers propose explanations|import with citations|literature access|M|C
Hypothesis ranking by evidence counts|users want an order|order by unresolved tests, never likelihood|hypotheses|L|B|||counts can be mistaken for strength
Cross-target hypothesis sharing|the same explanation recurs|shared viable explanations across investigations|corpus|L|A|py:mdnet|I:test_network_edges_need_a_rule_and_state_basis_and_limitation
Hypothesis kill criteria|when to abandon?|explicit abandonment criteria recorded|session|L|B
Hypothesis generation by models|models could propose explanations|model proposals labelled and tested by rules|a reachable model|M|C
# Evidence negotiation and decisions
Decision records with reasons|decisions are forgotten|recommendations with why-not-higher|record|L|A|py:decide|E:test_decisions_are_explained_and_questions_cite_their_source
Question forge|good questions are hard to find|questions from evidence in seven categories|record|L|A|py:decide|E:test_decisions_are_explained_and_questions_cite_their_source
Distinguishing tests per pair of explanations|which evidence separates two explanations?|unique open tests for each viable explanation|hypotheses|L|A|py:oracle|I:test_oracle_known_answers_and_refusals
No optimality claims|plans claimed optimal|orderings say they are not optima|decision records|L|A|py:decide;py:oracle|I:test_oracle_known_answers_and_refusals
Decision-theory workbench|decisions trade value, cost and risk|explicit utilities and costs with sensitivity|stated utilities|M|B|||utilities are opinions; they must be shown
Cost estimates per action|actions cost time|registered cost per action|registry|L|A|py:capabilities|F:test_registry_permissions_cover_every_action
Risk registers|actions carry risks|risk per action and plan|registry|L|B
Decision revisit prompts|decisions age|prompt when inputs change|session|L|B
Group decision records|teams decide together|record votes and dissent|accounts|M|D
Decision replay|why was this decided?|replay inputs at decision time from capsules|capsules|L|B
Reviewer evidence requests|reviewers ask for evidence|record each requested item and whether it exists|review board; session|L|B
Decision sensitivity to dropped evidence|would a decision survive losing one item?|recompute recommendations without each evidence item|decision records|M|B
# Observation planning
Hypothetical observation planner|observations need planning|candidate sets evaluated under the validated model|record|M|A|py:oracle;js:intelui2|C:test_i4_whatif_and_oracle
Validated slope-error formula|planning formulas may be wrong|reproduce the recorded σ before planning|record|L|A|py:futurelab|E:test_futurelab_formula_is_validated_before_scenarios
FutureLab calculator|scenarios need quick numbers|interactive hypothetical calculator|record|L|A|js:futureui|C:test_e5_models_uncertainty_future
Plans never presented as schedules|plans look like commitments|every plan states it is hypothetical|plans|L|A|py:oracle|I:test_oracle_known_answers_and_refusals
SPHEREx survey-strategy awareness|SPHEREx scans the sky on its own schedule|predict future survey coverage of the target|survey pointing plans|M|C
Visibility windows|targets are observable at times|compute visibility from orbit and constraints|orbit model|M|C
Exposure-time calculator|plans need exposure times|SNR versus exposure for SPHEREx channels|instrument sensitivity model|M|C
Follow-up with other facilities|other telescopes can follow up|plan follow-up requirements per facility|facility parameters|M|C
Plan comparison exports|plans need sharing|export candidate comparisons|plans|L|A|js:intelui2;py:synthobs|F:test_observation_design_compares_schedules
Telescope command interface|plans could be executed|out of scope without authorised integration|observatory interface|H|D
Plan memory warnings|plans repeat failures|memory-of-failure warnings in the planner|corpus|L|A|js:intelui2;js:intelcore|C:test_i4_whatif_and_oracle
Priority queues for targets|many targets compete|ordered queue with stated rules|targets|L|B
# Archive and data access
IRSA SIA and TAP acquisition|data must be fetched|documented IRSA interfaces with retries and caching|network access (refused here)|M|C|||blocked in this environment
Checksum-verified bundles|downloads may be corrupt|verify every file before analysis|bundles|L|A|py:bundle|O:test_full_workflow_without_network
Offline operation|networks fail|analysis never touches the network|bundles|L|A|py:archive/net|AR:test_offline_never_touches_network
Proxy-policy diagnostics|refusals need explanation|diagnose refusals without retrying|network|L|A|scripts/diagnose_environment.py|AR:test_proxy_policy_denial_not_retried
Release-separated caches|releases differ|cache per data release|archive|L|A|py:archive/net|AR:test_releases_are_cached_separately
Connector previews|users want to see requests|preview requests without sending|connector registry|L|A|py:connectors|R:test_connector_previews_match_acquisition_and_send_nothing
Gaia reference acquisition|references come from Gaia|TAP queries with quality cuts|Gaia access (refused here)|M|C
SIMBAD identification|targets need identities|SIMBAD TAP lookups|SIMBAD access (refused here)|L|C
Incremental archive updates|new releases appear|fetch only new exposures|archive access|M|C
Bulk cutout services|many cutouts are slow|batch cutout requests|archive access|M|C
Archive status monitoring|services go down|monitor service status|network|L|C
Data-access audit|acquisitions need records|acquisition audit trail|acquisition|L|A|py:archive/acquire|AR:test_live_then_cache_labels
# Data quality
Eleven data-quality rules|quality is judged vaguely|explicit rules with outcomes, no score|record|L|A|py:quality|R:test_quality_outcomes_and_injected_defects
Edge and blend exclusions|edges and blends distort|refuse with codes|images|L|A|py:analysis|M:test_blended_target_is_flagged_not_measured
Missing values never filled|filled values look real|unknowns counted and left empty|records|L|A|py:discovery|D:test_inventory_traces_to_manifest_and_counts_unknowns
Excluded-exposure share check|heavy exclusion biases samples|flag when a quarter or more is refused|record|L|A|py:instcheck|I:test_instrumental_check_and_budget
Quality reports|quality needs reporting|exportable quality report|record|L|A|py:quality|R:test_quality_outcomes_and_injected_defects
Injected-defect quality tests|quality rules must fire|inject defects and expect failures|records|L|A|py:quality|R:test_quality_outcomes_and_injected_defects
Image-level artefact detection|ghosts and satellites corrupt images|artefact masks from image statistics|images|M|B
Quality trends across releases|quality changes by release|compare quality between releases|several releases|L|C
Quality-weighted analyses|weighting by quality|deliberately avoided: rules, not weights|records|L|D|||weights hide decisions
Metadata completeness reports|missing metadata limits analysis|report unknown fields per observation|inventory|L|A|py:discovery|D:test_inventory_traces_to_manifest_and_counts_unknowns
User-defined quality rules|projects need extra rules|rule editor with validation|rules|M|B
Quality provenance|why was an exposure refused?|trace refusals to codes and files|record|L|A|py:negspace|E:test_negative_knowledge_registry_records_what_failed
# Sensitivity and robustness
Stability under parameter perturbations|small changes may flip results|five perturbations with stability verdicts|bundle|M|A|py:stability|A:test_phase3_params_and_stability
Calibration dependence|results may depend on calibration|re-assess without reference calibration|record|L|A|py:fingerprint|I:test_fingerprint_recomputes_and_never_scores
Error-model dependence|results may depend on error scale|re-assess with scaled errors|record|L|A|py:fingerprint;py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Model-selection dependence|results may depend on model choice|compare model preference with the category|record|L|A|py:fingerprint|I:test_fingerprint_recomputes_and_never_scores
Detector-exclusion robustness|one detector may drive a result|re-assess without each detector's pairs|record|L|A|py:whatif|I:test_whatif_is_isolated_validated_and_refuses_without_a_method
Robustness scores|users want one robustness number|deliberately not computed|none|L|D|||a score hides which choice matters
Global sensitivity analysis|interacting settings|Sobol-style sensitivity over settings|many re-runs|H|B|||costly; interactions need careful design
Sensitivity reports|sensitivity needs reporting|export fingerprints|fingerprint|L|A|js:intelui|C:test_i1_command_center_genome_and_fingerprint
Preprocessing-choice registry|preprocessing choices are implicit|list every preprocessing choice with defaults|pipeline|L|B
Stability across releases|releases change results|re-run on each release|several releases|M|C
Threshold provenance|thresholds look tuned|record when and why each threshold was fixed|thresholds|L|A|py:scicomp|E:test_compiler_runs_every_stage_and_states_the_precedence_rule
Robustness to reference selection|reference choice matters|re-run with alternative reference sets|re-analysis|M|B
# Human–AI research interaction
Evidence guard on model answers|models overstate|guard checks numbers, sources and wording|tool outputs|M|A|py:ai/guard|CP:test_phase6_intents_pass_the_guard
Read-only tool contracts|models must not act|sixteen read-only tools with schemas|tools|M|A|py:ai/tools|CP:test_plan_tool_executes_nothing_and_uses_registered_actions
Local fallback assistant|no model is reachable|deterministic assistant through the same tools|tools|M|A|py:ai/local|CP:test_quality_tool_has_no_score
Model never computes|language models compute badly|every number from deterministic code|tools|L|A|py:ai/copilot|CP:test_plan_tool_executes_nothing_and_uses_registered_actions
Copilot over the intelligence layer|users ask about memory and gates|tools reading the intelligence report|tools|M|B
Live Meta model answers|richer explanations|Meta Model API through the guard|API key and network (blocked here)|M|C
Answer source labels|users must know where answers came from|label tool, draft or recorded sources|answers|L|A|js:copilot|C:test_h2_copilot_sources_drafts_and_plan
Copilot paused during blind analysis|answers reveal outcomes|pause while blind|session|L|A|js:copilot|C:test_e8_protocol_and_blind_analysis
Multi-agent research|agents could divide work|blocked: no verified provider; design only|a verified model provider|H|C
Voice interaction|hands-free questions|speech interface|speech services|M|D
Model-written reports|drafts save time|labelled drafts from tool outputs|tools|L|A|js:notebook|C:test_h2_copilot_sources_drafts_and_plan
Model evaluation harness|model behaviour drifts|scripted evaluation of answers against tools|scripted clients|M|B
# Accessibility and research experience
Keyboard-operable maps|maps need keyboards|map bands are keyboard buttons|maps|L|A|js:intelui|C:test_i2_unknown_universe_and_network
Accessible names for every control|controls without names exclude users|every visible control named|interface|L|A|web/index.html|C:test_y_accessible_names
Reduced motion|animation harms some users|respect reduced-motion preferences|interface|L|A|web/css/app.css|X:test_reduced_motion_disables_animation
Contrast-tested palette|low contrast excludes users|text tokens meet WCAG AA|palette|L|A|web/css/app.css|X:test_primary_button_text_contrast
Responsive layouts|phones and tablets|no horizontal scroll at 820 and 390 px|interface|M|A|web/css/app.css|C:test_r_new_workspaces_narrow
Screen-reader testing|automated checks miss real use|tests with screen readers|assistive technology|M|C
Progressive disclosure|density overwhelms|details collapsed by default with summaries|interface|L|A|js:intelbits|C:test_i1_command_center_genome_and_fingerprint
Levels of detail|novices and experts differ|explore, investigate and research levels|interface|L|A|js:main|C:test_j_levels
Plain-language glossary|jargon excludes|glossary and help|glossary|L|A|js:palette|C:test_k_palette_help_shortcuts
Localisation|English-only interface|translated interface strings|translations|M|D
High-contrast theme|some users need more contrast|separate high-contrast theme|theme|L|B
Command palette|navigation is slow|keyboard command palette|interface|L|A|js:palette|C:test_k_palette_help_shortcuts
# Security and trust
Import validation|imports may be hostile|validate records, sessions and workflows on import|imports|L|A|py:server/research|A:test_phase6_research_planner_sessions_experiments_connectors
Path-traversal protection|file paths can escape|reject traversal in every route|routes|L|A|py:server/app|A:test_rejects_traversal
Keys only from the environment|keys leak through code|keys never in code, logs, records or browser|environment|L|A|py:ai/meta_client|A:test_status_and_security_headers
Strict content-security policy|injected scripts|CSP with no inline scripts and no external requests|interface|L|A|py:server/app|C:test_z_no_external_requests_no_errors
Manifest tamper detection|manifests can be altered|digest over manifest content|manifests|L|A|py:repronet|I:test_reproduction_manifests_validate_and_comparison_classes
No network permission for automation|automation reaches out|no autonomy level grants network|registry|L|A|py:capabilities|I:test_research_cycle_proposes_registered_actions_by_rule_and_levels_bound_execution
Dependency vulnerability review|dependencies carry vulnerabilities|review against advisories|package index and OSV (refused here)|L|C
Signed releases|releases may be replaced|sign release archives|key management|M|C
Sandboxed workflow execution|workflows run code|workflows run only registered actions|registry|L|A|py:workflows|R:test_workflow_validation
Rate limiting|servers can be flooded|per-client rate limits|deployment|L|B
Accounts and permissions|multi-user access|authentication and roles|identity service|H|D
Security regression tests|fixes regress|security tests in the suite|tests|L|A|tests/integration/test_api.py|A:test_rejects_traversal
# Performance and scale
Report caching by content hash|repeated work wastes time|cache reports by record hash|server|L|A|py:server/intelligence|A:test_phase9_intelligence_corpus_oracle_whatif_reproduction
Performance regression tests in the local suite|timings are measured by a script at release but no test checks them|a test that fails when timings exceed recorded budgets|measurement script|L|B
Corpus caching|corpus memory is expensive|cache memory and network by the set of hashes|server|L|A|py:server/intelligence|A:test_phase9_intelligence_corpus_oracle_whatif_reproduction
Static recordings within host limits|hosts limit file counts|one image file per target, loaded by the browser suite in static mode|static build|L|A|scripts/build_static.py;js:static/backend|C:test_a_load_and_run
Parallel pipeline runs|many targets take long|run analyses in parallel|multi-core|M|B
Incremental intelligence updates|recomputing everything is slow|update only affected parts|dependency tracking|M|B
Large-corpus memory indexing|memory scans everything|indexed concept lookup|large corpora|M|B
Streaming large images|images are large|stream tiles instead of whole images|tiling|M|B
GPU acceleration|fits are slow at scale|GPU kernels for fitting|GPU hardware|H|D
Database-backed storage|files do not scale|database for records and sessions|database|M|C
Performance budgets in CI|regressions creep in|fail builds over budget|CI|L|C
Memory-aware rendering|huge graphs freeze browsers|virtualised lists and graphs|interface|M|B
# Education and training
Guided missions|beginners need paths|missions whose completion is read from the session|session|L|A|py:missions|R:test_missions_read_completion_from_the_session
Synthetic training targets|teaching needs known answers|labelled synthetic targets|generator|L|A|py:synthetic|O:test_expected_outcomes_on_synthetic_truth
Method walkthroughs|methods are opaque|step-by-step method explanations|method genome|M|B
Interactive concept explanations|concepts are abstract|explanations inside the discovery engine|discovery engine|L|A|js:discovery|C:test_l_discovery_engine
Worked-example notebooks|examples teach|notebooks with recorded values|notebook|L|A|js:notebook|C:test_s10_figure_studio
Exercises on counterfactuals|counterfactual thinking is hard|exercises with prepared scenarios|scenarios|L|B
Exercises on debugging|debugging is a skill|planted-defect exercises|synthetic records|M|B
Assessment of learning|did users learn?|quizzes with feedback|questions|L|D
Instructor dashboards|teachers track students|class progress views|accounts|M|D
Curriculum alignment|courses need alignment|map missions to curricula|curricula|L|D
Misconception warnings|common errors recur|warnings for common misinterpretations (z is not a probability)|text|L|A|py:integrity|E:test_integrity_firewall_flags_problems_without_rewriting
Certificate of completion|learners want credit|completion certificates|accounts|L|D
"""


def _path(p):
    if p.startswith("py:"):
        return f"src/skytrace/{p[3:]}.py"
    if p.startswith("js:"):
        return f"web/js/{p[3:]}.js"
    return p


def _ver(v):
    if not v:
        return "—"
    k, _, name = v.partition(":")
    if k in TESTS:
        return TESTS[k] + (f"::{name}" if name else "")
    return v


def build() -> dict:
    info = {d[0]: d for d in DOMAINS}
    rows, cur = [], None
    for line in (r.strip() for r in ROWS.strip().split("\n")):
        if line.startswith("# "):
            cur = line[2:]
            assert cur in info, cur
        elif line:
            rows.append((cur, line))
    assert len(rows) == 600, len(rows)
    items = []
    for n, (dname, line) in enumerate(rows, 1):
        parts = (line.split("|") + [""] * 10)[:10]
        name, prob, cap, data, cx, st, ev, ver, val, risk = parts
        dom, value, drisk, deps = info[dname]
        evidence = [_path(p) for p in ev.split(";") if p]
        mods = sorted({p.split("/")[-1].rsplit(".", 1)[0] for p in evidence if p.startswith(("src/", "web/js/"))})
        items.append({"id": f"P9-{n:03d}", "number": n, "domain": dom, "name": name, "research_problem": prob, "proposed_capability": cap,
                      "scientific_value": value, "required_data": data, "dependencies": mods or [deps], "complexity": COMPLEXITY[cx],
                      "validation": val or DEFAULT_VALIDATION[st], "risks": risk or drisk, "category": st, "status": CATEGORY[st],
                      "evidence": evidence, "verification": _ver(ver)})
    c = Counter(x["category"] for x in items)
    counts = {"concepts": len(items), "domains": len(DOMAINS), "by_category": {f"{k} {CATEGORY[k]}": c[k] for k in CATEGORY},
              "by_complexity": dict(Counter(x["complexity"] for x in items))}
    return {"schema": "skytrace.phase9_catalogue/1", "categories": CATEGORY, "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    out = ["# Skytrace Phase 9 capability catalogue", "",
           "Generated by `python scripts/phase9_catalogue.py`; counts are computed. Checked by `tests/unit/test_phase9_catalogue.py` (600 distinct "
           "concepts in 50 domains, every field present, every A concept cites existing evidence and an existing test, B/C/D concepts cite none).", "",
           "This is a research roadmap, not a build list. **A** means implemented and tested in 0.9 or earlier; **B** implementable now with the "
           "available infrastructure (not built); **C** needs data, integrations or infrastructure named in *required data*; **D** speculative or "
           "outside the current scope (several D concepts are deliberate refusals, such as completeness percentages and probabilistic hypothesis "
           "statuses).", "",
           f"**{c['concepts']} concepts in {c['domains']} domains.** " + ", ".join(f"{v} {k}" for k, v in c["by_category"].items()) + ".", "",
           "| Domain | A | B | C | D |", "|---|---:|---:|---:|---:|"]
    for dom, *_ in DOMAINS:
        n = Counter(x["category"] for x in cat["items"] if x["domain"] == dom)
        out.append(f"| {dom} | {n['A']} | {n['B']} | {n['C']} | {n['D']} |")
    out.append("")
    for dom, value, risk, deps in DOMAINS:
        xs = [x for x in cat["items"] if x["domain"] == dom]
        out += [f"## {dom}", "", f"*Scientific value:* {value}. *Typical risk:* {risk}. *Dependencies:* {deps}.", "",
                "| ID | Capability | Cat. | Research problem | Proposed capability | Required data | Complexity | Validation | Risks | Evidence / test |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for x in xs:
            ev = (", ".join(f"`{e}`" for e in x["evidence"]) + f"; `{x['verification']}`") if x["category"] == "A" else "—"
            out.append(f"| {x['id']} | {x['name']} | {x['category']} | {x['research_problem']} | {x['proposed_capability']} | {x['required_data']} | "
                       f"{x['complexity']} | {x['validation']} | {x['risks']} | {ev} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "phase9_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "PHASE9_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
