"""The build writes the holiday heroes, their calendar and their credits."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import build
import credits
import holidays
import panels

ROOT = Path(__file__).resolve().parent.parent
CFG = tomllib.loads((ROOT / "profile.toml").read_text())
YEARS, HOLIDAYS = holidays.load()


def test_the_committed_calendar_is_the_one_holidays_toml_gives():
    committed = (ROOT / "assets" / "holidays.json").read_text()
    assert committed == holidays.calendar_json(YEARS, HOLIDAYS)
    doc = json.loads(committed)
    assert doc["schema"] == 1 and doc["from"] == "2026-01-01"


def test_every_holiday_gets_a_hero_job_in_both_modes():
    jobs = build.jobs(CFG, HOLIDAYS)
    assert {f"hero-{h.key}" for h in HOLIDAYS} <= set(jobs)
    assert len(list((ROOT / "assets").glob("hero-*.svg"))) == 2 * (len(HOLIDAYS) + 1)


def test_every_holiday_gets_a_clock_beside_its_hero():
    jobs = build.jobs(CFG, HOLIDAYS)
    assert {"clock"} | {f"clock-{h.key}" for h in HOLIDAYS} <= set(jobs)
    heroes = {p.name.removeprefix("hero-") for p in (ROOT / "assets").glob("hero-*.svg")}
    clocks = {p.name.removeprefix("clock-") for p in (ROOT / "assets").glob("clock-*.svg")}
    assert clocks == heroes and len(clocks) == 2 * (len(HOLIDAYS) + 1)


def test_a_dropped_holiday_takes_its_clocks_with_it(tmp_path):
    keep, drop = HOLIDAYS[0], HOLIDAYS[1]
    names = [f"clock-{h.key}" for h in (keep, drop)]
    panels.write({n: build.jobs(CFG, [keep, drop])[n] for n in names}, tmp_path)
    assert (tmp_path / f"clock-{drop.key}-light.svg").exists()
    panels.write({names[0]: build.jobs(CFG, [keep])[names[0]]}, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"clock-{keep.key}-dark.svg", f"clock-{keep.key}-light.svg"]


def test_credits_list_exactly_the_icons_in_use():
    text = credits.markdown(HOLIDAYS)
    with_icon = [h for h in HOLIDAYS if h.icon]
    assert text.count("| recoloured and resized |") == len(with_icon) == 53
    for h in with_icon:
        assert f"[{h.icon['title']}]({h.icon['url']})" in text
    for h in HOLIDAYS:
        if not h.icon:
            assert f"| {h.name} |" not in text, h.key
    assert (ROOT / "CREDITS.md").read_text() == text


def test_the_readme_credit_line_appears_only_with_icons():
    alts = {"hero": "h", "paper": "p", "desk": "d", "finale": "f"} | {
        f"section-{p['key']}": "s" for p in CFG["pillars"]
    }
    assert "CREDITS.md" not in build.page(CFG, alts)
    line = build.page(CFG, alts, credits.creator_count(HOLIDAYS))
    assert f"by {credits.creator_count(HOLIDAYS)} creators" in line and "CREDITS.md" in line


def test_a_dropped_holiday_takes_its_heroes_with_it(tmp_path):
    keep, drop = HOLIDAYS[0], HOLIDAYS[1]
    panels.write({f"hero-{h.key}": build.jobs(CFG, [h])[f"hero-{h.key}"] for h in (keep, drop)}, tmp_path)
    assert (tmp_path / f"hero-{drop.key}-dark.svg").exists()
    panels.write({f"hero-{keep.key}": build.jobs(CFG, [keep])[f"hero-{keep.key}"]}, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"hero-{keep.key}-dark.svg", f"hero-{keep.key}-light.svg"]


def test_themed_adds_the_pinned_icon_and_its_credit():
    christmas = next(h for h in HOLIDAYS if h.key == "christmas")
    t = build.themed(christmas, "light")
    assert t["icon_svg"].startswith('<g transform="scale(') and 'fill="currentColor"' in t["icon_svg"]
    assert t["icon_credit"] == (
        "Icon: Christmas tree by Mustiana Kartika, Noun Project, royalty-free (NounPro), recoloured."
    )
    juneteenth = next(h for h in HOLIDAYS if h.key == "juneteenth")
    assert "icon_svg" not in build.themed(juneteenth, "light")
