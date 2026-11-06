"""The smoke check sees what a visitor sees: every image is a well-formed SVG."""

from __future__ import annotations

from pathlib import Path

import pytest

import net
import smoke

ROOT = Path(__file__).resolve().parent.parent
GOOD = b'<svg xmlns="http://www.w3.org/2000/svg"><title>x</title></svg>'
DATA = b'{"schema": 1}'


def test_svg_error_accepts_svg_and_names_the_fault():
    assert smoke.svg_error(GOOD) is None
    assert smoke.svg_error(b'<svg aria-label="a "b" c"/>').startswith("malformed SVG")
    assert smoke.svg_error(b"<html><body>Not found</body></html>") == "root element is html, not svg"
    assert smoke.svg_error(b"").startswith("malformed SVG")


def test_every_committed_asset_is_well_formed():
    paths = sorted((ROOT / "assets").glob("*.svg"))
    assert paths
    assert [p.name for p in paths if smoke.svg_error(p.read_bytes())] == []


def test_readme_images_pass_when_every_url_serves_svg(monkeypatch):
    asked: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        smoke, "get", lambda url, follow=True: asked.append((url, follow)) or (DATA if url.endswith(".json") else GOOD)
    )
    assert smoke.main() == 0
    assert asked and all(follow is False for _, follow in asked)
    assert any("/api/clock/hero-" in url for url, _ in asked)
    assert any("/profile-data/" in url for url, _ in asked)


def test_a_redirect_or_bad_svg_fails_the_check(monkeypatch, capsys):
    def get(url, follow=True):
        if "/api/clock/" in url:
            raise net.FetchError(f"{url} returned HTTP 302")
        if url.endswith(".json"):
            return DATA
        return b"<svg" if "article-2" in url else GOOD

    monkeypatch.setattr(smoke, "get", get)
    assert smoke.main() == 1
    out = capsys.readouterr().out
    assert out.count("::error::") == 4  # two clock themes, two article-2 themes
    assert "returned HTTP 302" in out and "malformed SVG" in out


def test_a_missing_local_asset_fails(tmp_path):
    assert smoke.check("assets/no-such-panel-dark.svg") == "missing: assets/no-such-panel-dark.svg"


@pytest.mark.parametrize(("follow", "flag"), [(True, True), (False, False)])
def test_net_follows_redirects_only_when_asked(monkeypatch, follow, flag):
    seen: list[list[str]] = []

    class Done:
        stdout = b"x\n200 "

    monkeypatch.setattr(net.subprocess, "run", lambda cmd, **_: seen.append(cmd) or Done())
    assert net.get("https://example.test/a.svg", follow=follow) == b"x"
    assert ("-L" in seen[0]) is flag


def test_profile_json_must_parse_with_a_schema(monkeypatch):
    replies = {"good": b'{"schema": 1}', "html": b"<html>Not found</html>", "bare": b"[1, 2]"}
    monkeypatch.setattr(smoke, "get", lambda url, follow=True: replies[url.split("/")[-2]])
    assert smoke.check("https://x.test/good/profile.json") is None
    assert smoke.check("https://x.test/html/profile.json").startswith("not JSON")
    assert smoke.check("https://x.test/bare/profile.json") == "no schema field"


def test_the_readme_links_profile_json_and_the_smoke_check_reads_it(monkeypatch):
    asked: list[str] = []

    def get(url, follow=True):
        asked.append(url)
        return b'{"schema": 1}' if url.endswith(".json") else GOOD

    monkeypatch.setattr(smoke, "get", get)
    assert smoke.main() == 0
    assert any(url.endswith("/profile-data/profile.json") for url in asked)
