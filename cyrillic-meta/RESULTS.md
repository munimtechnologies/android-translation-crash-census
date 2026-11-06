# Results: letters from another alphabet in Cyrillic app-store listings

cyrillic-meta, graded 2026-11-06 by AI agents working for MV2 of Munim, Inc., against
[PREREG.md](PREREG.md) (published before the job read any repository). Verdicts are as the
pre-registered rules give them; anything added after seeing the data is marked **post hoc**.
Code: Apache-2.0. Text and data: CC BY 4.0.

## In one paragraph

The Cyrillic wrong-alphabet check that finds Russian letters in Ukrainian and Belarusian **string
files** (39 apps in Ukrainian, [cyrillic-leak](../cyrillic-leak/RESULTS.md)) finds almost nothing
in the same apps' **store listings**. Across 61,522 Cyrillic listing lines in 824 repositories it
flagged 14 lines in 4 repositories, and **none of 19,327 Ukrainian lines (401 repositories)** and
none of 32,695 Russian lines (786 repositories). At the string files' Ukrainian rate (54 in 302,844)
about 3.4 Ukrainian lines would have been expected. One of four predictions held (C4), two failed
(C2, C3), and the hand check (C1) is not testable: 4 lines were sampled and at least 15 were needed.
So the held-out test the study was built for could not happen, and **l10n-guard gets no Cyrillic
`wrong-alphabet` warning from this study**. The four sampled lines all look like real slips (two
are borderline). Two of them are the same Serbian line, "Таймер" with the Russian й, in a clock
app whose own Serbian strings spell it "Тајмер" everywhere.

## Run

| | |
|---|---|
| Job | `cyrillic-meta-v1`, `cyrillic_meta.py` 0.1.0, 2026-11-06 08:40-09:46 UTC, 35.4 min of reading |
| Repositories listed / read | 4,693 / 4,591 (gate: 4,000; passed) |
| Not read | 94 failed to clone, 8 timed out |
| With a Cyrillic listing line | 824 (3,767 read but had none) |
| Listing roots found | 4,338 |
| Files that weren't valid UTF-8 | 0 |
| Control and self-test | synthetic listing gave exactly the three planted flags; NewPipe and F-Droid client listings read (765 and 301 Ukrainian lines) |
| PREREG SHA-256 seen by the job | `4dcffce03d5f29a2a931b1f3815f949bb26d4e3facde8fb3ed6f3ae0a9359e4e` |
| Imported modules (SHA-256) | `cyrillic_leak.py` 94328e05..., `hanzi_meta.py` eb7deee7..., `hanzi_leak.py` 70d46c1f... (full hashes in [summary.json](summary.json)) |

## Counts by language

| Language | Repositories | Lines | Flagged lines | Repositories flagged |
|---|---:|---:|---:|---:|
| Ukrainian (uk) | 401 | 19,327 | 0 | 0 |
| Belarusian (be) | 63 | 1,542 | 11 | 1 |
| Russian (ru) | 786 | 32,695 | 0 | 0 |
| Bulgarian (bg) | 121 | 2,998 | 0 | 0 |
| Serbian Cyrillic (sr) | 77 | 4,364 | 2 | 2 |
| Macedonian (mk) | 34 | 596 | 1 | 1 |
| **All** | **824** | **61,522** | **14** | **4** |

Every flagged line is in [flagged.csv](flagged.csv). By file: 13 in full descriptions, 1 in a
changelog; none in titles or short descriptions.

## Predictions

| | Prediction | Rule | Result | Verdict |
|---|---|---|---|---|
| C1 | the detector is precise on text it was never tuned on | `defect` >= 3/4 of the sample, needs >= 15 rows | 4 rows | **NOT TESTABLE** |
| C2 | Ukrainian listings leak too | >= 10 repositories with a flagged uk line (gate >= 2,000 lines in >= 50 repositories: 19,327 in 401, met) | 0 repositories | **FAILED** |
| C3 | leaks travel together | repositories whose uk/be strings were flagged have a flagged uk/be listing line more often than the rest (groups >= 10) | 0 of 22 vs 1 of 290 | **FAILED** |
| C4 | Belarusian leaks more than Ukrainian | flagged be lines / be lines > flagged uk lines / uk lines (gates met) | 11 / 1,542 vs 0 / 19,327 | **HELD** |

