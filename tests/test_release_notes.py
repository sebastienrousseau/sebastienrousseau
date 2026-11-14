"""Release notes take the workspace format: titles in backticks, a blank line under each heading."""

from __future__ import annotations

import io

import release_notes

URL = "https://github.com/sebastienrousseau/sebastienrousseau/pull"

GENERATED = f"""## What's Changed
* feat: serve the hero clock live by @sebastienrousseau in {URL}/2
* build(deps): Bump astral-sh/setup-uv from 10.2.0 to 10.3.0 by @dependabot[bot] in {URL}/3

## New Contributors
* @dependabot[bot] made their first contribution in {URL}/3
"""

STYLED = f"""## What's Changed

* `feat: serve the hero clock live` by @sebastienrousseau in {URL}/2
* `build(deps): Bump astral-sh/setup-uv from 10.2.0 to 10.3.0` by @dependabot[bot] in {URL}/3

## New Contributors

* @dependabot[bot] made their first contribution in {URL}/3
"""


def test_generated_notes_take_the_workspace_format():
    assert release_notes.restyle(GENERATED) == STYLED


def test_restyling_twice_changes_nothing():
    assert release_notes.restyle(STYLED) == STYLED


def test_a_commit_entry_is_styled_like_a_pull_request():
    url = "https://github.com/sebastienrousseau/sebastienrousseau/commit/0a7750f"
    line = f"* build: build the manual with ssg 0.0.76 by @sebastienrousseau in {url}"
    want = f"* `build: build the manual with ssg 0.0.76` by @sebastienrousseau in {url}"
    assert release_notes.restyle(f"## What's Changed\n{line}\n") == f"## What's Changed\n\n{want}\n"


def test_lines_outside_whats_changed_are_left_alone():
    text = f"## New Contributors\n\n* @x made their first contribution in {URL}/9 by @y in {URL}/9\n"
    assert release_notes.restyle(text) == text


def test_main_filters_stdin_to_stdout(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(GENERATED))
    assert release_notes.main() == 0
    assert capsys.readouterr().out == STYLED
