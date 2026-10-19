# Results: l10n-guard 0.11.0's reading-leak warning

Graded 2026-10-18 against the predictions in [READING-LEAK-PREREG.md](../READING-LEAK-PREREG.md),
which was published (commit 4b83277, 19:49 UTC) more than three hours before the job ran (23:04-23:06
UTC) and before any of the rule's code existed. Made by MV2 of Munim, Inc., with AI agents. Text and
tables CC BY 4.0.

## What ran

Compute job `l10n-guard-0110-v1` built l10n-guard 0.11.0 from the 0.10.0 release by a patch script
(sha256 `ce6614bf...` -> `fc917bb2...`, 106,439 -> 107,754 bytes), ran every test file (55 + 6 + 14 +
21 + 13 + 7 + 14 + 15 + 26 + 13 = 184 tests, all passing, one skipped as always), then ran
[eval_0110.py](eval_0110.py) once, in a sealed container. The new rule, as pre-registered:

- a `＃` (U+FF03) that follows a character other than a space or `＃`, then one or more katakana
  (`ァ`-`ヺ`, `ー`), then a second `＃`: regular expression `(?<=[^\s＃])＃[ァ-ヺー]+＃`;
- reported only when the source string has no `#` or `＃`;
- a **warning** (`reading-leak`), since nothing crashes: users just see the reading as text.

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| P1 | nostrmo `lib/l10n/intl_ja.arb` at 94b8c643: `reading-leak` on exactly the 18 named keys, no others | HELD | 18 flagged, none missing, none extra |
| P2 | nostrmo `Search` (`検索けんさく`, a hiragana reading with no signs) is not flagged: the known miss | HELD | not flagged |
| P3 | 0 `reading-leak` warnings on the Japanese files the census already checked (laravel-eval, resx-eval, yaml-eval) at their pinned commits | HELD | 13 files checked, 0 not checked, 0 warnings |
| P4 | the seven unit cases (two flagged, five not) | HELD | 7 of 7 |

The 18 nostrmo strings, as flagged: Block and Blocks `制限＃セイゲン＃`, Custom `カスタム＃カスタム＃`, Data
`データ＃データ＃`, Delete `削除＃サクジョ＃`, Login `ログイン＃ログイン＃`, Members `メンバー＃メンバー＃`, Method
`方法＃ホウホウ＃`, Note, Notes and Posts `動的＃ドウテキ＃`, Private `プライベート＃プライベート＃`, Quote `参照＃サンショウ＃`,
Setting `設定＃セッテイ＃`, Soft `適用＃テキヨウ＃`, Topic and Topics `トピック＃トピック＃`, Url `リンク＃リンク＃`. The
same file also has 14 `missing-key` warnings, which were not part of the predictions.

## What it shows, and what it does not

- **The rule finds the hand-found cases exactly.** All 18 strings found by reading nostrmo's file, and
  nothing else in it. The P4 cases show the edges it was written for: a hashtag (`＃タグ`), ICU's
  plural `＃` (`{＃件}`), a number (`ルール＃1`), a match at the very start of a string, and a source
  that already contains `#` are all left alone.
- **P3 was a weak test, and this page says so.** It held, but none of the 13 Japanese files contains
  a single `＃` (the job counted them: 0 in every file). So P3 shows only that the rule does not
  fire on ordinary Japanese text. It says nothing about how the rule behaves on files that use `＃`
  for other things, which is where false positives would come from. That was a gap in how P3 was
  chosen, not something the job could have caught.
- **The known miss stays a miss.** `検索けんさく` is a reading written in hiragana with no signs. A rule
  for it would also hit ordinary okurigana (kanji followed by hiragana), so it is out of scope by
  design.

## After the run: more cases, and a stronger test

To close the P3 gap, a fresh Sourcegraph keyword search for `＃` in files with Japanese locale paths
(`ja`, `ja-JP`, `ja_JP`, `Japanese`, `values-ja`; JSON, ARB, YAML, PO, TS, JS, XML, properties and
similar) was run around midnight UTC on 2026-10-18/19. Read line by line, it found the same artifact in
**two projects not in the earlier note**:

| Project | File (commit) | Strings |
|---|---|---|
| NocoBase (no-code platform, about 24,600 stars) | `packages/core/client/src/locale/ja-JP.json` (10810697; unchanged on main since 6cf9e8dc, 2026-06-25) | Condition `条件＃ジョウケン＃`, Properties `属性＃ゾクセイ＃`, Sort `ソート＃ソート＃` |
| DuckPro-Kobra3 (custom firmware for a 3D printer, Qt) | `files/app/Translate/LanguageJapanese.ts` (6b5487a5) | Loading `ロード＃ロード＃` |

DuckPro-Kobra3's `ロード＃ロード＃` is the same string NetEase Meeting ships for "load", in an unrelated
project, which again points to a shared machine-translation source. NocoBase's file has 1,500+
strings and these are its only three `＃` values. Other uses of `＃` in the results (Blockly's
`文字列の＃ 終わりからの＃`, `＃お気に入り`, `最後から＃へ`, a `＃` followed by katakana with no closing sign)
are not this artifact, and the rule's pattern does not match them.

The same search also gives a fair false-positive test: 33 Japanese translation files that contain
`＃`, 28 of them in other uses. That test is pre-registered in [FP-PREREG.md](FP-PREREG.md), with
its file list and script, before it runs. These two new cases were found by searching and reading,
not by running the checker; the pre-registered run will check them.

## Limits

- One project (nostrmo) for P1 and P2; P3 had no `＃` to test against (above).
- Files were read, not run. No app was started.
- Code search hit Sourcegraph's match limit, so the cases above are cases, not a rate.
- No project has been contacted.

## Files

- `reading_leak_eval.json`: the nostrmo findings, each P3 file with its sha256 prefix, its issue count
  and its `＃` count, the P4 cases, and the graded predictions, as written by the job.
- `stdout.txt`: the job's full output.
- `eval_0110.py`: the evaluation script.

l10n-guard 0.11.0 is released at
[github.com/munimtechnologies/l10n-guard](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.11.0).