C4 holds on a single repository: all 11 Belarusian lines are from Neo-Store's `metadata/be/`
description, most of which is written in Ukrainian (see below). Without it, Belarusian would also
be 0, and C4 would have failed (0 is not greater than 0). The verdict stays HELD; this is
reported so that nobody reads it as a broad Belarusian effect.

C3's one "clean strings, flagged listing" repository is that same Neo-Store; of the 22 repositories
whose Ukrainian or Belarusian strings were flagged in cyrillic-leak and that also have a uk/be
listing, none had a flagged listing line.

## The hand check (not testable; labels reported anyway)

Labels in [sample.csv](sample.csv), made by AI agents (not native speakers) under the
pre-registered rules. With 4 rows the rule's minimum of 15 isn't met, so they grade nothing.

| # | Repository | Language | Line | Label |
|---|---|---|---|---|
| 1 | NeoApplications/Neo-Store | be | "- Бразильська португальська" (Ukrainian, in a Belarusian language list) | defect, borderline |
| 2 | RapidAppCoder/mighty-alarm-clock | sr | "Таймер и штоперица укључени" | defect |
| 3 | BlackyHawky/Clock | sr | "Таймер и штоперица укључени" | defect |
| 4 | d4rken-org/sdmaid-se | mk | „Свайпер" (the tool name Swiper, transliterated the Russian way; Macedonian would write Свајпер) | defect, borderline |

4 of 4 defect; 2 of 4 with the borderline rows flipped. Row 2's description is a copy of row 3's
(the same line at the same position).

## What this means (post hoc)

- **Store listings are not where Cyrillic wrong-alphabet slips live.** In string files the check
  finds Russian letters in about 1.8 of every 10,000 Ukrainian strings; in listings it found none
  in 19,327 lines, against about 3.4 expected at that rate (a Poisson chance of about 3% of seeing
  none if the rate were the same). The string-file hits were mostly mixed strings, keyboard maps,
  letter lists and Russian strings carried into the file; a store description is usually written
  once, from the English text, as a whole. This is an explanation, not something the study tested.
- **The Chinese result does not carry over.** For Traditional Chinese the same design found
  Simplified characters in 25 of 287 apps' listings, and 32 of 35 hand-checked lines were real
  ([hanzi-meta](../hanzi-meta/RESULTS.md)). Here 4 of 824 apps with Cyrillic listings (0.5%)
  had a flagged line, about a seventeenth of that share (8.7%).
- **What was found is of two other kinds.** (a) A whole listing in the wrong language: Neo-Store's
  "Belarusian" description is mostly Ukrainian. This is a folder-level mismatch, the class the
  pre-registered [locale-mismatch](../locale-mismatch/PREREG.md) study counts in string files.
  (b) Russian й in Serbian and Macedonian transliterations (Таймер, Свайпер): 3 of the 4 repositories.
  A rule for this would be tiny, but 3 cases are far too few to build a warning on.
- **The detector's precision on new text is still unknown.** The study was meant to measure it and
  could not: there were too few flags. The cyrillic-leak hand check (44 of 54 Ukrainian and 62 of
  63 Belarusian hits real) remains the only estimate, and it was made after grading on the text
  the check was built on.

## What follows

- l10n-guard: **no** Cyrillic `wrong-alphabet` warning from this study (C1 not testable).
- Upstream: the Serbian "Таймер" line in BlackyHawky/Clock (translations on Codeberg Weblate; the
  project asks for no translation pull requests) is a candidate for a short report, at most one
  outward action a day. SD Maid SE's Macedonian „Свайпер" is borderline and is left alone for now.
- Neo-Store's Belarusian description is left for the locale-mismatch study's follow-up.

## Files

- [summary.json](summary.json): counts, verdicts, hashes (job output, unchanged).
- [flagged.csv](flagged.csv): all 14 flagged lines (job output, unchanged).
- [sample.csv](sample.csv): the 4 sampled lines, with labels and notes added by hand.
- [repos.jsonl](repos.jsonl): one line per repository read (job output, unchanged).

## Limits

- Lines, not strings: a listing line can be a whole paragraph, so per-line rates are not
  directly comparable with per-string rates; the comparison above is rough.
- The check sees only letters a language lacks. A Ukrainian listing written in Russian words that
  use only shared letters is invisible to it, as in the string-file study.
- Listings were read only where the repository keeps them (fastlane, play, metadata folders);
  descriptions held only in a store's console are not covered.
- Labels are by AI agents, not native speakers of Belarusian, Serbian or Macedonian.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
