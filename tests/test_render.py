"""Rendering: the README points at the live branch, panels fit, orphans go."""

from __future__ import annotations

import json
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
        "published": "2026-08-04",
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
    cards = [r["name"] for p in CFG["pillars"] for r in p["repos"]]
    assert len(names) == 2 * (1 + 3 + len(cards)) and not orphan.exists()
    assert f"card-{cards[0]}-dark.svg" in names
    numbers = (tmp_path / "assets" / "numbers-light.svg").read_text()
    assert "3.7M All-time downloads" in numbers
    assert "Updated 4 November 2026." in numbers


KYBER = "https://github.com/sebastienrousseau/kyberlib"


def card_src(github_by: dict | None, crates_by: dict | None) -> dict:
    day = {"as_of": "2026-11-05"}
    empty = {"packages": 0, "all_time": 0, "recent": 0}
    gh = {"stars": 9} | ({"by": github_by} if github_by is not None else {})
    crates = empty | ({"by": crates_by} if crates_by is not None else {})
    return {"github": {"value": gh, **day}, "crates": {"value": crates, **day}, "pypi": {"value": empty, **day}}


def test_card_stats_sum_every_package_from_the_repo():
    by = {
        "kyberlib": {"repo": "kyberlib", "all_time": 41_000},
        "kyberlib-wasm": {"repo": "kyberlib", "all_time": 2_500},
        "hsh": {"repo": "hsh", "all_time": 9},
    }
    src = card_src({"kyberlib": 1234}, by)
    assert live.card_stats(src, "kyberlib") == "1.2K stars · 43.5K downloads"
    assert live.card_stats(src, "KyberLib") == "1.2K stars · 43.5K downloads"


def test_card_stats_without_packages_show_stars_alone():
    assert live.card_stats(card_src({"passmcp": 1}, {}), "passmcp") == "1 star"


def test_card_stats_leave_out_a_zero():
    # A zero is no evidence of anything; the card keeps just its language.
    assert live.card_stats(card_src({"passmcp": 0}, {}), "passmcp") == ""
    by = {"kyberlib": {"repo": "kyberlib", "all_time": 255}}
    assert live.card_stats(card_src({"kyberlib": 0}, by), "kyberlib") == "255 downloads"
    by0 = {"kyberlib": {"repo": "kyberlib", "all_time": 0}}
    assert live.card_stats(card_src({"kyberlib": 3}, by0), "kyberlib") == "3 stars"


def test_card_stats_survive_state_from_before_per_repo_figures():
    # The first run after this change starts from state with no "by"; a failed source keeps that.
    assert live.card_stats(card_src(None, None), "kyberlib") == ""
    assert live.card_stats(card_src({}, None), "kyberlib") == ""


def test_card_stats_fit_beside_the_language_label():
    # Widest realistic line against the widest language label, with a gap.
    stats = "88.8K stars · 888.8M downloads"
    lang = max((r["lang"] for p in CFG["pillars"] for r in p["repos"]), key=lambda x: width(panels.MED, x, 17))
    left_edge = 68 + width(panels.MED, lang, 17)
    assert panels.CARD_STATS_RIGHT - width(panels.SANS, stats, 17) > left_edge + 24


def test_card_shows_its_stats_and_keeps_its_alt_text():
    repo = CFG["pillars"][1]["repos"][0]
    plain = panels.card(THEMES["dark"], repo)
    live_card = panels.card(THEMES["dark"], repo, "1.2K stars · 43.5K downloads")
    assert "1.2K stars · 43.5K downloads" in live_card.render()
    assert live_card.title == plain.title == panels.card_alt(repo)


def test_readme_takes_cards_from_the_data_branch():
    readme = build.page(CFG, {k: k for k in build.jobs(CFG)})
    name = CFG["pillars"][0]["repos"][0]["name"]
    assert f'srcset="{CFG["live"]}/card-{name}-dark.svg"' in readme
    assert f'src="assets/card-{name}' not in readme
    assert not any(k.startswith("card-") for k in build.jobs(CFG))


def full_src() -> dict:
    day = "2026-11-05"
    regs = {"packages": 10, "all_time": 1_234_567, "recent": 8_900}
    crates = regs | {"by": {"kyberlib": {"repo": "kyberlib", "all_time": 41_000}}}
    items = [
        {"title": "T1", "topic": "AI", "date": "5 November 2026", "url": "https://x.test/a", "published": day},
        {"title": "T2", "topic": "AI", "date": "4 November 2026", "url": "https://x.test/b"},
    ]
    return {
        "github": {"value": {"stars": 700, "by": {"kyberlib": 45}}, "as_of": day},
        "crates": {"value": crates, "as_of": day},
        "pypi": {"value": regs, "as_of": day},
        "npm": {"value": regs, "as_of": "2026-11-04"},
        "articles": {"value": {"items": items}, "as_of": day},
    }


def test_profile_json_carries_the_live_figures_as_numbers():
    doc = live.profile_json(CFG, full_src())
    assert doc["schema"] == 1
    assert doc["site"] == CFG["site"] and doc["github"] == CFG["github"]
    assert doc["numbers"] == {
        "all_time_downloads": 3_703_701,
        "recent_downloads": 26_700,
        "window_days": 30,
        "github_stars": 700,
        "packages": 30,
        "as_of": "2026-11-04",
    }
    repos = {r["name"]: r for p in doc["pillars"] for r in p["repos"]}
    assert repos["kyberlib"]["stars"] == 45 and repos["kyberlib"]["downloads"] == 41_000
    assert repos["kyberlib"]["url"] == f"{CFG['github']}/kyberlib"
    assert repos["passmcp"]["stars"] is None and repos["passmcp"]["downloads"] == 0
    assert [a.get("published") for a in doc["articles"]] == ["2026-11-05", None]


def test_render_writes_profile_json_beside_the_panels(tmp_path):
    live.render(CFG, full_src(), tmp_path)
    doc = json.loads((tmp_path / "profile.json").read_text())
    assert doc["numbers"]["github_stars"] == 700
    assert len(doc["pillars"]) == len(CFG["pillars"])


def test_articles_carry_an_iso_date_for_machines():
    got = articles.parse(
        "https://site.test", index(("2026-08-04", "A", "AI"), ("2026-08-03", "B", "AI"), ("2026-08-02", "C", "AI"))
    )
    assert got[0]["published"] == "2026-08-04" and got[0]["date"] == "4 August 2026"


def test_readme_points_agents_at_profile_json():
    readme = build.page(CFG, {k: k for k in build.jobs(CFG)})
    assert f"{CFG['live'].removesuffix('/assets')}/profile.json" in readme
