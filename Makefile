PYTHON ?= python3

.PHONY: check-requirements adopt-spec

check-requirements:
	$(PYTHON) .github/scripts/check_requirements.py

adopt-spec: export FEATURE := $(FEATURE)
adopt-spec:
	@test -n "$$FEATURE" || (echo "Usage: make adopt-spec FEATURE=specs/NNN-feature-name" >&2; exit 2)
	$(PYTHON) .github/scripts/adopt_spec.py "$$FEATURE"
