"""Check what a visitor sees: every image README.md shows is a well-formed SVG.

make smoke        # networked; refresh.yml runs it after every publish

The refresh's own alert covers stale data. This covers the rest: a panel
that renders as a broken image (an unescaped quote once did), a live file
missing from profile-data, or the clock Worker falling back to the stopped
clock. Remote images must answer 200 with no redirect, because the Worker
redirects to the static SVG when it fails, and that still looks like an
image. Exits 1 and prints a GitHub error line for every failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.parsers import expat

from net import FetchError, get

ROOT = Path(__file__).resolve().parent.parent
IMAGE = re.compile(r'(?:src|srcset)="([^"]+\.svg)"')


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


def check(ref: str) -> str | None:
    """Why the image at `ref` (a URL, or a path from the repo root) would not show, or None."""
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
    return svg_error(data)


def main() -> int:
    refs = sorted(set(IMAGE.findall((ROOT / "README.md").read_text())))
    failures = [f"{ref}: {why}" for ref in refs if (why := check(ref))]
    for failure in failures:
        print(f"::error::{failure}")
    print(f"smoke: {len(refs)} images, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
