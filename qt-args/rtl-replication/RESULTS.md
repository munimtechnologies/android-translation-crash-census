# Replication: right-to-left Qt translations write `%1` as `1%` in 40 other projects too

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0; code Apache-2.0.
Plan: [PREREG.md](PREREG.md), committed before any translation file below was read. Code:
[rtl_replicate.py](rtl_replicate.py). Data: [data/](data/). Nothing was run on a device.

## Verdict: **replicated**

[RTL.md](../RTL.md) reported, as an exploratory finding in 39 Qt projects, that finished
right-to-left translations write a place marker digit-first (`1%` instead of `%1`) far more
often than other languages. The pre-registered test on 40 other open-source Qt projects
(read at their default branches on 2026-10-17, 22:49 UTC) gave:

| | right-to-left reversed | right-to-left finished | rate | other reversed | other finished | rate | ratio | one-sided p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all 40 projects (P1) | 41 | 1,948 | 2.105% | 46 | 82,201 | 0.056% | 37.6 | 2.4e-43 |
| without Pencil2D (P3) | 18 | 1,853 | 0.971% | 37 | 81,014 | 0.046% | 21.3 | 1.2e-16 |

- **Enough data** (at least 500 right-to-left and 10,000 other finished translations with
  markers): yes, 1,948 and 82,201.
- **P1** (ratio at least 5, p < 0.001): **held** (37.6, p = 2.4e-43).
- **P2** (right-to-left reversed rows in at least 3 projects): **held**, 7 projects: Pencil2D 23,
  Mixxx 8, Seafile client 5, Qucs-S 2, OpenBoard 1, NekoRay 1, Veyon 1.
- **P3** (ratio at least 5 and p < 0.01 with the project with the most right-to-left reversed
  rows, Pencil2D, left out of both groups): **held** (21.3, p = 1.2e-16).

All three held, so by the rule fixed in advance the verdict is **replicated**. Counting a
reversed hint anywhere in the row (reported, not graded) gives the same numbers.

The measure is qt_args 0.1.0 unchanged (sha256 `74b0ad4cd2b5b548…`, recorded by the job). All 40
projects were read; one (x64dbg) had no `.ts` files and 20 others had no right-to-left translations,
so the right-to-left side comes from 19 projects. No project was replaced or added. The
excluded group (Kurdish, Sindhi and other often-Arabic-script languages) had no translations in
this corpus.

## By language

| language | finished with markers | reversed | rate |
|---|---:|---:|---:|
| Persian (`fa`) | 270 | 17 | 6.30% |
| Hebrew (`he`) | 545 | 13 | 2.39% |
| Arabic (`ar`) | 708 | 11 | 1.55% |
| Urdu (`ur`) | 310 | 0 | 0% |
| Uyghur (`ug`) | 115 | 0 | 0% |
| all other languages | 82,201 | 46 | 0.056% |

Arabic, Hebrew and Persian all show the pattern again. Urdu does not: its 10 exploratory rows
all came from one project (QOwnNotes), and none of 310 Urdu translations here is reversed.

## Hand check

As the plan required, rows were read with their text before this was written
([data/reversed_rows.csv](data/reversed_rows.csv)):

- **All 41 right-to-left rows.** Each one is a place marker written digit-first where the
  source has `%1`, `%2` or `%3`. Examples: Pencil2D's Persian tool names, where every
  `Brush Tool (%1)`-style label has `(1%)` instead of the shortcut key; its Arabic
  `Easing: frame %1 to %2` with `1%` and `2%`; Seafile's Hebrew `Sync folder "%1"`, which shows
  `"1%"` where the folder name belongs; and Mixxx's Hebrew `Microphone %1` and `Preview Deck %1`,
  which show `1%` instead of the number. None was a percentage in the text, so the 20% correction
  in the plan does not apply.
- **All 46 other rows.** 44 are clearly digit-first markers, for example Dutch
  `Scraping of %1 and %2` with `2%`, and Veyon's Dutch `Veyon Service 1% bij 2%:3%`. Two are
  ambiguous: TeXstudio's Spanish and Polish `Values between 0 and %1` end in `1%`, which a
  translator might have meant as a percentage. Either way the value is lost.

## Other things the data shows (not graded)

- **Copies count more than once.** Mixxx has six Spanish files (`es`, `es_419`, `es_AR`, ...) and
  four Chinese files with the same reversed string, and Pencil2D has three Chinese-script ones
  (`zh_CN`, `zh_TW`, `yue`). These
  copies are mostly on the "other" side, so they make the comparison more conservative, not
  less. Among right-to-left rows, only one Qucs-S string is repeated (in two contexts).
- **Chinese is the next most affected language**: 12 of 7,106 (0.17%), three times the
  other-language rate, from GoldenCheetah, Mixxx, fooyin and Pencil2D. Chinese is written left to
  right, so if this is a real effect its cause is different. It was not predicted and would need
  its own test.
- **Pencil2D carries a large share** (23 of the 41 right-to-left rows: 15 Persian, 8 Arabic).
  Leaving it out entirely still gives 21 times the other-language rate (P3).

## What this does and does not show

It shows that the digit-first form is a common, project-independent failure of right-to-left Qt
translations, not a quirk of Scribus or the first corpus. For Arabic, Hebrew and Persian
together, roughly 1 to 2% of finished translations with markers lose a value this way, against
about 0.05% elsewhere. It does not show why. RTL.md's caution stands: in right-to-left text a
`%` next to digits is laid out by the Unicode bidirectional algorithm, and editors, platforms
and machine translation may each show or produce it differently. We make no claim about who or
what wrote these strings.

Limits: one format (Qt `.ts`); projects chosen from general knowledge of Qt software; projects
that share a translation platform team with an exploratory project are not fully independent of
it; "reversed" is qt_args's first hint only, so the counts are lower bounds; nothing was run in
the apps.

## How to catch it

Qt Linguist's place-marker check flags each such string as a marker mismatch. MV2's
[l10n-guard](https://github.com/munimtechnologies/l10n-guard) (`qt` kind, 0.7.0) reports it, usually as
`qt-arg-missing`, with the hint "looks like %1 written with the % after the number".

## Files

- [data/reversed_rows.csv](data/reversed_rows.csv): every row whose markers lose or misplace a
  value and whose first hint is `reversed`, with repository, commit, file, language, context,
  source and translation.
- [data/repos.csv](data/repos.csv), [data/files.csv](data/files.csv): per repository (commit read)
  and per file counts.
- [data/rtl_replication.json](data/rtl_replication.json),
  [data/rtl_replication.md](data/rtl_replication.md): the job's own report, unedited.
