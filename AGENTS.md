# Instructions for AI-assisted contributors

Read [DEVELOPMENT.md](DEVELOPMENT.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
first. Rules that apply to every change:

1. **Never edit generated output.** `README.md` and everything in `assets/`
   come from `profile.toml` and `tools/`. Change the source, run `make`, and
   commit the regenerated files with it.
2. **One gate.** `make check` must pass before you claim anything is done.
   CI runs the same command.
3. **Branches.** Work for the next version goes on `feat/v<next>`, where the
   version is the current one plus 0.0.1. At most one pull request targets
   `main`. Never push to `main`.
4. **Do not merge.** Merging a pull request needs an explicit instruction
   from the maintainer for that pull request.
5. **Commits.** Header `<type>: <subject>`, at most 50 characters,
   imperative. Body wrapped at 72 columns, saying what and why. Types:
   feat, fix, docs, style, refactor, perf, test, build, ci, chore. Commits
   are signed. Add the trailer
   `Assisted-by: <agent>:<model> [<analysis tools>]`, and never a
   `Signed-off-by:` on anyone's behalf.
6. **Pull requests** open with a two-line summary (what it does, why it
   matters), then Highlights, What's Changed, Validation with real numbers,
   Checksums and the Full Changelog link. No em dashes.
7. **Update `CHANGELOG.md`** with every user-visible or operational change.
8. **Do not silence a check.** No new ignore entries, baselines or
   suppressions to make a gate pass. Fix the cause.
9. **Do not invent facts.** Versions, owners, licences and figures come
   from the repository or the maintainer.
10. **Workflow files are linted** by `make lint` (actionlint). A file GitHub
    rejects runs nothing, silently.
11. **Complexity ceilings** per function: cyclomatic 10, cognitive 15, 60
    lines. Per file: 500 lines.
12. **Never send anything outside the machine** without being asked: no
    emails, no issues on other projects, no publishes, no announcements.

The repository is licensed Apache-2.0 OR MIT (`LICENSE`, `LICENSE-APACHE`,
`LICENSE-MIT`). Leave the licence texts alone.
