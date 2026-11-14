"""Date rules for holidays.toml: parse a rule, expand it to London days.

Pure functions, no I/O. A rule names the first day of a holiday in a given
year and how many whole London calendar days it lasts:

    fixed MM-DD [n]       the same date every year
    easter OFFSET [n]     Western Easter Sunday plus OFFSET days
    nth N WD MM [n]       the N-th (1..5 or "last") weekday WD of month MM
    table [n]             a start date per year from the holiday's dates;
                          a date may instead be a range "start..end"

n defaults to 1. A window may run past 31 December into the next year.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
GRAMMAR = re.compile(
    r"^(?:fixed (?P<month>\d\d)-(?P<day>\d\d)"
    r"|easter (?P<offset>[+-]?\d+)"
    r"|nth (?P<n>[1-5]|last) (?P<weekday>mon|tue|wed|thu|fri|sat|sun) (?P<nth_month>\d\d)"
    r"|(?P<table>table))"
    r"(?: (?P<length>[1-9]\d?))?$"
)
RANGE = re.compile(r"^(\d{4}-\d\d-\d\d)\.\.(\d{4}-\d\d-\d\d)$")


@dataclass(frozen=True)
class Rule:
    """One parsed rule; only the fields its kind uses are set."""

    kind: str  # fixed, easter, nth or table
    month: int = 0
    day: int = 0
    offset: int = 0
    n: int = 0  # 1..5; -1 for "last"
    weekday: int = 0  # Monday is 0
    length: int = 1


def easter(year: int) -> dt.date:
    """Western Easter Sunday: the anonymous Gregorian algorithm."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 19 * m) // 433
    month = (h + m - 7 * n + 90) // 25
    return dt.date(year, month, (h + m - 7 * n + 33 * month + 19) % 32)


def nth_weekday(year: int, month: int, n: int, weekday: int) -> dt.date:
    """The n-th weekday of a month (n = -1: the last one)."""
    days = [
        d for d in range(1, calendar.monthrange(year, month)[1] + 1) if dt.date(year, month, d).weekday() == weekday
    ]
    if n == -1:
        return dt.date(year, month, days[-1])
    if n > len(days):
        raise ValueError(f"{year}-{month:02d} has no {n}th {WEEKDAYS[weekday]}")
    return dt.date(year, month, days[n - 1])


def parse_rule(text: str, key: str) -> Rule:
    """A Rule from its text; SystemExit naming the holiday if it is malformed."""
    m = GRAMMAR.match(text)
    if not m:
        raise SystemExit(f"holidays.toml: {key}: rule {text!r} is not fixed, easter, nth or table")
    length = int(m["length"] or 1)
    if m["table"]:
        return Rule("table", length=length)
    if m["offset"] is not None:
        return Rule("easter", offset=int(m["offset"]), length=length)
    if m["weekday"]:
        n = -1 if m["n"] == "last" else int(m["n"])
        month = _month(m["nth_month"], text, key)
        return Rule("nth", month=month, n=n, weekday=WEEKDAYS.index(m["weekday"]), length=length)
    month, day = _month(m["month"], text, key), int(m["day"])
    if not 1 <= day <= calendar.monthrange(2027, month)[1]:  # 2027 is not a leap year: no 29 Feb, every year
        raise SystemExit(f"holidays.toml: {key}: rule {text!r} has no day {day} in month {month}")
    return Rule("fixed", month=month, day=day, length=length)


def _month(text: str, rule: str, key: str) -> int:
    month = int(text)
    if not 1 <= month <= 12:
        raise SystemExit(f"holidays.toml: {key}: rule {rule!r} has no month {month}")
    return month


def _span(start: dt.date, length: int) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range(length)]


def _table(rule: Rule, year: int, dates: dict[str, str]) -> list[dt.date]:
    value = dates[str(year)]
    if m := RANGE.match(value):
        first, last = (dt.date.fromisoformat(v) for v in m.groups())
        return _span(first, (last - first).days + 1)
    return _span(dt.date.fromisoformat(value), rule.length)


def expand(rule: Rule, year: int, dates: dict[str, str]) -> list[dt.date]:
    """Every London calendar day rule covers for the holiday starting in year."""
    if rule.kind == "table":
        return _table(rule, year, dates)
    if rule.kind == "easter":
        start = easter(year) + dt.timedelta(days=rule.offset)
    elif rule.kind == "nth":
        start = nth_weekday(year, rule.month, rule.n, rule.weekday)
    else:
        start = dt.date(year, rule.month, rule.day)
    return _span(start, rule.length)
