# qt-args: right-to-left translations write `%1` as `1%`

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0.
Data: [data/rows.csv](data/rows.csv) and [data/by_language.csv](data/by_language.csv) from the
qt-args 0.1.0 census ([RESULTS.md](RESULTS.md), [METHOD.md](METHOD.md)). Nothing here was run
on a device.

This is an **exploratory** result: we saw the pattern while reading the census rows by hand
and then counted it in the same data. No prediction was made in advance, so treat it as a
finding to test on other data, not as a confirmed law.

**Update (2026-10-17):** a pre-registered test on 40 other Qt projects **replicated** it: right-to-left
2.1% against 0.056% elsewhere, in 7 projects. See [rtl-replication/RESULTS.md](rtl-replication/RESULTS.md).

## The pattern

Qt's `QString::arg()` only reads a place marker written `%` then a digit (`%1`). A translation
that writes the digit first, `1%`, has no marker: the value is never shown and the user sees a
literal "1%". Where a second marker survives, the first value lands in it instead (see
RESULTS.md for Scribus's transform dialog, where an angle of 0 reads "10%").

In right-to-left languages this reversed form is common. In the others it is rare.

| | right-to-left languages | all other languages |
|---|---:|---:|
| finished translations whose source has `%1`-style markers | 7,911 | 172,310 |
| of these, a value lost or in the wrong place | 604 | 1,816 |
| of these, the first hint is a reversed marker (`1%` for `%1`) | **294** | **147** |
| reversed, per finished translation | **3.7%** | **0.085%** |
| reversed, as a share of the broken ones | 48.7% | 8.1% |

Right-to-left here means the census languages `ar` (Arabic), `fa` (Persian), `he` (Hebrew),
`ur` (Urdu), `ug` (Uyghur), `yi` (Yiddish) and `ps` (Pashto). Kurdish (`ku`) is left out
because its files are usually Kurmanji in Latin script; its 14 broken rows have no reversed
marker either way.

By language: Arabic 213, Hebrew 36, Persian 35, Urdu 10; Uyghur, Yiddish and Pashto 0.

## Not one project

Scribus's Arabic file alone has 167 of the 294 rows: almost every marker in it is reversed.
Counting none of those 167 (but keeping all of Scribus's Arabic messages in the denominator,
which makes this a lower bound), right-to-left languages still have 127 reversed rows in
7,911, **1.6%**, about 19 times the rate elsewhere.

Those 127 rows come from at least 14 of the 39 projects:

| project | rows | languages |
|---|---:|---|
| QOwnNotes | 45 | Hebrew 31, Urdu 10, Arabic 4 |
| Nextcloud desktop | 42 | Persian 28, Arabic 14 |
| Deepin dde-file-manager | 8 | Arabic |
| lxqt-panel | 5 | Arabic |
| PCSX2 | 4 | Arabic |
| LibreCAD | 5 | Arabic 3, Hebrew 2 |
| KeePassXC | 3 | Arabic |
| MuseScore | 4 | Persian 2, Arabic 1, Hebrew 1 |
| LMMS, Monero GUI, nomacs, SMPlayer, Shotcut | 1 or 2 each | Arabic, Hebrew |
| other projects | 5 | Persian |

## Examples (translation file read; calling code not opened unless stated)

| project, language | source | translation | what users see |
|---|---|---|---|
| Nextcloud desktop, Persian | `Server %1 is currently in maintenance mode.` | `سرور 1% اکنون در حالت تعمیر است.` | "1%" where the server name belongs |
| Nextcloud desktop, Persian | `Only %1 are available, need at least %2 to start` | `تنها 1% موجود است، حداقل 2% برای شروع مورد نیاز است` | neither the free space nor the space needed |
| QOwnNotes, Hebrew | `Cannot open file %1` | `לא ניתן לפתוח את הקובץ 1%` | the error without the file name |
| Scribus, Arabic | `Cannot write file %1` | `لا يمكن كتابة الملف 1%` | the error without the file name |
| Scribus, Arabic | `Rotate Angle = %1%2` | `زاوية التدوير = 1%2%` | an angle of 0 reads "10%" (call site read in the qt-args run) |

54 rows were read with their text (42 Scribus Arabic, 8 Nextcloud Persian, 4 QOwnNotes
Hebrew). Every one hinted as reversed was a real marker written digit-first, not a percentage
in the text.

## Why, and what it is not

We did not establish why it happens. In right-to-left text a `%` next to digits is laid out by
the Unicode bidirectional algorithm, and editors, translation platforms and machine
translation may each show or produce it differently, so a translator can type what looks
right on screen. Which of these applies to each file we don't know, and we make no claim about
who or what wrote these strings.

## Limits

- One corpus: the Qt `.ts` files of 39 open-source projects at their default branches on
  2026-10-17. Not tested on Android, gettext or other formats yet.
- "Reversed" is the census hint: the marker's digit followed by `%` with no digit or `%` before
  it. Rows where it is the second hint are not counted, so the counts are lower bounds.
- The "broken" row uses the census's raw categories, which still include the 12 renumbered
  rows RESULTS.md takes out of the headline (1 of them, LibreCAD's Hebrew `%12`, is right-to-left).
- Per-file denominators were not recorded, so a rate that leaves Scribus's Arabic file out
  entirely could not be computed; the 1.6% above is a lower bound.
- Found after looking at the data. The pre-registered test on another corpus has since replicated it
  ([rtl-replication/RESULTS.md](rtl-replication/RESULTS.md)).

## Prior work

We found no count or write-up of digit-first place markers in right-to-left translations (one
web search, and the prior work listed in RESULTS.md). Qt Linguist's place-marker check flags
such strings one at a time as a marker mismatch, and the Qt check being added to MV2's
[l10n-guard](https://github.com/munimtechnologies/l10n-guard) names the cause ("looks like %1
written with the % after the number"). Neither says how often it happens or where.
