"""Icon intake: an allowlist sanitiser, deterministic output, a hash pin."""

from __future__ import annotations

from pathlib import Path
from xml.parsers import expat

import pytest

import icons

FIXTURES = Path(__file__).parent / "fixtures" / "icons"


def test_a_free_download_loses_its_credit_band_colours_and_metadata():
    out = icons.sanitise((FIXTURES / "noun-star-123.svg").read_bytes())
    # 100 x 125 with a dropped <text>: cropped to the square 100 x 100 drawing.
    assert out.startswith('<g transform="scale(1) translate(-50 -50)" fill="currentColor"><g>')
    assert "Ada" not in out and "<title>" not in out and "#000000" not in out and "style" not in out
    assert "class" not in out
    assert 'd="M50 10.4L61.2 40H90L66.8 58l9 30L50 70 24.2 88l9-30L10 40h28.8z"' in out  # one decimal
    expat.ParserCreate().Parse(f'<svg xmlns="http://www.w3.org/2000/svg">{out}</svg>', True)


def test_a_pro_download_is_scaled_into_the_100_unit_box():
    out = icons.sanitise((FIXTURES / "noun_Pro_456.svg").read_bytes())
    assert out.startswith('<g transform="scale(0.0277778) translate(-1800 -1800)" fill="currentColor">')
    assert 'fill-rule="evenodd"' in out
    assert "c795.3 0 1440 644.7 1440 1440" in out


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("noun-script-1.svg", "<script"),
        ("noun-href-2.svg", "href"),
        ("noun-doctype-3.svg", "<!DOCTYPE"),
        ("noun-clip-4.svg", "refused <clipPath>"),
    ],
)
def test_unsafe_or_complex_icons_are_refused_by_name(name, why):
    with pytest.raises(SystemExit, match=why):
        icons.sanitise((FIXTURES / name).read_bytes())


def test_intake_writes_a_pinned_file_and_the_same_bytes_every_time(tmp_path):
    line = icons.intake("halloween", FIXTURES / "noun-star-123.svg", {}, art=tmp_path)
    first = (tmp_path / "halloween.svg").read_bytes()
    assert icons.intake("halloween", FIXTURES / "noun-star-123.svg", {}, art=tmp_path) == line
    assert (tmp_path / "halloween.svg").read_bytes() == first
    assert 'creator = "Ada Lovelace"' in line  # read from the credit text
    assert 'title = "Star"' in line
    assert 'url = "https://thenounproject.com/icon/star-123/"' in line
    assert f'sha256 = "{icons.sha256(first.decode())}"' in line


def test_a_pro_file_needs_its_creator_and_takes_the_given_title(tmp_path):
    with pytest.raises(SystemExit, match="names no creator"):
        icons.intake("christmas", FIXTURES / "noun_Pro_456.svg", {}, art=tmp_path)
    line = icons.intake(
        "christmas", FIXTURES / "noun_Pro_456.svg", {"creator": "Grace Hopper", "title": "Circle"}, art=tmp_path
    )
    assert 'id = "456", title = "Circle", creator = "Grace Hopper"' in line


def test_a_file_not_named_like_a_noun_project_download_is_refused(tmp_path):
    odd = tmp_path / "star.svg"
    odd.write_bytes((FIXTURES / "noun-star-123.svg").read_bytes())
    with pytest.raises(SystemExit, match="not a Noun Project file name"):
        icons.intake("christmas", odd, {"creator": "Ada"}, art=tmp_path)


def test_load_returns_the_markup_and_the_pin_catches_a_one_byte_change(tmp_path):
    icons.intake("easter", FIXTURES / "noun-star-123.svg", {}, art=tmp_path / "art" / "icons")
    text = (tmp_path / "art" / "icons" / "easter.svg").read_text()
    pin = {"file": "art/icons/easter.svg", "sha256": icons.sha256(text)}
    markup = icons.load(pin, root=tmp_path)
    assert markup.startswith('<g transform="scale(1)') and markup.endswith("</g>")
    (tmp_path / "art" / "icons" / "easter.svg").write_text(text.replace("10.4", "10.5"))
    with pytest.raises(SystemExit, match="sha256 does not match"):
        icons.load(pin, root=tmp_path)


def test_main_checks_the_key_exists(capsys):
    with pytest.raises(SystemExit, match="no holiday 'comet'"):
        icons.main(["comet", str(FIXTURES / "noun-star-123.svg")])
