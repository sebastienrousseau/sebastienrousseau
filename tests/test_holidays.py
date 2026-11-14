"""holidays.toml validation and the calendar the clock Worker reads."""

from __future__ import annotations

import json
import textwrap

import pytest

import holidays

GLYPHS, EMBLEMS = {"dot", "snowflake", "poppy", "gift"}, {"tree", "kinara", "poppy", "gift"}
ACCENTS = 'accent = { light = "#b91c1c", dark = "#ff7070" }\naccent2 = { light = "#15803d", dark = "#6fd08c" }'


def entry(key: str, rule: str, extra: str = "", glyph: str = "dot", emblem: str = "none") -> str:
    return (
        textwrap.dedent(f"""
        [[holiday]]
        key = "{key}"
        name = "{key.title()}"
        month = 12
        rule = {rule}
        motif = "test"
        glyph = "{glyph}"
        emblem = "{emblem}"
        """)
        + ACCENTS
        + "\n"
        + extra
        + "\n"
    )


def write(tmp_path, *entries: str, years: str = "[2026, 2027]"):
    path = tmp_path / "holidays.toml"
    path.write_text(f"schema = 1\nyears = {years}\n" + "".join(entries))
    return holidays.load(path)


BASE = (
    entry("new-year", '"fixed 01-01"'),
    entry("remembrance", '["fixed 11-11", "nth 2 sun 11"]', glyph="poppy", emblem="poppy"),
    entry("christmas", '"fixed 12-24 2"', glyph="snowflake", emblem="tree"),
    entry("boxing-day", '"fixed 12-26"', glyph="gift", emblem="gift"),
    entry("kwanzaa", '"fixed 12-26 7"', emblem="kinara"),
)


def test_a_valid_file_passes(tmp_path):
    years, hs = write(tmp_path, *BASE)
    holidays.validate(years, hs, GLYPHS, EMBLEMS)
    assert [h.key for h in hs] == ["new-year", "remembrance", "christmas", "boxing-day", "kwanzaa"]
    assert hs[1].rules == ("fixed 11-11", "nth 2 sun 11")


TABLE = 'source = "https://example.org/eid"\n'


@pytest.mark.parametrize(
    ("bad", "why"),
    [
        (entry("new-year", '"fixed 01-02"'), "key must be unique"),
        (entry("Eid", '"fixed 01-02"'), "key must be unique"),
        (entry("eid", '"fixed 01-02"', glyph="comet"), "unknown glyph 'comet'"),
        (entry("eid", '"fixed 01-02"', emblem="comet"), "unknown emblem 'comet'"),
        (entry("eid", '"fixed 01-02"').replace("#b91c1c", "red"), "accent needs a #rrggbb"),
        (entry("eid", '"fixed 01-02"', emblem="icon"), 'emblem = "icon" but no icon'),
        (entry("eid", '"fixed 01-02"', 'icon = { file = "art/icons/eid.svg" }'), "icon has no sha256 pin"),
        (entry("eid", '"table 3"', 'dates = { 2026 = "2026-03-20", 2027 = "2027-03-10" }'), "needs the https source"),
        (entry("eid", '"table 3"', 'source = "http://example.org"\ndates = { 2026 = "2026-03-20" }'), "https source"),
        (entry("eid", '"table 3"', TABLE + 'dates = { 2026 = "20 March", 2027 = "2027-03-10" }'), "is not YYYY-MM-DD"),
        (
            entry("eid", '"table 3"', TABLE + 'dates = { 2026 = "2027-03-10", 2027 = "2027-03-10" }'),
            "outside its year or the span",
        ),
        (entry("eid", '"weekly"'), "rule 'weekly' is not fixed"),
    ],
)
def test_a_bad_entry_is_named(tmp_path, bad, why):
    years, hs = write(tmp_path, *BASE, bad)
    with pytest.raises(SystemExit, match=f"holidays.toml: .*{why}"):
        holidays.validate(years, hs, GLYPHS, EMBLEMS)


def test_overlaps_keep_file_order_and_windows_cross_the_year(tmp_path):
    years, hs = write(tmp_path, *BASE)
    days = holidays.calendar(years, hs)
    assert days["2026-12-26"] == ["boxing-day", "kwanzaa"]
    assert days["2026-12-25"] == ["christmas"]
    kwanzaa = [d for d, keys in days.items() if "kwanzaa" in keys and "2026-12-01" <= d <= "2027-01-31"]
    assert kwanzaa == ["2026-12-26", "2026-12-27", "2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31", "2027-01-01"]
    # Kwanzaa 2025 runs into the span's first day, after New Year in file order.
    assert days["2026-01-01"] == ["new-year", "kwanzaa"]
    # The span's last Kwanzaa runs past it, so "to" is in the year after.
    assert max(days) == "2028-01-01"


