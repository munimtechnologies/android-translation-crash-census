# Results: script-coded gettext catalogs (zh_Hans, zh_Hant, sr_Latn) in LINGUAS

linguas-script census v1, graded 2026-11-12 against [PREREG.md](PREREG.md) (sha256
`5fe068bf9eff6c4cffa8072627d793cf225c205cd74bb99a495a91398c05d497`, published before the job ran).
The job ran 2026-11-12 05:26-05:38 UTC. Made with AI agents working for MV2 of Munim, Inc.
(mv2@munimtech.com). Code: Apache-2.0. Text and data: CC BY 4.0.

## Negatives first

- **H (hand check) FAILED: 8 of 12 sampled catalogs are real; at least 10 were needed.**
  - Three are empty stubs: the `zh_Hans.po` files of elly-code's cherrypick, jorts and inscriptions
    say "Automatically generated", still carry the placeholder revision date, and have no
    translated message. Listing them loses nothing, because there is nothing in them.
  - One is found anyway: Naev (`codeberg.org/naev/naev`) picks its catalog with its own loader
    (`src/gettext.c`). The loader takes only the language part of SDL's preferred locale (`zh`)
    and prefix-matches it against the installed folder names, so `zh` reaches `zh_Hans`. The
    glibc rule this census rests on doesn't apply to Naev.
  - So the census count of "lost" catalogs is too high: it counts empty stubs, and it can't see an
    app's own loader.
- **P5 FAILED: 36 of 52 readable lost catalogs (69%) are substantive (at least half translated and
  not fuzzy); at least 75% was predicted.** The 16 others include the 8 empty elly-code stubs.
- Because H failed, the pre-registered next steps (an l10n-guard check built on this census, and
  issues to the affected projects) do **not** follow from this census.

## What held

| Verdict | Prediction | Result |
|---|---|---|
| M1 HELD | glibc `gettext` with only `LANG` set never reaches a script-coded catalog; the POSIX controls are each reached; with `LANGUAGE` set the script-coded catalogs load | From `zh_CN.UTF-8`, `zh_TW.UTF-8`, `zh_HK.UTF-8`, `zh_SG.UTF-8`, `sr_RS.UTF-8@latin` and `pt_BR.UTF-8`, no `zh_Hans`, `zh_Hant` or `sr_Latn` catalog was reached. `zh_CN`, `zh_TW`, `sr@latin` and `pt_BR` were each reached from their own locale. With `LANGUAGE=zh_Hans` (etc.) each one loaded ([mechanism.json](v1/mechanism.json)) |
| M2 HELD | the same with Python's `gettext.translation(..., fallback=True)` | Same result |
| G PASSED | at least 1,000 repositories read and at least 150 governed | 2,245 of 2,249 repositories read (4 errors), from 3,398 Flathub apps; 527 governed |
| P1 HELD | 2-15% of governed repositories flagged | 50 of 527 = 9.5% |
| P2 HELD | at least half of the flagged repositories have a lost catalog | 40 of 50 (80%) |
| P3 HELD | repositories with a Weblate translate URL flagged more often | 31 of 62 (50%) against 19 of 465 (4.1%) |
| P4 HELD | at least 75% of listed script-coded codes are Chinese | 62 of 68 (91%): `zh_Hans` 39, `zh_Hant` 23, `sr_Latn` 4, `be_Latn` 2 |

Exploratory (not predicted): governed LINGUAS also list `pt-BR` twice, `pt-br` once and `en-us`
once. These spellings are the subject of the separate linguas-spelling census.

## Post-hoc (not pre-registered; read with care)

- 30 of the 40 repositories with a lost catalog have at least one lost catalog that is
  substantive. The 10 others are elly-code's four apps (8 empty stubs), Naev (content not read;
  its own loader finds it anyway) and five with only partly translated lost catalogs (jogger,
  Chronograph, Delineate, Pods, Pipeline).
- The 8 real cases in the hand check are devtoolbox `zh_Hant`, Daikhan `zh_Hans`, Flare `zh_Hans`,
  Escritoire `zh_Hans`, Delineate `zh_Hans`, Filmbook `zh_Hans`, Mousai `zh_Hant` and Frog
  `be_Latn`. Each is a real translation that its build installs under the script-coded name, with
  no `LANGUAGE` setting or renaming found in the files read ([labels.csv](v1/labels.csv); two
  checks were partial, see [DEVIATIONS.md](DEVIATIONS.md)).
- The conservative "lost" rule leaves out seven repositories that list `zh_Hant` next to `zh_CN`
  or `zh` (Tuba, Komikku, fsearch, NewsFlash, tsukimi, Planify, GDM Settings). Under M1, a
  `zh_TW` user of those apps gets English (next to `zh_CN`) or the plain `zh` catalog (next to
  `zh`), not the Traditional one.
- `be_Latn` was not part of the M1/M2 test. glibc names Latin-script Belarusian
  `be_BY.UTF-8@latin`, so the same reasoning applies, but it was not tested.

## Limits

- The population is Flathub apps whose build reads LINGUAS (Meson or autotools). It says nothing
  about apps that list languages in `meson.build` or load catalogs their own way.
- "Not loaded" here means: not reached by glibc or Python gettext from a normal locale with no
  `LANGUAGE` set. A user who sets `LANGUAGE=zh_Hans` by hand, or a desktop that does, gets the
  translation. The census did not survey what desktops put in `LANGUAGE`.
- The hand check read each project's `po/meson.build` and main entry file, not the whole code.

## What happens next

- MV2's own pull request marhkb/pods#1054 added `zh_Hant` to Pods' LINGUAS. PREREG.md promised
  that if M1 held, we would say so on that pull request: M1 held, so we will post the correction
  there (the `zh_Hant` catalog needs the name `zh_TW` to load on a default Taiwan system, and
  Pods' existing `zh_Hans` needs `zh_CN`).
- Any l10n-guard check for script-coded LINGUAS names will be pre-registered separately, will skip
  catalogs with no translated messages, and will be tested on a population other than this one.
- No issues will be filed on the strength of this census alone. Individual reports, if any, will
  each be checked by hand first.

## Files

[v1/](v1/) holds the job's outputs unchanged (`summary.json`, `mechanism.json`, `catalogs.csv`,
`lost_files.csv`, `sample.csv`, `results.jsonl`) and the hand-check labels (`labels.csv`). The
code that produced them is [linguas_script.py](linguas_script.py), with tests in
[test_linguas_script.py](test_linguas_script.py).
