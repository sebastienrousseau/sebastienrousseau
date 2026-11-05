"""Fetch the live data and render the panels that change: numbers and articles.

make live OUT=<checkout of the profile-data branch>   # default: .live/

Writes <OUT>/assets/{numbers,article-N}-{light,dark}.svg and <OUT>/state.json.
README.md on main points at these files on the profile-data branch, so a
refresh never needs a commit to the protected main branch.

Each source is fetched on its own. When one fails, or returns a value
outside the plausibility bands, its last good value is kept and the run
still publishes everything else. The run exits 1 once any source is older
than STALE_AFTER, so a stuck source pages a human (refresh.yml opens an
issue) while the profile keeps showing the freshest numbers it has.
Set PROFILE_ACCEPT=1 to accept values outside the bands after checking them.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import articles
import metrics
import panels
from net import FetchError

ROOT = Path(__file__).resolve().parent.parent
STALE_AFTER = dt.timedelta(days=2)
# The largest believable drop from the last good value. A partial API
# response looks exactly like a collapse, so a bigger drop is held for a
# human instead of published.
BANDS = {"packages": 0.10, "all_time": 0.01, "recent": 0.40, "stars": 0.05}
REGISTRIES = ("crates", "pypi", "npm")
FAILURES = (FetchError, LookupError, TypeError, ValueError)


def implausible(prev: dict, new: dict) -> str | None:
    """Why `new` is not believable after `prev`, or None."""
    for key, band in BANDS.items():
        old, now = prev.get(key), new.get(key)
        if old and now is not None and now < old * (1 - band):
            return f"{key} fell from {old} to {now}"
    return None


def refresh(fetch: Callable[[], dict], prev: dict | None, today: dt.date) -> tuple[dict | None, str]:
    """(state entry, status) for one source: the new value, or the last good one.

    A value may carry its own "as_of" (npm's is its oldest package figure);
    otherwise it is dated today.
    """
    try:
        value = fetch()
    except FAILURES as exc:
        kept = f"kept value from {prev['as_of']}" if prev else "no earlier value"
        return prev, f"failed ({exc}); {kept}"
    why = implausible(prev["value"], value) if prev and not os.environ.get("PROFILE_ACCEPT") else None
    if why:
        return prev, f"held ({why}); kept value from {prev['as_of']}"
    day = value.pop("as_of", today.isoformat())
    return {"value": value, "as_of": day}, "ok"


def collect(site: str, prev: dict, ledger: dict, today: dt.date) -> tuple[dict, dict]:
    """(source name -> state entry, source name -> status), in fetch order.

    `ledger` (npm's settled history) is updated in place, even by a run that
    fails part-way, so a throttled first run still makes progress.
    """
    out: dict[str, dict | None] = {}
    plan: list[tuple[str, Callable[[], dict]]] = [
        ("github", metrics.github),
        ("crates", metrics.crates),
        ("pypi", lambda: metrics.pypi(out["github"]["value"]["python_repos"])),
        ("npm", lambda: metrics.npm(ledger)),
        ("articles", lambda: {"items": articles.latest(site)}),
    ]
    status = {}
    for name, fetch in plan:
        out[name], status[name] = refresh(fetch, prev.get(name), today)
    return out, status


def stats(src: dict) -> list[dict]:
    regs = [src[name]["value"] for name in REGISTRIES]
    return [
        {"value": metrics.compact(sum(r["all_time"] for r in regs)), "label": "All-time downloads"},
        {"value": metrics.compact(sum(r["recent"] for r in regs)), "label": f"Downloads, last {metrics.WINDOW} days"},
        {"value": metrics.compact(src["github"]["value"]["stars"]), "label": "GitHub stars"},
        {"value": str(sum(r["packages"] for r in regs)), "label": "Packages published"},
    ]


def as_of(src: dict) -> dt.date:
    """The date of the oldest figure on the numbers panel."""
    return min(dt.date.fromisoformat(src[name]["as_of"]) for name in ("github", *REGISTRIES))


def render(cfg: dict, src: dict, out: Path) -> None:
    day = f"{as_of(src):%-d %B %Y}"
    todo = {"numbers": lambda t: panels.numbers(t, {**cfg["numbers"], "stats": stats(src), "as_of": day})}
    for n, a in enumerate(src["articles"]["value"]["items"], 1):
        todo[f"article-{n}"] = lambda t, a=a: panels.article(t, a)
    panels.write(todo, out / "assets")


def summary(src: dict, status: dict) -> str:
    rows = ["| Source | Status | As of |", "| --- | --- | --- |"]
    rows += [f"| {n} | {status[n]} | {(src[n] or {}).get('as_of', 'never')} |" for n in status]
    return "\n".join(rows) + "\n"


def stale(src: dict, today: dt.date) -> list[str]:
    return [n for n, e in src.items() if e is None or today - dt.date.fromisoformat(e["as_of"]) > STALE_AFTER]


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else ROOT / ".live"
    cfg = tomllib.loads((ROOT / "profile.toml").read_text())
    state_file = out / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    ledger = state.get("npm_ledger", {})
    today = metrics.utc_today()
    src, status = collect(cfg["site"], state.get("sources", {}), ledger, today)
    report = summary(src, status)
    print(report)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(path).write_text(report)
    out.mkdir(parents=True, exist_ok=True)
    kept = {n: e for n, e in src.items() if e is not None}
    state_file.write_text(json.dumps({"sources": kept, "npm_ledger": ledger}, indent=1, sort_keys=True) + "\n")
    if missing := sorted(set(src) - set(kept)):
        print(f"::error::no value yet for {', '.join(missing)}; panels not rendered")
        return 1
    render(cfg, src, out)
    if late := stale(src, today):
        print(f"::error::stale for more than {STALE_AFTER.days} days: {', '.join(late)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
