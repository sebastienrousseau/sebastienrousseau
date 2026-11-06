# Every tool runs from uv.lock, hash-checked; --locked fails if the lock is
# out of step with pyproject.toml. smoke needs only the standard library.
RUN := uv run --locked
OUT ?= .live
.PHONY: all live smoke audit manual check lint test drift

all:  ## Regenerate the static assets/ and README.md from profile.toml
	$(RUN) --group build tools/build.py

live:  ## Fetch live data and render the numbers and article panels into $(OUT)
	$(RUN) --group build tools/live.py $(OUT)

smoke:  ## Fetch every image README.md shows and check each is a well-formed SVG (networked)
	python3 tools/smoke.py

audit:  ## Check every locked dependency against known vulnerabilities (networked)
	mkdir -p .cache
	uv export --locked --all-groups --no-emit-project --format requirements-txt --output-file .cache/requirements.txt
	$(RUN) --group audit pip-audit --cache-dir .cache/pip-audit --strict --require-hashes --disable-pip -r .cache/requirements.txt

manual:  ## Build the manual into _site/ with the latest ssg (version in .github/ssg-version)
	python3 tools/manual.py prepare
	ssg build -q -f docs-site/ssg.toml
	python3 tools/manual.py finish

lint:
	$(RUN) --group lint ruff check --no-cache tools tests
	$(RUN) --group lint ruff format --no-cache --check tools tests
	$(RUN) --group lint complexipy tools tests --max-complexity-allowed 15
	$(RUN) --group lint python tools/ceilings.py tools tests
	shellcheck tools/*.sh
	$(RUN) --group lint actionlint .github/workflows/*.yml

test:
	$(RUN) --group build --group test python -m pytest -q -p no:cacheprovider tests

drift: all  ## Fail when the committed README.md or assets/ differ from a fresh build
	@changed="$$(git status --porcelain -- README.md assets)"; \
	if [ -n "$$changed" ]; then echo "Out of date; run make and commit:"; echo "$$changed"; exit 1; fi

check: lint test drift  ## The single gate CI runs
