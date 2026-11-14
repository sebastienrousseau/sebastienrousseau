"""Holiday heroes: the everyday hero is untouched, every variant keeps the clock contract."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from xml.parsers import expat

import pytest

import build
import holidays
import palette
import panels
from theme import THEMES

ROOT = Path(__file__).resolve().parent.parent
CFG = tomllib.loads((ROOT / "profile.toml").read_text())
_, HOLIDAYS = holidays.load()
LIMIT = 60 * 1024  # bytes per hero
MODES = ("light", "dark")


def hero(key: str, mode: str) -> str:
    h = next(h for h in HOLIDAYS if h.key == key)
    return panels.hero(build.themed(h, mode), CFG["hero"]).render()  # with its icon, as built


@pytest.mark.parametrize("mode", MODES)
def test_the_everyday_hero_is_byte_identical(mode):
    committed = (ROOT / "assets" / f"hero-{mode}.svg").read_text()
    assert panels.hero(THEMES[mode], CFG["hero"]).render() == committed


@pytest.mark.parametrize("key", [h.key for h in HOLIDAYS])
def test_every_holiday_hero_keeps_the_contract(key):
    for mode in MODES:
        svg = hero(key, mode)
        expat.ParserCreate().Parse(svg, True)
        assert svg.count(panels.CLOCK_MARKER) == 1
        assert svg.index(panels.CLOCK_MARKER) < svg.index(panels.REDUCED_MOTION)
        for selector in ('class="hand ss"', 'class="hand hh"', 'class="hand mm"'):
            assert selector in svg
        assert set(re.findall(r"https?://[^\"' )]+", svg)) == {"http://www.w3.org/2000/svg"}
        assert len(svg.encode()) <= LIMIT, f"{key}-{mode}: {len(svg.encode())} bytes"


def test_a_holiday_hero_says_what_it_is_decorated_for():
    svg = hero("christmas", "light")
    assert "Decorated for Christmas." in svg.split("<title>")[1].split("</title>")[0]
    assert 'aria-label="' in svg and "Decorated for Christmas." in svg.split("aria-label=")[1][:600]


def test_every_lattice_point_becomes_a_glyph():
    everyday = panels.hero(THEMES["light"], CFG["hero"]).render()
    holiday = hero("christmas", "light")
    points = everyday.count("<circle ") - holiday.count("<circle ")
    assert holiday.count('<use href="#gl"') == points > 100
    assert holiday.count('<g id="gl">') == 1
    assert "rotate(" in holiday  # Christmas spins its snowflakes


def test_the_seconds_hand_hub_and_minute_ring_take_the_second_accent():
    t = palette.style(next(h for h in HOLIDAYS if h.key == "christmas"), "light")
    svg = panels.hero(t, CFG["hero"]).render()
    seconds = svg.split('<g class="hand ss">')[1].split("</g>")[0]
    assert t["accent2"] in seconds and t["accent"] not in seconds
    assert f'r="7" fill="{t["accent2"]}"' in svg
    assert f'r="{panels.BADGE}" fill="{t["panel"]}" stroke="{t["accent2"]}"' in svg  # minute badge
    assert f'r="{panels.BADGE}" fill="{t["panel"]}" stroke="{t["accent"]}"' in svg  # hour badge


def test_quiet_and_emblemless_themes():
    quiet = hero("remembrance", "dark")
    assert 'id="g2"' not in quiet  # no second glow
    assert 'opacity="0.35"' in quiet  # dimmed emblem
    assert 'id="g2"' in hero("christmas", "dark")
    plain = hero("burns-night", "light")  # emblem = "none" and an icon
    assert "<desc>Icon: thistle by Alan Davis" in plain
    assert "<desc>" not in hero("juneteenth", "light")  # the placeholder burst, no icon
    assert "scale(4.4)" in hero("juneteenth", "light")
    t = palette.style(next(h for h in HOLIDAYS if h.key == "ashura"), "light")
    assert "scale(4.4)" not in panels.hero(t, CFG["hero"]).render()  # without its icon, "none" draws nothing
    assert "scale(4.4)" in hero("ashura", "light")  # with it, the icon is drawn
