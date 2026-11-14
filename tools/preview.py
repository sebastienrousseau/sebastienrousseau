"""A local gallery of every hero, with the clock running.

make preview    # then open _preview/index.html

Writes _preview/ (git-ignored) from the committed heroes and holidays.toml:
an index page from tools/preview.html and a copy of each hero with the
clock marker replaced the way the Worker replaces it, so the hands turn.
Not part of make check; run it before reviewing a palette or icon change.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import holidays
import palette
import panels
from theme import THEMES

ROOT = Path(__file__).resolve().parent.parent
RUNNING = ".hand{animation-play-state:running}"
EVERYDAY = {"month": 0, "key": "default", "name": "Everyday", "when": "All other days", "motif": "ML-KEM blue"}


def _swatches(t: dict) -> dict[str, str]:
    return {k: t.get(k, t["accent"]) for k in ("panel", "accent", "accent2")}


def entries(years: list[int], hs: list[holidays.Holiday]) -> list[dict]:
    """The gallery's data: the everyday theme, then every holiday in calendar order."""
    gaps = {g.split(":")[0]: g.split(": ")[1] for g in holidays.gaps(years, hs)}
    out = [EVERYDAY | {"l": _swatches(THEMES["light"]), "d": _swatches(THEMES["dark"])}]
    for h in hs:
        when = " + ".join(h.rules) + (f" ({gaps[h.key]})" if h.key in gaps else "")
        out.append(
            {"month": h.month, "key": h.key, "name": h.name, "when": when, "motif": h.motif}
            | {"l": _swatches(palette.style(h, "light")), "d": _swatches(palette.style(h, "dark"))}
        )
    return out


def write(out: Path, assets: Path = ROOT / "assets") -> int:
    """Write the gallery into out; the number of heroes copied."""
    years, hs = holidays.load()
    shutil.rmtree(out, ignore_errors=True)
    (out / "heroes").mkdir(parents=True)
    copied = 0
    for src in sorted(assets.glob("hero-*.svg")):
        name = src.name.removeprefix("hero-")
        name = "default-" + name if name in {"light.svg", "dark.svg"} else name
        (out / "heroes" / name).write_text(src.read_text().replace(panels.CLOCK_MARKER, RUNNING, 1))
        copied += 1
    page = (ROOT / "tools" / "preview.html").read_text()
    (out / "index.html").write_text(page.replace("__DATA__", json.dumps(entries(years, hs))))
    return copied


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "_preview"
    print(f"preview: {write(out)} heroes in {out}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
