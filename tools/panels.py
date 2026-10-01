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


# The lattice clock. The hero's ML-KEM point lattice is the dial: two
# lattice basis vectors are the hour and minute hands, a faint third one
# sweeps the seconds, and a badge at each tip rolls through the hour
# (12, 1 .. 11) or the minute (00 .. 59) like an odometer. Badges
# counter-rotate about their tip so the digits stay upright. Everything is
# CSS animation; statically it shows 10:09:30. The /api/clock/ Worker
# route on sebastienrousseau.com replaces CLOCK_MARKER with CSS that sets
# the .hh/.mm/.ss delays to the London time and starts .hand elements.
CLOCK_MARKER = "/*clock*/"
STATIC_TIME = 10 * 3600 + 9 * 60 + 30
HOUR_LEN, MINUTE_LEN, SECOND_LEN = 126, 184, 168
# Badge radius and the spacing between digits in a strip. MINUTE_LEN -
# HOUR_LEN exceeds 2 * BADGE, so the badges never overlap even when the
# hands align, and MINUTE_LEN + BADGE keeps clear of the headline and edge.
BADGE, ROW = 28, 54
CLOCK_CSS = (
    ".hand{{transform-box:view-box;transform-origin:{x}px {y}px;animation-name:spin;"
    "animation-timing-function:linear;animation-iteration-count:infinite;animation-play-state:paused}}"
    "@keyframes spin{{to{{transform:rotate(360deg)}}}}"
    "@keyframes unspin{{to{{transform:rotate(-360deg)}}}}"
    "@keyframes rollh{{to{{transform:translateY(-{rh}px)}}}}"
    "@keyframes rollm{{to{{transform:translateY(-{rm}px)}}}}"
    ".hh{{animation-duration:43200s;animation-delay:-{h}s}}"
    ".mm{{animation-duration:3600s;animation-delay:-{m}s}}"
    ".ss{{animation-duration:60s;animation-timing-function:steps(60);animation-delay:-{s}s}}"
    ".un{{animation-name:unspin}}"
    ".hh.roll{{animation-name:rollh;animation-timing-function:steps(12)}}"
    ".mm.roll{{animation-name:rollm;animation-timing-function:steps(60)}}"
)


def _badge(doc: Doc, t: dict, tip: tuple[float, float], unit: str) -> None:
    """A badge at a hand's tip: a clipped strip of numbers rolled by CSS.

    The outer group rotates with the hand about the clock centre (class
    `hand <unit>`); the inner one counter-rotates about the tip, so the
    badge rides the hand but stays upright.
    """
    tx, ty = tip
    labels = ["12", *map(str, range(1, 12))] if unit == "hh" else [f"{m:02d}" for m in range(60)]
    cid = f"clip-{unit}"
    doc.defs.append(f'<clipPath id="{cid}"><circle cx="{tx}" cy="{ty}" r="{BADGE - 3}"/></clipPath>')
    doc.add(f'<g class="hand {unit}"><g class="hand {unit} un" style="transform-origin:{tx}px {ty}px">')
    doc.add(f'<circle cx="{tx}" cy="{ty}" r="{BADGE}" fill="{t["panel"]}" stroke="{t["accent"]}" stroke-width="2"/>')
    doc.add(f'<g clip-path="url(#{cid})"><g class="hand {unit} roll">')
    for n, label in enumerate(labels):
        doc.text(tx, ty + 8.5 + n * ROW, label, (SEMI, 24, t["ink"]), anchor="middle", tracking=-0.02)
    doc.add("</g></g></g></g>")


def _lattice_clock(doc: Doc, t: dict, centre: tuple[float, float]) -> None:
    """Hands as lattice basis vectors, with rolling number badges."""
    cx, cy = centre
    doc.css.append(
        CLOCK_CSS.format(x=cx, y=cy, h=STATIC_TIME, m=STATIC_TIME % 3600, s=STATIC_TIME % 60, rh=12 * ROW, rm=60 * ROW)
    )
    doc.css.append(CLOCK_MARKER)
    a = t["accent"]
    line = f'stroke="{a}" stroke-linecap="round"'
    doc.add(
        f'<g class="hand ss"><path d="M{cx} {cy + 22}V{cy - SECOND_LEN}" {line} stroke-width="1.2" opacity=".45"/>'
        f'<circle cx="{cx}" cy="{cy - SECOND_LEN}" r="3.5" fill="{a}" opacity=".6"/></g>'
    )
    doc.add(f'<path class="hand hh" d="M{cx} {cy}V{cy - HOUR_LEN + BADGE}" {line} stroke-width="3"/>')
    doc.add(f'<path class="hand mm" d="M{cx} {cy}V{cy - MINUTE_LEN + BADGE}" {line} stroke-width="3"/>')
    _badge(doc, t, (cx, cy - HOUR_LEN), "hh")
    _badge(doc, t, (cx, cy - MINUTE_LEN), "mm")
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="7" fill="{a}"/>')
    doc.add(f'<circle cx="{cx}" cy="{cy}" r="2.6" fill="{t["panel"]}"/>')


def hero(t: dict, c: dict) -> Doc:
    doc = Doc(
        W,
        600,
        f"{c['eyebrow']}. {' '.join(c['headline'])} {' '.join(c['lede'])}"
        " A clock drawn on the lattice shows the time in London.",
    )
    _panel(doc, t["panel"])
    _glow(doc, "g", t["glow"], (1060, 300, 520), 0.28)
    _lattice(doc, t, (1038, 300))
    _lattice_clock(doc, t, (1038, 300))
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
