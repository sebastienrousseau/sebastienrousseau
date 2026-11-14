"""holidays.toml: the holiday themes, as data.

load() reads the file into Holiday records in file order, which is also the
order overlapping holidays alternate in. The calendar (which London days
each holiday covers) is built from these records by almanac.py.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import tomllib
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

import almanac

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "holidays.toml"
KEY = re.compile(r"^[a-z0-9-]{1,40}$")  # the clock Worker accepts only these
HEX = re.compile(r"^#[0-9a-f]{6}$")
DATE = re.compile(r"^\d{4}-\d\d-\d\d$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
    sources: tuple[str, ...] = ()
    icon: dict[str, str] | None = None

    def is_table(self) -> bool:
        """True when some of its dates are copied from a published source."""
        return any(text.split()[0] == "table" for text in self.rules)


def _tuple(value: str | list[str]) -> tuple[str, ...]:
    return tuple(value) if isinstance(value, list) else (value,)


def _holiday(raw: dict) -> Holiday:
    rules = _tuple(raw.pop("rule"))
    sources = _tuple(raw.pop("source")) if "source" in raw else ()
    dates = {str(year): str(day) for year, day in raw.pop("dates", {}).items()}
    return Holiday(rules=rules, dates=dates, sources=sources, **raw)


def load(path: Path = SOURCE) -> tuple[list[int], list[Holiday]]:
    """The inclusive year span and every holiday, in file order."""
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return list(data["years"]), [_holiday(dict(h)) for h in data["holiday"]]


def _fail(h: Holiday, why: str) -> NoReturn:
    raise SystemExit(f"holidays.toml: {h.key}: {why}")


def _check_art(h: Holiday, glyphs: Collection[str], emblems: Collection[str]) -> None:
    if h.glyph not in glyphs:
        _fail(h, f"unknown glyph {h.glyph!r}")
    if h.emblem not in emblems and h.emblem not in {"none", "icon"}:
        _fail(h, f"unknown emblem {h.emblem!r}")
    for name, pair in (("accent", h.accent), ("accent2", h.accent2)):
        if set(pair) != {"light", "dark"} or not all(HEX.match(v) for v in pair.values()):
            _fail(h, f"{name} needs a #rrggbb light and dark")


def _check_icon(h: Holiday) -> None:
    if h.emblem == "icon" and h.icon is None:
        _fail(h, 'emblem = "icon" but no icon')
    if h.icon is not None and not SHA256.match(str(h.icon.get("sha256", ""))):
        _fail(h, "icon has no sha256 pin")


def _check_dates(h: Holiday, years: list[int]) -> None:
    for text in h.rules:
        almanac.parse_rule(text, h.key)
    if not h.is_table():
        return
    if not h.sources or not all(s.startswith("https://") for s in h.sources):
        _fail(h, "a table rule needs the https source(s) its dates were copied from")
    for year, value in h.dates.items():
        if not almanac.RANGE.match(value) and not DATE.match(value):
            _fail(h, f"{year} date {value!r} is not YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD")
        if not value.startswith(year) or not years[0] <= int(year) <= years[1]:
            _fail(h, f"{year} date {value!r} is outside its year or the span")


def gaps(years: list[int], hs: list[Holiday]) -> list[str]:
    """Each table holiday's years with no sourced date: it has no theme then.

    Dates are never guessed (docs/HOLIDAYS.md); a year whose source could
    not be opened is left out and listed here, for the build to print.
    """
    out = []
    for h in hs:
        missing = [str(y) for y in range(years[0], years[1] + 1) if h.is_table() and str(y) not in h.dates]
        if missing:
            out.append(f"{h.key}: no sourced date for {', '.join(missing)}")
    return out


def validate(years: list[int], hs: list[Holiday], glyphs: Collection[str], emblems: Collection[str]) -> None:
    """SystemExit naming the holiday on the first problem in holidays.toml."""
    seen: set[str] = set()
    for h in hs:
        if not KEY.match(h.key) or h.key in seen:
            _fail(h, "key must be unique and match [a-z0-9-]{1,40}")
        seen.add(h.key)
        _check_art(h, glyphs, emblems)
        _check_icon(h)
        _check_dates(h, years)


def _days(h: Holiday, year: int) -> list[dt.date]:
    out: list[dt.date] = []
    for text in h.rules:
        rule = almanac.parse_rule(text, h.key)
        if rule.kind == "table" and str(year) not in h.dates:
            continue  # the year before the span: no table date, nothing spills in
        out += almanac.expand(rule, year, h.dates)
    return out


def calendar(years: list[int], hs: list[Holiday]) -> dict[str, list[str]]:
    """ISO London date to the keys of the holidays on it, in file order.

    The year before the span is expanded too, so a window that runs into the
    span's first January (Kwanzaa) is not lost.
    """
    order = {h.key: i for i, h in enumerate(hs)}
    first = dt.date(years[0], 1, 1)
    days: dict[str, set[str]] = {}
    for year in range(years[0] - 1, years[1] + 1):
        for h in hs:
            for day in _days(h, year):
                if day >= first:
                    days.setdefault(day.isoformat(), set()).add(h.key)
    return {iso: sorted(keys, key=order.__getitem__) for iso, keys in sorted(days.items())}


def calendar_json(years: list[int], hs: list[Holiday]) -> str:
    """assets/holidays.json: the calendar the clock Worker reads, byte-stable."""
    days = calendar(years, hs)
    doc = {"schema": 1, "tz": "Europe/London", "from": f"{years[0]}-01-01", "to": max(days), "days": days}
    return json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n"
