"""Noun Project icons: sanitise one into art/icons/, load it pinned by hash.

make icon KEY=<key> SVG=<file> CREATOR="<name>" [TITLE="<title>" URL=<page>]

The maintainer downloads each icon; nothing here touches the network.
sanitise() keeps an allowlist of shape elements and geometry attributes,
drops colour, text and metadata, refuses anything that could load or run
something, and maps the drawing into a 100-unit box centred on 0,0 filled
with currentColor, so a hero can recolour it. Same input, same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from xml.parsers import expat
from xml.sax.saxutils import quoteattr

import holidays

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art" / "icons"
LICENCE = "Noun Project, royalty-free (NounPro)"

REFUSED_BYTES = (b"<!DOCTYPE", b"<!ENTITY", b"<script", b"javascript:", b"<foreignObject", b"<image", b"href")
SHAPES = {"svg", "g", "path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}
DROPPED = {"text", "title", "desc", "metadata", "style", "tspan"}
KEPT = {"d", "points", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "x1", "y1", "x2", "y2"}
KEPT |= {"transform", "fill-rule", "clip-rule"}
GEOMETRY = {"d", "points", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "x1", "y1", "x2", "y2"}
NUMBER = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")
NAME = re.compile(r"^noun[-_](?P<slug>[A-Za-z0-9-]+)[-_](?P<id>\d+)\.svg$")
CREDIT = re.compile(r"Created by (.+?) from (?:the )?Noun Project")


def _number(m: re.Match) -> str:
    """One decimal is 1/36000 of a 3600-unit icon: invisible, and a third smaller."""
    text = f"{round(float(m[0]), 1):.1f}".removesuffix(".0")
    return "0" if text == "-0" else text


def _attrs(attrs: dict[str, str]) -> str:
    kept = []
    for name in sorted(attrs):
        if name in KEPT:
            value = NUMBER.sub(_number, attrs[name]) if name in GEOMETRY else attrs[name]
            kept.append(f" {name}={quoteattr(value)}")
    return "".join(kept)


class _Walk:
    """An expat walk that rebuilds only the allowed elements."""

    def __init__(self) -> None:
        self.out: list[str] = []
        self.depth = 0  # 1 inside the root <svg>
        self.skip = 0  # depth inside a dropped element
        self.root: dict[str, str] = {}
        self.dropped_text = False

    def start(self, tag: str, attrs: dict[str, str]) -> None:
        tag = tag.rsplit(" ", 1)[-1]
        self.depth += 1
        if self.skip or tag in DROPPED:
            self.skip += 1
            self.dropped_text |= tag == "text"
        elif tag not in SHAPES or (tag == "svg") != (self.depth == 1):
            raise SystemExit(f"icons: refused <{tag}>: simplify the icon or pick another")
        elif self.depth == 1:
            self.root = attrs
        else:
            self.out.append(f"<{tag}{_attrs(attrs)}>")

    def end(self, tag: str) -> None:
        if self.skip:
            self.skip -= 1
        elif self.depth > 1:
            self.out.append(f"</{tag.rsplit(' ', 1)[-1]}>")
        self.depth -= 1


def _box(root: dict[str, str], dropped_text: bool) -> tuple[float, float, float, float]:
    box = root.get("viewBox") or f"0 0 {root.get('width', '100')} {root.get('height', '100')}"
    x, y, w, h = (float(v) for v in re.split(r"[\s,]+", box.strip()))
    if dropped_text and abs(h - 1.25 * w) < 1e-6:
        h = w  # a free download's credit band: keep the square drawing above it
    return x, y, w, h


def sanitise(data: bytes) -> str:
    """The icon as one <g> in a 100-unit box centred on 0,0, filled with currentColor."""
    for pattern in REFUSED_BYTES:
        if pattern.lower() in data.lower():
            raise SystemExit(f"icons: refused: the file contains {pattern.decode()}")
    walk = _Walk()
    parser = expat.ParserCreate(namespace_separator=" ")
    parser.StartElementHandler = walk.start
    parser.EndElementHandler = walk.end
    parser.Parse(data, True)
    x, y, w, h = _box(walk.root, walk.dropped_text)
    scale = 100 / max(w, h)
    move = f"translate({-(x + w / 2):g} {-(y + h / 2):g})"
    body = "".join(walk.out)
    return f'<g transform="scale({scale:.6g}) {move}" fill="currentColor">{body}</g>'


def file_text(markup: str) -> str:
    """art/icons/<key>.svg: the sanitised icon as a viewable SVG file."""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 -50 100 100">{markup}</svg>\n'


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def intake(key: str, svg: Path, credit: dict[str, str], art: Path = ART) -> str:
    """Sanitise svg into art/icons/<key>.svg; the TOML line that pins it.

    credit may give the creator, title and url; the file name and its
    "Created by" text fill in the title, url and creator it leaves out.
    """
    m = NAME.match(svg.name)
    if not m:
        raise SystemExit(f"icons: {svg.name} is not a Noun Project file name (noun-<slug>-<id>.svg)")
    data = svg.read_bytes()
    found = CREDIT.search(data.decode(errors="replace"))
    creator = credit.get("creator") or (found[1] if found else "")
    if not creator:
        raise SystemExit(f"icons: {svg.name} names no creator: pass CREATOR=")
    title = credit.get("title") or m["slug"].replace("-", " ").capitalize()
    url = credit.get("url") or f"https://thenounproject.com/icon/{m['slug'].lower()}-{m['id']}/"
    text = file_text(sanitise(data))
    art.mkdir(parents=True, exist_ok=True)
    (art / f"{key}.svg").write_text(text)
    fields = {"file": f"art/icons/{key}.svg", "id": m["id"], "title": title, "creator": creator}
    fields |= {"url": url, "licence": LICENCE, "sha256": sha256(text)}
    return "icon = { " + ", ".join(f'{k} = "{v}"' for k, v in fields.items()) + " }"


def load(icon: dict[str, str], root: Path = ROOT) -> str:
    """The pinned icon's <g> markup; SystemExit if the file changed."""
    text = (root / icon["file"]).read_text()
    if sha256(text) != icon["sha256"]:
        raise SystemExit(f"{icon['file']}: sha256 does not match holidays.toml; re-run make icon")
    return text.split(">", 1)[1].removesuffix("</svg>\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sanitise a Noun Project icon into art/icons/.")
    ap.add_argument("key")
    ap.add_argument("svg", type=Path)
    ap.add_argument("--creator", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--url", default="")
    a = ap.parse_args(argv)
    if a.key not in {h.key for h in holidays.load()[1]}:
        raise SystemExit(f"icons: no holiday {a.key!r} in holidays.toml")
    print(intake(a.key, a.svg, {"creator": a.creator, "title": a.title, "url": a.url}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
