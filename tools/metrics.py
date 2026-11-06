"""Live proof numbers, fetched from each registry.

Every figure has named sources and one time window:

- All-time downloads: crates.io crate totals, PyPI totals from ClickHouse's
  public ClickPy dataset (the BigQuery PyPI download log, mirrored), and
  npm totals summed from each package's creation. Settled npm days never
  change, so their sum is kept in a ledger and each run asks npm for one
  range of daily counts per package.
- Downloads in the last 30 days: the same three registries, same sources
  (crates.io daily counts, ClickPy daily counts, npm daily counts).
- GitHub stars: every owned, non-fork repository, all pages.
- Packages published: crates + PyPI projects + npm packages.

GitHub Packages is absent: its download counts have no public API.
Each source is fetched on its own; tools/live.py decides what a failure
means, so one flaky registry never freezes the others.
"""

from __future__ import annotations

import datetime as dt
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from urllib.parse import quote, urlencode

from net import FetchError, get_json

USER = "sebastienrousseau"
WINDOW = 30
CLICKPY = "https://sql-clickhouse.clickhouse.com/"
# Names and window are typed query parameters, never spliced into the SQL.
CLICKPY_SQL = (
    "SELECT sum(count), sumIf(count, date > today() - {days:UInt16}) FROM pypi.pypi_downloads_per_day"
    " WHERE lower(project) IN {names:Array(String)} FORMAT JSONCompact"
)
NPM_EPOCH = dt.date(2015, 1, 10)  # npm's download counts start here
CLICKPY_TRIES = 4  # ClickPy replicas disagree; see clickpy()
NPM_SPAN = 539  # npm point and range queries cover at most 540 days
NPM_SETTLE = 3  # days before an npm daily count is treated as final
NPM_PACE = 0.3  # seconds between npm requests; api.npmjs.org rate-limits hard


class Counts(TypedDict):
    packages: int
    all_time: int
    recent: int


