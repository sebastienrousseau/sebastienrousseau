# Security policy

## Reporting a vulnerability

Please report privately through GitHub:
<https://github.com/sebastienrousseau/sebastienrousseau/security/advisories/new>

Do not open a public issue for a vulnerability. Include what you found, how
to reproduce it, and what you think the impact is.

Reports are handled on a best-effort basis by one maintainer. No response
time is promised.

## Scope

This repository generates a GitHub profile README and its SVG panels. It
ships no installable package and no service. In scope:

* The workflows in `.github/workflows/` and their token permissions.
* `tools/`, which fetches third-party data and writes the generated files.
* The `profile-data` branch, which the refresh workflow writes.

Out of scope: the registries it reads (crates.io, PyPI, ClickPy, npm), the
profile-clock Worker, and sebastienrousseau.com. Report those to their own
owners.

## What the project does for you

* Third-party actions are pinned by commit SHA, and Dependabot proposes
  updates.
* The refresh workflow commits through GitHub's `createCommitOnBranch`
  API, so every commit is signed and shows as Verified, and it writes only
  to `profile-data`. `main` changes through reviewed release pull requests.
* Source fonts are pinned by SHA-256 and verified before use.
* Python tools and libraries are pinned to exact versions in the
  `Makefile`.
* The GitHub token reaches `curl` on stdin, never on the command line.
* CodeQL, secret scanning and push protection are enabled.
