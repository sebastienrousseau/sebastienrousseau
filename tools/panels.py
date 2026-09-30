"""The profile's panels. Each function takes a theme and config and returns a Doc."""

from __future__ import annotations

import math

from fonts import wrap
from svg import Doc
from theme import LANGS

W = 1280
SANS, SEMI, MED, BOLD, SERIF = "inter-400", "inter-600", "inter-500", "inter-700", "news-500"


def _panel(doc: Doc, fill: str, radius: int = 32) -> None:
    doc.add(f'<rect width="{doc.width}" height="{doc.height}" rx="{radius}" fill="{fill}"/>')


def _glow(doc: Doc, gid: str, color: str, circle: tuple[float, float, float], alpha: float) -> None:
    cx, cy, r = circle
    doc.defs.append(
        f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="{alpha}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
    )
    doc.add(f'<rect width="{doc.width}" height="{doc.height}" rx="32" fill="url(#{gid})"/>')


def _lattice(doc: Doc, t: dict, centre: tuple[float, float]) -> None:
    """A skewed point lattice (a nod to ML-KEM) that fades toward the text."""
    doc.defs.append(
        '<linearGradient id="fade" x1="0" x2="1"><stop offset=".5" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".8" stop-color="#fff"/></linearGradient><mask id="m"><rect width="100%"'
        ' height="100%" fill="url(#fade)"/></mask>'
    )
    cx, cy = centre
    dots = []
    for i in range(-14, 15):
        for j in range(-8, 9):
            x, y = cx + i * 46 + j * 14, cy + i * 9 + j * 44
            d = math.hypot(x - cx, y - cy)
            if 20 < x < W - 20 and 20 < y < doc.height - 20 and d < 460:
                k = 1 - d / 460
                dots.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.2 + 2.6 * k:.2f}" opacity="{0.15 + 0.85 * k:.2f}"/>'
                )
    doc.add(f'<g mask="url(#m)" fill="{t["accent"]}">{"".join(dots)}</g>')


# A station clock after Hans Hilfiker's 1944 design for Swiss railways,
# deliberately not a copy: the second hand is the site's blue and ends in a
# ring, not SBB's red disc. Statically it shows 10:09:30. The /api/clock/
# Worker route on sebastienrousseau.com replaces CLOCK_MARKER with the
# London time and starts it: the minute hand jumps once a minute and the
# second hand sweeps in 58.5 s, then waits at the top.
CLOCK_MARKER = "/*clock*/"
STATIC_TIME = 10 * 3600 + 9 * 60 + 30
CLOCK_CSS = (
    ".hand{{transform-box:view-box;transform-origin:{x}px {y}px;animation-iteration-count:infinite;"
    "animation-play-state:paused}}"
    "@keyframes spin{{to{{transform:rotate(360deg)}}}}"
    "@keyframes sweep{{97.5%,to{{transform:rotate(360deg)}}}}"
    ".hh{{animation-name:spin;animation-timing-function:linear;animation-duration:43200s;animation-delay:-{h}s}}"
    ".mm{{animation-name:spin;animation-timing-function:steps(60);animation-duration:3600s;animation-delay:-{m}s}}"
    ".ss{{animation-name:sweep;animation-timing-function:linear;animation-duration:60s;animation-delay:-{s}s}}"
)
DIAL = 168


def _bar(cx: float, cy: float, back: float, front: float, widths: tuple[float, float]) -> str:
    """A blunt, slightly tapered hand pointing at 12, as polygon points."""
    wb, wt = widths[0] / 2, widths[1] / 2
    return f"{cx - wb},{cy + back} {cx + wb},{cy + back} {cx + wt},{cy - front} {cx - wt},{cy - front}"


