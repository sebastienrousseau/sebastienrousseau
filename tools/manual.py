"""Build the manual at https://sebastienrousseau.com/sebastienrousseau/ with ssg and Lucid.

make manual          # needs the latest ssg on PATH (.github/ssg-version)

    tools/manual.py prepare   # pages and their front matter from the repository's documents
    ssg build -q -f docs-site/ssg.toml
    tools/manual.py finish    # theme assets in, headings anchored, then check

The manual takes the format of doc.dotfiles.io/manual/: ssg with the Lucid
theme (docs-site/themes/lucid, vendored from the dotfiles repository), a
grouped side navigation, breadcrumbs, an "On this page" list and a pager.
Lucid's templates have no loops, so `prepare` renders those per page into
front matter, as dotfiles' tools/docs/build-manual-site.py does.

The pages are the repository's own documents, so they cannot drift: each
H1 becomes the page's headline, its first paragraph the lead, and links to
another document point at its manual page or, failing that, at GitHub.
`finish` fails on a broken internal link, a dangling fragment, or a page
without the copyright line linked to sebastienrousseau.com.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import posixpath
import re
import shutil
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs-site"
THEME = SITE / "themes" / "lucid" / "_layouts"
OUT = ROOT / "_site"
BASE = "/sebastienrousseau/"
REPO_URL = "https://github.com/sebastienrousseau/sebastienrousseau"
BLOB = f"{REPO_URL}/blob/main/"
AUTHOR_URL = "https://sebastienrousseau.com/"
COPYRIGHT = f'<a href="{AUTHOR_URL}" rel="author">Sebastien Rousseau</a>'
LICENCE = "Code licensed under Apache-2.0 OR MIT; the profile's copy and visual identity are reserved."
# Theme files ssg renders around but does not copy.
ASSETS = ("skeletonic.min.css", "styles.css", "theme-init.js", "main.js", "favicon.ico", "assets/logo.svg")
# (source, page, side-navigation group), in reading order.
PAGES = (
    ("docs/index.md", "", "Start"),
    ("docs/ARCHITECTURE.md", "architecture", "Reference"),
    ("docs/DATA.md", "data", "Reference"),
    ("DEVELOPMENT.md", "development", "Contributing"),
    ("SECURITY.md", "security", "Contributing"),
    ("CHANGELOG.md", "changelog", "Contributing"),
)
LINK = re.compile(r"\]\(([^)\s]+)\)")
MD_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
FENCE = re.compile(r"^(```|~~~)")
TAG = re.compile(r"<[^>]+>")
HEADING = re.compile(r"<(h[2-4])([^>]*)>(.*?)</\1>", re.DOTALL)
ID_ATTR = re.compile(r'\bid\s*=\s*"([^"]*)"')
HREF = re.compile(r'\bhref="([^"]*)"')
PROSE = re.compile(r'(<div class="prose">)(.*?)(</div>\s*<nav class="pager")', re.DOTALL)
HIGHLIGHT_LINK = re.compile(r'<link[^>]+href="[^"]*highlight[^"]*\.css"[^>]*>\s*')


@dataclass
class Page:
    source: str
    page: str
    group: str
    headline: str = ""
    lead: str = ""
    body: str = ""
    toc: list[tuple[str, str]] = field(default_factory=list)

    @property
    def url(self) -> str:
        return page_url(self.page)


def slug(text: str) -> str:
    """A heading's id, the same for the Markdown source and the rendered HTML."""
    text = html.unescape(TAG.sub("", text)).replace("&", " and ").replace("'", "")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def unique(base: str, seen: set[str]) -> str:
    candidate, n = base, 2
    while candidate in seen:
        candidate, n = f"{base}-{n}", n + 1
    seen.add(candidate)
    return candidate


def strip_inline(text: str) -> str:
    return re.sub(r"[`*]", "", MD_LINK.sub(lambda m: m[1], text)).strip()


def split_page(text: str) -> tuple[str, str, str]:
    """(headline, lead, body): the H1 and a plain first paragraph move to the layout."""
    lines = text.lstrip("\n").splitlines()
    headline = strip_inline(lines.pop(0)[2:]) if lines and lines[0].startswith("# ") else ""
    while lines and not lines[0].strip():
        lines.pop(0)
    lead: list[str] = []
    if lines and not re.match(r"^\s*([#>|\-*+`~<]|\d+\.|!\[)", lines[0]):
        while lines and lines[0].strip():
            lead.append(lines.pop(0).strip())
    return headline, " ".join(lead), "\n".join(lines).strip() + "\n"


