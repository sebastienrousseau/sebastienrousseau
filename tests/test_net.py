"""Retries back off within a budget and honour Retry-After."""

from __future__ import annotations

import pytest

import net


@pytest.fixture
def replies(monkeypatch):
    """Script the responses curl would give; record the sleeps."""
    script: list[tuple[bytes, str, str]] = []
    sleeps: list[float] = []
    monkeypatch.setattr(net, "_once", lambda url, data: script.pop(0))
    monkeypatch.setattr(net.time, "sleep", sleeps.append)
    return script, sleeps


def test_retry_after_is_honoured(replies):
    script, sleeps = replies
    script += [(b"", "429", "7"), (b'{"ok": 1}', "200", "")]
    assert net.get_json("https://api.npmjs.org/x") == {"ok": 1}
    assert sleeps == [7.0]


def test_exponential_without_retry_after(replies):
    script, sleeps = replies
    script += [(b"", "503", ""), (b"", "000", ""), (b"x", "200", "")]
    assert net.get("https://crates.io/x") == b"x"
    assert sleeps == [2.0, 4.0]


def test_budget_caps_the_total_wait(replies):
    script, sleeps = replies
    script += [(b"", "429", "100"), (b"", "429", "100")]
    with pytest.raises(net.FetchError, match="HTTP 429"):
        net.get("https://api.npmjs.org/x?secret=1")
    assert sleeps == [100.0]


def test_errors_drop_the_query_string(replies):
    script, _ = replies
    script += [(b"", "401", "")]
    with pytest.raises(net.FetchError) as err:
        net.get("https://sql-clickhouse.clickhouse.com/?user=demo&param_names=x")
    assert "param_names" not in str(err.value)


def test_404_is_none_only_when_allowed(replies):
    script, _ = replies
    script += [(b"", "404", ""), (b"", "404", "")]
    assert net.get("https://pypi.org/pypi/x/json", ok404=True) is None
    with pytest.raises(net.FetchError):
        net.get("https://pypi.org/pypi/x/json")


def test_token_goes_to_github_only_and_never_argv(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "t0k3n")
    assert net._headers("https://api.github.com/users/x") == b"Authorization: Bearer t0k3n\n"
    assert net._headers("https://crates.io/api/v1/users/x") == b""
