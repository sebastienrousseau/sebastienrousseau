"""The glyph and emblem library: well-formed, currentColor only, and all of it in use."""

from __future__ import annotations

import re
from xml.parsers import expat

import pytest

import holidays
from emblems import EMBLEMS
from motifs import GLYPHS, petals, rays, star

NS = "http://www.w3.org/2000/svg"
ART = [("glyph", k, v) for k, v in GLYPHS.items()] + [("emblem", k, v) for k, v in EMBLEMS.items()]
PAINT = re.compile(r'(?:fill|stroke|color|stop-color)="([^"]*)"')
_, HOLIDAYS = holidays.load()


@pytest.mark.parametrize(("kind", "key", "markup"), ART, ids=[f"{k}:{n}" for k, n, _ in ART])
def test_art_is_well_formed_and_paints_only_with_current_color(kind, key, markup):
    tags: set[str] = set()
    parser = expat.ParserCreate()
    parser.StartElementHandler = lambda tag, _attrs: tags.add(tag)
    parser.Parse(f'<svg xmlns="{NS}">{markup}</svg>', True)  # raises on malformed markup
    assert tags.isdisjoint({"text", "script", "style", "image", "use", "foreignObject"}), (kind, key)
    assert "href" not in markup and "style=" not in markup, (kind, key)
    assert set(PAINT.findall(markup)) <= {"currentColor", "none"}, (kind, key)


def test_every_glyph_and_emblem_named_by_a_holiday_exists():
    for h in HOLIDAYS:
        assert h.glyph in GLYPHS, h.key
        assert h.emblem in EMBLEMS or h.emblem == "none", h.key


def test_every_glyph_and_emblem_in_the_library_is_used():
    assert {h.glyph for h in HOLIDAYS} | {"dot"} == set(GLYPHS)
    assert {h.emblem for h in HOLIDAYS} - {"none"} == set(EMBLEMS)


def test_star_alternates_outer_and_inner_points_from_the_top():
    pts = star(4, 10, 5).split()
    assert len(pts) == 8
    assert pts[0] == "0.00,-10.00"  # the first point is straight up
    assert pts[1] == "3.54,-3.54"  # then an inner point, 45 degrees on


def test_petals_start_at_the_top_and_go_round():
    assert petals(2, 5, 3) == '<circle cx="0.00" cy="-5.00" r="3"/><circle cx="0.00" cy="5.00" r="3"/>'


def test_rays_are_rounded_lines_in_one_group():
    out = rays(2, 1, 2, 0.5)
    assert out.startswith('<g stroke="currentColor" stroke-width="0.5" stroke-linecap="round">')
    assert out.count("<line ") == 2
    assert '<line x1="1.00" y1="0.00" x2="2.00" y2="0.00"/>' in out
