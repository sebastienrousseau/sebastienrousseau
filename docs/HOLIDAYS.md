# Holiday themes

On 57 holidays the profile hero changes colour, its lattice points become a
small motif and an icon sits behind the clock. Layout, copy and the clock
itself do not change. This page explains how a theme is chosen and how to
change the calendar.

## How a theme is chosen

`make` renders a light and a dark hero per holiday,
`assets/hero-<key>-<mode>.svg`, beside the everyday `hero-light.svg` and
`hero-dark.svg`, and writes `assets/holidays.json`: every London calendar
day from 1 January of the first year to the end of the last holiday, with
the keys of the holidays on that day.

The profile-clock Worker, from the release that reads the calendar (until
then it serves the everyday hero every day), reads that file. It takes today's
date in London, looks up its keys and, when several holidays share a day,
serves `keys[hour % keys.length]`: they alternate hour by hour in the order
of `holidays.toml`. If the calendar or a holiday hero cannot be fetched, it
serves the everyday hero. The README's image URLs never change.

Holidays are whole London calendar days, 00:00 to 24:00. Jewish and Islamic
days begin at sunset the evening before; the hero shows the civil daytime
date.

## Adding or changing a holiday

Each holiday is one `[[holiday]]` table in `holidays.toml`, in calendar
order:

* `key`: lower-case letters, digits and hyphens, at most 40 characters; it
  names the files and is the only thing the Worker takes from the calendar.
* `accent` and `accent2`: the two colours per mode. Panel, glows and text
  colours are derived from them in `tools/palette.py`, nudged until text
  meets 4.5:1 and graphics 3:1 on the panel.
* `glyph` and `emblem`: art from `tools/motifs.py` and `tools/emblems.py`.
  The emblem is the placeholder until an `icon` is added.
* `quiet = true` for solemn days: a dimmer glow, no second glow, a fainter
  emblem.
* `rule`: when it falls (below).

Run `make`, check the result with `make preview` (open
`_preview/index.html`), and commit `holidays.toml` with the regenerated
files. Deleting a holiday's table deletes its heroes and its calendar days.

## Date rules

| Rule | Meaning | Example |
| --- | --- | --- |
| `fixed MM-DD [n]` | The same date every year, `n` days (default 1) | `fixed 12-26 7` Kwanzaa |
| `easter OFFSET [n]` | Western Easter plus `OFFSET` days | `easter -21` Mothering Sunday |
| `nth N WD MM [n]` | The N-th (1 to 5 or `last`) weekday of a month | `nth last mon 05` Spring Bank Holiday |
| `table [n]` | A start date per year in `dates`, with its `source` | `table 3` Eid al-Fitr |

`rule` may be a list (Remembrance: 11 November and the second Sunday). A
`table` date may be a range, `YYYY-MM-DD..YYYY-MM-DD`, when the length
changes from year to year. A window may run into the next year.

## Sources for table dates

A `table` date is copied from a published source and never worked out or
guessed. Each holiday names its source page or pages in `source`.

| Kind | Source |
| --- | --- |
| Chinese lunisolar | Hong Kong Observatory Gregorian-lunar tables |
| Hebrew | hebcal.com, diaspora |
| Islamic | Umm al-Qura calendar (R.H. van Gent's table, Aladhan's converter) |
| Hindu | Government of India holiday lists; past them, timeanddate.com and dekhopanchang.com |
| Equinoxes and solstices | US Naval Observatory, converted to the London date |
| Events | The organiser's own site or the city's press calendar |

When no source can be opened for a year, that year is left out: the
holiday has no theme then, and `make` prints the gap. Islamic dates follow
the calculated Umm al-Qura calendar; the three-day windows absorb a day's
difference after moon sightings.

To add a year, open the source, copy the date into `dates` and keep the
URL in `source`.

## Adding an icon

Icons come from the Noun Project, downloaded by the maintainer:

```sh
make icon KEY=christmas SVG=~/Downloads/noun_Christmastree_7489615.svg \
  CREATOR="Mustiana Kartika" TITLE="Christmas tree" \
  URL=https://thenounproject.com/icon/christmas-tree-7489615/
```

It sanitises the file into `art/icons/<key>.svg` and prints the `icon = {
... }` line to paste into that holiday. Files from a free download carry
their creator in the file; Pro downloads do not, so pass `CREATOR`. The
build checks each icon against its SHA-256, credits it in `CREDITS.md` and
in the hero's `<desc>`, and fails the size test if the hero passes 60 KB:
pick a simpler icon then.

## When the calendar runs out

`holidays.toml` covers the years in `years`. The smoke check, every 30
minutes, fails once fewer than 180 days of calendar are left, which opens
the refresh issue. Extend `years`, add the new `table` dates, and run
`make`.
