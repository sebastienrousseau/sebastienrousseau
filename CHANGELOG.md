# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.12] - Unreleased

### Changed

- `audit` (pip-audit over `uv.lock`) is a required check on `main`
  alongside `check`, so a pull request that locks a dependency with a
  known vulnerability cannot merge. The docs say so.

## [0.0.11] - 2026-11-06

### Added

- A smoke check after every refresh: `make smoke` fetches each image the
  README shows and fails unless it is a well-formed SVG, and unless the
  clock Worker answered directly instead of redirecting to the stopped
  clock. A failure opens the refresh issue.
- Tests that every committed SVG parses, and that the hero keeps the
  selectors and marker the clock Worker relies on.
- `make audit`: pip-audit over every locked dependency, hashes required,
  in CI on every pull request and weekly.

### Fixed

- PyPI counts every package the `wwdseb` account owns, as PyPI lists
  them. Matching GitHub repos by language missed `audioanalyser`: 37
  packages and 409,872 all-time downloads, not 36 and 390,697.
- A package missing from one npm search keeps its history and its count.
  It leaves after three runs in a row without it, instead of at once,
  which forced a full re-fetch from npm's most rate-limited endpoint.
- `state.json` is written whole or not at all, so a run that dies
  mid-write cannot leave a file the next run fails to parse.

### Changed

- The refresh runs in two jobs. The one that runs the Python render and
  the registry calls has a read-only token; the one that commits runs no
  third-party code.
- Every Python library and tool (fontTools, brotli, pytest, ruff,
  complexipy, actionlint, pip-audit) is locked with hashes in `uv.lock`,
  and Dependabot now proposes updates for it.

## [0.0.10] - 2026-11-06

### Fixed

- An article whose title contains a double quote no longer breaks its
  panel. The title went into the SVG's `aria-label` attribute with only
  `&`, `<` and `>` escaped, so a `"` ended the attribute early and the
  SVG was malformed, showing as a broken image. Titles come from the
  live site, so this needed no change on the profile's side to happen.

## [0.0.9] - 2026-11-06

### Fixed

- The hero clock no longer freezes completely for readers with reduced
  motion. v0.0.3 stopped every moving part; now the hour and minute hands
  keep turning at their very slow normal pace, and only the seconds sweep
  and the badge digits pause, frozen at the time the image loaded.

## [0.0.8] - 2026-11-06

### Added

- `SECURITY.md` (private reporting through GitHub, scope, and the
  protections the project relies on), `DEVELOPMENT.md`,
  `docs/ARCHITECTURE.md`, `AGENTS.md`, `.editorconfig` and
  `.compliance.yml` (tier L1).

### Changed

- Merged branches delete themselves, and the twelve stale remote
  branches are gone. Only `main` and `profile-data` remain.

## [0.0.7] - 2026-11-06

### Fixed

- PyPI's all-time downloads no longer dip. ClickPy sometimes answers
  from a replica that lacks older rows: the same query seconds apart
  returned 106,555 downloads from 2023-11-08 and 169,994 from
  2023-03-11. Three refresh runs held the figure at about 295k against
  391k. The query now runs four times and keeps the fullest answer,
  since an all-time total only grows.

## [0.0.6] - 2026-11-06

### Changed

- A held value now logs everything the source returned (packages,
  all-time, recent), not only the field that tripped the band. PyPI's
  all-time figure was held on two runner runs at about 294k against 391k
  from a laptop, and the summary could not say which part moved.

## [0.0.5] - 2026-11-06

### Fixed

- `tools/commit.sh push` exited 1 after a successful commit: its cleanup
  trap read a function-local variable at shell exit, which `set -u`
  rejects. The refresh's first run published its state to `profile-data`
  and then failed on this. A test now runs the script against a stubbed
  `gh`, covering additions, deletions and the no-change path.

## [0.0.4] - 2026-11-06

### Fixed

- `refresh.yml` is valid YAML again. v0.0.3 shipped it with an unquoted
  colon and space in a `run:` line, so GitHub rejected the file and no
  refresh ran.

### Changed

- `make check` lints the workflow files with actionlint, so a file
  GitHub would reject fails the gate before it merges.

## [0.0.3] - 2026-11-06

### Fixed

- The refresh publishes again. It had failed every day since 2026-10-14:
  first on npm rate limits, then on the argument-length limit in
  `tools/commit.sh`, and since v0.0.2 on `main`'s branch protection.
  The numbers and article panels now live on a `profile-data` branch,
  which `refresh.yml` commits to every three hours; `main` changes only
  through release pull requests.
- One failing source no longer freezes the profile. Each source keeps its
  last good value, values outside plausibility bands are held, and a
  source stale for more than two days fails the run and opens an issue.
- The fonts are pinned by SHA-256. The site had shipped new font files,
  which silently changed every SVG on the next refresh.

### Changed

- npm all-time downloads come from a ledger of settled ranges, so a
  normal run makes one range request per package instead of one per 540
  days of history.
- crates.io and npm listings are paginated, so neither caps silently.
- Every request has a 30-second timeout and backs off on 429 and 5xx,
  honouring `Retry-After`, within a two-minute budget per URL. The
  GitHub token travels on stdin, not argv.
- `make check` is offline apart from the pinned fonts. It adds tests,
  shellcheck and a drift check that the committed README and assets
  match a fresh build. Tool and library versions are pinned.
- The numbers panel says when its figures were last updated.
- The hero clock stops for readers who prefer reduced motion.
- Renders delete SVGs that no panel draws any more.

## [0.0.2] - 2026-11-05

### Fixed

- `tools/commit.sh` passes file contents to `jq` through a file (#8).

### Changed

- Bump astral-sh/setup-uv to 10.3.3 (#8).

## [0.0.1] - 2026-11-04

### Changed

- Bump astral-sh/setup-uv from 10.3.0 to 10.3.2 (#6).
