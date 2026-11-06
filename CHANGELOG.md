# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.7] - Unreleased

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
  `: ` in a `run:` line, so GitHub rejected the file and no refresh ran.

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
