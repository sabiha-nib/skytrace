"""Phase 10 innovation catalogue: 800 possible scientific capabilities in more than 60 domains — a future innovation map, not a
build list. For every idea it records the ten fields the Phase 10 brief asks for: name, scientific problem, user value, technical
design, required inputs, dependencies, complexity, scientific limitations, validation strategy and implementation status.

    python scripts/phase10_catalogue.py      # writes docs/phase10_catalogue.json and docs/PHASE10_CATALOGUE.md

Composition, stated plainly: 600 ideas are carried over from the Phase 9 catalogue (scripts/phase9_catalogue.py) and re-classified
where 0.10 changed their status; 200 are new in Phase 10, in 15 new domains and five existing ones. Nothing was implemented to
raise the implemented count.

Classes   A implemented and tested (cites existing evidence files and an existing test function; both are checked)
          B feasible with the current infrastructure (not built; claims no evidence)
          C requires additional infrastructure or verified integrations (named in 'required inputs')
          D speculative or outside the current scope (several are deliberate refusals)
New rows  grouped under "# <domain>" lines: name | scientific problem | user value | technical design | required inputs |
          complexity (L/M/H) | class | evidence (";"-separated; py:x = src/skytrace/x.py, js:x = web/js/x.js, other paths as given) |
          verifying test (P10: test_phase10, A: test_api, C: e2e test_controls, F: test_frontier, E: test_epistemic, I: test_intelligence,
          R: test_research_os, S: test_research_session) | scientific limitation (optional)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = {"A": "implemented and tested", "B": "feasible with current infrastructure", "C": "requires additional infrastructure or verified integrations",
           "D": "speculative or outside current scope"}
COMPLEXITY = {"L": "low", "M": "medium", "H": "high"}
TESTS = {"P10": "tests/unit/test_phase10.py", "A": "tests/integration/test_api.py", "C": "tests/e2e/test_controls.py", "F": "tests/unit/test_frontier.py",
         "E": "tests/unit/test_epistemic.py", "I": "tests/unit/test_intelligence.py", "R": "tests/unit/test_research_os.py", "S": "tests/unit/test_research_session.py"}
VALIDATION = {"A": "the cited test, run in the release suite",
              "B": "known-answer tests on synthetic fixtures with documented ground truth before the capability is offered",
              "C": "validation against the named external resource once it is connected and verified, with an independent cross-check",
              "D": "not defined: a validation strategy is part of bringing the idea into scope"}

# new domains: (domain, user value, typical limitation, dependencies)
NEW_DOMAINS = [
    ("Multilingual NLP", "researchers work in their own language", "machine translation can shift meaning", "translation dictionaries; script-aware rendering"),
    ("Cross-language retrieval", "records found whatever language they were searched in", "keyword mapping misses paraphrase", "terminology base; normalisation"),
    ("Scientific terminology", "terms used consistently across languages", "a term base frozen before expert review", "term base; review workflow"),
    ("Translation quality assurance", "translation errors found before users meet them", "automatic checks cannot judge fluency", "catalogue; quality checks"),
    ("Radio astronomy", "radio context for infrared sources", "different beams and epochs are not directly comparable", "radio catalogues; cross-matching"),
    ("Gravitational-wave science", "electromagnetic follow-up of GW events", "large sky areas make association weak", "alert streams; sky maps"),
    ("Galactic dynamics", "motions placed in a Galactic context", "proper motions alone do not give 3-D velocities", "distances; radial velocities"),
    ("Transient astronomy", "changes caught and characterised quickly", "sparse cadence misses short events", "alert brokers; dense photometry"),
    ("Model selection", "models compared under stated assumptions", "a criterion used where its assumptions fail", "fits; residual diagnostics"),
    ("Digital twins", "computational stand-ins that state what they model", "a simulation mistaken for the sky", "generators; validation data"),
    ("Data governance", "who may see, change and share what is explicit", "governance implying controls that do not exist", "accounts; policies"),
    ("Data interoperability", "work moves between tools without loss", "formats that drop provenance", "versioned schemas"),
    ("Distributed scientific computing", "heavy work runs where resources are", "distribution adding failure modes", "job runners; storage"),
    ("Research ethics", "research done with care for people and data", "ethics reduced to a checkbox", "policies; review"),
    ("Computational mathematics", "numerics that are stable and checked", "silent numerical failure", "numerical libraries; tests"),
]

ROWS = """
# Multilingual NLP
Six-language interface|science is excluded by language|use Skytrace in Bangla, Hindi, Spanish, French, German or English|gettext-style catalogue keyed by English text; DOM translator for rendered text and attributes; patterns keep substituted values|catalogue; language files|H|A|js:i18n;scripts/i18n_extract.py;web/i18n/catalog.json|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders|translations are machine-made and unreviewed
Language persistence|a language chosen once should stay|the interface remembers the language across navigation, restarts and sessions|localStorage, URL override and session preferences|browser storage; session schema|L|A|js:i18n;js:settingsui;py:session|C:test_l1_language_switch_persists_and_localises
Plural rules per language|counts read wrongly with English plurals|counts phrased correctly in each language|keyed messages with Intl.PluralRules categories|keyed messages|L|A|js:i18n;web/i18n/en.json|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
Locale number formatting|decimal separators differ by language|numbers read naturally with digits kept exact|Intl.NumberFormat with the number of decimals preserved; Western-digit option|recorded numbers|M|A|js:i18n;js:settingsui|C:test_l1_language_switch_persists_and_localises
Script-aware fonts|Bangla and Devanagari need fonts with conjuncts|text renders without broken glyphs|Noto Sans Bengali and Devanagari subsets with unicode-range|font files (OFL)|L|A|web/fonts/OFL.txt;web/css/app.css|P10:test_bangla_and_hindi_translations_use_their_own_scripts
Machine-translation labelling|readers must know a translation is unreviewed|every translated view and report says how it was translated|status, translator and review flag in each language file and report header|language files|L|A|py:i18n;js:settingsui|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
Recorded text kept in its language|engine statements are scientific content|statements stay exactly as computed|recorded engine text excluded from translation and marked lang=en|records|L|A|py:report;js:languagesui|P10:test_report_in_six_languages_keeps_every_number_and_engine_statement
Server-side message marking|reports need the same dictionaries as the interface|reports and exports translated with one catalogue|_t() calls extracted into the catalogue|server code|L|A|py:i18n;scripts/i18n_extract.py|P10:test_server_translation_matches_marked_messages
Right-to-left support|Arabic and Urdu readers are excluded|interface mirrored for RTL scripts|logical CSS properties and dir=rtl|RTL translations|M|B|||mirroring charts can mislead
Additional languages|six languages still exclude many researchers|more languages from the same catalogue|new language files through the same pipeline|translators or reviewed MT|M|B|||each language needs review
Human translation review workflow|machine translations need native review|reviewed strings marked and versioned|review status per message|native-speaker reviewers|M|C
Model-assisted retranslation|catalogue grows faster than translators|draft translations proposed for review|translation model behind the review gate|a verified translation model|M|C|||drafts never shipped unreviewed
Speech output of explanations|reading is a barrier for some users|explanations read aloud in six languages|text-to-speech of keyed explanations|speech engines per language|M|C
# Cross-language retrieval
Terminology-mapped search|a Bangla query should find English records|search in any of six languages|query terms mapped through TERM-1 to canonical English and the interface language|terminology base|M|A|py:xsearch;js:xsearch;web/i18n/terms.json|P10:test_cross_language_search_maps_terms_and_never_claims_semantics
Labelled retrieval layers|users must know how a result matched|each result says exact text, terminology or words|three ordered layers with the method label|query; documents|L|A|py:xsearch;js:xsearch|P10:test_cross_language_search_maps_terms_and_never_claims_semantics
Script detection|queries mix scripts|the query's script reported|Unicode block counts|query|L|A|py:xsearch|P10:test_cross_language_search_maps_terms_and_never_claims_semantics
Diacritic-insensitive matching|é and e should match|accent-insensitive Latin search|NFKC, NFD and combining-mark removal|query|L|A|py:xsearch;js:xsearch|P10:test_cross_language_search_maps_terms_and_never_claims_semantics
Browser–server search parity|two implementations drift|identical results in the preview and the server|parity test on queries and documents|both implementations|L|A|py:xsearch;js:xsearch|P10:test_browser_translation_search_and_handoff_match_python
Cross-language command palette|commands should be found in any language|the palette accepts queries in six languages|palette documents include translated labels and the term base|palette commands|L|A|js:palette;js:xsearch|C:test_l1_language_switch_persists_and_localises
Stem matching for inflections|inflected forms miss exact matches|German compounds and plurals found|shared stems of five or more letters|term base|L|A|py:xsearch|P10:test_cross_language_search_maps_terms_and_never_claims_semantics
Semantic retrieval with embeddings|paraphrases are missed by keywords|meaning-level search|multilingual embedding model with an evaluation set|a verified embedding model|H|C|||never labelled semantic without a model
Transliteration search|users type Bangla or Hindi in Latin letters|romanised queries matched|transliteration tables per script|transliteration rules|M|B
Cross-language record linking|records in different languages describe one object|related records linked|identifier and term overlap with stated rules|multilingual records|M|B
Relevance evaluation set|retrieval quality is unmeasured|precision and recall per language|labelled query–record pairs|annotators|M|C
Query translation by a model|free text beyond the term base|wider coverage|model translation of the query, shown to the user|a verified translation model|M|C
Search across the literature|related work is outside Skytrace|indexed literature searched in six languages|literature index connector|a literature API and terms|H|C
# Scientific terminology
Six-language term base|technical terms are translated inconsistently|one agreed term per language with synonyms|TERM-1 file generated from a reviewed source|term list|M|A|scripts/i18n_terms.py;web/i18n/terms.json|P10:test_terminology_base_covers_six_languages_with_definitions_and_pronunciation|terms not yet reviewed by domain experts
Definitions in every language|terms need meaning, not just words|definition, context and units per term|definitions per language|term base|M|A|scripts/i18n_terms.py|P10:test_terminology_base_covers_six_languages_with_definitions_and_pronunciation
Pronunciation guides|Bangla and Hindi readers meet transliterated terms|romanised pronunciation|transliteration per term|term base|L|A|scripts/i18n_terms.py|P10:test_terminology_base_covers_six_languages_with_definitions_and_pronunciation
Units and symbols kept|units must not be translated|µm, mas, σ and method identifiers unchanged|checks that every unit in a definition survives translation|term base|L|A|scripts/i18n_terms.py|P10:test_terminology_base_covers_six_languages_with_definitions_and_pronunciation
Terminology consistency check|one term translated two ways confuses readers|inconsistencies listed for review|messages containing a term checked for its accepted forms|catalogue; term base|M|A|py:i18n|P10:test_quality_observatory_counts_and_terminology_consistency
Terminology browser|learners need the vocabulary|a table of terms in six languages|terms table with definitions by context|term base|L|A|js:languagesui|C:test_l2_signal_world_and_explanations
Expert review of terms|machine-proposed terms can be wrong|terms marked reviewed by domain experts|review records per term|domain experts per language|M|C
Term provenance|where did a translation come from?|each term cites its source glossary|source fields per term|published glossaries|M|C
IAU nomenclature links|object names follow conventions|names checked against IAU rules|IAU naming references|IAU resources|M|C
Term deprecation history|terms change|old terms kept with dates|versioned term entries|term base|L|B
Glossary export|teachers want handouts|glossary exported per language|term base to Markdown or CSV|term base|L|B
Term-aware writing assistant|notes use loose terms|notes checked against the term base|term matching on notebook text|term base; notes|M|B
# Translation quality assurance
Completeness test|untranslated strings slip through|release blocked by missing translations|every catalogue key present in every language|catalogue; language files|L|A|py:i18n;scripts/i18n_merge.py|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
Placeholder validation|broken placeholders corrupt values|values always land in translations|same placeholders required at merge and in tests|catalogue|L|A|scripts/i18n_merge.py|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
Number preservation check|translations may alter numbers|numbers identical across languages|digit sequences compared per message|catalogue|L|A|py:i18n|P10:test_translations_keep_numbers_and_method_identifiers
Identifier preservation check|method identifiers must survive|WLMATCH-2 stays WLMATCH-2|identifier patterns compared|catalogue|L|A|py:i18n|P10:test_translations_keep_numbers_and_method_identifiers
Unicode hygiene|broken characters and non-normalised text|clean NFC text without replacement characters|NFC and control-character checks|language files|L|A|py:i18n|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
Native-script check|a Bangla string in Latin letters is untranslated|untranslated prose found|script-block test on prose messages|language files|L|A|py:i18n|P10:test_bangla_and_hindi_translations_use_their_own_scripts
Quality observatory|translation state is invisible|counts per language in the interface|I18N-Q1 generated file plus runtime missing list|quality.json|M|A|py:i18n;scripts/i18n_quality.py;js:languagesui|P10:test_quality_observatory_counts_and_terminology_consistency
Live overflow check|longer translations overflow boxes|clipped text listed for the current page|scrollWidth checks on visible labels|rendered page|L|A|js:languagesui|C:test_l2_signal_world_and_explanations
Generated files kept current|stale catalogues ship|the build refuses stale translation files|--check modes for extract, terms and quality|scripts|L|A|scripts/i18n_extract.py;scripts/i18n_terms.py;scripts/i18n_quality.py|P10:test_generated_i18n_files_are_up_to_date
Visual regression per language|layout breaks in one language only|screenshots compared between releases|pixel or DOM diff per language and width|baseline screenshots|M|B
Back-translation spot checks|meaning drift is invisible to counts|samples back-translated and compared|model back-translation with human review|a translation model; reviewers|M|C
Fluency rating by native speakers|automatic checks miss awkwardness|rated samples per language|review forms|native reviewers|M|C
Translation memory|repeated phrases translated differently|consistent reuse|segment store with fuzzy matching|catalogue history|M|B
# Radio astronomy
Radio counterpart lookup|infrared sources may have radio emission|radio fluxes beside SPHEREx results|cone search of radio surveys with provenance|NVSS/FIRST/VLASS access|M|C
Radio variability context|radio variability supports some explanations|radio light curves where available|survey epochs compared with stated beams|multi-epoch radio surveys|H|C
Spectral index across bands|radio–IR SEDs constrain emission|spectral indices with errors|matched photometry across bands|radio and IR photometry|M|C|||beam mismatch biases indices
Beam-matched comparisons|different resolutions confuse comparison|comparisons only at matched resolution|convolution to a common beam|images with beams|H|C
Radio frequency interference flags|RFI mimics signals|RFI-affected data excluded with reasons|RFI masks from archives|archive flags|M|C
Radio transient alerts|radio transients need IR follow-up|alerts linked to targets|alert stream connector|a verified alert stream|H|C
Pulsar timing context|pulsars give distances and motions|timing solutions for matched sources|pulsar catalogues|ATNF catalogue|M|C
Interferometric image ingestion|radio images need different handling|visibility-based images read with metadata|FITS readers with beam metadata|interferometric products|H|D
Radio–infrared astrometric tie|frames differ slightly|frame offsets checked|matched positions|radio and Gaia positions|M|C
Radio source morphology classification|extended sources need classes|morphology labels with uncertainty|trained classifiers|labelled radio images|H|D
Synthetic radio–IR scenarios|methods need ground truth|generated multi-band scenarios|generator extension|generator|M|B
Radio data provenance|radio products have complex pipelines|pipeline versions recorded|provenance fields|archive metadata|L|B
# Gravitational-wave science
GW alert sky-map overlap|does a target fall in a GW localisation?|overlap probability from the published sky map|HEALPix sky-map reading|GW alert sky maps|M|C|||overlap is not association
Counterpart candidate vetting|many candidates follow each alert|candidates ranked by stated rules|cross-match and light-curve checks|alerts; dense photometry|H|C
Kilonova colour evolution checks|kilonovae redden quickly|colour evolution against models|multi-band photometry|rapid photometry|H|D
GW–EM timing windows|association needs time coincidence|time windows stated per hypothesis|alert times|alert stream|L|C
Distance consistency|GW distance versus host distance|consistency test with both errors|GW distance posteriors; host redshifts|catalogues; alerts|M|C
Archival pre-imaging|was the source there before?|pre-event images found|archive search by time|archive access|M|C
Negative follow-up records|non-detections constrain models|non-detections recorded with limits|NEGX-1 distinctions for follow-up|follow-up data|M|B|||a non-detection is not absence
Alert stream adapter|alerts need verified sources|alerts read with provenance|connector with retrieval time|GCN/IGWN access|M|C
Synthetic GW counterpart scenarios|vetting rules need tests|generated counterparts with known truth|generator|generator|M|B
Rate-based priors|association priors depend on rates|stated rate assumptions|rate tables|published rates|H|D
Multi-messenger handoff|teams need shared records|handoffs with alert identifiers|HANDOFF-1 extension|alerts|L|B
Detector-noise context|GW data quality affects localisation|data-quality flags shown|flag ingestion|IGWN data-quality products|M|D
Population context|single events need population context|population model comparison|population catalogues|GWTC catalogues|H|D
# Galactic dynamics
Tangential velocity with distance|proper motion needs distance for velocity|v_tan with propagated errors when a parallax is recorded|parallax and proper motion|Gaia parallaxes|L|B|||no 3-D velocity without a radial velocity
Galactic coordinate context|positions need Galactic context|l, b and motion in Galactic frame|frame transformation|positions|L|B
Population membership hints|kinematic groups suggest populations|stated kinematic criteria|velocity ellipsoids|distances; radial velocities|M|C|||membership is probabilistic and model-based
Orbit integration|where has a star been?|orbits in a stated potential|integrator and potential model|6-D phase space|H|D
Moving-group matching|co-moving stars share origins|candidates by stated motion criteria|catalogue cross-match|Gaia catalogue access|M|C
Reflex-motion correction|solar motion biases proper motions|corrections with stated solar parameters|solar motion parameters|positions; distances|M|B
High-velocity star flags|unusual velocities need checks|flags with the rule that fired|velocity thresholds|distances|L|B
Extinction-aware photometry|dust changes colours|extinction with stated maps|3-D dust maps|dust map access|M|C
Disk–halo classification|kinematics separate populations|classification rules stated|velocity criteria|full kinematics|M|D
Proper-motion catalogue comparison|measured motion versus catalogues|differences with significance|catalogue values|catalogue|L|A|py:analysis;py:view|E:test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit
Wide-binary detection|companions share motion|pairs by common proper motion|catalogue cross-match|Gaia access|M|C
Galactic potential sensitivity|orbits depend on the potential|orbits under several potentials|integrator|6-D phase space|H|D
Synthetic kinematic scenarios|kinematic rules need tests|generated stars with known motions|generator|generator|M|B
# Transient astronomy
Single change-point detection|a source may switch level|the most likely switch between observations with Δχ²|two-segment constant model at gaps only|light curve|M|A|py:sigintel|P10:test_signal_methods_known_answers|one change point; location only between observations
Transient alert broker adapter|alerts arrive from brokers|alerts read with provenance and retrieval time|broker connector|a verified broker API|M|C
Rapid classification with uncertainty|transients need early classes|class probabilities from a validated classifier|trained classifier|labelled transients|H|D
Pre-discovery light curves|did the transient brighten before?|archival photometry before the alert|archive search by time|archive access|M|C
Host association|transients need hosts|host candidates by stated separation rules|galaxy catalogues|catalogue access|M|C
Cadence adequacy check|can these data catch the event timescale?|timescales the sampling can resolve|sampling diagnostics|sampling times|L|A|py:sigintel|P10:test_signal_workbench_on_a_record_never_interpolates
Discovery Radar sources registry|monitoring needs registered sources|sources listed with connection state|EXTSRC-1 registry; nothing shown unless connected|source list|L|A|py:universal;js:universalui|P10:test_opportunities_sources_compiler_agents_director_and_market_stay_honest
Monitoring interests in sessions|researchers want to follow sources|interest recorded without contacting anyone|session monitors field|session|L|A|py:session;js:universalui|C:test_l4_phase10_sections_in_existing_workspaces
Live monitoring with deduplication|updates repeat across sources|deduplicated update history|connector polling with change detection|verified connectors|H|C|||no update without a connector
Transient light-curve fitting|transients have templates|template fits with residuals|template library|dense photometry|H|C
Follow-up prioritisation|follow-up time is scarce|ranked follow-up by stated rules|rule set|alerts; feasibility|M|B
Negative-space for transients|missed transients bias rates|recorded gaps and non-detections|NEGX-1 for monitoring|sampling|L|B
Alert provenance audit|alerts are revised|revisions kept with times|append-only alert log|alert stream|M|C
# Model selection
BIC with assumption checks|criteria used where assumptions fail|BIC shown only when N and χ²ν checks pass|assumption checks before BIC|fits with errors|M|A|py:sigintel|P10:test_bic_only_when_assumptions_hold
Multi-criteria model table|one score hides trade-offs|fit, residuals, parameters and meaning side by side|table without a single ranking|fits|L|A|py:sigintel;js:universalui|P10:test_bic_only_when_assumptions_hold
Robust trend against least squares|outliers pull fits|Theil–Sen beside weighted least squares|median of pairwise slopes|series|L|A|py:sigintel|P10:test_signal_methods_known_answers
Static versus linear motion|is it moving?|nested models with χ² and AIC|model arena|visit positions|M|A|py:modelarena|E:test_model_arena_compares_nested_models_and_reproduces_the_pipeline_fit
Cross-validation of models|criteria assume asymptotics|held-out prediction error|leave-one-out refits|series with enough points|M|B
Bayesian evidence|nested sampling gives evidence ratios|evidence with prior sensitivity|nested sampler|explicit priors; samplers|H|C|||evidence depends on priors
Likelihood-ratio tests for nested models|nested models need a test with a known null distribution|Δχ² compared with χ² for Δk degrees of freedom where Wilks' theorem applies|nested fits with stated errors|fits|L|B|||invalid at parameter-space boundaries
Residual autocorrelation tests|correlated residuals invalidate χ²|autocorrelation of residuals with lags|DCF on residuals|residuals|M|B
Overfitting diagnostics|extra parameters always fit better|Δk-aware comparisons and validation|criteria plus validation|fits|M|B
Model assumption registry|assumptions are scattered|each model lists its assumptions|registry entries|models|L|B
Gaussian-process models|stochastic variability needs flexible models|GP fits with stated kernels|GP library|dense series|H|C
Model comparison across runs|choices change model preference|preference per run with parameters|sibling runs|runs|M|B
Information criteria for photometric groups|which brightness model?|constant, linear, step compared per group|SIGNAL-1 model comparison|photometry groups|L|A|py:sigintel|P10:test_signal_workbench_on_a_record_never_interpolates
# Digital twins
Synthetic observatory as a scenario model|methods need data with known truth|generated observations with stated assumptions|SYNOBS-1 generator with fixed stamp|generator parameters|M|A|py:synthobs|F:test_synthetic_scenarios_are_labelled_deterministic_and_known_answer|a generator, not a physically validated twin
Scenario variation with seeds|single scenarios pass by luck|verdict stability across seeds|SIMCHECK-1|generator|L|A|py:simcheck|E:test_simulation_audit_refuses_invalid_scenarios
Observation-schedule twins|which schedule detects more?|schedules compared on one truth|SYNOBS design comparison|generator|M|A|py:synthobs|F:test_observation_design_compares_schedules
Counterfactual re-assessment|what if a choice changed?|isolated scenarios that never overwrite|CF-1|recorded investigation|M|A|py:counterfactual|F:test_counterfactuals_are_isolated_and_labelled
Instrument model twin|the instrument shapes data|a model of the LVF, PSF and noise per detector|instrument model|SPHEREx instrument characterisation|H|C|||unvalidated models are not twins
Twin validation against real data|twins need checking|twin outputs compared with archive data|comparison suite|real archive data|H|C
Twin versioning|twins change|versions with assumptions|versioned scenario records|generator|L|B
Physical source twins|sources have physics|stellar models generating light curves|stellar models|model grids|H|D
Twin uncertainty propagation|twin outputs need errors|parameter uncertainty propagated|Monte Carlo over parameters|generator|M|B
Twin labelling in exports|simulations must not pass as observations|every twin output labelled simulated|labels in exports|exports|L|A|py:synthobs;py:universal|P10:test_multimodal_rows_keep_units_and_compatibility_rules
Twin-based method benchmarks|methods need benchmarks|benchmark suite of scenarios|scenario library|generator|M|B
Twin comparison dashboards|many scenarios are hard to compare|side-by-side scenario outcomes|scenario tables|scenarios|L|B
# Data governance
Sessions without accounts stated|governance claims need honesty|it is said that Skytrace has no user accounts|explicit statements in the interface|interface|L|A|js:universalui;py:session|S:test_session_new_validates_and_hashes
Never publish automatically|private work must stay private|exports are downloads only|no publish action exists|interface|L|A|js:universalui|C:test_l3_gateway_handoff_reports_and_recorder
Licence declaration check|sharing needs a licence|missing licence flagged before sharing|OSG-1 checklist|repository metadata|L|A|js:universalui|C:test_l3_gateway_handoff_reports_and_recorder|the check cannot choose a licence
Access control by role|shared deployments need roles|roles for viewing and editing|authentication and authorisation|identity provider|H|C
Data retention policy|data kept indefinitely|stated retention with deletion|policy and jobs|storage|M|B
Audit of exports|who exported what?|export events in the session history|history entries for exports|session|L|A|js:universalui;py:session|C:test_l3_gateway_handoff_reports_and_recorder
Consent records for shared data|shared data may involve people|consent tracked where relevant|consent fields|policies|M|D
Dataset licence propagation|licences must follow data|licence of each source shown in reports|archive licence metadata|archive terms|M|C
Private notes separation|notes may be private|notes excluded from exports by choice|export filters|session|L|B
Credential isolation|keys must never reach the browser|keys only from the server environment|environment-only configuration|server|L|A|py:ai/meta_client|A:test_status_and_security_headers
Data deletion with history|deletion must be visible|deletions logged, never silent|append-only history|session|L|B
Multi-tenant isolation|one deployment for many teams|isolated storage per team|tenant separation|server infrastructure|H|C
Governance documentation|rules must be readable|governance in plain language|docs|policies|L|B
# Data interoperability
Versioned handoff schema|work moves between people and tools|skytrace.handoff/1 with digest and language metadata|HANDOFF-1 build and validation|investigation; universal report|M|A|py:handoff;js:handoff|P10:test_handoff_round_trip_and_validation
Handoff import validation|imported files may be edited or wrong|edits and mislabels refused with reasons|digest, schema and synthetic-label checks|handoff files|L|A|py:handoff;js:handoff;js:universalui|C:test_l3_gateway_handoff_reports_and_recorder
Handoff parity|preview and server must agree|identical handoffs from both|parity test|both implementations|L|A|py:handoff;js:handoff|P10:test_browser_translation_search_and_handoff_match_python
Open-science bundle|sharing needs a complete package|record, reports, handoff and checklist in one ZIP|OSG-1 bundle|record|M|A|js:universalui;js:zipstore|C:test_l3_gateway_handoff_reports_and_recorder
Common measurement representation|modalities use different shapes|one row shape with units and sources|MODAL-1|record|M|A|py:universal|P10:test_multimodal_rows_keep_units_and_compatibility_rules
Columnar measurement tables|large measurement sets are slow as JSON|CSV and Parquet exports with units|columnar writers with unit metadata|measurements|L|B
IVOA provenance model|provenance should follow standards|provenance in IVOA form|mapping to the provenance data model|provenance|H|B
RO-Crate packages|research objects need standard packaging|RO-Crate metadata in bundles|crate writer|bundle|M|B
Notebook export|analysts use notebooks|reproduction notebook generated|notebook template|record|M|B
DOI minting|citable outputs need identifiers|DOIs for bundles|DataCite integration|DataCite account|M|C
Schema registry|schemas evolve|documented, versioned schemas|registry docs|schemas|L|B
Import from other tools|other tools produce records|importers for known formats|parsers|external formats|M|C
Interoperability tests|formats drift|round-trip tests per format|test suite|formats|L|B
# Distributed scientific computing
Batch analysis of many targets|one target at a time does not scale|queued analyses with progress|job queue|workers|H|C
Cached reports by content hash|recomputing is slow|reports cached by hash, never by name|content-hash caches|server|L|A|py:server/universal;py:server/intelligence|A:test_phase10_universal_and_multilingual_report
Static preview as precomputed compute|hosting without a server|results precomputed and labelled|build_static recording|server at build time|M|A|scripts/build_static.py;js:static/backend|C:test_l2_signal_world_and_explanations
Remote workers for heavy fits|PSF fits are heavy|remote execution with provenance|worker protocol|compute resources|H|C
Reproducible environments|results depend on software|environment manifests per run|REPRONET-1 manifest|environment|L|A|py:repronet|I:test_reproduction_manifests_validate_and_comparison_classes
Pinned dependency lockfiles|installs drift between machines|identical library versions everywhere|hash-pinned requirement files|package index|L|B
Workflow engines|long pipelines need orchestration|DAG execution with retries|workflow engine|infrastructure|H|C
Result storage service|records live on one machine|shared storage with checksums|object storage|storage service|M|C
Progress feedback for long jobs|long work looks frozen|visible progress|progress events|server|L|B
Interrupted-job recovery|jobs fail midway|resume from checkpoints|checkpointing|storage|M|B
Distributed reproduction network|independent reproductions need other machines|reproductions on independent hardware|REPRONET across hosts|other hosts|H|C
Vectorised periodograms|large frequency grids are slow|fast periodograms for long series|vectorised evaluation checked against the reference loop|long series|M|B
# Research ethics
No fabricated results by construction|pressure to show results|missing data shown as missing|refusals instead of fills|record|L|A|py:universal;py:analysis|P10:test_negative_space_nine_distinctions_say_what_they_do_not_mean
Agent caveat|role agents can look like independent reviewers|agents labelled as rule sets sharing one model|AGENTS-1 caveat|record|L|A|py:universal|P10:test_opportunities_sources_compiler_agents_director_and_market_stay_honest
Novelty honesty|local absence is not global novelty|novelty scoped to what Skytrace holds|OPP-2 scopes|corpus|L|A|py:universal|P10:test_opportunities_sources_compiler_agents_director_and_market_stay_honest
Synthetic data labelling everywhere|test data can leak into claims|synthetic labels in records, reports and handoffs|labels and validation|records|L|A|py:handoff;py:report|P10:test_handoff_round_trip_and_validation
Machine-review labelling|simulated review can pass as peer review|rule-set reviewers named as such|REVIEWX labels|record|L|A|py:reviewx|E:test_review_board_links_every_item
Dual-use review|some analyses have misuse risk|risk notes per capability|review checklist|policy|L|D
Credit and attribution|data providers deserve credit|attribution in every export|provider citations|archive terms|L|B
Bias audits of classifiers|classifiers can encode bias|bias reports per class|evaluation sets|labelled data|M|D
Accessibility as ethics|exclusion by design|accessible interface checks|accessibility tests|interface|L|A|js:main|C:test_l1_language_switch_persists_and_localises
Ethics statement in reports|reports should state limits|limitations and caveats in every report|report sections|records|L|A|py:report|P10:test_report_in_six_languages_keeps_every_number_and_engine_statement
Language equity|English dominance excludes|six languages with equal features|i18n architecture|catalogue|M|A|js:i18n|P10:test_every_message_is_translated_in_every_language_with_identical_placeholders
# Computational mathematics
Generalised Lomb–Scargle|uneven sampling breaks the FFT|weighted, floating-mean periodogram|Zechmeister–Kürster formulas|series with errors|M|A|py:sigintel|P10:test_signal_methods_known_answers|no false-alarm probability is computed
Spectral window|sampling creates aliases|window power beside every periodogram peak|squared modulus of the mean of exp(−2πift) over the sampling times|sampling times|L|A|py:sigintel|P10:test_signal_methods_known_answers
Discrete correlation function|autocorrelation needs uniform sampling|correlation for uneven sampling with pair counts|Edelson–Krolik DCF|series with errors|M|A|py:sigintel|P10:test_signal_methods_known_answers
Haar wavelet energies|signals live on several scales|energy by scale for uniform series|Haar transform on a power-of-two prefix|uniform series|L|B|||implemented but without a known-answer test
Canonical JSON digests|hashes need one byte form|identical digests in Python and the browser|SKY-CANON-1|documents|L|A|py:canon;js:canon|P10:test_browser_translation_search_and_handoff_match_python
Condition-number checks|ill-conditioned fits fail silently|condition numbers reported|linear algebra diagnostics|fits|M|B
Arbitrary-precision checks|float error accumulates|high-precision re-computation of key sums|mpmath checks|numerics|M|B
Interval arithmetic for bounds|bounds need guarantees|rigorous bounds on derived quantities|interval libraries|numerics|H|D
Automatic differentiation|derivatives by hand are error-prone|exact gradients for fits|AD frameworks|models|M|B
Numerical parity across languages|ports drift numerically|tolerance-checked parity tests|parity harnesses|both implementations|L|A|py:xsearch;js:xsearch|P10:test_browser_translation_search_and_handoff_match_python
Robust medians and percentiles|outliers distort means|median-based estimators|Theil–Sen and percentiles|series|L|A|py:sigintel|P10:test_signal_methods_known_answers
Frequency grids with stated resolution|grids that are too coarse miss peaks|oversampled grids from the span|1/(5·span) spacing, capped|sampling|L|A|py:sigintel|P10:test_signal_methods_known_answers
Symbolic checks of formulas|formula typos survive tests|symbolic verification of derivations|computer algebra|formulas|M|D
# Signal processing
Signal workbench on recorded series|time-series methods are applied blindly|methods selected by stated rules with reasons|SIGNAL-1 method selection|recorded series|M|A|py:sigintel;js:universalui|P10:test_signal_workbench_on_a_record_never_interpolates
Wavelength-matched photometry series|LVF wavelengths mix brightness and colour|series at one wavelength per detector|grouping within the WLMATCH-2 tolerance|measurements|M|A|py:sigintel|P10:test_signal_workbench_on_a_record_never_interpolates
# Data provenance
Research flight recorder replay|what happened in a session?|chronological replay with chain verification|session history and VAULT-1|session|L|A|js:universalui;js:sessioncore|C:test_l3_gateway_handoff_reports_and_recorder|tamper-evident, not immutable
Discovery timeline with separate times|observation, processing and publication times get mixed|four lanes kept apart|TIMES-1|record|L|A|py:universal|P10:test_timeline_keeps_four_kinds_of_time_apart
World model with explicit basis|relationships without a basis mislead|every relation cites its rule and field|WORLD-1 with structured query|record|M|A|py:universal;js:universalui|P10:test_world_model_relationships_have_a_basis_and_queries_are_exact
# Reproducibility
Multilingual reports with identical numbers|translation could change results|reports in six languages with the same numbers|_t() wording, values unchanged, metadata header|record|M|A|py:report;py:i18n|A:test_phase10_universal_and_multilingual_report
Convergence by independence|repeated data look like confirmation|independent lines counted by shared exposures|CONV-1 grouping|record|M|A|py:universal|P10:test_convergence_groups_shared_exposures_and_never_counts_repeated_data
# Research automation
Investigation director|automation without approval is unsafe|ordered steps that wait for approval, with an audit log|DIRECT-1 plan and session audit|record; session|M|A|py:universal;js:universalui|C:test_l4_phase10_sections_in_existing_workspaces
Experiment marketplace with validation status|unvalidated methods look recommended|only methods with a named known-answer test are recommended|EXPMKT-1|tests|L|A|py:universal;js:universalui|P10:test_opportunities_sources_compiler_agents_director_and_market_stay_honest
Explanations in eight layers|results need explaining at several depths|observed, measured, how, compared, result, certainty, alternatives, limits|EXPLAIN-1 keyed messages|record|M|A|py:universal;js:languagesui|P10:test_explanations_use_keyed_messages_present_in_every_language
Contradictions as research leads|disagreements get dismissed or dramatised|leads with possible resolutions|LEAD-1|record|M|A|py:universal|P10:test_convergence_groups_shared_exposures_and_never_counts_repeated_data
"""

# Phase 9 ideas whose status Phase 10 changed: name → (class, technical design, evidence, verifying test)
OVERRIDES = {
    "Periodogram with window function": ("A", "generalised Lomb–Scargle with the spectral window beside every peak; no false-alarm probability is computed",
                                          ["src/skytrace/sigintel.py"], "tests/unit/test_phase10.py::test_signal_methods_known_answers"),
    "Localisation": ("A", "gettext-style catalogue in six languages with a DOM translator, keyed plurals and locale numbers",
                     ["web/js/i18n.js", "web/i18n/catalog.json"], "tests/unit/test_phase10.py::test_every_message_is_translated_in_every_language_with_identical_placeholders"),
}


# Phase 9 names that overstated what exists; renamed so the catalogue never claims a capability Skytrace lacks
RENAMES = {"Semantic search across investigations": "Exact and concept-recall search across investigations (no semantic search: no embedding model)"}


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
    return TESTS[k] + (f"::{name}" if name else "") if k in TESTS else v


def _phase9():
    spec = importlib.util.spec_from_file_location("p9cat", ROOT / "scripts" / "phase9_catalogue.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.build()["items"]


def build() -> dict:
    items = []
    for x in _phase9():
        cls, design, evidence, ver = x["category"], x["proposed_capability"], x["evidence"], x["verification"]
        changed = x["name"] in OVERRIDES
        if changed:
            cls, design, evidence, ver = OVERRIDES[x["name"]]
        items.append({"domain": x["domain"], "name": RENAMES.get(x["name"], x["name"]), "scientific_problem": x["research_problem"], "user_value": x["scientific_value"],
                      "technical_design": design, "required_inputs": x["required_data"], "dependencies": x["dependencies"], "complexity": x["complexity"],
                      "scientific_limitations": x["risks"], "validation_strategy": VALIDATION[cls] if changed or cls == "A" else x["validation"],
                      "class": cls, "implementation_status": CLASSES[cls], "evidence": evidence if cls == "A" else [], "verification": ver if cls == "A" else "—",
                      "origin": "Phase 9 catalogue" + (" (re-classified in 0.10)" if changed else "") + (" (renamed in 0.10)" if x["name"] in RENAMES else "")})
    info = {d[0]: d for d in NEW_DOMAINS}
    p9doms = {x["domain"] for x in items}
    cur = None
    for line in (r.strip() for r in ROWS.strip().split("\n")):
        if line.startswith("# "):
            cur = line[2:]
            assert cur in info or cur in p9doms, cur
            continue
        if not line:
            continue
        parts = (line.split("|") + [""] * 10)[:10]
        name, prob, value, design, inputs, cx, cls, ev, ver, lim = parts
        dom = info.get(cur)
        evidence = [_path(p) for p in ev.split(";") if p]
        mods = sorted({p.split("/")[-1].rsplit(".", 1)[0] for p in evidence if p.startswith(("src/", "web/js/"))})
        items.append({"domain": cur, "name": name, "scientific_problem": prob, "user_value": value, "technical_design": design, "required_inputs": inputs,
                      "dependencies": mods or [dom[3] if dom else "existing Skytrace modules"], "complexity": COMPLEXITY[cx],
                      "scientific_limitations": lim or (dom[2] if dom else "stated in the cited method documentation"),
                      "validation_strategy": VALIDATION[cls], "class": cls, "implementation_status": CLASSES[cls],
                      "evidence": evidence, "verification": _ver(ver), "origin": "new in Phase 10"})
    for n, x in enumerate(items, 1):
        x["id"] = f"P10-{n:03d}"
    c = Counter(x["class"] for x in items)
    counts = {"ideas": len(items), "domains": len({x["domain"] for x in items}), "new_in_phase10": sum(x["origin"] == "new in Phase 10" for x in items),
              "reclassified": sum("re-classified" in x["origin"] for x in items),
              "by_class": {f"{k} {CLASSES[k]}": c[k] for k in CLASSES}, "by_complexity": dict(Counter(x["complexity"] for x in items))}
    return {"schema": "skytrace.phase10_catalogue/1", "classes": CLASSES, "fields": ["name", "scientific_problem", "user_value", "technical_design",
            "required_inputs", "dependencies", "complexity", "scientific_limitations", "validation_strategy", "implementation_status"],
            "counts": counts, "items": items}


def markdown(cat: dict) -> str:
    c = cat["counts"]
    doms = list(dict.fromkeys(x["domain"] for x in cat["items"]))
    out = ["# Skytrace Phase 10 innovation catalogue", "",
           "Generated by `python scripts/phase10_catalogue.py`; counts are computed and checked by `tests/unit/test_phase10_catalogue.py`.", "",
           "A future innovation map, not a build list. **A** implemented and tested (evidence files and a verifying test function are cited and "
           "checked to exist); **B** feasible with the current infrastructure (not built); **C** requires additional infrastructure or verified "
           "integrations; **D** speculative or outside the current scope.", "",
           f"**{c['ideas']} ideas in {c['domains']} domains.** {c['new_in_phase10']} are new in Phase 10; the other {c['ideas'] - c['new_in_phase10']} "
           f"carry over from the Phase 9 catalogue, {c['reclassified']} of them re-classified because 0.10 implemented them. "
           + ", ".join(f"{v} {k}" for k, v in c["by_class"].items()) + ".", "",
           "| Domain | A | B | C | D |", "|---|---:|---:|---:|---:|"]
    for d in doms:
        n = Counter(x["class"] for x in cat["items"] if x["domain"] == d)
        out.append(f"| {d} | {n['A']} | {n['B']} | {n['C']} | {n['D']} |")
    out.append("")
    for d in doms:
        out += [f"## {d}", "", "| ID | Name | Class | Scientific problem | User value | Technical design | Required inputs | Dependencies | Complexity | "
                "Scientific limitations | Validation strategy | Evidence / test |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in (i for i in cat["items"] if i["domain"] == d):
            ev = (", ".join(f"`{e}`" for e in x["evidence"]) + f"; `{x['verification']}`") if x["class"] == "A" else "—"
            cells = [x["id"], x["name"], x["class"], x["scientific_problem"], x["user_value"], x["technical_design"], x["required_inputs"],
                     ", ".join(x["dependencies"]), x["complexity"], x["scientific_limitations"], x["validation_strategy"], ev]
            out.append("| " + " | ".join(str(v).replace("|", "/") for v in cells) + " |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    cat = build()
    (ROOT / "docs" / "phase10_catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "PHASE10_CATALOGUE.md").write_text(markdown(cat) + "\n")
    print(json.dumps(cat["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
