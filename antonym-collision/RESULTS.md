# Antonym collisions: results

Results of the scan pre-registered in [PREREG.md](PREREG.md), graded as
written, failures included. Made by MV2 of Munim, Inc. with AI agents; the
A5 hand grading below was also done by AI agents, and no human has checked
it yet. Text CC BY 4.0; code Apache-2.0.

Job `antonym-collision-v1` ran on 2026-10-19 from 03:54:49Z to 03:55:55Z
(python:3.12, network on). All 15 offline tests passed before the scan.
Raw output next to this file: [summary.json](summary.json),
[collisions.csv](collisions.csv), [stdout.txt](stdout.txt),
[zw_count.json](zw_count.json).

## Scorecard

| | Prediction | Result |
|---|---|---|
| A0 | Both tarballs download; >= 100 NocoBase and >= 50 Mastodon locale files parse | **Held**: 1,614 and 105, none unparsed |
| A1 | "Default collapse" / "Default expanded" flagged in exactly the 13 expected locales, copy in exactly pt-BR and tr-TR | **Held**, exactly |
| A2 | The 13 shared values are byte for byte the ones in the table (NFC) | **Held**: no difference, none equal only after NFC |
| A3 | At least 10 NocoBase flagged instances besides A1's pair | **Failed**: 6 |
| A4 | NocoBase rate >= 5x Mastodon's, with >= 500 Mastodon comparisons | **Failed**: 2.91 vs 1.41 per 1,000 (2.1x), 5,672 comparisons |
| A5 | >= 60% of the first 60 NocoBase flagged instances judged are real defects | **Held**: 19 of 19 judged, 0 unsure (see the caveat) |

| Project | Commit | Locale files | Antonym pairs | Comparisons | Flagged | Copies | Per 1,000 |
|---|---|---|---|---|---|---|---|
| NocoBase | 10810697 | 1,614 (132 dirs) | 426 | 6,530 | 19 | 2 | 2.91 |
| Mastodon | cab53a59 | 105 | 93 | 5,672 | 8 | 0 | 1.41 |

## What the failures mean

A3 and A4 were guesses that NocoBase's locales would be much worse than
Mastodon's. They were wrong. NocoBase had 6 flagged instances beyond the
known one, not 10, and its rate is about twice Mastodon's, not five times.
Rule-matching collisions are rare in both projects: under 3 per 1,000
comparisons. The rule picks out a small number of strings, and in our hand
reading most of them really are wrong (A5 below).

## A5: the 19 NocoBase instances, read by hand

