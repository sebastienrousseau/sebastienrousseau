"""Holiday colours reproduce the approved proposal and meet their contrast targets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import holidays
import palette
from theme import THEMES

GOLDEN = Path(__file__).parent / "fixtures" / "palettes.json"
MODES = ("light", "dark")
_, HOLIDAYS = holidays.load()


def golden() -> dict[str, dict]:
    """The proposal gallery's tokens per key, from the prototype's render.py."""
    return {entry["key"]: entry["modes"] for entry in json.loads(GOLDEN.read_text())}


@pytest.mark.parametrize("mode", MODES)
def test_every_holiday_matches_the_proposal(mode):
    want = golden()
    assert len(HOLIDAYS) == 57
    for h in HOLIDAYS:
        expected = {k: v for k, v in want[h.key][mode].items() if k != "contrast"}
        got = palette.tokens(h.accent[mode], h.accent2[mode], mode)
        assert got == expected, h.key


@pytest.mark.parametrize("mode", MODES)
def test_every_theme_meets_its_contrast_targets(mode):
    lows = {"accent": 99.0, "mute": 99.0, "ink": 99.0, "accent2": 99.0}
    for h in HOLIDAYS:
        t = palette.style(h, mode)
        for key in lows:
            lows[key] = min(lows[key], palette.contrast(t[key], t["panel"]))
    assert lows["accent"] >= 4.5
    assert lows["mute"] >= 4.5
    assert lows["ink"] >= 7
    assert lows["accent2"] >= 3
    print(f"contrast minimums ({mode}): " + ", ".join(f"{k} {v:.2f}" for k, v in lows.items()))


def test_style_dresses_a_copy_of_the_everyday_theme():
    christmas = next(h for h in HOLIDAYS if h.key == "christmas")
    before = dict(THEMES["light"])
    t = palette.style(christmas, "light")
    assert THEMES["light"] == before
    assert t["page"] == before["page"]
    assert (t["glyph"], t["spin"], t["emblem"], t["name"]) == ("snowflake", True, "tree", "Christmas")
    assert (t["glow_alpha"], t["glow2_alpha"], t["emblem_alpha"]) == (0.28, 0.16, 0.5)


def test_quiet_themes_dim_their_glows_and_emblem():
    remembrance = next(h for h in HOLIDAYS if h.key == "remembrance")
    t = palette.style(remembrance, "dark")
    assert (t["glow_alpha"], t["glow2_alpha"], t["emblem_alpha"]) == (0.14, 0, 0.35)


def test_a_greyish_accent_gets_a_glow_saturated_in_proportion():
    # #806060 has HLS saturation 0.143 (under the 0.3 cut), so the glow
    # takes 1.6 times it, 0.229, at lightness 0.65: #ba9191.
    assert palette.glow("#806060", "light") == "#ba9191"
    # Dark mode takes three quarters of that saturation, at lightness 0.53.
    assert palette.glow("#806060", "dark") == "#9c7373"


def test_colour_helpers():
    assert palette.mix("#000000", "#ffffff", 0.5) == "#808080"
    assert palette.hexc([1.2, -0.1, 0.5]) == "#ff0080"
    assert round(palette.contrast("#000000", "#ffffff"), 2) == 21.0
    # Already readable: ensure() returns the colour unchanged.
    assert palette.ensure("#000000", "#ffffff", 4.5, "light") == "#000000"
