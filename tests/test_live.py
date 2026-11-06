"""The refresh never publishes a partial or implausible figure, and never freezes."""

from __future__ import annotations

import datetime as dt

import pytest

import live
import metrics
from net import FetchError

TODAY = dt.date(2026, 11, 5)
PREV = {"value": {"packages": 100, "all_time": 1000, "recent": 100}, "as_of": "2026-11-04"}


def boom() -> dict:
    raise FetchError("https://api.npmjs.org/x returned HTTP 429")


def test_new_value_is_dated_today():
    entry, status = live.refresh(lambda: {"packages": 101, "all_time": 1010, "recent": 90}, PREV, TODAY)
    assert status == "ok"
    assert entry == {"value": {"packages": 101, "all_time": 1010, "recent": 90}, "as_of": "2026-11-05"}


def test_failure_keeps_the_last_good_value():
    entry, status = live.refresh(boom, PREV, TODAY)
    assert entry is PREV
    assert status.startswith("failed (") and status.endswith("kept value from 2026-11-04")


def test_failure_without_history_yields_nothing():
    entry, status = live.refresh(boom, None, TODAY)
    assert entry is None
    assert status.endswith("no earlier value")


@pytest.mark.parametrize(
    ("new", "held"),
    [
        ({"packages": 91, "all_time": 1000, "recent": 100}, False),  # -9% packages: within band
        ({"packages": 89, "all_time": 1000, "recent": 100}, True),  # -11% packages: a partial listing
        ({"packages": 100, "all_time": 980, "recent": 100}, True),  # all-time cannot really fall 2%
        ({"packages": 100, "all_time": 1000, "recent": 61}, False),
        ({"packages": 100, "all_time": 1000, "recent": 59}, True),
    ],
)
def test_bands_hold_implausible_drops(new, held):
    entry, status = live.refresh(lambda: new, PREV, TODAY)
    assert (entry is PREV) is held
    assert status.startswith("held (") is held


def test_accept_overrides_the_bands(monkeypatch):
    monkeypatch.setenv("PROFILE_ACCEPT", "1")
    entry, status = live.refresh(lambda: {"packages": 1, "all_time": 1, "recent": 1}, PREV, TODAY)
    assert status == "ok"
    assert entry["value"]["packages"] == 1


def test_growth_is_never_held():
    assert live.implausible(PREV["value"], {"packages": 500, "all_time": 10**9, "recent": 10**6}) is None


def test_a_value_can_carry_its_own_date():
    entry, status = live.refresh(
        lambda: {"packages": 100, "all_time": 1000, "recent": 99, "as_of": "2026-11-03"}, PREV, TODAY
    )
    assert status == "ok"
    assert entry == {"value": {"packages": 100, "all_time": 1000, "recent": 99}, "as_of": "2026-11-03"}


def test_stale_after_two_days():
    src = {
        "fresh": {"as_of": "2026-11-05"},
        "edge": {"as_of": "2026-11-03"},
        "late": {"as_of": "2026-11-02"},
        "never": None,
    }
    assert live.stale(src, TODAY) == ["late", "never"]


def test_pypi_failure_follows_a_github_failure(monkeypatch):
    monkeypatch.setattr(metrics, "github", boom)
    monkeypatch.setattr(metrics, "crates", lambda: PREV["value"])
    monkeypatch.setattr(metrics, "npm", lambda ledger: PREV["value"])
    monkeypatch.setattr(live.articles, "latest", lambda site: [])
    src, status = live.collect("https://example.test", {}, {}, TODAY)
    assert src["github"] is None and src["pypi"] is None
    assert status["crates"] == "ok" and status["npm"] == "ok"


def test_numbers_date_is_the_oldest_figure():
    day = {"value": {}, "as_of": "2026-11-05"}
    src = {"github": day, "crates": day, "pypi": {"value": {}, "as_of": "2026-11-03"}, "npm": day}
    assert live.as_of(src) == dt.date(2026, 11, 3)
