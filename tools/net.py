"""Every network GET in tools/, through curl, with timeouts and bounded retries.

curl negotiates the site's TLS where urllib cannot, so it stays the
transport. Three rules hold for every call:

- Each request has a hard timeout, so a hung host cannot stall a run.
- 429 and 5xx responses back off, honouring Retry-After, within a total
  budget per URL; a rate-limited registry gets fewer requests, not more.
- The GitHub token travels on stdin, never on argv, so it does not show
  in the process table.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

UA = "sebastienrousseau-profile (https://github.com/sebastienrousseau/sebastienrousseau)"
TIMEOUT = 30  # seconds, per request
RETRY_BUDGET = 120.0  # seconds of back-off, in total, per URL
ATTEMPTS = 6
# "000" is curl's code for a connection failure or timeout.
RETRYABLE = frozenset({"000", "429", "500", "502", "503", "504"})


class FetchError(RuntimeError):
    """A GET that still failed after its retries."""


def _headers(url: str) -> bytes:
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        return f"Authorization: Bearer {token}\n".encode()
    return b""


def _once(url: str, data: str | None) -> tuple[bytes, str, str]:
    """One request: (body, HTTP status, Retry-After header)."""
    cmd = ["curl", "-sSL", "--max-time", str(TIMEOUT), "-A", UA, "-H", "@-"]
    cmd += ["-w", "\n%{http_code} %header{retry-after}", url]
    if data is not None:
        cmd += ["--data-binary", data]
    proc = subprocess.run(cmd, input=_headers(url), capture_output=True, check=False)  # noqa: S603, S607
    body, _, tail = proc.stdout.rpartition(b"\n")
    code, _, retry = tail.decode().strip().partition(" ")
    return body, code or "000", retry


def backoff(attempt: int, retry_after: str) -> float:
    """Seconds to wait before the next attempt."""
    return float(retry_after) if retry_after.isdigit() else 2.0 * 2**attempt


def get(url: str, *, data: str | None = None, ok404: bool = False) -> bytes | None:
    """GET (or POST `data`) and return the body. None on 404 when `ok404`."""
    waited = 0.0
    for attempt in range(ATTEMPTS):
        body, code, retry = _once(url, data)
        if code not in RETRYABLE:
            break
        pause = backoff(attempt, retry)
        if waited + pause > RETRY_BUDGET:
            break
        time.sleep(pause)
        waited += pause
    if code == "404" and ok404:
        return None
    if code != "200":
        raise FetchError(f"{url.split('?')[0]} returned HTTP {code}")
    return body


def get_json(url: str, *, data: str | None = None, ok404: bool = False) -> object:
    body = get(url, data=data, ok404=ok404)
    return None if body is None else json.loads(body)
