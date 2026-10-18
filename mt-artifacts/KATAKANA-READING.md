# Japanese translations that ship the word's reading between ＃ signs

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0. An exploratory note:
cases found by searching, not a rate.

## What it looks like

Some Japanese UI strings contain the translated word followed by its katakana reading between
two fullwidth number signs (`＃`, U+FF03). A Japanese user would see the whole thing, e.g. a
**Delete** button that reads `削除＃サクジョ＃` ("delete#sakujo#").

| Project | File | Strings | Examples (key: value) |
|---|---|---:|---|
| [nostrmo](https://github.com/haorendashu/nostrmo) (Flutter Nostr client) | [`lib/l10n/intl_ja.arb`](https://github.com/haorendashu/nostrmo/blob/94b8c64/lib/l10n/intl_ja.arb) at `94b8c64` (the file's latest commit, 2025-09-16) | 18 of 358 | `Delete`: `削除＃サクジョ＃`; `Setting`: `設定＃セッテイ＃`; `Block`: `制限＃セイゲン＃`; `Custom`: `カスタム＃カスタム＃` |
| [NetEase Meeting](https://github.com/GrowthEase/NetEase_Meeting) | `meeting-flutter/meeting_kit/lib/l10n/strings_ja.arb` (main) | 1 | `load`: `ロード＃ロード＃` |
| NetEase Meeting | `meeting-electron/packages/meeting-kit-core/src/locales/ja.ts` (main) | 2 | `load`: `ロード＃ロード＃`; `meetingPin`: `ロック＃ロック＃` |

In each case the text before the first `＃` is a usable translation, and the text between the
signs is its reading in katakana. For a word that is already katakana, that means the word
twice (`ロード＃ロード＃`). nostrmo's file has a second form of the same leak without the signs:
`Search` is `検索けんさく`, the word followed by its hiragana reading. The two NetEase files belong
to two different clients of one product, and they carry the same string, so the artifact probably
came from one shared source of translations.

## Where it probably comes from

The output looks like a reading (furigana) annotation that a tool or a dictionary-style lookup
added, and that was pasted in as the translation. We don't know which tool. A web search
(2026-10-18) found no write-up of this pattern. A placeholder check can't catch it, because no
placeholder is involved. A check for a `＃` in a Japanese string that the source string doesn't
have would catch it.

## How it was found, and limits

- Sourcegraph keyword searches for `＃` in files whose path names Japanese (`ja`, `ja-JP`,
  `ja_JP`, `values-ja`) and in all `.arb` files, on 2026-10-18. The searches hit Sourcegraph's
  match limit, so they are not complete. Other projects may have the same artifact. These are
  the only ones the searches returned.
- Other uses of `＃` in Japanese files were literal: a number sign (`ルール＃1`, Blockly's
  `文字列からの部分文字列を取得 ＃`), a hashtag, or a Markdown heading. None of them is listed here.
- The strings were read in the files and not run in the apps. We haven't contacted either
  project.
- The same searches looked for a fullwidth `＃` used as the number in ICU plural messages
  (`{count, plural, other {＃件}}`, where ICU only reads `#`). They found none. Because the
  searches were not complete, that is not evidence that it never happens.