def _watch(doc: Doc, t: dict, centre: tuple[float, float]) -> None:
    """The station clock; hands are driven by CSS animation."""
    cx, cy = centre
    doc.css.append(CLOCK_CSS.format(x=cx, y=cy, h=STATIC_TIME, m=STATIC_TIME % 3600, s=STATIC_TIME % 60))
    doc.css.append(CLOCK_MARKER)
    doc.defs.append(
        '<filter id="lift" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="10" stdDeviation="14" flood-opacity=".18"/></filter>'
    )
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{DIAL + 8}" fill="{t["dial_rim"]}" filter="url(#lift)"/>')
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{DIAL}" fill="{t["dial"]}"/>')
    marks = []
    for n in range(60):
        major = n % 5 == 0
        w, inner = (9, DIAL - 44) if major else (3.2, DIAL - 16)
        marks.append(
            f'<rect x="{cx - w / 2}" y="{cy - DIAL + 8}" width="{w}" height="{DIAL - 8 - inner}"'
            f' transform="rotate({n * 6} {cx} {cy})"/>'
        )
    doc.add(f'<g fill="{t["dial_ink"]}">{"".join(marks)}</g>')
    ink = t["dial_ink"]
    doc.add(f'<polygon class="hand hh" points="{_bar(cx, cy, 34, 96, (15, 11))}" fill="{ink}"/>')
    doc.add(f'<polygon class="hand mm" points="{_bar(cx, cy, 34, 148, (12, 8))}" fill="{ink}"/>')
    doc.add(
        f'<g class="hand ss" stroke="{t["accent"]}" stroke-width="3.5"><path d="M{cx} {cy + 46}V{cy - 94}"/>'
        f'<circle cx="{cx}" cy="{cy - 106}" r="12" fill="none"/>'
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="{t["accent"]}"/></g>'
    )


def hero(t: dict, c: dict) -> Doc:
    doc = Doc(W, 600, f"{c['eyebrow']}. {' '.join(c['headline'])} {' '.join(c['lede'])} A station clock shows the time in London.")
    _panel(doc, t["panel"])
    _glow(doc, "g", t["glow"], (1060, 300, 520), 0.28)
    _lattice(doc, t, (1060, 290))
    _watch(doc, t, (1060, 290))
    doc.text(88, 168, c["eyebrow"], (SEMI, 18, t["accent"]), tracking=0.14, upper=True)
    for n, line in enumerate(c["headline"]):
        doc.text(84, 268 + n * 92, line, (BOLD, 86, t["ink"]), tracking=-0.032)
    for n, line in enumerate(c["lede"]):
        doc.text(88, 450 + n * 38, line, (SANS, 25, t["mute"]), tracking=-0.01)
    return doc


def numbers(t: dict, c: dict) -> Doc:
    stats = c["stats"]
    doc = Doc(W, 430, f"{c['headline']} " + ", ".join(f"{s['value']} {s['label']}" for s in stats))
    _panel(doc, t["panel"])
    doc.defs.append(
        f'<linearGradient id="n" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["ink"]}"/>'
        f'<stop offset="1" stop-color="{t["accent"]}"/></linearGradient>'
    )
    doc.text(W / 2, 88, c["eyebrow"], (SEMI, 16, t["accent"]), anchor="middle", tracking=0.14, upper=True)
    doc.text(W / 2, 148, c["headline"], (BOLD, 52, t["ink"]), anchor="middle", tracking=-0.025)
    col = (W - 160) / len(stats)
    for n, s in enumerate(stats):
        x = 80 + col * (n + 0.5)
        doc.text(x, 268, s["value"], (BOLD, 80, "url(#n)"), anchor="middle", tracking=-0.035)
        for k, line in enumerate(wrap(SANS, s["label"], 19, col - 48)):
            doc.text(x, 308 + k * 26, line, (SANS, 19, t["mute"]), anchor="middle")
        if n:
            doc.add(f'<rect x="{80 + col * n:.1f}" y="206" width="1" height="130" fill="{t["rule"]}"/>')
    doc.text(W / 2, 394, c["note"], (SANS, 14, t["mute"]), anchor="middle")
    return doc


def section(t: dict, c: dict, index: int) -> Doc:
    lede = wrap(SANS, c["lede"], 22, 1000)
    doc = Doc(W, 190 + 32 * len(lede), f"{index:02d}. {c['eyebrow']}. {c['headline']} {c['lede']}")
    doc.add(f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>')
    doc.text(0, 150, f"{index:02d}", (SERIF, 132, t["accent"]), tracking=-0.04)
    doc.text(212, 72, c["eyebrow"], (SEMI, 16, t["accent"]), tracking=0.14, upper=True)
    doc.text(208, 132, c["headline"], (BOLD, 52, t["ink"]), tracking=-0.025)
    for n, line in enumerate(lede):
        doc.text(212, 180 + n * 32, line, (SANS, 22, t["mute"]))
    return doc


def card(t: dict, repo: dict) -> Doc:
    lines = wrap(SANS, repo["text"], 21, 540)
    if len(lines) > 2:
        raise ValueError(f"{repo['name']}: blurb wraps to {len(lines)} lines, keep it to 2")
    doc = Doc(630, 230, f"{repo['name']}: {repo['text']} ({repo['lang']})")
    _panel(doc, t["tile"], 26)
    doc.text(44, 76, repo["name"], (SEMI, 30, t["ink"]), tracking=-0.02)
    arrow = f'stroke="{t["accent"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    doc.add(f'<path d="M572 52L590 52L590 70M590 52L568 74" {arrow}/>')
    for n, line in enumerate(lines):
        doc.text(44, 120 + n * 30, line, (SANS, 21, t["mute"]))
    doc.add(f'<circle cx="52" cy="189" r="7" fill="{LANGS[repo["lang"]]}"/>')
    doc.text(68, 195, repo["lang"], (MED, 17, t["ink"]))
    return doc


def paper(t: dict, c: dict) -> Doc:
    head = wrap(SERIF, c["headline"], 62, 700)
    doc = Doc(
        W,
        316 + len(head) * 66 + len(c["lede"]) * 32,
        f"{c['eyebrow']}. {c['headline']} {' '.join(c['lede'])} {c['cta']}.",
    )
    _panel(doc, t["deep"])
    _glow(doc, "p", t["glow"], (1090, 230, 420), 0.45)
    ring = f'fill="none" stroke="{t["deep_accent"]}"'
    for n, r in enumerate((60, 110, 160, 210)):
        doc.add(f'<circle cx="1060" cy="235" r="{r}" {ring} stroke-width="1.5" opacity="{0.9 - n * 0.2:.1f}"/>')
    doc.add(f'<circle cx="1060" cy="235" r="10" fill="{t["deep_accent"]}"/>')
    doc.text(88, 108, c["eyebrow"], (SEMI, 16, t["deep_accent"]), tracking=0.14, upper=True)
    for n, line in enumerate(head):
        doc.text(86, 180 + n * 66, line, (SERIF, 62, t["deep_ink"]), tracking=-0.015)
    y = 180 + len(head) * 66 + 20
    for n, line in enumerate(c["lede"]):
        doc.text(88, y + n * 32, line, (SANS, 21, t["deep_mute"]))
    doc.text(88, y + len(c["lede"]) * 32 + 40, f"{c['cta']} ›", (SEMI, 21, t["deep_accent"]))
    return doc


def header(t: dict, eyebrow: str, headline: str) -> Doc:
    doc = Doc(W, 150, f"{eyebrow}. {headline}")
    doc.add(f'<rect x="0" y="0" width="{W}" height="1" fill="{t["rule"]}"/>')
    doc.text(W / 2, 74, eyebrow, (SEMI, 16, t["accent"]), anchor="middle", tracking=0.14, upper=True)
    doc.text(W / 2, 132, headline, (BOLD, 52, t["ink"]), anchor="middle", tracking=-0.025)
    return doc


def finale(t: dict, c: dict) -> Doc:
    doc = Doc(W, 380, f"{' '.join(c['headline'])} {c['lede']} Start a conversation.")
    _panel(doc, t["panel"])
    _glow(doc, "f", t["glow"], (W / 2, 380, 560), 0.22)
    for n, line in enumerate(c["headline"]):
        doc.text(W / 2, 132 + n * 72, line, (BOLD, 64, t["ink"]), anchor="middle", tracking=-0.03)
    doc.text(W / 2, 270, c["lede"], (SANS, 22, t["mute"]), anchor="middle")
    doc.text(W / 2, 326, "Start a conversation ›", (SEMI, 22, t["accent"]), anchor="middle")
    return doc


def article(t: dict, a: dict) -> Doc:
    """One of the latest articles, styled like the site's "From the desk" cards."""
    lines = wrap(SEMI, a["title"], 25, 350)
    if len(lines) > 4:
        lines = lines[:4]
        lines[3] = lines[3].rsplit(" ", 1)[0] + "…"
    doc = Doc(420, 300, f"{a['topic']}. {a['title']} {a['date']}.")
    _panel(doc, t["tile"], 24)
    doc.text(34, 54, a["topic"], (SEMI, 13, t["accent"]), tracking=0.12, upper=True)
    for n, line in enumerate(lines):
        doc.text(32, 102 + n * 33, line, (SEMI, 25, t["ink"]), tracking=-0.015)
    doc.text(34, 266, a["date"], (SANS, 16, t["mute"]))
    return doc
