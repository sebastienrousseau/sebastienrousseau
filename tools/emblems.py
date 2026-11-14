"""Emblems: the large line art a holiday hero draws behind the clock.

Each emblem is SVG markup in a 100-unit box centred on 0,0, drawn only with
currentColor. They are the placeholders until a holiday's Noun Project icon
lands (emblem = "icon" in holidays.toml). Original art from the approved
proposal's prototype; motifs.py holds the small glyphs and the helpers.
"""

from __future__ import annotations

import math

from motifs import DROP, GLYPHS, F, S, petals, rays, star

THIN = S + ' stroke-width=".6"'  # a glyph scaled up four times draws at 2.4


def _scaled(glyph: str, *widths: str) -> str:
    """A glyph drawn as line art at four times its size."""
    body = GLYPHS[glyph].replace(F, THIN)
    for width in widths:
        body = body.replace(f'stroke-width="{width}"', 'stroke-width=".6"')
    return f'<g transform="scale(4)">{body}</g>'


def _flames(xs: tuple[int, ...], y: int, y0: int | None = None) -> str:
    """A small flame at each x; the centre one at y0 when given."""
    return "".join(f'<path {F} transform="translate({x} {y0 if x == 0 and y0 else y})" d="{DROP}"/>' for x in xs)


def _menorah() -> str:
    arms = "".join(f'<path d="M{-k * 9} -14V-6A{k * 9} {k * 9} 0 0 0 {k * 9} -6V-14"/>' for k in (1, 2, 3, 4))
    holders = (-36, -27, -18, -9, 0, 9, 18, 27, 36)
    return f'<g {S} stroke-width="2.4"><path d="M0-30V36M-22 36H22"/>{arms}</g>' + _flames(holders, -18, -34)


def _kinara() -> str:
    xs = (-36, -24, -12, 0, 12, 24, 36)
    candles = "".join(f'<rect x="{x - 3.5}" y="-20" width="7" height="30" rx="1.5"/>' for x in xs)
    return f'<g {S} stroke-width="2.4"><path d="M-44 10H44M-30 10L-20 30H20L30 10"/>{candles}</g>' + _flames(xs, -26)


def _wreath() -> str:
    leaves = []
    for a in range(0, 360, 30):
        x, y = f"{36 * math.cos(math.radians(a)):.1f}", f"{36 * math.sin(math.radians(a)):.1f}"
        leaves.append(
            f'<ellipse cx="{x}" cy="{y}" rx="4" ry="9" transform="rotate({a + 30} {x} {y})" {S} stroke-width="2"/>'
        )
    return f'<circle r="36" {S} stroke-width="2.4"/>' + "".join(leaves)


EMBLEMS = {
    "tree": f'<g {S} stroke-width="2.4"><path d="M0-48L-18-20H-9L-27 6H-14L-36 34H36L14 6H27L9-20H18Z"/>'
    f'<path d="M-6 34V46H6V34"/></g><polygon {F} points="{star(5, 6, 2.6)}" transform="translate(0 -50)"/>',
    "menorah": _menorah(),
    "crescent": f'<path {S} stroke-width="2.4" d="M10-44A46 46 0 1 0 10 44A36 36 0 1 1 10-44Z"/>'
    f'<polygon {F} points="{star(5, 8, 3.4)}" transform="translate(30 -14)"/>',
    "lantern": f'<g {S} stroke-width="2.4"><path d="M0-50V-40"/><rect x="-14" y="-40" width="28" height="6" rx="2"/>'
    '<path d="M-12-34C-34-20-34 20-12 34H12C34 20 34-20 12-34Z"/>'
    '<path d="M0-34V34M-14-30C-22-10-22 10-14 30M14-30C22-10 22 10 14 30"/>'
    '<rect x="-14" y="34" width="28" height="6" rx="2"/><path d="M-4 40V52M0 40V54M4 40V52"/></g>',
    "sun": f'<circle r="20" {S} stroke-width="2.4"/>{rays(16, 28, 44, 2.4)}',
    "moon": f'<circle r="40" {S} stroke-width="2.4"/><circle r="40" {F} opacity=".18"/>',
    "pumpkin": f'<g {S} stroke-width="2.4"><ellipse rx="44" ry="34" cy="6"/><ellipse rx="22" ry="34" cy="6"/>'
    '<path d="M0-28C0-36 4-42 10-46"/></g>',
    "maple": _scaled("maple"),
    "poppy": f'<g {S} stroke-width="2.4">{petals(4, 18, 22)}</g><circle r="7" {F}/>',
    "heart": f'<path {S} stroke-width="2.4" d="M0 40C-60 0-40-52 0-20C40-52 60 0 0 40Z"/>',
    "shamrock": f'<g {S} stroke-width="2.4">{petals(3, 20, 20)}<path d="M0 12Q4 36 16 48"/></g>',
    "flame": f'<path {S} stroke-width="2.4" d="M0-48C24-16 32 4 24 24A26 26 0 0 1-24 24C-32 4-16-12 0-48Z"/>'
    '<path fill="none" stroke="currentColor" stroke-width="2.4"'
    ' d="M0-6C8 6 10 14 6 22A7 7 0 0 1-6 22C-10 14-6 8 0-6Z"/>',
    "rangoli": f'<g {S} stroke-width="2.4">{petals(8, 26, 14)}<circle r="12"/><circle r="44"/></g>',
    "burst": rays(12, 14, 46, 2.4) + rays(12, 50, 52, 3),
    "star": f'<polygon {S} stroke-width="2.4" points="{star(5, 46, 19)}"/>',
    "globe": f'<g {S} stroke-width="2.4"><circle r="42"/><ellipse rx="18" ry="42"/>'
    '<path d="M-42 0H42M-37-20H37M-37 20H37"/></g>',
    "wreath": _wreath(),
    "kinara": _kinara(),
    "apple": _scaled("apple", "2"),
    "wheat": _scaled("wheat", "1.6"),
    "boat": f'<g {S} stroke-width="2.4"><path d="M-50 4Q0 30 50 4L44-6Q0 14-44-6Z"/><path d="M44-6Q52-20 42-26"/>'
    '<path d="M-30 12L-38 34M-10 16L-14 38M10 16L14 38M30 12L38 34"/><path d="M-50 44Q-25 36 0 44T50 44"/></g>',
    "gift": f'<g {S} stroke-width="2.4"><rect x="-36" y="-14" width="72" height="56" rx="4"/>'
    '<rect x="-42" y="-26" width="84" height="14" rx="3"/>'
    '<path d="M0-26V42M0-26C-24-56-44-26 0-26C44-26 24-56 0-26"/></g>',
    "candle": f'<g {S} stroke-width="2.4"><rect x="-10" y="-14" width="20" height="58" rx="3"/></g>'
    f'<path {F} d="M0-46C10-34 12-26 8-20A8 8 0 0 1-8-20C-12-26-10-34 0-46Z"/>',
    "egg": f'<path {S} stroke-width="2.4" d="M0-46C24-46 38 0 38 12A38 38 0 0 1-38 12C-38 0-24-46 0-46Z"/>'
    '<path fill="none" stroke="currentColor" stroke-width="2" d="M-36 0L-24-8L-12 0L0-8L12 0L24-8L36 0"/>',
    "leaf": f'<path {S} stroke-width="2.4" d="M0 46C-40 20-40-30 0-48C40-30 40 20 0 46Z"/>'
    f'<path {S} stroke-width="2" d="M0-40V50"/>',
}
