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


# An original wall clock drawn as a superconducting qubit mounting plate:
# a gold plate whose flange carries 12 coax connectors as hour markers
# (blue cores at the quarters) with bolt holes at the half hours, a ring of
# 60 vias for the minutes, wire-bond traces fanning out from a square chip
# etched LONDON, graphite hands, and a slim blue second hand with a tail
# counterweight. Statically it shows 10:09:30. The /api/clock/ Worker route
# on sebastienrousseau.com replaces CLOCK_MARKER with the London time and
# starts the hands.
CLOCK_MARKER = "/*clock*/"
STATIC_TIME = 10 * 3600 + 9 * 60 + 30
CLOCK_CSS = (
    ".hand{{transform-box:view-box;transform-origin:{x}px {y}px;animation-name:spin;"
    "animation-timing-function:linear;animation-iteration-count:infinite;animation-play-state:paused}}"
    "@keyframes spin{{to{{transform:rotate(360deg)}}}}"
    ".hh{{animation-duration:43200s;animation-delay:-{h}s}}"
    ".mm{{animation-duration:3600s;animation-delay:-{m}s}}"
    ".ss{{animation-duration:60s;animation-timing-function:steps(60);animation-delay:-{s}s}}"
)
DIAL, FLANGE, CHIP = 194, 158, 42
GOLD_DEFS = (
    '<filter id="lift" x="-20%" y="-20%" width="140%" height="140%">'
    '<feDropShadow dx="0" dy="12" stdDeviation="16" flood-opacity=".25"/></filter>'
    '<linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6dd92"/>'
    '<stop offset=".5" stop-color="#a97d1f"/><stop offset="1" stop-color="#e8c565"/></linearGradient>'
    '<radialGradient id="plate" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#f3d98e"/>'
    '<stop offset=".6" stop-color="#d9b458"/><stop offset="1" stop-color="#b98f2e"/></radialGradient>'
    '<radialGradient id="pin" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff3c4"/>'
    '<stop offset=".55" stop-color="#d8b04f"/><stop offset="1" stop-color="#8a6516"/></radialGradient>'
    '<linearGradient id="die" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a7f9e"/>'
    '<stop offset=".5" stop-color="#14546d"/><stop offset="1" stop-color="#0a3040"/></linearGradient>'
    '<linearGradient id="graphite" x1="0" x2="1"><stop offset="0" stop-color="#3a3a3e"/>'
    '<stop offset=".5" stop-color="#18181b"/><stop offset="1" stop-color="#2e2e32"/></linearGradient>'
    '<radialGradient id="glass" cx=".32" cy=".24" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".28"/>'
    '<stop offset=".45" stop-color="#fff" stop-opacity="0"/></radialGradient>'
)


def _at(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def _bar(cx: float, cy: float, back: float, front: float, widths: tuple[float, float]) -> str:
    """A slim, tapered hand pointing at 12, as polygon points."""
    wb, wt = widths[0] / 2, widths[1] / 2
    return f"{cx - wb},{cy + back} {cx + wb},{cy + back} {cx + wt},{cy - front} {cx - wt},{cy - front}"


def _flange(cx: float, cy: float, t: dict) -> str:
    """Coax connectors at the hours, bolt holes at the half hours."""
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{FLANGE}" fill="none" stroke="#9a7424" stroke-width="1.4"/>']
    for hour in range(12):
        x, y = _at(cx, cy, 176, hour * 30)
        core = t["clock_accent"] if hour % 3 == 0 else "#3b2a08"
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10.5" fill="#8a6516"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="url(#pin)"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{core}"/>'
        )
        hx, hy = _at(cx, cy, 176, hour * 30 + 15)
        parts.append(
            f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="4.4" fill="#5c430e"/>'
            f'<circle cx="{hx:.1f}" cy="{hy + 0.8:.1f}" r="3.2" fill="#2a1d05"/>'
        )
    return "".join(parts)


