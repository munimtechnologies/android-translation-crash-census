# Results: translations left out of `po/LINGUAS` in Flathub apps' source code

Graded 2026-11-09 by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com) against
[PREREG.md](PREREG.md) (SHA-256 `25c24ed6…16c53`, printed by the job). Job `linguas-census-v1`,
run 2026-11-09 17:18-17:34 UTC; its outputs are unchanged under [v1/](v1/). Hand labels are in
[labels.csv](labels.csv). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Headline

**51 of 526 Flathub apps' repositories (9.7%) whose build reads `po/LINGUAS` hold `.po`
translations that the build never compiles.** Users of those languages see English even though
the translation is in the repository. 67 of the 120 readable dropped files are mostly translated,
and together the dropped files hold 14,980 translated messages. All five pre-registered checks held,
and so did the hand check (10 of 12 real; it needed 9).

GNOME-hosted apps, whose translators see a LINGUAS warning on l10n.gnome.org, are flagged at
**1.8%** (2 of 111); the other governed repositories at **11.8%** (49 of 415). That is an
association. GNOME modules also differ in their release processes and maintainer teams.

Meson says nothing when a `.po` file is left out of LINGUAS, but it stops the build when a
listed language has no file. The census found 47 repositories with the silent slip and **none**
with the loud one.

## Gate and predictions

| Item | Rule | Observed | Verdict |
|---|---|---|---|
| Control | GNOME Calculator `po/` reads as meson, lists `de`, `de.po` substantive | passed | PASSED |
| Gate | >= 1,000 repos read, >= 150 governed | 2,238 read, 526 governed (meson 512, autotools 14) | PASSED |
| P1 | 3-25% of governed repos flagged | 51 / 526 = 9.7% | HELD |
| P2 | >= half of dropped files with known content substantive | 67 / 120 | HELD |
| P3 | gnome group flagged at a strictly lower rate | 2/111 (1.8%) vs 49/415 (11.8%) | HELD |
| P4 | meson: fewer repos with a phantom than with a dropped file | 0 vs 47 | HELD |
| **H1** | real × 4 >= 3 × checked, >= 6 checked | **10 real of 12** (40 >= 36) | **HELD** |

Population: 3,394 apps on Flathub's API on 2026-11-09 (list SHA-256 `b32b5e80…7af368`); 2,275
named a repository on a supported host, giving 2,243 repositories, of which 2,238 were read (5 errors).
594 have a LINGUAS directory.

## Hand check (H1)

12 flagged repositories, one dropped file each, chosen by hash before reading
(`v1/sample.csv`). AI agents read `po/LINGUAS` and `po/meson.build` at the recorded commit:

- **Real (10):** mini-text `fr`, merkato `fa`, Design `ko`, minder `fa` (856 of 1,109 messages
  translated), whisper `pt_BR`, **Pods `vi` (881 of 881)**, appeditor `cs`, mousam `fi_FI` (no
  `fi` either), plus two **borderline** cases: Pigment `nl` (a stub, 0 of 41 translated) and
  Draughts `en_US` (an English variant in an English app). Each of these 10 has a
  `po/meson.build` calling `i18n.gettext()` with no `languages:`, and its language is not listed.
- **Not real (2):** warmux `old/wormux-0.8.1/po/el.po` is an archived copy of an old release.
  The app is built from `trunk/`, and the census's excluded-directory list did not include
  `old`. tempo `it_complete.po` is an extra working file; Italian itself is listed.
- **Flips:** counting Pigment as not real gives 9 of 12, which still holds. Counting both
  borderline cases as not real gives 8 of 12, which fails.
- **Not checked by hand:** each app's Flathub manifest. All ten real cases are projects built
  with Meson.

## Exploratory (no predictions)

- **By translation platform (governed repos flagged):** gnome 2/111, weblate 3/62, other 20/136,
  none 25/215, transifex 1/2.
- **Largest translations that ship unused** (translated messages, at the recorded commit):
  Pods `vi` 881, `zh_Hant` 880 and `cs` 538; minder `fa` 856 and `eu` 520; Alpaca `be` 822 and
  `az` 510; MangoJuice `tr_TR` 443; Resources `af_ZA` 339; ThiefMD `pl` 301; Warehouse `eu` 281;
  Gradia `it` 276. Some may be held back on purpose; the census cannot see intent.
- **Builds:** 542 meson LINGUAS directories (50 with a dropped file), 33 autotools (7), 72
  "other" builds (8, not graded), 3 with an explicit `languages:` (not graded). No phantoms in
  any of them.
- No dropped stem differed from a listed language only by case or `-`/`_`. Dropped stems with a
  region added or a lower-case region (`tr_TR`, `fi_FI`, `zh_cn`) do occur. Whether a near
  variant is listed was checked only for mousam (neither `fi` nor `fi_FI`).
- Some flagged directories are not shipped code: warmux contributes four dropped files from
  `old/` copies. The P1 count includes such cases.

## Limits

The build rules come from Meson's and gettext's source, not from building each app. Flathub
over-represents GTK/GNOME apps. HEAD only, so a slip fixed since the last release still counts.
A file may be held back on purpose (an unfinished translation). Labels were made by AI agents.

## What happens next

H1 held. The planned next steps are an l10n-guard `linguas` check (a `.po` next to LINGUAS but
not listed, and a listed language with no file), pre-registered with a held-out test, and
one-line LINGUAS fixes offered upstream one at a time, where each project's rules allow it.
Each fix is checked with `msgfmt --check` first and says it was made with AI agents.
