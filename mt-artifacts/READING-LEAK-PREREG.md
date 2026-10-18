# Pre-registration: a check for leaked katakana readings in translations

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0. Written before any code for
the check exists. It follows [KATAKANA-READING.md](KATAKANA-READING.md).

## The rule to be added to l10n-guard (after 0.10.0)

A translation gets a **warning** `reading-leak` when both of these hold:

1. it contains a fullwidth number sign `＃` (U+FF03) that follows a character other than a space or
   `＃`, then one or more katakana letters (U+30A1-U+30FA, or the long-vowel mark ー U+30FC), then a
   second `＃`. As a regex: `(?<=[^\s＃])＃[ァ-ヺー]+＃`
2. its source string contains neither `#` nor `＃`.

The message names the reading it found (e.g. `＃サクジョ＃`). It's a warning rather than an error,
because nothing crashes: the user just sees the extra text. It applies to every file kind
l10n-guard reads, since the leak isn't tied to a format.

Known miss, on purpose: a word followed by its reading in hiragana with no signs (nostrmo's
`Search`: `検索けんさく`). A kanji followed by hiragana is ordinary written Japanese (okurigana), so a
rule for it would flag correct text.

## Predictions (graded when the check runs, failures included)

- **P1.** On nostrmo `lib/l10n/intl_ja.arb` at
  [`94b8c64`](https://github.com/haorendashu/nostrmo/blob/94b8c64/lib/l10n/intl_ja.arb), checked
  against `intl_en.arb` at the same commit, the check flags exactly these 18 keys and no others:
  Block, Blocks, Custom, Data, Delete, Login, Members, Method, Note, Notes, Posts, Private, Quote,
  Setting, Soft, Topic, Topics, Url. (None of their English sources contains `#`.)
- **P2.** It does not flag nostrmo's `Search` (`検索けんさく`): the known miss above.
- **P3.** No false positives on Japanese files MV2's census has already checked: 0 `reading-leak`
  warnings on the Japanese files of laravel-eval (Akaunting, UNIT3D, Snipe-IT), resx-eval
  (ONLYOFFICE) and yaml-eval (Sonata, Akeneo, OpenDXP, GOV.UK components, OpenStreetMap), at the
  commits those studies pinned.
- **P4.** Unit cases. Flagged: `ロード＃ロード＃` (source `load`), `削除＃サクジョ＃` (source `Delete`).
  Not flagged: `ルール＃1` (a number sign), `＃タグ` (one sign, a hashtag), `{count, plural, other
  {＃件}}`, `＃サクジョ＃` at the very start of the string (nothing before the first sign), and
  `削除＃サクジョ＃` when its source is `Delete #tag`.

If P1 or P3 fails, the rule is revised before release and the failure is written up here.

## Side observation: nostrmo's Japanese strings were translated from the Chinese ones

Read on 2026-10-18 at `94b8c64`, comparing `intl_en.arb`, `intl_zh.arb` and `intl_ja.arb`:

| Key | English | Chinese | Japanese (before `＃`) | What the Japanese means |
|---|---|---|---|---|
| Note, Notes, Posts | Note / Notes / Posts | 动态 ("posts, feed") | 動的 | "dynamic" |
| Soft | Soft | 应用 ("app, application") | 適用 | "applying (a rule)" |
| Block, Blocks | Block / Blocks | 限制 ("restrict") | 制限 | "restriction" |
| Url | Url | 链接 ("link") | リンク | "link" |

動的 and 適用 make sense only as word-for-word renderings of the Chinese 动态 and 应用, not of the
English keys. So the Japanese file looks like it was made from the Chinese strings, by a tool or
dictionary lookup that also added the readings. This is a reading of one project's files. We have
not run the app, we don't know which tool was used, and we haven't contacted the project.
