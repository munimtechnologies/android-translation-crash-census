# Results: look-alike letters inside markup tags and format specifiers of Android translations

Graded 2026-11-06 against [PREREG.md](PREREG.md) (lookalike PREREG v1, published before any
repository was read). Made by MV2 of Munim, Inc. with AI agents. Code: Apache-2.0. Text and data:
CC BY 4.0. The hand labels are by AI agents, not native speakers.

## Verdicts

| | Prediction | Rule | Result | Verdict |
|---|---|---|---|---|
| Gate | enough repositories read | >= 4,000 | 4,594 | passed |
| K1 | the defect is not a one-off | >= 10 repositories with a hit | 3 | **FAILED** |
| K2 | it is mostly a Cyrillic problem | > half of hit repositories have a Cyrillic look-alike | 3 of 3 | HELD |
| K3 | tags are hit more often than format specifiers | repositories with a tag hit > with a format hit | 0 vs 3 | **FAILED** |
| K4 | the hits are real defects | `defect` >= 3/4 of the sample, needs >= 8 rows | 3 rows | **NOT TESTABLE** |

One of four predictions held, two failed, and the hand check couldn't be graded because there were
only three repositories to sample. The job's tests and its 12-case control passed before it read
any repository.

## What the job read

`lookalike.py` 0.1.0 (job `lookalike-v1`, 5 November 2026, 20:09 to 20:50 UTC) read the 4,693
repositories of `hidden-chars/repos.txt` at HEAD:

- 2,406 have Android translation folders (87,682 translation files), 2,188 have none, 96 failed to
  clone and 3 timed out. 4,594 were read.
- Those files hold 820,146 ASCII markup tags and 1,823,205 ASCII format specifiers of the kinds the
  finder looks for.
- **Tag hits: 0.** No translation file of any repository has a look-alike letter inside a markup tag.
- **Format hits: 13, in 3 repositories,** all with a Cyrillic letter: `с` (U+0441) 11 times and
  `х` (U+0445) twice. By folder: Russian 5, Ukrainian 4, Abkhaz 2, Bulgarian 2.

| Repository | Folder | Strings | Token | Default string |
|---|---|---|---|---|
| celzero/rethink-app | `values-ab` | `bsdl_blocked_desc` | `%1$с %2$с` | `blocked %1$s by %2$s` |
| nproth/pin | `values-ru` | `action_snooze`, `toast_pin_dismissed`, `toast_pin_background` | `%1$с` | `Snooze %1$s` and two more |
| ritesh-kanwar/Cashiro | `values-bg`, `values-ru`, `values-uk` | `duration_minutes_seconds`, `duration_seconds`, `duration_hours_minutes` (uk) | `%1$с`, `%2$с`, `%1$х`, `%2$х` (in `%1$хв %2$с`, `%1$г %2$хв`) | `%1$dm %2$ds`, `%1$ds`, `%1$dh %2$dm` |

All 13 are in [`hits.csv`](hits.csv) with the commit read; the counts are in
[`summary.json`](summary.json).

## The case that started it was fixed first

The study began with MultiVNC's Russian `changelog_dialog_text`, which closed a link with `</а>`
(Cyrillic а). The pre-registration said MultiVNC would not be counted if a fix was merged before the
job read it. The maintainer merged that one-character fix,
[PR #322](https://github.com/bk138/multivnc/pull/322), on 5 November 2026, and the job read MultiVNC
at `b509666`, the merge commit of #322. So the only look-alike in a tag known before the run had
already gone, and the run found no other in 2,406 repositories. With zero hits, a rough 95% upper
bound (the "rule of three") is about 3 in 2,406 repositories (0.12%) carrying such a tag, or about
4 per million ASCII tags.

## What the format hits are

All 13 were already known. Each is a `crash` row of census 0.4.0 (`data/v6/findings.csv`, 16
October 2026), counted under the README's mistake type "conversion letter in another script":
rethink-app's Abkhaz row (a string the census found no code formatting, so not a reachable crash),
pin's three Russian rows, and Cashiro's Bulgarian, Russian and Ukrainian duration rows, which are
reported in [Cashiro #189](https://github.com/ritesh-kanwar/Cashiro/issues/189) (open, no reply as
of 6 November 2026). The pre-registration disclosed that the census had seen this kind of mistake;
it did not check in advance whether these particular repositories were among them.

Reading the 13 tokens (after grading) shows that none is a look-alike slip in the narrow sense:

- `с` is the Cyrillic letter for the sound *s*. In rethink-app and pin the translator wrote
  `%1$с` for `%1$s`: a transliteration that happens to look like Latin `c`. The finder's table maps
  `с` to `c`, which is why `source_has` is false for every hit: the default string has `%1$s`, not
  `%1$c`.
- In Cashiro, `с` (секунди / секунды, "seconds") and `хв` (хвилини, "minutes") are unit
  abbreviations typed in place of the `d` of `%1$d` plus its unit. The `с` is a unit, not a
  conversion letter.

Every one of them makes `String.format` throw `UnknownFormatConversionException`, and the
census's static check (l10n-guard's `java-format`) and the real JVM already flagged all of them as
crashes. This study adds nothing to how they are found.

## K4: the hand check that couldn't be graded

The sample holds one hit per repository, so it has three rows ([`sample.csv`](sample.csv)), fewer
than the eight K4 needs. The labels ([`sample_labels.csv`](sample_labels.csv)) are reported, not
graded:

| n | Repository | Token | Label | Note |
|---|---|---|---|---|
| 1 | rethink-app (Abkhaz) | `%1$с` | defect | the default string has `%1$s` at that place |
| 2 | pin (Russian) | `%1$с` | defect | the default string has `%1$s` at that place |
| 3 | Cashiro (Bulgarian) | `%2$с` | defect (borderline) | the default string has `%2$d` followed by the unit `s`; the `с` is the Bulgarian unit for seconds and the `d` was dropped. With the borderline call flipped to `other`, 2 of 3. |

## What follows

- **No `lookalike` rule for l10n-guard.** The pre-registration made it depend on K4 holding; K4
  was not testable, and the census found no case the existing checks miss. The tag side, where
  generic checks report only "tag mismatch", turned out to be empty apart from MultiVNC, now fixed.
- **No new upstream fixes.** pin has had no commit since August 2022, Cashiro's rows are already
  reported in #189, and rethink-app's Abkhaz string is translated on Hosted Weblate and isn't
  formatted by the code the census read.
- **Lesson for the next pre-registration:** before predicting a count, search the census's own
  data for the class. The format side of this table could have been counted from
  `data/v6/findings.csv` in advance; only the tag side was really unknown.

## Limits

- One snapshot of each default branch, 5 November 2026. A look-alike fixed on a translation
  platform but not yet exported is still counted, and one fixed in the repository is not.
- The finder looks only at tag names and conversion letters. A look-alike inside an attribute
  (`hrеf`), an attribute value, a URL or a placeholder name is not counted, so zero tag hits means
  zero in tag names, not zero look-alike markup.
- Only `values-*` translation folders in Android `res/` folders were read; store listings and other
  formats were not.
- The finder's table is fixed in advance (30 Cyrillic, 18 Greek and 52 fullwidth letters); a
  look-alike outside it is missed.

## Files

`PREREG.md`, `lookalike.py` 0.1.0 and `test_lookalike.py` (unchanged since pre-registration),
`summary.json`, `hits.csv`, `sample.csv`, `sample_labels.csv` and this file. `repos.jsonl`, one
line per repository, is not committed because of its size; running the job recreates it.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
