# Pre-registration: does the reading-leak rule fire on other uses of ＃?

Written 2026-10-19, before the run, by MV2 of Munim, Inc., with AI agents. Text CC BY 4.0; code
Apache-2.0.

## Why

l10n-guard 0.11.0 warns when a Japanese translation shows a word's katakana reading between
fullwidth number signs (`削除＃サクジョ＃` for "Delete"). Its first test ([RESULTS.md](RESULTS.md)) held,
but its false-positive check (P3) ran on 13 Japanese files that contain no `＃` at all, so it could
not have caught a false positive. This test uses files that do contain `＃` for other things:
Blockly's `文字列の＃ 終わりからの＃`, hashtags, list positions, plural signs and so on.

## Population (fixed before the run)

[population.csv](population.csv): **33 Japanese translation files that contain `＃`**, at the commits
Sourcegraph had indexed (each commit checked on GitHub). They were found by two Sourcegraph
keyword searches for `＃` around midnight UTC on 2026-10-18/19, over files with Japanese locale
paths (`ja`, `ja-JP`, `ja_JP`, `Japanese`, `values-ja`): JSON, ARB and YAML in one search, PO, TS,
JS, XML, properties and similar in the other.

- **5 "leak" files** known, by reading them, to ship the artifact: nostrmo `intl_ja.arb` (18 lines),
  NetEase Meeting `strings_ja.arb` (1) and `ja.ts` (2), NocoBase `ja-JP.json` (3), DuckPro-Kobra3
  `LanguageJapanese.ts` (1). Two of these files were not among the searches' results and were added
  from the earlier note: nostrmo and NetEase Meeting's `strings_ja.arb`.
- **28 "other" files** from the search results that use `＃` otherwise: Blockly message files in
  five projects (JSON and JS), odoo (4 `.po`), DBeaver (3 `.properties`), Phoenix CTMS (4
  `.properties`), App Inventor, DTube, Talawa, godoos, miniPaint, Smile's emoji names, Task-Board.
- **Left out**, with the reason: source code rather than translations (fjordllc/bootcamp's three
  JS files, mama2's `ajax.js`, the `natural` library's Japanese normalizer, tokenizer and specs in
  two repositories), a font map (Simply Love's `_jfonts 16px.ini`), TV listings data (Tempest EPG),
  and two `zh_Hans` files in Shuup (Chinese, not Japanese).

Both searches hit Sourcegraph's match limit, so this population is what the searches returned,
not every Japanese file with `＃` on GitHub.

## Method

[eval_fp.py](eval_fp.py) downloads `l10n_guard.py` from the **released v0.11.0 tag**, refuses to go
on unless its version is 0.11.0 and its rule is exactly `(?<=[^\s＃])＃[ァ-ヺー]+＃`, and runs the rule
on every line of every file. Line level is stricter than the shipped check, which also skips a
string whose source has a number sign. One difference goes the other way: on a line, a `＃` right
after a quote, `=`, `:` or `>` starts the value, and the shipped check sees nothing before it
there. Those matches are listed apart as `value-start` and are not counted as matches. Offline
tests: [test_eval_fp.py](test_eval_fp.py).

## Predictions

| | Prediction |
|---|---|
| F0 | All 33 files fetch at their pinned commits. |
| F1 | The rule matches exactly the expected lines: 18, 1, 2, 3 and 1 in the five leak files (25 lines), and **no line** in the 28 other files. |
| F2 | The 28 other files hold at least 80 lines that contain `＃`, so this test has something to bite on (the searches showed about 110). |
| F3 | Read by hand after the run: every matched line is a reading leak, a word followed by its reading (or itself) between `＃` signs. |

If F1 fails because the rule matches a line in an "other" file, that line is read and called a
false positive or a new case. A false positive means the rule is revised before any later
release, and the failure is written up here.

## Results

To be written in `FP-RESULTS.md` in this folder after the run, failures included.
