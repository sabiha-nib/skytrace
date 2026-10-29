# Skytrace — common commands. Every target works without network access except `acquire`, `live` and `smoke`.
PY ?= python3

.PHONY: install run offline test e2e verify fixtures acquire index live smoke release

install:          ## install Skytrace and its dependencies (add astropy for the preferred FITS reader)
	$(PY) -m pip install -e ".[astro,dev]"

run:              ## start the application on http://127.0.0.1:8600
	$(PY) run.py

offline:          ## start with all network use disabled
	OFFLINE=1 $(PY) run.py

test:             ## deterministic unit + API tests
	$(PY) -m pytest

e2e:              ## browser acceptance test (Playwright + Chromium)
	$(PY) -m pytest -m e2e tests/e2e

verify:           ## dependencies, configuration, secrets, bundles, checksums, tests
	$(PY) scripts/verify.py

fixtures:         ## regenerate the SYNTHETIC test bundles
	$(PY) scripts/make_synthetic_fixtures.py

acquire:          ## download real SPHEREx data for all targets (needs network)
	$(PY) scripts/acquire_targets.py --all && $(PY) scripts/build_observation_index.py && $(PY) scripts/verify_data_bundle.py

index:
	$(PY) scripts/build_observation_index.py

live:             ## check the real archive interfaces (needs network)
	$(PY) -m pytest -m live tests/live -s

smoke:            ## check the Meta Model API with your key (needs network)
	$(PY) scripts/meta_smoke_test.py

release:          ## build dist/skytrace-<version>.zip from the committed tree
	$(PY) scripts/make_release.py
