# The profile, as code

This repository generates the GitHub profile at
[github.com/sebastienrousseau](https://github.com/sebastienrousseau): the
README and every panel on it. Nothing on the profile is drawn by hand.

## What a visitor sees

* **Static panels** (hero, sections, the paper, the closing panel) come from
  `profile.toml`, rendered as SVG in the typefaces and colours of
  [sebastienrousseau.com](https://sebastienrousseau.com/). CI rebuilds them
  and fails on any difference, so the committed files cannot drift.
* **Live panels** (the numbers, the project cards with their stars and
  downloads, and the three latest articles) are refreshed every three hours
  from crates.io, PyPI, npm, GitHub and the site, on a separate
  `profile-data` branch.
* **The clock** on the hero keeps London time. A Cloudflare Worker sets it
  on every view.
* **profile.json** carries the same figures as data, for the site and for
  agents. Its fields are described under [Data](DATA.md).

## How it stays right

* Every figure has a named source, and a value that falls further than is
  believable is held for a person to check instead of published.
* After each refresh, and every 30 minutes in between, a smoke check fetches
  every image the README shows and fails unless it would render. A failure
  opens an issue.
* Every tool the build runs is locked with hashes, audited for known
  vulnerabilities, and kept current by Dependabot. The job that commits
  never runs third-party code.

## Where to go next

* [Architecture](ARCHITECTURE.md): the two pipelines, the modules, and the
  decisions behind them.
* [Development](../DEVELOPMENT.md): the commands, and how to change copy,
  panels, sources and dependencies.
* [Security](../SECURITY.md): how to report a problem, and the protections
  the project relies on.
* [Changelog](../CHANGELOG.md): every release.
