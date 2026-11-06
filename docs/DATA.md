# profile.json

Every refresh publishes the profile's figures as data at
<https://raw.githubusercontent.com/sebastienrousseau/sebastienrousseau/profile-data/profile.json>,
beside the panels it draws. `tools/live.py` writes it (`profile_json()`).

`schema` is `1`. It changes only when a field is renamed or removed; new
fields may appear at any time, so read the ones you need and ignore the
rest.

## Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | integer | The format version: `1`. |
| `name` | string | The hero's eyebrow, for example `Sebastien Rousseau · London`. |
| `headline` | string | The hero's headline, on one line. |
| `site` | string | The website. |
| `github` | string | The GitHub profile. |
| `numbers` | object | The figures on the numbers panel, below. |
| `pillars` | array | The four sections and their project cards, below. |
| `articles` | array | The latest articles from the site, newest first. |
| `links` | array | The contact links, each `label` and `url`. |

### numbers

| Field | Type | Meaning |
| --- | --- | --- |
| `all_time_downloads` | integer | crates.io, PyPI and npm downloads since each package was published. |
| `recent_downloads` | integer | The same, over the last `window_days` days. |
| `window_days` | integer | `30`. |
| `github_stars` | integer | Stars over every owned, non-fork repository. |
| `packages` | integer | Crates, PyPI projects and npm packages published. |
| `as_of` | string | The ISO date of the oldest figure above. |

### pillars

Each pillar has `key`, `eyebrow`, `headline`, `lede` and `more` (a link),
copied from `profile.toml`, and `repos`. Each repo has:

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | string | The repository name. |
| `lang` | string | Its main language. |
| `text` | string | The card's description. |
| `url` | string | The repository on GitHub. |
| `stars` | integer or null | Its GitHub stars; null when not yet known. |
| `downloads` | integer | All-time downloads of every package whose own metadata links to this repository; 0 when none does. |

### articles

Each article has `title`, `topic`, `url`, `date` (as displayed, for example
`28 October 2026`) and `published` (the ISO date). An article fetched
before `published` existed may lack it.

## Sources and limits

* Downloads come from each registry's own figures: crates.io, PyPI through
  ClickPy's public mirror of PyPI's download data, and npm. GitHub Packages
  has no public download counts and is not included.
* A figure is held, not published, when it falls further than is
  believable; the previous value stays until a person checks it.
* The file is replaced whole on each refresh, roughly every three hours.