def _plate(cx: float, cy: float) -> str:
    """Minute vias, and wire-bond traces fanning out from the chip."""
    parts = []
    for n in range(60):
        x, y = _at(cx, cy, FLANGE - 10, n * 6)
        r = 2.4 if n % 5 == 0 else 1.3
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#7a5a14"/>')
    for n in range(48):
        deg = n * 7.5
        x1, y1 = _at(cx, cy, CHIP * 1.25, deg)
        x2, y2 = _at(cx, cy, 104 + (n % 2) * 14, deg)
        parts.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/><circle cx="{x2:.1f}" cy="{y2:.1f}" r="1.6"/>')
    return f'<g stroke="#a47c22" stroke-width=".8" fill="#a47c22">{"".join(parts)}</g>'


def _chip(doc: Doc, cx: float, cy: float) -> None:
    pads = []
    for k in range(7):
        o = -CHIP + 8 + k * (2 * CHIP - 16) / 6
        for x, y in (
            (cx + o, cy - CHIP - 4),
            (cx + o, cy + CHIP + 4),
            (cx - CHIP - 4, cy + o),
            (cx + CHIP + 4, cy + o),
        ):
            pads.append(f'<rect x="{x - 2.2:.1f}" y="{y - 2.2:.1f}" width="4.4" height="4.4"/>')
    doc.add(f'<g fill="#7a5a14">{"".join(pads)}</g>')
    side = 2 * CHIP
    doc.add(
        f'<rect x="{cx - CHIP}" y="{cy - CHIP}" width="{side}" height="{side}" rx="3" fill="url(#die)"'
        ' stroke="#e3c46a" stroke-width="1.2"/>'
    )
    doc.text(cx, cy + CHIP + 30, "London", (SEMI, 10, "#6b4e10"), anchor="middle", tracking=0.34, upper=True)


def _watch(doc: Doc, t: dict, centre: tuple[float, float]) -> None:
    """The quantum-plate clock; hands are driven by CSS animation."""
    cx, cy = centre
    doc.css.append(CLOCK_CSS.format(x=cx, y=cy, h=STATIC_TIME, m=STATIC_TIME % 3600, s=STATIC_TIME % 60))
    doc.css.append(CLOCK_MARKER)
    doc.defs.append(GOLD_DEFS)
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{DIAL + 5}" fill="url(#rim)" filter="url(#lift)"/>')
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{DIAL}" fill="url(#plate)"/>')
    doc.add(_flange(cx, cy, t))
    doc.add(_plate(cx, cy))
    _chip(doc, cx, cy)
    doc.add(f'<polygon class="hand hh" points="{_bar(cx, cy, 30, 112, (10, 6.5))}" fill="url(#graphite)"/>')
    doc.add(f'<polygon class="hand mm" points="{_bar(cx, cy, 30, 150, (7.5, 4.5))}" fill="url(#graphite)"/>')
    doc.add(
        f'<g class="hand ss" fill="{t["clock_accent"]}"><path d="M{cx} {cy + 44}V{cy - 156}"'
        f' stroke="{t["clock_accent"]}" stroke-width="1.8" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy + 34}" r="7"/></g>'
    )
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="url(#pin)"/>')
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="3.4" fill="{t["clock_accent"]}"/>')
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="{DIAL}" fill="url(#glass)"/>')


def hero(t: dict, c: dict) -> Doc:
    doc = Doc(
        W,
        600,
        f"{c['eyebrow']}. {' '.join(c['headline'])} {' '.join(c['lede'])} A station clock shows the time in London.",
    )
    _panel(doc, t["panel"])
    _glow(doc, "g", t["glow"], (1060, 300, 520), 0.28)
    _lattice(doc, t, (1066, 300))
    _watch(doc, t, (1066, 300))
    doc.text(88, 168, c["eyebrow"], (SEMI, 18, t["accent"]), tracking=0.14, upper=True)
    for n, line in enumerate(c["headline"]):
        doc.text(84, 268 + n * 88, line, (BOLD, 80, t["ink"]), tracking=-0.032)
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
        doc.text(x, 266, s["value"], (BOLD, 70, "url(#n)"), anchor="middle", tracking=-0.035)
        for k, line in enumerate(wrap(SANS, s["label"], 19, col - 16)):
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
