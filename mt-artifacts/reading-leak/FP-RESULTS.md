# Results: the reading-leak rule on 33 Japanese files that use ＃

Graded 2026-10-19 against the predictions in [FP-PREREG.md](FP-PREREG.md), which was published
(commit 12f4c81, 00:09 UTC) three hours before the job ran (03:11-03:12 UTC). Made by MV2 of Munim,
Inc., with AI agents. Text and tables CC BY 4.0.

## What ran

Compute job `reading-leak-fp-v1` ran [test_eval_fp.py](test_eval_fp.py) (12 tests, all passing),
then [eval_fp.py](eval_fp.py) once, in a sealed container. The script downloaded `l10n_guard.py`
from the released v0.11.0 tag (sha256 `fc917bb2...`), checked that its version is 0.11.0 and its
rule is exactly `(?<=[^\s＃])＃[ァ-ヺー]+＃`, fetched the 33 files of [population.csv](population.csv)
at their pinned commits, and ran the rule on every line of every file. The 33 files hold 138 lines
that contain `＃`: 25 in the five files known to ship the artifact, 113 in the 28 files that use the
sign for other things.

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| F0 | All 33 files fetch at their pinned commits | HELD | 33 fetched, none missing |
| F1 | The rule matches exactly 18, 1, 2, 3 and 1 lines in the five leak files (25) and **no line** in the 28 other files | HELD | 25 matched in the leak files, 0 in the others, no differences |
| F2 | The 28 other files hold at least 80 lines with `＃` | HELD | 113 |
| F3 | Read by hand: every matched line is a reading leak, a word followed by its reading (or itself) between `＃` signs | HELD | 25 of 25 |

Four of four held. No line was listed as `value-start` (a match whose `＃` sits right after a quote,
`=`, `:` or `>`), so the line-level test and the shipped string-level check agree on every file.

## F3, line by line

Each matched line, with the word, the text between the signs, and whether that text is the word's
reading or the word itself. Readings are given in Hepburn romanization for the kanji cases.

| File | Key | Value | Between the signs |
|---|---|---|---|
| nostrmo | Block, Blocks | `制限＃セイゲン＃` | セイゲン = *seigen*, the reading of 制限 |
| nostrmo | Custom | `カスタム＃カスタム＃` | the word itself |
| nostrmo | Data | `データ＃データ＃` | the word itself |
| nostrmo | Delete | `削除＃サクジョ＃` | サクジョ = *sakujo*, the reading of 削除 |
| nostrmo | Login | `ログイン＃ログイン＃` | the word itself |
| nostrmo | Members | `メンバー＃メンバー＃` | the word itself |
| nostrmo | Method | `方法＃ホウホウ＃` | ホウホウ = *hōhō*, the reading of 方法 |
| nostrmo | Note, Notes, Posts | `動的＃ドウテキ＃` | ドウテキ = *dōteki*, the reading of 動的 (the translation itself is wrong, "dynamic", but the shape is the same) |
| nostrmo | Private | `プライベート＃プライベート＃` | the word itself |
| nostrmo | Quote | `参照＃サンショウ＃` | サンショウ = *sanshō*, the reading of 参照 |
| nostrmo | Setting | `設定＃セッテイ＃` | セッテイ = *settei*, the reading of 設定 |
| nostrmo | Soft | `適用＃テキヨウ＃` | テキヨウ = *tekiyō*, the reading of 適用 |
| nostrmo | Topic, Topics | `トピック＃トピック＃` | the word itself |
| nostrmo | Url | `リンク＃リンク＃` | the word itself |
| NetEase Meeting (Flutter) | load | `ロード＃ロード＃` | the word itself |
| NetEase Meeting (Electron) | load | `ロード＃ロード＃` | the word itself |
| NetEase Meeting (Electron) | meetingPin | `ロック＃ロック＃` | the word itself |
| NocoBase | Condition | `条件＃ジョウケン＃` | ジョウケン = *jōken*, the reading of 条件 |
| NocoBase | Properties | `属性＃ゾクセイ＃` | ゾクセイ = *zokusei*, the reading of 属性 |
| NocoBase | Sort | `ソート＃ソート＃` | the word itself |
| DuckPro-Kobra3 | Loading | `ロード＃ロード＃` | the word itself |

Ten of the 21 distinct values are kanji words followed by their katakana reading; eleven are
katakana loanwords followed by themselves. Both are the same artifact: a reading field that was
meant to stay out of the text.

## The 113 other lines, and what the rule did with them

None matched, as predicted. They are, by file: Blockly message files in five projects (`文字列の＃
終わりからの＃`, `最後から＃へ`, 4 or 14 lines each in JSON and JS form), odoo's `.po` files (`＃リード`,
`＃ビュー`, "# Leads" and "# Views" as count signs), DBeaver and Phoenix CTMS `.properties` files,
App Inventor's `galleryAppLikeError=＃サーバーエラー：...`, DTube, Talawa, godoos, miniPaint, Smile's
emoji names and Task-Board.

The script also lists, as an exploratory count, every line in the other files where `＃` is
directly followed by katakana: three lines (odoo `＃リード` and `＃ビュー`, App Inventor
`＃サーバーエラー`). All three are a sign at the start of the value with no closing sign, so neither the
rule nor the shipped check fires on them. That is the right outcome for odoo's two ("# Leads",
"# Views"); App Inventor's `＃` looks like a stray character, but it is not a reading leak and
the rule is right to leave it alone.

## What it shows, and what it does not

- **The rule does not fire on other uses of `＃`**, at least not on the 113 lines in 28 files that
  the search returned: hashtags, count signs, list positions, Blockly's string-index messages, and
  a sign at the start of a value. This closes the gap that P3 in [RESULTS.md](RESULTS.md) left
  open, where the 13 files tested had no `＃` at all.
- **Every match is a real case.** 25 of 25, read one by one (F3).
- **This is precision on a found population, not a rate.** Both Sourcegraph searches hit the match
  limit, so these are the Japanese files with `＃` that the searches returned, not all of them.
  A use of `＃` that the search did not reach could still fool the rule; the rule's shape (a
  word, a sign, katakana only, a sign) makes that unlikely but not impossible.
- Files were read, not run. No project has been contacted.

## Files

- `fp_eval.json`: every file with its sha256 prefix, line count, `＃` line count, matched lines,
  value-start lines and katakana-after-sign lines, and the graded F0-F2, as written by the job.
- `lines.csv`: the 25 matched lines and the 3 exploratory lines, one per row.
- `fp_stdout.txt`: the job's full output (`stdout.txt` next to this file is the earlier job's).
- `eval_fp.py`, `test_eval_fp.py`, `population.csv`: the script, its offline tests and the file
  list, published with the pre-registration.
