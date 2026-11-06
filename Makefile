DEPS := --with fonttools==4.68.0 --with brotli==1.2.1
UV := uv run --no-project $(DEPS)
OUT ?= .live
.PHONY: all live smoke check lint test drift

all:  ## Regenerate the static assets/ and README.md from profile.toml
	$(UV) tools/build.py

live:  ## Fetch live data and render the numbers and article panels into $(OUT)
	$(UV) tools/live.py $(OUT)

smoke:  ## Fetch every image README.md shows and check each is a well-formed SVG (networked)
	uv run --no-project tools/smoke.py

lint:
	uvx ruff@0.17.4 check --no-cache tools tests
	uvx ruff@0.17.4 format --no-cache --check tools tests
	uvx complexipy@8.3.0 tools tests --max-complexity-allowed 15
	shellcheck tools/*.sh
	uvx --from actionlint-py==1.7.12.25 actionlint .github/workflows/*.yml

test:
	$(UV) --with pytest==9.2.0 python -m pytest -q -p no:cacheprovider tests

drift: all  ## Fail when the committed README.md or assets/ differ from a fresh build
	@changed="$$(git status --porcelain -- README.md assets)"; \
	if [ -n "$$changed" ]; then echo "Out of date; run make and commit:"; echo "$$changed"; exit 1; fi

check: lint test drift  ## The single gate CI runs
