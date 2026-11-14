"""Holiday colour tokens, derived from two accents per mode.

Ported from the approved proposal's prototype (render.py): the panel takes
a tint of the accent, the glows take its hue, and every text colour is
nudged toward black (light) or white (dark) until it meets its contrast
target on that panel. Standard library only.
"""

from __future__ import annotations

import colorsys
from typing import Any, Protocol

from theme import THEMES

# Contrast targets on the panel (WCAG 2.2): body-size text 4.5:1,
# graphics 3:1.
TEXT, GRAPHIC = 4.5, 3.0
STEP = 0.02  # how far ensure() moves toward black or white per try

# Holiday panels: a near-white or near-black base with a touch of accent.
BASE = {"light": ("#f9f9fb", 0.045), "dark": ("#030305", 0.07)}
GLOW_LIGHTNESS = {"light": 0.65, "dark": 0.53}
GLOW2_ALPHA = {"light": 0.16, "dark": 0.2}
EMBLEM_ALPHA = {"light": 0.5, "dark": 0.55}
HERO_GLOW_ALPHA = 0.28  # panels.hero's main glow; quiet themes halve it
QUIET_EMBLEM_ALPHA = 0.35


class Holiday(Protocol):
    """What style() reads from a holiday (holidays.Holiday satisfies it)."""

    name: str
    accent: dict[str, str]
    accent2: dict[str, str]
    quiet: bool
    glyph: str
    spin: bool
    emblem: str


def rgb(h: str) -> list[float]:
    """'#rrggbb' to three floats in 0..1."""
    h = h.lstrip("#")
    return [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def hexc(c: list[float] | tuple[float, ...]) -> str:
    """Three floats in 0..1 (clamped) to '#rrggbb'."""
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in c)


def mix(a: str, b: str, t: float) -> str:
    """The colour t of the way from a to b."""
    return hexc([x + (y - x) * t for x, y in zip(rgb(a), rgb(b), strict=True)])


def _linear(v: float) -> float:
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def lum(h: str) -> float:
    """WCAG relative luminance."""
    r, g, b = map(_linear, rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours."""
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def glow(h: str, mode: str) -> str:
    """A saturated glow in the hue of h, as bright as the mode needs."""
    hue, _, s = colorsys.rgb_to_hls(*rgb(h))
    sat = 1.0 if s > 0.3 else min(1, s * 1.6)
    if mode == "dark":
        sat *= 0.75
    return hexc(colorsys.hls_to_rgb(hue, GLOW_LIGHTNESS[mode], sat))


def ensure(fg: str, bg: str, target: float, mode: str) -> str:
    """fg, nudged toward black (light) or white (dark) until it meets target on bg."""
    end = "#000000" if mode == "light" else "#ffffff"
    t = 0.0
    while contrast(mix(fg, end, t), bg) < target and t < 1:
        t += STEP
    return mix(fg, end, t)


def tokens(accent: str, accent2: str, mode: str) -> dict[str, Any]:
    """The eight colour tokens the proposal gallery was rendered with."""
    base, tint = BASE[mode]
    panel = mix(base, accent, tint)
    every = THEMES[mode]
    return {
        "panel": panel,
        "ink": every["ink"],
        "accent": ensure(accent, panel, TEXT, mode),
        "accent2": ensure(accent2, panel, GRAPHIC, mode),
        "glow": glow(accent, mode),
        "glow2": glow(accent2, mode),
        "glow2_alpha": GLOW2_ALPHA[mode],
        "mute": ensure(every["mute"], panel, TEXT, mode),
    }


def style(h: Holiday, mode: str) -> dict[str, Any]:
    """THEMES[mode] dressed for holiday h: the theme dict panels.hero reads."""
    t = {**THEMES[mode], **tokens(h.accent[mode], h.accent2[mode], mode)}
    t.update(
        glow_alpha=HERO_GLOW_ALPHA,
        glyph=h.glyph,
        spin=h.spin,
        emblem=h.emblem,
        emblem_alpha=EMBLEM_ALPHA[mode],
        name=h.name,
    )
    if h.quiet:
        t.update(glow_alpha=HERO_GLOW_ALPHA / 2, glow2_alpha=0, emblem_alpha=QUIET_EMBLEM_ALPHA)
    return t
