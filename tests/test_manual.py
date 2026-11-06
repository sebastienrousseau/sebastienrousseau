"""The manual is built from the repository's own documents and always carries the author link."""

from __future__ import annotations

import pytest

import manual

BASE = manual.BASE


@pytest.mark.parametrize(
    ("source", "text", "want"),
    [
        ("docs/index.md", "[a](ARCHITECTURE.md)", f"[a]({BASE}/architecture/)"),
        ("docs/index.md", "[a](../DEVELOPMENT.md#tests)", f"[a]({BASE}/development/#tests)"),
        ("DEVELOPMENT.md", "[a](docs/ARCHITECTURE.md)", f"[a]({BASE}/architecture/)"),
        ("docs/index.md", "[a](index.md)", f"[a]({BASE}/)"),
        ("DEVELOPMENT.md", "[a](profile.toml)", f"[a]({manual.BLOB}profile.toml)"),
        ("docs/DATA.md", "[a](../tools/live.py)", f"[a]({manual.BLOB}tools/live.py)"),
        ("SECURITY.md", "[a](https://x.test/y.md)", "[a](https://x.test/y.md)"),
        ("SECURITY.md", "[a](#scope)", "[a](#scope)"),
        ("SECURITY.md", "[a](mailto:x@y.test)", "[a](mailto:x@y.test)"),
    ],
)
def test_links_point_at_manual_pages_or_github(source, text, want):
    assert manual.relink(text, source) == want


def test_every_page_comes_from_a_document_that_exists():
    for source, *_ in manual.PAGES:
        assert (manual.ROOT / source).is_file(), source


def test_generate_writes_front_matter_navigation_and_year(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "SITE", tmp_path)
    manual.generate()
    page = (tmp_path / "content" / "data.md").read_text()
    assert page.startswith('---\ntitle: "Data"\n')
    assert "layout: page\n---\n\n# profile.json" in page
    nav = (tmp_path / "data" / "nav.toml").read_text()
    assert nav.count("[[links]]") == len(manual.PAGES)
    assert 'url = "/"' in nav and 'url = "/changelog/"' in nav
    assert (tmp_path / "data" / "build.toml").read_text().startswith("year = 20")


def built(tmp_path, footer: str) -> None:
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "style.css").write_text("body{}")
    for _, page, _, _ in manual.PAGES:
        html = tmp_path / manual.url_of(page).strip("/") / "index.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(f"<html><footer>{footer}</footer></html>")


def test_a_complete_build_has_no_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, f"&copy; 2026 {manual.COPYRIGHT}")
    assert manual.problems() == []


def test_a_page_without_the_author_link_is_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, "&copy; 2026 Sebastien Rousseau")
    assert len(manual.problems()) == len(manual.PAGES)
    assert manual.problems()[0].endswith("no copyright line linked to sebastienrousseau.com")


def test_missing_pages_and_stylesheet_are_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    assert manual.problems()[:2] == ["css/style.css missing", "index: not built"]


def test_finish_drops_the_empty_cname_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(manual, "OUT", tmp_path)
    built(tmp_path, f"&copy; 2026 {manual.COPYRIGHT}")
    (tmp_path / "CNAME").write_text("")
    assert manual.finish() == 0
    assert not (tmp_path / "CNAME").exists()
    assert (tmp_path / "css" / "style.css").read_text() == (manual.SITE / "static" / "style.css").read_text()
    assert capsys.readouterr().out.strip() == f"manual: {len(manual.PAGES)} pages, 0 problems"


def test_main_takes_one_step_at_a_time(capsys):
    assert manual.main([]) == 2
    assert "usage" in capsys.readouterr().err
