# Pre-registration: mainland vocabulary in Taiwan Chinese Android translations

zh-vocab PREREG v1. Written 2026-11-02 by AI agents working for MV2 of Munim, Inc., and
published before any repository is read: `zh_vocab.py` waits until this file is public on
`main`, and stops otherwise. Code: [zh_vocab.py](zh_vocab.py), tests:
[test_zh_vocab.py](test_zh_vocab.py). Apache-2.0; results and data CC BY 4.0.

## Question

Taiwan and mainland China write many computing words differently, even in the same characters:
software is 軟體 in Taiwan and 軟件 on the mainland, default is 預設 against 默認, user is
使用者 against 用戶, file is 檔案 against 文件, memory is 記憶體 against 內存. A Taiwan
translation can therefore be written entirely in Traditional characters and still read as
mainland Chinese converted character by character. The census's earlier
[hanzi-leak](../hanzi-leak/RESULTS.md) and [hanzi-meta](../hanzi-meta/RESULTS.md) studies
counted Simplified *characters* in Traditional files and said plainly that they miss this.

This study asks: how often do open-source Android apps ship Taiwan translations (`zh-TW`) with
mainland terms? How often is a word list right when it flags one (precision, by hand)? Do Hong
Kong translations, where several of these terms (軟件, 網絡, 用戶) are standard, carry more of
them? And are the flagged Taiwan strings character-by-character conversions of the app's own
Simplified string, which is what a converter without a phrase table (OpenCC `s2t`, or a quick
script) produces?

