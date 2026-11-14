"""Check what a visitor sees: every image README.md shows is a well-formed SVG.

make smoke        # networked; refresh.yml runs it after every publish,
                  # and smoke.yml every 30 minutes in between

The refresh's own alert covers stale data. This covers the rest: a panel
that renders as a broken image (an unescaped quote once did), a live file
missing from profile-data, or the clock Worker falling back to the stopped
clock. Remote images must answer 200 with no redirect, because the Worker
redirects to the static SVG when it fails, and that still looks like an
image. profile.json, which the README links for agents, must parse and
carry its schema. The holiday calendar the Worker reads must parse and run
at least HORIZON days ahead, so it is extended before it silently ends.
Exits 1 and prints a GitHub error line for every failure.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from xml.parsers import expat

from net import FetchError, get

ROOT = Path(__file__).resolve().parent.parent
IMAGE = re.compile(r'(?:src|srcset)="([^"]+\.svg)"')
DATA = re.compile(r'href="([^"]+/profile\.json)"')
CALENDAR = "https://raw.githubusercontent.com/sebastienrousseau/sebastienrousseau/main/assets/holidays.json"
HORIZON = 180  # days of calendar left before the alert opens


def svg_error(data: bytes) -> str | None:
    """Why `data` is not a well-formed SVG document, or None."""
    tags: list[str] = []
    parser = expat.ParserCreate()
    parser.StartElementHandler = lambda tag, _attrs: tags.append(tag)
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        return f"malformed SVG ({exc})"
    return None if tags[0] == "svg" else f"root element is {tags[0]}, not svg"


def json_error(data: bytes) -> str | None:
    """Why `data` is not a profile.json an agent could use, or None."""
    try:
        doc = json.loads(data)
    except ValueError as exc:
        return f"not JSON ({exc})"
    return None if isinstance(doc, dict) and "schema" in doc else "no schema field"


def calendar_error(data: bytes, today: dt.date) -> str | None:
    """Why `data` is not a holiday calendar good for HORIZON more days, or None."""
    try:
        doc = json.loads(data)
        last = dt.date.fromisoformat(doc["to"])
    except (ValueError, KeyError, TypeError) as exc:
        return f"not a holiday calendar ({exc})"
    if doc.get("schema") != 1:
        return "holiday calendar schema is not 1"
    left = (last - today).days
    return None if left >= HORIZON else f"the holiday calendar ends {last}, {left} days away: extend holidays.toml"


def check(ref: str, today: dt.date) -> str | None:
    """Why the file at `ref` (a URL, or a path from the repo root) would not serve, or None."""
    if ref.startswith("https://"):
        try:
            data = get(ref, follow=False)
        except FetchError as exc:
            return str(exc)
    else:
        path = ROOT / ref
        if not path.is_file():
            return f"missing: {ref}"
        data = path.read_bytes()
    if ref.endswith("/holidays.json"):
        return calendar_error(data, today)
    return json_error(data) if ref.endswith(".json") else svg_error(data)


def main(today: dt.date | None = None) -> int:
    today = today or dt.datetime.now(dt.UTC).date()
    readme = (ROOT / "README.md").read_text()
    refs = sorted(set(IMAGE.findall(readme)) | set(DATA.findall(readme)) | {CALENDAR})
    failures = [f"{ref}: {why}" for ref in refs if (why := check(ref, today))]
    for failure in failures:
        print(f"::error::{failure}")
    print(f"smoke: {len(refs)} files, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
