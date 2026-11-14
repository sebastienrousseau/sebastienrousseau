"""Glyphs: the small motif that replaces each hero lattice point.

Each glyph is SVG markup in a 24-unit box centred on 0,0, drawn only with
currentColor, so the hero can colour every point along the lattice's
gradient. Original geometric art from the approved proposal's prototype.
emblems.py holds the large line art behind the clock.
"""

from __future__ import annotations

import math

F = 'fill="currentColor"'
S = 'fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"'
DROP = "M0-8C3-4 3-1 2 1A2 2 0 0 1-2 1C-3-1-3-4 0-8Z"  # a small flame


def star(n: int, ro: float, ri: float, rot: float = -90) -> str:
    """Polygon points of an n-pointed star, outer radius ro, inner ri."""
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + i * 180 / n)
        pts.append(f"{r * math.cos(a):.2f},{r * math.sin(a):.2f}")
    return " ".join(pts)


def petals(n: int, d: float, r: float) -> str:
    """n circles of radius r, d from the centre, the first pointing up."""
    out = []
    for i in range(n):
        a = math.radians(-90 + i * 360 / n)
        out.append(f'<circle cx="{d * math.cos(a):.2f}" cy="{d * math.sin(a):.2f}" r="{r}"/>')
    return "".join(out)


def rays(n: int, r1: float, r2: float, w: float) -> str:
    """n rounded lines from radius r1 to r2, stroke width w."""
    out = []
    for i in range(n):
        a = math.radians(i * 360 / n)
        out.append(
            f'<line x1="{r1 * math.cos(a):.2f}" y1="{r1 * math.sin(a):.2f}"'
            f' x2="{r2 * math.cos(a):.2f}" y2="{r2 * math.sin(a):.2f}"/>'
        )
    return f'<g stroke="currentColor" stroke-width="{w}" stroke-linecap="round">{"".join(out)}</g>'


def _snowflake() -> str:
    arm = '<path d="M0-11V11M0-7l-3-3M0-7l3-3M0 7l-3 3M0 7l3 3"/>'
    return f'<g {S} stroke-width="2">' + "".join(f'<g transform="rotate({a})">{arm}</g>' for a in (0, 60, 120)) + "</g>"


def _wheat() -> str:
    grains = "".join(
        f'<ellipse cx="{sx * 3}" cy="{y}" rx="2" ry="4" transform="rotate({sx * 30} {sx * 3} {y})"/>'
        for y in (-7, -1, 5)
        for sx in (-1, 1)
    )
    return f'<path {S} stroke-width="1.6" d="M0 12V-12"/><g {F}>{grains}</g>'


