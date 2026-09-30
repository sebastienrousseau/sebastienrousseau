UV := uv run --no-project --with fonttools --with brotli
.PHONY: all check lint

all:  ## Regenerate assets/ and README.md from profile.toml
	$(UV) tools/build.py

lint:
	uvx ruff check tools
	uvx ruff format --check tools
	uvx complexipy tools --max-complexity-allowed 15

check: lint all  ## The single gate CI runs
