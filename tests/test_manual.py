"""The manual follows doc.dotfiles.io/manual/ (ssg and Lucid), built from the repository's own documents."""

from __future__ import annotations

import pytest

import manual

BASE = manual.BASE


@pytest.mark.parametrize(
    ("source", "text", "want"),
    [
        ("docs/index.md", "[a](ARCHITECTURE.md)", f"[a]({BASE}architecture/)"),
        ("docs/index.md", "[a](../DEVELOPMENT.md#tests)", f"[a]({BASE}development/#tests)"),
        ("DEVELOPMENT.md", "[a](docs/ARCHITECTURE.md)", f"[a]({BASE}architecture/)"),
        ("docs/DATA.md", "[a](index.md)", f"[a]({BASE})"),
        ("DEVELOPMENT.md", "[a](profile.toml)", f"[a]({manual.BLOB}profile.toml)"),
        ("docs/DATA.md", "[a](../tools/live.py)", f"[a]({manual.BLOB}tools/live.py)"),
        ("SECURITY.md", "[a](https://x.test/y.md)", "[a](https://x.test/y.md)"),
        ("SECURITY.md", "[a](#scope)", "[a](#scope)"),
        ("SECURITY.md", "[a](mailto:x@y.test)", "[a](mailto:x@y.test)"),
    ],
)
def test_links_point_at_manual_pages_or_github(source, text, want):
    assert manual.relink(text, source) == want


def test_every_page_comes_from_a_document_with_a_title():
    for source, *_ in manual.PAGES:
        assert (manual.ROOT / source).read_text().startswith("# "), source


def test_the_title_and_first_paragraph_move_to_the_layout():
    headline, lead, body = manual.split_page("# Title `x`\n\nFirst [line](a.md)\nwraps.\n\n## Part\n\nText.\n")
    assert (headline, lead) == ("Title x", "First [line](a.md) wraps.")
    assert body == "## Part\n\nText.\n"


def test_a_page_opening_with_a_list_has_no_lead():
    assert manual.split_page("# T\n\n* item\n")[1:] == ("", "* item\n")


def test_headings_outside_code_get_unique_ids():
    body = "## Fields\n\n```text\n## not a heading\n```\n\n## Fields\n\n## What's `new` & next\n"
    want = [("Fields", "fields"), ("Fields", "fields-2"), ("What's new & next", "whats-new-and-next")]
    assert manual.headings(body) == want


def pages() -> list[manual.Page]:
    return [manual.Page(*row, headline=f"H{n}") for n, row in enumerate(manual.PAGES)]


def test_side_nav_groups_pages_and_marks_the_current_one():
    ps = pages()
    nav = manual.side_nav(ps, ps[2])
    assert nav.count('class="side-h"') == 3
    assert f'<a href="{BASE}">Overview</a>' in nav
    assert f'<a href="{BASE}data/" aria-current="page">H2</a>' in nav


def test_pager_links_both_neighbours_and_skips_the_missing_one():
    ps = pages()
    assert "pager-prev" not in manual.pager(None, ps[1])
    both = manual.pager(ps[0], ps[2])
    assert f'href="{BASE}"' in both and f'href="{BASE}data/"' in both


def test_front_matter_carries_layout_navigation_and_footer():
    ps = pages()
    ps[1].toc = [("Modules", "modules")]
    fm = manual.front_matter(ps, 1, manual.shared(2026))
    assert fm["layout"] == "doc"
    assert fm["eyebrow"] == "Reference"
    assert fm["crumb_group"] == f'<li><a href="{BASE}architecture/">Reference</a></li>'
    assert fm["toc_items"] == '<li><a href="#modules">Modules</a></li>'
    assert fm["copyright_years"] == "© 2026" and fm["author_url"] == "https://sebastienrousseau.com/"
    assert "copy and visual identity are reserved" in fm["copyright_licence"]
    home = manual.front_matter(ps, 0, manual.shared(2026))
    assert home["eyebrow"].startswith("Manual · v0.0.") and home["crumb_group"] == ""
    assert home["cur_manual"] == ' aria-current="true"'


def test_generate_writes_one_page_per_document(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "SITE", tmp_path)
    manual.generate()
    names = sorted(p.name for p in (tmp_path / "content").iterdir())
    assert names == sorted(f"{page or 'index'}.md" for _, page, _ in manual.PAGES)
    data = (tmp_path / "content" / "data.md").read_text()
    assert data.startswith('---\nlayout: "doc"\n')
    assert 'headline: "profile.json"' in data


def test_anchor_gives_prose_headings_ids_once():
    page = '<div class="prose"><h2>Fields</h2><h3>Fields</h3><h2 id="x">Kept</h2></div>\n<nav class="pager">'
    out = manual.anchor(page)
    assert '<h2 id="fields">Fields</h2>' in out and '<h3 id="fields-2">Fields</h3>' in out
    assert '<h2 id="x">Kept</h2>' in out
    assert manual.anchor("<p>no prose</p>") == "<p>no prose</p>"


def built(tmp_path, footer: str, extra: str = "") -> None:
    for asset in manual.ASSETS:
        (tmp_path / asset).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / asset).write_text("x")
    for _, page, _ in manual.PAGES:
        html = tmp_path / page / "index.html" if page else tmp_path / "index.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(f'<html><h2 id="top">T</h2>{extra}<footer>{footer}</footer></html>')


def test_a_complete_build_has_no_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, f"© 2026 {manual.COPYRIGHT}", f'<a href="#top">t</a><a href="{BASE}data/#top">d</a>')
    assert manual.problems() == []


def test_a_page_without_the_author_link_is_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, "© 2026 Sebastien Rousseau")
    found = manual.problems()
    assert len(found) == len(manual.PAGES)
    assert found[0].endswith("no copyright line linked to sebastienrousseau.com")


def test_broken_links_and_fragments_are_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    links = f'<a href="#nowhere">a</a><a href="{BASE}missing/">b</a><a href="{BASE}data/#nope">c</a>'
    built(tmp_path, manual.COPYRIGHT, links)
    found = [p for p in manual.problems() if p.startswith("index.html")]
    assert found == [
        "index.html: dangling fragment #nowhere",
        f"index.html: broken link {BASE}missing/",
        f"index.html: {BASE}data/#nope has no #nope",
    ]


def test_missing_assets_and_pages_are_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    assert manual.problems()[0] == "skeletonic.min.css missing"
    assert "index: not built" in manual.problems()


def test_finish_adds_the_theme_and_drops_cname_and_highlighting(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, manual.COPYRIGHT)
    (tmp_path / "CNAME").write_text("")
    (tmp_path / "highlight.abc.css").write_text("x")
    page = tmp_path / "index.html"
    page.write_text('<link rel="stylesheet" href="/highlight.abc.css">' + page.read_text())
    assert manual.finish() == 0
    assert not (tmp_path / "CNAME").exists() and not (tmp_path / "highlight.abc.css").exists()
    assert "highlight" not in page.read_text()
    assert (tmp_path / "styles.css").read_bytes() == (manual.THEME / "styles.css").read_bytes()
    assert capsys.readouterr().out.strip() == f"manual: {len(manual.PAGES)} pages, 0 problems"


def test_main_takes_one_step_at_a_time(capsys):
    assert manual.main([]) == 2
    assert "usage" in capsys.readouterr().err