def test_a_holiday_on_two_rules_that_meet_is_listed_once(tmp_path):
    years, hs = write(tmp_path, *BASE, years="[2029, 2029]")
    days = holidays.calendar(years, hs)
    assert days["2029-11-11"] == ["remembrance"]  # 11 November 2029 is the second Sunday
    assert sum("remembrance" in keys for keys in days.values()) == 1


def test_table_dates_and_ranges_reach_the_calendar(tmp_path):
    fest = entry("fest", '"table"', TABLE + 'dates = { 2026 = "2026-09-19..2026-09-21", 2027 = "2027-09-18" }')
    years, hs = write(tmp_path, *BASE, fest)
    holidays.validate(years, hs, GLYPHS, EMBLEMS)
    days = holidays.calendar(years, hs)
    assert [d for d, keys in days.items() if "fest" in keys] == ["2026-09-19", "2026-09-20", "2026-09-21", "2027-09-18"]


def test_calendar_json_is_byte_stable_and_carries_its_span(tmp_path):
    years, hs = write(tmp_path, *BASE)
    text = holidays.calendar_json(years, hs)
    assert text == holidays.calendar_json(years, hs)
    assert text.endswith("}\n") and "\n" not in text[:-1]
    doc = json.loads(text)
    assert (doc["schema"], doc["tz"], doc["from"], doc["to"]) == (1, "Europe/London", "2026-01-01", "2028-01-01")
    assert doc["days"]["2026-12-26"] == ["boxing-day", "kwanzaa"]


def test_a_year_without_a_sourced_date_is_a_gap_not_a_guess(tmp_path):
    sources = 'source = ["https://example.org/a", "https://example.org/b"]\n'
    eid = entry("eid", '"table 3"', sources + 'dates = { 2026 = "2026-03-20" }')
    vesak = entry("vesak", '"table"', 'source = "https://example.org/v"')
    years, hs = write(tmp_path, *BASE, eid, vesak)
    holidays.validate(years, hs, GLYPHS, EMBLEMS)
    assert hs[5].sources == ("https://example.org/a", "https://example.org/b")
    assert holidays.gaps(years, hs) == ["eid: no sourced date for 2027", "vesak: no sourced date for 2026, 2027"]
    days = holidays.calendar(years, hs)
    assert [d for d, keys in days.items() if "eid" in keys] == ["2026-03-20", "2026-03-21", "2026-03-22"]
    assert not any("vesak" in keys for keys in days.values())


def test_the_real_calendar_validates_and_covers_every_sourced_year():
    from emblems import EMBLEMS as ART_EMBLEMS
    from motifs import GLYPHS as ART_GLYPHS

    years, hs = holidays.load()
    holidays.validate(years, hs, ART_GLYPHS, ART_EMBLEMS)
    assert len(hs) == 57
    gaps = holidays.gaps(years, hs)
    assert gaps == [
        "holi: no sourced date for 2028, 2029, 2030",
        "vesak: no sourced date for 2026, 2027, 2028, 2029, 2030",
        "raksha-bandhan: no sourced date for 2028, 2029, 2030",
        "oktoberfest: no sourced date for 2026, 2028, 2029, 2030",
        "navaratri: no sourced date for 2028, 2029, 2030",
        "diwali: no sourced date for 2028, 2029, 2030",
    ]
    unsourced = {(g.split(":")[0], y) for g in gaps for y in g.split("for ")[1].split(", ")}
    days = holidays.calendar(years, hs)
    for year in map(str, range(years[0], years[1] + 1)):
        present = {k for d, keys in days.items() if d.startswith(year) for k in keys}
        for h in hs:
            assert h.key in present or (h.key, year) in unsourced, (h.key, year)
    for keys in days.values():
        assert len(keys) == len(set(keys))
    overlaps = {y: sum(len(k) > 1 for d, k in days.items() if d.startswith(str(y))) for y in range(2026, 2031)}
    print("overlap days per year:", overlaps)


def test_the_real_calendar_rotates_known_overlaps_in_file_order():
    years, hs = holidays.load()
    days = holidays.calendar(years, hs)
    assert days["2026-12-26"] == ["boxing-day", "kwanzaa"]
    assert days["2027-12-25"] == ["hanukkah", "christmas"]  # Hanukkah begins on Christmas Day 2027
    assert days["2030-09-23"] == ["autumn-equinox"]  # 22 Sep 23:27 UTC is 23 Sep in London
