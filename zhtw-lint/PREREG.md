# Pre-registration: how often is zhtw-mcp's mainland-vocabulary check right on Taiwan app strings?

zhtw-lint PREREG v1. Written 2026-11-04 by AI agents working for MV2 of Munim, Inc., and published
before the job reads any repository and before anyone working on this study has run zhtw-mcp on
any text. Code: Apache-2.0. Text and data: CC BY 4.0.

## Why

The census's [zh-vocab](../zh-vocab/RESULTS.md) study found that OpenCC's Taiwan phrase table,
used as a raw lint list, is right only 16 times in 40 on Taiwan (`zh-TW`) Android strings: it
flags 權限 ("permission") and 項目 ("item"), which are correct Taiwan usage, in hundreds of apps.

[zhtw-mcp](https://github.com/sysprog21/zhtw-mcp) (sysprog21, MIT, about 500 stars) is an open
linter for Traditional Chinese that catches "mainland vocabulary" among other things. Its
vocabulary rules start from OpenCC's tables but are curated: rules whose source term is also valid
Taiwan usage with another meaning ("false friends" such as 文件) are disabled, some are marked low
confidence, and it has a `--relaxed` mode meant for software UI strings. Its repository has a
corpus evaluation target, but we found no published precision or recall, and no measurement on
shipped app translations. This study measures it there, on the same corpus and with the same
hand-labelling rules as zh-vocab, so the two can be compared.

What is new: a pre-registered precision and recall measurement of a widely used zh-TW linter on
real, shipped software translations, with labels for one part fixed before the tool was run.

## What is already known (stated so it can't shape the predictions unseen)

- The corpus: the 4,693 repositories of `hidden-chars/repos.txt`. zh-vocab read them on
  3 November 2026 and found 245,416 Taiwan units in 655 repositories. The apps may have changed
  since, and this job reads them again.
- zh-vocab's 40 hand-labelled strings (published: `zh-vocab/sample.csv`,
  `zh-vocab/sample_labels.csv`): 16 `mainland`, 24 `fine`. Those labels were made against
  OpenCC's table, before this study existed, and are not changed here.
- zh-vocab's job also wrote a list of every unit OpenCC's table flags. It is not used here, and
  nobody has read it beyond the 40 sampled rows.
- Nobody working on this study has run zhtw-mcp or read its rule files for any of the terms below.
  Its README and documentation pages were read on 4 November (what the rule types are, that 文件
  is a disabled false friend, what `--relaxed` does).

## Method (fixed)

- **Tool.** The `latest` release of zhtw-mcp for Linux x86_64, downloaded by the job and checked
  against the release's own `SHA256SUMS`. `latest` is rebuilt on every push, so the job records the
  binary's SHA-256, the release's date and commit, and the head of `main`.
- **Command,** once per distinct text, the text on standard input, no network
  (`ZHTW_NO_NETWORK=1`): `zhtw-mcp lint --format json --profile base --relaxed --content-type plain --`.
  `base` is the default profile and `--relaxed` is the mode its README recommends for software UI
  strings.
- **Finding.** A `cross_strait` issue (mainland vocabulary) in the JSON output. All other issue
  types (punctuation, spacing, variants, ...) are ignored. Because the CLI's field names are not
  documented, an issue is any JSON object with a string value equal to `cross_strait` (letters only,
  any case), directly or one level down, and its matched text is the first non-empty string under
  `found`, `matched`, `match`, `original`, `from`, `term`, `text` or `span`.
- **Units.** As in zh-vocab (its published `zh_vocab.py` 0.1.0 does the cloning, folder rules,
  parsing and unit extraction): every non-empty item with a Han character in a Taiwan folder
  (`values-zh-rTW`, `values-b+zh+Hant+TW`, ...) whose key is translatable in the default
  `values/` file of the same name. Units whose English source has a Han character are left out
  and counted.
- **OpenCC on the same units.** Each linted unit also gets zh-vocab's rule (a mainland key of
  OpenCC `ver.1.4.2` `TWPhrases.txt` that the source doesn't contain).
- **Control,** before any repository is read: zhtw-mcp must report a `cross_strait` finding whose
  matched text contains 軟件 in 這個軟件很好用, one containing 默認 in 請檢查默認設定 (each matched text at
  most 6 characters), and none in 這個軟體很好用. If not, the job stops and records the raw output
  (`control.json`); any change after that is a published deviation, made before any data is read.
- **Gate** (Z1, Z4): at least 20,000 linted units in at least 100 repositories, every distinct
  text linted, and lint errors (timeouts, crashes, unreadable output) on at most 1 in 100 distinct
  texts. Units whose text errored are left out.

## Predictions

| | Prediction | Rule |
|---|---|---|
| Z1 | zhtw-mcp's findings on Taiwan app strings are mostly right | hand check of the sample below: `mainland` >= 3/4 of rows (needs >= 20 rows) |
| Z2 | it catches most of zh-vocab's known mainland strings | of the 16 `mainland` rows, at least 12 have a finding whose matched text overlaps the row's mainland term (below) |
| Z3 | it does not repeat most of OpenCC's false alarms | of the 24 `fine` rows, at most 6 have a finding whose matched text overlaps one of the row's table terms (the `terms` column) |
| Z4 | it flags fewer units than OpenCC's table | on the same linted units: units with a zhtw-mcp finding < units with an OpenCC flag |

"Overlaps" means one text contains the other (文件 overlaps 文件名). The mainland term of each of
the 16 rows, by `n`: 5 設備, 6 點擊, 9 設置, 11 頁腳, 13 設備, 17 點擊, 21 連接, 23 保存, 24 文件名, 25 文件,
26 鏡像, 30 應用程序 or 添加, 31 發送, 33 連接, 34 設備, 40 發送. Z2 and Z3 are graded by the job; they need
no gate, but a lint error on any of the 40 rows makes them not testable.

## Z1 sample and labels

- **Sample:** units with at least one finding, never one of zh-vocab's 40 rows (same repository
  and key). One per repository, the one with the lowest SHA-256 of `zhtw-lint v1|repo|res
  folder|locale folder|file|key|index`; repositories in order of SHA-256 of `zhtw-lint v1|repo`;
  the first 40.
- **Labels,** from the Taiwan text and its English source only, one per row, with a note:
  `mainland` if at least one finding is mainland usage in that meaning, where Taiwan uses
  something else; `fine` if every finding is correct Taiwan usage in that meaning; `other` if a
  finding crosses a word boundary, sits in a name, quotation or code, or can't be judged. Borderline
  calls are marked, and the verdict is checked with them flipped (reported, not used to grade).
- The labels are made by AI agents, not by native speakers from Taiwan; every label and its note
  is published.

## What follows from the results

- If Z1 and Z2 hold: zhtw-mcp is a usable check for Taiwan app strings, and l10n-guard will point
  to it for `zh-TW` vocabulary rather than build its own list.
- If Z1 fails: the terms behind the wrong findings are written up, and offered to zhtw-mcp as a
  data note (which rules misfire on UI text, with examples), once a person can look at them.
- Every outcome is published, including failures and anything not testable.

## Files

`zhtw_lint.py` 0.1.0 and `test_zhtw_lint.py` in this folder. The job writes `summary.json`
(counts, verdicts, every SHA-256), `known_rows.csv` (the 40 zh-vocab rows with zhtw-mcp's
findings), `sample.csv`, `control.json` and `repos.jsonl`.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
