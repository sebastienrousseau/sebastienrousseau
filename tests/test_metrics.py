"""npm history is fetched once; a normal run makes one call per package."""

from __future__ import annotations

import datetime as dt

import pytest

import metrics
from net import FetchError

CREATED = dt.date(2023, 1, 1)


def downloads(start: dt.date, end: dt.date) -> int:
    """The fake registry: one download a day."""
    return max((end - start).days + 1, 0)


@pytest.fixture
def calls(monkeypatch):
    """Fake npm and record every query as (kind, span)."""
    seen: list[tuple[str, str]] = []

    def span_dates(span: str) -> tuple[dt.date, dt.date]:
        a, _, b = span.partition(":")
        return dt.date.fromisoformat(a), dt.date.fromisoformat(b)

    def point(span: str, pkg: str) -> int:
        seen.append(("point", span))
        return downloads(*span_dates(span))

    def days(span: str, pkg: str) -> list[tuple[dt.date, int]]:
        seen.append(("range", span))
        a, b = span_dates(span)
        assert (b - a).days <= metrics.NPM_SPAN, "npm range queries cover at most 540 days"
        return [(a + dt.timedelta(days=i), 1) for i in range((b - a).days + 1)]

    monkeypatch.setattr(metrics, "get_json", lambda url, **kw: {"time": {"created": f"{CREATED}T10:00:00.000Z"}})
    monkeypatch.setattr(metrics, "_npm_point", point)
    monkeypatch.setattr(metrics, "_npm_days", days)
    return seen


def test_first_run_walks_history_then_one_range(calls):
    today = dt.date(2026, 11, 5)
    entry, total, recent = metrics.npm_package("pkg", {}, today)
    assert total == downloads(CREATED, today)
    assert recent == 30
    assert entry == {"closed_through": "2026-10-03", "closed": downloads(CREATED, dt.date(2026, 10, 3))}
    assert calls[0] == ("point", "2023-01-01:2024-06-23")  # 540 days
    assert [k for k, _ in calls].count("range") == 1
    assert calls[-1][0] == "range" and calls[-1][1].endswith(":2026-11-05")


def test_next_run_is_one_call(calls):
    entry, _, _ = metrics.npm_package("pkg", {}, dt.date(2026, 11, 5))
    calls.clear()
    again, total, recent = metrics.npm_package("pkg", entry, dt.date(2026, 11, 6))
    assert calls == [("range", "2026-10-04:2026-11-06")]
    assert again["closed_through"] == "2026-10-04"
    assert total == downloads(CREATED, dt.date(2026, 11, 6))
    assert recent == 30


def test_same_day_rerun_changes_nothing(calls):
    entry, total, _ = metrics.npm_package("pkg", {}, dt.date(2026, 11, 5))
    again, total2, _ = metrics.npm_package("pkg", entry, dt.date(2026, 11, 5))
    assert (again, total2) == (entry, total)


def test_young_package_needs_no_point_queries(calls, monkeypatch):
    monkeypatch.setattr(metrics, "get_json", lambda url, **kw: {"time": {"created": "2026-10-20T00:00:00.000Z"}})
    entry, total, recent = metrics.npm_package("new", {}, dt.date(2026, 11, 5))
    assert calls == [("range", "2026-10-20:2026-11-05")]
    assert total == recent == 17
    assert entry == {"closed_through": "2026-10-19", "closed": 0}


def test_packages_older_than_npm_counts_start_at_the_epoch(calls, monkeypatch):
    monkeypatch.setattr(metrics, "get_json", lambda url, **kw: {"time": {"created": "2012-03-04T00:00:00.000Z"}})
    metrics.npm_package("old", {}, dt.date(2016, 1, 1))
    assert calls[0][1].startswith("2015-01-10:")


def cached(day: str, total: int = 10, recent: int = 3) -> dict:
    return {"closed_through": "2026-10-01", "closed": 7, "total": total, "recent": recent, "as_of": day}


@pytest.fixture
def registry(monkeypatch):
    """Packages a, b, c; package `b` is refused. Returns the names asked for."""
    monkeypatch.setattr(metrics, "npm_packages", lambda: ["a", "b", "c"])
    monkeypatch.setattr(metrics, "utc_today", lambda: dt.date(2026, 11, 5))
    asked: list[str] = []

    def package(name, entry, today):
        asked.append(name)
        if name == "b":
            raise FetchError("https://api.npmjs.org/b returned HTTP 429")
        return {"closed_through": "2026-10-03", "closed": 5}, 100, 40

    monkeypatch.setattr(metrics, "npm_package", package)
    return asked


def test_first_failure_stops_npm_and_keeps_progress(registry):
    ledger: dict = {}
    with pytest.raises(FetchError, match="2 of 3 npm packages not fetched yet"):
        metrics.npm(ledger)
    assert registry == ["a", "b"]
    assert ledger == {
        "a": {"closed_through": "2026-10-03", "closed": 5, "total": 100, "recent": 40, "as_of": "2026-11-05"}
    }