def headings(body: str) -> list[tuple[str, str]]:
    """The H2 headings outside code fences, as (text, id)."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    fenced = False
    for line in body.splitlines():
        if FENCE.match(line.strip()):
            fenced = not fenced
        elif not fenced and line.startswith("## ") and (base := slug(strip_inline(line[3:]))):
            found.append((strip_inline(line[3:]), unique(base, seen)))
    return found


def page_url(page: str) -> str:
    return BASE + (f"{page}/" if page else "")


def relink(text: str, source: str) -> str:
    """Point links at manual pages where the target is one, else at the file on GitHub."""
    pages = {src: page for src, page, _ in PAGES}

    def target(m: re.Match) -> str:
        href = m[1]
        if re.match(r"[a-z]+:|#", href):
            return m[0]
        path, _, anchor = href.partition("#")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        new = page_url(pages[resolved]) if resolved in pages else BLOB + resolved
        return f"]({new}{'#' + anchor if anchor else ''})"

    return LINK.sub(target, text)


def link(href: str, text: str, current: bool = False) -> str:
    here = ' aria-current="page"' if current else ""
    return f'<a href="{html.escape(href)}"{here}>{html.escape(text)}</a>'


def side_nav(pages: list[Page], current: Page) -> str:
    """The side navigation: each group's heading, then its pages."""
    groups: dict[str, list[Page]] = {}
    for p in pages:
        groups.setdefault(p.group, []).append(p)
    blocks = []
    for name, members in groups.items():
        items = "".join(f"<li>{link(p.url, p.headline if p.page else 'Overview', p is current)}</li>" for p in members)
        blocks.append(f'<p class="side-h">{html.escape(name)}</p><ul class="side-list">{items}</ul>')
    return "".join(blocks)


def pager(prev: Page | None, nxt: Page | None) -> str:
    links = []
    for p, cls, label in ((prev, "pager-prev", "Previous"), (nxt, "pager-next", "Next")):
        if p is not None:
            links.append(
                f'<a class="pager-link {cls}" href="{html.escape(p.url)}"><span class="pager-dir">{label}</span>'
                f'<span class="pager-name">{html.escape(p.headline)}</span></a>'
            )
    return "".join(links)


def shared(year: int) -> dict[str, str]:
    """Front matter every page carries: labels, header links, the footer and the version."""
    labels = {
        "label_skip": "Skip to main content",
        "label_menu": "Menu",
        "label_nav": "Main",
        "label_docs_nav": "Manual",
        "label_crumbs": "Breadcrumb",
        "label_pager": "Page",
        "label_toc": "On this page",
        "label_theme": "Theme",
        "label_theme_system": "System",
        "label_theme_light": "Light",
        "label_theme_dark": "Dark",
    }
    nav = {
        "nav_manual": "Manual",
        "nav_data": "Data",
        "nav_profile": "Profile",
        "nav_repo": "GitHub",
        "nav_home": "Manual",
    }
    return {
        "author": "Sebastien Rousseau",
        "language": "en-GB",
        "name": "Profile manual",
        "base_path": BASE,
        "root": BASE,
        "form_origin": "",
        "repo_url": REPO_URL,
        "profile_url": "https://github.com/sebastienrousseau",
        **nav,
        **labels,
        "footer_note": "How the GitHub profile of Sebastien Rousseau is generated, refreshed and checked.",
        "copyright_years": f"© {year}",
        "author_name": "Sebastien Rousseau",
        "author_url": AUTHOR_URL,
        "copyright_licence": LICENCE,
        "version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"],
    }


def front_matter(pages: list[Page], i: int, common: dict[str, str]) -> dict[str, str]:
    """One page's front matter: its own fields, the shared ones, and its rendered navigation."""
    p = pages[i]
    description = p.lead or f"{p.headline}: the profile manual."
    if len(description) > 160:
        description = description[:157].rsplit(" ", 1)[0] + "…"
    first = next(q for q in pages if q.group == p.group)
    return {
        "layout": "doc",
        "title": f"{p.headline} · Profile manual" if p.page else "Profile manual",
        "description": description,
        "headline": p.headline,
        "headline_id": slug(p.headline),
        "lead": p.lead,
        "eyebrow": p.group if p.page else f"Manual · v{common['version']}",
        **common,
        "cur_manual": "" if p.page else ' aria-current="true"',
        "cur_data": ' aria-current="true"' if p.page == "data" else "",
        "side_nav": side_nav(pages, p),
        "crumb_group": f"<li>{link(first.url, p.group)}</li>" if p.page else "",
        "pager": pager(pages[i - 1] if i else None, pages[i + 1] if i + 1 < len(pages) else None),
        "toc_items": "".join(f'<li><a href="#{a}">{html.escape(t)}</a></li>' for t, a in p.toc),
    }


