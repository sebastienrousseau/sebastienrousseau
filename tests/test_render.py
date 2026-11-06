"""Rendering: the README points at the live branch, panels fit, orphans go."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from xml.parsers import expat

import pytest

import articles
import build
import live
import panels
from fonts import width
from theme import THEMES

ROOT = Path(__file__).resolve().parent.parent
CFG = tomllib.loads((ROOT / "profile.toml").read_text())
CARD = '<p class="card-eyebrow">{topic}</p><h2><a href="/{day}-{slug}/">{title}</a></h2><time datetime="{day}">'


def index(*rows: tuple[str, str, str]) -> str:
    return "".join(CARD.format(day=d, slug=d, title=t, topic=p) for d, t, p in rows)


def test_articles_newest_first_and_unescaped():
    text = index(
        ("2026-08-02", "Old", "AI"),
        ("2026-08-04", "Newest &amp; best", "Policy &amp; Resilience"),
        ("2026-08-03", "Middle", "AI"),
        ("2026-07-01", "Oldest", "AI"),
    )
    got = articles.parse("https://site.test", text)
    assert [a["title"] for a in got] == ["Newest & best", "Middle", "Old"]
    assert got[0] == {
        "title": "Newest & best",
        "topic": "POLICY & RESILIENCE",
        "date": "4 August 2026",
        "url": "https://site.test/2026-08-04-2026-08-04/",
    }


def test_articles_markup_change_is_loud():
    with pytest.raises(ValueError, match="markup changed"):
        articles.parse("https://site.test", index(("2026-08-02", "Only", "AI")))


def test_readme_takes_live_panels_from_the_data_branch():
    readme = build.page(CFG, {k: k for k in build.jobs(CFG)})
    base = CFG["live"]
    assert base.endswith("/profile-data/assets")
    for name in ("numbers", "article-1", "article-2", "article-3"):
        assert f'srcset="{base}/{name}-dark.svg"' in readme
        assert f'src="{base}/{name}-light.svg"' in readme
    assert 'src="assets/numbers' not in readme


def test_article_with_quotes_is_well_formed_svg():
    # Titles come from the live site; a double quote must not end the aria-label attribute.
    text = index(
        ("2026-08-04", "Why &quot;quantum-safe&quot; isn&#39;t &lt;optional&gt;", "Policy &amp; Risk"),
        ("2026-08-03", "Middle", "AI"),
        ("2026-08-02", "Old", "AI"),
    )
    a = articles.parse("https://site.test", text)[0]
    seen: dict[str, str] = {}
    parser = expat.ParserCreate()
    parser.StartElementHandler = lambda tag, attrs: seen.setdefault(tag, attrs.get("aria-label", ""))
    parser.Parse(panels.article(THEMES["dark"], a).render(), True)  # raises ExpatError if malformed
    assert seen["svg"] == 'POLICY & RISK. Why "quantum-safe" isn\'t <optional> 4 August 2026.'


def test_hero_keeps_the_clock_worker_contract():
    # The profile-clock Worker (sebastienrousseau.github.io, workers/clock.js,
    # clockCSS) replaces the marker with rules for exactly these selectors. If
    # one goes, the live clock freezes with no error, so pin them here.
    svg = panels.hero(THEMES["dark"], CFG["hero"]).render()
    assert svg.count(panels.CLOCK_MARKER) == 1
    classes = set(re.findall(r'class="([^"]+)"', svg))
    for unit in ("hh", "mm", "ss"):
        assert f"hand {unit}" in classes
        assert f".{unit}{{animation-duration:" in svg


def test_numbers_note_fits_on_one_line():
    note = f"{CFG['numbers']['note']} Updated 30 September 2026."
    assert width(panels.SANS, note, 14) < panels.W - 160


def test_hero_honours_reduced_motion():
    svg = panels.hero(THEMES["dark"], CFG["hero"]).render()
    assert svg.index(panels.CLOCK_MARKER) < svg.index("prefers-reduced-motion")
    rule = panels.REDUCED_MOTION
    # The seconds sweep and the digit roll pause; the hour and minute hands keep turning.
    assert ".ss,.roll{animation-play-state:paused!important}" in rule
    assert "animation:none" not in rule
    assert ".hh" not in rule
    assert ".mm" not in rule


def test_live_render_writes_both_themes_and_prunes(tmp_path):
    day = "2026-11-05"
    regs = {"packages": 10, "all_time": 1_234_567, "recent": 8_900}
    items = [{"title": f"T{n}", "topic": "AI", "date": "5 November 2026", "url": "https://x.test"} for n in (1, 2, 3)]
    src = {
        "github": {"value": {"stars": 700}, "as_of": day},
        "crates": {"value": regs, "as_of": day},
        "pypi": {"value": regs, "as_of": day},
        "npm": {"value": regs, "as_of": "2026-11-04"},
        "articles": {"value": {"items": items}, "as_of": day},
    }
    (tmp_path / "assets").mkdir()
    orphan = tmp_path / "assets" / "article-4-dark.svg"
    orphan.write_text("<svg/>")
    live.render(CFG, src, tmp_path)
    names = sorted(p.name for p in (tmp_path / "assets").iterdir())
    assert len(names) == 8 and not orphan.exists()
    numbers = (tmp_path / "assets" / "numbers-light.svg").read_text()
    assert "3.7M All-time downloads" in numbers
    assert "Updated 4 November 2026." in numbers
