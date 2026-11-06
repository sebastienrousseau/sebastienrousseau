"""The complexity ceilings that ruff and complexipy do not check.

make lint            # runs: tools/ceilings.py tools tests

ruff enforces cyclomatic complexity (C901, 10) and complexipy cognitive
complexity (15). This adds the rest of the workspace ceilings: Halstead
difficulty 30 and 60 lines per function, and 500 lines per file. Nothing
in the repository is over a ceiling, so there is no baseline: any offender
fails the gate.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from radon.metrics import h_visit

MAX_DIFFICULTY = 30
MAX_FUNCTION_LINES = 60
MAX_FILE_LINES = 500
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def offences(path: Path) -> list[str]:
    """Every ceiling `path` exceeds, one line each."""
    src = path.read_text()
    found = []
    if (count := len(src.splitlines())) > MAX_FILE_LINES:
        found.append(f"{path}: {count} lines, ceiling {MAX_FILE_LINES}")
    tree = ast.parse(src)
    where = {n.name: n.lineno for n in ast.walk(tree) if isinstance(n, FUNCTIONS)}
    for node in ast.walk(tree):
        if isinstance(node, FUNCTIONS) and (lines := node.end_lineno - node.lineno + 1) > MAX_FUNCTION_LINES:
            found.append(f"{path}:{node.lineno} {node.name}: {lines} lines, ceiling {MAX_FUNCTION_LINES}")
    for name, report in h_visit(src).functions:
        if report.difficulty > MAX_DIFFICULTY:
            line = f"{path}:{where.get(name, 0)} {name}: Halstead difficulty {report.difficulty:.1f}"
            found.append(f"{line}, ceiling {MAX_DIFFICULTY}")
    return found


def main(args: list[str]) -> int:
    files = sorted(p for a in map(Path, args) for p in (a.rglob("*.py") if a.is_dir() else [a]))
    found = [line for path in files for line in offences(path)]
    for line in found:
        print(line)
    print(f"ceilings: {len(files)} files, {len(found)} over")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