def test_oldest_first_and_a_throttled_run_still_sums_everything(registry):
    ledger = {"a": cached("2026-11-04"), "b": cached("2026-11-02"), "c": cached("2026-11-03")}
    got = metrics.npm(ledger)
    assert registry == ["b"]  # the oldest is tried first, and its failure stops the run
    assert got == {"packages": 3, "all_time": 30, "recent": 9, "as_of": "2026-11-02"}


def test_rotation_reaches_every_package(registry):
    ledger = {"a": cached("2026-11-01"), "b": cached("2026-11-04"), "c": cached("2026-11-02")}
    got = metrics.npm(ledger)
    assert registry == ["a", "c", "b"]
    assert got == {"packages": 3, "all_time": 210, "recent": 83, "as_of": "2026-11-04"}


def test_dropped_packages_leave_the_ledger(monkeypatch):
    monkeypatch.setattr(metrics, "npm_packages", lambda: ["a"])
    monkeypatch.setattr(metrics, "utc_today", lambda: dt.date(2026, 11, 5))
    monkeypatch.setattr(metrics, "npm_package", lambda name, entry, today: ({"closed": 1}, 2, 1))
    ledger = {"gone": cached("2026-01-01")}
    assert metrics.npm(ledger) == {"packages": 1, "all_time": 2, "recent": 1, "as_of": "2026-11-05"}
    assert list(ledger) == ["a"]


ROLES = (
    "<?xml version='1.0'?><methodResponse><params><param><value><array><data>"
    "<value><array><data><value><string>Owner</string></value><value><string>pain001</string></value>"
    "</data></array></value>"
    "<value><array><data><value><string>Maintainer</string></value><value><string>Audio_Analyser</string></value>"
    "</data></array></value>"
    "</data></array></value></param></params></methodResponse>"
)


def test_pypi_packages_come_from_the_account_that_owns_them(monkeypatch):
    asked: list[dict] = []

    def get(url, **kw):
        asked.append({"url": url, **kw})
        return ROLES.encode()

    monkeypatch.setattr(metrics, "get", get)
    assert metrics.pypi_packages() == ["audio_analyser", "pain001"]
    assert asked[0]["url"] == "https://pypi.org/pypi"
    assert asked[0]["content_type"] == "text/xml"
    assert f"<string>{metrics.PYPI_USER}</string>" in asked[0]["data"]


@pytest.mark.parametrize(
    ("reply", "error"),
    [
        ("<methodResponse><fault><value><string>boom</string></value></fault></methodResponse>", "fault"),
        ("<methodResponse><params><param><value><array><data></data></array></value></param></params>", "no packages"),
    ],
)
def test_pypi_packages_refuse_a_fault_or_an_empty_answer(monkeypatch, reply, error):
    monkeypatch.setattr(metrics, "get", lambda url, **kw: reply.encode())
    with pytest.raises(ValueError, match=error):
        metrics.pypi_packages()


def test_pypi_counts_every_owned_package(monkeypatch):
    monkeypatch.setattr(metrics, "pypi_packages", lambda: ["pain001", "o'brien"])
    seen: list[str] = []
    monkeypatch.setattr(metrics, "clickpy", lambda names: seen.append(names) or (900, 40))
    assert metrics.pypi() == {"packages": 2, "all_time": 900, "recent": 40}
    assert seen == ["['pain001','o\\'brien']"]


def clickpy_replies(monkeypatch, rows: list[list[str]]) -> list[str]:
    """Script ClickPy's answers (all-time, window); return the requests made."""
    asked: list[str] = []

    def reply(url, **kw):
        asked.append(url)
        return {"data": [rows[len(asked) - 1]]}

    monkeypatch.setattr(metrics, "get_json", reply)
    return asked


def test_clickpy_keeps_the_fullest_answer(monkeypatch):
    # A replica missing older rows answers low; the complete answer wins, window figure included.
    rows = [["106555", "9000"], ["169994", "9100"], ["106555", "9000"], ["169994", "9100"]]
    asked = clickpy_replies(monkeypatch, rows)
    assert metrics.clickpy("['a']") == (169994, 9100)
    assert len(asked) == metrics.CLICKPY_TRIES


def test_clickpy_all_replicas_agreeing_changes_nothing(monkeypatch):
    clickpy_replies(monkeypatch, [["390697", "69690"]] * metrics.CLICKPY_TRIES)
    assert metrics.clickpy("['a']") == (390697, 69690)


def test_clickpy_never_prefers_a_larger_window_over_a_fuller_history(monkeypatch):
    rows = [["295361", "99999"], ["390697", "69690"], ["295361", "99999"], ["295361", "99999"]]
    clickpy_replies(monkeypatch, rows)
    assert metrics.clickpy("['a']") == (390697, 69690)


def test_compact():
    got = [metrics.compact(n) for n in (999, 1_000, 1_250, 51_200_000, 2_000_000)]
    assert got == ["999", "1K", "1.2K", "51.2M", "2M"]
