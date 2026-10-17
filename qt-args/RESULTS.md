# qt-args 0.1.0 results: Qt translations that put a value in the wrong place

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0, code Apache-2.0.
Method and code: [METHOD.md](METHOD.md), [qt_args.py](qt_args.py). Raw output: [data/](data/).

This was a counting pass with no predictions. The rows were then read by hand, as
METHOD.md promised, and one category was split after reading (see "What changed after
reading"). Nothing here was run on a device: the effects follow from Qt's `arg()` rule
(read in qtbase source) and from each project's own calling code where we read it.

## Headline

In the Qt `.ts` files of 39 open-source desktop projects (180,221 finished translations
whose English source has `%1`-style markers):

| what the app shows | finished translations | share | projects |
|---|---:|---:|---:|
| a value **in the wrong place** (`arg()` fills a slot meant for another value) | **118** | 0.065% | **15** |
| a value lost (its marker is missing or not a marker) | 2,290 | 1.27% | |
| markers renumbered, values still land where the translator put them | 11 | | |
| one marker renumbered and a second one missing (counted with "lost" in spirit) | 1 | | |

The 118 wrong-place rows are the ones a placeholder checker reports only as "missing
marker". They are worse than a missing value: the user sees a real value under the wrong
label. In 9 of 9 call sites we opened (8 projects), the code passes every argument the
English source has, so the effect is real wherever the translation ships. The other rows'
call sites were not opened.

## How a value ends up in the wrong place

`QString::arg()` fills the **lowest-numbered** marker left in the string, and the
multi-argument form gives argument *i* to the *i*-th smallest marker. So if a translation of
`%1 ... %2` loses its `%1`, the first value goes into `%2`, and the second is dropped.

What happened to the lost marker, among the 118 rows (a row can have two):

| what the translator's text has instead | rows |
|---|---:|
| `% 1` (a space after the percent sign) | 32 |
| `1%` (digit before the percent sign: 5 Scribus Arabic messages, plus Catalan, Hungarian, Czech, Irish, Basque and others) | 18 |
| a look-alike percent sign (`％1` fullwidth, `٪` Arabic) | 3 |
| nothing recognisable: the marker was deleted or mistyped (`&1`, `$3`, `1 %2`) | 67 |

Counting all broken rows, not just these 118, the digit-first `1%` form turns up in 3.7% of
finished right-to-left translations and 0.085% of the others, about 40 times as often (an
exploratory count): see [RTL.md](RTL.md).

## Confirmed examples (translation file and calling code both read)

| project, language | source | translation | code | what users see |
|---|---|---|---|---|
| dde-file-manager (Deepin), Armenian (5 messages), Amharic (4), Nepali (1) | `Failed to create the directory %1, cause: %2` | keeps only `%2` | `.arg(url.path(), errorMsg)` | the folder path is shown as the **cause**; the real error is never shown |
| Scribus, Arabic | `Rotate Angle = %1%2` | `زاوية التدوير = 1%2%` | `.arg(angle).arg(suffix)` | an angle of 0 reads **10%**, 45 reads 145%; the degree sign is lost. Same pattern in Skew and Translate |
| Flameshot, Tamil | `Monitor %1: %2 (%3x%4)` | `மானிட்டர்% 1:% 2 (%3x%4)` | `.arg(i + 1).arg(name).arg(width).arg(height)` | the monitor list shows the number and name where the resolution belongs; the resolution is lost |
| Shotcut, Irish | `Ch: %1: %2 (%3 dBFS)` | `Ch: %1:% 2 (%3 dBFS)` | `.arg(c + 1).arg(sample).arg(dB)` | the raw sample value is shown **as the dBFS level**; the dB value is lost |
| qBittorrent, Persian (4 messages, desktop and Web UI) | `%1 (seeded for %2)` | `% 1 (سید برای %2)` | `.arg(activeTime, seedingTime)` | total active time is shown as seeding time |
| Nextcloud desktop, Korean (4 messages) | `... received "%1 %2".` | `... "1 %2"...` | `.arg(httpCode).arg(reason)` | the HTTP code appears after a stray "1"; the reason is lost |
| LibreCAD, Turkish (3 messages) | `... Supplementary: %3 Alternative: %4 ...` | `Tamamlayıcı:%34 Alternatif: %4` | one 9- or 10-argument `.arg(...)` | `%34` is a two-digit marker, so the third and later values land in the wrong slots |
| Cockatrice, Chinese and Cantonese | `%1 lends %2 to %3.` | `%1把&2借給%3.` | `.arg(player).arg(zone).arg(otherPlayer)` | the zone name is shown as the player it was lent to |

## By project (finished translations)

| project | wrong place | value lost | finished with markers |
|---|---:|---:|---:|
| LibreCAD/LibreCAD | 29 | 207 | 7,892 |
| nextcloud/desktop | 16 | 370 | 15,208 |
| linuxdeepin/dde-file-manager | 14 | 216 | 14,686 |
| FreeCAD/FreeCAD | 11 | 582 | 14,752 |
| scribusproject/scribus | 11 | 247 | 12,467 |
| qbittorrent/qBittorrent | 10 | 65 | 17,875 |
| flameshot-org/flameshot | 6 | 19 | 712 |
| Cockatrice/Cockatrice | 4 | 12 | 2,075 |
| wireshark/wireshark | 4 | 5 | 2,780 |
| pbek/QOwnNotes | 4 | 173 | 5,702 |
| mumble-voip/mumble | 3 | 56 | 5,241 |
| mltframework/shotcut | 2 | 62 | 4,621 |
| qTox/qTox | 2 | 20 | 1,500 |
| musescore/MuseScore | 1 | 37 | 7,467 |
| hluk/CopyQ | 1 | 4 | 1,073 |
| the other 24 projects | 0 | 215 | 66,170 |

24 projects have none, including Bitcoin Core, KeePassXC, PCSX2, DuckStation, Tiled and
Fritzing. The median project has 0, so a handful of projects carry most rows.
Unfinished translations add 9 wrong-place rows, all in LibreCAD (lrelease ships unfinished
translations unless it is given `-nounfinished`; we did not check LibreCAD's build flags).

## What changed after reading

The census tagged 16 rows `text_marker_takes_value`: a marker number the source doesn't
have, which receives a value. Reading them showed two different things:

- **4 rows are real and stay in "wrong place"** (they also move other values): LibreCAD
  Turkish `%34` (3 messages) and LibreCAD Galician, where `%0` takes the first of ten values.
- **12 rows display correctly or nearly so** and are taken out of the headline: the
  translator renumbered a marker (`to %1` -> `nach %2` in Deepin German, `%1` -> `%11` in
  qBittorrent Dutch and Mumble Finnish, `'%2'` -> `'%22'` in qBittorrent Latvian, and 7
  more). With one marker per value, the value lands where the translator put it. Qt
  Linguist's "place marker" check and `lrelease -fail-on-invalid` still flag these, which is
  harmless noise. One of them still misleads: Subsurface's Norwegian Bokmål `Fant 1%11
  mediefiler` shows "Fant 15 mediefiler" when 5 files were found, because of the stray
  "1". LibreCAD Hebrew `שטח: %12` for `Area: %1 %2^2` shows the area but drops the unit.

So the headline counts 130 - 12 = 118.

## Qt 6.6 and non-ASCII digits

Two rows differ by Qt version: QOwnNotes Bengali messages using `%১` (Bengali digit one).
Before Qt 6.6 that was a marker; from 6.6 on it is not, so the value disappears. Which one
users see depends on the Qt their build uses (not checked).

## Limits

- Translations at each project's default branch on 2026-10-17; we did not check which ones
  are in released builds.
- 9 call sites read by hand (dde-file-manager, LibreCAD, Nextcloud, Flameshot, qBittorrent,
  Scribus, Cockatrice x2, Shotcut). The other wrong-place rows assume the code passes as many
  arguments as the source has markers. A string formatted by something other than `arg()`
  would be a false positive.
- "Value lost" rows were spot-read (14 rows), not checked one by one.
- Plural (numerus) messages are excluded here; see `qt-numerus/` for those.
- `data/qt_args.md` and `data/by_language.csv` are the raw census output and still count
  the 12 renumbered rows as wrong-place.

## Prior work

Single-project reports exist: Nextcloud desktop #11027 (Danish `% 1`), QGroundControl #15174
(a sync that restored a dropped marker), UNetbootin PR #394 (a `.ts` check across 12
languages), and a validator with the lowest-marker rule in miguelaguiar01/corpus #1003. We
found no count across many projects that sorts mismatches by what `arg()` then shows, and
none that separates "value in the wrong place" from "value lost".

## What comes next

- l10n-guard 0.7.0 (MV2's open checker, built and waiting for its test run) adds a Qt `.ts`
  check that names the wrong-place case ("`%2` shows the value of the source's `%1`") rather
  than only "missing marker". These results suggest a follow-up: report a pure renumbering
  (the 11 rows above) as a warning, not an error. That change is written as 0.7.1 and is
  being tested together with 0.7.0.
- Reports to the projects above, one per project, once MV2's GitHub account is visible again.
