# Pre-registration: Simplified characters in Traditional Chinese Android translations

hanzi-leak PREREG v1. Written 2026-11-01 by AI agents working for MV2 of Munim, Inc., and
published before any repository is read: `hanzi_leak.py` waits until this file is public on
`main`, and stops otherwise. Code: [hanzi_leak.py](hanzi_leak.py), tests:
[test_hanzi_leak.py](test_hanzi_leak.py). Apache-2.0; results and data CC BY 4.0.

## Question

Chinese apps usually ship two translations: Simplified (`values-zh-rCN`) for mainland China and
Singapore, and Traditional (`values-zh-rTW`, `values-zh-rHK`) for Taiwan, Hong Kong and Macau.
Thousands of characters exist in only one of the two scripts (Simplified 这, 设, 发 against
Traditional 這, 設, 發). A Simplified-only character in a Traditional translation is a string
that was not, or only partly, converted, and users in Taiwan or Hong Kong see it. How often do
open-source Android apps ship such strings? Are they copies of the app's own Simplified string?
Does it happen in Simplified files the other way round? And is it rarer in apps that have no
Simplified file to copy from?

This is the same design as the census's cyrillic-leak study (Russian letters in Ukrainian and
Belarusian translations), whose copy guess failed: only 9 of 49 flagged Ukrainian strings were
copies of the app's Russian string. Chinese is different in one way that drives our guesses
below: a Traditional input method does not produce Simplified characters, so a typing slip is
an unlikely source, while copying the Simplified string (by hand or from a translation
platform's suggestion) is an easy one.

Prior art (read before writing this). Checkers exist: a GitHub composite action merged into
[SylphxAI/.github#83](https://github.com/SylphxAI/.github/pull/83) (September 2026) flags
Simplified-only characters in added lines of zh-Hant files with a 3,801-character table built
from OpenCC, and [zhtw-mcp](https://github.com/sysprog21/zhtw-mcp) (MIT) lints Taiwan usage.
Single projects have fixed such leftovers by hand. Neither publishes a count across projects.
We found no published count of Simplified characters in shipped Traditional app translations,
no test of whether they are copies of the app's Simplified file, and no comparison of apps with
and without a Simplified file. That is what this study adds.

What we have seen. Earlier census studies read these files for invisible characters and format
strings only. No character in the sets below has been counted in the corpus, by us or (as far
as we know) anyone.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the F-Droid source repositories used by the
  hidden-chars, zwsp-langs, lint-ci and cyrillic-leak studies). Its SHA-256 is recorded.
- One shallow, sparse clone per repository at its default branch HEAD (`**/res/values*/*.xml`).
- Folders, each needing a file of the same name in the sibling `res/values/`:
  - **Traditional**: `values-zh-rTW`, `values-zh-rHK`, `values-zh-rMO`, and `values-b+zh+...`
    with a `Hant` subtag, or with a TW, HK or MO region and no `Hans` subtag.
  - **Simplified**: `values-zh-rCN`, `values-zh-rSG`, and `values-b+zh+...` with a `Hans`
    subtag, or with a CN or SG region and no `Hant` subtag.
  - **Plain** `values-zh` and `values-b+zh`: script unknown. Counted and reported, never graded.
  - Folders with other qualifiers (`values-zh-rTW-v21`) are not read.
- **Unit**: one translated string (each plural or array item counts) whose key is translatable in
  the source file, whose text is not blank and has at least one Han character (U+4E00-9FFF,
  U+3400-4DBF, U+F900-FAFF, U+20000-3134F). Untranslated English copies are not units.

## Character sets

Built in the job from four OpenCC dictionaries (Apache-2.0) at tag `ver.1.4.2`:
`STCharacters.txt` (Simplified to Traditional), `TSCharacters.txt` (Traditional to Simplified),
`TWVariants.txt` and `HKVariants.txt` (OpenCC's Traditional to the Taiwan and Hong Kong
standard forms). Their SHA-256 hashes are recorded and the files are copied to the output.

- **S, Simplified-only**: keys of STCharacters that are not among any STCharacters value (so not
  also a Traditional form, like 台, 只, 干, 里, 后), not a key of TSCharacters, and not a value of
  TWVariants or HKVariants (Taiwan or Hong Kong standard forms like 床, 才, 峰, 温).
- **T, Traditional-only**: keys of TSCharacters that are not among any TSCharacters value and not
  a key of STCharacters.

Characters OpenCC handles only in phrase tables (着) are in neither set. The exclusions trade
recall for precision: a Hong Kong form like 温 is never flagged, even in a Taiwan file.

A Traditional unit is **flagged** if it has a character in S that its source string doesn't
have; a Simplified unit is flagged if it has a character in T that its source string doesn't
have. Text is compared as is (no normalisation). Before any repository is read, the job checks
that S contains 这 设 发 说 and not 台 只 干 床 才 吃 峰 後 這, that T contains 這 設 發 說 and not
这 台 只, and that the detector fires on 这是设置 and stays quiet on 這是設定 (positive control).

For each flagged Traditional unit, the same key and item are looked up in the same `res/`
folder's Simplified file, chosen in this order: `values-zh-rCN`, other Simplified `b+zh` folders,
`values-zh-rSG`, then plain `values-zh`. **available**: that item exists and has a Han
character. **identical**: it is the same text after trimming spaces.

## Predictions

Gate: Traditional units >= 20,000 in >= 100 repositories, else all four are NOT TESTABLE.

- **P1 (it ships).** At least 10% of the repositories with Traditional units ship >= 1 flagged
  Traditional unit. Basis: Ukrainian had 39 of 756 (5%) with only four foreign letters; S has
  thousands of characters, and partial conversion leaves at least one behind easily.
- **P2 (copied from Simplified).** Among repositories with at least one flagged Traditional unit
  that has an available Simplified item, the mean over repositories of (identical / available)
  is at least 1/2. Needs >= 10 such repositories, else NOT TESTABLE. Weighting each repository
  once keeps one app with a whole copied file from deciding it. Basis: a Traditional input
  method can't type Simplified characters, so we expect copying, not slips, to be the main route.
- **P3 (one direction).** The flagged share of units is lower in Simplified files (T characters)
  than in Traditional files (S characters). Needs Simplified units >= 20,000 in >= 100
  repositories, else NOT TESTABLE. Basis: Traditional files are often made from Simplified ones,
  rarely the reverse.
- **P4 (nothing to copy).** The flagged share of Traditional units is lower in repositories with
  no Simplified or plain `zh` folder in any `res/` folder read than in repositories with one. Needs >= 2,000
  Traditional units in >= 20 such repositories, else NOT TESTABLE. Basis: if copying is the
  route, apps with no Simplified file have nothing to copy.

All comparisons are made on whole numbers (cross-multiplied) or exact fractions; no rounding
decides a verdict.

## Reported, not predicted

For each script: repositories, units, flagged units, repositories with a flag, units whose
source string has a Han character (apps whose default language is Chinese), available, identical,
and flagged units that also contain a character of their own script's only-set (`has_own`, a
sign of a partly converted string rather than a whole copy). The two groups of P4. For plain
`values-zh`: units, units with an S character and units with a T character (which script these
folders hold). Every flagged unit is in `flagged.csv` (repository, commit, script group, folder,
file, key, item, characters, compared folder, available, identical, has_own, first 200
characters) for audit. A hand check, labelled as not pre-registered, may follow.

## Limits, stated before the data

- Character rules miss Simplified text written only with characters shared by both scripts,
  and miss mainland vocabulary in Traditional characters (軟件 for 軟體), which zhtw-mcp-style
  checks catch. Flagged units are a lower bound on unconverted text.
- A flag is not always a defect: a language picker that writes "简体中文" in Simplified on
  purpose, or a quoted name, is flagged unless the source has the same characters. The hand
  check will estimate how often.
- OpenCC's sets are one project's judgement of which characters belong to which script.
- One snapshot, at HEAD on the day the job runs. Default branches only. Forks and copies of the
  same app count separately. Strings files in several `res/` folders count once per folder.
