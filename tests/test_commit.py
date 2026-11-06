"""tools/commit.sh pushes a directory's changes through the GraphQL API, with gh stubbed."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "commit.sh"
STUB = """#!/usr/bin/env bash
# Stand-in for gh: log the call, keep the request body, answer like the API.
echo "$@" >>"$STUB_DIR/calls"
cat >"$STUB_DIR/body.json"
echo https://example.test/commit/abc
"""


def git(cwd: Path, *args: str) -> None:
    ident = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    env = {**os.environ, **ident, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)  # noqa: S603, S607


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    repo = tmp_path / "live"
    (repo / "assets").mkdir(parents=True)
    (repo / "state.json").write_text("{}\n")
    (repo / "assets" / "old-dark.svg").write_text("<svg/>")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "start")
    return repo


def run_push(repo: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (stub_dir / "gh").write_text(STUB)
    (stub_dir / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{stub_dir}:{os.environ['PATH']}", "STUB_DIR": str(stub_dir),
           "GITHUB_REPOSITORY": "o/r", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}  # fmt: skip
    return subprocess.run(  # noqa: S603
        ["bash", str(SCRIPT), "push", str(repo), "profile-data", "docs: refresh"],  # noqa: S607
        capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip


def test_push_sends_additions_and_deletions_and_exits_zero(checkout, tmp_path):
    (checkout / "state.json").write_text('{"a": 1}\n')
    (checkout / "assets" / "new-dark.svg").write_text("<svg>new</svg>")
    (checkout / "assets" / "old-dark.svg").unlink()
    done = run_push(checkout, tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "https://example.test/commit/abc"
    sent = json.loads((tmp_path / "stub" / "body.json").read_text())["variables"]["i"]
    assert sent["branch"] == {"repositoryNameWithOwner": "o/r", "branchName": "profile-data"}
    assert sent["message"] == {"headline": "docs: refresh"}
    assert sorted(a["path"] for a in sent["fileChanges"]["additions"]) == ["assets/new-dark.svg", "state.json"]
    assert sent["fileChanges"]["deletions"] == [{"path": "assets/old-dark.svg"}]


def test_push_with_nothing_changed_makes_no_request(checkout, tmp_path):
    done = run_push(checkout, tmp_path)
    assert done.returncode == 0, done.stderr
    assert "No changes." in done.stdout
    assert not (tmp_path / "stub" / "body.json").exists()
