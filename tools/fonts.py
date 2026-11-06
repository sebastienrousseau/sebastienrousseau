"""Font instancing, subsetting and text measurement for the SVG panels.

The variable WOFF2 files come from sebastienrousseau.com so the profile
renders in the same typefaces as the site (Inter, Newsreader; SIL OFL 1.1,
which permits embedding). Each SVG embeds only the glyphs it uses.

Every source file is pinned by SHA-256. When the site ships new fonts the
build stops, and moving the pin is a deliberate change that re-renders
every panel, instead of a silent one that happens mid-refresh.
"""

from __future__ import annotations

import base64
import hashlib
import io
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from net import get

CACHE = Path(__file__).resolve().parent.parent / ".cache" / "fonts"
SOURCE = "https://sebastienrousseau.com/fonts/{}.woff2"
PINS = {
    "inter-latin": "0618a81c824079e978803ca05a22388ea3989c978f5b7cf14e60bf6cb5e3e58c",
    "newsreader-latin": "11611d3e41f8b8429dc31d00eb59db4d52c91dde701769e7af1b5d1ea72f476d",
}

# face name -> (source file, axis location)
FACES = {
    "inter-400": ("inter-latin", {"wght": 400}),
    "inter-500": ("inter-latin", {"wght": 500}),
    "inter-600": ("inter-latin", {"wght": 600}),
    "inter-700": ("inter-latin", {"wght": 700}),
    "news-500": ("newsreader-latin", {"wght": 500, "opsz": 72}),
}


def _source(name: str) -> Path:
    """The pinned source file, from the cache or the site, verified either way."""
    pin = PINS[name]
    path = CACHE / f"{name}-{pin[:12]}.woff2"
    data = path.read_bytes() if path.exists() else get(SOURCE.format(name))
    digest = hashlib.sha256(data).hexdigest()
    if digest != pin:
        raise SystemExit(f"fonts: {name}.woff2 has sha256 {digest}, pinned {pin}; update PINS deliberately")
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path


@cache
def face(name: str) -> TTFont:
    """Return a static instance of a named face."""
    src, loc = FACES[name]
    font = TTFont(_source(src), recalcTimestamp=False)
    return instancer.instantiateVariableFont(font, loc)


def width(name: str, text: str, size: float, tracking: float = 0.0) -> float:
    """Advance width of `text` in SVG units, with tracking in em."""
    font = face(name)
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    upem = font["head"].unitsPerEm
    units = sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text)
    return units * size / upem + tracking * size * max(len(text) - 1, 0)


def wrap(name: str, text: str, size: float, limit: float) -> list[str]:
    """Greedy word wrap to `limit` SVG units."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and width(name, trial, size) > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


@dataclass
class Glyphs:
    """Collects the characters each face draws in one SVG."""

    used: dict[str, set[str]] = field(default_factory=dict)

    def add(self, name: str, text: str) -> None:
        self.used.setdefault(name, set()).update(text)

    def css(self) -> str:
        return "\n".join(_font_face(n, "".join(sorted(c))) for n, c in self.used.items())


@cache
def _instance_bytes(name: str) -> bytes:
    buf = io.BytesIO()
    face(name).save(buf)
    return buf.getvalue()


def _font_face(name: str, chars: str) -> str:
    sub = TTFont(io.BytesIO(_instance_bytes(name)), recalcTimestamp=False)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "tnum"]
    opts.name_IDs = [0, 13, 14]  # keep copyright and OFL licence (OFL 1.1 §2)
    sub_er = subset.Subsetter(opts)
    sub_er.populate(text=chars + " ")
    sub_er.subset(sub)
    out = io.BytesIO()
    sub.flavor = "woff2"
    sub.save(out)
    data = base64.b64encode(out.getvalue()).decode()
    return f"@font-face{{font-family:{name};src:url(data:font/woff2;base64,{data}) format('woff2')}}"
