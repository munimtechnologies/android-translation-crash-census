# Pre-registration: Simplified characters in Traditional Chinese app-store listings

hanzi-meta PREREG v1. Written 2026-11-02 by AI agents working for MV2 of Munim, Inc., and
published before any listing file is read: `hanzi_meta.py` waits until this file is public on
`main`, and stops otherwise. Code: [hanzi_meta.py](hanzi_meta.py), tests:
[test_hanzi_meta.py](test_hanzi_meta.py). Apache-2.0; results and data CC BY 4.0.

## Why

The [hanzi-leak](../hanzi-leak/RESULTS.md) study counted Simplified-only characters in the
Traditional Chinese string files of open-source Android apps: 188 of 692 apps ship them. A hand
check of 40 flagged strings found 39 real defects. That is high precision, but it was measured on
the same files the study was about. Before a check like this goes into a translation linter
(MV2's [l10n-guard](https://github.com/munimtechnologies/l10n-guard)), its precision should be
measured on text it was not checked on before.

This study uses a different kind of text from the same apps: the **app-store listings** (title,
short and full description, release notes) that F-Droid and Google Play show to readers in
Taiwan, Hong Kong and Macau. They are plain text files, often translated by different people
and through different tools than the app's strings. As far as we know, nobody has counted
Simplified characters in Traditional Chinese store listings. The detector and character sets
are exactly the ones hanzi-leak pre-registered; nothing was tuned after its results.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the same 4,693 F-Droid source repositories).
  SHA-256 recorded. One shallow, sparse clone per repository at its default branch HEAD.
- **Listing roots**, any folder whose path ends in `fastlane/metadata/android`,
  `play/listings` or `play/release-notes`, plus a top-level `metadata` folder.
- **Locale folders** directly in a root. Names are read case-insensitively with `_` as `-`:
  - **Traditional**: `zh-TW`, `zh-HK`, `zh-MO`, or a `Hant` subtag (`zh-Hant`, `zh-Hant-TW`).
  - **Simplified**: `zh-CN`, `zh-SG`, or a `Hans` subtag. Plain `zh` is not read.
- **Files**: `*.txt` directly in a locale folder, and in its `changelogs/` folder. Kinds:
  title, short description, full description, changelog (also every file under
  `play/release-notes`), other.
- **Unit**: one non-blank line of a file, after trimming, with at least one Han character
  (the same ranges as hanzi-leak). Files are read as UTF-8; undecodable bytes are replaced and
  the files counted.
- **Source**: the file of the same relative name in the root's `en-US`, `en-GB` or `en` folder
  (first found). A character the source file also has is never flagged.

## Detector (unchanged from hanzi-leak)

S (Simplified-only) and T (Traditional-only) are built from OpenCC `ver.1.4.2` exactly as in
hanzi-leak (the job imports `hanzi_leak.py` from `main` and records its SHA-256). A Traditional
unit is **flagged** if it has a character in S that its source file doesn't have. Simplified
units with a T character are counted the same way and reported. Positive control before any
repository is read: a synthetic listing with `这是设置` in `zh-TW` is flagged and `這是設定` is not.

For each flagged unit: **available** if the root has a Simplified folder (`zh-CN` first, then a
`Hans` folder, then `zh-SG`) with a file of the same relative name; **identical** if that file
has the same trimmed line.

## Predictions

- **M1 (precision).** In the hand-check sample below, at least 80% of flagged Traditional units
  are labelled `defect`. Needs at least 20 units in the sample, else NOT TESTABLE. Graded as
  `defects * 5 >= sample * 4`. Basis: 39 of 40 in hanzi-leak's hand check; listings contain more
  names, quotes and language lists, so we expect lower but still high precision.
- **M2 (it ships).** At least 10% of repositories with Traditional units have a flagged unit.
  Needs Traditional units >= 2,000 in >= 50 repositories, else NOT TESTABLE.
- **M3 (same apps).** Among repositories with Traditional units in both their string files
  (hanzi-leak `repos.jsonl` on `main`) and their listings, the share with a flagged listing unit
  is higher among repositories whose string files were flagged than among those whose string
  files were not. Needs >= 10 repositories in each group, else NOT TESTABLE. Compared by
  cross-multiplication. Basis: the same team and process translate both.

## Hand-check sample and labels (M1)

The job draws the sample before anyone reads a flagged unit: for each repository, its flagged
Traditional units sorted by SHA-256 of `repo|path|line number`, first 2 kept; then all kept
units sorted the same way, first 60 taken. The sample is written to `sample.csv` with an empty
label column. Each unit gets one label, in sample order, from AI agents in one pass:

- `defect`: a flagged character is a Simplified form where the folder's region writes a
  different character, in the listing's own running text.
- `name_or_quote`: the flagged characters are in a proper name, trademark, URL, handle or
  quotation that is written that way in its original.
- `deliberate`: the line shows Simplified text on purpose (for example a list of supported
  languages that writes 简体中文).
- `regional`: the character is the conventional form in that region (for example the
  Cantonese particle written 晒 in Hong Kong).
- `not_chinese`: the line is not Chinese (for example Japanese).

Only `defect` counts toward M1. Labels and a short note per row are published with the results.

## Reported, not predicted

Repositories, units, flagged units and flagged repositories for each script and file kind;
available and identical counts; files with undecodable bytes; the M3 table. Every flagged unit
is in `flagged.csv`.

## Limits, stated before the data

- Same lower-bound caveats as hanzi-leak: shared-character Simplified text and mainland
  vocabulary are not counted.
- Listings in the repository may differ from what a store shows, and F-Droid's own metadata
  repository is not read. One snapshot, default branches only.
- The hand check is one reading by AI agents, not by native readers.
