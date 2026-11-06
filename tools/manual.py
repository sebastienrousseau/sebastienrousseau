"""Build the manual at https://sebastienrousseau.com/sebastienrousseau/ with ssg.

make manual          # needs the latest ssg on PATH (.github/ssg-version)

    tools/manual.py prepare   # content and data from the repository's documents
    ssg build -q -f docs-site/ssg.toml
    tools/manual.py finish    # stylesheet in, empty CNAME out, then check

The manual's pages are the repository's own documents, so they cannot
drift: `prepare` copies each into docs-site/content/ with front matter,
points links between them at manual pages and links to any other file at
GitHub, and writes the navigation and the build year into docs-site/data/.
`finish` copies the stylesheet and fails unless every page was built and
carries the copyright line linked to sebastienrousseau.com.
"""

from __future__ import annotations

import datetime as dt
import posixpath
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs-site"
OUT = ROOT / "_site"
BLOB = "https://github.com/sebastienrousseau/sebastienrousseau/blob/main/"
BASE = "https://sebastienrousseau.com/sebastienrousseau"
COPYRIGHT = '<a href="https://sebastienrousseau.com/" rel="author">Sebastien Rousseau</a>'
# (source, page, navigation label, description)
PAGES = (
    ("docs/index.md", "index", "Overview", "How the GitHub profile is generated, refreshed and checked."),
    ("docs/ARCHITECTURE.md", "architecture", "Architecture", "The static and live pipelines, modules and decisions."),
    ("docs/DATA.md", "data", "Data", "The fields of profile.json, the profile's figures as data."),
    ("DEVELOPMENT.md", "development", "Development", "Commands, and how to change copy, panels and sources."),
    ("SECURITY.md", "security", "Security", "How to report a problem, and the protections in place."),
    ("CHANGELOG.md", "changelog", "Changelog", "Every release of the profile."),
)
LINK = re.compile(r"\]\(([^)\s]+)\)")


def url_of(page: str) -> str:
    """A page's path under the manual's base: index is the root."""
    return "/" if page == "index" else f"/{page}/"


def relink(text: str, source: str) -> str:
    """Point links at manual pages where the target is one, else at the file on GitHub."""
    pages = {src: page for src, page, _, _ in PAGES}

    def target(m: re.Match) -> str:
        href = m[1]
        if re.match(r"[a-z]+:|#", href):
            return m[0]
        path, _, anchor = href.partition("#")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        new = BASE + url_of(pages[resolved]) if resolved in pages else BLOB + resolved
        return f"]({new}{'#' + anchor if anchor else ''})"

    return LINK.sub(target, text)


def generate() -> None:
    """Write docs-site/content/ and docs-site/data/ from the repository's documents."""
    content, data = SITE / "content", SITE / "data"
    for directory in (content, data):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)
    for source, page, label, description in PAGES:
        body = relink((ROOT / source).read_text(), source)
        front = f'---\ntitle: "{label}"\ndescription: "{description}"\nlayout: page\n---\n\n'
        (content / f"{page}.md").write_text(front + body)
    nav = "".join(f'[[links]]\nname = "{label}"\nurl = "{url_of(page)}"\n\n' for _, page, label, _ in PAGES)
    (data / "nav.toml").write_text(nav)
    (data / "build.toml").write_text(f"year = {dt.datetime.now(dt.UTC).year}\n")


def problems() -> list[str]:
    """Why the built manual is not fit to publish, or nothing."""
    found = [] if (OUT / "css" / "style.css").is_file() else ["css/style.css missing"]
    for _, page, _, _ in PAGES:
        html = OUT / url_of(page).strip("/") / "index.html"
        if not html.is_file():
            found.append(f"{page}: not built")
        elif COPYRIGHT not in html.read_text():
            found.append(f"{page}: no copyright line linked to sebastienrousseau.com")
    return found


def finish() -> int:
    """Complete ssg's output and check it: 0 when it is fit to publish."""
    (OUT / "css").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SITE / "static" / "style.css", OUT / "css" / "style.css")
    # ssg writes an empty CNAME. This project site inherits the user site's
    # domain and must never claim one of its own.
    (OUT / "CNAME").unlink(missing_ok=True)
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