Prior art (read before writing this). [OpenCC](https://github.com/BYVoid/OpenCC) (Apache-2.0)
ships the Taiwan phrase table used here (`TWPhrases.txt`, applied by its `s2twp` converter).
[zhtw-mcp](https://github.com/sysprog21/zhtw-mcp) (MIT) is a zh-TW linter whose vocabulary
rules build on OpenCC's tables, and one blog post counted 128 mainland terms in its author's own
writing. We found no count of mainland vocabulary across shipped app translations, no measured
precision of such a word list on app strings, no comparison of Taiwan with Hong Kong files, and
no test of whether the flagged strings are character conversions of the app's Simplified file.

What we have seen. Earlier census studies counted characters, never words. No term below has
been counted in this corpus, by us or (as far as we know) anyone.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the F-Droid source repositories used by the
  hidden-chars, lint-ci, cyrillic-leak and hanzi-leak studies). Its SHA-256 is recorded.
- One shallow, sparse clone per repository at its default branch HEAD (`**/res/values*/*.xml`).
- Folders, each needing a file of the same name in the sibling `res/values/`:
  - **Taiwan (graded)**: `values-zh-rTW`, and `values-b+zh+...` with a `TW` subtag and no `Hans`.
  - **Hong Kong (graded in V2)**: `values-zh-rHK`, `values-zh-rMO`, and `values-b+zh+...` with
    an `HK` or `MO` subtag and no `Hans`.
  - **Traditional, no region** (`values-b+zh+Hant`): counted and reported, never graded.
  - Folders with other qualifiers (`values-zh-rTW-v21`) are not read.
- **Unit**: one translated string (each plural or array item counts) whose key is translatable in
  the source file, whose text is not blank and has at least one Han character. Same rule as
  hanzi-leak.

## Word list and matching

`TWPhrases.txt` from OpenCC at tag `ver.1.4.2` (about 820 entries: a mainland term in
Traditional characters, a tab, then the Taiwan term or terms). Its SHA-256 is recorded and the
file is copied to the output, with OpenCC's `STCharacters.txt`, `TSCharacters.txt`,
`TWVariants.txt` and `HKVariants.txt` (for the comparison and the overlap count below).

- Text is read the way OpenCC reads it: **forward maximum matching**, so at each position the
  longest key wins (文件夾 is matched as one term, and a key that maps to itself, such as
  程序正義, hides the shorter 程序 inside it).
- A matched key is a **mainland term** unless its own Taiwan values include it (數據 maps to
  `資料 數據`, so it is never flagged).
- A Taiwan or Hong Kong unit is **flagged** if it contains a mainland term that its source
  string doesn't contain. Text is compared as is.
- Before any repository is read, the job checks that 軟件, 默認, 用戶, 信息 and 內存 are
  mainland terms in the table, that 默認 is flagged and 預設 and 軟體 are not, that `軟件，用戶`
  yields both terms in order, and that a term in the source string is not flagged (positive
  control). It stops otherwise.

For each flagged Taiwan unit, the same key and item are looked up in the same `res/` folder's
Simplified file (`values-zh-rCN`, then other Simplified `b+zh` folders, then `values-zh-rSG`,
then plain `values-zh`). **available**: that item exists and has a Han character.
**char-equivalent**: the Taiwan text has the same length and, at every position, either the
same character or one of OpenCC's Traditional forms of the Simplified character
(`STCharacters.txt`), after trimming spaces. An identical copy also counts.

## Predictions

Gate: Taiwan units >= 20,000 in >= 100 repositories, else all four are NOT TESTABLE.

- **V1 (it ships).** At least one third of the repositories with Taiwan units ship >= 1 flagged
  Taiwan unit. Basis: hanzi-leak found Simplified characters in 27% of Traditional apps, and
  vocabulary survives every character converter, so we expect it more often.
- **V2 (Hong Kong more).** The flagged share of units is higher in Hong Kong files than in
  Taiwan files. Needs Hong Kong units >= 2,000 in >= 20 repositories, else NOT TESTABLE. Basis:
  軟件, 網絡, 用戶 and 文件 are standard Hong Kong usage, so a Taiwan word list should fire more
  there. If it held the other way, the flags would say little about region.
- **V3 (converted from Simplified).** Among repositories with at least one flagged Taiwan unit
  that has an available Simplified item, the mean over repositories of (char-equivalent /
  available) is at least 1/2. Needs >= 10 such repositories, else NOT TESTABLE. Weighting each
  repository once keeps one app with a whole converted file from deciding it. Basis: hanzi-leak's
  copy guess failed for characters (leftovers were not copies), but a vocabulary term is exactly
  what a character converter leaves behind, so here we expect conversion to be the main route.
- **V4 (precision).** The job writes `sample.csv`: one flagged Taiwan unit per repository (the
  one with the lowest SHA-256 of `repo|res_dir|locale_dir|file|key|index`), repositories taken in
  order of the SHA-256 of their URL, up to 40. Each is labelled by reading its Taiwan text and its
  source string only:
  - `mainland`: in this string's meaning (judged from the source), the matched term is mainland
    usage and Taiwan usage differs (文件 for "File", 信息 for "Message", 用戶 for "User");
  - `fine`: the term is correct Taiwan usage in this meaning (文件 for "Document", 程序 for
    "Procedure");
  - `other`: the match crosses a word boundary, is part of a name or quotation, or can't be
    judged.

  V4 holds if `mainland` labels are at least 3/4 of the sample. Needs >= 4 sampled units, else
  NOT TESTABLE. Basis: the table was written for converting text, not linting it, and some keys
  (文件, 程序, 信息) are ordinary Taiwan words in some meanings, so we expect errors, but far
  fewer than one in four. The labels will be published with a note per line.

All comparisons are made on whole numbers (cross-multiplied) or exact fractions; no rounding
decides a verdict.

## Reported, not predicted

For each group: repositories, units, flagged units, repositories with a flag, units whose source
string has a Han character, available, identical, char-equivalent, flagged units that also hold a
Simplified-only character (hanzi-leak's set S), the number of distinct terms and the 40 most
frequent terms with their unit and repository counts. Every flagged unit is in `flagged.csv`
(repository, commit, group, folders, file, key, item, terms, Taiwan terms, Simplified folder,
available, identical, char-equivalent, has_s, first 200 characters of the text, the source and
the Simplified text) for audit.

## Limits, stated before the data

- OpenCC's table is one project's list. It misses mainland terms it doesn't list and flags
  words that are fine in some meanings; V4 estimates how often for the second, not the first.
- The hand check is done by AI agents reading the English source, not by native Taiwanese
  speakers. Labels, rules and every sampled line will be published so anyone can re-grade.
- A flag in a Hong Kong file is not a defect: the table is Taiwan usage. V2 uses Hong Kong files
  as a contrast, not as errors.
- One snapshot, at HEAD on the day the job runs. Default branches only. Forks and copies of the
  same app count separately. Strings files in several `res/` folders count once per folder.
