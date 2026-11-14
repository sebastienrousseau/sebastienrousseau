"""Restyle GitHub's generated release notes to the workspace format.

gh api repos/.../releases/generate-notes --jq .body | python3 tools/release_notes.py

release.yml pipes the generated notes through this before drafting a
release. Under "What's Changed" each title goes in backticks, and every
heading is followed by a blank line, as the dotfiles releases are laid out
(~/Code/AGENTS.md section 3). Restyled notes pass through unchanged.
"""

from __future__ import annotations

import re
import sys

ENTRY = re.compile(r"^\* (?!`)(.+) by (@\S+) in (https://github\.com/\S+/(?:pull/\d+|commit/[0-9a-f]+))$")


def restyle(text: str) -> str:
    """`text` with each change's title in backticks and a blank line under each heading."""
    out: list[str] = []
    section = ""
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line
        elif section == "## What's Changed":
            line = ENTRY.sub(r"* `\1` by \2 in \3", line)
        if out and out[-1].startswith("## ") and line:
            out.append("")
        out.append(line)
    return "\n".join(out)


def main() -> int:
    sys.stdout.write(restyle(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
