"""Holiday date rules: Easter, nth weekdays, the rule grammar and expansion."""

from __future__ import annotations

import datetime as dt

import pytest

import almanac

D = dt.date


def test_easter_matches_the_published_table():
    """US Census Bureau, "Easter Dates" (X-13ARIMA-SEATS holiday table):
    https://www.census.gov/data/software/x13as/genhol/easter-dates.html
    """
    published = {2026: D(2026, 4, 5), 2027: D(2027, 3, 28), 2028: D(2028, 4, 16), 2029: D(2029, 4, 1)}
    published[2030] = D(2030, 4, 21)
    assert {year: almanac.easter(year) for year in published} == published


@pytest.mark.parametrize(
    ("year", "may", "august", "thanksgiving"),
    [
        (2026, 25, 31, 26),
        (2027, 31, 30, 25),
        (2028, 29, 28, 23),
        (2029, 28, 27, 22),
        (2030, 27, 26, 28),
    ],
)
def test_bank_holidays_and_thanksgiving(year, may, august, thanksgiving):
    assert almanac.nth_weekday(year, 5, -1, 0) == D(year, 5, may)
    assert almanac.nth_weekday(year, 8, -1, 0) == D(year, 8, august)
    assert almanac.nth_weekday(year, 11, 4, 3) == D(year, 11, thanksgiving)


def test_a_fifth_weekday_that_does_not_exist_is_an_error():
    with pytest.raises(ValueError, match="no 5th mon"):
        almanac.nth_weekday(2026, 2, 5, 0)


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("fixed 12-24 2", almanac.Rule("fixed", month=12, day=24, length=2)),
        ("fixed 01-01", almanac.Rule("fixed", month=1, day=1)),
        ("easter -21", almanac.Rule("easter", offset=-21)),
        ("easter -50 4", almanac.Rule("easter", offset=-50, length=4)),
        ("nth last mon 05", almanac.Rule("nth", month=5, n=-1, weekday=0)),
        ("nth 2 sun 11", almanac.Rule("nth", month=11, n=2, weekday=6)),
        ("table 3", almanac.Rule("table", length=3)),
        ("table", almanac.Rule("table")),
    ],
)
def test_every_form_of_the_grammar_parses(text, rule):
    assert almanac.parse_rule(text, "k") == rule


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("fixed 12-24 0", "is not fixed"),
        ("fixed 13-01", "no month 13"),
        ("fixed 02-29", "no day 29"),
        ("nth 6 mon 05", "is not fixed"),
        ("nth last mon 00", "no month 0"),
        ("weekly mon", "is not fixed"),
    ],
)
def test_a_malformed_rule_names_its_holiday(text, why):
    with pytest.raises(SystemExit, match=f"holidays.toml: diwali: rule .*{why}"):
        almanac.parse_rule(text, "diwali")


def test_a_window_runs_into_the_next_year():
    kwanzaa = almanac.parse_rule("fixed 12-26 7", "kwanzaa")
    days = almanac.expand(kwanzaa, 2026, {})
    assert (days[0], days[-1], len(days)) == (D(2026, 12, 26), D(2027, 1, 1), 7)


def test_easter_offsets_and_table_ranges_expand():
    carnival = almanac.expand(almanac.parse_rule("easter -50 4", "carnival"), 2026, {})
    assert carnival == [D(2026, 2, 14), D(2026, 2, 15), D(2026, 2, 16), D(2026, 2, 17)]  # Saturday to Shrove Tuesday
    table = almanac.parse_rule("table 2", "holi")
    assert almanac.expand(table, 2026, {"2026": "2026-03-03"}) == [D(2026, 3, 3), D(2026, 3, 4)]
    ranged = almanac.expand(almanac.parse_rule("table", "oktoberfest"), 2026, {"2026": "2026-09-19..2026-10-04"})
    assert (ranged[0], ranged[-1], len(ranged)) == (D(2026, 9, 19), D(2026, 10, 4), 16)
    spring = almanac.expand(almanac.parse_rule("nth last mon 05", "spring-bank-holiday"), 2027, {})
    assert spring == [D(2027, 5, 31)]