def load() -> list[Page]:
    """Every page, its headline, lead, body and headings, from its source document."""
    pages = []
    for source, page, group in PAGES:
        p = Page(source, page, group)
        p.headline, lead, body = split_page((ROOT / source).read_text())
        p.lead = strip_inline(lead)
        p.body = relink(body, source)
        p.toc = headings(p.body)
        pages.append(p)
    return pages


def generate() -> None:
    """Write docs-site/content/: one Markdown file per page, its front matter as JSON strings."""
    content = SITE / "content"
    shutil.rmtree(content, ignore_errors=True)
    content.mkdir(parents=True)
    pages = load()
    common = shared(dt.datetime.now(dt.UTC).year)
    for i, p in enumerate(pages):
        fields = front_matter(pages, i, common)
        front = "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in fields.items())
        (content / f"{p.page or 'index'}.md").write_text(f"---\n{front}---\n\n{p.body}")


def anchor(page_html: str) -> str:
    """Give the prose's h2 to h4 headings ids, h2 first so they match the contents list."""
    m = PROSE.search(page_html)
    if not m:
        return page_html
    prose, seen = m[2], set(ID_ATTR.findall(page_html))

    def assign(level: str, text: str) -> str:
        def repl(h: re.Match) -> str:
            if h[1] != level or "id=" in h[2] or not (base := slug(h[3])):
                return h[0]
            return f'<{h[1]}{h[2]} id="{unique(base, seen)}">{h[3]}</{h[1]}>'

        return HEADING.sub(repl, text)

    for level in ("h2", "h3", "h4"):
        prose = assign(level, prose)
    return page_html[: m.start(2)] + prose + page_html[m.end(2) :]


def target_of(href: str) -> tuple[Path, str]:
    """The built file an internal `href` names, and its fragment."""
    path, _, frag = href[len(BASE) :].partition("#")
    return (OUT / path / "index.html" if not path or path.endswith("/") else OUT / path), frag


def broken_links(page: Path) -> list[str]:
    """Internal links on `page` that lead nowhere: a missing page or a missing fragment."""
    text, found = page.read_text(), []
    rel = page.relative_to(OUT).as_posix()
    ids = set(ID_ATTR.findall(text))
    for href in map(html.unescape, HREF.findall(text)):
        if href.startswith("#") and href[1:] and href[1:] not in ids:
            found.append(f"{rel}: dangling fragment {href}")
        elif href.startswith(BASE):
            target, frag = target_of(href)
            if not target.is_file():
                found.append(f"{rel}: broken link {href}")
            elif frag and target.suffix == ".html" and frag not in ID_ATTR.findall(target.read_text()):
                found.append(f"{rel}: {href} has no #{frag}")
    return found


def problems() -> list[str]:
    """Why the built manual is not fit to publish, or nothing."""
    found = [f"{a} missing" for a in ASSETS if not (OUT / a).is_file()]
    for _, page, _ in PAGES:
        built = OUT / page / "index.html" if page else OUT / "index.html"
        if not built.is_file():
            found.append(f"{page or 'index'}: not built")
            continue
        if COPYRIGHT not in built.read_text():
            found.append(f"{page or 'index'}: no copyright line linked to sebastienrousseau.com")
        found += broken_links(built)
    return found


def finish() -> int:
    """Complete ssg's output and check it: 0 when it is fit to publish."""
    for asset in ASSETS:
        (OUT / asset).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(THEME / asset, OUT / asset)
    # ssg writes an empty CNAME; this site inherits the user site's domain.
    (OUT / "CNAME").unlink(missing_ok=True)
    # ssg's highlight stylesheet follows the OS colour scheme, not Lucid's
    # toggle, and Lucid styles code itself, so the sheet and its link go.
    for css in OUT.glob("highlight*.css"):
        css.unlink()
    for page in OUT.rglob("index.html"):
        page.write_text(anchor(HIGHLIGHT_LINK.sub("", page.read_text())))
    for problem in (found := problems()):
        print(f"::error::manual: {problem}")
    print(f"manual: {len(PAGES)} pages, {len(found)} problems")
    return 1 if found else 0


def main(args: list[str]) -> int:
    if args == ["prepare"]:
        generate()
        shutil.rmtree(OUT, ignore_errors=True)
        return 0
    if args == ["finish"]:
        return finish()
    print("usage: tools/manual.py prepare | finish", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