GLYPHS = {
    "dot": f'<circle r="6" {F}/>',
    "star": f'<polygon {F} points="{star(5, 11, 4.6)}"/>',
    "sparkle": f'<path {F} d="M0-12Q1.6-1.6 12 0Q1.6 1.6 0 12Q-1.6 1.6-12 0Q-1.6-1.6 0-12Z"/>',
    "heart": f'<path {F} d="M0 10C-15 0-10-13 0-5C10-13 15 0 0 10Z"/>',
    "shamrock": f'<g {F}>{petals(3, 5, 5)}</g><path {S} stroke-width="2" d="M0 3Q1 9 4 12"/>',
    "crescent": f'<path {F} d="M3-11A11 11 0 1 0 3 11A8.6 8.6 0 1 1 3-11Z"/>',
    "snowflake": _snowflake(),
    "leaf": f'<path {F} d="M-10 10C-11-5-2-12 11-11C12 2 5 11-10 10Z"/>',
    "maple": f'<path {F} d="M0-12L2.5-6L6-8L5-2L11-4L8 1L11 3L4 4L4.5 7L1 6L1 12H-1L-1 6L-4.5 7L-4 4'
    'L-11 3L-8 1L-11-4L-5-2L-6-8L-2.5-6Z"/>',
    "diya": f'<path {F} d="M0-12C4-6 5-3 3 0A3.5 3.5 0 0 1-3 0C-5-3-4-6 0-12Z"/>'
    f'<path {F} d="M-11 3H11Q9 11 0 11Q-9 11-11 3Z"/>',
    "lantern": f'<g {F}><rect x="-7" y="-8" width="14" height="16" rx="6"/>'
    '<rect x="-4" y="-11" width="8" height="2.5" rx="1"/>'
    '<rect x="-4" y="8.5" width="8" height="2.5" rx="1"/></g>',
    "sun": f'<circle r="5" {F}/>{rays(8, 8, 11.5, 2)}',
    "flower": f'<g {F}>{petals(5, 6, 4.6)}</g><circle r="3" {F} opacity=".55"/>',
    "marigold": f"<g {F}>{petals(8, 6.5, 4)}{petals(6, 3, 3.2)}</g>",
    # The prototype painted the centre #1d1d1f; currentColor at full
    # strength over petals at 0.7 keeps it darker without a fixed colour.
    "poppy": f'<g {F} opacity=".7">{petals(4, 4.5, 6)}</g><circle r="2.6" {F}/>',
    "lotus": f'<g {F}><path d="M0-11C4-5 4 3 0 9C-4 3-4-5 0-11Z"/><path d="M-1 9C-9 7-12 0-11-5C-6-3-2 2-1 9Z"/>'
    '<path d="M1 9C9 7 12 0 11-5C6-3 2 2 1 9Z"/></g>',
    "kite": f'<polygon {F} points="0,-12 8,-2 0,9 -8,-2"/><path {S} stroke-width="1.6" d="M0 9Q3 12 0 14"/>',
    "diamond": f'<polygon {F} points="0,-11 7,0 0,11 -7,0"/>',
    "drop": f'<path {F} d="M0-11C5-3 8 2 8 5A8 8 0 0 1-8 5C-8 2-5-3 0-11Z"/>',
    "wave": f'<path {S} stroke-width="2.6" d="M-12 2Q-6-6 0 2T12 2"/>',
    "burst": rays(8, 4, 11, 2.2),
    "bat": f'<path {F} d="M0 1C-3-3-6-4-12-3C-9-1-9 2-7 4C-5 2-3 3 0 5C3 3 5 2 7 4C9 2 9-1 12-3C6-4 3-3 0 1Z"/>',
    "bell": f'<path {F} d="M-8 6C-8-2-6-9 0-9C6-9 8-2 8 6Z"/><circle cy="9" r="2.4" {F}/>',
    "apple": f'<path {F} d="M0-5C-6-10-12-5-10 3C-8 10-3 12 0 10C3 12 8 10 10 3C12-5 6-10 0-5Z"/>'
    f'<path {S} stroke-width="2" d="M0-5Q1-10 4-12"/>',
    "wheat": _wheat(),
    "egg": f'<path {F} d="M0-11C6-11 9 0 9 3A9 9 0 0 1-9 3C-9 0-6-11 0-11Z"/>',
    "candle": f'<rect x="-3.5" y="-3" width="7" height="14" rx="1.5" {F}/>'
    f'<path {F} d="M0-12C2.5-9 3-7 2-5A2 2 0 0 1-2-5C-3-7-2.5-9 0-12Z"/>',
    "confetti": f'<g {F}><rect x="-10" y="-8" width="7" height="3.5" rx="1" transform="rotate(-25)"/>'
    '<circle cx="6" cy="-6" r="2.6"/><rect x="0" y="4" width="8" height="3.5" rx="1" transform="rotate(30)"/></g>',
    "splash": f'<g {F}><circle r="6"/><circle cx="7" cy="-6" r="3"/><circle cx="-7" cy="6" r="2.4"/></g>',
    "saltire": f'<path {S} stroke-width="3.2" d="M-9-9L9 9M9-9L-9 9"/>',
    "gift": f'<g {F}><rect x="-9" y="-4" width="18" height="14" rx="2"/></g>'
    f'<path {S} stroke-width="2" d="M0-4C-6-12-10-4 0-4C10-4 6-12 0-4"/>',
    "tulip": f'<path {F} d="M-7-9L-3-5L0-10L3-5L7-9V0A7 7 0 0 1-7 0Z"/><path {S} stroke-width="2" d="M0 6V12"/>',
}
