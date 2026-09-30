"""A minimal SVG document builder that embeds only the glyphs it draws."""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from fonts import Glyphs


@dataclass
class Doc:
    width: int
    height: int
    title: str
    defs: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    glyphs: Glyphs = field(default_factory=Glyphs)

    def add(self, markup: str) -> None:
        self.body.append(markup)

    def text(self, x: float, y: float, s: str, style: tuple[str, float, str], **kw: object) -> None:
        """Draw one line of text in (face, size, fill). kw: anchor, tracking (em), upper."""
        face, size, fill = style
        if kw.get("upper"):
            s = s.upper()
        self.glyphs.add(face, s)
        anchor = kw.get("anchor", "start")
        track = kw.get("tracking", 0)
        spacing = f' letter-spacing="{track * size:.2f}"' if track else ""
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{face}" font-size="{size}"'
            f' fill="{fill}" text-anchor="{anchor}"{spacing}>{escape(s)}</text>'
        )

    def render(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}"'
            f' viewBox="0 0 {self.width} {self.height}" role="img" aria-label="{escape(self.title)}">'
            f"<title>{escape(self.title)}</title>"
            f"<defs><style>{self.glyphs.css()}\ntext{{font-kerning:normal}}</style>"
            f"{''.join(self.defs)}</defs>{''.join(self.body)}</svg>\n"
        )