There were only 19 flagged instances, so all of them were graded. Each was
judged against the definition fixed in PREREG.md: is the shared value one
side only (so one of the two labels says the wrong thing), or neither side
clearly (so users can't tell the two apart)?

| # | Where | Keys | Shared value | Meaning | Verdict |
|---|---|---|---|---|---|
| 1-2 | `locales/` (root), id-ID | `Required` (client, plugin-map) / `Optional` (plugin-theme-editor) | Wajib | "required" | real: the theme editor's "Optional" tag reads "Required" |
| 3-4 | `locales/` (root), zh-CN, zh-TW | `Add {{type}} after "{{title}}"` / `... before ...` | 在 "{{title}}" 前插入{{type}} | "insert {{type}} **before** {{title}}" | real: the "after" label says "before" |
| 5-16 | `packages/core/client/src/locale`, de-DE es-ES fr-FR hu-HU id-ID it-IT ja-JP ko-KR nl-NL ru-RU uk-UA vi-VN | `Default collapse` / `Default expanded` | see PREREG table | "collapse by default" (fr-FR: "expanded/collapsed by default") | real: the switch that expands the panel is labelled "collapse" (fr-FR: names both, so it doesn't say which) |
| 17-18 | same dir, zh-CN, zh-TW | `Add {{type}} after "{{title}}"` / `... before ...` | 在 "{{title}}" 前插入{{type}} | as 3-4 | real |
| 19 | same dir, zh-TW | `Default collapse` / `Default expanded` | 預設展開 | "expanded by default" | real by the definition: the old "Default collapse" key reads "expanded" |

**Result: 19 of 19 real defects by the pre-registered definition, so A5 held.**

**Caveat, found while grading:** the definition asks only whether a label
says the wrong thing. It does not ask whether users ever see that label. We
then checked how each key is used, with Sourcegraph searches of NocoBase main
at 3638cfc6:

- **Used, so users see the wrong label (14):** the 12 "Default expanded"
  labels (`t('Default expanded')` in the filter-collapse settings), plus the
  Indonesian theme tag. In `plugin-theme-editor`'s `ThemeCard.tsx`, a theme
  that end users may select gets a green `t('Optional')` tag. In Indonesian it
  reads "Wajib" ("Required"), and "Non-optional" reads "Tidak wajib" ("Not
  required"), so the pair is swapped. The plugin's own
  `src/locale/id-ID.json` has the same two values.
- **No use found in code (5):** the old `Default collapse` key (zh-TW,
  instance 19). PR #8820 replaced it, and no `t('Default collapse')` call is
  left. Also the four `Add {{type}} after/before "{{title}}"` instances: a
  regex search for `type}} after|before` outside the JSON files found no
  call. These may be leftover keys, or a key built at run time that the
  search can't see.

So on the stricter question of "wrong *and* shown to users", the count is
14 of 19 confirmed. The other 5 are unknown, not false.

## Exploratory, not pre-registered: Mastodon's 8

The Mastodon instances were graded by hand only out of interest. These
locales are translated by people on Crowdin.

| Locale | Keys | Value | Reading |
|---|---|---|---|
| el | `account.mute_notifications_short` / `unmute_...` | Σίγαση ειδοποιήσεων | "mute notifications": the unmute button says mute (real) |
| eu | `account.menu.hide_reblogs` / `show_reblogs` | Ezkutatu bultzadak denbora-lerroan | "hide boosts in timeline": the show option says hide (real) |
| it | `video.mute` / `video.unmute` | Muta | "mute": the unmute button says mute (real) |
| ku | `account.mute_notifications_short` / `unmute_...` | Agahdariyan bêdeng bike | "silence notifications" (real, lower confidence) |
| mk | `account.mute` / `account.unmute` | Зачути го @{name} | unsure |
| my | `lightbox.next` / `lightbox.previous`; `lightbox.previous` / `report.next`; `status.mute_conversation` / `status.unmute_conversation` | ရှေ့သို့; စကားဝိုင်းကို ပိတ်ထားရန် | unsure (3) |

That is 4 real and 4 unsure. Weblate's "Reused translation" check would also
catch these, but along with every harmless reuse. The antonym rule alone
already narrows them to a short list a reviewer can read in minutes.

## Exploratory: zero-width characters in Japanese words

`zw_count.py` counted zero-width characters (U+200B, U+200C, U+200D, U+2060,
U+FEFF) in the 33 Japanese files of the reading-leak false-positive test. All
33 were fetched. Two files have them **inside** a Japanese word:

- DuckPro-Kobra3 `files/app/Translate/LanguageJapanese.ts` @6b5487a5: 4,
  2 of them inside words. Two U+200B sit inside 受信して<U+200B><U+200B>います
  (line 629) and inside お待<U+200B><U+200B>ちください (line 735).
  This confirms the page summary from the PREREG in bytes.
- Task-Board `src/utils/lang/locale/ja.json`: 2, 1 inside a word. Two U+200B
  split プラ<U+200B><U+200B>グイン ("plugin", line 95).

A third file, mijorus/smile's emoji locale, has 308 zero-width characters,
none inside Japanese words; we did not look at which ones. This is a count
only. Zero-width spaces inside a word are invisible but can break search
and copy-paste; we haven't tested whether they cause any visible fault.

## Limits

- Two projects, one pinned commit each. Rates from two projects say little
  about other projects.
- The word list misses antonyms in different classes ("Visible"/"Hidden")
  by design, so this is precision, not recall.
- The hand grading was done by AI agents and no human has checked it yet.
  For the Burmese and Macedonian instances, the agents could not read the
  language with confidence, so they are marked unsure.
- Nothing here has been reported upstream yet.

## Next

The A5 precision is high enough that the plan in PREREG.md goes ahead:
pre-register an `antonym-collision` warning for l10n-guard, publish that
pre-registration first, and only then build it.
