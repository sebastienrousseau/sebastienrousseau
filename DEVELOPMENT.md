# Development

This repository generates a GitHub profile: `README.md` and the SVG panels
in `assets/`, from `profile.toml`. Both are generated, so edit `profile.toml`
or `tools/` and regenerate. How the pieces fit is in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

* [uv](https://docs.astral.sh/uv/), which supplies Python 3.12 or newer and
  every pinned library.
* `make`, `curl`, `git`, `jq` and `shellcheck`.
* `gh` only for `make live` against real registries and for the refresh
  scripts.

## Everyday commands

| Command | What it does |
| --- | --- |
| `make` | Rebuild `README.md` and `assets/` from `profile.toml`. |
| `make check` | The single gate CI runs: lint, tests, and a check that the committed files match a fresh build. |
| `make lint` | ruff, ruff format, complexipy (ceiling 15), shellcheck, actionlint. |
| `make test` | pytest. No network is used. |
| `make drift` | Rebuild, then fail if `README.md` or `assets/` changed. |
| `make live OUT=/tmp/live` | Fetch the live numbers and articles and render them into `OUT`. Hits the real registries. |

`make check` needs the network only to download the two pinned font files on
a first run. They are verified by SHA-256 and cached in `.cache/fonts/`.

## Changing things

* **Copy, cards, links:** edit `profile.toml`, run `make`, commit the
  regenerated `README.md` and `assets/` with it. CI fails if they disagree.
* **A panel's layout:** `tools/panels.py`. Text is measured with the real
  font metrics in `tools/fonts.py`, so wrapping is exact.
* **A new data source:** add a function to `tools/metrics.py` that returns
  its numbers, register it in `collect()` in `tools/live.py`, and give it a
  band in `BANDS` if its values need a sanity check.
* **New fonts on the site:** the build stops on a SHA-256 mismatch. Update
  `PINS` in `tools/fonts.py` on purpose, then `make` and commit every
  regenerated SVG.
* **Dependencies:** versions are pinned in the `Makefile` (`DEPS`, ruff,
  complexipy, pytest, actionlint-py) and in the workflows (actions by
  SHA). Move a pin and run `make check`.

## Tests

`tests/` runs offline. Network calls are stubbed at `metrics.get_json` and
`net._once`, and `tools/commit.sh` runs against a stub `gh` in a throwaway
git repository.

## Release flow

All work for the next version goes on `feat/v<next>`, one pull request at a
time into `main`, CI green before merge. Versions step by 0.0.1. Add a
`CHANGELOG.md` entry with each change. `main` is protected: signed commits,
pull request, and the `check` status required.

The refresh workflow never writes to `main`. It writes only to the
`profile-data` branch.

## Running the refresh by hand

```sh
gh workflow run refresh.yml
```

Set the `accept` input to true only after reading the previous run's summary,
to publish a value that the plausibility bands held back.
