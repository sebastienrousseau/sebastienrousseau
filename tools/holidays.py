"""holidays.toml: the holiday themes, as data.

load() reads the file into Holiday records in file order, which is also the
order overlapping holidays alternate in. The calendar (which London days
each holiday covers) is built from these records by almanac.py.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "holidays.toml"


@dataclass(frozen=True)
class Holiday:
    """One [[holiday]] table of holidays.toml."""

    key: str
    name: str
    month: int
    rules: tuple[str, ...]
    motif: str
    accent: dict[str, str]
    accent2: dict[str, str]
    glyph: str
    emblem: str
    quiet: bool = False
    spin: bool = False
    dates: dict[str, str] = field(default_factory=dict)
    source: str = ""
    icon: dict[str, str] | None = None


def _holiday(raw: dict) -> Holiday:
    rule = raw.pop("rule")
    rules = tuple(rule) if isinstance(rule, list) else (rule,)
    dates = {str(year): str(day) for year, day in raw.pop("dates", {}).items()}
    return Holiday(rules=rules, dates=dates, **raw)


def load(path: Path = SOURCE) -> tuple[list[int], list[Holiday]]:
    """The inclusive year span and every holiday, in file order."""
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return list(data["years"]), [_holiday(dict(h)) for h in data["holiday"]]
