# Antonym collisions: one translation for two opposite labels (pre-registration)

Written and published before the scan below ran. The predictions are graded
as written, failures included. Made by MV2 of Munim, Inc. with AI agents.
Text CC BY 4.0; code Apache-2.0.

## The case that started it: NocoBase "Default expanded"

NocoBase (github.com/nocobase/nocobase, 24.6k stars) has a switch in the
settings of a filter-collapse item. Its stored property is still called
`defaultCollapse`, but turning it on makes the panel start **expanded**
(`AssociationFilter.Item.tsx` puts the field into the Collapse's
`defaultActiveKey` when `defaultCollapse` is true). The English label used to
say "Default collapse", the opposite of what the switch does.

NocoBase PR #8820 ("fix(client): correct default expanded label", merged
2026-03-10) fixed the English. The label is now `t('Default expanded')`, and a
code comment says the old name is historical and the switch means "expanded
by default". The PR added the new key to all 17 locale files in
`packages/core/client/src/locale/`. Chinese got a correct new value (默认展开,
"expanded by default"). Most other locales got the old "collapse" wording,
copied unchanged into the new key.

Values of `"Default expanded"` at commit 10810697 (2026-10-18). We read these
through page fetches of each file and a Sourcegraph search, which agreed. The
scan below checks them byte for byte.

| Locale | Value of "Default expanded" | Meaning |
|---|---|---|
| zh-CN | 默认展开 | expanded by default (correct) |
| zh-TW | 預設展開 | expanded by default (correct; "Default collapse" has the same value) |
| fr-FR | Développé/réduit par défaut | "expanded/collapsed by default" (doesn't say which) |
| de-DE | Standardmäßig eingeklappt | collapsed by default |
| es-ES | Contraer por defecto | collapse by default |
| hu-HU | Alapértelmezett összecsukás | default collapse |
| id-ID | Ciutkan default | collapse by default |
| it-IT | Comprimi di default | collapse by default |
| ja-JP | デフォルト閉じる | close by default |
| ko-KR | 기본 축소 | default collapse |
| nl-NL | Standaard inklappen | collapse by default |
| ru-RU | Сворачивание по умолчанию | collapse by default |
| uk-UA | Згорнути за замовчуванням | collapse by default |
| vi-VN | Thu gọn mặc định | collapsed by default |
| pt-BR | Default collapse | English, the old opposite label |
| tr-TR | Default collapse | English, the old opposite label |

So in 13 of the 16 non-English locales, the switch's label says the opposite
of what it does: 11 translated and 2 left in English. In every one of them
the new key has exactly the same value as the old `"Default collapse"` key.
The fix reached English and Chinese only.

The underlying slip (a source-string fix that doesn't refresh translations) is
well known; gettext marks such strings "fuzzy" for this reason. What makes this
case easy to catch is the shape it leaves behind: **two keys whose English
texts are antonyms of each other ("expanded" vs "collapse") now share one
translation.** Weblate already has a general check for shared translations,
"Reused translation" (since 4.18: "different strings are translated the
same"). It fires on every reused string, many of them harmless. The narrow
version tested here fires only when the two English texts differ by
antonyms alone. That should make it precise enough to act on without a reviewer.

## The rule (fixed before the scan)

In each directory that has an English file (`en-US.json`, `en.json` or
`en_US.json`), every other JSON object file is a locale. Nested objects are
flattened to dotted keys; only string values count.

1. Each English text is lower-cased and split into words `[a-z]+`. A word in
   the antonym list is replaced by its class and gets a side (+ or -). The
   list has 40 classes: expand/collapse, show/hide, enable/disable,
   open/close, lock/unlock, allow/deny, visible/invisible,
   ascending/descending, increase/decrease, max/min, include/exclude,
   select/deselect, pin/unpin, mute/unmute, follow/unfollow, block/unblock,
   favourite/unfavourite, bookmark/unbookmark, subscribe/unsubscribe,
   archive/unarchive, add/remove, import/export, upload/download,
   start/end, before/after, above/below, left/right, first/last,
   next/previous, more/less, in/out, on/off, yes/no, true/false,
   read/unread, public/private, online/offline, connect/disconnect,
   login/logout, required/optional, each with the inflections listed in
   `antonym_scan.py`.
2. Two keys form an **antonym pair** when their word sequences are equal
   after that replacement and the sides differ in an odd number of
   positions. "Collapse" and "Collapsed" are not a pair; "Show hidden" and
   "Hide shown" are not a pair (the two flips cancel).
3. For each pair and each locale where both keys have a non-empty value,
   that is one **comparison**. If the two values are equal, it is
   **flagged**, unless the value equals either English text, in which case it
   is an untranslated **copy** (counted, not flagged).

## Population (pinned before the scan)

- NocoBase at `10810697c31f85d6f2ad7eaa0a0e1990970ea93b`: every
  `*/locale/*.json` and `*/locales/*.json` (core and all plugins).
  Many of the Japanese lines we looked at last changed in one "fix: improve
  locales" commit (#8017), and several locales keep English values, so we
  expect more collisions here.
- Mastodon at `cab53a591ec66159c31b4853271fd15f9e2bbb80`:
  `app/javascript/mastodon/locales/*.json`. These are translated by people on
  Crowdin. It is the comparison project.

Both are read from GitHub's codeload tarballs at those commits.

## Predictions

- **A0** Both tarballs download; at least 100 NocoBase and 50 Mastodon locale
  files parse.
- **A1** In NocoBase `packages/core/client/src/locale`, the pair
  ("Default collapse", "Default expanded") is flagged in exactly de-DE, es-ES,
  fr-FR, hu-HU, id-ID, it-IT, ja-JP, ko-KR, nl-NL, ru-RU, uk-UA, vi-VN and
  zh-TW (13), and is a copy in exactly pt-BR and tr-TR (so zh-CN is neither).
  fr-FR and zh-TW are flagged by the rule even though their "Default
  expanded" label isn't inverted: fr-FR's shared value names both states,
  and in zh-TW it is the old "Default collapse" key that is wrong.
- **A2** The 13 shared values are exactly the ones in the table (after NFC
  normalization; any value equal only after NFC is listed).
- **A3** NocoBase has at least 10 flagged instances besides A1's pair.
- **A4** NocoBase's flagged instances per 1,000 comparisons are at least 5
  times Mastodon's, with at least 500 Mastodon comparisons.
- **A5** (graded by hand from `collisions.csv`) Of the first 60 NocoBase
  flagged instances in file order, at least 60% of those judged are real
  defects: the shared value names only one side, so one of the two labels says
  the wrong thing, or the value names neither side clearly, so users can't tell
  the two apart. Instances in a language the grader can't read with confidence
  are marked unsure and left out; their number is reported.

## Files

- `antonym_scan.py` does the scan and grades A0-A4. `test_antonym_scan.py`
  holds the offline tests (rule, pairing, copies, tarball reading, grading).
- Results will be in `RESULTS.md`, `summary.json` and `collisions.csv` next
  to this file.
- Run in the same job, exploratory and not graded: `zw_count.py` counts
  zero-width characters inside Japanese words in the 33 Japanese files of the
  reading-leak false-positive test (`population.csv`). A page summary said
  DuckPro-Kobra3's file has them (お待ちください with two U+200B inside);
  nothing is claimed until the bytes are counted.

Limits, stated now: one known case; English texts that are antonyms in
meaning but not in this word list (for example "Visible" and "Hidden", which
fall in different classes) are missed by design. A flagged pair is a
candidate, not proof: some languages may use one word for both sides on
purpose (for example a toggle labelled the same either way). A5 is there to
measure that.