def utc_today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def github() -> dict:
    """Stars over every owned, non-fork repository, and the Python repo names."""
    repos, page = [], 1
    while batch := get_json(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"):
        repos += [r for r in batch if not r["fork"]]
        page += 1
    return {
        "stars": sum(r["stargazers_count"] for r in repos),
        "python_repos": sorted(r["name"] for r in repos if r["language"] == "Python"),
    }


def _crate_listing(uid: int) -> list[dict]:
    listing: list[dict] = []
    for page in range(1, 100):
        out = get_json(f"https://crates.io/api/v1/crates?user_id={uid}&per_page=100&page={page}")
        listing += out["crates"]
        if not out["crates"] or len(listing) >= out["meta"]["total"]:
            break
        time.sleep(1)  # crates.io crawler policy: at most one request a second
    return listing


def crates() -> Counts:
    uid = get_json(f"https://crates.io/api/v1/users/{USER}")["user"]["id"]
    listing = _crate_listing(uid)
    since = (utc_today() - dt.timedelta(days=WINDOW)).isoformat()
    recent = 0
    for c in listing:
        time.sleep(1)  # crates.io crawler policy: at most one request a second
        daily = get_json(f"https://crates.io/api/v1/crates/{c['id']}/downloads")
        rows = daily["version_downloads"] + daily["meta"]["extra_downloads"]
        recent += sum(r["downloads"] for r in rows if r["date"] > since)
    return {"packages": len(listing), "all_time": sum(c["downloads"] for c in listing), "recent": recent}


def _is_ours(name: str) -> bool:
    info = get_json(f"https://pypi.org/pypi/{name}/json", ok404=True)
    if not info:
        return False
    urls = [info["info"].get("home_page") or "", *(info["info"].get("project_urls") or {}).values()]
    return any(f"github.com/{USER}/" in u.lower() for u in urls)


def clickpy(names: str) -> tuple[int, int]:
    """(all-time, window) downloads for `names`, from the fullest of CLICKPY_TRIES answers.

    ClickPy sometimes answers from a replica that lacks older rows: the same
    query seconds apart returned 106,555 downloads from 2023-11-08 and
    169,994 from 2023-03-11. All-time totals only grow, so the largest
    answer is the complete one, and its window figure comes with it.
    """
    params = urlencode({"user": "demo", "param_names": names, "param_days": WINDOW})
    answers = [get_json(f"{CLICKPY}?{params}", data=CLICKPY_SQL)["data"][0] for _ in range(CLICKPY_TRIES)]
    total, recent = max((int(a), int(b)) for a, b in answers)
    return total, recent


def pypi(python_repos: list[str]) -> Counts:
    """Python repos published to PyPI under the same name and linking back here."""
    with ThreadPoolExecutor(8) as pool:
        ours = [n.lower() for n, keep in zip(python_repos, pool.map(_is_ours, python_repos), strict=True) if keep]
    names = "[" + ",".join("'" + n.replace("\\", "\\\\").replace("'", "\\'") + "'" for n in ours) + "]"
    total, recent = clickpy(names)
    return {"packages": len(ours), "all_time": total, "recent": recent}


def npm_packages() -> list[str]:
    """Every package this account maintains, across all search pages."""
    names: list[str] = []
    while True:
        found = get_json(f"https://registry.npmjs.org/-/v1/search?text=maintainer:{USER}&size=250&from={len(names)}")
        names += [o["package"]["name"] for o in found["objects"]]
        if not found["objects"] or len(names) >= found["total"]:
            return sorted(set(names))


def _npm_point(span: str, pkg: str) -> int:
    time.sleep(NPM_PACE)
    point = get_json(f"https://api.npmjs.org/downloads/point/{span}/{pkg}", ok404=True)
    return point["downloads"] if point else 0


def _npm_days(span: str, pkg: str) -> list[tuple[dt.date, int]]:
    time.sleep(NPM_PACE)
    out = get_json(f"https://api.npmjs.org/downloads/range/{span}/{pkg}", ok404=True)
    return [(dt.date.fromisoformat(d["day"]), d["downloads"]) for d in (out or {}).get("downloads", [])]


def npm_package(name: str, entry: dict, today: dt.date) -> tuple[dict, int, int]:
    """(updated ledger entry, all-time downloads, downloads in the window) for one package.

    The entry holds the settled total through `closed_through`, which trails
    today by the window plus NPM_SETTLE days. One range query from there to
    today returns daily counts: their sum completes the all-time figure, the
    last WINDOW days are the recent figure, and the days that have settled
    fold into the entry. So a normal run makes one call per package; only
    the first walks older history, in 540-day point queries.
    """
    pkg = quote(name, safe="@")
    if "closed_through" not in entry:
        created = dt.date.fromisoformat(get_json(f"https://registry.npmjs.org/{pkg}")["time"]["created"][:10])
        entry = {"closed_through": (max(created, NPM_EPOCH) - dt.timedelta(days=1)).isoformat(), "closed": 0}
    start = dt.date.fromisoformat(entry["closed_through"]) + dt.timedelta(days=1)
    closed = entry["closed"]
    cutoff = today - dt.timedelta(days=WINDOW + NPM_SETTLE)
    while (today - start).days >= NPM_SPAN:  # until the range query fits in 540 days
        end = min(start + dt.timedelta(days=NPM_SPAN), cutoff)
        closed += _npm_point(f"{start}:{end}", pkg)
        start = end + dt.timedelta(days=1)
    days = _npm_days(f"{start}:{today}", pkg)
    settled = max(start - dt.timedelta(days=1), cutoff)
    since = today - dt.timedelta(days=WINDOW)
    entry = {"closed_through": settled.isoformat(), "closed": closed + sum(n for d, n in days if d <= settled)}
    return entry, closed + sum(n for _, n in days), sum(n for d, n in days if d > since)


def npm(ledger: dict) -> dict:
    """Counts for packages this account maintains, dated by the oldest figure.

    `ledger` caches each package's settled history and last result, and is
    updated in place. Packages are refreshed oldest first, and the first
    failure stops the run's npm requests: its retries are already spent, and
    hammering a registry that is refusing us only lengthens the block. The
    sum then uses each package's latest result, so a throttled run still
    publishes a complete figure and the next run picks up where it stopped.
    """
    names, today = npm_packages(), utc_today()
    error: FetchError | None = None
    for name in sorted(names, key=lambda n: ledger.get(n, {}).get("as_of", "")):
        try:
            entry, total, recent = npm_package(name, ledger.get(name, {}), today)
        except FetchError as exc:
            error = exc
            break
        ledger[name] = {**entry, "total": total, "recent": recent, "as_of": today.isoformat()}
    for gone in set(ledger) - set(names):
        del ledger[gone]
    if missing := [n for n in names if "as_of" not in ledger.get(n, {})]:
        raise FetchError(f"{len(missing)} of {len(names)} npm packages not fetched yet: {error}")
    rows = [ledger[n] for n in names]
    return {
        "packages": len(names),
        "all_time": sum(r["total"] for r in rows),
        "recent": sum(r["recent"] for r in rows),
        "as_of": min(r["as_of"] for r in rows),
    }


def compact(n: int) -> str:
    for size, suffix in ((1_000_000, "M"), (1_000, "K")):
        if n >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)
