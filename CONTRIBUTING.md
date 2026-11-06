# Contributing

This repository generates the GitHub profile at
[github.com/sebastienrousseau](https://github.com/sebastienrousseau). Most of
it is the maintainer's own copy, so the most useful contributions are fixes:
a panel that renders wrongly, a figure that is miscounted, a check that
misses a broken image, or a document that says something untrue.

## Before you start

* Read [DEVELOPMENT.md](DEVELOPMENT.md) for the commands, and
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit.
* For anything beyond a small fix, open an issue first so we can agree on
  the change.
* Report a security problem privately, as [SECURITY.md](SECURITY.md)
  describes, never in a public issue.

## Making a change

1. Edit the source, never the generated output: `README.md` and `assets/`
   come from `profile.toml` and `tools/`. Run `make` to regenerate them.
2. Add or change a test with any change in behaviour, and see it fail
   before your fix.
3. Run `make check`. It is the gate CI runs, and it must pass.
4. Add a line to [CHANGELOG.md](CHANGELOG.md) for anything a visitor or a
   maintainer would notice.
5. Open a pull request against `main`. Commits are signed, with headers of
   the form `<type>: <subject>` (at most 50 characters) and a body that says
   what changed and why.

By contributing, you agree that your contribution is licensed under the
terms in [LICENSE](LICENSE): Apache-2.0 OR MIT, at the user's option.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
