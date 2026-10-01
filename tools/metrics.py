"""Live proof numbers, fetched from each registry at build time.

Every figure has named sources and one time window:

- All-time downloads: crates.io crate totals, PyPI totals from ClickHouse's
  public ClickPy dataset (the BigQuery PyPI download log, mirrored), and
  npm totals summed in 18-month ranges from each package's creation.
- Downloads in the last 30 days: the same three registries, same sources
  (crates.io daily counts, ClickPy daily counts, npm `last-month`).
- GitHub stars: every owned, non-fork repository, all pages.
- Packages published: crates + PyPI projects + npm packages.

GitHub Packages is absent: its download counts have no public API.
A failed fetch stops the build, so a bad day leaves yesterday's numbers
in place rather than publishing a partial sum.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlencode

USER = "sebastienrousseau"
UA = f"{USER}-profile (https://github.com/{USER}/{USER})"
WINDOW = 30
CLICKPY = "https://sql-clickhouse.clickhouse.com/"
# Names and window are typed query parameters, never spliced into the SQL.
CLICKPY_SQL = (
    "SELECT sum(count), sumIf(count, date > today() - {days:UInt16}) FROM pypi.pypi_downloads_per_day"
    " WHERE lower(project) IN {names:Array(String)} FORMAT JSONCompact"
)


def _curl(url: str) -> tuple[str, str]:
    cmd = ["curl", "-sSL", "-A", UA, "-w", "\n%{http_code}", url]
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        cmd[1:1] = ["-H", f"Authorization: Bearer {token}"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout  # noqa: S603
    body, _, code = out.rpartition("\n")
    return body, code


def get(url: str, *, ok404: bool = False) -> dict | list | None:
    """GET JSON with curl, backing off on HTTP 429. None on 404 when `ok404`; other failures raise."""
    for attempt in range(6):
        body, code = _curl(url)
        if code != "429":
            break
        time.sleep(5 * 2**attempt)
    if code == "404" and ok404:
        return None
    if code != "200":
        raise SystemExit(f"metrics: {url} returned HTTP {code}")
    return json.loads(body)


def github_repos() -> list[dict]:
    repos, page = [], 1
    while batch := get(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"):
        repos += [r for r in batch if not r["fork"]]
        page += 1
    return repos


def crates() -> tuple[int, int, int]:
    """(crate count, all-time downloads, downloads in the window)."""
    uid = get(f"https://crates.io/api/v1/users/{USER}")["user"]["id"]
    listing = get(f"https://crates.io/api/v1/crates?user_id={uid}&per_page=100")["crates"]
    since = (dt.date.today() - dt.timedelta(days=WINDOW)).isoformat()
    recent = 0
    for c in listing:
        time.sleep(1)  # crates.io crawler policy: at most one request a second
        daily = get(f"https://crates.io/api/v1/crates/{c['id']}/downloads")
        rows = daily["version_downloads"] + daily["meta"]["extra_downloads"]
        recent += sum(r["downloads"] for r in rows if r["date"] > since)
    return len(listing), sum(c["downloads"] for c in listing), recent


def _is_ours(name: str) -> bool:
    info = get(f"https://pypi.org/pypi/{name}/json", ok404=True)
    if not info:
        return False
    urls = [info["info"].get("home_page") or "", *(info["info"].get("project_urls") or {}).values()]
    return any(f"github.com/{USER}/" in u.lower() for u in urls)


def pypi(repos: list[dict]) -> tuple[int, int, int]:
    """(project count, all-time, window) for Python repos published to PyPI."""
    names = [r["name"] for r in repos if r["language"] == "Python"]
    with ThreadPoolExecutor(8) as pool:
        ours = [n.lower() for n, keep in zip(names, pool.map(_is_ours, names), strict=True) if keep]
    names = "[" + ",".join("'" + n.replace("\\", "\\\\").replace("'", "\\'") + "'" for n in ours) + "]"
    params = urlencode({"user": "demo", "param_names": names, "param_days": WINDOW})
    out = subprocess.run(  # noqa: S603
        ["curl", "-fsS", "--max-time", "120", f"{CLICKPY}?{params}", "--data-binary", CLICKPY_SQL],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    total, recent = (int(v) for v in json.loads(out)["data"][0])
    return len(ours), total, recent


def _npm_all_time(name: str) -> int:
    """Sum npm's point totals in 540-day ranges (its maximum) from creation to today."""
    pkg = quote(name, safe="@")
    created = dt.date.fromisoformat(get(f"https://registry.npmjs.org/{pkg}")["time"]["created"][:10])
    start, today, total = max(created, dt.date(2015, 1, 10)), dt.date.today(), 0
    while start <= today:
        end = min(start + dt.timedelta(days=539), today)
        point = get(f"https://api.npmjs.org/downloads/point/{start}:{end}/{pkg}", ok404=True)
        total += point["downloads"] if point else 0
        start = end + dt.timedelta(days=1)
    return total


def _npm_month(name: str) -> int:
    point = get(f"https://api.npmjs.org/downloads/point/last-month/{quote(name, safe='@')}", ok404=True)
    return point["downloads"] if point else 0


def npm() -> tuple[int, int, int]:
    """(package count, all-time, last month) for packages this account maintains."""
    found = get(f"https://registry.npmjs.org/-/v1/search?text=maintainer:{USER}&size=250")
    names = [o["package"]["name"] for o in found["objects"]]
    with ThreadPoolExecutor(6) as pool:
        return len(names), sum(pool.map(_npm_all_time, names)), sum(pool.map(_npm_month, names))


def compact(n: int) -> str:
    for size, suffix in ((1_000_000, "M"), (1_000, "K")):
        if n >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def collect() -> list[dict]:
    repos = github_repos()
    counts = [crates(), pypi(repos), npm()]
    return [
        {"value": compact(sum(c[1] for c in counts)), "label": "All-time downloads"},
        {"value": compact(sum(c[2] for c in counts)), "label": f"Downloads, last {WINDOW} days"},
        {"value": compact(sum(r["stargazers_count"] for r in repos)), "label": "GitHub stars"},
        {"value": str(sum(c[0] for c in counts)), "label": "Packages published"},
    ]
