"""The latest English articles, parsed from sebastienrousseau.com's /articles/ index.

The site's /feed.json lags the index by months, so the index stays the
source until the feed catches up.
"""

from __future__ import annotations

import datetime as dt
import html
import re

from net import get

COUNT = 3
CARD = re.compile(r'card-eyebrow">([^<]+)</p><h2><a href="(/\d{4}-[^"]+)">([^<]+)</a></h2><time datetime="([\d-]+)"')


def parse(site: str, text: str) -> list[dict]:
    """The newest COUNT article cards in `text`, newest first."""
    rows = sorted({(m[3], m[1], m[2], m[0]) for m in CARD.findall(text)}, reverse=True)
    if len(rows) < COUNT:
        raise ValueError("articles: too few cards parsed from /articles/; has the markup changed?")
    return [
        {
            "title": html.unescape(title),
            "topic": html.unescape(topic).upper(),
            "date": f"{dt.date.fromisoformat(day):%-d %B %Y}",
            "published": day,
            "url": f"{site}{path}",
        }
        for day, path, title, topic in rows[:COUNT]
    ]


def latest(site: str) -> list[dict]:
    return parse(site, get(f"{site}/articles/").decode())
